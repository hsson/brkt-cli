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
import logging
import os
from brkt_cli.encryptor_service import (
    encryptor_did_single_disk,
    wait_for_encryptor_up,
    wait_for_encryption,
)
from brkt_cli.util import Deadline
from brkt_cli.esx.esx_service import (
    launch_mv_vm_from_s3,
    validate_local_mv_ovf
)


log = logging.getLogger(__name__)


def update_ovf_image_mv_vm(vc_swc, enc_svc_cls, values, guest_vm, mv_vm,
                           user_data_str, static_ip=None):
    new_root_disk_name = None
    try:
        # Reconfigure VM with more CPUs and memory
        vc_swc.reconfigure_vm_cpu_ram(mv_vm)
        if static_ip:
            vc_swc.configure_static_ip(mv_vm, static_ip)
        # Clone the first disk of the encrypted guest VM and attach the
        # clone to the MV VM.
        log.info("Cloning guest root disk")
        guest_root_disk = vc_swc.get_disk(guest_vm, unit_number=0)
        guest_root_disk_name = vc_swc.get_disk_name(guest_root_disk)
        new_root_disk_name = vc_swc.get_session_vmdk_name(guest_root_disk_name)
        vc_swc.clone_disk(source_disk=guest_root_disk,
                          dest_disk_name=new_root_disk_name)
        vc_swc.add_disk(mv_vm, filename=new_root_disk_name, unit_number=1)
        # Power on the MV VM and wait for encryption
        vc_swc.power_on(mv_vm)
        # Send user data
        vc_swc.send_userdata(mv_vm, user_data_str)
        ip_addr = vc_swc.get_ip_address(mv_vm)
        log.info("MV VM ip address is %s", ip_addr)
        # wait for encryption to complete
        host_ips = [ip_addr]
        enc_svc = enc_svc_cls(host_ips, port=values.status_port)
        log.info('Waiting for updater service on port %s on %s',
                 enc_svc.port, ', '.join(host_ips))
        wait_for_encryptor_up(enc_svc, Deadline(600))
        try:
            wait_for_encryption(enc_svc)
        except Exception as e:
            log.exception("Update failed with error %s", e)
            raise

        single_disk = encryptor_did_single_disk(enc_svc)

        # Power off the MV VM
        vc_swc.power_off(mv_vm)

        # Create final disk attachment
        if single_disk:
            guest_root_disk = vc_swc.detach_disk(guest_vm, unit_number=0)
            new_root_disk = vc_swc.detach_disk(mv_vm, unit_number=1)
            vc_swc.add_disk(guest_vm,
                            filename=vc_swc.get_disk_name(new_root_disk),
                            unit_number=0)
        else:
            guest_old_disk = vc_swc.detach_disk(guest_vm, unit_number=1)
            mv_old_disk = vc_swc.detach_disk(guest_vm, unit_number=0)
            # Clone and attach new MV disk to guest VM
            log.info("Cloning Metavisor disk")
            new_disk = vc_swc.get_disk(mv_vm, unit_number=0)
            u_disk_name = vc_swc.clone_disk(source_disk=new_disk,
                                            dest_disk=mv_old_disk)
            # Add disks to guest VM
            vc_swc.add_disk(guest_vm, filename=u_disk_name, unit_number=0)
            vc_swc.add_disk(guest_vm,
                            filename=vc_swc.get_disk_name(guest_old_disk),
                            unit_number=1)
            vc_swc.delete_disk(new_root_disk_name)
            new_root_disk_name = None

        # Create images
        if values.encrypted_ovf_name:
            log.info("Creating images")
            if values.target_path is None:
                raise Exception("Cannot create ova/ovf as target path is None")
            if values.create_ova:
                # delete the old mf file
                os.remove(os.path.join(values.target_path,
                                       values.encrypted_ovf_name + ".mf"))
            # import the new OVF
            ovf = vc_swc.export_to_ovf(guest_vm, values.target_path,
                                       ovf_name=values.encrypted_ovf_name)
            if values.create_ova:
                if values.ovftool_path is not None:
                    # delete the old ova
                    os.remove(os.path.join(values.target_path,
                                           values.encrypted_ovf_name + ".ova"))
                    ova = vc_swc.convert_ovf_to_ova(values.ovftool_path, ovf)
                    print(ova)
            else:
                print(ovf)
        else:
            # delete the old vm template
            template_vm = vc_swc.find_vm(values.template_vm_name)
            old_template_vm_name = None
            if template_vm:
                old_template_vm_name = values.template_vm_name + "-" + \
                                       vc_swc.session_id
                log.info("Renaming the old template to %s",
                         old_template_vm_name)
                try:
                    vc_swc.rename_vm(template_vm, old_template_vm_name)
                except Exception as e:
                    if "vim.fault.FileFault" not in str(e):
                        raise
                    log.info("Rename VM not supported. "
                             "Deleting the old template %s.", template_vm.name)
                    if not vc_swc.find_vm(values.template_vm_name):
                        vc_swc.change_vm_name(template_vm,
                                              values.template_vm_name)
                    vc_swc.destroy_vm(template_vm)
            # clone the vm to create template
            log.info("Creating the template VM")
            template_vm = vc_swc.clone_vm(guest_vm,
                                          vm_name=values.template_vm_name,
                                          template=True)
            print(vc_swc.get_vm_name(template_vm))
            if old_template_vm_name:
                old_template = vc_swc.find_vm(old_template_vm_name)
                if old_template:
                    log.info("Deleting the old template")
                    vc_swc.destroy_vm(old_template)
    except Exception as e:
        log.exception("Failed to update the image with error %s", e)
        if new_root_disk_name:
            vc_swc.delete_disk(new_root_disk_name)
        raise
    finally:
        vc_swc.destroy_vm(guest_vm)
        vc_swc.destroy_vm(mv_vm)
    log.info("Done")


def launch_guest_vm(vc_swc, values):
    log.info("Launching encrypted guest VM")
    if values.template_vm_name:
        template_vm = vc_swc.find_vm(values.template_vm_name)
        vm = vc_swc.clone_vm(template_vm)
    elif values.encrypted_ovf_name:
        if values.create_ova:
            ova = os.path.join(values.target_path,
                               values.encrypted_ovf_name + ".ova")
            vc_swc.convert_ova_to_ovf(values.ovftool_path, ova)
        vm = vc_swc.upload_ovf_to_vcenter(values.target_path,
                                          values.encrypted_ovf_name + ".ovf",
                                          validate_mf=False)
    else:
        log.error("Cannot launch guest VM without template VM/OVF/OVA")
        vm = None
    return vm


def update_from_s3(vc_swc, enc_svc_cls, values, download_file_list=None,
                   user_data_str=None, static_ip=None):
    guest_vm = None
    mv_vm = None
    try:
        guest_vm = launch_guest_vm(vc_swc, values)
    except Exception as e:
        log.exception("Failed to lauch guest VM (%s)", e)
        if (guest_vm is not None):
            vc_swc.destroy_vm(guest_vm)
        raise
    try:
        if values.source_image_path is None or download_file_list is None:
            log.error("Cannot get metavisor OVF from S3")
            raise Exception("Invalid MV OVF")
        mv_vm = launch_mv_vm_from_s3(vc_swc, values.source_image_path,
                                     download_file_list,
                                     vm_name=None, cleanup=values.cleanup)
    except Exception as e:
        log.exception("Failed to launch metavisor OVF from S3 (%s)", e)
        if (mv_vm is not None):
            vc_swc.destroy_vm(mv_vm)
        if (guest_vm is not None):
            vc_swc.destroy_vm(guest_vm)
        raise
    update_ovf_image_mv_vm(vc_swc, enc_svc_cls, values, guest_vm, mv_vm,
                           user_data_str, static_ip)


def update_from_local_ovf(vc_swc, enc_svc_cls, values, user_data_str=None,
                          static_ip=None):
    guest_vm = None
    mv_vm = None
    if values.source_image_path is None or values.image_name is None:
        log.error("Metavisor OVF path needs to be specified")
        return
    try:
        guest_vm = launch_guest_vm(vc_swc, values)
    except Exception as e:
        log.exception("Failed to lauch guest VM (%s)", e)
        if (guest_vm is not None):
            vc_swc.destroy_vm(guest_vm)
        raise
    try:
        log.info("Launching MV VM from local OVF")
        validate_local_mv_ovf(values.source_image_path, values.image_name)
        mv_vm = vc_swc.upload_ovf_to_vcenter(values.source_image_path,
                                             values.image_name)
    except Exception as e:
        log.exception("Failed to launch from metavisor OVF (%s)", e)
        if (mv_vm is not None):
            vc_swc.destroy_vm(mv_vm)
        if (guest_vm is not None):
            vc_swc.destroy_vm(guest_vm)
        raise
    update_ovf_image_mv_vm(vc_swc, enc_svc_cls, values, guest_vm, mv_vm,
                           user_data_str, static_ip)


def update_from_vmdk(vc_swc, enc_svc_cls, values, user_data_str=None,
                     static_ip=None):
    guest_vm = None
    mv_vm = None
    if values.encryptor_vmdk is None:
        log.error("Metavisor VMDK is not specified")
        return
    try:
        guest_vm = launch_guest_vm(vc_swc, values)
    except Exception as e:
        log.exception("Failed to lauch guest VM (%s)", e)
        if (guest_vm is not None):
            vc_swc.destroy_vm(guest_vm)
        raise
    try:
        # Add datastore path to the vmdk
        metavisor_vmdk_path = vc_swc.get_datastore_path(values.encryptor_vmdk)
        # Create a metavisor VM
        vm = vc_swc.create_vm()
        # Attach metavisor vmdk as root disk
        vc_swc.add_disk(vm, filename=metavisor_vmdk_path, unit_number=0)
    except Exception as e:
        log.exception("Failed to launch metavisor VMDK (%s)", e)
        if (mv_vm is not None):
            vc_swc.destroy_vm(mv_vm)
        if (guest_vm is not None):
            vc_swc.destroy_vm(guest_vm)
        raise
    update_ovf_image_mv_vm(vc_swc, enc_svc_cls, values, guest_vm, mv_vm,
                           user_data_str, static_ip)
