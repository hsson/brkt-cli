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
    ENCRYPTOR_STATUS_PORT,
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


def update_gcp_image(gcp_svc, enc_svc_cls, image_id, encryptor_image,
                     encrypted_image_name, zone, instance_config,
                     keep_encryptor=False, image_file=None,
                     image_bucket=None, network=None,
                     subnetwork=None, status_port=ENCRYPTOR_STATUS_PORT,
                     cleanup=True, gcp_tags=None):
    snap_created = None
    instance_name = 'brkt-updater-' + gcp_svc.get_session_id()
    updater = instance_name + '-metavisor'
    updater_launched = False
    try:
        # create image from file in GCS bucket
        log.info('Retrieving encryptor image from GCS bucket')
        if not encryptor_image:
            encryptor_image = gcp_svc.get_latest_encryptor_image(zone,
                image_bucket, image_file=image_file)
        else:
            # Keep user provided encryptor image
            keep_encryptor = True

        encrypted_image_disk = instance_name + '-guest'

        # Create disk from encrypted guest snapshot. This disk
        # won't be altered. It will be re-snapshotted and paired
        # with the new encryptor image.
        gcp_svc.disk_from_snapshot(zone, image_id, encrypted_image_disk)
        gcp_svc.wait_for_disk(zone, encrypted_image_disk)
        log.info("Creating snapshot of encrypted image disk")
        gcp_svc.create_snapshot(zone, encrypted_image_disk, encrypted_image_name)
        snap_created = True

        log.info("Launching encrypted updater")
        user_data = gcp_metadata_from_userdata(instance_config.make_userdata())
        gcp_svc.run_instance(zone,
                             updater,
                             encryptor_image,
                             network=network,
                             subnet=subnetwork,
                             disks=[],
                             delete_boot=False,
                             metadata=user_data,
                             tags=gcp_tags)
        ip = gcp_svc.get_instance_ip(updater, zone)
        updater_launched = True
        enc_svc = enc_svc_cls([ip], port=status_port)

        # wait for updater to finish and guest root disk
        wait_for_encryptor_up(enc_svc, Deadline(600))
        log.info(
            'Waiting for updater service on %s (%s:%s)',
            updater, ip, enc_svc.port
        )
        try:
            wait_for_encryption(enc_svc)
        except:
            raise

        # delete updater instance
        log.info('Deleting updater instance')
        gcp_svc.delete_instance(zone, updater)
        updater_launched = False

        # wait for updater root disk
        gcp_svc.wait_for_detach(zone, updater)

        # create image from mv root disk and snapshot
        # encrypted guest root disk
        log.info("Creating updated metavisor image")
        gcp_svc.create_gcp_image_from_disk(zone, encrypted_image_name, updater)
        gcp_svc.wait_image(encrypted_image_name)
        gcp_svc.wait_snapshot(encrypted_image_name)
    except:
        if updater_launched:
            f = gcp_svc.write_serial_console_file(zone, updater)
            if f:
                log.info('Update failed. Writing console to %s' % f)
        log.info("Update failed. Cleaning up")
        if snap_created:
            gcp_svc.delete_snapshot(encrypted_image_name)
        if not cleanup:
            return
        gcp_svc.cleanup(zone, encryptor_image, keep_encryptor)
        raise
    finally:
        if not cleanup:
            return
        gcp_svc.cleanup(zone, encryptor_image, keep_encryptor)
    return encrypted_image_name
