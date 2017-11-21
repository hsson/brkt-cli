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
import os
import unittest

from brkt_cli import encryptor_service

from brkt_cli import util

from brkt_cli.aws import (
    encrypt_ami, test_aws_service, update_ami
)
from brkt_cli.aws.test_aws_service import build_aws_service
from brkt_cli.test_encryptor_service import (
    DummyEncryptorService,
    FailedEncryptionService
)
from brkt_cli.util import CRYPTO_XTS


class DummyValues():
    def __init__(self, encryptor, guest):
        self.ami = guest
        self.ca_cert = None
        self.crypto = CRYPTO_XTS
        self.encrypted_ami_name = None
        self.encryptor_ami = encryptor
        self.encryptor_instance_type = None
        self.guest_instance_type = None
        self.ntp_servers = None
        self.proxies = None
        self.proxy_config_file = None
        self.save_encryptor_logs = None
        self.security_group_ids = None
        self.single_disk = False
        self.subnet_id = None
        self.status_port = 80
        self.terminate_encryptor_on_failure = True
        self.updater_instance_type = None


class TestRunUpdate(unittest.TestCase):

    def setUp(self):
        util.SLEEP_ENABLED = False

    def test_subnet_and_security_groups(self):
        """ Test that the subnet and security group ids are passed through
        to run_instance().
        """
        test_subnet = 'subnet-1'
        test_secgrps = ['sg-1', 'sg-2']

        aws_svc, encryptor_image, guest_image = build_aws_service()
        values = DummyValues(encryptor_image.id, guest_image.id)

        encrypted_ami_id = encrypt_ami.encrypt(
            aws_svc=aws_svc,
            enc_svc_cls=DummyEncryptorService,
            values=values)

        values = DummyValues(encryptor_image.id, encrypted_ami_id)
        values.subnet_id = test_subnet
        values.security_group_ids = test_secgrps

        self.call_count = 0

        def run_instance_callback(args):
            if args.image_id == encryptor_image.id:
                self.call_count += 1
                self.assertEqual(args.subnet_id, test_subnet)
                self.assertEqual(args.security_group_ids, test_secgrps)

        aws_svc.run_instance_callback = run_instance_callback

        ami_id = update_ami(
            aws_svc=aws_svc,
            enc_svc_class=DummyEncryptorService,
            values=values)

        self.assertEqual(1, self.call_count)
        self.assertIsNotNone(ami_id)

    def test_guest_instance_type(self):
        """ Test that the guest instance type is passed through
        to run_instance().
        """
        test_insttype = 't2.micro'

        aws_svc, encryptor_image, guest_image = build_aws_service()
        values = DummyValues(encryptor_image.id, guest_image.id)

        encrypted_ami_id = encrypt_ami.encrypt(
            aws_svc=aws_svc,
            enc_svc_cls=DummyEncryptorService,
            values=values)

        values = DummyValues(encryptor_image.id, encrypted_ami_id)
        values.guest_instance_type = test_insttype

        def run_instance_callback(args):
            if args.image_id == encrypted_ami_id:
                self.assertEqual(args.instance_type, test_insttype)

        aws_svc.run_instance_callback = run_instance_callback

        update_ami(
            aws_svc=aws_svc,
            enc_svc_class=DummyEncryptorService,
            values=values)

    def test_security_group_eventual_consistency(self):
        """ Test that we handle eventually consistency issues when creating
        a temporary security group.
        """
        aws_svc, encryptor_image, guest_image = build_aws_service()
        values = DummyValues(encryptor_image.id, guest_image.id)

        encrypted_ami_id = encrypt_ami.encrypt(
            aws_svc=aws_svc,
            enc_svc_cls=DummyEncryptorService,
            values=values)

        values = DummyValues(encryptor_image.id, encrypted_ami_id)

        self.call_count = 0

        def run_instance_callback(args):
            if args.image_id != encryptor_image.id:
                return
            self.call_count += 1
            if self.call_count >= 3:
                return
            # Simulate eventual consistency error while creating
            # security group.
            raise test_aws_service.new_client_error('InvalidGroup.NotFound')

        aws_svc.run_instance_callback = run_instance_callback

        update_ami(
            aws_svc=aws_svc,
            enc_svc_class=DummyEncryptorService,
            values=values)

        self.assertEqual(3, self.call_count)

    def test_update_error_console_output(self):
        """ Test that when an update failure occurs, we write the
        console log to a temp file.
        """
        aws_svc, encryptor_image, guest_image = build_aws_service()
        values = DummyValues(encryptor_image.id, guest_image.id)

        encrypted_ami_id = encrypt_ami.encrypt(
            aws_svc=aws_svc,
            enc_svc_cls=DummyEncryptorService,
            values=values)

        values = DummyValues(encryptor_image.id, encrypted_ami_id)

        # Create callbacks that make sure that we stop the updater
        # instance before collecting logs.
        self.updater_instance = None

        def run_instance_callback(args):
            if args.image_id == encryptor_image.id:
                self.updater_instance = args.instance

        self.updater_stopped = False

        def stop_instance_callback(instance):
            if (self.updater_instance and
                    instance.id == self.updater_instance.id):
                self.updater_stopped = True

        aws_svc.run_instance_callback = run_instance_callback
        aws_svc.stop_instance_callback = stop_instance_callback

        try:
            update_ami(
                aws_svc=aws_svc,
                enc_svc_class=FailedEncryptionService,
                values=values)

            self.fail('Update should have failed')
        except encryptor_service.EncryptionError as e:
            with open(e.console_output_file.name) as f:
                content = f.read()
                self.assertEquals(
                    test_aws_service.CONSOLE_OUTPUT_TEXT, content)
            os.remove(e.console_output_file.name)

        self.assertTrue(self.updater_stopped)

    def test_ena_support(self):
        """ Test that we enable ENA support on the guest instance when ENA
        support is enabled on the Metavisor instance."""
        aws_svc, encryptor_image, guest_image = build_aws_service()
        values = DummyValues(encryptor_image.id, guest_image.id)

        encrypted_ami_id = encrypt_ami.encrypt(
            aws_svc=aws_svc,
            enc_svc_cls=DummyEncryptorService,
            values=values)

        values = DummyValues(encryptor_image.id, encrypted_ami_id)

        self.encrypted_instance = None

        def run_instance_callback(args):
            if args.image_id == encryptor_image.id:
                args.instance.ena_support = True
            elif args.image_id == encrypted_ami_id:
                args.instance.ena_support = False
                self.encrypted_instance = args.instance

        aws_svc.run_instance_callback = run_instance_callback

        update_ami(
            aws_svc=aws_svc,
            enc_svc_class=DummyEncryptorService,
            values=values)

        self.assertTrue(self.encrypted_instance.ena_support)
