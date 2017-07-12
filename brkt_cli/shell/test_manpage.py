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

from brkt_cli.shell.manpage import Manpage
from brkt_cli.shell.test_utils import make_app


class TestManpage(unittest.TestCase):
    def test_get_text(self):
        app = make_app()
        manpage = Manpage(app)

        ret = manpage.get_text(Document(u''))
        self.assertEqual(ret, '')

        ret = manpage.get_text(Document(u'deep'))
        self.assertTrue(ret.startswith('has subcommands'))
        self.assertTrue('[-h]' in ret)

        ret = manpage.get_text(Document(u'deep semi_shallow'))
        self.assertTrue(ret.startswith('has no subcommands and one arguments'))
        self.assertTrue('[-h]' in ret)
        self.assertTrue('[--optional_store OPTIONAL_STORE]' in ret)

        ret = manpage.get_text(Document(u'super_shallow'))
        self.assertTrue(ret.startswith('has no subcommands and no arguments'))
        self.assertTrue('[-h]' in ret)

        ret = manpage.get_text(Document(u'shallow'))
        self.assertTrue(ret.startswith('has no subcommands but all arguments'))
        self.assertTrue('[--optional_true]' in ret)
        self.assertTrue('[--optional_false]' in ret)
        self.assertTrue('[--optional_store OPTIONAL_STORE]' in ret)
        self.assertTrue('[--optional_store_int OPTIONAL_STORE_INT]' in ret)
        self.assertTrue('[--optional_store_default OPTIONAL_STORE_DEFAULT]' in ret)
        self.assertTrue('[--optional_store_choices {hot,cold}]' in ret)
        self.assertTrue('[--optional_const]' in ret)
        self.assertTrue('[--optional_append OPTIONAL_APPEND]' in ret)
        self.assertTrue('[--optional_append_const_a]' in ret)
        self.assertTrue('[--optional_append_const_b]' in ret)
        self.assertTrue('[--optional_count]' in ret)
        self.assertTrue('POSITIONAL_1 POSITIONAL_2' in ret)

        ret = manpage.get_text(Document(u'shallow --optional_store'))
        self.assertEqual(ret, 'Optional store')

        ret = manpage.get_text(Document(u'shallow --optional_store foo'))
        self.assertEqual(ret, 'Optional store')

        ret = manpage.get_text(Document(u'shallow --optional_store foo '))
        self.assertTrue(ret.startswith('has no subcommands but all arguments'))
        self.assertTrue('[--optional_true]' in ret)
        self.assertTrue('[--optional_false]' in ret)
        self.assertTrue('[--optional_store OPTIONAL_STORE]' in ret)
        self.assertTrue('[--optional_store_int OPTIONAL_STORE_INT]' in ret)
        self.assertTrue('[--optional_store_default OPTIONAL_STORE_DEFAULT]' in ret)
        self.assertTrue('[--optional_store_choices {hot,cold}]' in ret)
        self.assertTrue('[--optional_const]' in ret)
        self.assertTrue('[--optional_append OPTIONAL_APPEND]' in ret)
        self.assertTrue('[--optional_append_const_a]' in ret)
        self.assertTrue('[--optional_append_const_b]' in ret)
        self.assertTrue('[--optional_count]' in ret)
        self.assertTrue('POSITIONAL_1 POSITIONAL_2' in ret)

        ret = manpage.get_text(Document(u'shallow --optional_store foo --optional_true'))
        self.assertEqual(ret, 'Optional true')


if __name__ == '__main__':
    unittest.main()
