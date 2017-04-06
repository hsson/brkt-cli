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
from boto.ec2.blockdevicemapping import (
    BlockDeviceMapping,
    EBSBlockDeviceType,
)
from brkt_cli.aws.aws_service import snapshot_log_volume

log = logging.getLogger(__name__)


def share(aws_svc=None, instance_id=None,
          region=None, snapshot_id=None, bucket=None, path=None):

    log.info('Sharing logs')
    try:
        # Check bucket for file and bucket permissions
        bucket_exists = aws_svc.check_bucket_file(bucket, path, region)

        if bucket_exists is False:
            log.info('Creating new bucket')
            # If bucket isn't already owned create new one
            new_bucket = aws_svc.make_bucket(bucket, region)
            # Reconnect with updated bucket list
            aws_svc.s3_connect(region)
            # Allow public write access to new bucket
            new_bucket.set_acl('public-read-write')

        if snapshot_id is None:
            # Get instance from ID
            instance = aws_svc.get_instance(instance_id)
            # Find name of the root device
            root_name = instance.root_device_name
            # Get root volume ID
            current_value = instance.block_device_mapping.current_value
            vol_id = current_value.connection[root_name].volume_id
            # Create a snapshot of the root volume
            snapshot = aws_svc.create_snapshot(
                volume_id=vol_id, name="temp-logs-snapshot")
            # Wait for snapshot to post
            aws_svc.wait_snapshot(snapshot)

        else:  # Taking logs from a snapshot
            snapshot = aws_svc.get_snapshot(snapshot_id)

        # Split path name into path and file
        os.path.split(path)
        file = os.path.basename(path)
        
        # Updates ACL on logs file object
        acl = '--no-sign-request --acl public-read-write'
        # Startup script for new instance
        # This creates logs file and copys to bucket
        amzn = '#!/bin/bash\n' + \
        'sudo mount -t ufs -o ro,ufstype=ufs2 /dev/xvdg4 /mnt\n' + \
        'sudo tar czvf /tmp/%s -C /mnt ./log ./crash\n' % (file) + \
        'sudo aws s3 cp /tmp/%s s3://%s/%s %s\n' % (file, bucket, path, acl)

        # Specifies volume to be attached to instance
        bdm = BlockDeviceMapping()
        mv_disk = EBSBlockDeviceType(volume_type='gp2',
            snapshot_id=snapshot.id, delete_on_termination=True)
        mv_disk.size = snapshot.volume_size
        bdm['/dev/sdg'] = mv_disk

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

        # Launch new instance, with volume and startup script
        new_instance = aws_svc.run_instance(
            image_id, instance_type='m3.medium', block_device_map=bdm,
            user_data=amzn, ebs_optimized=False)

        # wait for instance to launch
        aws_svc.wait_instance(new_instance)

        # wait for file to upload
        aws_svc.wait_bucket_file(bucket, path, region)
        log.info('Deleting new snapshot and instance')

    finally:
        try:
            aws_svc.delete_snapshot(snapshot.id)
            aws_svc.terminate_instance(new_instance.id)
        except Exception as e:
            log.warn("Failed during cleanup: %s", e)
