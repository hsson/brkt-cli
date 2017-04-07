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
from __future__ import print_function

import logging
import re
import time

import jwt

from brkt_cli import util, version
from brkt_cli.brkt_jwt import jwk
from brkt_cli.validation import ValidationError

log = logging.getLogger(__name__)

# Registered claim names, per RFC 7519.
JWT_REGISTERED_CLAIMS = (
    'iss', 'sub', 'aud', 'exp', 'nbf', 'iat', 'jti'
)


def name_value_list_to_dict(l):
    """ Convert a list of NAME=VALUE strings to a dictionary.
    :raise ValidationError if a key is specified more than once.
    """
    d = {}
    if l:
        for name_value in l:
            name, value = util.parse_name_value(name_value)
            validate_name_value(name, value)
            if name in d:
                raise ValidationError(
                    'Claim %s specified multiple times' % name)
            d[name] = value
    return d


def brkt_tags_from_name_value_list(l):
    """ Convert a list of NAME=VALUE strings to a dictionary.

    :raise ValidationError if a key is specified more than once or a key
    matches a JWT registered claim
    """
    d = name_value_list_to_dict(l)
    for k, _ in d.iteritems():
        if k.lower() in JWT_REGISTERED_CLAIMS:
            raise ValidationError(
                k + ' is a JWT registered claim'
            )
    return d


def make_jwt(crypto, exp=None, nbf=None, claims=None, customer=None):
    """ Generate a JWT.

    :param crypto a brkt_cli.crypto.Crypto object
    :param exp expiration time as a datetime
    :param nbf not before as a datetime
    :param claims a dictionary of claims
    :param customer customer UUID as a string
    :return the JWT as a string
    """

    kid = jwk.get_thumbprint(crypto.x, crypto.y)

    payload = {
        'jti': util.make_nonce(),
        'iss': 'brkt-cli-' + version.VERSION,
        'iat': int(time.time())
    }
    if claims:
        payload.update(claims)

    if exp:
        payload['exp'] = util.datetime_to_timestamp(exp)
    if nbf:
        payload['nbf'] = util.datetime_to_timestamp(nbf)
    if customer:
        payload['customer'] = customer

    return jwt.encode(
        payload, crypto.private_key, algorithm='ES384', headers={'kid': kid})


def get_header(jwt_string):
    """ Return all of the headers in the given JWT.

    :return the headers as a dictionary
    """
    try:
        return jwt.get_unverified_header(jwt_string)
    except jwt.InvalidTokenError as e:
        log.debug('', exc_info=1)
        raise ValidationError('Unable to decode token: %s' % e)


def get_payload(jwt_string):
    """ Return the payload of the given JWT.

    :return the payload as a dictionary
    """
    try:
        return jwt.decode(jwt_string, verify=False)
    except jwt.InvalidTokenError as e:
        log.debug('', exc_info=1)
        raise ValidationError('Unable to decode token: %s' % e)


def validate_name_value(name, value):
    """ Validate the format of a NAME=VALUE pair.

    :raise ValidationError if the format is invalid
    """
    if not re.match(r'[A-Za-z0-9_\-]+$', name) or \
            not re.match(r'[A-Za-z0-9_\-]+$', value):
        raise ValidationError(
            'Claim name and value must only contain letters, numbers, "-" '
            'and "_"'
        )
    # Don't allow "any", since we treat it as a reserved word.
    if name.lower() == 'any' or value.lower() == 'any':
        raise ValidationError(
            '"any" is not allowed for claim name or value'
        )


