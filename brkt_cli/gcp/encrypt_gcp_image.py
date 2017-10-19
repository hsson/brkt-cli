#!/usr/bin/env python

import httplib
import logging
import socket

from googleapiclient import errors

from brkt_cli.encryptor_service import (
    wait_for_encryption,
    wait_for_encryptor_up
)
from brkt_cli.gcp.gcp_service import gcp_metadata_from_userdata
from brkt_cli.util import (
    CRYPTO_GCM,
    Deadline,
    METAVISOR_DISK_SIZE,
    append_suffix,
    retry
)


log = logging.getLogger(__name__)


def setup_encryption(gcp_svc, values, encrypted_image_disk, instance_name):
    try:
        # Create disk from guest image.
        gcp_svc.disk_from_image(values.zone, values.image, instance_name,
                                values.image_project)
        log.info('Waiting for guest root disk to become ready')
        gcp_svc.wait_for_detach(values.zone, instance_name)
        guest_disk_size = gcp_svc.get_disk_size(values.zone, instance_name)

        # Create a blank disk. The size of which depends on the crypto
        # policy and whether we do single-disk encryption or not.
        encrypted_disk_size = guest_disk_size
        if values.crypto == CRYPTO_GCM:
            encrypted_disk_size *= 2
        if values.single_disk:
            encrypted_disk_size += METAVISOR_DISK_SIZE
        else:
            encrypted_disk_size += 1
        log.info('Creating a %sGB disk for the encrypted image',
                 encrypted_disk_size)
        gcp_svc.create_disk(values.zone, encrypted_image_disk,
                            encrypted_disk_size)

        #
        # Amazing but true - just attach a big drive to get more IOPS
        # to be shared by all volumes attached to this VM. We don't
        # use the dummy-iops drive but get to use it's IOPS for other
        # drives.
        #
        dummy_disk_size = 500
        log.info('Creating a %sGB dummy disk for better IOPS', dummy_disk_size)
        dummy_name = append_suffix(encrypted_image_disk, "-dummy-iops", 64)
        gcp_svc.create_disk(values.zone, dummy_name, dummy_disk_size)
    except:
        log.info('Encryption setup failed')
        raise


def do_encryption(gcp_svc, enc_svc_cls, values, encryptor, instance_name,
                  instance_config, encrypted_image_disk):
    log.info('Launching encryptor instance')
    dummy_name = append_suffix(encrypted_image_disk, "-dummy-iops", 64)
    disks = [gcp_svc.get_disk(values.zone, instance_name),
             gcp_svc.get_disk(values.zone, encrypted_image_disk),
             gcp_svc.get_disk(values.zone, dummy_name)]
    metadata = gcp_metadata_from_userdata(instance_config.make_userdata())
    gcp_svc.run_instance(zone=values.zone, name=encryptor,
                         image=values.encryptor_image, network=values.network,
                         subnet=values.subnetwork, disks=disks,
                         delete_boot=False, metadata=metadata,
                         tags=values.gcp_tags)

    try:
        host_ips = []
        ip = gcp_svc.get_instance_ip(encryptor, values.zone)
        if ip:
            host_ips.append(ip)
        pvt_ip = gcp_svc.get_private_ip(encryptor, values.zone)
        if pvt_ip:
            host_ips.append(pvt_ip)
        enc_svc = enc_svc_cls(host_ips, port=values.status_port)
        wait_for_encryptor_up(enc_svc, Deadline(600))
        log.info('Waiting for encryption service on %s (%s:%s)',
                 encryptor, ip, enc_svc.port)
        wait_for_encryption(enc_svc)
    except:
        f = gcp_svc.write_serial_console_file(values.zone, encryptor)
        if f:
            log.info('Encryption failed. Writing console to %s' % f)
        raise
    retry(function=gcp_svc.delete_instance, on=[httplib.BadStatusLine,
          socket.error, errors.HttpError])(values.zone, encryptor)


def create_image(gcp_svc, values, encrypted_image_disk, encrypted_image_name,
                 encryptor):
    try:
        if not values.single_disk:
            # Snapshot the encrypted guest disk
            log.info("Creating snapshot of encrypted image disk")
            gcp_svc.create_snapshot(values.zone, encrypted_image_disk,
                                    encrypted_image_name)
            root_disk = encryptor
        else:
            root_disk = encrypted_image_disk

        # Create image from the given root disk
        gcp_svc.wait_for_detach(values.zone, root_disk)

        log.info("Creating bracketized guest image")
        gcp_svc.create_gcp_image_from_disk(values.zone, encrypted_image_name,
                                           root_disk)
        gcp_svc.wait_image(encrypted_image_name)
        if not values.single_disk:
            gcp_svc.wait_snapshot(encrypted_image_name)
        log.info("Image %s successfully created!", encrypted_image_name)
    except:
        log.info('Image creation failed.')
        raise


def encrypt(gcp_svc, enc_svc_cls, values, encrypted_image_name,
            instance_config):
    try:
        instance_name = 'brkt-guest-' + gcp_svc.get_session_id()
        encryptor = instance_name + '-encryptor'
        encrypted_image_disk = 'encrypted-image-' + gcp_svc.get_session_id()

        # create guest root disk and blank disk to dd to
        setup_encryption(gcp_svc, values, encrypted_image_disk, instance_name)

        # run encryptor instance with avatar_creator as root,
        # customer image and blank disk
        do_encryption(gcp_svc, enc_svc_cls, values, encryptor, instance_name,
                      instance_config, encrypted_image_disk)

        # create image
        create_image(gcp_svc, values, encrypted_image_disk,
                     encrypted_image_name, encryptor)

        return encrypted_image_name
    except errors.HttpError as e:
        log.exception('GCP API request failed: {}'.format(e.message))
    finally:
        if not values.cleanup:
            log.info("Not cleaning up")
            return None
        log.info("Cleaning up")
        gcp_svc.cleanup(values.zone, values.encryptor_image,
                        values.keep_encryptor)
