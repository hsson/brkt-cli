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
from brkt_cli.dev_arg import add_hidden_argument
from brkt_cli.esx import esx_args


def setup_wrap_with_esx_host_args(parser, dev_help):
    parser.add_argument(
        'vmdk',
        metavar='VMDK-NAME',
        help='The Guest VMDK path (in the datastore) that will be encrypted'
    )
    esx_args.add_vcenter_host(parser, use_esx=True)
    esx_args.add_vcenter_port(parser, use_esx=True)
    esx_args.add_vcenter_datastore(parser, use_esx=True)
    esx_args.add_vcenter_network_name(parser, use_esx=True)
    esx_args.add_cpu(parser, help="Number of CPUs to assign to the VM")
    esx_args.add_memory(parser, help="Memory to assign to the VM")
    parser.add_argument(
        '--vm-name',
        metavar='NAME',
        dest='vm_name',
        help='Specify the name of the launched VM',
        required=False
    )
    esx_args.add_ovf_source_directory(parser)
    esx_args.add_metavisor_ovf_image_name(parser)
    esx_args.add_metavisor_version(parser)
    esx_args.add_disk_type(parser)
    esx_args.add_encryptor_vmdk(parser, dev_help)
    esx_args.add_ssh_public_key(parser, dev_help)
    esx_args.add_bucket_name(parser, dev_help)
    esx_args.add_nic_type(parser, dev_help)
    esx_args.add_http_s3_proxy(parser, dev_help)
    esx_args.add_no_cleanup(parser, dev_help)
    add_hidden_argument(
        parser,
        dev_help,
        '--guest-fqdn',
        metavar='FQDN',
        dest='guest_fqdn',
        help='Used by Metavisor as the CN field of the Subject DN in the cert requests it submits to an EST server '
             '(for North-South VPN tunneling).'
    )
