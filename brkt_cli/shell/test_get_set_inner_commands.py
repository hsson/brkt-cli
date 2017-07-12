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

from brkt_cli.shell.get_set_inner_commmands import set_inner_command, \
    complete_set_inner_command, get_inner_command, del_inner_command, complete_get_inner_command, \
    complete_del_inner_command
from brkt_cli.shell.inner_commands import InnerCommandError
from brkt_cli.shell.test_utils import trap_print_output, make_app


class TestGetSetInnerCommands(unittest.TestCase):
    def test_set_inner_command_func(self):
        app = make_app()

        def on_change_manual_arg(val):
            pass

        def on_delete_manual_arg():
            pass
        app.manual_args = {
            'app': {
                'manual_arg': (on_change_manual_arg, on_delete_manual_arg)
            }
        }

        set_inner_command.run_action('/set test.shallow.optional_store abc', app)
        self.assertEqual(app.set_args['test.shallow']['optional_store'], 'abc')

        set_inner_command.run_action('/set test.shallow.optional_store xyz', app)
        self.assertEqual(app.set_args['test.shallow']['optional_store'], 'xyz')

        set_inner_command.run_action('/set test.shallow.optional_store_int 64', app)
        self.assertEqual(app.set_args['test.shallow']['optional_store_int'], 64)

        with self.assertRaises(ValueError):
            set_inner_command.run_action('/set test.shallow.optional_store_int forty nine', app)

        set_inner_command.run_action('/set test.shallow.optional_const true', app)
        self.assertEqual(app.set_args['test.shallow']['optional_const'], True)
        set_inner_command.run_action('/set test.shallow.optional_const false', app)
        self.assertEqual(app.set_args['test.shallow']['optional_const'], False)

        with self.assertRaises(InnerCommandError):
            set_inner_command.run_action('/set test.shallow.optional_const bool', app)

        set_inner_command.run_action('/set test.shallow.optional_append hello, world', app)
        self.assertEqual(app.set_args['test.shallow']['optional_append'], ['hello', 'world'])

        set_inner_command.run_action('/set test.shallow.optional_append_const_a true', app)
        self.assertEqual(app.set_args['test.shallow']['optional_append_const_a'], True)

        set_inner_command.run_action('/set test.shallow.optional_count 4', app)
        self.assertEqual(app.set_args['test.shallow']['optional_count'], 4)

        with self.assertRaises(ValueError):
            set_inner_command.run_action('/set test.shallow.optional_count nine', app)

        set_inner_command.run_action('/set test.shallow.optional_true true', app)
        self.assertEqual(app.set_args['test.shallow']['optional_true'], True)
        set_inner_command.run_action('/set test.shallow.optional_false false', app)
        self.assertEqual(app.set_args['test.shallow']['optional_false'], False)

        set_inner_command.run_action('/set test.shallow.POSITIONAL_1 stem', app)
        self.assertEqual(app.set_args['test.shallow']['POSITIONAL_1'], 'stem')

        with self.assertRaises(InnerCommandError):
            set_inner_command.run_action('/set test.fake.fake-arg foobar', app)

        with self.assertRaises(InnerCommandError):
            set_inner_command.run_action('/set test.shallow.fake-arg foobar', app)

        set_inner_command.run_action('/set app.manual_arg floof', app)
        self.assertEqual(app.set_args['app']['manual_arg'], 'floof')

        with self.assertRaises(InnerCommandError):
            set_inner_command.run_action('/set app.fake foobar', app)

        with self.assertRaises(InnerCommandError):
            set_inner_command.run_action('/set test.shallow.optional_store_hidden phrase', app)

        app.dev_mode = True
        set_inner_command.run_action('/set test.shallow.optional_store_hidden phrase', app)
        self.assertEqual(app.set_args['test.shallow']['optional_store_hidden'], 'phrase')
        app.dev_mode = False

    def test_complete_set_inner_command(self):
        app = make_app()

        def on_change_manual_arg(val):
            pass

        def on_delete_manual_arg():
            pass
        app.manual_args = {
            'app': {
                'manual_arg': (on_change_manual_arg, on_delete_manual_arg)
            }
        }

        ret = complete_set_inner_command(0, app, [], Document(u'/set '))
        ret.sort()
        self.assertListEqual(ret, ['app.manual_arg', 'test.deep.semi_shallow.optional_store',
                                   'test.shallow.POSITIONAL_1', 'test.shallow.POSITIONAL_2',
                                   'test.shallow.optional_append', 'test.shallow.optional_append_const_a',
                                   'test.shallow.optional_append_const_b', 'test.shallow.optional_const',
                                   'test.shallow.optional_count', 'test.shallow.optional_false',
                                   'test.shallow.optional_store', 'test.shallow.optional_store_choices',
                                   'test.shallow.optional_store_default', 'test.shallow.optional_store_int',
                                   'test.shallow.optional_true'])

        app.dev_mode = True
        ret = complete_set_inner_command(0, app, [], Document(u'/set '))
        ret.sort()
        self.assertListEqual(ret, ['app.manual_arg', 'test.deep.semi_shallow.optional_store',
                                   'test.shallow.POSITIONAL_1', 'test.shallow.POSITIONAL_2',
                                   'test.shallow.optional_append', 'test.shallow.optional_append_const_a',
                                   'test.shallow.optional_append_const_b', 'test.shallow.optional_const',
                                   'test.shallow.optional_count', 'test.shallow.optional_false',
                                   'test.shallow.optional_store', 'test.shallow.optional_store_choices',
                                   'test.shallow.optional_store_default', 'test.shallow.optional_store_hidden',
                                   'test.shallow.optional_store_int', 'test.shallow.optional_true'])
        app.dev_mode = False

        ret = complete_set_inner_command(1, app, ['test.shallow.optional_store'],
                                         Document(u'/set test.shallow.optional_store '))
        ret.sort()
        self.assertListEqual(ret, [])

        ret = complete_set_inner_command(1, app, ['test.shallow.optional_store_choices'],
                                         Document(u'/set test.shallow.optional_store_choices '))
        ret.sort()
        self.assertListEqual(ret, ['cold', 'hot'])

        ret = complete_set_inner_command(1, app, ['test.shallow.optional_true'],
                                         Document(u'/set test.shallow.optional_true '))
        ret.sort()
        self.assertListEqual(ret, ['false', 'true'])

    def test_get_inner_command_func(self):
        app = make_app()

        def on_change_manual_arg(val):
            pass

        def on_delete_manual_arg():
            pass
        app.manual_args = {
            'app': {
                'manual_arg': (on_change_manual_arg, on_delete_manual_arg)
            }
        }
        app.set_args = {
            'test.shallow': {
                'optional_store': 'xyz',
                'optional_store_int': 64,
                'optional_const': False,
                'optional_append': ['hello', 'world'],
                'optional_append_const_a': True,
                'optional_count': 4,
                'optional_true': True,
                'optional_false': False,
                'POSITIONAL_1': 'stem',
                'optional_store_hidden': 'phrase',
            },
            'app': {
                'manual_arg': 'floof',
            }
        }

        with trap_print_output() as (out, err):
            get_inner_command.run_action('/get test.shallow.optional_store', app)
            self.assertEqual(out.getvalue().strip(), 'test.shallow.optional_store: xyz')

        with trap_print_output() as (out, err):
            get_inner_command.run_action('/get test.shallow.optional_store_int', app)
            self.assertEqual(out.getvalue().strip(), 'test.shallow.optional_store_int: 64')

        with trap_print_output() as (out, err):
            get_inner_command.run_action('/get test.shallow.optional_const', app)
            self.assertEqual(out.getvalue().strip(), 'test.shallow.optional_const: False')

        with trap_print_output() as (out, err):
            get_inner_command.run_action('/get test.shallow.optional_append', app)
            self.assertEqual(out.getvalue().strip(), 'test.shallow.optional_append: [\'hello\', \'world\']')

        with trap_print_output() as (out, err):
            get_inner_command.run_action('/get test.shallow.optional_append_const_a', app)
            self.assertEqual(out.getvalue().strip(), 'test.shallow.optional_append_const_a: True')

        with trap_print_output() as (out, err):
            get_inner_command.run_action('/get test.shallow.optional_count', app)
            self.assertEqual(out.getvalue().strip(), 'test.shallow.optional_count: 4')

        with trap_print_output() as (out, err):
            get_inner_command.run_action('/get test.shallow.optional_true', app)
            self.assertEqual(out.getvalue().strip(), 'test.shallow.optional_true: True')
        with trap_print_output() as (out, err):
            get_inner_command.run_action('/get test.shallow.optional_false', app)
            self.assertEqual(out.getvalue().strip(), 'test.shallow.optional_false: False')

        with trap_print_output() as (out, err):
            get_inner_command.run_action('/get test.shallow.POSITIONAL_1', app)
            self.assertEqual(out.getvalue().strip(), 'test.shallow.POSITIONAL_1: stem')

        with trap_print_output() as (out, err):
            get_inner_command.run_action('/get app.manual_arg', app)
            self.assertEqual(out.getvalue().strip(), 'app.manual_arg: floof')

        with trap_print_output() as (out, err):
            get_inner_command.run_action('/get test.shallow.optional_append_const_b', app)
            self.assertEqual(out.getvalue().strip(), 'test.shallow.optional_append_const_b: None')

        with self.assertRaises(InnerCommandError):
            get_inner_command.run_action('/get test.shallow.optional_store_hidden', app)

        app.dev_mode = True
        with trap_print_output() as (out, err):
            get_inner_command.run_action('/get test.shallow.optional_store_hidden', app)
            self.assertEqual(out.getvalue().strip(), 'test.shallow.optional_store_hidden: phrase')
        app.dev_mode = False

        with self.assertRaises(InnerCommandError):
            get_inner_command.run_action('/get test.fake.fake-arg', app)

        with self.assertRaises(InnerCommandError):
            get_inner_command.run_action('/get test.shallow.fake-arg', app)

    def test_complete_get_inner_command(self):
        app = make_app()

        def on_change_manual_arg(val):
            pass

        def on_delete_manual_arg():
            pass
        app.manual_args = {
            'app': {
                'manual_arg': (on_change_manual_arg, on_delete_manual_arg)
            }
        }
        app.set_args = {
            'test.shallow': {
                'optional_store': 'xyz',
                'optional_store_int': 64,
                'optional_const': False,
                'optional_append': ['hello', 'world'],
                'optional_append_const_a': True,
                'optional_count': 4,
                'optional_true': True,
                'optional_false': False,
                'POSITIONAL_1': 'stem',
                'optional_store_hidden': 'phrase',
            },
            'app': {
                'manual_arg': 'floof',
            }
        }

        ret = complete_get_inner_command(0, app, [], Document(u'/get '))
        ret.sort()
        self.assertListEqual(ret, ['app.manual_arg',
                                   'test.shallow.POSITIONAL_1',
                                   'test.shallow.optional_append', 'test.shallow.optional_append_const_a',
                                   'test.shallow.optional_const',
                                   'test.shallow.optional_count', 'test.shallow.optional_false',
                                   'test.shallow.optional_store', 'test.shallow.optional_store_int',
                                   'test.shallow.optional_true'])

        app.dev_mode = True
        ret = complete_get_inner_command(0, app, [], Document(u'/get '))
        ret.sort()
        self.assertListEqual(ret, ['app.manual_arg',
                                   'test.shallow.POSITIONAL_1',
                                   'test.shallow.optional_append', 'test.shallow.optional_append_const_a',
                                   'test.shallow.optional_const',
                                   'test.shallow.optional_count', 'test.shallow.optional_false',
                                   'test.shallow.optional_store', 'test.shallow.optional_store_hidden',
                                   'test.shallow.optional_store_int', 'test.shallow.optional_true'])
        app.dev_mode = False

    def test_del_inner_command_func(self):
        app = make_app()

        def on_change_manual_arg(val):
            pass

        def on_delete_manual_arg():
            pass
        app.manual_args = {
            'app': {
                'manual_arg': (on_change_manual_arg, on_delete_manual_arg)
            }
        }
        app.set_args = {
            'test.shallow': {
                'optional_store': 'xyz',
                'optional_store_int': 64,
                'optional_const': False,
                'optional_append': ['hello', 'world'],
                'optional_append_const_a': True,
                'optional_count': 4,
                'optional_true': True,
                'optional_false': False,
                'POSITIONAL_1': 'stem',
                'optional_store_hidden': 'phrase',
            },
            'app': {
                'manual_arg': 'floof',
            }
        }

        del_inner_command.run_action('/del test.shallow.optional_store', app)
        self.assertFalse('optional_store' in app.set_args['test.shallow'])

        del_inner_command.run_action('/del test.shallow.optional_store_int', app)
        self.assertFalse('optional_store_int' in app.set_args['test.shallow'])

        del_inner_command.run_action('/del test.shallow.optional_const', app)
        self.assertFalse('optional_const' in app.set_args['test.shallow'])

        del_inner_command.run_action('/del test.shallow.optional_append', app)
        self.assertFalse('optional_append' in app.set_args['test.shallow'])

        del_inner_command.run_action('/del test.shallow.optional_append_const_a', app)
        self.assertFalse('optional_append_const_a' in app.set_args['test.shallow'])

        del_inner_command.run_action('/del test.shallow.optional_count', app)
        self.assertFalse('optional_count' in app.set_args['test.shallow'])

        del_inner_command.run_action('/del test.shallow.optional_true', app)
        self.assertFalse('optional_true' in app.set_args['test.shallow'])

        del_inner_command.run_action('/del test.shallow.optional_false', app)
        self.assertFalse('optional_false' in app.set_args['test.shallow'])

        del_inner_command.run_action('/del test.shallow.POSITIONAL_1', app)
        self.assertFalse('POSITIONAL_1' in app.set_args['test.shallow'])

        with self.assertRaises(InnerCommandError):
            set_inner_command.run_action('/del test.shallow.optional_store_hidden', app)

        app.dev_mode = True
        del_inner_command.run_action('/del test.shallow.optional_store_hidden', app)
        self.assertFalse('optional_store_hidden' in app.set_args['test.shallow'])
        app.dev_mode = False

        del_inner_command.run_action('/del app.manual_arg', app)
        self.assertFalse('manual_arg' in app.set_args['app'])

        with self.assertRaises(InnerCommandError):
            set_inner_command.run_action('/del test.shallow.optional_append_const_b', app)

        with self.assertRaises(InnerCommandError):
            set_inner_command.run_action('/del test.fake.fake-arg', app)

        with self.assertRaises(InnerCommandError):
            set_inner_command.run_action('/del test.shallow.fake-arg', app)

        self.assertDictEqual(app.set_args, {
            'test.shallow': {},
            'app': {},
        })

    def test_complete_del_inner_command(self):
        app = make_app()

        def on_change_manual_arg(val):
            pass

        def on_delete_manual_arg():
            pass
        app.manual_args = {
            'app': {
                'manual_arg': (on_change_manual_arg, on_delete_manual_arg)
            }
        }
        app.set_args = {
            'test.shallow': {
                'optional_store': 'xyz',
                'optional_store_int': 64,
                'optional_const': False,
                'optional_append': ['hello', 'world'],
                'optional_append_const_a': True,
                'optional_count': 4,
                'optional_true': True,
                'optional_false': False,
                'POSITIONAL_1': 'stem',
                'optional_store_hidden': 'phrase',
            },
            'app': {
                'manual_arg': 'floof',
            }
        }

        ret = complete_del_inner_command(0, app, [], Document(u'/del '))
        ret.sort()
        self.assertListEqual(ret, ['app.manual_arg',
                                   'test.shallow.POSITIONAL_1',
                                   'test.shallow.optional_append', 'test.shallow.optional_append_const_a',
                                   'test.shallow.optional_const',
                                   'test.shallow.optional_count', 'test.shallow.optional_false',
                                   'test.shallow.optional_store', 'test.shallow.optional_store_int',
                                   'test.shallow.optional_true'])

        app.dev_mode = True
        ret = complete_del_inner_command(0, app, [], Document(u'/del '))
        ret.sort()
        self.assertListEqual(ret, ['app.manual_arg',
                                   'test.shallow.POSITIONAL_1',
                                   'test.shallow.optional_append', 'test.shallow.optional_append_const_a',
                                   'test.shallow.optional_const',
                                   'test.shallow.optional_count', 'test.shallow.optional_false',
                                   'test.shallow.optional_store', 'test.shallow.optional_store_hidden',
                                   'test.shallow.optional_store_int', 'test.shallow.optional_true'])
        app.dev_mode = False


if __name__ == '__main__':
    unittest.main()
