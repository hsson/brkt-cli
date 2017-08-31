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
Create an Bracket wrapped based on an existing unencrypted AMI.

Overview of the process:
    * Obtain the Bracket (metavisor) image to be used
    * Obtain the root volume snapshot of the guest image
    * When lacking "create volume" permissions on the guest image
        create a local snapshot of the guest image
    * Configure the Bracket image to be launched with the guest
        root volume attached at /dev/sdf
    * Pass appropriate user-data to the Bracket image to indicate
        that the guest volume is unencrypted
    * Launch the Bracket image

Before running brkt encrypt-ami, set the AWS_ACCESS_KEY_ID and
AWS_SECRET_ACCESS_KEY environment variables, like you would when
running the AWS command line utility.
"""

import logging

from brkt_cli.user_data import gzip_user_data

from brkt_cli.aws import aws_service, boto3_device
from brkt_cli.aws.aws_service import (
    EBS_OPTIMIZED_INSTANCES, wait_for_instance, clean_up)
from brkt_cli.instance_config import InstanceConfig
from brkt_cli.util import make_nonce, append_suffix
from brkt_cli.validation import ValidationError

# End user-visible terminology.  These are resource names and descriptions
# that the user will see in his or her EC2 console.

# Security group names
NAME_INSTANCE_SECURITY_GROUP = 'Bracket Wrapped %(nonce)s'
DESCRIPTION_INSTANCE_SECURITY_GROUP = (
    "Allows SSH access to the Bracket wrapped instance.")

NAME_WRAPPED_IMAGE_SUFFIX = ' (wrapped %(nonce)s)'

INSTANCE_NAME_MAX_LENGTH = 128

log = logging.getLogger(__name__)


def get_wrapped_suffix():
    """ Return a suffix that will be appended to the wrapped instance name.
    The suffix is in the format "(wrapped 787ace7a)".
    """
    return NAME_WRAPPED_IMAGE_SUFFIX % {'nonce': make_nonce()}


def get_name_from_image(image):
    name = append_suffix(
        image.name,
        get_wrapped_suffix(),
        max_length=INSTANCE_NAME_MAX_LENGTH
    )
    return name


def create_instance_security_group(aws_svc, vpc_id=None):
    """ Creates a default security group to allow SSH access. This ensures
    that even if a security group is not specified in the arguments, the
    user can SSH in to the launched instance.
    """
    sg_name = NAME_INSTANCE_SECURITY_GROUP % {'nonce': make_nonce()}
    sg_desc = DESCRIPTION_INSTANCE_SECURITY_GROUP
    sg = aws_svc.create_security_group(sg_name, sg_desc, vpc_id=vpc_id)
    log.info('Created security group with id %s', sg.id)
    try:
        aws_svc.authorize_security_group_ingress(sg.id, port=22)
    except Exception as e:
        log.error('Failed adding security group rule to %s: %s', sg.id, e)
        clean_up(aws_svc, security_group_ids=[sg.id])

    aws_svc.create_tags(sg.id, name=sg_name, description=sg_desc)
    return sg


def _get_metavisor_root_device(aws_svc, metavisor_ami):
    # Get the Metavisor root snapshot.
    mv_image = aws_svc.get_image(metavisor_ami)
    mv_image_root_dev = boto3_device.get_device(
        mv_image.block_device_mappings, mv_image.root_device_name)

    # Verify that we have access to the Metavisor root snapshot.
    mv_root_snapshot_id = mv_image_root_dev['Ebs']['SnapshotId']
    aws_svc.get_snapshot(mv_root_snapshot_id)

    return mv_image_root_dev


def launch_wrapped_image(aws_svc, image_id, metavisor_ami,
                         wrapped_instance_name=None, subnet_id=None,
                         security_group_ids=None, instance_type='m4.large',
                         instance_config=None, iam=None):
    # If the guest already has /dev/sdf mounted, don't try to put the guest
    # root there.
    guest_image = aws_svc.get_image(image_id)
    bdm = list(guest_image.block_device_mappings)
    if boto3_device.get_device(bdm, '/dev/sdf'):
        raise ValidationError(
            'Cannot wrap %s because it has a block device at /dev/sdf' %
            image_id
        )

    # Verify that we have access to the Metavisor AMI and snapshot before
    # launching the guest instance.
    _get_metavisor_root_device(aws_svc, metavisor_ami)

    if not wrapped_instance_name:
        wrapped_instance_name = get_name_from_image(guest_image)

    instance = None
    temp_sg = None
    completed = False

    try:
        log.info('Running guest instance.')
        if not security_group_ids:
            vpc_id = None
            if subnet_id:
                subnet = aws_svc.get_subnet(subnet_id)
                vpc_id = subnet.vpc_id
            temp_sg = create_instance_security_group(
                aws_svc, vpc_id=vpc_id)
            security_group_ids = [temp_sg.id]

        instance = aws_svc.run_instance(
            image_id,
            subnet_id=subnet_id,
            instance_type=instance_type,
            ebs_optimized=instance_type in EBS_OPTIMIZED_INSTANCES,
            security_group_ids=security_group_ids,
            name=wrapped_instance_name,
            instance_profile_name=iam
        )

        wait_for_instance(aws_svc, instance.id)
        instance = wrap_instance(
            aws_svc, instance.id, metavisor_ami, instance_config)
        completed = True
    finally:
        if not completed:
            sg_ids = []
            if temp_sg:
                sg_ids.append(temp_sg.id)
            instance_ids = []
            if instance:
                instance_ids.append(instance.id)

            clean_up(
                aws_svc,
                instance_ids=instance_ids,
                security_group_ids=sg_ids
            )

    return instance


def wrap_instance(aws_svc, instance_id, metavisor_ami, instance_config=None):
    instance = aws_svc.get_instance(instance_id)

    # If the guest already has /dev/sdf mounted, don't try to put the guest
    # root there.
    if boto3_device.get_device(instance.block_device_mappings, '/dev/sdf'):
        raise ValidationError(
            'Cannot wrap %s because it has a block device at /dev/sdf' %
            instance_id
        )

    mv_image_root_dev = _get_metavisor_root_device(aws_svc, metavisor_ami)
    guest_root_vol = None
    mv_root_vol = None
    completed = False

    try:
        aws_svc.stop_instance(instance.id)
        instance = wait_for_instance(aws_svc, instance.id, state='stopped')

        if instance_config is None:
            instance_config = InstanceConfig()
        instance_config.brkt_config['allow_unencrypted_guest'] = True
        user_data = instance_config.make_userdata()

        aws_svc.modify_instance_attribute(
            instance.id, 'userData', gzip_user_data(user_data))

        log.info('Creating Metavisor root volume.')
        mv_root_vol = aws_svc.create_volume(
            size=mv_image_root_dev['Ebs']['VolumeSize'],
            zone=instance.placement['AvailabilityZone'],
            snapshot_id=mv_image_root_dev['Ebs']['SnapshotId'],
            volume_type='gp2'
        )

        log.info(
            'Moving guest root volume from %s to /dev/sdf.',
            instance.root_device_name
        )
        guest_root_dev = boto3_device.get_device(
            instance.block_device_mappings, instance.root_device_name)
        guest_root_vol = aws_svc.detach_volume(
            guest_root_dev['Ebs']['VolumeId'], instance.id)
        guest_root_vol = aws_service.wait_for_volume(
            aws_svc, guest_root_vol.id)
        aws_svc.attach_volume(guest_root_vol.id, instance.id, '/dev/sdf')

        log.info('Attaching Metavisor root volume.')
        mv_root_vol = aws_service.wait_for_volume(aws_svc, mv_root_vol.id)
        aws_svc.attach_volume(
            mv_root_vol.id, instance.id, instance.root_device_name)

        log.info('Waiting for Metavisor and guest root volumes to attach.')
        aws_service.wait_for_volume_attached(
            aws_svc, instance.id, instance.root_device_name)
        aws_service.wait_for_volume_attached(aws_svc, instance.id, '/dev/sdf')

        # Create guest and metavisor device mappings to be deleted on termination
        guest_device = boto3_device.make_device(
            device_name='/dev/sdf',
            delete_on_termination=True
        )
        metavisor_device = boto3_device.make_device(
            device_name=instance.root_device_name,
            delete_on_termination=True
        )

        log.info('Starting wrapped instance.')
        instance = aws_svc.start_instance(instance.id)
        # Re-attached volumes lose their DeleteOnTermination Settings
        # Modify instance attributes to mark the guest root and
        # metavisor volumes to get terminated on instance termination
        aws_svc.modify_instance_attribute(
            instance.id, 'blockDeviceMappings',
            [metavisor_device, guest_device]
        )
        completed = True
    finally:
        if not completed:
            volume_ids = []
            if mv_root_vol:
                volume_ids.append(mv_root_vol.id)
            if guest_root_vol:
                volume_ids.append(guest_root_vol.id)

            clean_up(
                aws_svc,
                volume_ids=volume_ids
            )

    log.info('Done.')
    return instance
