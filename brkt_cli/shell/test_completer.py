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

from prompt_toolkit.document import Document

from brkt_cli.shell.test_utils import make_app


class TestCompleter(unittest.TestCase):
    def test_get_completions_list(self):
        app = make_app()

        # Test nothing in prompt. Should return commands.
        doc = Document(u'')
        ret = app.completer.get_completions_list(doc)
        self.assertListEqual(ret, ['deep', 'shallow', 'super_shallow'])

        # Test a deep command in prompt. Should return subcommand.
        doc = Document(u'deep')
        ret = app.completer.get_completions_list(doc)
        self.assertListEqual(ret, ['semi_shallow'])

        # Test a deep command and subcommand in prompt. Should return options.
        doc = Document(u'deep semi_shallow')
        ret = app.completer.get_completions_list(doc)
        self.assertListEqual(ret, ['--help', '--optional_store'])

        # Test a deep command and subcommand and help argument in prompt. Should return no options as help stops
        # further options.
        doc = Document(u'deep semi_shallow --help')
        ret = app.completer.get_completions_list(doc)
        self.assertListEqual(ret, [])

        # Test a deep command and subcommand and regular argument in prompt. Should return one option as the
        # --optional_store option cannot be specified again.
        doc = Document(u'deep semi_shallow --optional_store')
        ret = app.completer.get_completions_list(doc)
        self.assertListEqual(ret, ['--help'])

        # Test a command with no arguments. Should return --help.
        doc = Document(u'super_shallow')
        ret = app.completer.get_completions_list(doc)
        self.assertListEqual(ret, ['--help'])

        # Test a command with no arguments. Should return all.
        doc = Document(u'shallow')
        ret = app.completer.get_completions_list(doc)
        self.assertListEqual(ret, ['--help', '--optional_append', '--optional_append_const_a',
                                   '--optional_append_const_b', '--optional_const', '--optional_count',
                                   '--optional_false', '--optional_store', '--optional_store_choices',
                                   '--optional_store_default', '--optional_store_int', '--optional_true'])

        # Test a command with no arguments and dev mode enabled. Should return all plus the hidden argument.
        app.dev_mode = True
        doc = Document(u'shallow')
        ret = app.completer.get_completions_list(doc)
        self.assertListEqual(ret, ['--help', '--optional_append', '--optional_append_const_a',
                                   '--optional_append_const_b', '--optional_const', '--optional_count',
                                   '--optional_false', '--optional_store', '--optional_store_choices',
                                   '--optional_store_default', '--optional_store_hidden', '--optional_store_int',
                                   '--optional_true'])
        app.dev_mode = False

        # Test a command with help argument. Should no arguments as --help stops suggestions
        doc = Document(u'shallow --help')
        ret = app.completer.get_completions_list(doc)
        self.assertListEqual(ret, [])

        # Test a command with an argument being written
        doc = Document(u'shallow --optional_store ')
        ret = app.completer.get_completions_list(doc)
        self.assertListEqual(ret, [])

        # Test a command with an argument that has been entered. Should remove the argument from the list.
        doc = Document(u'shallow --optional_store foo ')
        ret = app.completer.get_completions_list(doc)
        self.assertListEqual(ret, ['--help', '--optional_append', '--optional_append_const_a',
                                   '--optional_append_const_b', '--optional_const', '--optional_count',
                                   '--optional_false', '--optional_store_choices',
                                   '--optional_store_default', '--optional_store_int', '--optional_true'])

        # Test a command with an argument being written
        doc = Document(u'shallow --optional_append ')
        ret = app.completer.get_completions_list(doc)
        self.assertListEqual(ret, [])

        # Test a command with an argument that has been entered. Should NOT remove the argument from the list.
        doc = Document(u'shallow --optional_append foo ')
        ret = app.completer.get_completions_list(doc)
        self.assertListEqual(ret, ['--help', '--optional_append', '--optional_append_const_a',
                                   '--optional_append_const_b', '--optional_const', '--optional_count',
                                   '--optional_false', '--optional_store', '--optional_store_choices',
                                   '--optional_store_default', '--optional_store_int', '--optional_true'])

        # Test a command with an argument being written. Should leave space for argument value and suggest
        # default choices.
        doc = Document(u'shallow --optional_store_choices ')
        ret = app.completer.get_completions_list(doc)
        self.assertListEqual(ret, ['cold', 'hot'])

        # Test a command with an argument being written. Should not leave space for argument value and should remove
        # the argument from the list.
        doc = Document(u'shallow --optional_const ')
        ret = app.completer.get_completions_list(doc)
        self.assertListEqual(ret, ['--help', '--optional_append', '--optional_append_const_a',
                                   '--optional_append_const_b', '--optional_count',
                                   '--optional_false', '--optional_store', '--optional_store_choices',
                                   '--optional_store_default', '--optional_store_int', '--optional_true'])

        # Test a command with an argument being written. Should not leave space for argument value and should remove
        # the argument from the list.
        doc = Document(u'shallow --optional_append_const_a ')
        ret = app.completer.get_completions_list(doc)
        self.assertListEqual(ret, ['--help', '--optional_append',
                                   '--optional_append_const_b', '--optional_const', '--optional_count',
                                   '--optional_false', '--optional_store', '--optional_store_choices',
                                   '--optional_store_default', '--optional_store_int', '--optional_true'])

        # Test a command with an argument being written. Should not leave space for argument value and should NOT
        # remove the argument from the list.
        doc = Document(u'shallow --optional_count ')
        ret = app.completer.get_completions_list(doc)
        self.assertListEqual(ret, ['--help', '--optional_append', '--optional_append_const_a',
                                   '--optional_append_const_b', '--optional_const', '--optional_count',
                                   '--optional_false', '--optional_store', '--optional_store_choices',
                                   '--optional_store_default', '--optional_store_int', '--optional_true'])

        # Test a command with an argument being written. Should not leave space for argument value and should remove
        # the argument from the list.
        doc = Document(u'shallow --optional_false')
        ret = app.completer.get_completions_list(doc)
        self.assertListEqual(ret, ['--help', '--optional_append', '--optional_append_const_a',
                                   '--optional_append_const_b', '--optional_const', '--optional_count',
                                   '--optional_store', '--optional_store_choices',
                                   '--optional_store_default', '--optional_store_int', '--optional_true'])

        # Test a command with an argument being written. Should not leave space for argument value and should remove
        # the argument from the list.
        doc = Document(u'shallow --optional_true')
        ret = app.completer.get_completions_list(doc)
        self.assertListEqual(ret, ['--help', '--optional_append', '--optional_append_const_a',
                                   '--optional_append_const_b', '--optional_const', '--optional_count',
                                   '--optional_false', '--optional_store', '--optional_store_choices',
                                   '--optional_store_default', '--optional_store_int'])

    def test_get_current_command(self):
        app = make_app()

        doc = Document(u'')
        ret = app.completer.get_current_command(doc)
        self.assertIsNone(ret)

        doc = Document(u'deep semi_shallow')
        ret = app.completer.get_current_command(doc)
        self.assertEqual(ret.path, 'test.deep.semi_shallow')

        doc = Document(u'super_shallow')
        ret = app.completer.get_current_command(doc)
        self.assertEqual(ret.path, 'test.super_shallow')

        doc = Document(u'shallow')
        ret = app.completer.get_current_command(doc)
        self.assertEqual(ret.path, 'test.shallow')

        doc = Document(u'shallow --optional_store foo --optional_const')
        ret = app.completer.get_current_command(doc)
        self.assertEqual(ret.path, 'test.shallow')

        doc = Document(u'deep fake')
        ret = app.completer.get_current_command(doc)
        self.assertEqual(ret.path, 'test.deep')

    def test_get_current_command_location(self):
        app = make_app()

        doc = Document(u'')
        ret_start, ret_end = app.completer.get_current_command_location(doc)
        self.assertEqual(ret_start, 0)
        self.assertEqual(ret_end, 0)

        doc = Document(u'deep semi_shallow')
        ret_start, ret_end = app.completer.get_current_command_location(doc)
        self.assertEqual(ret_start, 0)
        self.assertEqual(ret_end, 17)

        doc = Document(u'shallow')
        ret_start, ret_end = app.completer.get_current_command_location(doc)
        self.assertEqual(ret_start, 0)
        self.assertEqual(ret_end, 7)

        doc = Document(u'shallow --optional_store foo --optional_const')
        ret_start, ret_end = app.completer.get_current_command_location(doc)
        self.assertEqual(ret_start, 0)
        self.assertEqual(ret_end, 7)

        doc = Document(u'deep fake')
        ret_start, ret_end = app.completer.get_current_command_location(doc)
        self.assertEqual(ret_start, 0)
        self.assertEqual(ret_end, 4)

    def test_get_current_argument(self):
        app = make_app()

        doc = Document(u'')
        ret = app.completer.get_current_argument(doc)
        self.assertIsNone(ret)

        doc = Document(u'shallow')
        ret = app.completer.get_current_argument(doc)
        self.assertIsNone(ret)

        doc = Document(u'deep semi_shallow')
        ret = app.completer.get_current_argument(doc)
        self.assertIsNone(ret)

        doc = Document(u'deep semi_shallow --optional_store')
        ret = app.completer.get_current_argument(doc)
        self.assertEqual(ret.tag, '--optional_store')

        doc = Document(u'deep fake --optional_store')
        ret = app.completer.get_current_argument(doc)
        self.assertIsNone(ret)

        doc = Document(u'shallow --optional_store')
        ret = app.completer.get_current_argument(doc)
        self.assertEqual(ret.tag, '--optional_store')

        doc = Document(u'shallow --optional_store foo')
        ret = app.completer.get_current_argument(doc)
        self.assertEqual(ret.tag, '--optional_store')

        doc = Document(u'shallow --optional_store foo ')
        ret = app.completer.get_current_argument(doc)
        self.assertIsNone(ret)

        doc = Document(u'shallow --optional_store foo --optional_true')
        ret = app.completer.get_current_argument(doc)
        self.assertEqual(ret.tag, '--optional_true')


if __name__ == '__main__':
    unittest.main()
