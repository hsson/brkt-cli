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
import argparse
import getpass
import logging
import sys

from brkt_cli import argutil, ValidationError, util
from brkt_cli import yeti
from brkt_cli.subcommand import Subcommand
from brkt_cli.yeti import YetiError, YetiService

log = logging.getLogger(__name__)


SUBCOMMAND_NAME = 'auth'


class AuthSubcommand(Subcommand):

    def __init__(self):
        self.cfg = None

    def name(self):
        return SUBCOMMAND_NAME

    def register(self, subparsers, parsed_config):
        self.cfg = parsed_config

        parser = subparsers.add_parser(
            self.name(),
            description=(
                'Authenticate with the Bracket service. On success, print the API token (JSON\n'  # noqa
                'Web Token) that is used for making calls to Bracket REST API endpoints. You \n'  # noqa
                'must set the BRKT_API_TOKEN environment variable to this value, to allow other\n'  # noqa
                'brkt-cli commands to communicate with the Bracket service:\n'
                '\n'
                '$ export BRKT_API_TOKEN=$(brkt auth)'
            ),
            help='Authenticate with the Bracket service',
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        parser.add_argument(
            '--email',
            metavar='ADDRESS',
            help='If not specified, show a prompt.'
        )
        argutil.add_exp(parser)
        argutil.add_out(parser)
        parser.add_argument(
            '--password',
            help='If not specified, show a prompt.'
        )
        argutil.add_public_api_ca_cert(parser, parsed_config)
        argutil.add_root_url(parser, parsed_config)

    def run(self, values):
        try:
            if not yeti.is_yeti(
                values.root_url,
                root_cert_path=values.public_api_ca_cert
            ):
                raise ValidationError(
                    values.root_url +
                    ' is not the Bracket service'
                )
        except IOError as e:
            log.debug('', exc_info=1)
            msg = 'Unable to reach the Bracket service'
            if e.message:
                msg = '%s: %s' % (msg, e.message)
            raise ValidationError(msg)

        email = values.email
        if not email:
            # Write to stderr, so that the user doesn't see the prompt
            # in the output file when redirecting stdout.
            sys.stderr.write('Email: ')
            email = raw_input()
        password = values.password or getpass.getpass('Password: ')
        y = YetiService(
            values.root_url,
            root_cert_path=values.public_api_ca_cert
        )
        try:
            token = y.auth(email, password)
        except YetiError as e:
            if e.http_status == 401:
                raise ValidationError(
                    'Invalid email or password for %s' % values.root_url)
            raise ValidationError(e.message)

        if values.exp:
            dt = util.parse_duration(values.exp)
            token = y.create_api_token(expiry=dt)

        util.write_to_file_or_stdout(token, path=values.out)

        return 0


def get_subcommands():
    return [AuthSubcommand()]
