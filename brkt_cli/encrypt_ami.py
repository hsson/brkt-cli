# Copyright 2015 Bracket Computing, Inc. All Rights Reserved.
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
Create an encrypted AMI based on an existing unencrypted AMI.

Overview of the process:
    * Start an instance based on the unencrypted guest AMI.
    * Stop that instance
    * Snapshot the root volume of the unencrypted instance.
    * Start a Bracket Encryptor instance.
    * Attach the unencrypted root volume to the Encryptor instance.
    * The Bracket Encryptor copies the unencrypted root volume to a new
        encrypted volume that's 2x the size of the original.
    * Detach the Bracket Encryptor root volume
    * Snapshot the Bracket Encryptor system volumes and the new encrypted
        root volume.
    * Attach the Bracket Encryptor root volume to the stopped guest instance
    * Create a new AMI based on the snapshots and stopped guest instance.
    * Terminate the Bracket Encryptor instance.
    * Terminate the original guest instance.
    * Delete the unencrypted snapshot.

Before running brkt encrypt-ami, set the AWS_ACCESS_KEY_ID and
AWS_SECRET_ACCESS_KEY environment variables, like you would when
running the AWS command line utility.
"""

import json
import os
import logging
import string
import tempfile
import time
import urllib2

from boto.exception import EC2ResponseError
from boto.ec2.blockdevicemapping import (
    BlockDeviceMapping,
    EBSBlockDeviceType,
)
from boto.ec2.instance import InstanceAttribute

from brkt_cli import encryptor_service
from brkt_cli.util import (
    BracketError,
    Deadline,
    make_nonce,
)

# End user-visible terminology.  These are resource names and descriptions
# that the user will see in his or her EC2 console.

# Guest instance names.
NAME_GUEST_CREATOR = 'Bracket guest'
DESCRIPTION_GUEST_CREATOR = \
    'Used to create an encrypted guest root volume from %(image_id)s'

# Updater instance
NAME_METAVISOR_UPDATER = 'Bracket Updater'
DESCRIPTION_METAVISOR_UPDATER = \
    'Used to upgrade existing encrypted AMI with latest metavisor'

# Security group names
NAME_ENCRYPTOR_SECURITY_GROUP = 'Bracket Encryptor %(nonce)s'
DESCRIPTION_ENCRYPTOR_SECURITY_GROUP = (
    "Allows access to the encryption service.")

# Encryptor instance names.
NAME_ENCRYPTOR = 'Bracket volume encryptor'
DESCRIPTION_ENCRYPTOR = \
    'Copies the root snapshot from %(image_id)s to a new encrypted volume'

# Snapshot names.
NAME_ORIGINAL_SNAPSHOT = 'Bracket encryptor original volume'
DESCRIPTION_ORIGINAL_SNAPSHOT = \
    'Original unencrypted root volume from %(image_id)s'
NAME_ENCRYPTED_ROOT_SNAPSHOT = 'Bracket encrypted root volume'
NAME_METAVISOR_ROOT_SNAPSHOT = 'Bracket system root'
NAME_METAVISOR_GRUB_SNAPSHOT = 'Bracket system GRUB'
NAME_METAVISOR_LOG_SNAPSHOT = 'Bracket system log'
DESCRIPTION_SNAPSHOT = 'Based on %(image_id)s'

# Volume names.
NAME_ORIGINAL_VOLUME = 'Original unencrypted root volume from %(image_id)s'
NAME_ENCRYPTED_ROOT_VOLUME = 'Bracket encrypted root volume'
NAME_METAVISOR_ROOT_VOLUME = 'Bracket system root'
NAME_METAVISOR_GRUB_VOLUME = 'Bracket system GRUB'
NAME_METAVISOR_LOG_VOLUME = 'Bracket system log'

# Tag names.
TAG_ENCRYPTOR = 'BrktEncryptor'
TAG_ENCRYPTOR_SESSION_ID = 'BrktEncryptorSessionID'
TAG_ENCRYPTOR_AMI = 'BrktEncryptorAMI'
TAG_DESCRIPTION = 'Description'

NAME_ENCRYPTED_IMAGE = '%(original_image_name)s %(encrypted_suffix)s'
NAME_ENCRYPTED_IMAGE_SUFFIX = ' (encrypted %(nonce)s)'
SUFFIX_ENCRYPTED_IMAGE = (
    ' - based on %(image_id)s, encrypted by Bracket Computing'
)
DEFAULT_DESCRIPTION_ENCRYPTED_IMAGE = \
    'Based on %(image_id)s, encrypted by Bracket Computing'

SLEEP_ENABLED = True
AMI_NAME_MAX_LENGTH = 128

BRACKET_ENVIRONMENT = "prod"
ENCRYPTOR_AMIS_URL = "http://solo-brkt-%s-net.s3.amazonaws.com/amis.json"
HVM_ENCRYPTOR_AMIS_URL = \
    "http://solo-brkt-%s-net.s3.amazonaws.com/hvm_amis.json"
ENCRYPTION_PROGRESS_TIMEOUT = 10 * 60  # 10 minutes

log = logging.getLogger(__name__)


# boto2 does not support this attribute, and this attribute needs to be
# queried for as metavisor does not support sriovNet
if 'sriovNetSupport' not in InstanceAttribute.ValidValues:
    InstanceAttribute.ValidValues.append('sriovNetSupport')


class SnapshotError(BracketError):
    pass


class InstanceError(BracketError):
    pass


class BracketEnvironment(object):
    def __init__(self):
        self.api_host = None
        self.api_port = None
        self.hsmproxy_host = None
        self.hsmproxy_port = None

    def __repr__(self):
        return '<BracketEnvironment api=%s:%d, hsmproxy=%s:%d>' % (
            self.api_host,
            self.api_port,
            self.hsmproxy_host,
            self.hsmproxy_port
        )


def get_default_tags(session_id, encryptor_ami):
    default_tags = {
        TAG_ENCRYPTOR: True,
        TAG_ENCRYPTOR_SESSION_ID: session_id,
        TAG_ENCRYPTOR_AMI: encryptor_ami
    }
    return default_tags


def _get_snapshot_progress_text(snapshots):
    elements = [
        '%s: %s' % (str(s.id), str(s.progress))
        for s in snapshots
    ]
    return ', '.join(elements)


def sleep(seconds):
    if SLEEP_ENABLED:
        time.sleep(seconds)


def wait_for_instance(
        aws_svc, instance_id, timeout=300, state='running'):
    """ Wait for up to timeout seconds for an instance to be in the
        'running' state.  Sleep for 2 seconds between checks.
    :return: The Instance object, or None if a timeout occurred
    :raises InstanceError if a timeout occurs or the instance unexpectedly
        goes into an error or terminated state
    """

    log.debug(
        'Waiting for %s, timeout=%d, state=%s',
        instance_id, timeout, state)

    deadline = Deadline(timeout)
    while not deadline.is_expired():
        instance = aws_svc.get_instance(instance_id)
        log.debug('Instance %s state=%s', instance.id, instance.state)
        if instance.state == state:
            return instance
        if instance.state == 'error':
            raise InstanceError(
                'Instance %s is in an error state.  Cannot proceed.' %
                instance_id
            )
        if state != 'terminated' and instance.state == 'terminated':
            raise InstanceError(
                'Instance %s was unexpectedly terminated.' % instance_id
            )
        sleep(2)
    raise InstanceError(
        'Timed out waiting for %s to be in the %s state' %
        (instance_id, state)
    )


def wait_for_volume(
        aws_svc, volume, timeout=300, state='available'):
    log.debug(
        'Waiting for %s, timeout=%d, state=%s',
        volume.id, timeout, state)

    deadline = Deadline(timeout)
    while not deadline.is_expired():
        volume = aws_svc.get_volume(volume.id)
        if volume.status == state:
            return volume
        sleep(2)
    raise InstanceError(
        'Timed out waiting for %s to be in the %s state' %
        (volume.id, state)
    )


def wait_for_encryptor_up(enc_svc, deadline):
    start = time.time()
    while not deadline.is_expired():
        if enc_svc.is_encryptor_up():
            log.debug(
                'Encryption service is up after %.1f seconds',
                time.time() - start
            )
            return
        sleep(5)
    raise BracketError(
        'Unable to contact encryptor instance at %s.' %
        ', '.join(enc_svc.hostnames)
    )


class EncryptionError(BracketError):
    def __init__(self, message):
        super(EncryptionError, self).__init__(message)
        self.console_output_file = None


class UnsupportedGuestError(BracketError):
    pass


class AWSPermissionsError(BracketError):
    pass


class InvalidNtpServerError(BracketError):
    pass


def wait_for_encryption(enc_svc,
                        progress_timeout=ENCRYPTION_PROGRESS_TIMEOUT):
    err_count = 0
    max_errs = 10
    start_time = time.time()
    last_log_time = start_time
    progress_deadline = Deadline(progress_timeout)
    last_progress = 0
    last_state = ''

    while err_count < max_errs:
        try:
            status = enc_svc.get_status()
            err_count = 0
        except Exception as e:
            log.warn("Failed getting encryption status: %s", e)
            log.warn("Retrying. . .")
            err_count += 1
            sleep(10)
            continue

        state = status['state']
        percent_complete = status['percent_complete']
        log.debug('state=%s, percent_complete=%d', state, percent_complete)

        # Make sure that encryption progress hasn't stalled.
        if progress_deadline.is_expired():
            raise EncryptionError(
                'Waited for encryption progress for longer than %s seconds' %
                progress_timeout
            )
        if percent_complete > last_progress or state != last_state:
            last_progress = percent_complete
            last_state = state
            progress_deadline = Deadline(progress_timeout)

        # Log progress once a minute.
        now = time.time()
        if now - last_log_time >= 60:
            if state == encryptor_service.ENCRYPT_INITIALIZING:
                log.info('Encryption process is initializing')
            else:
                state_display = 'Encryption'
                if state == encryptor_service.ENCRYPT_DOWNLOADING:
                    state_display = 'Download from S3'
                log.info(
                    '%s is %d%% complete', state_display, percent_complete)
            last_log_time = now

        if state == encryptor_service.ENCRYPT_SUCCESSFUL:
            log.info('Encrypted root drive created.')
            return
        elif state == encryptor_service.ENCRYPT_FAILED:
            failure_code = status.get('failure_code')
            log.debug('failure_code=%s', failure_code)
            if failure_code == \
                    encryptor_service.FAILURE_CODE_UNSUPPORTED_GUEST:
                raise UnsupportedGuestError(
                    'The specified AMI uses an unsupported operating system')
            if failure_code == encryptor_service.FAILURE_CODE_AWS_PERMISSIONS:
                raise AWSPermissionsError(
                    'The specified IAM profile has insufficient permissions')
            if failure_code == \
                    encryptor_service.FAILURE_CODE_INVALID_NTP_SERVERS:
                raise InvalidNtpServerError(
                    'Invalid NTP servers provided.')
            raise EncryptionError('Encryption failed')

        sleep(10)
    # We've failed to get encryption status for _max_errs_ consecutive tries.
    # Assume that the server has crashed.
    raise EncryptionError('Encryption service unavailable')


def get_encrypted_suffix():
    """ Return a suffix that will be appended to the encrypted image name.
    The suffix is in the format "(encrypted 787ace7a)".  The nonce portion of
    the suffix is necessary because Amazon requires image names to be unique.
    """
    return NAME_ENCRYPTED_IMAGE_SUFFIX % {'nonce': make_nonce()}


def append_suffix(name, suffix, max_length=None):
    """ Append the suffix to the given name.  If the appended length exceeds
    max_length, truncate the name to make room for the suffix.

    :return: The possibly truncated name with the suffix appended
    """
    if not suffix:
        return name
    if max_length:
        truncated_length = max_length - len(suffix)
        name = name[:truncated_length]
    return name + suffix


def get_encryptor_ami(region, hvm=False):
    bracket_env = os.getenv('BRACKET_ENVIRONMENT',
                            BRACKET_ENVIRONMENT)
    if not bracket_env:
        raise BracketError('No bracket environment found')
    if hvm:
        bucket_url = HVM_ENCRYPTOR_AMIS_URL % (bracket_env)
    else:
        bucket_url = ENCRYPTOR_AMIS_URL % (bracket_env)
    log.debug('Getting encryptor AMI list from %s', bucket_url)
    r = urllib2.urlopen(bucket_url)
    if r.getcode() not in (200, 201):
        raise BracketError(
            'Getting %s gave response: %s' % (bucket_url, r.text))
    resp_json = json.loads(r.read())
    ami = resp_json.get(region)
    if not ami:
        raise BracketError('No AMI for %s returned.' % region)
    return ami


def get_name_from_image(image):
    name = append_suffix(
        image.name,
        get_encrypted_suffix(),
        max_length=AMI_NAME_MAX_LENGTH
    )
    return name


def get_description_from_image(image):
    if image.description:
        suffix = SUFFIX_ENCRYPTED_IMAGE % {'image_id': image.id}
        description = append_suffix(
            image.description, suffix, max_length=255)
    else:
        description = DEFAULT_DESCRIPTION_ENCRYPTED_IMAGE % {
            'image_id': image.id
        }
    return description


def wait_for_image(amazon_svc, image_id):
    log.debug('Waiting for %s to become available.', image_id)
    for i in range(180):
        sleep(5)
        try:
            image = amazon_svc.get_image(image_id)
        except EC2ResponseError, e:
            if e.error_code == 'InvalidAMIID.NotFound':
                log.debug('AWS threw a NotFound, ignoring')
                continue
            else:
                log.warn('Unknown AWS error: %s', e)
        # These two attributes are optional in the response and only
        # show up sometimes. So we have to getattr them.
        reason = repr(getattr(image, 'stateReason', None))
        code = repr(getattr(image, 'code', None))
        log.debug("%s: %s reason: %s code: %s",
                  image.id, image.state, reason, code)
        if image.state == 'available':
            break
        if image.state == 'failed':
            raise BracketError('Image state became failed')
    else:
        raise BracketError(
            'Image failed to become available (%s)' % (image.state,))


def wait_for_snapshots(svc, *snapshot_ids):
    log.debug('Waiting for status "completed" for %s', str(snapshot_ids))
    last_progress_log = time.time()

    # Give AWS some time to propagate the snapshot creation.
    # If we create and get immediately, AWS may return 400.
    sleep(20)

    while True:
        snapshots = svc.get_snapshots(*snapshot_ids)
        log.debug('%s', {s.id: s.status for s in snapshots})

        done = True
        error_ids = []
        for snapshot in snapshots:
            if snapshot.status == 'error':
                error_ids.append(snapshot.id)
            if snapshot.status != 'completed':
                done = False

        if error_ids:
            # Get rid of unicode markers in error the message.
            error_ids = [str(id) for id in error_ids]
            raise SnapshotError(
                'Snapshots in error state: %s.  Cannot continue.' %
                str(error_ids)
            )
        if done:
            return

        # Log progress if necessary.
        now = time.time()
        if now - last_progress_log > 60:
            log.info(_get_snapshot_progress_text(snapshots))
            last_progress_log = now

        sleep(5)


def create_encryptor_security_group(aws_svc, vpc_id=None):
    sg_name = NAME_ENCRYPTOR_SECURITY_GROUP % {'nonce': make_nonce()}
    sg_desc = DESCRIPTION_ENCRYPTOR_SECURITY_GROUP
    sg = aws_svc.create_security_group(sg_name, sg_desc, vpc_id=vpc_id)
    log.info('Created temporary security group with id %s', sg.id)
    try:
        aws_svc.add_security_group_rule(
            sg.id, ip_protocol='tcp',
            from_port=encryptor_service.ENCRYPTOR_STATUS_PORT,
            to_port=encryptor_service.ENCRYPTOR_STATUS_PORT,
            cidr_ip='0.0.0.0/0')
    except Exception as e:
        log.error('Failed adding security group rule to %s: %s', sg.id, e)
        try:
            log.info('Cleaning up temporary security group %s', sg.id)
            aws_svc.delete_security_group(sg.id)
        except Exception as e2:
            log.warn('Failed deleting temporary security group: %s', e2)
        raise e

    aws_svc.create_tags(sg.id)
    return sg


def add_brkt_env_to_user_data(brkt_env, user_data):
    if brkt_env:
        if 'brkt' not in user_data:
            user_data['brkt'] = {}
        api_host_port = '%s:%d' % (brkt_env.api_host, brkt_env.api_port)
        hsmproxy_host_port = '%s:%d' % (
            brkt_env.hsmproxy_host, brkt_env.hsmproxy_port)
        user_data['brkt']['api_host'] = api_host_port
        user_data['brkt']['hsmproxy_host'] = hsmproxy_host_port


def run_encryptor_instance(aws_svc, encryptor_image_id,
           snapshot, root_size,
           guest_image_id, brkt_env=None, security_group_ids=None,
           subnet_id=None, zone=None, ntp_servers=None):
    bdm = BlockDeviceMapping()
    user_data = {}
    add_brkt_env_to_user_data(brkt_env, user_data)

    if ntp_servers:
        user_data['ntp-servers'] = ntp_servers

    image = aws_svc.get_image(encryptor_image_id)
    virtualization_type = image.virtualization_type

    # Use gp2 for fast burst I/O copying root drive
    guest_unencrypted_root = EBSBlockDeviceType(
        volume_type='gp2',
        snapshot_id=snapshot,
        delete_on_termination=True)
    # Use gp2 for fast burst I/O copying root drive
    log.info('Launching encryptor instance with snapshot %s', snapshot)
    # They are creating an encrypted AMI instead of updating it
    # Use gp2 for fast burst I/O copying root drive
    guest_encrypted_root = EBSBlockDeviceType(
        volume_type='gp2',
        delete_on_termination=True)
    guest_encrypted_root.size = 2 * root_size + 1

    if virtualization_type == 'paravirtual':
        bdm['/dev/sda4'] = guest_unencrypted_root
        bdm['/dev/sda5'] = guest_encrypted_root
    else:
        # Use 'sd' names even though AWS maps these to 'xvd'
        # The AWS GUI only exposes 'sd' names, and won't allow
        # the user to attach to an existing 'sd' name in use, but
        # would allow conflicts if we used 'xvd' names here.
        bdm['/dev/sdf'] = guest_unencrypted_root
        bdm['/dev/sdg'] = guest_encrypted_root

    instance = aws_svc.run_instance(encryptor_image_id,
                                    security_group_ids=security_group_ids,
                                    user_data=json.dumps(user_data),
                                    placement=zone,
                                    block_device_map=bdm,
                                    subnet_id=subnet_id)
    aws_svc.create_tags(
        instance.id,
        name=NAME_ENCRYPTOR,
        description=DESCRIPTION_ENCRYPTOR % {'image_id': guest_image_id}
    )
    instance = wait_for_instance(aws_svc, instance.id)
    log.info('Launched encryptor instance %s', instance.id)
    # Tag volumes.
    bdm = instance.block_device_mapping
    if virtualization_type == 'paravirtual':
        aws_svc.create_tags(
            bdm['/dev/sda5'].volume_id, name=NAME_ENCRYPTED_ROOT_VOLUME)
        aws_svc.create_tags(
            bdm['/dev/sda2'].volume_id, name=NAME_METAVISOR_ROOT_VOLUME)
        aws_svc.create_tags(
            bdm['/dev/sda1'].volume_id, name=NAME_METAVISOR_GRUB_VOLUME)
        aws_svc.create_tags(
            bdm['/dev/sda3'].volume_id, name=NAME_METAVISOR_LOG_VOLUME)
    else:
        aws_svc.create_tags(
            bdm['/dev/sda1'].volume_id, name=NAME_METAVISOR_ROOT_VOLUME)
        aws_svc.create_tags(
            bdm['/dev/sdg'].volume_id, name=NAME_ENCRYPTED_ROOT_VOLUME)

    return instance


def run_guest_instance(aws_svc, image_id, subnet_id=None):
    instance = aws_svc.run_instance(
        image_id, subnet_id=subnet_id,
        instance_type='m3.medium', ebs_optimized=False)
    log.info(
        'Launching instance %s to snapshot root disk for %s',
        instance.id, image_id)
    aws_svc.create_tags(
        instance.id,
        name=NAME_GUEST_CREATOR,
        description=DESCRIPTION_GUEST_CREATOR % {'image_id': image_id}
    )
    return instance


def _snapshot_root_volume(aws_svc, instance, image_id):
    """ Snapshot the root volume of the given AMI.

    :except SnapshotError if the snapshot goes into an error state
    """
    log.info(
        'Stopping instance %s in order to create snapshot', instance.id)
    aws_svc.stop_instance(instance.id)
    wait_for_instance(aws_svc, instance.id, state='stopped')

    # Snapshot root volume.
    instance = aws_svc.get_instance(instance.id)
    root_dev = instance.root_device_name
    bdm = instance.block_device_mapping

    if root_dev not in bdm:
        # try stripping partition id
        root_dev = string.rstrip(root_dev, string.digits)
    root_vol = bdm[root_dev]
    vol = aws_svc.get_volume(root_vol.volume_id)
    aws_svc.create_tags(
        root_vol.volume_id,
        name=NAME_ORIGINAL_VOLUME % {'image_id': image_id}
    )

    snapshot = aws_svc.create_snapshot(
        vol.id,
        name=NAME_ORIGINAL_SNAPSHOT,
        description=DESCRIPTION_ORIGINAL_SNAPSHOT % {'image_id': image_id}
    )
    log.info(
        'Creating snapshot %s of root volume for instance %s',
        snapshot.id, instance.id
    )
    wait_for_snapshots(aws_svc, snapshot.id)

    # Now try to detach the root volume.
    log.info('Detaching root volume %s from %s' %
         (root_vol.volume_id, instance.id)
    )
    aws_svc.detach_volume(
        root_vol.volume_id,
        instance_id=instance.id,
        force=True
    )
    # And now delete it
    log.info('Deleting root volume %s' % (root_vol.volume_id,))
    aws_svc.delete_volume(root_vol.volume_id)

    ret_values = (
        snapshot.id, root_dev, vol.size, vol.type, root_vol.iops)
    log.debug('Returning %s', str(ret_values))
    return ret_values


def write_console_output(aws_svc, instance_id):

    try:
        console_output = aws_svc.get_console_output(instance_id)
        if console_output.output:
            prefix = instance_id + '-'
            with tempfile.NamedTemporaryFile(
                    prefix=prefix, suffix='.log', delete=False) as t:
                t.write(console_output.output)
            return t
    except:
        log.exception('Unable to write console output')

    return None


def terminate_instance(aws_svc, id, name, terminated_instance_ids):
    try:
        log.info('Terminating %s instance %s', name, id)
        aws_svc.terminate_instance(id)
        terminated_instance_ids.add(id)
    except Exception as e:
        log.warn('Could not terminate %s instance: %s', name, e)


def clean_up(aws_svc, instance_ids=None, volume_ids=None,
              snapshot_ids=None, security_group_ids=None):
    """ Clean up any resources that were created by the encryption process.
    Handle and log exceptions, to ensure that the script doesn't exit during
    cleanup.
    """
    instance_ids = instance_ids or []
    volume_ids = volume_ids or []
    snapshot_ids = snapshot_ids or []
    security_group_ids = security_group_ids or []

    # Delete instances and snapshots.
    terminated_instance_ids = set()
    for instance_id in instance_ids:
        try:
            log.info('Terminating instance %s', instance_id)
            aws_svc.terminate_instance(instance_id)
            terminated_instance_ids.add(instance_id)
        except EC2ResponseError as e:
            log.warn('Unable to terminate instance %s: %s', instance_id, e)
        except:
            log.exception('Unable to terminate instance %s', instance_id)

    for snapshot_id in snapshot_ids:
        try:
            log.info('Deleting snapshot %s', snapshot_id)
            aws_svc.delete_snapshot(snapshot_id)
        except EC2ResponseError as e:
            log.warn('Unable to delete snapshot %s: %s', snapshot_id, e)
        except:
            log.exception('Unable to delete snapshot %s', snapshot_id)

    # Wait for instances to terminate before deleting security groups and
    # volumes, to avoid dependency errors.
    for id in terminated_instance_ids:
        log.info('Waiting for instance %s to terminate.', id)
        try:
            wait_for_instance(aws_svc, id, state='terminated')
        except (EC2ResponseError, InstanceError) as e:
            log.warn(
                'An error occurred while waiting for instance to '
                'terminate: %s', e)
        except:
            log.exception(
                'An error occurred while waiting for instance '
                'to terminate'
            )

    # Delete volumes and security groups.
    for volume_id in volume_ids:
        try:
            log.info('Deleting volume %s', volume_id)
            aws_svc.delete_volume(volume_id)
        except EC2ResponseError as e:
            log.warn('Unable to delete volume %s: %s', volume_id, e)
        except:
            log.exception('Unable to delete volume %s', volume_id)

    for sg_id in security_group_ids:
        try:
            log.info('Deleting security group %s', sg_id)
            aws_svc.delete_security_group(sg_id)
        except EC2ResponseError as e:
            log.warn('Unable to delete security group %s: %s', sg_id, e)
        except:
            log.exception('Unable to delete security group %s', sg_id)


def log_exception_console(aws_svc, e, id):
    log.error(
        'Encryption failed.  Check console output of instance %s '
        'for details.',
        id
    )

    e.console_output_file = write_console_output(aws_svc, id)
    if e.console_output_file:
        log.error(
            'Wrote console output for instance %s to %s',
            id, e.console_output_file.name
        )
    else:
        log.error(
            'Encryptor console output is not currently available.  '
            'Wait a minute and check the console output for '
            'instance %s in the EC2 Management '
            'Console.',
            id
        )


def snapshot_encrypted_instance(aws_svc, enc_svc_cls, encryptor_instance,
                       encryptor_image, image_id=None, vol_type='', iops=None,
                       legacy=False):
    # First wait for encryption to complete
    host_ips = []
    if encryptor_instance.ip_address:
        host_ips.append(encryptor_instance.ip_address)
    if encryptor_instance.private_ip_address:
        host_ips.append(encryptor_instance.private_ip_address)

    enc_svc = enc_svc_cls(host_ips)
    log.info('Waiting for encryption service on %s (port %s on %s)',
             encryptor_instance.id, enc_svc.port, ', '.join(host_ips))
    wait_for_encryptor_up(enc_svc, Deadline(600))

    log.info('Creating encrypted root drive.')
    try:
        wait_for_encryption(enc_svc)
    except EncryptionError as e:
        log_exception_console(aws_svc, e, encryptor_instance.id)
        raise e

    log.info('Encrypted root drive is ready.')
    # The encryptor instance may modify its volume attachments while running,
    # so we update the encryptor instance's local attributes before reading
    # them.
    encryptor_instance = aws_svc.get_instance(encryptor_instance.id)
    encryptor_bdm = encryptor_instance.block_device_mapping

    # Stop the encryptor instance.
    log.info('Stopping encryptor instance %s', encryptor_instance.id)
    aws_svc.stop_instance(encryptor_instance.id)
    wait_for_instance(aws_svc, encryptor_instance.id, state='stopped')

    description = DESCRIPTION_SNAPSHOT % {'image_id': image_id}

    # Set up new Block Device Mappings
    log.debug('Creating block device mapping')
    new_bdm = BlockDeviceMapping()
    if not vol_type or vol_type == '':
        vol_type = 'gp2'

    # Snapshot volumes.
    if encryptor_image.virtualization_type == 'paravirtual':
        snap_guest = aws_svc.create_snapshot(
            encryptor_bdm['/dev/sda5'].volume_id,
            name=NAME_ENCRYPTED_ROOT_SNAPSHOT,
            description=description
        )
        snap_bsd = aws_svc.create_snapshot(
            encryptor_bdm['/dev/sda2'].volume_id,
            name=NAME_METAVISOR_ROOT_SNAPSHOT,
            description=description
        )
        snap_log = aws_svc.create_snapshot(
            encryptor_bdm['/dev/sda3'].volume_id,
            name=NAME_METAVISOR_LOG_SNAPSHOT,
            description=description
        )
        log.info(
            'Creating snapshots for the new encrypted AMI: %s, %s, %s',
            snap_guest.id, snap_bsd.id, snap_log.id)

        wait_for_snapshots(
            aws_svc, snap_guest.id, snap_bsd.id, snap_log.id)

        if vol_type is None:
            vol_type = "gp2"
        dev_guest_root = EBSBlockDeviceType(volume_type=vol_type,
                                    snapshot_id=snap_guest.id,
                                    iops=iops,
                                    delete_on_termination=True)
        mv_root_id = encryptor_bdm['/dev/sda1'].volume_id

        dev_mv_root = EBSBlockDeviceType(volume_type='gp2',
                                  snapshot_id=snap_bsd.id,
                                  delete_on_termination=True)
        dev_log = EBSBlockDeviceType(volume_type='gp2',
                                 snapshot_id=snap_log.id,
                                 delete_on_termination=True)
        new_bdm['/dev/sda2'] = dev_mv_root
        new_bdm['/dev/sda3'] = dev_log
        new_bdm['/dev/sda5'] = dev_guest_root
    else:
        # HVM instance type
        snap_guest = aws_svc.create_snapshot(
            encryptor_bdm['/dev/sdg'].volume_id,
            name=NAME_ENCRYPTED_ROOT_SNAPSHOT,
            description=description
        )
        log.info(
            'Creating snapshots for the new encrypted AMI: %s' % (
                    snap_guest.id)
        )
        wait_for_snapshots(aws_svc, snap_guest.id)
        dev_guest_root = EBSBlockDeviceType(volume_type=vol_type,
                                    snapshot_id=snap_guest.id,
                                    iops=iops,
                                    delete_on_termination=True)
        mv_root_id = encryptor_bdm['/dev/sda1'].volume_id
        new_bdm['/dev/sdf'] = dev_guest_root

    if not legacy:
        log.info("Detaching new guest root %s" % (mv_root_id,))
        aws_svc.detach_volume(
            mv_root_id,
            instance_id=encryptor_instance.id,
            force=True
        )
        aws_svc.create_tags(
            mv_root_id, name=NAME_METAVISOR_ROOT_VOLUME)

    if image_id:
        log.debug('Getting image %s', image_id)
        guest_image = aws_svc.get_image(image_id)
        if guest_image is None:
            raise BracketError("Can't find image %s" % image_id)

        # Propagate any ephemeral drive mappings to the soloized image
        guest_bdm = guest_image.block_device_mapping
        for key in guest_bdm.keys():
            guest_vol = guest_bdm[key]
            if guest_vol.ephemeral_name:
                log.info('Propagating block device mapping for %s at %s' %
                         (guest_vol.ephemeral_name, key))
                new_bdm[key] = guest_vol

    return mv_root_id, new_bdm


def register_ami(aws_svc, encryptor_instance, encryptor_image, name,
                 description, mv_bdm=None, legacy=False, guest_instance=None,
                 mv_root_id=None, root_device_name=None):
    if not mv_bdm:
        mv_bdm = BlockDeviceMapping()
    # Register the new AMI.
    if legacy:
        # The encryptor instance may modify its volume attachments while
        # running, so we update the encryptor instance's local attributes
        # before reading them.
        encryptor_instance = aws_svc.get_instance(encryptor_instance.id)
        guest_id = encryptor_instance.id
        # Explicitly detach/delete all but root drive
        bdm = encryptor_instance.block_device_mapping
        for d in ['/dev/sda2', '/dev/sda3', '/dev/sda4',
                  '/dev/sda5', '/dev/sdf', '/dev/sdg']:
            if not bdm.get(d):
                continue
            aws_svc.detach_volume(
                bdm[d].volume_id,
                instance_id=encryptor_instance.id,
                force=True
            )
            aws_svc.delete_volume(bdm[d].volume_id)
    else:
        guest_id = guest_instance.id
        # Explicitly attach new mv root to guest instance
        aws_svc.attach_volume(
            mv_root_id,
            guest_instance.id,
            root_device_name,
        )
        log.info("Done attaching new root: %s" % (root_device_name,))
        guest_instance = aws_svc.get_instance(guest_instance.id)
        bdm = guest_instance.block_device_mapping
        mv_bdm[root_device_name] = bdm[root_device_name]
        mv_bdm[root_device_name].delete_on_termination = True

    # Legacy:
    #   Create AMI from (stopped) MV instance
    # Non-legacy:
    #   Create AMI from original (stopped) guest instance. This
    #   preserves any billing information found in
    #   the identity document (i.e. billingProduct)
    ami = aws_svc.create_image(
        guest_id,
        name,
        description=description,
        no_reboot=True,
        block_device_mapping=mv_bdm
    )

    if not legacy:
        log.info("Deleting volume %s" % (mv_root_id,))
        aws_svc.detach_volume(
            mv_root_id,
            instance_id=guest_instance.id,
            force=True
        )
        aws_svc.delete_volume(mv_root_id)

    log.info('Registered AMI %s based on the snapshots.', ami)
    wait_for_image(aws_svc, ami)
    image = aws_svc.get_image(ami, retry=True)
    if encryptor_image.virtualization_type == 'paravirtual':
        name = NAME_METAVISOR_GRUB_SNAPSHOT
    else:
        name = NAME_METAVISOR_ROOT_SNAPSHOT
    snap = image.block_device_mapping[image.root_device_name]
    aws_svc.create_tags(
        snap.snapshot_id,
        name=name,
        description=description
    )
    aws_svc.create_tags(ami)

    ami_info = {}
    ami_info['volume_device_map'] = []
    result_image = aws_svc.get_image(ami, retry=True)
    for attach_point, bdt in result_image.block_device_mapping.iteritems():
        if bdt.snapshot_id:
            bdt_snapshot = aws_svc.get_snapshot(bdt.snapshot_id)
            device_details = {
                'attach_point': attach_point,
                'description': bdt_snapshot.tags.get('Name', ''),
                'size': bdt_snapshot.volume_size
            }
            ami_info['volume_device_map'].append(device_details)

    ami_info['ami'] = ami
    ami_info['name'] = name
    return ami_info


def encrypt(aws_svc, enc_svc_cls, image_id, encryptor_ami, brkt_env=None,
            encrypted_ami_name=None, subnet_id=None, security_group_ids=None,
            ntp_servers=None):
    encryptor_instance = None
    ami = None
    snapshot_id = None
    guest_instance = None
    temp_sg_id = None
    guest_image = aws_svc.get_image(image_id)
    mv_image = aws_svc.get_image(encryptor_ami)

    # Normal operation is both encryptor and guest match
    # on virtualization type, but we'll support a PV encryptor
    # and a HVM guest (legacy)
    log.debug('Guest type: %s Encryptor type: %s',
        guest_image.virtualization_type, mv_image.virtualization_type)
    if (mv_image.virtualization_type == 'hvm' and
        guest_image.virtualization_type == 'paravirtual'):
            raise BracketError(
                    "Encryptor/Guest virtualization type mismatch")
    legacy = False
    if (mv_image.virtualization_type == 'paravirtual' and
        guest_image.virtualization_type == 'hvm'):
            # This will go away when HVM MV GA's
            log.warn("Must specify a paravirtual AMI type in order to "
                     "preserve guest OS license information")
            legacy = True
    root_device_name = guest_image.root_device_name
    if not guest_image.block_device_mapping.get(root_device_name):
            log.warn("AMI must have root_device_name in block_device_mapping "
                    "in order to preserve guest OS license information")
            legacy = True
    if (guest_image.root_device_name != "/dev/sda1"):
        log.warn("Guest Operating System license information will not be "
                 "preserved because the root disk is attached at %s "
                 "instead of /dev/sda1", guest_image.root_device_name)
        legacy = True
    try:
        guest_instance = run_guest_instance(aws_svc,
            image_id, subnet_id=subnet_id)
        wait_for_instance(aws_svc, guest_instance.id)
        snapshot_id, root_dev, size, vol_type, iops = _snapshot_root_volume(
            aws_svc, guest_instance, image_id
        )

        if (guest_image.virtualization_type == 'hvm'):
            net_sriov_attr = aws_svc.get_instance_attribute(guest_instance.id,
                                                            "sriovNetSupport")
            if (net_sriov_attr.get("sriovNetSupport") == "simple"):
                log.warn("Guest Operating System license information will not "
                         "be preserved because guest has sriovNetSupport "
                         "enabled and metavisor does not support sriovNet")
                legacy = True

        if not security_group_ids:
            vpc_id = None
            if subnet_id:
                subnet = aws_svc.get_subnet(subnet_id)
                vpc_id = subnet.vpc_id
            temp_sg_id = create_encryptor_security_group(
                aws_svc, vpc_id=vpc_id).id
            security_group_ids = [temp_sg_id]
        root_device_name = guest_instance.root_device_name

        encryptor_instance = run_encryptor_instance(
            aws_svc=aws_svc,
            encryptor_image_id=encryptor_ami,
            snapshot=snapshot_id,
            root_size=size,
            guest_image_id=image_id,
            brkt_env=brkt_env,
            security_group_ids=security_group_ids,
            subnet_id=subnet_id,
            zone=guest_instance.placement,
            ntp_servers=ntp_servers,
        )


        log.debug('Getting image %s', image_id)
        image = aws_svc.get_image(image_id)
        if image is None:
            raise BracketError("Can't find image %s" % image_id)
        if encrypted_ami_name:
            name = encrypted_ami_name
        elif image_id:
            name = get_name_from_image(image)
        description = get_description_from_image(image)

        mv_root_id, mv_bdm = snapshot_encrypted_instance(aws_svc, enc_svc_cls,
                encryptor_instance, mv_image, image_id=image_id,
                vol_type=vol_type, iops=iops, legacy=legacy)
        ami_info = register_ami(aws_svc, encryptor_instance, mv_image, name,
                description, legacy=legacy, guest_instance=guest_instance,
                root_device_name=root_device_name, mv_root_id=mv_root_id,
                mv_bdm=mv_bdm)
        ami = ami_info['ami']
        log.info('Created encrypted AMI %s based on %s', ami, image_id)
    finally:
        instance_ids = []
        if guest_instance:
            instance_ids.append(guest_instance.id)
        if encryptor_instance:
            instance_ids.append(encryptor_instance.id)

        # Delete volumes explicitly.  They should get cleaned up during
        # instance deletion, but we've gotten reports that occasionally
        # volumes can get orphaned.
        volume_ids = None
        try:
            volumes = aws_svc.get_volumes(
                tag_key=TAG_ENCRYPTOR_SESSION_ID,
                tag_value=aws_svc.session_id
            )
            volume_ids = [v.id for v in volumes]
        except EC2ResponseError as e:
            log.warn('Unable to clean up orphaned volumes: %s', e)
        except:
            log.exception('Unable to clean up orphaned volumes')

        sg_ids = []
        if temp_sg_id:
            sg_ids.append(temp_sg_id)

        snapshot_ids = []
        if snapshot_id:
            snapshot_ids.append(snapshot_id)

        clean_up(
            aws_svc,
            instance_ids=instance_ids,
            volume_ids=volume_ids,
            snapshot_ids=snapshot_ids,
            security_group_ids=sg_ids
        )

    log.info('Done.')
    return ami
