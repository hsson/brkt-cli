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


def setup_assign_static_ip_args(parser):
    parser.add_argument(
        'vm',
        metavar='VM-NAME',
        help='The name of the VM to be assigned the static IP'
    )
    esx_args.add_vcenter_host(parser)
    esx_args.add_vcenter_port(parser)
    esx_args.add_static_ip_address(
        parser,
        help="Specify the static IP address of the VM"
    )
    esx_args.add_static_subnet_mask(
        parser,
        help="Specify the static subnet mask of the VM"
    )
    esx_args.add_static_default_router(
        parser,
        help="Specify the static default router of the VM"
    )
    esx_args.add_static_dns_domain(
        parser,
        help="Specify the static DNS domain of the VM"
    )
    esx_args.add_static_dns_server(
        parser,
        help="Specify the static DNS server of the VM"
    )
    esx_args.add_no_verify_cert(parser)
