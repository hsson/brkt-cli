import logging
import time
import unittest
import uuid

import test
from brkt_cli import util
from brkt_cli.gcp import encrypt_gcp_image
from brkt_cli.gcp import gcp_service
from brkt_cli.gcp import update_gcp_image
from brkt_cli.gcp import share_logs
from brkt_cli.gcp import wrap_gcp_image
from brkt_cli.instance_config import InstanceConfig
from brkt_cli.util import CRYPTO_GCM
from brkt_cli.test_encryptor_service import (
    DummyEncryptorService,
    FailedEncryptionService
)
from brkt_cli.validation import ValidationError

NONEXISTANT_IMAGE = 'image'
NONEXISTANT_PROJECT = 'project'
IGNORE_IMAGE = 'ignore'
TOKEN = 'token'

log = logging.getLogger(__name__)


def _new_id():
    return uuid.uuid4().hex[:6]


class DummyGCPService(gcp_service.BaseGCPService):
    def __init__(self):
        super(DummyGCPService, self).__init__('testproject', _new_id(), log)

    def cleanup(self, zone, encryptor_image, keep_encryptor=False):
        for disk in self.disks[:]:
            if self.disk_exists(zone, disk):
                self.wait_for_detach(zone, disk)
                self.delete_disk(zone, disk)
        for instance in self.instances:
            self.delete_instance(zone, instance)
        if not keep_encryptor:
            self.delete_image(encryptor_image)

    class OACInserter():
        def execute(self):
            return

    class OAC():
        def insert(self, bucket, object, body):
            oacInserter = DummyGCPService.OACInserter()
            return oacInserter

    class Storage():
        def objectAccessControls(self):
            oac = DummyGCPService.OAC()
            return oac

    storage = Storage()

    def list_zones(self):
        return ['us-central1-a']

    def get_session_id(self):
        return self.session_id

    def get_snapshot(self, name):
        return {'status': 'READY', 'diskSizeGb': '1'}

    def validate_file_name(self, path):
        return False

    def validate_bucket_name(self, bucket):
        return False

    def get_public_image(self):
        return

    def check_bucket_name(self, bucket, project):
        return

    def wait_bucket_file(self, bucket, path):
        return True

    def check_bucket_file(self, bucket, path):
        return

    def wait_snapshot(self, snapshot):
        while True:
            if self.get_snapshot(snapshot)['status'] == 'READY':
                return
            time.sleep(5)

    def get_network(self, nw):
        if nw == 'test-nw' or nw == 'default':
            return True
        return False

    def get_image(self, image, image_project):
        if image == NONEXISTANT_IMAGE:
            raise
        if image_project and image_project == NONEXISTANT_PROJECT:
            raise
        return True

    def image_exists(self, image, image_project=None):
        try:
            self.get_image(image, image_project)
        except:
            return False
        if image == 'encryptor-image' or image == IGNORE_IMAGE:
            return True
        else:
            return False

    def project_exists(self, project=None):
        if project == 'testproject':
            return True
        return False

    def delete_instance(self, zone, instance):
        if instance in self.instances:
            self.instances.remove(instance)

    def delete_disk(self, zone, disk):
        if disk in self.disks:
            self.disks.remove(disk)
            return
        raise test.TestException('disk doesnt exist')

    def wait_instance(self, name, zone):
        return

    def get_instance_ip(self, name, zone):
        return

    def get_private_ip(self, name, zone):
        return

    def detach_disk(self, zone, instance, diskName):
        return self.wait_for_detach(zone, diskName)

    def wait_for_disk(self, zone, diskName):
        return

    def get_disk_size(self, zone, diskName):
        return 10

    def wait_for_detach(self, zone, diskName):
        return

    def disk_exists(self, zone, name):
        if name == NONEXISTANT_IMAGE:
            return False
        return True

    def create_snapshot(self, zone, disk, snapshot_name):
        return

    def delete_snapshot(self, snapshot_name):
        return

    def disk_from_snapshot(self, zone, snapshot, name):
        return

    def create_disk(self, zone, name, size):
        self.disks.append(name)

    def create_gcp_image_from_disk(self, zone, image_name, disk_name):
        return

    def create_gcp_image_from_file(self, zone, image_name, file_name, bucket):
        return

    def wait_image(self, image_name):
        pass

    def delete_image(self, image_name):
        pass

    def get_younger(self, new, old):
        pass

    def disk_from_image(self, zone, image, name, image_project=None):
        source_disk = "projects/%s/zones/%s/disks/%s" % (image_project, zone, name)
        return {
            'boot': False,
            'autoDelete': False,
            'source': self.gcp_res_uri + source_disk,
        }

    def get_image_file(self, bucket):
        pass

    def get_latest_encryptor_image(self,
                                   zone,
                                   image_name,
                                   bucket,
                                   image_file=None):
        pass

    def run_instance(self,
                     zone,
                     name,
                     image,
                     network=None,
                     subnet=None,
                     disks=[],
                     metadata={},
                     delete_boot=False,
                     block_project_ssh_keys=False,
                     instance_type='n1-standard-4',
                     image_project=None,
                     tags=None):
        self.instances.append(name)
        if not delete_boot:
            self.disks.append(name)

    def get_disk(self, zone, disk_name):
        source_disk = "projects/%s/zones/%s/disks/%s" % (self.project, zone, disk_name)
        return {
            'boot': False,
            'autoDelete': False,
            'source': self.gcp_res_uri + source_disk,
        }

    def set_tags(self, zone, instance, tags):
        return

    def get_tags_fingerprint(self, instance, zone):
        return 'fingerprint'


class DummyValues():
    def __init__(self, image=IGNORE_IMAGE):
        self.bucket = None
        self.cleanup = True
        self.crypto = CRYPTO_GCM
        self.encryptor_image = 'encryptor-image'
        self.gcp_tags = None
        self.image = image
        self.image_file = None
        self.image_project = None
        self.keep_encryptor = False
        self.network = None
        self.single_disk = False
        self.status_port = 80
        self.subnetwork = None
        self.zone = 'us-central1-a'


class TestEncryptedImageName(unittest.TestCase):

    def test_get_image_name(self):
        image_name = 'test'
        n1 = gcp_service.get_image_name(None, image_name)
        n2 = gcp_service.get_image_name(None, image_name)
        self.assertNotEqual(n1, n2)

    def test_long_image_name(self):
        image_name = 'test-image-with-long-name-encrypted-so-we-hit-63-char-limit-a'
        n1 = gcp_service.get_image_name(None, image_name)
        n2 = gcp_service.get_image_name(None, image_name)
        self.assertNotEqual(n1, n2)
        self.assertTrue('64-char-limit' not in n1 and '64-char-limit' not in n2)

    def test_user_supplied_name(self):
        encrypted_image_name = 'something'
        image_name = 'something_else'
        n1 = gcp_service.get_image_name(encrypted_image_name, image_name)
        n2 = gcp_service.get_image_name(encrypted_image_name, None)
        self.assertEqual(n1, n2)
        self.assertEqual(n1, encrypted_image_name)

    def test_image_name(self):
        encrypted_image_name = 'valid-name'
        self.assertEquals(encrypted_image_name,
            gcp_service.validate_image_name(encrypted_image_name))
        with self.assertRaises(ValidationError):
            gcp_service.validate_image_name(None)
        with self.assertRaises(ValidationError):
            gcp_service.validate_image_name('Valid-Name')
        with self.assertRaises(ValidationError):
            gcp_service.validate_image_name('validname-')
        with self.assertRaises(ValidationError):
            gcp_service.validate_image_name('a' * 65)
        for c in '?!#$%^&*~`{}\|"<>()[]./\'@_':
            with self.assertRaises(ValidationError):
                gcp_service.validate_image_name('valid' + c)


class TestRunEncryption(unittest.TestCase):

    def setUp(self):
        util.SLEEP_ENABLED = False

    def test_smoke(self):
        gcp_svc = DummyGCPService()
        encrypted_image = encrypt_gcp_image.encrypt(
            gcp_svc=gcp_svc,
            enc_svc_cls=DummyEncryptorService,
            values=DummyValues(),
            encrypted_image_name='ubuntu-encrypted',
            instance_config=InstanceConfig({'identity_token': TOKEN})
        )
        self.assertIsNotNone(encrypted_image)
        self.assertEqual(len(gcp_svc.disks), 0)
        self.assertEqual(len(gcp_svc.instances), 0)

    def test_cleanup(self):
        gcp_svc = DummyGCPService()
        encrypt_gcp_image.encrypt(
            gcp_svc=gcp_svc,
            enc_svc_cls=DummyEncryptorService,
            values=DummyValues(),
            encrypted_image_name='ubuntu-encrypted',
            instance_config=InstanceConfig({'identity_token': TOKEN})
        )
        self.assertEqual(len(gcp_svc.disks), 0)
        self.assertEqual(len(gcp_svc.instances), 0)

    def test_cleanup_on_fail(self):
        gcp_svc = DummyGCPService()
        with self.assertRaises(Exception):
             encrypt_gcp_image.encrypt(
                gcp_svc=gcp_svc,
                enc_svc_cls=test.FailedEncryptionService,
                values=DummyValues(image='test-ubuntu'),
                encrypted_image_name='ubuntu-encrypted',
                instance_config=InstanceConfig({'identity_token': TOKEN})
            )
        self.assertEqual(len(gcp_svc.disks), 0)
        self.assertEqual(len(gcp_svc.instances), 0)


class TestImageValidation(unittest.TestCase):

    def setUp(self):
        util.SLEEP_ENABLED = False

    def test_nonexistant_guest(self):
        gcp_svc = DummyGCPService()
        with self.assertRaises(ValidationError):
            gcp_service.validate_images(
                gcp_svc=gcp_svc,
                guest_image=NONEXISTANT_IMAGE,
                encryptor='americium',
                encrypted_image_name=NONEXISTANT_IMAGE,
                image_project=None,
            )

    def test_desired_output_image_exists(self):
        gcp_svc = DummyGCPService()
        with self.assertRaises(ValidationError):
            gcp_service.validate_images(
                gcp_svc=gcp_svc,
                guest_image='test-ubuntu',
                encryptor='americium',
                encrypted_image_name='deuterium',
                image_project=None,
            )

    def test_nonexistant_image_project(self):
        gcp_svc = DummyGCPService()
        with self.assertRaises(ValidationError):
            gcp_service.validate_images(
                gcp_svc=gcp_svc,
                guest_image='test-ubuntu',
                encryptor='americium',
                encrypted_image_name='deuterium',
                image_project=NONEXISTANT_IMAGE,
             )


class TestRunUpdate(unittest.TestCase):

    def setUp(self):
        util.SLEEP_ENABLED = False

    def test_cleanup_on_fail(self):
        gcp_svc = DummyGCPService()
        with self.assertRaises(Exception):
             update_gcp_image.update_gcp_image(
                gcp_svc=gcp_svc,
                enc_svc_cls=FailedEncryptionService,
                values=DummyValues(),
                encrypted_image_name='ubuntu-encrypted',
                instance_config=InstanceConfig({'identity_token': TOKEN})
            )
        self.assertEqual(len(gcp_svc.disks), 0)
        self.assertEqual(len(gcp_svc.instances), 0)

    def test_cleanup(self):
        gcp_svc = DummyGCPService()
        encrypted_image = update_gcp_image.update_gcp_image(
            gcp_svc=gcp_svc,
            enc_svc_cls=DummyEncryptorService,
            values=DummyValues(),
            encrypted_image_name='centos-encrypted',
            instance_config=InstanceConfig({'identity_token': TOKEN})
        )

        self.assertIsNotNone(encrypted_image)
        self.assertEqual(len(gcp_svc.disks), 0)
        self.assertEqual(len(gcp_svc.instances), 0)


class ShareLogsValues():
    def __init__(self):
        self.instance = 'test-instance'
        self.zone = 'us-central1-a'
        self.email = 'support@brkt.com'
        self.bucket = 'test-bucket'
        self.project = 'test-project'
        self.path = 'test-file'


class GCPService1(DummyGCPService):
    def check_bucket_name(self, bucket, project):
        raise ValidationError()


class GCPService2(DummyGCPService):
    def check_bucket_file(self, bucket, path):
        raise ValidationError("File already exists")


class GCPService3(DummyGCPService):
    def check_bucket_file(self, bucket, path):
        raise util.BracketError("Can't upload logs file")


class GCPService4(gcp_service.GCPService):
    def __init__(self):
        super


class TestShareLogs(unittest.TestCase):

    def setUp(self):
        util.SLEEP_ENABLED = False
        self.values = ShareLogsValues()

    # Run the program under normal conditions
    def test_normal(self):
        gcp_svc = DummyGCPService()
        logs = share_logs(self.values, gcp_svc)
        self.assertEqual(logs, 0)
        self.assertEqual(len(gcp_svc.disks), 0)
        self.assertEqual(len(gcp_svc.instances), 0)

    # This tests bucket permission being denied
    def test_bucket_name_exists(self):
        gcp_svc = GCPService1()
        with self.assertRaises(ValidationError):
            share_logs(self.values, gcp_svc)

    # This tests if a file with the same name has already
    # Been uploaded to the bucket
    def test_file_exists(self):
        gcp_svc = GCPService2()
        with self.assertRaises(ValidationError):
            share_logs(self.values, gcp_svc)

    # This tests 5 cases of object name beind invalid
    def test_file_name_invalid(self):
        gcp_svc = GCPService4()
        paths = ['object?', '[object', 'object]', '#object', 'obj*ect']
        for p in paths:
            with self.assertRaises(ValidationError):
                gcp_svc.validate_file_name(p)

    # This tests if the file is unable to upload
    def test_file_upload(self):
        gcp_svc = GCPService3()
        with self.assertRaises(util.BracketError):
            share_logs(self.values, gcp_svc)


class TestWrappedGuest(unittest.TestCase):

    def setUp(self):
        util.SLEEP_ENABLED = False

    def test_smoke(self):
        gcp_svc = DummyGCPService()
        wrapped_instance = wrap_gcp_image.wrap_guest_image(
            gcp_svc=gcp_svc,
            image_id=IGNORE_IMAGE,
            encryptor_image='encryptor-image',
            zone='us-central1-a',
            metadata={}
        )
        self.assertIsNotNone(wrapped_instance)
        self.assertEqual(len(gcp_svc.disks), 0)
        self.assertEqual(len(gcp_svc.instances), 1)

    def test_cleanup(self):
        gcp_svc = DummyGCPService()
        wrap_gcp_image.wrap_guest_image(
            gcp_svc=gcp_svc,
            image_id=IGNORE_IMAGE,
            encryptor_image='encryptor-image',
            zone='us-central1-a',
            metadata={}
        )
        self.assertEqual(len(gcp_svc.disks), 0)
        self.assertEqual(len(gcp_svc.instances), 1)
