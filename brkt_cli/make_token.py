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

import argparse
import json
import logging
import uuid

import brkt_cli
import brkt_cli.crypto
from brkt_cli import (
    brkt_jwt, ValidationError, util, argutil, instance_config_args
)
from brkt_cli.subcommand import Subcommand
from brkt_cli.util import parse_timestamp

log = logging.getLogger(__name__)

SUBCOMMAND_NAME = 'make-token'


class MakeTokenSubcommand(Subcommand):

    def __init__(self):
        self.config = None

    def name(self):
        return SUBCOMMAND_NAME

    def register(self, subparsers, parsed_config):
        self.config = parsed_config
        _setup_args(subparsers, parsed_config)

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
            if values.root_url:
                yeti = instance_config_args.get_yeti_service(values.root_url)
            else:
                brkt_env = self.config.get_current_env()[1]
                yeti = instance_config_args.yeti_service_from_brkt_env(
                    brkt_env)

            tags = brkt_jwt.brkt_tags_from_name_value_list(values.brkt_tags)
            jwt_string = yeti.get_launch_token(tags=tags)

        log.debug('Header: %s', json.dumps(brkt_jwt.get_header(jwt_string)))
        log.debug('Payload: %s', json.dumps(brkt_jwt.get_payload(jwt_string)))
        util.write_to_file_or_stdout(jwt_string, path=values.out)

        return 0


def get_subcommands():
    return [MakeTokenSubcommand()]


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
    claims = brkt_jwt.name_value_list_to_dict(values.claims)
    claims.update(brkt_jwt.brkt_tags_from_name_value_list(values.brkt_tags))

    return brkt_jwt.make_jwt(
        crypto,
        exp=exp,
        nbf=nbf,
        customer=customer,
        claims=claims
    )


def _setup_args(subparsers, parsed_config):
    parser = subparsers.add_parser(
        SUBCOMMAND_NAME,
        description=(
            'Generate a launch token (JSON Web Token), '
            'used by the Metavisor to communicate with the Bracket service. '
            'Users who need fine-grained control of their launch tokens can '
            'optionally use this command, and pass the generated launch '
            'token to the encrypt, update, and make-user-data commands. If '
            'a signing key is not specified, retrieve a launch token from '
            'the Bracket service. A timestamp can be either a '
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
    argutil.add_root_url(parser, parsed_config)

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
