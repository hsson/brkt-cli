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
"""
Create a Bracket wrapped instance based on an existing unencrypted VMDK

Overview of the process:
    * Create a VM based on the metavisor VMDK.
    * Attach the unencrypted guest VMDK to the above VM
    * Pass appropriate guestInfo to the VM to indicate that the guest
        volume is unencrypted
    * Start the VM and display its IP address

Before running, do "pip install pyvmomi".
"""

import logging
from brkt_cli.esx.esx_service import (
    launch_mv_vm_from_s3,
    validate_local_mv_ovf
)


log = logging.getLogger(__name__)


def wrap_from_s3(vc_swc, guest_vmdk, vm_name=None,
                 ovf_name=None, download_file_list=None,
                 user_data_str=None, cleanup=True):
    vm = None
    try:
        if (ovf_name is None or download_file_list is None):
            log.error("Cannot get metavisor OVF from S3")
            raise Exception("Invalid MV OVF")
        vm = launch_mv_vm_from_s3(vc_swc, ovf_name,
                                  download_file_list, vm_name,
                                  cleanup)
        guest_vmdk_path = vc_swc.get_datastore_path(guest_vmdk)
        vc_swc.add_disk(vm, filename=guest_vmdk_path, unit_number=1)
        if user_data_str:
            vc_swc.send_userdata(vm, user_data_str)
        vc_swc.power_on(vm)
        ip_addr = vc_swc.get_ip_address(vm)
        log.info("VM ip address is %s", ip_addr)
    except Exception as e:
        log.exception("Failed to launch wrapped guest from S3 (%s)", e)
        if (vm is not None):
            vc_swc.destroy_vm(vm)
        raise


def wrap_from_local_ovf(vc_swc, guest_vmdk, vm_name=None,
                        source_image_path=None, ovf_image_name=None,
                        user_data_str=None):
    vm = None
    try:
        if ((source_image_path is None) or
            (ovf_image_name is None)):
            log.error("Metavisor OVF path needs to be specified")
            return
        # Launch OVF
        log.info("Launching VM from local OVF")
        ovf_image_name = ovf_image_name + ".ovf"
        validate_local_mv_ovf(source_image_path, ovf_image_name)
        vm = vc_swc.upload_ovf_to_vcenter(source_image_path,
                                          ovf_image_name,
                                          vm_name=vm_name)
        guest_vmdk_path = vc_swc.get_datastore_path(guest_vmdk)
        vc_swc.add_disk(vm, filename=guest_vmdk_path, unit_number=1)
        if user_data_str:
            vc_swc.send_userdata(vm, user_data_str)
        vc_swc.power_on(vm)
        ip_addr = vc_swc.get_ip_address(vm)
        log.info("VM ip address is %s", ip_addr)
    except Exception as e:
        log.exception("Failed to launch from metavisor OVF (%s)", e)
        if (vm is not None):
            vc_swc.destroy_vm(vm)
        raise


def wrap_from_vmdk(vc_swc, guest_vmdk, vm_name=None,
                   metavisor_vmdk=None, user_data_str=None):
    try:
        vm = None
        if (metavisor_vmdk is None):
            log.error("Metavisor VMDK is not specified")
            return
        # Add datastore path to the vmdk
        metavisor_vmdk_path = vc_swc.get_datastore_path(metavisor_vmdk)
        guest_vmdk_path = vc_swc.get_datastore_path(guest_vmdk)
        # Create a metavisor VM
        vm = vc_swc.create_vm(vm_name=vm_name)
        # Attach metavisor vmdk as root disk
        vc_swc.add_disk(vm, filename=metavisor_vmdk_path, unit_number=0)
        # Attach guest vmdk as first attached disk
        vc_swc.add_disk(vm, filename=guest_vmdk_path, unit_number=1)
        if user_data_str:
            vc_swc.send_userdata(vm, user_data_str)
        vc_swc.power_on(vm)
        ip_addr = vc_swc.get_ip_address(vm)
        log.info("VM ip address is %s", ip_addr)
    except Exception as e:
        log.exception("Failed to launch metavisor VMDK (%s)", e)
        if (vm is not None):
            vc_swc.destroy_vm(vm)
        raise
