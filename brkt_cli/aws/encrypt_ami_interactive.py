import json
import os
import re
import urllib2
from abc import ABCMeta, abstractmethod
from argparse import Namespace
from getpass import getpass

import boto.ec2

from brkt_cli.yeti import YetiService


def format_error(message):
    return 'Error: ' + message


class InteractiveArgument(object):
    __metaclass__ = ABCMeta
    
    def __init__(self):
        pass

    @abstractmethod
    def run(self):
        pass


class InteractiveTextField(InteractiveArgument):
    def __init__(self, prompt):
        self.prompt = prompt
        super(InteractiveTextField, self).__init__()

    def run(self, has_back=False):
        val = ''
        while val == '':
            print self.prompt + (' (leave blank to go back)' if has_back else '') + ':',
            val = raw_input()
            if val == '' and has_back:
                return None
        return val


class InteractivePasswordField(InteractiveArgument):
    def __init__(self, prompt):
        self.prompt = prompt
        super(InteractivePasswordField, self).__init__()

    def run(self, has_back=False):
        val = ''
        while val == '':
            val = getpass(self.prompt + (' (leave blank to go back)' if has_back else '') + ': ')
            if val == '' and has_back:
                return None
        return val


class InteractiveSelectionMenu(InteractiveArgument):
    def __init__(self, prompt, options):
        self.prompt = prompt
        self.options = options
        super(InteractiveSelectionMenu, self).__init__()

    def run(self, has_back=False):
        return InteractiveSelectionNameKeyMenu(self.prompt, map(lambda x: (x,x), self.options)).run(has_back=has_back)


class InteractiveSelectionNameKeyMenu(InteractiveArgument):
    def __init__(self, prompt, options):
        """

        :param prompt:
        :param options: list of tuples containing the name and key/ID of the option
        :type options: list[(str, (Any | None))]
        """
        self.prompt = prompt
        self.options = options
        super(InteractiveSelectionNameKeyMenu, self).__init__()

    def run(self, has_back=False):
        print self.prompt + ':'
        option_list = self.options

        if has_back:
            option_list.append(('[Back]', None))

        for idx, (name, key) in enumerate(option_list):
            print '%d) %s' % (idx, name)

        val = ''
        val_idx = None
        while val == '':
            print '>',
            val = raw_input()
            if val == '':
                continue

            if not val.isdigit():
                print format_error('Value is not digit')
                val = ''
                continue

            try:
                val_idx = int(val)
            except AssertionError as err:
                print format_error(err.message)
                val = ''
                continue

            if val_idx >= len(option_list):
                print format_error('Value is not an option')
                val = ''
                continue

        name, key = option_list[val_idx]
        return key


class InteractiveSuperMenu(InteractiveArgument):
    def __init__(self, prompt, options):
        """

        :param prompt:
        :param options:
        :type options: list[(str, (() -> (str | None)) | None)]
        """
        self.prompt = prompt
        self.options = options
        super(InteractiveSuperMenu, self).__init__()

    def run(self, has_back=False):
        while True:
            ret = InteractiveSelectionNameKeyMenu(self.prompt, self.options).run(has_back=has_back)
            if ret is None:
                return None
            ret_called = ret()
            if ret_called is not None:
                return ret_called


# Gets the list of official non-AWS Marketplace Ubuntu AMIs
def get_ubuntu_amis():
    resp = urllib2.urlopen("https://cloud-images.ubuntu.com/locator/ec2/releasesTable")
    resp_str = resp.read()
    resp.close()
    # This API endpoint returns faulty JSON with a trailing comma. This regex removes this trailing comma
    resp_str = re.sub(",[ \t\r\n]+}", "}", resp_str)
    resp_str = re.sub(",[ \t\r\n]+\]", "]", resp_str)
    ami_data = json.loads(resp_str)['aaData']
    return ami_data


# The API endpoint returns an HTML tag with the AMI ID in it. This regex just gets the AMI ID
def get_ubuntu_ami_id_from_row(ami_row):
    match_obj = re.match('^<.+>(ami-.+)</.+>$', ami_row[6])
    return match_obj.group(1)


def run_interactive(values, parsed_config):
    if 'BRKT_API_TOKEN' not in os.environ:
        email = InteractiveTextField('Enter Email').run()
        password = InteractivePasswordField('Enter Password').run()

        _, env = parsed_config.get_current_env()
        root_url = 'https://%s:%d' % (
            env.public_api_host, env.public_api_port)
        y = YetiService(root_url)

        token = y.auth(email, password)
        os.environ['BRKT_API_TOKEN'] = token

    regions = map(lambda x: x.name, boto.ec2.regions())
    regions.sort()
    region = InteractiveSelectionMenu('Region', regions).run()

    def run_get_ami_lib():
        conn = boto.ec2.connect_to_region(region)
        images = conn.get_all_images(owners=['self'])
        return InteractiveSelectionNameKeyMenu('AMI',
                                               map(lambda x:
                                                   (x.name if x.name is not None and x.name != '' else x.id, x.id),
                                                   images)).run(has_back=True)

    def run_get_ubuntu_ami():
        amis = filter(lambda x: x[0] == region and x[4] == 'hvm:ebs-ssd', get_ubuntu_amis())
        amis.sort(key=lambda x: x[2])
        return InteractiveSelectionNameKeyMenu('Ubuntu AMI',
                                               map(lambda x: ('Ubuntu ' + x[2], get_ubuntu_ami_id_from_row(x)),
                                                   amis)).run(has_back=True)

    def run_get_custom_ami():
        return InteractiveTextField('Enter Custom AMI').run(has_back=True)

    ami = InteractiveSuperMenu('AMI', [
        ('Select AMI from Library Owned by me', run_get_ami_lib),
        ('Select an Ubuntu AMI', run_get_ubuntu_ami),
        ('Input a Custom AMI', run_get_custom_ami),
    ]).run()

    values.ami = ami
    values.region = region

    return values

