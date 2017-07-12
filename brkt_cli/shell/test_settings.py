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

from brkt_cli.shell.inner_commands import InnerCommandError
from brkt_cli.shell.settings import Setting, bool_parse_value, bool_validate_change, setting_inner_command, \
    complete_setting_inner_command
from brkt_cli.shell.test_utils import make_app, trap_print_output


class TestSettings(unittest.TestCase):
    def test_set_value(self):
        self.test_set_value_changed = False

        def on_changed(val):
            self.test_set_value_changed = True
        setting = Setting('test', True, str_acceptable_values=['true', 'false'], parse_value=bool_parse_value,
                          validate_change=bool_validate_change, on_changed=on_changed)

        self.assertEqual(setting.value, True)

        setting.value = False
        self.assertEqual(setting.value, False)
        self.assertTrue(self.test_set_value_changed)

        with self.assertRaises(InnerCommandError):
            setting.value = 'foobar'

    def test_set_value_with_str(self):
        setting = Setting('test', True, str_acceptable_values=['true', 'false'], parse_value=bool_parse_value)

        setting.set_value_with_str('false')
        self.assertEqual(setting.value, False)

        with self.assertRaises(InnerCommandError):
            setting.set_value_with_str('foobar')

    def test_setting_inner_command_func(self):
        app = make_app()
        app.settings = {
            'test': Setting('test', True, str_acceptable_values=['true', 'false'], parse_value=bool_parse_value),
        }

        with trap_print_output() as (out, err):
            setting_inner_command.run_action('/setting test', app)
            self.assertTrue('test - True' in out.getvalue().strip())

        with self.assertRaises(InnerCommandError):
            setting_inner_command.run_action('/setting fake', app)

        setting_inner_command.run_action('/setting test false', app)
        self.assertEqual(app.settings['test'].value, False)

        with self.assertRaises(InnerCommandError):
            setting_inner_command.run_action('/setting test fake-val', app)

        with self.assertRaises(InnerCommandError):
            setting_inner_command.run_action('/setting fake fake-val', app)

    def test_complete_setting_inner_command(self):
        app = make_app()
        app.settings = {
            'test': Setting('test', True, str_acceptable_values=['true', 'false'], parse_value=bool_parse_value),
            'anything': Setting('anything', 'hello'),
        }

        ret = complete_setting_inner_command(0, app, [], Document(u'/setting '))
        ret.sort()
        self.assertListEqual(ret, ['anything', 'test'])

        ret = complete_setting_inner_command(1, app, ['test'], Document(u'/setting test '))
        ret.sort()
        self.assertListEqual(ret, ['false', 'true'])

        ret = complete_setting_inner_command(1, app, ['anything'], Document(u'/setting anything '))
        ret.sort()
        self.assertListEqual(ret, [])

        ret = complete_setting_inner_command(1, app, ['fake'], Document(u'/setting fake '))
        ret.sort()
        self.assertListEqual(ret, [])

if __name__ == '__main__':
    unittest.main()
