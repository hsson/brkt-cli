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
from brkt_cli.aws import test_aws_service
from brkt_cli.validation import ValidationError
from brkt_cli.aws import share_logs


class AWSService1(test_aws_service.DummyAWSService):
    # This class is used for testing ShareLogs
    class Snapshot():
        def id(self):
            return

        def volume_size():
            return
    def s3_connect(self):
        return

    def check_bucket_file(self, bucket, region, file, s3, permissions=True):
        return True

    def get_snapshot(self, snapshot_id):
        snapshot = self.Snapshot()
        return snapshot

    def get_image(self, image_id, retry=False):
        return

    def run_instance(self, image_id, instance_type,
                     block_device_map, user_data, ebs_optimized):
        return

    def wait_instance(self, instance):
        return

    def wait_bucket_file(self, bucket, path, region, s3):
        return


class TestShareLogs(unittest.TestCase):

    def test_path(self):
        aws_svc = test_aws_service.DummyAWSService()
        paths = ['#path', '\path', '@path', '$path', 'path%']
        for p in paths:
            with self.assertRaises(ValidationError):
                aws_svc.validate_file_name(p)

        # These charictors are all valid
        path = "!-_'/.*()PaTh8"
        result = aws_svc.validate_file_name(path)
        self.assertEqual(result, 0)

    def test_bucket_file(self):
        aws_svc = test_aws_service.DummyAWSService()
        # Tests if user doesn't already own bucket
        result = aws_svc.check_bucket_file("un-matching name", "match", "file")
        self.assertEqual(result, 0)
        # Tests if user owns bucket in wrong region
        with self.assertRaises(ValidationError):
            aws_svc.check_bucket_file("matching", "un-matching region", "file")
        # Tests if the bucket has a matching file
        with self.assertRaises(ValidationError):
            aws_svc.check_bucket_file("matching", "matching", "file")
        # Tests if the bucket has write permission
        with self.assertRaises(ValidationError):
            aws_svc.check_bucket_file("matching", "matching",
                                      None, permissions=False)
        # Tests if the user owns a writeable bucket
        result2 = aws_svc.check_bucket_file("matching", "matching", None)
        self.assertEqual(result2, 1)

    def test_normal(self):
        aws_svc = AWSService1()
        logs_svc = AWSService1()
        instance = 'test-instance'
        snapshot_id = 'test-snapshot'
        region = 'us-west-2'
        bucket = 'test-bucket'
        path = 'test/path'

        share_logs.share(aws_svc, logs_svc, instance_id=instance,
            snapshot_id=snapshot_id, region=region, bucket=bucket, path=path)
