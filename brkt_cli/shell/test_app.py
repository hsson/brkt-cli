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

from brkt_cli.shell import ShellCompleter, App
from brkt_cli.shell.inner_commands import InnerCommand
from brkt_cli.shell.raw_commands import CommandPromptToolkit

class TestAppClass(App):

    INNER_COMMANDS = {
        u'/test': InnerCommand('test', 'tests with no arguments', 'test', None),
        u'/test_arg': InnerCommand('test_arg', 'tests with an arguments', 'test ARG', None),
    }

    def make_cli_interface(self):
        pass

def generate_app():
    cmd = CommandPromptToolkit('test', 'tester', 'test', 'test', None)
    completer = ShellCompleter(cmd)
    return TestAppClass(completer, cmd)

class TestApp(unittest.TestCase):
    def test_parse_embedded_commands(self):
        def parse_text(text):
            return [text[start+2:end] for start, end in App.parse_embedded_commands(text)]

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
