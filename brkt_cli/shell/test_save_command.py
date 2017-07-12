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

from brkt_cli.shell.save_command import complete_alias_inner_command
from brkt_cli.shell.test_utils import make_app


class TestSaveCommand(unittest.TestCase):
    def test_complete_alias_inner_command(self):
        app = make_app()

        ret = complete_alias_inner_command(0, app, [], Document(u'/alias '))
        ret.sort()
        self.assertListEqual(ret, [])

        ret = complete_alias_inner_command(1, app, ['foo'], Document(u'/alias foo '))
        ret.sort()
        self.assertListEqual(ret, ['deep', 'shallow', 'super_shallow'])


if __name__ == '__main__':
    unittest.main()
