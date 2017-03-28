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

import argparse
import json
import logging
import re
import time
import uuid
from datetime import datetime

import iso8601
import jwt

import brkt_cli
from brkt_cli import argutil, config, util, version
from brkt_cli.brkt_jwt import jwk
from brkt_cli.subcommand import Subcommand
from brkt_cli.validation import ValidationError
import brkt_cli.crypto

log = logging.getLogger(__name__)


SUBCOMMAND_NAME = 'make-token'

# Registered claim names, per RFC 7519.
JWT_REGISTERED_CLAIMS = (
    'iss', 'sub', 'aud', 'exp', 'nbf', 'iat', 'jti'
)


def _name_value_list_to_dict(l):
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
    d = _name_value_list_to_dict(l)
    for k, _ in d.iteritems():
        if k.lower() in JWT_REGISTERED_CLAIMS:
            raise ValidationError(
                k + ' is a JWT registered claim'
            )
    return d


def _make_jwt_from_signing_key(values, signing_key):
    crypto = brkt_cli.crypto.read_private_key(signing_key)
    exp = None
    if values.exp:
        exp = parse_timestamp(values.exp)
    nbf = None
    if values.nbf:
        nbf = parse_timestamp(values.nbf)
    customer = None
    if values.customer:
        customer = str(values.customer)

    # Merge claims and tags.
    claims = _name_value_list_to_dict(values.claims)
    claims.update(brkt_tags_from_name_value_list(values.brkt_tags))

    return make_jwt(
        crypto,
        exp=exp,
        nbf=nbf,
        customer=customer,
        claims=claims
    )


class MakeTokenSubcommand(Subcommand):

    def __init__(self):
        self.config = None

    def name(self):
        return SUBCOMMAND_NAME

    def register(self, subparsers, parsed_config):
        self.config = parsed_config
        setup_make_jwt_args(subparsers)

    def verbose(self, values):
        return values.make_jwt_verbose

    def run(self, values):
        if values.signing_key_option:
            log.warn(
                'The --signing-key option is deprecated and will be removed '
                'in a future release.'
            )

        signing_key = (
            # The signing_key field doesn't exist if cryptography isn't
            # installed.
            getattr(values, 'signing_key', None) or
            values.signing_key_option
        )
        if signing_key:
            # Original workflow: create a launch token from a private key.
            if not brkt_cli.crypto.cryptography_library_available:
                raise ValidationError(
                    'Token generation from a private key requires the '
                    'cryptography library.\nPlease run pip install '
                    'cryptography.'
                )
            jwt_string = _make_jwt_from_signing_key(values, signing_key)
        else:
            # We're scaling back the list of supported claims.  Don't allow
            # these until there's a need, and the service API supports it.
            msg = (
                '%s is not supported when getting a launch '
                'token from the Bracket service'
            )
            if values.claims:
                raise ValidationError(msg % '--claim')
            if values.customer:
                raise ValidationError(msg % '--customer')
            if values.exp:
                raise ValidationError(msg % '--exp')
            if values.nbf:
                raise ValidationError(msg % '--nbf')

            # New workflow: get a launch token from Yeti.
            yeti = config.get_yeti_service(self.config)
            tags = brkt_tags_from_name_value_list(values.brkt_tags)
            jwt_string = yeti.get_launch_token(tags=tags)

        log.debug('Header: %s', json.dumps(get_header(jwt_string)))
        log.debug('Payload: %s', json.dumps(get_payload(jwt_string)))
        util.write_to_file_or_stdout(jwt_string, path=values.out)

        return 0


def _timestamp_to_datetime(ts):
    """ Convert a Unix timestamp to a datetime with timezone set to UTC. """
    return datetime.fromtimestamp(ts, tz=iso8601.UTC)


def _datetime_to_timestamp(dt):
    """ Convert a datetime to a Unix timestamp in seconds. """
    time_zero = _timestamp_to_datetime(0)
    return (dt - time_zero).total_seconds()


def get_subcommands():
    return [MakeTokenSubcommand()]


def parse_timestamp(ts_string):
    """ Return a datetime that represents the given timestamp
    string.  The string can be a Unix timestamp in seconds or an ISO 8601
    timestamp.

    :raise ValidationError if ts_string is malformed
    """
    now = int(time.time())

    # Parse integer timestamp.
    m = re.match('\d+(\.\d+)?$', ts_string)
    if m:
        t = float(ts_string)
        if t < now:
            raise ValidationError(
                '%s is earlier than the current timestamp (%s).' % (
                    ts_string, now))
        return _timestamp_to_datetime(t)

    # Parse ISO 8601 timestamp.
    dt_now = _timestamp_to_datetime(now)
    try:
        dt = iso8601.parse_date(ts_string)
    except iso8601.ParseError:
        raise ValidationError(
            'Timestamp "%s" must either be a Unix timestamp or in iso8601 '
            'format (2016-05-10T19:15:36Z).' % ts_string
        )
    if dt < dt_now:
        raise ValidationError(
            '%s is earlier than the current timestamp (%s).' % (
                ts_string, dt_now))
    return dt


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
        payload['exp'] = _datetime_to_timestamp(exp)
    if nbf:
        payload['nbf'] = _datetime_to_timestamp(nbf)
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


def setup_make_jwt_args(subparsers):
    parser = subparsers.add_parser(
        SUBCOMMAND_NAME,
        description=(
            'Generate a launch token (JSON Web Token) for encrypting an '
            'instance or launching an encrypted instance. If a signing key is '
            'not specified, get a token from the Bracket service. '
            'A timestamp can be either a '
            'Unix timestamp in seconds or ISO 8601 (2016-05-10T19:15:36Z). '
            'Timezone offset defaults to UTC if not specified.'),
        help=(
            'Generate a JSON Web Token for encrypting or launching an '
            'instance'),
        formatter_class=brkt_cli.SortingHelpFormatter
    )

    if brkt_cli.crypto.cryptography_library_available:
        parser.add_argument(
            'signing_key',
            metavar='SIGNING-KEY-PATH',
            nargs='?',
            help=(
                'The private key that is used to sign the JWT. The key must '
                'be a 384-bit ECDSA private key (NIST P-384) in PEM format.'
            )
        )

    argutil.add_brkt_tag(parser)
    parser.add_argument(
        '--claim',
        metavar='NAME=VALUE',
        dest='claims',
        help=(
            'JWT claim specified by name and value.  May be specified '
            'multiple times.'),
        action='append'
    )

    parser.add_argument(
        '--customer',
        metavar='UUID',
        type=uuid.UUID,
        help=(
            'Required for API access when using a third party JWK server'
        )
    )
    parser.add_argument(
        '--exp',
        metavar='TIMESTAMP',
        help='Token expiration time'
    )
    parser.add_argument(
        '--nbf',
        metavar='TIMESTAMP',
        help='Token is not valid before this time'
    )
    argutil.add_out(parser)
    parser.add_argument(
        '-v',
        '--verbose',
        dest='make_jwt_verbose',
        action='store_true',
        help=argparse.SUPPRESS
    )

    # The signing key is now passed as a positional argument.  This option
    # is deprecated and will be removed in a future release.
    parser.add_argument(
        '--signing-key',
        dest='signing_key_option',
        metavar='PATH',
        help=argparse.SUPPRESS
    )
