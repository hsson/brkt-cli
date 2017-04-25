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

import re
import unittest

from brkt_cli import mv_version


class TestMetavisorVersionCheck(unittest.TestCase):

    def test_version_regex_found(self):
        v = 'metavisor-1-3-20-gc90f6f77d-special'
        version_args = [ '1.3', '1', '1-3', '1-3-20',
                         'metavisor-1-3-20-gc90f6f77d-special']

        for version in version_args:
            vr = mv_version.version_regex(version)
            self.assertIsNotNone(re.search(vr, v))


    def test_version_regex_not_found(self):
        v = 'metavisor-1-3-20-gc90f6f77d-special'
        version_args = [ '1.2', '2', '1-5', '1.3.21',
                         'metavisor-1-3-20-gc90f6f77d' ]

        for version in version_args:
            vr = mv_version.version_regex(version)
            self.assertIsNone(re.search(vr, v))
