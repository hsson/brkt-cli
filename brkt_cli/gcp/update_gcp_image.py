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

from brkt_cli.encryptor_service import (
    encryptor_did_single_disk,
    wait_for_encryption,
    wait_for_encryptor_up
)
from brkt_cli.gcp.gcp_service import gcp_metadata_from_userdata
from brkt_cli.util import Deadline

"""
Create an encrypted GCP image (with new metavisor) based
on an existing encrypted GCP image.
"""

log = logging.getLogger(__name__)


def update_gcp_image(gcp_svc, enc_svc_cls, values, encrypted_image_name,
                     instance_config):
    instance_name = 'brkt-updater-' + gcp_svc.get_session_id()
    updater = instance_name + '-metavisor'
    updater_launched = False
    snapshot_created = False
    try:
        # Create disk from encrypted guest snapshot.
        encrypted_image_disk = instance_name + '-root'
        gcp_svc.disk_from_image(values.zone, values.image,
                                encrypted_image_disk)
        gcp_svc.wait_for_disk(values.zone, encrypted_image_disk)

        log.info("Launching encrypted updater")
        user_data = gcp_metadata_from_userdata(instance_config.make_userdata())
        disks = [gcp_svc.get_disk(values.zone, encrypted_image_disk)]
        gcp_svc.run_instance(values.zone,
                             updater,
                             values.encryptor_image,
                             network=values.network,
                             subnet=values.subnetwork,
                             disks=disks,
                             delete_boot=False,
                             metadata=user_data,
                             tags=values.gcp_tags)
        host_ips = []
        ip = gcp_svc.get_instance_ip(updater, values.zone)
        if ip:
            host_ips.append(ip)
        pvt_ip = gcp_svc.get_private_ip(updater, values.zone)
        if pvt_ip:
            host_ips.append(pvt_ip)
        updater_launched = True
        enc_svc = enc_svc_cls(host_ips, port=values.status_port)

        # wait for updater to finish and guest root disk
        wait_for_encryptor_up(enc_svc, Deadline(600))
        log.info('Waiting for updater service on %s (%s:%s)',
                 updater, ip, enc_svc.port)
        try:
            wait_for_encryption(enc_svc)
        except:
            raise

        single_disk = encryptor_did_single_disk(enc_svc)

        # delete updater instance
        log.info('Deleting updater instance')
        gcp_svc.delete_instance(values.zone, updater)
        updater_launched = False

        if not single_disk:
            # Create disk from encrypted guest snapshot. This disk
            # won't be altered. It will be re-snapshotted and paired
            # with the new encryptor image.
            encrypted_guest_disk = instance_name + '-guest'
            gcp_svc.disk_from_snapshot(values.zone, values.image,
                                       encrypted_guest_disk)
            gcp_svc.wait_for_disk(values.zone, encrypted_guest_disk)
            log.info("Creating new snapshot of encrypted guest disk")
            gcp_svc.create_snapshot(values.zone, encrypted_guest_disk,
                                    encrypted_image_name)
            snapshot_created = True
            gcp_svc.wait_for_detach(values.zone, updater)
            image_disk = updater
        else:
            gcp_svc.wait_for_detach(values.zone, encrypted_image_disk)
            image_disk = encrypted_image_disk

        # create image from mv root disk and snapshot
        # encrypted guest root disk
        log.info("Creating updated guest image")
        gcp_svc.create_gcp_image_from_disk(values.zone, encrypted_image_name,
                                           image_disk)
        gcp_svc.wait_image(encrypted_image_name)
        if not single_disk:
            gcp_svc.wait_snapshot(encrypted_image_name)
    except:
        if updater_launched:
            f = gcp_svc.write_serial_console_file(values.zone, updater)
            if f:
                log.info('Update failed. Writing console to %s' % f)
        log.info("Update failed. Cleaning up")
        if snapshot_created:
            gcp_svc.delete_snapshot(encrypted_image_name)
        if not values.cleanup:
            return
        gcp_svc.cleanup(values.zone, values.encryptor_image,
                        values.keep_encryptor)
        raise
    finally:
        if not values.cleanup:
            return
        gcp_svc.cleanup(values.zone, values.encryptor_image,
                        values.keep_encryptor)
    return encrypted_image_name
