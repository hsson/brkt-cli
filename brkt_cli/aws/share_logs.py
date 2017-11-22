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

import logging
import os
import time
import subprocess
from brkt_cli.aws import aws_service, boto3_device

log = logging.getLogger(__name__)


def share(aws_svc=None, logs_svc=None, instance_id=None, region=None,
          snapshot_id=None, dest=None, subnet_id=None, bast_key=None,
          bast_user=None, bast_ip=None):

    log.info('Sharing logs')
    snapshot = None
    new_instance = None
    key_name = None
    new_snapshot = False

    try:

        if not snapshot_id:
            # Get instance from ID
            instance = aws_svc.get_instance(instance_id)
            # Find name of the root device
            root_name = instance.root_device_name
            # Get root volume ID
            root_dev = boto3_device.get_device(
                instance.block_device_mappings, root_name)
            # Create a snapshot of the root volume
            snapshot = aws_svc.create_snapshot(
                volume_id=root_dev['Ebs']['VolumeId'],
                name="temp-logs-snapshot"
            )
            # Wait for snapshot to post
            log.info('Waiting for snapshot...')
            aws_service.wait_for_snapshots(aws_svc, snapshot.id)
            new_snapshot = True

        else:  # Taking logs from a snapshot
            snapshot = aws_svc.get_snapshot(snapshot_id)

        # Split destination path name into path and file
        path, logs_file = os.path.split(dest)

        # Specifies volume to be attached to instance
        mv_disk = boto3_device.make_device(
            device_name='/dev/sdg',
            volume_type='gp2',
            snapshot_id=snapshot.id,
            delete_on_termination=True,
            volume_size=snapshot.volume_size
        )
        bdm = [mv_disk]

        # Images taken on 4/3/2017 from:
        # https://aws.amazon.com/amazon-linux-ami/
        IMAGES_BY_REGION = {
            "us-east-1": "ami-0b33d91d",
            "us-east-2": "ami-c55673a0",
            "us-west-1": "ami-165a0876",
            "us-west-2": "ami-f173cc91",
            "ap-south-1": "ami-f9daac96",
            "ap-northeast-2": "ami-dac312b4",
            "ap-southeast-1": "ami-dc9339bf",
            "ap-southeast-2": "ami-1c47407f",
            "ap-northeast-1": "ami-56d4ad31",
            "eu-central-1": "ami-af0fc0c0",
            "eu-west-1": "ami-70edb016",
            "eu-west-2": "ami-f1949e95",
        }

        image_id = IMAGES_BY_REGION[region]

        # name key_pair
        key_name = 'ShareLogsKey' + time.strftime("%Y%m%d%H%M")
        # generate new random key to use for scp
        logs_svc.create_key(aws_svc.ec2client, path, key_name)
        # start up script for new instance
        amzn = '#!/bin/bash\n' + \
        'sudo mount -t ufs -o ro,ufstype=ufs2 /dev/xvdg4 /mnt\n' + \
        'sudo tar czvf /tmp/temp_logs -C /mnt ./log ./crash\n' + \
        'mv /tmp/temp_logs /tmp/%s' % (logs_file)

        # Launch new instance, with volume and startup script
        new_instance = aws_svc.ec2client.run_instances(
            ImageId=image_id, MinCount=1, MaxCount=1, InstanceType='m4.large',
            BlockDeviceMappings=bdm, UserData=amzn, EbsOptimized=False,
            SubnetId=subnet_id, KeyName=key_name)

        instance_id = new_instance['Instances'][0]['InstanceId']

        # wait for instance to launch
        log.info('Waiting for instance to launch')
        aws_service.wait_for_instance(aws_svc, instance_id)

        instance_ip = logs_svc.get_instance_ip(aws_svc.ec2, instance_id)

        # wait for file to download
        log.info('Waiting for file to download')
        logs_svc.wait_file(instance_ip, logs_file, dest, key_name, path,
                           bast_key, bast_user, bast_ip)

        log.info('Deleting new snapshot, instance, and key')

    finally:
        # delete only new instances, snapshots, and keys
        if key_name:
            aws_svc.ec2client.delete_key_pair(KeyName=key_name)
            os.remove("%s/%s.pem" % (path, key_name))
        if new_snapshot and new_instance:
            aws_service.clean_up(aws_svc, instance_ids=[instance_id],
                snapshot_ids=[snapshot.id])
        if not new_snapshot and new_instance:
            aws_service.clean_up(aws_svc, instance_ids=[instance_id])
            new_snapshot = False
        if new_snapshot and not new_instance:
            aws_service.clean_up(aws_svc, snapshot_ids=[snapshot.id])


class ShareLogsService():

    def wait_file(self, ip, logs_file, dest, key, path,
                  bast_key, bast_user, bast_ip):
        for i in range(60):
            try:
                self.scp(ip, "/tmp/%s" % logs_file, dest, key, path,
                         bast_key, bast_user, bast_ip)
                return
            except subprocess.CalledProcessError:
                time.sleep(15)
                pass
        log.error("Timed out waiting for file to download")

    def scp(self, external_ip, src, dest, key, path,
            bast_key, bast_user, bast_ip):
        sshflags = " ".join([
            "-o ServerAliveInterval=10",
            "-o UserKnownHostsFile=/dev/null",
            "-o StrictHostKeyChecking=no",
            "-o ConnectTimeout=5",
            "-o LogLevel=quiet",
        ])
        if bast_key:
            bastion = "ssh -i %s -W %%h:%%p %s@%s" % (bast_key,
                bast_user, bast_ip)
            sshflags += " -o ProxyCommand='%s'" % bastion

        command = 'scp %s -i %s/%s.pem ec2-user@%s:%s %s >& /dev/null' % (
            sshflags, path, key, external_ip, src, dest)
        return subprocess.check_output(command, shell=True)

    def get_instance_ip(self, ec2, instance_id):
        ip = None
        for i in range(40):
            instance = ec2.Instance(instance_id)
            ip = instance.public_dns_name
            if ip:
                return ip
            if instance.state == 'terminated':
                raise Exception('Instance died on launch')

            time.sleep(5)

        log.error('Failed finding IP address for instance %s' % instance_id)

    def create_key(self, ec2client, dest, key):
        # create new key and put file in destination dir
        outfile = open("%s/%s.pem" % (dest, key), 'w')
        key_pair = ec2client.create_key_pair(KeyName=key)
        key_pair_out = str(key_pair['KeyMaterial'])
        outfile.write(key_pair_out)
        # change permissions on key file
        subprocess.check_output("chmod 400 %s/%s.pem" %
            (dest, key), shell=True)
