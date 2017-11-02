import logging
import unittest
import datetime

# import test
from brkt_cli import util
from brkt_cli.esx import (
    encrypt_vmdk,
    update_vmdk,
    esx_service,
    wrap_image
)
from brkt_cli.test_encryptor_service import (
    DummyEncryptorService,
    FailedEncryptionService
)
from brkt_cli.util import (
    CRYPTO_GCM,
    CRYPTO_XTS
)
from brkt_cli.instance_config import INSTANCE_UPDATER_MODE

TOKEN = 'token'

log = logging.getLogger(__name__)


class NullHandler(logging.Handler):
    def emit(self, record):
        pass


class DummyValues():
    def __init__(self):
        self.cleanup = True
        self.create_ovf = False
        self.create_ova = False
        self.crypto = CRYPTO_XTS
        self.encrypted_ovf_name = None
        self.encryptor_vmdk = None
        self.image_name = None
        self.ovftool_path = None
        self.serial_port_file_name = None
        self.single_disk = True
        self.source_image_path = "mv-ovf"
        self.ssh_public_key_file = None
        self.status_port = 80
        self.target_path = None
        self.template_vm_name = "template-encrypted"
        self.vcenter_datacenter = None
        self.vcenter_host = None
        self.vcenter_port = None
        self.vmdk = "guest-vmdk"


class DummyDisk(object):
    def __init__(self, size, filename):
        self.size = size
        self.filename = filename


class DummyVM(object):
    def __init__(self, name, cpu, memory, poweron=False, template=False):
        self.name = name
        self.cpu = cpu
        self.memory = memory
        self.poweron = poweron
        self.template = template
        self.userdata = None
        self.disks = dict()

    def add_disk(self, disk, unit_number):
        self.disks[unit_number] = disk

    def remove_disk(self, unit_number):
        self.disks.pop(unit_number)


class DummyOVF(object):
    def __init__(self, vm, name):
        self.vm = vm
        self.name = name


class DummyVCenterService(esx_service.BaseVCenterService):
    def __init__(self):
        self.vms = dict()
        self.disks = dict()
        self.connection = False
        super(DummyVCenterService, self).__init__(
            'testhost', 'testuser', 'testpass', 'testport', 'testdcname',
            'testdsname', False, 'testclustername', 1, 1024, "123",
            'VM Network', 'Port')

    def connect(self):
        self.connection = True

    def disconnect(self):
        self.connection = False

    def connected(self):
        return self.connection

    def validate_connection(self):
        return

    def get_session_id(self):
        return self.session_id

    def get_datastore_path(self, vmdk_name):
        return vmdk_name

    def validate_vcenter_params(self):
        return

    def find_vm(self, vm_name):
        return self.vms.get(vm_name)

    def power_on(self, vm):
        vm.poweron = True

    def power_off(self, vm):
        vm.poweron = False

    def destroy_vm(self, vm):
        disk_list = vm.disks.keys()
        for c_unit in disk_list:
            c_disk = vm.disks.get(c_unit)
            self.disks.pop(c_disk.filename)
        self.vms.pop(vm.name)

    def get_ip_address(self, vm):
        return ("10.10.10.1")

    def create_vm(self, memory_gb=1, no_of_cpus=1):
        timestamp = datetime.datetime.utcnow().isoformat() + 'Z'
        vm_name = "VM-" + timestamp
        vm = DummyVM(vm_name, no_of_cpus, memory_gb)
        self.vms[vm_name] = vm
        return vm

    def reconfigure_vm_cpu_ram(self, vm):
        vm.cpu = self.no_of_cpus
        vm.memory = self.memory_gb

    def rename_vm(self, vm, new_name):
        del self.vms[vm.name]
        vm.name = new_name
        self.vms[new_name] = vm
        disk_list = vm.disks.keys()
        for c_unit in disk_list:
            c_disk = vm.disks.get(c_unit)
            name = c_disk.filename
            size = c_disk.size
            new_d_name = new_name + name
            self.disks.pop(name)
            vm.disks.pop(c_unit)
            new_disk = DummyDisk(size, new_d_name)
            self.disks[new_d_name] = new_disk
            vm.add_disk(new_disk, c_unit)

    def add_disk(self, vm, disk_size=12*1024*1024,
                 filename=None, unit_number=0):
        diskname = vm.name + str(unit_number)
        if filename:
            disk = self.disks[filename]
            disk_size = disk.size
        disk = DummyDisk(disk_size, diskname)
        vm.add_disk(disk, unit_number)
        self.disks[diskname] = disk

    def detach_disk(self, vm, unit_number=2):
        disk = vm.disks.get(unit_number)
        vm.remove_disk(unit_number)
        return disk

    def reattach_disk(self, vm, old_unit_number, new_unit_number):
        disk = vm.disks.get(old_unit_number)
        vm.remove_disk(old_unit_number)
        vm.add_disk(disk, new_unit_number)

    def clone_disk(self, source_disk=None, source_disk_name=None,
                   dest_disk=None, dest_disk_name=None):
        if source_disk is None:
            source_disk = self.disks[source_disk_name]
        if (dest_disk_name is None):
            if (dest_disk is None):
                raise Exception("Cannot clone disk as destination "
                                "not specified")
            dest_disk_name = source_disk.filename + dest_disk.filename
        disk = DummyDisk(source_disk.size, dest_disk_name)
        self.disks[dest_disk_name] = disk
        return dest_disk_name

    def delete_disk(self, disk_name):
        del self.disks[disk_name]

    def get_disk(self, vm, unit_number):
        # return vim.vm.device.VirtualDisk
        return vm.disks.get(unit_number)

    def get_disk_size(self, vm, unit_number):
        disk = vm.disks.get(unit_number)
        return disk.size

    def clone_vm(self, vm, power_on=False, vm_name=None, template=False):
        if vm_name is None:
            timestamp = datetime.datetime.utcnow().isoformat() + 'Z'
            vm_name = "template-vm-" + timestamp
        clone = DummyVM(vm_name, vm.cpu, vm.memory,
                        poweron=power_on, template=template)
        disk_list = vm.disks.keys()
        for c_unit in disk_list:
            c_disk = vm.disks.get(c_unit)
            self.add_disk(clone, c_disk.size, unit_number=c_unit)
        self.vms[vm_name] = clone
        return clone

    def create_userdata_str(self, instance_config, update=False,
                            ssh_key_file=None,
                            rescue_proto=None, rescue_url=None):
        brkt_config = {}
        if instance_config:
            brkt_config = instance_config.get_brkt_config()
        if update is True:
            instance_config.set_mode(INSTANCE_UPDATER_MODE)
        if ssh_key_file:
            with open(ssh_key_file, 'r') as f:
                key_value = (f.read()).strip()
            brkt_config['ssh-public-key'] = key_value
        if rescue_proto:
            brkt_config = dict()
            brkt_config['rescue'] = dict()
            brkt_config['rescue']['protocol'] = rescue_proto
            brkt_config['rescue']['url'] = rescue_url
        instance_config.set_brkt_config(brkt_config)
        user_data = instance_config.make_userdata()
        return user_data

    def send_userdata(self, vm, user_data_str):
        vm.userdata = user_data_str

    def keep_lease_alive(self, lease):
        return

    def export_to_ovf(self, vm, target_path, ovf_name=None):
        ovf = DummyOVF(vm, ovf_name)
        return ovf

    def convert_ovf_to_ova(self, ovftool_path, ovf_path):
        return

    def convert_ova_to_ovf(self, ovftool_path, ova_path):
        return

    def get_ovf_descriptor(self, ovf_path):
        return ovf_path

    def upload_ovf_to_vcenter(self, target_path, ovf_name, vm_name=None):
        ovf = target_path
        if target_path == "./":
            ovf = self.ovfs[0]
        return self.clone_vm(ovf.vm, vm_name=ovf_name)

    def get_vm_name(self, vm):
        return vm.name

    def get_disk_name(self, disk):
        return disk.filename


class TestRunEncryption(unittest.TestCase):

    def setUp(self):
        util.SLEEP_ENABLED = False
        h = NullHandler()
        logging.getLogger("brkt_cli").addHandler(h)

    def test_smoke(self):
        values = DummyValues()
        vc_swc = DummyVCenterService()
        mv_vm = DummyVM("mv_image", 1, 1024)
        disk = DummyDisk(12*1024*1024, None)
        mv_vm.add_disk(disk, 0)
        mv_ovf = DummyOVF(mv_vm, "mv-ovf")
        vc_swc.ovfs = [mv_ovf]
        guest_vmdk_disk = DummyDisk(16*1024*1024, values.vmdk)
        vc_swc.disks[values.vmdk] = guest_vmdk_disk
        values.crypto = CRYPTO_GCM
        encrypt_vmdk.encrypt_from_s3(vc_swc, DummyEncryptorService, values,
                                     download_file_list=[], user_data_str=None)
        self.assertEqual(len(vc_swc.vms), 1)
        self.assertEqual(len(vc_swc.disks), 4)
        template_vm = (vc_swc.vms.values())[0]
        self.assertEqual(len(template_vm.disks), 1)
        self.assertEqual(template_vm.name, "template-encrypted")
        # Verify disk size for GCM
        self.assertEqual(template_vm.disks[0].size, 38*1024*1024)
        self.assertTrue(template_vm.template)

        values.crypto = CRYPTO_XTS
        encrypt_vmdk.encrypt_from_s3(vc_swc, DummyEncryptorService, values,
                                     download_file_list=[], user_data_str=None)
        self.assertEqual(len(vc_swc.vms), 1)
        self.assertEqual(len(vc_swc.disks), 4)
        template_vm = (vc_swc.vms.values())[0]
        self.assertEqual(len(template_vm.disks), 1)
        self.assertEqual(template_vm.name, "template-encrypted")
        # Verify disk size for XTS
        self.assertEqual(template_vm.disks[0].size, 22*1024*1024)
        self.assertTrue(template_vm.template)

    def test_cleanup_on_bad_guest_image(self):
        values = DummyValues()
        vc_swc = DummyVCenterService()
        mv_vm = DummyVM("mv_image", 1, 1024)
        disk = DummyDisk(12*1024*1024, None)
        mv_vm.add_disk(disk, 0)
        mv_ovf = DummyOVF(mv_vm, "mv-ovf")
        vc_swc.ovfs = [mv_ovf]
        with self.assertRaises(Exception):
            encrypt_vmdk.encrypt_from_s3(vc_swc, DummyEncryptorService, values,
                                         download_file_list=[],
                                         user_data_str=None)
        self.assertEqual(len(vc_swc.vms), 0)
        self.assertEqual(len(vc_swc.disks), 0)

    def test_cleanup_bad_mv_image(self):
        values = DummyValues()
        vc_swc = DummyVCenterService()
        with self.assertRaises(Exception):
            encrypt_vmdk.encrypt_from_s3(vc_swc, DummyEncryptorService, values,
                                         download_file_list=[],
                                         user_data_str=None)
        self.assertEqual(len(vc_swc.vms), 0)
        self.assertEqual(len(vc_swc.disks), 0)

    def test_cleanup_bad_encryption(self):
        values = DummyValues()
        vc_swc = DummyVCenterService()
        mv_vm = DummyVM("mv_image", 1, 1024)
        disk = DummyDisk(12*1024*1024, None)
        mv_vm.add_disk(disk, 0)
        mv_ovf = DummyOVF(mv_vm, "mv-ovf")
        vc_swc.ovfs = [mv_ovf]
        guest_vmdk_disk = DummyDisk(16*1024*1024, values.vmdk)
        vc_swc.disks[values.vmdk] = guest_vmdk_disk
        try:
            encrypt_vmdk.encrypt_from_s3(vc_swc, FailedEncryptionService,
                                         values, download_file_list=[],
                                         user_data_str=None)
            self.fail('Encryption should have failed')
        except Exception:
            self.assertEqual(len(vc_swc.vms), 0)
            self.assertEqual(len(vc_swc.disks), 2)


class TestRunUpdate(unittest.TestCase):

    def setUp(self):
        util.SLEEP_ENABLED = False
        h = NullHandler()
        logging.getLogger("brkt_cli").addHandler(h)

    def test_smoke(self):
        values = DummyValues()
        vc_swc = DummyVCenterService()
        mv_vm = DummyVM("mv_image", 1, 1024)
        disk = DummyDisk(14*1024*1024, None)
        mv_vm.add_disk(disk, 0)
        mv_ovf = DummyOVF(mv_vm, "mv-ovf")
        vc_swc.ovfs = [mv_ovf]
        template_vm = vc_swc.create_vm(1024, 1)
        template_vm.template = True
        values.template_vm_name = template_vm.name
        vc_swc.add_disk(template_vm, disk_size=12*1024*1024, unit_number=0)
        vc_swc.add_disk(template_vm, disk_size=16*1024*1024, unit_number=1)
        update_vmdk.update_from_s3(vc_swc, DummyEncryptorService, values,
                                   download_file_list=[], user_data_str=None)
        self.assertEqual(len(vc_swc.vms), 1)
        self.assertEqual(len(vc_swc.disks), 3)
        template_vm = (vc_swc.vms.values())[0]
        self.assertEqual(len(template_vm.disks), 2)
        self.assertEqual(template_vm.name, values.template_vm_name)
        self.assertEqual(template_vm.disks[0].size, 14*1024*1024)
        self.assertEqual(template_vm.disks[1].size, 16*1024*1024)
        self.assertTrue(template_vm.template)

    def test_cleanup_bad_mv_image(self):
        values = DummyValues()
        vc_swc = DummyVCenterService()
        template_vm = vc_swc.create_vm(1024, 1)
        template_vm.template = True
        values.template_vm_name = template_vm.name
        vc_swc.add_disk(template_vm, disk_size=12*1024*1024, unit_number=0)
        vc_swc.add_disk(template_vm, disk_size=33*1024*1024, unit_number=1)
        with self.assertRaises(Exception):
            update_vmdk.update_from_s3(vc_swc, DummyEncryptorService, values,
                                       download_file_list=[],
                                       user_data_str=None)
        self.assertEqual(len(vc_swc.vms), 1)
        self.assertEqual(len(vc_swc.disks), 2)
        template_vm = (vc_swc.vms.values())[0]
        self.assertEqual(len(template_vm.disks), 2)
        self.assertEqual(template_vm.name, values.template_vm_name)
        self.assertEqual(template_vm.disks[0].size, 12*1024*1024)
        self.assertEqual(template_vm.disks[1].size, 33*1024*1024)
        self.assertTrue(template_vm.template)

    def test_cleanup_bad_encryption(self):
        values = DummyValues()
        vc_swc = DummyVCenterService()
        mv_vm = DummyVM("mv_image", 1, 1024)
        disk = DummyDisk(14*1024*1024, None)
        mv_vm.add_disk(disk, 0)
        mv_ovf = DummyOVF(mv_vm, "mv-ovf")
        vc_swc.ovfs = [mv_ovf]
        template_vm = vc_swc.create_vm(1024, 1)
        template_vm.template = True
        values.template_vm_name = template_vm.name
        vc_swc.add_disk(template_vm, disk_size=12*1024*1024, unit_number=0)
        vc_swc.add_disk(template_vm, disk_size=33*1024*1024, unit_number=1)
        with self.assertRaises(Exception):
            update_vmdk.update_from_s3(vc_swc, FailedEncryptionService,
                                       values, download_file_list=[],
                                       user_data_str=None)
        self.assertEqual(len(vc_swc.vms), 1)
        self.assertEqual(len(vc_swc.disks), 2)
        template_vm = (vc_swc.vms.values())[0]
        self.assertEqual(len(template_vm.disks), 2)
        self.assertEqual(template_vm.name, values.template_vm_name)
        self.assertEqual(template_vm.disks[0].size, 12*1024*1024)
        self.assertEqual(template_vm.disks[1].size, 33*1024*1024)
        self.assertTrue(template_vm.template)


class TestWrappedGuest(unittest.TestCase):

    def setUp(self):
        util.SLEEP_ENABLED = False
        h = NullHandler()
        logging.getLogger("brkt_cli").addHandler(h)

    def test_smoke(self):
        vc_swc = DummyVCenterService()
        mv_vm = DummyVM("mv_image", 1, 1024)
        disk = DummyDisk(12*1024*1024, None)
        mv_vm.add_disk(disk, 0)
        mv_ovf = DummyOVF(mv_vm, "mv-ovf")
        vc_swc.ovfs = [mv_ovf]
        guest_vmdk = "guest-vmdk"
        guest_vmdk_disk = DummyDisk(16*1024*1024, guest_vmdk)
        vc_swc.disks[guest_vmdk] = guest_vmdk_disk
        wrap_image.wrap_from_s3(
            vc_swc,
            guest_vmdk,
            vm_name="template-unencrypted",
            ovf_name="mv-ovf",
            download_file_list=[],
            user_data_str=None
        )
        self.assertEqual(len(vc_swc.vms), 1)
        template_vm = (vc_swc.vms.values())[0]
        self.assertEqual(len(template_vm.disks), 2)
        # With vCenter, the VM name will be set as "VM-<Timestamp>"
        self.assertNotEqual(template_vm.name, "template-unencrypted")
        self.assertEqual(template_vm.disks[0].size, 12*1024*1024)
        # Verify disk size remains same for unencrypted guest
        self.assertEqual(template_vm.disks[1].size, 16*1024*1024)
        # Will be created as an instance, instead of a template
        self.assertFalse(template_vm.template)
