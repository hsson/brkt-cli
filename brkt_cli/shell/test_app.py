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
from brkt_cli.shell.test_utils import make_app


class TestApp(unittest.TestCase):
    def test_parse_command(self):
        app = make_app()
        app.saved_commands = {
            'foo': u'shallow --optional_true',
            'bar': u'foo'
        }

        ret = app.parse_command(Document(u'shallow --optional_true --optional_false --optional_store abc'))
        self.assertEqual(ret, u'shallow --optional_true --optional_false --optional_store abc')

        ret = app.parse_command(Document(u'foo'))
        self.assertEqual(ret, u'shallow --optional_true')

        ret = app.parse_command(Document(u'bar'))
        self.assertEqual(ret, u'shallow --optional_true')

    def test_parse_embedded_commands(self):
        app = make_app()

        cmd_text = u'/set test $(shallow --optional_true)'
        embedded_commands = App.parse_embedded_command_text(cmd_text)
        ret = app._parse_embedded_commands(cmd_text, embedded_commands)
        self.assertRegexpMatches(ret, r'^\/set test .+ shallow --optional_true$')

        cmd_text = u'/set test $(shallow --optional_true) and $(deep semi_shallow)'
        embedded_commands = App.parse_embedded_command_text(cmd_text)
        ret = app._parse_embedded_commands(cmd_text, embedded_commands)
        self.assertRegexpMatches(ret, r'^\/set test .+ shallow --optional_true and .+ deep semi_shallow$')

        cmd_text = u'/set test $(shallow $(deep semi_shallow) --optional_true)'
        embedded_commands = App.parse_embedded_command_text(cmd_text)
        ret = app._parse_embedded_commands(cmd_text, embedded_commands)
        self.assertRegexpMatches(ret, r'^\/set test .+ shallow .+ deep semi_shallow --optional_true$')

    def test_parse_set_args_commands(self):
        app = make_app()
        super_shallow_cmd = app.cmd.get_subcommand_from_path('test.super_shallow')
        shallow_cmd = app.cmd.get_subcommand_from_path('test.shallow')

        # Test with no arguments specified
        doc = Document(text=u'test super_shallow')
        app.set_args['test.super_shallow'] = {}
        ret = app._parse_set_args_commands(doc, super_shallow_cmd)
        self.assertEqual(ret.strip(), u'test super_shallow')

        # Test with only required arguments specified
        doc = Document(text=u'test shallow tree king')
        app.set_args['test.shallow'] = {}
        ret = app._parse_set_args_commands(doc, shallow_cmd)
        self.assertEqual(ret.strip(), u'test shallow tree king')

        # Test with all arguments specified
        doc = Document(text=u'test shallow --optional_true --optional_false --optional_store abc '
                            u'--optional_store_int 81 --optional_store_default marker --optional_const '
                            u'--optional_append foo --optional_append bar --optional_append baz '
                            u'--optional_append_const_a --optional_append_const_b --optional_count '
                            u'--optional_count tree king')
        app.set_args['test.shallow'] = {}
        ret = app._parse_set_args_commands(doc, shallow_cmd)
        self.assertEqual(ret.strip(), u'test shallow --optional_true --optional_false --optional_store abc '
                                      u'--optional_store_int 81 --optional_store_default marker --optional_const '
                                      u'--optional_append foo --optional_append bar --optional_append baz '
                                      u'--optional_append_const_a --optional_append_const_b --optional_count '
                                      u'--optional_count tree king')

        # Test with all arguments in set_args
        doc = Document(text=u'test shallow')
        app.set_args['test.shallow'] = {
            'optional_false': True,
            'optional_true': True,
            'optional_store': 'xyz',
            'optional_store_int': 64,
            'optional_store_default': 'glass',
            'optional_const': True,
            'optional_append': ['hello', 'world'],
            'optional_append_const_a': True,
            'optional_append_const_b': True,
            'optional_count': 4,
            'POSITIONAL_1': 'stem',
            'POSITIONAL_2': 'queen',
        }
        ret = app._parse_set_args_commands(doc, shallow_cmd)
        self.assertEqual(ret.strip(), u'test shallow --optional_true --optional_false --optional_store xyz '
                                      u'--optional_store_int 64 --optional_store_default glass --optional_const '
                                      u'--optional_append hello --optional_append world '
                                      u'--optional_append_const_a --optional_append_const_b --optional_count '
                                      u'--optional_count --optional_count --optional_count stem queen')

        # Test with all arguments in set_args and specified. This is to test override order: specified values should
        # trump set_args
        doc = Document(text=u'test shallow --optional_true --optional_false --optional_store abc '
                            u'--optional_store_int 81 --optional_store_default marker --optional_const '
                            u'--optional_append foo --optional_append bar --optional_append baz '
                            u'--optional_append_const_a --optional_append_const_b --optional_count '
                            u'--optional_count tree king')
        app.set_args['test.shallow'] = {
            'optional_false': False,
            'optional_true': False,
            'optional_store': 'xyz',
            'optional_store_int': 64,
            'optional_store_default': 'glass',
            'optional_const': False,
            'optional_append': ['hello', 'world'],
            'optional_append_const_a': False,
            'optional_append_const_b': False,
            'optional_count': 4,
            'POSITIONAL_1': 'stem',
            'POSITIONAL_2': 'queen',
        }
        ret = app._parse_set_args_commands(doc, shallow_cmd)
        self.assertEqual(ret.strip(), u'test shallow --optional_true --optional_false --optional_store abc '
                                      u'--optional_store_int 81 --optional_store_default marker --optional_const '
                                      u'--optional_append foo --optional_append bar --optional_append baz '
                                      u'--optional_append_const_a --optional_append_const_b --optional_count '
                                      u'--optional_count tree king')

        # Test to make sure that optional_true and optional_false must be True in set_args to be in the command
        doc = Document(text=u'test shallow')
        app.set_args['test.shallow'] = {
            'optional_false': True,
            'optional_true': True,
        }
        ret = app._parse_set_args_commands(doc, shallow_cmd)
        self.assertEqual(ret.strip(), u'test shallow --optional_true --optional_false')

        # Test to make sure that optional_true and optional_false must be False in set_args to not be in the command
        doc = Document(text=u'test shallow')
        app.set_args['test.shallow'] = {
            'optional_false': False,
            'optional_true': False,
        }
        ret = app._parse_set_args_commands(doc, shallow_cmd)
        self.assertEqual(ret.strip(), u'test shallow')

        # Test that hidden commands do not work when dev mode is off
        doc = Document(text=u'test shallow --optional_store_hidden word')
        app.set_args['test.shallow'] = {}
        ret = app._parse_set_args_commands(doc, shallow_cmd)
        self.assertEqual(ret.strip(), u'test shallow')

        # Test that hidden commands do not work when dev mode is off
        doc = Document(text=u'test shallow')
        app.set_args['test.shallow'] = {
            'optional_store_hidden': 'phrase',
        }
        ret = app._parse_set_args_commands(doc, shallow_cmd)
        self.assertEqual(ret.strip(), u'test shallow')

        # Test that hidden commands work only when dev mode is on
        app.dev_mode = True
        doc = Document(text=u'test shallow --optional_store_hidden word')
        app.set_args['test.shallow'] = {}
        ret = app._parse_set_args_commands(doc, shallow_cmd)
        self.assertEqual(ret.strip(), u'test shallow --optional_store_hidden word')

        # Test that hidden commands work only when dev mode is on
        app.dev_mode = True
        doc = Document(text=u'test shallow')
        app.set_args['test.shallow'] = {
            'optional_store_hidden': 'phrase',
        }
        ret = app._parse_set_args_commands(doc, shallow_cmd)
        self.assertEqual(ret.strip(), u'test shallow --optional_store_hidden phrase')

        # Reset dev mode
        app.dev_mode = False

    def test_parse_embedded_command_text(self):
        def parse_text(text):
            return [text[start+2:end] for start, end in App.parse_embedded_command_text(text)]

        self.assertListEqual(parse_text('foo bar'), [])
        self.assertListEqual(parse_text(''), [])
        self.assertListEqual(parse_text('foo $(hello world) bar'), ['hello world'])
        self.assertListEqual(parse_text('$(hello world) foo bar'), ['hello world'])
        self.assertListEqual(parse_text('foo bar $(hello world)'), ['hello world'])
        self.assertListEqual(parse_text('foo $(hello) bar $(world) baz'), ['hello','world'])
        self.assertListEqual(parse_text('foo $(hello $(inserted) world) bar'), ['hello $(inserted) world'])
        self.assertListEqual(parse_text('foo $(hello) \$\(world\) bar'), ['hello'])
        self.assertListEqual(parse_text('foo $(hel\)lo) bar'), ['hel\\)lo'])


if __name__ == '__main__':
    unittest.main()
