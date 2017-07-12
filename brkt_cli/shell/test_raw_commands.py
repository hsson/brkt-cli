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
import unittest

from brkt_cli.shell import traverse_tree
from brkt_cli.shell.raw_commands import CommandPromptToolkit
from brkt_cli.shell.test_utils import make_top_cmd_subparsers, make_top_cmd


class TestRawCommands(unittest.TestCase):
    def test_traverse_tree(self):
        ret = traverse_tree('test', make_top_cmd_subparsers(), None, '', '', None, '', None)
        ret_arr = ret.get_all_paths()
        ret_arr.sort()
        self.assertListEqual(ret_arr, ['test', 'test.deep', 'test.deep.semi_shallow', 'test.shallow',
                                       'test.super_shallow'])
        sc = ret.get_subcommand_from_path('test.super_shallow')
        self.assertEqual(sc.name, 'super_shallow')
        self.assertEqual(sc.description, 'has no subcommands and no arguments')
        args = map(lambda x: x.get_name(), sc.optional_arguments+sc.positionals)
        args.sort()
        self.assertListEqual(args, ['help'])

        sc = ret.get_subcommand_from_path('test.shallow')
        self.assertEqual(sc.name, 'shallow')
        self.assertEqual(sc.description, 'has no subcommands but all arguments')
        args = map(lambda x: x.get_name(), sc.optional_arguments+sc.positionals)
        args.sort()
        self.assertListEqual(args, ['POSITIONAL_1', 'POSITIONAL_2', 'help', 'optional_append',
                                    'optional_append_const_a', 'optional_append_const_b', 'optional_const',
                                    'optional_count', 'optional_false', 'optional_store', 'optional_store_choices',
                                    'optional_store_default', 'optional_store_hidden', 'optional_store_int',
                                    'optional_true'])

        sc = ret.get_subcommand_from_path('test.deep')
        self.assertEqual(sc.name, 'deep')
        self.assertEqual(sc.description, 'has subcommands')
        args = map(lambda x: x.get_name(), sc.optional_arguments + sc.positionals)
        args.sort()
        self.assertListEqual(args, ['help'])

        sc = ret.get_subcommand_from_path('test.deep.semi_shallow')
        self.assertEqual(sc.name, 'semi_shallow')
        self.assertEqual(sc.description, 'has no subcommands and one arguments')
        args = map(lambda x: x.get_name(), sc.optional_arguments + sc.positionals)
        args.sort()
        self.assertListEqual(args, ['help', 'optional_store'])

    def test_list_subcommand_names(self):
        cmd = make_top_cmd()
        ret = cmd.list_subcommand_names()
        ret.sort()
        self.assertListEqual(ret, ['deep', 'shallow', 'super_shallow'])

        cmd = CommandPromptToolkit('foo', 'has no subcommands', 'foo', 'foo', None)
        ret = cmd.list_subcommand_names()
        ret.sort()
        self.assertListEqual(ret, [])

    def test_get_all_paths(self):
        cmd = make_top_cmd()
        ret = cmd.get_all_paths()
        ret.sort()
        self.assertListEqual(ret, ['test', 'test.deep', 'test.deep.semi_shallow', 'test.shallow', 'test.super_shallow'])

        cmd = CommandPromptToolkit('foo', 'has no subcommands', 'foo', 'foo', None)
        ret = cmd.get_all_paths()
        ret.sort()
        self.assertListEqual(ret, ['foo'])

    def test_get_argument_from_full_path(self):
        cmd = make_top_cmd()
        ret = cmd.get_argument_from_full_path('test.deep.semi_shallow.optional_store')
        self.assertEqual(ret.tag, '--optional_store')

        ret = cmd.get_argument_from_full_path('test.deep.fake.fake-arg')
        self.assertIsNone(ret)

        ret = cmd.get_argument_from_full_path('test.deep.semi_shallow.fake-arg')
        self.assertIsNone(ret)

    def test_has_subcommands(self):
        cmd = make_top_cmd()
        self.assertTrue(cmd.has_subcommands())
        self.assertFalse(cmd.get_subcommand_from_path('test.deep.semi_shallow').has_subcommands())
        self.assertFalse(CommandPromptToolkit('foo', 'has no subcommands', 'foo', 'foo', None).has_subcommands())


if __name__ == '__main__':
    unittest.main()
