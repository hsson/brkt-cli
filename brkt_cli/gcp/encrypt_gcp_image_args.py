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
from brkt_cli.gcp import gcp_args
from brkt_cli.util import (
    CRYPTO_GCM,
    CRYPTO_XTS
)


def setup_encrypt_gcp_image_args(parser, parsed_config):
    parser.add_argument(
        'image',
        metavar='ID',
        help='The image that will be encrypted',
    )
    parser.add_argument(
        '--encrypted-image-name',
        metavar='NAME',
        dest='encrypted_image_name',
        help='Specify the name of the generated encrypted image',
        required=False
    )
    gcp_args.add_gcp_zone(parser, parsed_config)
    gcp_args.add_no_validate(parser)
    gcp_args.add_gcp_project(parser, parsed_config)
    gcp_args.add_gcp_image_project(parser)
    gcp_args.add_gcp_encryptor_image(parser)
    gcp_args.add_gcp_network(parser, parsed_config)
    gcp_args.add_gcp_subnetwork(parser, parsed_config)
    parser.add_argument(
        '--gcp-tag',
        metavar='VALUE',
        dest='gcp_tags',
        action='append',
        help=(
              'Set a GCP tag on the encryptor instance. May be specified'
              ' multiple times.'
        )
    )
    gcp_args.add_gcp_encryptor_image_file(parser)
    gcp_args.add_gcp_encryptor_image_bucket(parser)
    gcp_args.add_no_cleanup(parser)
    parser.add_argument(
        '--keep-encryptor',
        dest='keep_encryptor',
        action='store_true',
        help=argparse.SUPPRESS
    )
    # Optional argument for root disk crypto policy. The supported values
    # currently are "gcm" and "xts" with "gcm" being the default
    parser.add_argument(
        '--crypto-policy',
        dest='crypto',
        metavar='NAME',
        choices=[CRYPTO_GCM, CRYPTO_XTS],
        help=argparse.SUPPRESS,
        default=None
    )
