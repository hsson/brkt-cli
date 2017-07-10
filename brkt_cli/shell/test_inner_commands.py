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

from brkt_cli.shell import App
from brkt_cli.shell.inner_commands import exit_inner_command_func, inner_command_completer_static, InnerCommand, \
    InnerCommandError
from brkt_cli.shell.test_app import generate_app


class TestInnerCommand(unittest.TestCase):
    def test_run_action(self):
        app = generate_app()
        def action(params, app):
            return params, app

        cmd = InnerCommand('test', 'a test', '/test', action)
        ret_params, ret_app = cmd.run_action('/test', app)
        self.assertEqual(ret_app, app)
        self.assertIsNotNone(ret_params)
        self.assertEqual(ret_params.group(0), '')
        with self.assertRaises(IndexError):
            ret_params.group(1)

        cmd = InnerCommand('test', 'a test', 'test', action)
        with self.assertRaises(InnerCommandError):
            cmd.run_action('/test unwanted', app)

        cmd = InnerCommand('test', 'a test', 'test REQUIRED TEXT', action, param_regex=r'^(.+)$')
        ret_params, ret_app = cmd.run_action('/test foobar', app)
        self.assertEqual(ret_app, app)
        self.assertIsNotNone(ret_params)
        self.assertEqual(ret_params.group(0), 'foobar')
        self.assertEqual(ret_params.group(1), 'foobar')

        cmd = InnerCommand('test', 'a test', 'test REQUIRED TEXT', action, param_regex=r'^(.+)$')
        with self.assertRaises(InnerCommandError):
            cmd.run_action('/test', app)

        cmd = InnerCommand('test', 'a test', 'test REQUIRED TEXT', action, param_regex=r'^(.+)$')
        ret_params, ret_app = cmd.run_action('/test foo bar', app)
        self.assertEqual(ret_app, app)
        self.assertIsNotNone(ret_params)
        self.assertEqual(ret_params.group(0), 'foo bar')
        self.assertEqual(ret_params.group(1), 'foo bar')

        cmd = InnerCommand('test', 'a test', 'test REQUIRED REQUIRED', action, param_regex=r'^([^ ]+) (.+)$')
        ret_params, ret_app = cmd.run_action('/test foo bar', app)
        self.assertEqual(ret_app, app)
        self.assertIsNotNone(ret_params)
        self.assertEqual(ret_params.group(0), 'foo bar')
        self.assertEqual(ret_params.group(1), 'foo')
        self.assertEqual(ret_params.group(2), 'bar')

        cmd = InnerCommand('test', 'a test', 'test REQUIRED REQUIRED', action, param_regex=r'^([^ ]+) (.+)$')
        with self.assertRaises(InnerCommandError):
            cmd.run_action('/test foo', app)

        cmd = InnerCommand('test', 'a test', 'test REQUIRED [optional]', action, param_regex=r'^([^ ]+)(?: (.+))?$')
        ret_params, ret_app = cmd.run_action('/test foo bar', app)
        self.assertEqual(ret_app, app)
        self.assertIsNotNone(ret_params)
        self.assertEqual(ret_params.group(0), 'foo bar')
        self.assertEqual(ret_params.group(1), 'foo')
        self.assertEqual(ret_params.group(2), 'bar')

        cmd = InnerCommand('test', 'a test', 'test REQUIRED [optional]', action, param_regex=r'^([^ ]+)(?: (.+))?$')
        ret_params, ret_app = cmd.run_action('/test foo', app)
        self.assertEqual(ret_app, app)
        self.assertIsNotNone(ret_params)
        self.assertEqual(ret_params.group(0), 'foo')
        self.assertEqual(ret_params.group(1), 'foo')
        self.assertIsNone(ret_params.group(2))

    def test_inner_command_error(self):
        self.assertEqual(InnerCommandError('Unknown error').format_error(), 'Error: Unknown error')
        self.assertEqual(InnerCommandError('').format_error(), 'Error: ')
        self.assertEqual(InnerCommandError.format(Exception('foo bar').message), 'Error: foo bar')


    def test_inner_command_completer_static(self):
        app = generate_app()

        res_func = inner_command_completer_static()
        res = res_func(0, app, [], Document())
        self.assertListEqual(res, [])

        res_func = inner_command_completer_static()
        res = res_func(100, app, [], Document())
        self.assertListEqual(res, [])

        res_func = inner_command_completer_static([['foo','bar']])
        res = res_func(0, app, [], Document())
        self.assertListEqual(res, ['foo', 'bar'])

        res_func = inner_command_completer_static([['foo', 'bar'], []])
        res = res_func(1, app, [], Document())
        self.assertListEqual(res, [])

        res_func = inner_command_completer_static([['foo', 'bar']])
        res = res_func(1, app, [], Document())
        self.assertListEqual(res, [])

        res_func = inner_command_completer_static([['foo', 'bar'], ['baz']])
        res = res_func(1, app, [], Document())
        self.assertListEqual(res, ['baz'])
    def test_exit_inner_command_func(self):
        res = exit_inner_command_func([], generate_app())
        self.assertEqual(res, App.MachineCommands.Exit)


if __name__ == '__main__':
    unittest.main()
