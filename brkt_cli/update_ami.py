# Copyright 2015 Bracket Computing, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
# https://github.com/brkt/brkt-sdk-java/blob/master/LICENSE
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

import logging
import json

from boto.ec2.blockdevicemapping import EBSBlockDeviceType

from brkt_cli import encryptor_service
from brkt_cli.util import Deadline

from encrypt_ami import (
    create_encryptor_security_group,
    log_exception_console,
    terminate_instance,
    wait_for_instance,
    wait_for_snapshots,
    wait_for_volume,
    wait_for_encryptor_up,
    wait_for_encryption,
    DESCRIPTION_GUEST_CREATOR,
    DESCRIPTION_METAVISOR_UPDATER,
    NAME_GUEST_CREATOR,
    NAME_METAVISOR_UPDATER,
    NAME_METAVISOR_GRUB_SNAPSHOT,
    NAME_METAVISOR_ROOT_SNAPSHOT,
    NAME_METAVISOR_LOG_SNAPSHOT,
)

log = logging.getLogger(__name__)


def update_ami(aws_svc, encrypted_ami, updater_ami,
               encrypted_ami_name, subnet_id=None, security_group_ids=None):
    encrypted_guest = None
    updater = None
    mv_root_id = None
    temp_sg_id = None
    tids = set()
    try:
        guest_image = aws_svc.get_image(encrypted_ami)

        # Step 1. Launch encrypted guest AMI
        # Use 'updater' mode to avoid chain loading the guest
        # automatically. We just want this AMI/instance up as the
        # base to create a new AMI and preserve license
        # information embedded in the guest AMI
        log.info("Launching encrypted guest/updater")
        user_data = json.dumps({'brkt': { 'solo_mode': 'updater'}})

        if not security_group_ids:
            vpc_id = None
            if subnet_id:
                subnet = aws_svc.get_subnet(subnet_id)
                vpc_id = subnet.vpc_id
            temp_sg_id = create_encryptor_security_group(
                aws_svc, vpc_id=vpc_id).id
            security_group_ids = [temp_sg_id]

        encrypted_guest = aws_svc.run_instance(encrypted_ami,
                    instance_type="m3.medium",
                    ebs_optimized=False,
                    security_group_ids=security_group_ids,
                    user_data=user_data)
        aws_svc.create_tags(
            encrypted_guest.id,
            name=NAME_GUEST_CREATOR,
            description=DESCRIPTION_GUEST_CREATOR % {'image_id': encrypted_ami}
        )
        updater = aws_svc.run_instance(updater_ami,
                    instance_type="m3.medium",
                    user_data=user_data,
                    ebs_optimized=False,
                    security_group_ids=security_group_ids)
        aws_svc.create_tags(
            updater.id,
            name=NAME_METAVISOR_UPDATER,
            description=DESCRIPTION_METAVISOR_UPDATER,
        )
        wait_for_instance(aws_svc, encrypted_guest.id, state="running")
        log.info("Launched guest: %s Updater: %s" %
             (encrypted_guest.id, updater.id)
        )

        # Step 2. Wait for the updater to finish and stop the instances
        aws_svc.stop_instance(encrypted_guest.id)

        wait_for_instance(aws_svc, updater.id, state="running")
        updater.update()
        host_ip = updater.ip_address
        enc_svc = encryptor_service.EncryptorService(host_ip)
        log.info("Waiting for updater service on %s" % (host_ip,))
        wait_for_encryptor_up(enc_svc, Deadline(600))
        try:
            wait_for_encryption(enc_svc)
        except Exception as e:
            log_exception_console(aws_svc, e, updater.id)
            raise e

        aws_svc.stop_instance(updater.id)
        wait_for_instance(aws_svc, encrypted_guest.id, state="stopped")
        wait_for_instance(aws_svc, updater.id, state="stopped")
        encrypted_guest.update()

        guest_bdm = encrypted_guest.block_device_mapping
        updater_bdm = updater.block_device_mapping

        # Step 3. Detach old BSD drive(s) and delete from encrypted guest
        if guest_image.virtualization_type == 'paravirtual':
            d_list = ['/dev/sda1', '/dev/sda2', '/dev/sda3']
        else:
            d_list = ['/dev/sda1']
        for d in d_list:
            log.info("Detaching old metavisor disk: %s from %s" %
                (guest_bdm[d].volume_id, encrypted_guest.id))
            aws_svc.detach_volume(guest_bdm[d].volume_id,
                    instance_id=encrypted_guest.id,
                    force=True
            )
            aws_svc.delete_volume(guest_bdm[d].volume_id)

        zone = encrypted_guest.placement

        # Step 4. Snapshot MV volume(s)
        log.info("Creating snapshots")
        if guest_image.virtualization_type == 'paravirtual':
            snap_boot = aws_svc.create_snapshot(
                updater_bdm['/dev/sda1'].volume_id,
                name=NAME_METAVISOR_GRUB_SNAPSHOT
            )
            snap_root = aws_svc.create_snapshot(
                updater_bdm['/dev/sda2'].volume_id,
                name=NAME_METAVISOR_ROOT_SNAPSHOT
            )
            snap_log = aws_svc.create_snapshot(
                updater_bdm['/dev/sda3'].volume_id,
                name=NAME_METAVISOR_LOG_SNAPSHOT
            )
            wait_for_snapshots(aws_svc, snap_boot.id,
                               snap_root.id, snap_log.id
            )
            dev_root = EBSBlockDeviceType(volume_type='gp2',
                        snapshot_id=snap_root.id,
                        delete_on_termination=True)
            dev_log = EBSBlockDeviceType(volume_type='gp2',
                        snapshot_id=snap_log.id,
                        delete_on_termination=True)
            guest_bdm['/dev/sda2'] = dev_root
            guest_bdm['/dev/sda3'] = dev_log
        else:
            snap_boot = aws_svc.create_snapshot(
                updater_bdm['/dev/sda1'].volume_id,
                name=NAME_METAVISOR_ROOT_SNAPSHOT
            )
            wait_for_snapshots(aws_svc, snap_boot.id)

        # Step 5. Create new MV boot disk from snapshot
        log.info("Creating new metavisor boot from %s" % (snap_boot.id,))
        new_vol = aws_svc.create_volume(snap_boot.volume_size, zone,
            snapshot=snap_boot.id,
            volume_type="gp2",
            encrypted=False,
        )
        mv_root_id = new_vol.id
        wait_for_volume(aws_svc, new_vol, state="available")

        # Step 6. Attach new boot disk to guest instance
        log.info("Attaching new MV boot disk: %s to %s" %
            (mv_root_id, encrypted_guest.id)
        )
        aws_svc.attach_volume(mv_root_id, encrypted_guest.id, '/dev/sda1')
        encrypted_guest.update()
        guest_bdm['/dev/sda1'] = \
            encrypted_guest.block_device_mapping['/dev/sda1']
        guest_bdm['/dev/sda1'].delete_on_termination = True

        # Step 7. Create new AMI. Preserve billing/license info
        log.info("Creating new AMI")
        ami = aws_svc.create_image(
            encrypted_guest.id,
            encrypted_ami_name,
            description=guest_image.description,
            no_reboot=True,
            block_device_mapping=guest_bdm
        )
        log.info("Created %s" % (ami,))
        # Step 8. Clean up
        terminate_instance(aws_svc, encrypted_guest.id, 'guest', tids)
        terminate_instance(aws_svc, updater.id, 'updater', tids)
        encrypted_guest = None
        updater = None
        aws_svc.delete_volume(mv_root_id)
        mv_root_id = None
        if temp_sg_id:
            aws_svc.delete_security_group(temp_sg_id)
        temp_sg_id = None
        return 0
    except:
        log.exception('Upgrade Failed')
    finally:
        if encrypted_guest:
            terminate_instance(aws_svc, encrypted_guest.id, 'guest', tids)
        if updater:
            terminate_instance(aws_svc, updater.id, 'updater', tids)
        if mv_root_id:
            aws_svc.delete_volume(mv_root_id)
        if temp_sg_id:
            aws_svc.delete_security_group(temp_sg_id)