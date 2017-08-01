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
import brkt_cli
from brkt_cli.aws import share_logs, boto3_device
from brkt_cli.aws.model import Instance, Snapshot
from brkt_cli.validation import ValidationError


class S3():
    def __init__(self):
        self.buckets = Buckets()
        self.bucket = Bucket()
        self.meta = Meta()

    def Bucket(self, name):
        return self.bucket


class Bucket():
    def __init__(self):
        self.name = 'test-bucket'
        self.acl = ACL()
        self.region = 'matching-region'
        self.objects = Objects()

    def Acl(self):
        return self.acl

    def Object(self, path):
        return self.objects


class Buckets():
    def __init__(self):
        self.bucket = Bucket()

    def all(self):
        return [self.bucket]


class Meta():
    def __init__(self):
        self.client = Client()


class Client():
    def __init__(self):
        self.region = 'matching'
        self.value = None

    def head_bucket(self, Bucket):
        if self.region == 'unmatching':
            raise ValidationError()
        return self.value


class Objects():
    def __init__(self):
        self.list = List()

    def all(self):
        return [self.list]

    def get(self):
        return


class List():
    def __init__(self):
        self.key = 'matching'


class ACL():
    def __init__(self):
        self.grant = {'Grantee': {'Type': 'User',
                'URI': 'http://acs.amazonaws.com/groups/global/AllUsers'},
                'Permission': 'WRITE'}
        self.grants = [self.grant]


# This class is used for testing ShareLogs
class ShareLogsTestService(share_logs.ShareLogsService):
    created = False

    def get_instance(self, instance_id):
        instance = Instance()
        instance.state['Name'] = 'running'
        instance.root_device_name = '/dev/sda1'
        instance.id = 'test-id'

        dev = boto3_device.make_device(
            device_name='/dev/sda1',
            volume_id='vol-1'
        )
        instance.block_device_mappings = [dev]
        return instance

    def s3_connect(self):
        return S3()

    def create_snapshot(self, volume_id, name):
        snapshot = Snapshot()
        snapshot.id = 'test-id'
        snapshot.volume_size = '5'
        return snapshot

    def get_snapshots(self, snapshot_id):
        snapshot = Snapshot()
        snapshot.state = 'completed'
        return [snapshot]

    def run_instance(self, image_id, instance_type, block_device_mappings,
                     user_data, ebs_optimized, subnet_id):
        instance = Instance()
        ShareLogsTestService.created = True
        return instance


class TestShareLogs(unittest.TestCase):

    def setUp(self):
        brkt_cli.util.SLEEP_ENABLED = False

    def test_path(self):
        aws_svc = ShareLogsTestService()
        paths = ['#path', '\path', '@path', '$path', 'path%']
        for p in paths:
            with self.assertRaises(ValidationError):
                aws_svc.validate_file_name(p)

        # These charictors are all valid
        path = "!-_'/.*()PaTh8"
        result = aws_svc.validate_file_name(path)
        self.assertEqual(result, 0)

    def test_bucket_file(self):
        aws_svc = ShareLogsTestService()
        s3 = S3()

        # Tests if user doesn't already own bucket
        result = aws_svc.check_bucket_file(
            "different-bucket", "file", "matching", s3)
        self.assertEqual(result, 0)

        # Tests if user owns bucket in wrong region
        s3.meta.client.region = 'unmatching'
        with self.assertRaises(ValidationError):
            aws_svc.check_bucket_file(
                'test-bucket', "file", "unmatching", s3)

        s3.meta.client.region = 'matching'
        # Tests if the bucket has a matching file
        with self.assertRaises(ValidationError):
            aws_svc.check_bucket_file(
                "test-bucket", "matching", "matching", s3)

        # Tests if the bucket doesn't have write permission
        for b in s3.buckets.all():
            b.acl.grant['Permission'] = 'read'
        with self.assertRaises(ValidationError):
            aws_svc.check_bucket_file(
                "test-bucket", "file", "matching", s3)

    def test_normal(self):
        aws_svc = ShareLogsTestService()
        logs_svc = ShareLogsTestService()
        instance_id = 'test-instance'
        snapshot_id = None
        region = 'us-west-2'
        bucket = 'test-bucket'
        path = 'test/path'

        share_logs.share(aws_svc, logs_svc, instance_id=instance_id, 
        snapshot_id=snapshot_id, region=region, bucket=bucket, path=path,
        subnet_id=None)
