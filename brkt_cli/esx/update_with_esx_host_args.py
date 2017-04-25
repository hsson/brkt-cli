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


def setup_update_with_esx_host_args(parser):
    esx_args.add_vcenter_host(parser, use_esx=True)
    esx_args.add_vcenter_port(parser, use_esx=True)
    esx_args.add_vcenter_datastore(parser, use_esx=True)
    esx_args.add_vcenter_network_name(parser, use_esx=True)
    esx_args.add_cpu(parser, help="Number of CPUs to assign to the Updater VM")
    esx_args.add_memory(parser, help="Memory to assign to the Updater VM")
    esx_args.add_encrypted_image_name(
        parser,
        help="Directory to fetch the encrypted OVF/OVA image"
    )
    esx_args.add_template_vm_name(
        parser,
        help="Specify the name of the template VM to be updated"
    )
    parser.add_argument(
        '--update-ovf',
        dest='create_ovf',
        action='store_true',
        default=False,
        help="Update OVF package"
    )
    parser.add_argument(
        '--update-ova',
        dest='create_ova',
        action='store_true',
        default=False,
        help="Update OVA package"
    )
    esx_args.add_encrypted_image_directory(
        parser,
        help="Directory to fetch the encrypted OVF/OVA image"
    )
    esx_args.add_ovftool_path(parser)
    esx_args.add_ovf_source_directory(parser)
    esx_args.add_metavisor_ovf_image_name(parser)
    esx_args.add_metavisor_version(parser)
    esx_args.add_console_file_name(parser)
    esx_args.add_disk_type(parser)
    esx_args.add_encryptor_vmdk(parser)
    esx_args.add_ssh_public_key(parser)
    esx_args.add_no_teardown(parser)
    esx_args.add_bucket_name(parser)
    esx_args.add_nic_type(parser)
    esx_args.add_http_s3_proxy(parser)
    esx_args.add_no_cleanup(parser)
