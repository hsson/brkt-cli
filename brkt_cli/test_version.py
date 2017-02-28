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

import datetime

import iso8601

from brkt_cli import CLIConfig
from brkt_cli import version


class TestVersionCheck(unittest.TestCase):

    def test_is_version_supported(self):
        supported = [
            '0.9.8', '0.9.9', '0.9.9.1', '0.9.10', '0.9.11', '0.9.12'
        ]
        self.assertFalse(
            version._is_version_supported('0.9.7', supported)
        )
        self.assertTrue(
            version._is_version_supported('0.9.8', supported)
        )
        self.assertTrue(
            version._is_version_supported('0.9.12', supported)
        )
        self.assertTrue(
            version._is_version_supported('0.9.13pre1', supported)
        )
        self.assertTrue(
            version._is_version_supported('0.9.13', supported)
        )

    def test_is_later_version_available(self):
        supported = [
            '0.9.8', '0.9.9', '0.9.9.1', '0.9.10', '0.9.11', '0.9.12'
        ]
        self.assertTrue(
            version._is_later_version_available('0.9.11', supported)
        )
        self.assertFalse(
            version._is_later_version_available('0.9.12', supported)
        )
        self.assertFalse(
            version._is_later_version_available('0.9.13pre1', supported)
        )

    def test_version_check_time(self):
        cfg = CLIConfig()

        # Not set.
        self.assertIsNone(version.get_last_version_check_time(cfg))

        # Set.
        before = datetime.datetime.now(tz=iso8601.UTC)
        version.set_last_version_check_time(cfg)
        t = version.get_last_version_check_time(cfg)
        self.assertIsNotNone(t)
        after = datetime.datetime.now(tz=iso8601.UTC)

        self.assertTrue(before <= t <= after)

    def test_is_version_check_needed(self):
        cfg = CLIConfig()

        # Not set.
        self.assertTrue(version.is_version_check_needed(cfg))

        # Set to 25 hours ago.
        now = datetime.datetime.now(tz=iso8601.UTC)
        dt = now - datetime.timedelta(hours=25)
        version.set_last_version_check_time(cfg, dt=dt)
        self.assertTrue(version.is_version_check_needed(cfg))

        # Set to 23 hours ago.
        dt = now - datetime.timedelta(hours=23)
        version.set_last_version_check_time(cfg, dt=dt)
        self.assertFalse(version.is_version_check_needed(cfg))
