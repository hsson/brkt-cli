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
from StringIO import StringIO
from contextlib import contextmanager

import sys

from brkt_cli.shell import traverse_tree, App, ShellCompleter
from brkt_cli.shell.inner_commands import InnerCommand


@contextmanager
def trap_print_output():
    out, err = StringIO(), StringIO()
    std_out, std_err = sys.stdout, sys.stderr
    try:
        sys.stdout, sys.stderr = out, err
        yield sys.stdout, sys.stderr
    finally:
        sys.stdout, sys.stderr = std_out, std_err


def make_top_cmd_subparsers():
    top_cmd_parser = argparse.ArgumentParser(
        description='testing command',
    )
    subparsers = top_cmd_parser.add_subparsers()  # type: argparse._SubParsersAction

    subparsers.add_parser(
        'super_shallow',
        description='has no subcommands and no arguments',
    )
    shallow_cmd_parser = subparsers.add_parser(
        'shallow',
        description='has no subcommands but all arguments',
    )
    deep_cmd_parser = subparsers.add_parser(
        'deep',
        description='has subcommands',
    )
    deep_cmd_subparser = deep_cmd_parser.add_subparsers()
    semi_shallow_cmd_parser = deep_cmd_subparser.add_parser(
        'semi_shallow',
        description='has no subcommands and one arguments',
    )
    semi_shallow_cmd_parser.add_argument(
        '--optional_store',
        dest='optional_store',
        help='Optional store'
    )

    shallow_cmd_parser.add_argument(
        'pos1',
        metavar='POSITIONAL_1',
        help='First positional')
    shallow_cmd_parser.add_argument(
        'pos2',
        metavar='POSITIONAL_2',
        help='Second positional')
    shallow_cmd_parser.add_argument(
        '--optional_true',
        dest='optional_true',
        action='store_true',
        help='Optional true')
    shallow_cmd_parser.add_argument(
        '--optional_false',
        dest='optional_false',
        action='store_false',
        help='Optional false')
    shallow_cmd_parser.add_argument(
        '--optional_store',
        dest='optional_store',
        help='Optional store')
    shallow_cmd_parser.add_argument(
        '--optional_store_int',
        dest='optional_store_int',
        type=int,
        help='Optional store int')
    shallow_cmd_parser.add_argument(
        '--optional_store_hidden',
        dest='optional_store_hidden',
        help=argparse.SUPPRESS)
    shallow_cmd_parser.add_argument(
        '--optional_store_default',
        dest='optional_store_default',
        default='foobar',
        help='Optional store default')
    shallow_cmd_parser.add_argument(
        '--optional_store_choices',
        dest='optional_store_choices',
        choices=['hot', 'cold'],
        help='Optional store choices')
    shallow_cmd_parser.add_argument(
        '--optional_const',
        dest='optional_const',
        action='store_const',
        const='123abc',
        help='Optional store const')
    shallow_cmd_parser.add_argument(
        '--optional_append',
        dest='optional_append',
        action='append',
        help='Optional append')
    shallow_cmd_parser.add_argument(
        '--optional_append_const_a',
        dest='optional_append_const',
        action='append_const',
        const='a',
        help='Optional append const a')
    shallow_cmd_parser.add_argument(
        '--optional_append_const_b',
        dest='optional_append_const',
        action='append_const',
        const='b',
        help='Optional append const b')
    shallow_cmd_parser.add_argument(
        '--optional_count',
        dest='optional_count',
        action='count',
        help='Optional count')

    return subparsers


def make_top_cmd():
    return traverse_tree('test', make_top_cmd_subparsers(), None, '', '', None, '', None)


class TestAppClass(App):

    def make_cli_interface(self):
        pass


def make_app():
    top_cmd = make_top_cmd()
    app = TestAppClass(ShellCompleter(top_cmd), top_cmd)

    def inner_command_run(params, the_app):
        pass

    app.inner_commands = {
        u'/test': InnerCommand('test', 'tests with no arguments', 'test', inner_command_run),
        u'/test_arg': InnerCommand('test_arg', 'tests with an arguments', 'test ARG', inner_command_run,
                                   param_regex=r'^(.+)$'),
    }
    app.dummy = True
    return app
