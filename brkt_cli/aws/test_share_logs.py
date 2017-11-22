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


class EC2():

    def Instance(self, instance_id):
        instance = Instance()
        instance.id = instance_id
        instance.public_dns_name = 'test-name'
        instance.state = 'running'
        return instance


class EC2Client():

    def delete_key_pair(self, KeyName):
        return

    def create_key_pair(self, KeyName):
        return {'KeyMaterial': 123}

    def run_instances(self, ImageId, MinCount, MaxCount, InstanceType,
            BlockDeviceMappings, UserData, EbsOptimized,
            SubnetId, KeyName):
        instance = {'Instances': [{'InstanceId': 'test-id'}]}

        return instance


# This class is used for testing ShareLogs
class ShareLogsTestService(share_logs.ShareLogsService):

    def __init__(self):
        self.ec2client = EC2Client()
        self.ec2 = EC2()

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

    def create_snapshot(self, volume_id, name):
        snapshot = Snapshot()
        snapshot.id = 'test-id'
        snapshot.volume_size = '5'
        return snapshot

    def get_snapshots(self, snapshot_id):
        snapshot = Snapshot()
        snapshot.state = 'completed'
        return [snapshot]

    def get_snapshot(self, snapshot_id):
        snapshot = Snapshot()
        snapshot.state = 'completed'
        return snapshot

    def wait_file(self, ip, logs_file, dest, key, path,
                  bast_key=None, bast_user=None, bast_ip=None):
        return


class TestShareLogs(unittest.TestCase):

    def setUp(self):
        brkt_cli.util.SLEEP_ENABLED = False

    def test_with_instance_id(self):
        aws_svc = ShareLogsTestService()
        logs_svc = ShareLogsTestService()
        instance_id = 'test-instance'
        snapshot_id = None
        region = 'us-west-2'
        destination = "./logs.tar.gz"

        share_logs.share(aws_svc, logs_svc, instance_id=instance_id,
        snapshot_id=snapshot_id, region=region, dest=destination,
        subnet_id=None, bast_key=None, bast_user=None, bast_ip=None)

    def test_with_snapshot_id(self):
        aws_svc = ShareLogsTestService()
        logs_svc = ShareLogsTestService()
        instance_id = None
        snapshot_id = 'test-snapshot'
        region = 'us-west-2'
        destination = "./logs.tar.gz"

        share_logs.share(aws_svc, logs_svc, instance_id=instance_id,
        snapshot_id=snapshot_id, region=region, dest=destination,
        subnet_id=None, bast_key=None, bast_user=None, bast_ip=None)
