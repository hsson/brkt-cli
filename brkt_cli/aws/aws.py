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
import json
import urllib2

from brkt_cli import mv_version
from brkt_cli.util import BracketError

ENCRYPTOR_AMIS_AWS_BUCKET = 'solo-brkt-prod-net'


def _get_encryptor_amis_list(version):
    """ Read the list of AMIs from the AMI endpoint and return them

    :raise BracketError if the list of AMIs cannot be read
    """
    bucket = ENCRYPTOR_AMIS_AWS_BUCKET
    amis_url = mv_version.get_amis_url(version, bucket)

    r = urllib2.urlopen(amis_url)
    if r.getcode() not in (200, 201):
        raise BracketError(
            'Getting %s gave response: %s' % (amis_url, r.text))
    resp_json = json.loads(r.read())
    return resp_json