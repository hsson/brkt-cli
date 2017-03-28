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
import time
#from brkt_cli.aws.encrypt_ami import (snapshot_log_volume)
from brkt_cli.aws.aws_service import (wait_for_volume)
#from brkt_cli.aws.aws_service import (create_snapshot)
import boto
from boto.ec2.blockdevicemapping import (
    BlockDeviceMapping,
    EBSBlockDeviceType,
)
#from brkt_cli.aws.aws_service import (create_volume)

#log = logging.getLogger(__name__)

def share(aws_svc=None, instance_id=None, bracket_aws_account=None, snapshot_id=None):
    
    aws_svc.s3_connect('us-west-2')
    aws_svc.make_bucket('voll-bucket')
    aws_svc.wait_bucket_file()
    """
    #Get instance from ID
    instance = aws_svc.get_instance(instance_id)
    print 'got instance'

    #Find name of the root device
    root_name = instance.root_device_name
    #Get root volume ID
    vol_id = instance.block_device_mapping.current_value.connection[root_name].volume_id
    #Create a snapshot of the root volume
    snapshot = aws_svc.create_snapshot(volume_id=vol_id, name="my-snapshot")
    #Wait for snapshot to post
    aws_svc.wait_snapshot(snapshot)

    #Startup script for new instance
    #This creates logs file and copys to bucket
    amzn = '#!/bin/bash\n' + \
    'sudo mount -t ufs -o ro,ufstype=44bsd /dev/xvdg7 /mnt\n' + \
    'sudo tar czvf /tmp/file.tar.gz -C /mnt .\n' + \
    'sudo aws s3 cp /tmp/file.tar.gz s3://voll-bucket/file.tar.gz --no-sign-request --acl public-read-write\n'

    #Specifies volume to be attached to instance
    bdm = BlockDeviceMapping()
    mv_disk = EBSBlockDeviceType(volume_type='gp2', snapshot_id=snapshot.id, delete_on_termination=True)
    mv_disk.size = snapshot.volume_size
    bdm['/dev/sdg'] = mv_disk

    #Hard coded image type
    image_id = "ami-f173cc91"
    print 'launching instance'
    #Launch new instance, with volume and startup script
    instance = aws_svc.run_instance(image_id, instance_type='t2.small', block_device_map=bdm, user_data=amzn, ebs_optimized=False)
    
    # wait for instance to launch
    aws_svc.wait_instance(instance)

    print 'waiting'
    time.sleep(85)

    print 'deleting'
    aws_svc.delete_snapshot(snapshot.id)
    aws_svc.terminate_instance(instance.id)
    """
