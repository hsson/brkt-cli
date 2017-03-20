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


def add_gcp_network(parser, parsed_config):
    parser.add_argument(
        '--network',
        dest='network',
        default=parsed_config.get_option('gcp.network', 'default'),
        required=False
    )

def add_no_validate(parser):
    parser.add_argument(
        '--no-validate',
        dest='validate',
        action='store_false',
        default=True,
        help="Don't validate images or token"
    )

def add_gcp_project(parser, parsed_config):
    required_project = parsed_config.get_option('gcp.project', None)
    parser.add_argument(
        '--project',
        help='GCP project name',
        dest='project',
        default=required_project,
        required=not bool(required_project)
    )

def add_gcp_subnetwork(parser, parsed_config):
    parser.add_argument(
        '--subnetwork',
        dest='subnetwork',
        default=parsed_config.get_option('gcp.subnetwork', None),
        required=False
    )

def add_gcp_zone(parser, parsed_config):
    zone_kwargs = {
        'help': 'GCP zone to operate in',
        'dest': 'zone',
        'default': parsed_config.get_option('gcp.zone'),
        'required': False,
    }
    if zone_kwargs['default'] is None:
        zone_kwargs['required'] = True
    parser.add_argument(
        '--zone',
        **zone_kwargs
    )

def add_gcp_image_project(parser):
    parser.add_argument(
        '--image-project',
        metavar='NAME',
        help='GCP project name which owns the image (e.g. centos-cloud)',
        dest='image_project',
        required=False
    )

def add_gcp_encryptor_image(parser):
    # Optional encryptor image name, if it exists in the local GCP project
    # argument is hidden because it's only used for development.
    parser.add_argument(
        '--encryptor-image',
        dest='encryptor_image',
        required=False,
        help=argparse.SUPPRESS
    )

def add_gcp_encryptor_image_file(parser):
    # Optional Image Name that's used to launch the metavisor instance. This
    # argument is hidden because it's only used for development.
    parser.add_argument(
        '--encryptor-image-file',
        dest='image_file',
        required=False,
        help=argparse.SUPPRESS
    )

def add_gcp_encryptor_image_bucket(parser):
    # Optional bucket name to retrieve the metavisor image from
    # (prod, stage, shared, <custom>)
    parser.add_argument(
        '--encryptor-image-bucket',
        help=argparse.SUPPRESS,
        dest='bucket',
        default='prod',
        required=False
    )

def add_no_cleanup(parser):
    parser.add_argument(
        '--no-cleanup',
        dest='cleanup',
        required=False,
        default=True,
        action='store_false',
        help=argparse.SUPPRESS
    )
