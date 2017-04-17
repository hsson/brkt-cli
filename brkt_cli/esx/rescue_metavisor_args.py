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
from brkt_cli.esx import esx_args


def setup_rescue_metavisor_args(parser):
    esx_args.add_vcenter_host(parser)
    esx_args.add_vcenter_port(parser)
    esx_args.add_vcenter_datacenter(parser)
    esx_args.add_vcenter_datastore(parser)
    esx_args.add_vcenter_cluster(parser)
    esx_args.add_no_verify_cert(parser)
    parser.add_argument(
        'vm_name',
        metavar='VM-NAME',
        help='Specify the name of the metavisor VM'
    )
    parser.add_argument(
        '--rescue-upload-protocol',
        metavar='PROTOCOL',
        choices=['http', 'https'],
        dest='protocol',
        help=(
            'Specify the protocol which metavisor '
            'will use to upload the diagnostics information'
        ),
        required=True
    )
    parser.add_argument(
        '--rescue-upload-url',
        metavar='URL',
        dest='url',
        help=(
            'Specify the URL location to which metavisor '
            'will upload the diagnostics information'
        ),
        required=True
    )
