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

from brkt_cli.shell.enum import Enum


class TestEnum(unittest.TestCase):
    def test_format_enum(self):
        class FakeEnum(Enum):
            Unknown, Foo, Bar = range(3)

        self.assertEqual(FakeEnum.format_enum(FakeEnum.Unknown), 'Unknown')
        self.assertEqual(FakeEnum.format_enum(FakeEnum.Foo), 'Foo')
        self.assertEqual(FakeEnum.format_enum(FakeEnum.Bar), 'Bar')
        self.assertEqual(FakeEnum.format_enum(2), 'Bar')
        self.assertIsNone(FakeEnum.format_enum(3))


if __name__ == '__main__':
    unittest.main()
