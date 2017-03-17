#!/usr/bin/env python

import logging

from googleapiclient import errors


log = logging.getLogger(__name__)


def wrap_guest_image(gcp_svc, image_id, encryptor_image,
                     zone, metadata, instance_name=None,
                     image_project=None, image_file=None,
                     image_bucket=None, network=None, subnet=None,
                     cleanup=True, ssd_disks=0, gcp_tags=None):
    try:
        keep_encryptor = True
        if not encryptor_image:
            log.info('Retrieving encryptor image from GCE bucket')
            try:
                encryptor_image = gcp_svc.get_latest_encryptor_image(zone,
                    image_bucket, image_file=image_file)
                keep_encryptor = False
            except errors.HttpError as e:
                encryptor_image = None
                log.exception('GCE API call to retrieve image failed')
                return

        if not instance_name:
            instance_name = 'brkt-guest-' + gcp_svc.get_session_id()
            guest_disk_name = instance_name + '-unencrypted'
        else:
            guest_disk_name = instance_name + gcp_svc.get_session_id()
        
        gcp_svc.disk_from_image(zone, image_id, guest_disk_name, image_project)
        log.info('Waiting for guest root disk to become ready')
        gcp_svc.wait_for_detach(zone, guest_disk_name)

        guest_disk = gcp_svc.get_disk(zone, guest_disk_name)
        guest_disk['autoDelete'] = True
        disks = [guest_disk]
        for x in range(ssd_disks):
            ssd_disk = gcp_svc.create_ssd_disk(zone)
            disks.append(ssd_disk)

        log.info('Launching wrapped guest image')
        gcp_svc.run_instance(zone=zone,
                             name=instance_name,
                             image=encryptor_image,
                             network=network,
                             subnet=subnet,
                             disks=disks,
                             delete_boot=True,
                             metadata=metadata,
                             tags=gcp_tags)
        gcp_svc.wait_instance(instance_name, zone)
        log.info("Instance %s (%s) launched successfully" % (instance_name,
            gcp_svc.get_instance_ip(instance_name, zone)))
    except errors.HttpError as e:
        log.exception('GCE API request failed: {}'.format(e.message))
    finally:
        if not cleanup:
            log.info("Not cleaning up")
        else:
            if not keep_encryptor and encryptor_image:
                log.info('Deleting encryptor image %s' % encryptor_image)
                gcp_svc.delete_image(encryptor_image)

    return instance_name


