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
import getpass
import logging

import brkt_cli
from brkt_cli import ValidationError
from brkt_cli import argutil
from brkt_cli import util
from brkt_cli.subcommand import Subcommand
from brkt_cli.yeti import YetiService, YetiError

log = logging.getLogger(__name__)


SUBCOMMAND_NAME = 'auth'


class AuthSubcommand(Subcommand):

    def name(self):
        return SUBCOMMAND_NAME

    def register(self, subparsers, parsed_config):
        parser = subparsers.add_parser(
            self.name(),
            description=(
                'Authenticate with the Bracket service. On success, print '
                'the JSON Web Token that can be used to make calls '
                'to Bracket REST API endpoints.'
            ),
            # Hide this command while the feature is in development.
            # help='Authenticate with the Bracket service',
            formatter_class=brkt_cli.SortingHelpFormatter
        )
        parser.add_argument(
            '--email',
            metavar='ADDRESS',
            help='If not specified, show a prompt.'
        )
        parser.add_argument(
            '--password',
            help='If not specified, show a prompt.'
        )
        parser.add_argument(
            '--root-url',
            metavar='URL',
            default='https://api.mgmt.brkt.com',
            help='Bracket service root URL'
        )
        argutil.add_out(parser)

    def run(self, values):
        email = values.email or raw_input('Email: ')
        password = values.password or getpass.getpass('Password: ')
        y = YetiService(values.root_url)
        try:
            token = y.auth(email, password)
        except YetiError as e:
            raise ValidationError(e.message)
        util.write_to_file_or_stdout(token, path=values.out)

        return 0

    def exposed(self):
        return False


def get_subcommands():
    return [AuthSubcommand()]
