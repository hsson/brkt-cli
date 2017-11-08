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

"""
Create an encrypted AMI (with new metavisor) based
on an existing encrypted AMI.

Before running brkt updaet-encrypted-ami, set the AWS_ACCESS_KEY_ID and
AWS_SECRET_ACCESS_KEY environment variables, like you would when
running the AWS command line utility.
"""

import json
import logging
import os

from brkt_cli.aws import boto3_device, aws_service
from brkt_cli.aws.aws_constants import (
    DESCRIPTION_GUEST_CREATOR,
    DESCRIPTION_METAVISOR_UPDATER,
    NAME_ENCRYPTED_ROOT_SNAPSHOT,
    NAME_GUEST_CREATOR,
    NAME_METAVISOR_ROOT_SNAPSHOT,
    NAME_METAVISOR_UPDATER)
from brkt_cli.aws.aws_service import (
    clean_up,
    create_encryptor_security_group,
    log_exception_console,
    snapshot_root_volume,
    stop_and_wait,
    wait_for_image,
    wait_for_instance,
    wait_for_volume_attached)
from brkt_cli.encryptor_service import (
    encryptor_did_single_disk,
    wait_for_encryptor_up,
    wait_for_encryption
)
from brkt_cli.instance_config import (
    InstanceConfig,
    INSTANCE_UPDATER_MODE,
)
from brkt_cli.util import Deadline

log = logging.getLogger(__name__)

MV_ROOT_DEVICE_NAME = '/dev/sda1'
GUEST_ROOT_DEVICE_NAME = '/dev/sdf'


def update_ami(aws_svc, enc_svc_class, values, instance_config=None):
    encrypted_guest = None
    updater = None
    new_mv_vol_id = None
    temp_sg_id = None
    snap_id = None

    if instance_config is None:
        instance_config = InstanceConfig(mode=INSTANCE_UPDATER_MODE)

    try:
        instance_config.brkt_config['status_port'] = values.status_port

        log.info("Starting update of %s with %s", values.ami,
                 values.encryptor_ami)

        # Step 1. Launch encrypted guest AMI
        # Use 'updater' mode to avoid chain loading the guest
        # automatically. We just want this AMI/instance up as the
        # base to create a new AMI and preserve license
        # information embedded in the guest AMI

        description = DESCRIPTION_GUEST_CREATOR % {'image_id': values.ami}
        encrypted_guest = aws_svc.run_instance(
            values.ami,
            instance_type=values.guest_instance_type,
            ebs_optimized=False,
            subnet_id=values.subnet_id,
            user_data=json.dumps(instance_config.brkt_config),
            name=NAME_GUEST_CREATOR,
            description=description)
        encrypted_guest = wait_for_instance(aws_svc, encrypted_guest.id)
        mv_root_device_name = encrypted_guest.root_device_name

        log.info("Launched encrypted guest %s", encrypted_guest.id)

        # Step 2. Create a disk device of the root file system of the
        # encrypted guest's root disk by making a snapshot of the
        # root disk of the instance just launched. This disk will have
        # the metavisor on it.  Use gp2 for fast burst I/O.

        snap = snapshot_root_volume(aws_svc, encrypted_guest, values.ami)
        snap_id, snap_dev, snap_size, snap_type, snap_iops = snap

        log.info("Created snapshot %s of encrypted guest root", snap_id)

        # Step 3. Run updater in same zone as guest so we can swap
        # volumes.  Attach the snapshot as an additional disk.

        guest_encrypted_root = boto3_device.make_device(
            device_name='/dev/sdf',
            volume_type='gp2',
            snapshot_id=snap_id,
            delete_on_termination=True)

        # If the user didn't specify a security group, create a temporary
        # security group that allows brkt-cli to get status from the updater.
        run_instance = aws_svc.run_instance
        if not values.security_group_ids:
            vpc_id = None
            if values.subnet_id:
                subnet = aws_svc.get_subnet(values.subnet_id)
                vpc_id = subnet.vpc_id
            temp_sg_id = create_encryptor_security_group(
                aws_svc, vpc_id=vpc_id, status_port=values.status_port).id
            values.security_group_ids = [temp_sg_id]

            # Wrap with a retry, to handle eventual consistency issues with
            # the newly-created group.
            run_instance = aws_svc.retry(
                aws_svc.run_instance,
                error_code_regexp='InvalidGroup\.NotFound')

        updater = run_instance(
            values.encryptor_ami,
            instance_type=values.updater_instance_type,
            user_data=instance_config.make_userdata(),
            ebs_optimized=False,
            subnet_id=values.subnet_id,
            placement=encrypted_guest.placement,
            security_group_ids=values.security_group_ids,
            block_device_mappings=[guest_encrypted_root],
            name=NAME_METAVISOR_UPDATER,
            description=DESCRIPTION_METAVISOR_UPDATER)
        updater = wait_for_instance(aws_svc, updater.id)

        log.info("Launched updater %s with snapshot %s", updater.id, snap_id)

        # Enable ENA if Metavisor supports it.
        updater_ena_support = aws_service.has_ena_support(updater)
        guest_ena_support = aws_service.has_ena_support(encrypted_guest)
        log.debug(
            'ENA support: updater=%s, guest=%s',
            updater_ena_support,
            guest_ena_support
        )
        if updater_ena_support and not guest_ena_support:
            aws_svc.modify_instance_attribute(
                encrypted_guest.id,
                'enaSupport',
                'True'
            )

        host_ips = []
        if updater.public_ip_address:
            host_ips.append(updater.public_ip_address)
        if updater.private_ip_address:
            host_ips.append(updater.private_ip_address)
            log.info('Adding %s to NO_PROXY environment variable' %
                     updater.private_ip_address)
            if os.environ.get('NO_PROXY'):
                os.environ['NO_PROXY'] += "," + \
                    updater.private_ip_address
            else:
                os.environ['NO_PROXY'] = updater.private_ip_address

        # Step 4. Wait for the updater to complete.
        enc_svc = enc_svc_class(host_ips, port=values.status_port)
        log.info('Waiting for updater service on %s (port %s on %s)',
                 updater.id, enc_svc.port, ', '.join(host_ips))
        try:
            wait_for_encryptor_up(enc_svc, Deadline(600))
        except:
            log.error('Unable to connect to encryptor instance.')
            raise
        try:
            wait_for_encryption(enc_svc)
        except Exception as e:
            # Stop the updater instance, to make the console log available.
            stop_and_wait(aws_svc, updater.id)
            log_exception_console(aws_svc, e, updater.id)
            raise

        single_disk = encryptor_did_single_disk(enc_svc)

        aws_svc.stop_instance(updater.id)
        updater = wait_for_instance(aws_svc, updater.id, state="stopped")

        guest_bdm = encrypted_guest.block_device_mappings
        updater_bdm = updater.block_device_mappings
        new_bdm = list()

        # Step 5. Create block device mappings for the new image.  Preserve
        # volume properties that may get reset to their defaults while
        # updating block device mappings.
        for d in guest_bdm:
            new_dev = boto3_device.make_device_for_image(d)
            name = d['DeviceName']
            # Preserve volume type
            if name == snap_dev:
                vol_type = snap_type
                vol_iops = snap_iops
            else:
                vol = aws_svc.get_volume(d['Ebs']['VolumeId'])
                vol_type = vol.volume_type
                vol_iops = vol.iops
            new_dev['Ebs']['VolumeType'] = vol_type
            # io1 volumes must have the Iops attribute set
            if vol_type == 'io1':
                new_dev['Ebs']['Iops'] = vol_iops
            if name == mv_root_device_name:
                new_dev['Ebs']['DeleteOnTermination'] = True
            new_bdm.append(new_dev)

        if single_disk:
            # Step 6. Detach the Metavisor root from the updater instance.
            log.info('Detaching boot volume from %s', updater.id)
            new_mv_dev = boto3_device.get_device(updater_bdm,
                                                 GUEST_ROOT_DEVICE_NAME)
            new_mv_vol_id = new_mv_dev['Ebs']['VolumeId']
            aws_svc.detach_volume(new_mv_vol_id, instance_id=updater.id,
                                  force=True)

            # Step 7. Attach new boot disk to guest instance.
            log.info('Attaching new metavisor boot disk %s to %s',
                     new_mv_vol_id, encrypted_guest.id)
            aws_svc.attach_volume(new_mv_vol_id, encrypted_guest.id,
                                  mv_root_device_name)
            encrypted_guest = wait_for_volume_attached(aws_svc,
                                                       encrypted_guest.id,
                                                       mv_root_device_name)

            # Step 8. Create new AMI.
            log.info("Creating new AMI")
            guest_image = aws_svc.get_image(values.ami)
            image = aws_svc.create_image(encrypted_guest.id,
                                         values.encrypted_ami_name,
                                         description=guest_image.description,
                                         no_reboot=True,
                                         block_device_mappings=new_bdm)
            image = wait_for_image(aws_svc, image.id)
        else:
            # Step 6. Detach the Metavisor root from the updater instance.
            log.info('Detaching boot volume from %s', updater.id)
            new_mv_dev = boto3_device.get_device(updater_bdm,
                                                 MV_ROOT_DEVICE_NAME)
            new_mv_vol_id = new_mv_dev['Ebs']['VolumeId']
            aws_svc.detach_volume(new_mv_vol_id, instance_id=updater.id,
                                  force=True)

            # Step 7. Attach new boot disk to guest instance.
            log.info('Attaching new metavisor boot disk %s to %s',
                     new_mv_vol_id, encrypted_guest.id)
            aws_svc.attach_volume(new_mv_vol_id, encrypted_guest.id,
                                  mv_root_device_name)
            encrypted_guest = wait_for_volume_attached(aws_svc,
                                                       encrypted_guest.id,
                                                       mv_root_device_name)

            # Step 8. Create new AMI.
            log.info("Creating new AMI")
            guest_image = aws_svc.get_image(values.ami)
            image = aws_svc.create_image(encrypted_guest.id,
                                         values.encrypted_ami_name,
                                         description=guest_image.description,
                                         no_reboot=True,
                                         block_device_mappings=new_bdm)
            image = wait_for_image(aws_svc, image.id)

            # Step 9. Tag the snapshots and image that we just created.
            guest_dev = boto3_device.get_device(image.block_device_mappings,
                                                GUEST_ROOT_DEVICE_NAME)
            aws_svc.create_tags(guest_dev['Ebs']['SnapshotId'],
                                name=NAME_ENCRYPTED_ROOT_SNAPSHOT)

        # Step 9. Tag the snapshots and image that we just created.
        mv_root_dev = boto3_device.get_device(image.block_device_mappings,
                                              mv_root_device_name)
        if mv_root_dev:
            aws_svc.create_tags(mv_root_dev['Ebs']['SnapshotId'],
                                name=NAME_METAVISOR_ROOT_SNAPSHOT)
        aws_svc.create_tags(image.id)
        return image.id

    finally:
        if snap_id:
            aws_svc.delete_snapshot(snap_id)

        instance_ids = set()
        volume_ids = set()
        sg_ids = set()

        if encrypted_guest:
            instance_ids.add(encrypted_guest.id)
        if updater:
            instance_ids.add(updater.id)
        if new_mv_vol_id:
            volume_ids.add(new_mv_vol_id)
        if temp_sg_id:
            sg_ids.add(temp_sg_id)

        clean_up(aws_svc,
                 instance_ids=instance_ids,
                 volume_ids=volume_ids,
                 security_group_ids=sg_ids)
