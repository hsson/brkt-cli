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

import json
import os
import tempfile
import unittest

import brkt_cli
from brkt_cli import (
    proxy, instance_config_args)
from brkt_cli.config import CLIConfig
from brkt_cli.instance_config import (
    BRKT_CONFIG_CONTENT_TYPE,
    BRKT_FILES_CONTENT_TYPE,
    InstanceConfig,
    INSTANCE_CREATOR_MODE,
    INSTANCE_METAVISOR_MODE,
    INSTANCE_UPDATER_MODE
)
import brkt_cli.crypto
from brkt_cli.instance_config_args import (
    instance_config_args_to_values,
    instance_config_from_values
)
from brkt_cli.proxy import Proxy
from brkt_cli.user_data import get_mime_part_payload
from brkt_cli.validation import ValidationError

test_jwt = (
    'eyJhbGciOiAiRVMzODQiLCAidHlwIjogIkpXVCJ9.eyJpc3MiOiAiYnJrdC1jb'
    'GktMC45LjE3cHJlMSIsICJpYXQiOiAxNDYzNDI5MDg1LCAianRpIjogImJlN2J'
    'mYzYwIiwgImtpZCI6ICJhYmMifQ.U2lnbmVkLCBzZWFsZWQsIGRlbGl2ZXJlZA'
)

test_ca_cert = """-----BEGIN CERTIFICATE-----
MIIBeTCCAR6gAwIBAgIQQg73wXID1mYCOCE1JW5Y4DAKBggqhkjOPQQDAjAcMRow
GAYDVQQKExFCcmFja2V0IENvbXB1dGluZzAeFw0xNTA2MDUwNDEwMDRaFw0xNjA2
MDQwNDEwMDRaMBwxGjAYBgNVBAoTEUJyYWNrZXQgQ29tcHV0aW5nMFkwEwYHKoZI
zj0CAQYIKoZIzj0DAQcDQgAEjPs/ziaJhGEAmrqG70to+ezekjIRIDIYK6rvqi2S
xaFGjuyHpnyzl/O6o/dhTXBrT3SOPEJDNHC4ZdL7gt7EM6NCMEAwDgYDVR0PAQH/
BAQDAgCsMB0GA1UdJQQWMBQGCCsGAQUFBwMBBggrBgEFBQcDAjAPBgNVHRMBAf8E
BTADAQH/MAoGCCqGSM49BAMCA0kAMEYCIQC8N+zLHBgPXNckbK6VGACHC1M4rPSe
gcHhlcow44jARAIhAN+LFgLbZxzJ6Qmez2UXKcRK0wNkBrAoPrnWIF584d0O
-----END CERTIFICATE-----
"""

# Some test constants
api_host_port = 'api.example.com:777'
hsmproxy_host_port = 'hsmproxy.example.com:888'
network_host_port = 'network.example.com:999'
ntp_server1 = '10.4.5.6'
ntp_server2 = '199.55.32.1'
proxy_host = '10.22.33.44'
proxy_port = 3128
proxy_host_port = '%s:%d' % (proxy_host, proxy_port)


def _verify_proxy_config_in_userdata(ut, userdata):
    brkt_files = get_mime_part_payload(userdata, BRKT_FILES_CONTENT_TYPE)
    ut.assertTrue('/var/brkt/ami_config/proxy.yaml: ' +
                    '{contents: "version: 2.0' in brkt_files)
    ut.assertTrue('host: %s' % proxy_host in brkt_files)
    ut.assertTrue('port: %d' % proxy_port in brkt_files)


class TestInstanceConfig(unittest.TestCase):

    def test_brkt_env(self):
        brkt_config_in = {
            'api_host': api_host_port,
            'hsmproxy_host': hsmproxy_host_port,
            'network_host': network_host_port
        }
        ic = InstanceConfig(brkt_config_in)
        config_json = ic.make_brkt_config_json()
        expected_json = ('{"brkt": {"api_host": "%s", ' +
            '"hsmproxy_host": "%s", "network_host": "%s", ') % \
            (api_host_port, hsmproxy_host_port, network_host_port) + \
            '"solo_mode": "creator"}}'
        self.assertEqual(config_json, expected_json)

    def test_ntp_servers(self):
        # First with just one server
        ic = InstanceConfig({'ntp_servers': [ntp_server1]})

        config_json = ic.make_brkt_config_json()
        expected_json = '{"brkt": {"ntp_servers": ["%s"], ' % ntp_server1 + \
                        '"solo_mode": "creator"}}'
        self.assertEqual(config_json, expected_json)

        # Now try two servers
        ic = InstanceConfig({'ntp_servers': [ntp_server1, ntp_server2]})

        config_json = ic.make_brkt_config_json()
        expected_json = '{"brkt": {"ntp_servers": ["%s", "%s"], ' % \
                        (ntp_server1, ntp_server2) + \
                        '"solo_mode": "creator"}}'
        self.assertEqual(config_json, expected_json)

    def test_jwt(self):
        ic = InstanceConfig({'identity_token': test_jwt})
        config_json = ic.make_brkt_config_json()
        expected_json = '{"brkt": {"identity_token": "%s", ' % test_jwt + \
                        '"solo_mode": "creator"}}'
        self.assertEqual(config_json, expected_json)

    def test_proxy_config(self):
        # The proxy file goes in a brkt-file part,
        # so the brkt config should be empty
        ic = InstanceConfig({})
        p = Proxy(host=proxy_host, port=proxy_port)
        proxy_config = proxy.generate_proxy_config(p)
        ic.add_brkt_file('proxy.yaml', proxy_config)
        _verify_proxy_config_in_userdata(self, ic.make_userdata())

    def test_multiple_options(self):
        brkt_config_in = {
            'api_host': api_host_port,
            'hsmproxy_host': hsmproxy_host_port,
            'network_host': network_host_port,
            'ntp_servers': [ntp_server1],
            'identity_token': test_jwt
        }
        ic = InstanceConfig(brkt_config_in)
        ic.add_brkt_file('ca_cert.pem.example.com', 'DUMMY CERT')
        ud = ic.make_userdata()
        brkt_config_json = get_mime_part_payload(ud, BRKT_CONFIG_CONTENT_TYPE)
        brkt_config = json.loads(brkt_config_json)['brkt']

        self.assertEqual(brkt_config['identity_token'], test_jwt)
        self.assertEqual(brkt_config['ntp_servers'], [ntp_server1])
        self.assertEqual(brkt_config['api_host'], api_host_port)
        self.assertEqual(brkt_config['hsmproxy_host'], hsmproxy_host_port)
        self.assertEqual(brkt_config['network_host'], network_host_port)

        brkt_files = get_mime_part_payload(ud, BRKT_FILES_CONTENT_TYPE)
        self.assertEqual(brkt_files,
                        "/var/brkt/ami_config/ca_cert.pem.example.com: " +
                        "{contents: DUMMY CERT}\n")

        """
        gcp_metadata = ic.make_gcp_metadata()
        item_list = gcp_metadata['items']
        self.assertEqual(len(item_list), 1)
        brkt_item = item_list[0]
        self.assertEqual(brkt_item['key'], 'brkt')
        brkt_userdata = brkt_item['value']
        """


PROD_ENV = brkt_cli.get_prod_brkt_env()


def _get_brkt_config_for_cli_args(cli_args='', mode=INSTANCE_CREATOR_MODE,
                                  brkt_env=PROD_ENV, launch_token=None):
    values = instance_config_args_to_values(cli_args)
    ic = instance_config_from_values(
        values, mode=mode, brkt_env=brkt_env, launch_token=launch_token)
    ud = ic.make_userdata()
    brkt_config_json = get_mime_part_payload(ud, BRKT_CONFIG_CONTENT_TYPE)
    brkt_config = json.loads(brkt_config_json)['brkt']
    return brkt_config


class TestInstanceConfigFromCliArgs(unittest.TestCase):

    def test_brkt_env(self):
        env_string = '%s,%s,%s' % (
            api_host_port, hsmproxy_host_port, network_host_port)
        brkt_env = brkt_cli.parse_brkt_env(env_string)
        brkt_config = _get_brkt_config_for_cli_args(brkt_env=brkt_env)
        self.assertEqual(brkt_config['api_host'], api_host_port)
        self.assertEqual(brkt_config['hsmproxy_host'], hsmproxy_host_port)
        self.assertEqual(brkt_config['network_host'], network_host_port)

    def test_service_domain(self):
        brkt_env = brkt_cli.brkt_env_from_domain('example.com')
        brkt_config = _get_brkt_config_for_cli_args(brkt_env=brkt_env)
        self.assertEqual(brkt_config['api_host'], 'yetiapi.example.com:443')
        self.assertEqual(
            brkt_config['hsmproxy_host'], 'hsmproxy.example.com:443')
        self.assertEqual(
            brkt_config['network_host'], 'network.example.com:443')

    def test_default_brkt_env(self):
        """ Test that Yeti endpoints aren't set when they're not specified
        on the command line.
        """

        # Verify that we require BracketEnvironment for creator and
        # updater mode.
        for mode in (INSTANCE_CREATOR_MODE, INSTANCE_UPDATER_MODE):
            with self.assertRaises(Exception):
                values = instance_config_args_to_values('', mode=mode)
                instance_config_from_values(values)

        # BracketEnvironment isn't required in Metavisor mode.
        brkt_config = _get_brkt_config_for_cli_args(
            mode=INSTANCE_METAVISOR_MODE, brkt_env=None)
        self.assertIsNone(brkt_config.get('api_host'))
        self.assertIsNone(brkt_config.get('hsmproxy_host'))
        self.assertIsNone(brkt_config.get('network_host'))

    def test_env_from_config(self):
        """ Test that we can use a custom environment that is stored
        in the config
        """
        config = CLIConfig()
        env = brkt_cli.brkt_env_from_domain('foo.com')
        config.set_env('test', env)
        config.set_current_env('test')
        for mode in (INSTANCE_CREATOR_MODE, INSTANCE_UPDATER_MODE):
            brkt_config = _get_brkt_config_for_cli_args(
                mode=mode, brkt_env=env)
            for attr in ('api', 'hsmproxy', 'network'):
                endpoint = '%s:%d' % (
                    getattr(env, attr + '_host'),
                    getattr(env, attr + '_port'))
                self.assertEqual(endpoint, brkt_config.get(attr + '_host'))

    def test_ntp_servers(self):
        cli_args = '--ntp-server %s' % ntp_server1
        brkt_config = _get_brkt_config_for_cli_args(cli_args)
        server_list = brkt_config['ntp_servers']
        self.assertEqual(server_list, [ntp_server1])

        cli_args = '--ntp-server %s --ntp-server %s' % \
                   (ntp_server1, ntp_server2)
        brkt_config = _get_brkt_config_for_cli_args(cli_args)
        server_list = brkt_config['ntp_servers']
        self.assertEqual(server_list, [ntp_server1, ntp_server2])

    def test_jwt(self):
        brkt_config = _get_brkt_config_for_cli_args(launch_token='abc')
        self.assertEqual(brkt_config['identity_token'], 'abc')

    def test_proxy_config(self):
        cli_args = '--proxy %s' % (proxy_host_port)
        values = instance_config_args_to_values(cli_args)
        ic = instance_config_from_values(values, brkt_env=PROD_ENV)
        _verify_proxy_config_in_userdata(self, ic.make_userdata())

    def _check_brkt_files(self, mv_mode, cli_args, brkt_files_start,
                          brkt_env):
        values = instance_config_args_to_values(cli_args)
        ic = instance_config_from_values(
            values, mode=mv_mode, brkt_env=brkt_env)
        ud = ic.make_userdata()
        brkt_files = get_mime_part_payload(ud, BRKT_FILES_CONTENT_TYPE)
        self.assertTrue(
            brkt_files.startswith(brkt_files_start),
            msg='%s does not start with %s' % (brkt_files, brkt_files_start)
        )

    def test_ca_cert(self):
        domain = 'dummy.foo.com'
        # First make sure that you can't use --ca-cert without specifying endpoints
        cli_args = '--ca-cert dummy.crt'
        values = instance_config_args_to_values(cli_args)
        with self.assertRaises(ValidationError):
            instance_config_from_values(values, brkt_env=PROD_ENV)

        brkt_env_string = 'api.%s:7777,hsmproxy.%s:8888,network.%s:9999' % (
            domain, domain, domain)
        endpoint_args = '--brkt-env ' + brkt_env_string
        dummy_env = brkt_cli.parse_brkt_env(brkt_env_string)

        if brkt_cli.crypto.cryptography_library_available:
            # Now specify endpoint args but use a bogus cert.  Validation
            # only works if the cryptography library is available or
            # openssl is installed.
            dummy_ca_cert = 'THIS IS NOT A CERTIFICATE'
            with tempfile.NamedTemporaryFile() as f:
                f.write(dummy_ca_cert)
                f.flush()
                cli_args = endpoint_args + ' --ca-cert %s' % f.name
                values = instance_config_args_to_values(cli_args)
                with self.assertRaises(ValidationError):
                    instance_config_from_values(values, brkt_env=PROD_ENV)

        # Now use endpoint args and a valid cert, with all three modes
        with tempfile.NamedTemporaryFile() as f:
            f.write(test_ca_cert)
            f.flush()
            cli_args = endpoint_args + ' --ca-cert %s' % f.name

            mv_mode_start = (
                "/var/brkt/instance_config/ca_cert.pem.dummy.foo.com: "
                "{contents: '-----BEGIN CERTIFICATE-----"
            )
            creator_updater_start = (
                "/var/brkt/ami_config/ca_cert.pem.dummy.foo.com: " +
                "{contents: '-----BEGIN CERTIFICATE-----"
            )
            self._check_brkt_files(
                INSTANCE_METAVISOR_MODE,
                cli_args,
                mv_mode_start,
                dummy_env
            )
            self._check_brkt_files(
                INSTANCE_CREATOR_MODE,
                cli_args,
                creator_updater_start,
                dummy_env
            )
            self._check_brkt_files(
                INSTANCE_UPDATER_MODE,
                cli_args,
                creator_updater_start,
                dummy_env
            )


class YetiServiceTestCase(unittest.TestCase):

    def setUp(self):
        self.original_token = os.environ.get('BRKT_API_TOKEN')

    def tearDown(self):
        if self.original_token:
            os.environ['BRKT_API_TOKEN'] = self.original_token
        else:
            del os.environ['BRKT_API_TOKEN']

    def test_get_yeti_service(self):
        brkt_env = brkt_cli.get_prod_brkt_env()
        y = instance_config_args._yeti_service_from_brkt_env(brkt_env)
        self.assertEqual('https://api.mgmt.brkt.com:443', y.root_url)
        self.assertEqual(self.original_token, y.token)

        # Make sure the API token environment variable is picked up.
        os.environ['BRKT_API_TOKEN'] = 'abc'
        y = instance_config_args._yeti_service_from_brkt_env(brkt_env)
        self.assertEqual('abc', y.token)
