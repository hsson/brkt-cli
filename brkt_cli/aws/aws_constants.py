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

# End user-visible terminology.  These are resource names and descriptions
# that the user will see in his or her EC2 console.

# Snapshot names.
NAME_LOG_SNAPSHOT = 'Bracket logs from %(instance_id)s'
DESCRIPTION_LOG_SNAPSHOT = \
    'Bracket logs from %(instance_id)s in AWS account %(aws_account)s '\
    'taken at %(timestamp)s'

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
DESCRIPTION_SNAPSHOT = 'Based on %(image_id)s'

# Volume names.
NAME_ORIGINAL_VOLUME = 'Original unencrypted root volume from %(image_id)s'
NAME_ENCRYPTED_ROOT_VOLUME = 'Bracket encrypted root volume'
NAME_METAVISOR_ROOT_VOLUME = 'Bracket system root'

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
