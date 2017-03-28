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

from __future__ import print_function

import argparse
import importlib
import json
import logging
import os
import re
import sys
import tempfile
from operator import attrgetter

import sshpubkeys

from brkt_cli import brkt_jwt, util, version
from brkt_cli.config import CLIConfig, CONFIG_PATH
from brkt_cli.proxy import Proxy, generate_proxy_config, validate_proxy_config
from brkt_cli.util import validate_dns_name_ip_address
from brkt_cli.validation import ValidationError

# The list of modules that may be loaded.  Modules contain subcommands of
# the brkt command and CSP-specific code.
SUBCOMMAND_MODULE_PATHS = [
    'brkt_cli.auth',
    'brkt_cli.aws',
    'brkt_cli.brkt_jwt',
    'brkt_cli.config',
    'brkt_cli.esx',
    'brkt_cli.gcp',
    'brkt_cli.get_public_key',
    'brkt_cli.make_key',
    'brkt_cli.make_user_data'
]

log = logging.getLogger(__name__)


class BracketEnvironment(object):
    def __init__(self, api_host=None, api_port=443,
                 hsmproxy_host=None, hsmproxy_port=443,
                 network_host=None, network_port=443,
                 public_api_host=None, public_api_port=443):
        self.api_host = api_host
        self.api_port = api_port
        self.hsmproxy_host = hsmproxy_host
        self.hsmproxy_port = hsmproxy_port
        self.network_host = network_host
        self.network_port = network_port
        self.public_api_host = public_api_host
        self.public_api_port = public_api_port

    def __repr__(self):
        return (
            '<BracketEnvironment api={be.api_host}:{be.api_port} '
            'hsmproxy={be.hsmproxy_host}:{be.hsmproxy_port} '
            'network={be.network_host}:{be.network_port} '
            'public_api={be.public_api_host}:{be.public_api_port}>'
        ).format(be=self)


def validate_ntp_servers(ntp_servers):
    if ntp_servers is None:
        return
    for server in ntp_servers:
        if not validate_dns_name_ip_address(server):
            raise ValidationError(
                'Invalid ntp-server %s specified. '
                'Should be either a host name or an IPv4 address' % server)


def parse_tags(tag_strings):
    """ Parse the tags specified on the command line.

    :param: tag_strings a list of strings in KEY=VALUE format
    :return: the tags as a dictionary
    :raise: ValidationError if any of the tags are invalid
    """
    if not tag_strings:
        return {}

    tags = {}
    for s in tag_strings:
        key, value = util.parse_name_value(s)
        tags[key] = value

    return tags


def parse_brkt_env(brkt_env_string):
    """ Parse the --brkt-env value.  The value is in the following format:

    api_host:port,hsmproxy_host:port,network_host:port

    :return: a BracketEnvironment object
    :raise: ValidationError if brkt_env is malformed
    """
    error_msg = (
        '--brkt-env value must be in the following format: '
        '<api-host>:<api-port>,<hsm-proxy-host>:<hsm-proxy-port>,'
        '<network-host>:<network-port>'
    )
    endpoints = brkt_env_string.split(',')
    if len(endpoints) != 3:
        raise ValidationError(error_msg)

    be = BracketEnvironment()
    names = ('api', 'hsmproxy', 'network')
    for name, endpoint in zip(names, endpoints):
        try:
            host, port = util.parse_endpoint(endpoint)
            if not port:
                raise ValidationError(error_msg)
            setattr(be, name + '_host', host)
            setattr(be, name + '_port', port)
            if name == 'api':
                # set public api host based on the same prefix assumption
                # service-domain makes. Hopefully we'll remove brkt-env
                # soon and we can get rid of it
                be.public_api_host = be.api_host.replace('yetiapi', 'api')
                be.public_api_port = be.api_port
        except ValueError:
            raise ValidationError(error_msg)

    return be


def brkt_env_from_domain(domain):
    """ Return a BracketEnvironment object based on the given domain
    (e.g. stage.mgmt.brkt.com).
    """
    return BracketEnvironment(
        api_host='yetiapi.' + domain,
        hsmproxy_host='hsmproxy.' + domain,
        network_host='network.' + domain,
        public_api_host='api.' + domain
    )


def get_prod_brkt_env():
    """ Return a BracketEnvironment object that represents the production
    service endpoints.
    """
    return brkt_env_from_domain('mgmt.brkt.com')


def brkt_env_from_values(values):
    """ Return a BracketEnvironment object based on options specified
    on the command line.  If the environment was not specified with
    --service-domain or --brkt-env, return None.
    """
    if values.service_domain:
        return brkt_env_from_domain(values.service_domain)
    elif values.brkt_env:
        return parse_brkt_env(values.brkt_env)
    else:
        return None


def _parse_proxies(*proxy_host_ports):
    """ Parse proxies specified on the command line.

    :param proxy_host_ports: a list of strings in "host:port" format
    :return: a list of Proxy objects
    :raise: ValidationError if any of the items are malformed
    """
    proxies = []
    for s in proxy_host_ports:
        m = re.match(r'([^:]+):(\d+)$', s)
        if not m:
            raise ValidationError('%s is not in host:port format' % s)
        host = m.group(1)
        port = int(m.group(2))
        if not util.validate_dns_name_ip_address(host):
            raise ValidationError('%s is not a valid hostname' % host)
        proxy = Proxy(host, port)
        proxies.append(proxy)

    return proxies


def get_proxy_config(values):
    """ Read proxy config specified by either the --proxy or
    --proxy-config-file option.

    :return the contents of the proxy.yaml file, or None if not specified
    :raise ValidationError if the file cannot be read or is malformed
    """
    proxy_config = None
    if values.proxy_config_file:
        path = values.proxy_config_file
        log.debug('Loading proxy config from %s', path)
        try:
            with open(path) as f:
                proxy_config = f.read()
        except IOError as e:
            log.debug('Unable to read %s: %s', path, e)
            raise ValidationError('Unable to read %s' % path)
        validate_proxy_config(proxy_config)
    elif values.proxies:
        proxies = _parse_proxies(*values.proxies)
        proxy_config = generate_proxy_config(*proxies)
        log.debug('Using proxy configuration:\n%s', proxy_config)

    return proxy_config


def _base64_decode_json(base64_string):
    """ Decode the given base64 string, and return the parsed JSON as a
    dictionary.
    :raise ValidationError if either the base64 or JSON is malformed
    """
    try:
        json_string = util.urlsafe_b64decode(base64_string)
        return json.loads(json_string)
    except (TypeError, ValueError) as e:
        raise ValidationError(
            'Unable to decode %s as JSON: %s' % (base64_string, e)
        )


def validate_jwt(jwt):
    """ Check the incoming JWT and verify that it has all of the fields that
    we require.

    :param jwt a JSON Web Token as a string
    :return the JWT string
    :raise ValidationError if validation fails
    """
    if not jwt:
        return None

    # Validate header.
    header = brkt_jwt.get_header(jwt)
    expected_fields = ['typ', 'alg', 'kid']
    missing_fields = [f for f in expected_fields if f not in header]
    if missing_fields:
        raise ValidationError(
            'Missing fields in token header: %s.  Use the %s command '
            'to generate a valid token.' % (
                ','.join(missing_fields),
                brkt_jwt.SUBCOMMAND_NAME
            )
        )

    # Validate payload.
    payload = brkt_jwt.get_payload(jwt)
    if not payload.get('jti'):
        raise ValidationError(
            'Token payload does not contain the jti field.  Use the %s '
            'command to generate a valid token.' %
            brkt_jwt.SUBCOMMAND_NAME
        )

    return jwt


def validate_ssh_pub_key(key):
    ssh = sshpubkeys.SSHKey(key)
    try:
        if ssh.bits > 0:
            return True
        else:
            raise ValidationError(
                'Invalid public key: %s' % key
                )
    except Exception as e:
        raise ValidationError(
            'Unable to validate public key: %s' % e.message
            )


def add_brkt_env_to_brkt_config(brkt_env, brkt_config):
    """ Add BracketEnvironment values to the config dictionary
    that will be passed to the metavisor via userdata.

    :param brkt_env a BracketEnvironment object
    :param brkt_config a dictionary that contains configuration data
    """
    if brkt_env:
        api_host_port = '%s:%d' % (brkt_env.api_host, brkt_env.api_port)
        hsmproxy_host_port = '%s:%d' % (
            brkt_env.hsmproxy_host, brkt_env.hsmproxy_port)
        network_host_port = '%s:%d' % (
            brkt_env.network_host, brkt_env.network_port)
        brkt_config['api_host'] = api_host_port
        brkt_config['hsmproxy_host'] = hsmproxy_host_port
        brkt_config['network_host'] = network_host_port


class SortingHelpFormatter(argparse.HelpFormatter):
    def add_arguments(self, actions):
        actions = sorted(actions, key=attrgetter('option_strings'))
        super(SortingHelpFormatter, self).add_arguments(actions)

    def _get_help_string(self, action):
        """ Append the default value to the argument description.  This code
        is inspired by argparse.ArgumentDefaultsHelpFormatter, with the
        following differences:

        1. Don't print "default: None".  The behavior for options that don't
        have defaults is already clear from the usage output.

        2. Don't print the default for boolean options.  Behavior for boolean
        options is also already clear.  Printing a default for 'store_false'
        results in confusing usage output for options with negative names,
        like --no-validate.
        """
        help = action.help

        if action.default is None or type(action.default) == bool:
            return help

        if '%(default)' not in action.help:
            if action.default is not argparse.SUPPRESS:
                defaulting_nargs = [argparse.OPTIONAL, argparse.ZERO_OR_MORE]
                if action.option_strings or action.nargs in defaulting_nargs:
                    help += ' (default: %(default)s)'
        return help


def is_verbose(values, subcommand):
    if subcommand.verbose(values):
        print(
            '%s --verbose is deprecated. Please use brkt --verbose '
            'instead.' % subcommand.name(), file=sys.stderr)

    return values.verbose or subcommand.verbose(values)


def main():
    parser = argparse.ArgumentParser(
        description='Command-line interface to the Bracket Computing service.',
        formatter_class=SortingHelpFormatter
    )
    parser.add_argument(
        '-v',
        '--verbose',
        dest='verbose',
        action='store_true',
        help='Print status information to the console'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='brkt-cli version %s' % version.VERSION
    )
    parser.add_argument(
        '--no-check-version',
        dest='check_version',
        action='store_false',
        default=True,
        help="Don't check whether this version of brkt-cli is supported"
    )

    # Batch up messages that are logged while loading modules.  We don't know
    # whether to log them yet, since we haven't parsed arguments.  argparse
    # seems to get confused when you parse arguments twice.
    subcommand_load_messages = []

    config = CLIConfig()

    # Add config options that span multiple commands
    config.register_option(
        'token',
        'The default token to use when encrypting, updating, or launching'
        ' images')

    # Dynamically load subcommands from modules.
    subcommands = []
    for module_path in SUBCOMMAND_MODULE_PATHS:
        try:
            module = importlib.import_module(module_path)
            subcommands.extend(module.get_subcommands())
        except ImportError as e:
            # Parse the module name from the module path.
            m = re.match(r'(.*\.)?(.+)', module_path)
            module_name = None
            if m:
                module_name = m.group(2)

            if module_name and \
                    e.message == ('No module named ' + module_name):
                # The subcommand module is not installed.
                subcommand_load_messages.append(
                    'Skipping module %s: %s' % (module_path, e))
            else:
                # There is an import problem inside the subcommand module.
                raise

    # Use metavar to hide any subcommands that we don't want to expose.
    exposed_subcommand_names = [s.name() for s in subcommands if s.exposed()]
    metavar = '{%s}' % ','.join(sorted(exposed_subcommand_names))

    subparsers = parser.add_subparsers(
        dest='subparser_name',
        metavar=metavar
    )

    # Setup expected config sections/options before we attempt to read from
    # disk
    for s in subcommands:
        s.setup_config(config)

    # Load defaults from disk. Subcommands are expected to register config
    # sections at import time so that correct default values can be displayed
    # to users if they request help.
    subcommand_load_messages.append(
        'Reading config from %s' % (CONFIG_PATH,))
    config.read()

    # Add subcommands to the parser.
    for s in subcommands:
        subcommand_load_messages.append(
            'Registering subcommand %s' % s.name())
        s.register(subparsers, config)

    argv = sys.argv[1:]
    values = parser.parse_args(argv)

    # Find the matching subcommand.
    subcommand = None
    for s in subcommands:
        if s.name() == values.subparser_name:
            subcommand = s
            break
    if not subcommand:
        raise Exception('Could not find subcommand ' + values.subparser_name)

    # Initialize logging.  Verbose logging can be specified for either
    # the top-level "brkt" command or one of the subcommands.  We support
    # both because users got confused when "brkt encrypt-ami -v" didn't work.
    log_level = logging.INFO
    verbose = is_verbose(values, subcommand)
    subcommand.init_logging(verbose)
    if verbose:
        log_level = logging.DEBUG

    # Prefix log messages with a compact timestamp, so that the user
    # knows how long each operation took.
    fmt = '%(asctime)s %(message)s'
    datefmt = '%H:%M:%S'

    # Set the root log level to DEBUG.  This passes all log messages to all
    # handlers.  We then filter by log level in each handler.
    logging.root.setLevel(logging.DEBUG)

    # Log to stderr at the level specified by the user.
    stderr_handler = logging.StreamHandler()
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
    stderr_handler.setFormatter(formatter)
    stderr_handler.setLevel(log_level)
    logging.root.addHandler(stderr_handler)

    # Optionally log to a temp file at debug level.  If the command succeeds,
    # we delete this file.  If the command fails, we keep it around so that
    # the user can get more details.
    debug_handler = None
    debug_log_file = None
    if subcommand.debug_log_to_temp_file(values) and log_level != logging.DEBUG:
        debug_log_file = tempfile.NamedTemporaryFile(
            delete=False, prefix='brkt_cli')
        debug_handler = logging.FileHandler(debug_log_file.name)
        formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
        debug_handler.setFormatter(formatter)
        debug_handler.setLevel(logging.DEBUG)
        logging.root.addHandler(debug_handler)

    # Turn off unnecessary logging from known libraries.
    logging.getLogger('requests').setLevel(logging.WARNING)

    # Write messages that were logged before logging was initialized.
    for msg in subcommand_load_messages:
        log.debug(msg)

    # Check if the version is supported.
    dt = version.get_last_version_check_time(config)
    if dt:
        log.debug('Last version check: %s', dt.isoformat())
    if values.check_version and version.is_version_check_needed(config):
        if not version.check_version():
            return 1
        version.set_last_version_check_time(config)
        config.save_config()

    result = 1

    # Run the subcommand.
    allow_debug_log = True
    try:
        result = subcommand.run(values)
        if not isinstance(result, (int, long)):
            raise Exception(
                '%s did not return an integer result' % subcommand.name())
        log.debug('%s returned %d', subcommand.name(), result)
    except ValidationError as e:
        allow_debug_log = False
        print(e, file=sys.stderr)
    except util.BracketError as e:
        log.debug('', exc_info=1)
        log.error(e.message)
    except KeyboardInterrupt:
        allow_debug_log = False
        log.debug('', exc_info=1)
        log.error('Interrupted by user')
    finally:
        if debug_handler:
            logging.root.removeHandler(debug_handler)
            debug_handler.close()
            debug_log_file.close()

            if result != 0 and allow_debug_log:
                log.info('Debug log is available at %s', debug_log_file.name)
            else:
                os.remove(debug_log_file.name)
    return result


if __name__ == '__main__':
    exit_status = main()
    exit(exit_status)
