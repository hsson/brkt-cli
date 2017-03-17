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


def setup_wrap_gcp_image_args(parser, parsed_config):
    parser.add_argument(
        'image',
        metavar='ID',
        help='The image that will be wrapped with the Bracket Metavisor',
    )
    parser.add_argument(
        '--instance-name',
        metavar='NAME',
        dest='instance_name',
        help='Name of the instance'
    )
    parser.add_argument(
        '--instance-type',
        help='Instance type',
        dest='instance_type',
        default='n1-standard-1'
    )
    gcp_args.add_gcp_zone(parser, parsed_config)
    parser.add_argument(
        '--no-delete-boot',
        help='Do not delete boot disk when instance is deleted',
        dest='delete_boot',
        default=True,
        action='store_false'
    )
    gcp_args.add_gcp_project(parser, parsed_config)
    gcp_args.add_gcp_image_project(parser)
    gcp_args.add_gcp_network(parser, parsed_config)
    parser.add_argument(
        '--gcp-tag',
        dest='gcp_tags',
        action='append',
        metavar='VALUE',
        help=(
              'Set a GCP tag on the encrypted instance being launched. May be '
              'specified multiple times.'
        )
    )
    gcp_args.add_gcp_encryptor_image(parser)
    gcp_args.add_gcp_encryptor_image_file(parser)
    gcp_args.add_gcp_encryptor_image_bucket(parser)
    # Optional startup script. Hidden because it is only used for development
    # and testing. It should be passed as a string containing a multi-line
    # script (bash, python etc.)
    parser.add_argument(
        '--startup-script',
        help=argparse.SUPPRESS,
        dest='startup_script',
        metavar='SCRIPT'
    )
    gcp_args.add_gcp_subnetwork(parser, parsed_config)
    parser.add_argument(
        '--guest-fqdn',
        metavar='FQDN',
        dest='guest_fqdn',
        help=argparse.SUPPRESS
    )
    gcp_args.add_no_cleanup(parser)
    # Optional (number of) SSD scratch disks because these can only be attached
    # at instance launch time, compared to the other (persistent) disks
    parser.add_argument(
        '--ssd-scratch-disks',
        metavar='N',
        type=int,
        default=0,
        dest='ssd_scratch_disks',
        help='Number of SSD scratch disks to be attached (max. 8)'
    )
