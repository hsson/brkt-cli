# Copyright 2017 Bracket Computing, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
# https://github.com/brkt/brkt-cli/blob/master/LICENSE
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and
# limitations under the License.
import os
import boto.ec2

from brkt_cli.aws.encrypt_ami import get_ubuntu_amis, get_ubuntu_ami_id_from_row
from brkt_cli.interactive_mode import InteractiveTextField, InteractivePasswordField, \
    InteractiveSelectionNameValueMenu, InteractiveSuperMenu, InteractiveYNField, InteractiveMultiKeyValueTextField, \
    InteractiveSkipTextField
from brkt_cli.yeti import YetiService


def run_interactive_encrypt_ami(values, parsed_config):
    """
    Runs the interactive encrypt ami mode
    :param values: the parsed values
    :param parsed_config: the parsed config
    :return: new values
    """
    if 'BRKT_API_TOKEN' not in os.environ:  # If missing yeti API token, get it
        email = InteractiveTextField('Enter Email').run()
        password = InteractivePasswordField('Enter Password').run()

        _, env = parsed_config.get_current_env()
        root_url = 'https://%s:%d' % (
            env.public_api_host, env.public_api_port)
        y = YetiService(root_url)

        token = y.auth(email, password)
        os.environ['BRKT_API_TOKEN'] = token

    regions = map(lambda x: (x.name, x.name), boto.ec2.regions())  # Ask which region
    regions.sort()
    config_region = parsed_config.get_option('aws.region')
    region_ids = [x[0] for x in regions]
    if config_region is not None and config_region in region_ids:
        idx = region_ids.index(config_region)
        regions[idx] = ('%s ** Default' % regions[idx][1], regions[idx][1])

    region = InteractiveSelectionNameValueMenu('Region', regions).run()

    def run_get_ami_lib():  # Get all AMIs in library
        conn = boto.ec2.connect_to_region(region)
        images = conn.get_all_images(owners=['self'])
        return InteractiveSelectionNameValueMenu('AMI',
                                               map(lambda x:
                                                   (x.name if x.name is not None and x.name != '' else x.id, x.id),
                                                   images)).run(has_back=True)

    def run_get_ubuntu_ami():  # Get all working Ubuntu AMIs
        amis = filter(lambda x: x[0] == region and x[4] == 'hvm:ebs-ssd', get_ubuntu_amis())
        amis.sort(key=lambda x: x[2])
        return InteractiveSelectionNameValueMenu('Ubuntu AMI',
                                               map(lambda x: ('Ubuntu ' + x[2], get_ubuntu_ami_id_from_row(x)),
                                                   amis)).run(has_back=True)

    def run_get_centos_ami():  # Get all working CentOS AMIs
        conn = boto.ec2.connect_to_region(region)
        centos_6_images = conn.get_all_images(filters={'product-code': '6x5jmcajty9edm3f211pqjfn2'})
        centos_7_images = conn.get_all_images(filters={'product-code': 'aw0evgkw8e5c1q413zgy5pjce'})
        amis = map(lambda x: (x.name if x.name is not None and x.name != '' else x.id, x.id),
                   centos_6_images+centos_7_images)
        amis.sort(key=lambda x: x[0])
        return InteractiveSelectionNameValueMenu('CentOS AMI', amis).run(has_back=True)

    def run_get_custom_ami():  # Write in a custom AMI
        return InteractiveTextField('Enter Custom AMI').run(has_back=True)

    ami = InteractiveSuperMenu('AMI', [
        ('Select an AMI from Library Owned by Me', run_get_ami_lib),
        ('Select an Ubuntu AMI', run_get_ubuntu_ami),
        ('Select a CentOS AMI', run_get_centos_ami),
        ('Input a Custom AMI', run_get_custom_ami),
    ]).run()

    raw_brkt_tags = InteractiveMultiKeyValueTextField('Brkt Tags', 'Name', 'Value').run()
    brkt_tags = map(lambda (k, v): k + '=' + v, raw_brkt_tags)

    encrypted_ami_name = InteractiveSkipTextField('Encrypted AMI Name').run()

    if InteractiveYNField('Run Command', question_mark=True).run() is not True:
        return 0

    # Set the values
    values.ami = ami
    values.region = region
    values.brkt_tags = brkt_tags
    values.encrypted_ami_name = encrypted_ami_name

    return values

