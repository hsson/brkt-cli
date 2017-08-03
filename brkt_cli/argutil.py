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

from brkt_cli import crypto
from brkt_cli.validation import ValidationError


def add_out(parser):
    """ Add the --out argument, for writing command output to a file instead
    of stdout.
    """
    parser.add_argument(
        '--out',
        metavar='PATH',
        help=(
            'Write to a file instead of stdout.  This can be used to avoid '
            'character encoding issues when redirecting output on Windows.'
        )
    )


def add_brkt_tag(parser):
    parser.add_argument(
        '--brkt-tag',
        metavar='NAME=VALUE',
        dest='brkt_tags',
        help=(
            'Bracket tag which will be embedded in the JWT as a claim.  All '
            'characters must be alphanumeric or [-_.].  The tag name cannot '
            'be a JWT registered claim name (see RFC 7519).'),
        action='append'
    )


def add_exp(parser):
    parser.add_argument(
        '--exp',
        metavar='DURATION',
        help='Token expiry time duration in the format N[dhms] (e.g. 12h)'
    )


def add_root_url(parser, cli_config):
    """ Add the --root-url argument, for specifying the Yeti public API
    endpoint. """
    _, env = cli_config.get_current_env()
    default_url = 'https://%s:%d' % (
        env.public_api_host, env.public_api_port)
    parser.add_argument(
        '--root-url',
        metavar='URL',
        default=default_url,
        help='Bracket service root URL'
    )


def _validate_cert_path(path):
    try:
        crypto.validate_cert_path(path)
    except ValidationError as e:
        raise argparse.ArgumentTypeError(e.message)
    return path


def add_public_api_ca_cert(parser, cli_config=None):
    default_path = None
    if cli_config:
        _, env = cli_config.get_current_env()
        default_path = env.public_api_ca_cert_path

    parser.add_argument(
        '--public-api-ca-cert',
        metavar='PATH',
        default=default_path,
        type=_validate_cert_path,
        help=(
            'Root X.509 CA certificate for a Customer Managed MCP in PEM '
            'format.'
        )
    )
