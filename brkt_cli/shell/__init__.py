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
from __future__ import unicode_literals
import argparse
import logging

from brkt_cli.shell.app import App
from brkt_cli.shell.completer import ShellCompleter
from brkt_cli.shell.raw_commands import traverse_tree
from brkt_cli.subcommand import Subcommand

log = logging.getLogger(__name__)


SUBCOMMAND_NAME = 'shell'


class ShellSubcommand(Subcommand):

    def __init__(self):
        self.cfg = None

    def name(self):
        return SUBCOMMAND_NAME

    def set_subparsers(self, subparsers):
        self.subparsers = subparsers

    def register(self, subparsers, parsed_config):
        self.cfg = parsed_config

        parser = subparsers.add_parser(
            self.name(),
            description=(
                'Brkt CLI Shell'
            ),
            help='Brkt CLI Shell',
            formatter_class=argparse.RawDescriptionHelpFormatter
        )

        # Dummy will just pretend to run command but not actually run it. Used for development and testing.
        parser.add_argument(
            '--dummy',
            dest='dummy',
            action='store_true',
            default=False,
            help=argparse.SUPPRESS
        )

    def run(self, values):
        brkt_cmd = traverse_tree("brkt", self.subparsers, None, "", "", None)
        brkt_app = App(ShellCompleter(brkt_cmd))
        brkt_app.dummy = values.dummy
        brkt_app.run()

        return 0


def can_get_docs(app):
    return True


def get_subcommands():
    return [ShellSubcommand()]
