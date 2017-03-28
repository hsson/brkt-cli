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

import argparse
import os
import StringIO
import unittest

import brkt_cli
from brkt_cli.config import (
    BRKT_HOSTED_ENV_NAME,
    CLIConfig,
    ConfigSubcommand,
    InvalidOptionError,
    UnknownEnvironmentError
)
from brkt_cli.validation import ValidationError


class SetValues(object):
    def __init__(self, option, value):
        self.config_subcommand = 'set'
        self.option = option
        self.value = value


class SetEnvValues(object):
    def __init__(self, env_name, api_server=None, key_server=None,
                 network_server=None, public_api_server=None,
                 service_domain=None):
        self.config_subcommand = 'set-env'
        self.env_name = env_name
        self.api_server = api_server
        self.key_server = key_server
        self.network_server = network_server
        self.public_api_server = public_api_server
        self.service_domain = service_domain


class UnsetEnvValues(object):
    def __init__(self, env_name):
        self.config_subcommand = 'unset-env'
        self.env_name = env_name


class UseEnvValues(object):
    def __init__(self, env_name):
        self.config_subcommand = 'use-env'
        self.env_name = env_name


def noop():
    pass


class InternalOptionTestCase(unittest.TestCase):

    def test_internal_option(self):
        cfg = CLIConfig()

        # Not set.
        self.assertIsNone(cfg.get_internal_option('test'))
        self.assertEqual(
            'abc', cfg.get_internal_option('test', default='abc'))

        # Set.
        cfg.set_internal_option('test', 'abc')
        self.assertEqual('abc', cfg.get_internal_option('test'))

        # Save, reread, and make sure that the internal option is still set.
        f = StringIO.StringIO()
        cfg.write(f)
        yaml = f.getvalue()

        cfg = CLIConfig()
        cfg.read(StringIO.StringIO(yaml))
        self.assertEqual('abc', cfg.get_internal_option('test'))


class CLIConfigTestCase(unittest.TestCase):

    def setUp(self):
        self.cfg = CLIConfig()

    def test_get_unknown_option(self):
        """Verify that we raise an error if the user attempts to fetch an
        unknown option.
        """
        options = ['no-section', 'test-section.no-option']
        for option in options:
            with self.assertRaises(InvalidOptionError):
                self.cfg.get_option(option)

    def test_set_unknown_option(self):
        """Verify that we raise an error if the user attempts to set an
        unknown option.
        """
        args = (('no-section.no-option', 'foo'),
                ('test-section.no-option', 'foo'))
        for opt, val in args:
            with self.assertRaises(InvalidOptionError):
                self.cfg.set_option(opt, val)

    def test_unset_unknown_option(self):
        """Verify that we raise an error if the user attempts to unset an
        unknown option.
        """
        options = ['no-section', 'test-section.no-option']
        for option in options:
            with self.assertRaises(InvalidOptionError):
                self.cfg.unset_option(option)

    def test_cleanup_empty_subsections(self):
        """Verify that we clean up empty subsections of the config"""
        opt1 = 'a.b.c'
        opt2 = 'a.d.e'
        for opt in [opt1, opt2]:
            self.cfg.register_option(opt, 'test')
            self.cfg.set_option(opt, 'val')

        self.cfg.unset_option(opt1)
        self.assertEquals(
            self.cfg._config['options'],
            {'a': {'d': {'e': 'val'}}}
        )

        self.cfg.unset_option(opt2)
        self.assertEquals(self.cfg._config['options'], {})

    def test_get_default_env(self):
        """Verify that the brkt hosted environment is present by default"""
        env = self.cfg.get_env('brkt-hosted')
        self.assertEqual('yetiapi.mgmt.brkt.com', env.api_host)
        self.assertEqual('hsmproxy.mgmt.brkt.com', env.hsmproxy_host)
        self.assertEqual('network.mgmt.brkt.com', env.network_host)
        self.assertEqual('api.mgmt.brkt.com', env.public_api_host)

        ports = (
            env.api_port, env.hsmproxy_port,
            env.network_port, env.public_api_port
        )
        for port in ports:
            self.assertEqual(443, port)

    def test_set_env_from_service_domain(self):
        """Verify that you can define an environment using its service
        domain.
        """
        env = brkt_cli.brkt_env_from_domain('foo.com')
        self.cfg.set_env('test', env)
        attr_host = {
            'api': 'yetiapi',
            'hsmproxy': 'hsmproxy',
            'network': 'network',
            'public_api': 'api',
        }
        for attr, host in attr_host.iteritems():
            exp = "%s.%s" % (host, 'foo.com')
            self.assertEqual(getattr(env, attr + '_host'), exp)

    def test_unset_unknown_env(self):
        """Verify that an error is raised when attempting to delete
        an unknown environment.
        """
        with self.assertRaises(UnknownEnvironmentError):
            self.cfg.unset_env('unknown')

    def test_unset_known_env(self):
        """Verify that we can delete an environment we have created
        """
        env = brkt_cli.brkt_env_from_domain('foo.com')
        self.cfg.set_env('test', env)
        self.cfg.get_env('test')
        self.cfg.unset_env('test')
        with self.assertRaises(UnknownEnvironmentError):
            self.cfg.get_env('test')

    def test_use_unknown_env(self):
        """Verify that we raise an error when the user attempts to
        activate an unknown environment.
        """
        with self.assertRaises(UnknownEnvironmentError):
            self.cfg.set_current_env('unknown')


class ConfigCommandTestCase(unittest.TestCase):
    def setUp(self):
        self.out = StringIO.StringIO()
        self.cfg = CLIConfig()
        self.cfg.register_option('test-section.test-option', 'A test')
        self.cmd = ConfigSubcommand(stdout=self.out)
        parser = argparse.ArgumentParser()
        self.cmd.register(parser.add_subparsers(), self.cfg)
        self.cmd._write_config = noop

    def test_set_list_get_unset(self):
        """Verify that we can successfully set, get, and unset an existing
        option.
        """
        val = 'test-val'
        opt = 'test-section.test-option'
        self.cfg.set_option(opt, val)
        self.assertEqual(self.cfg.get_option(opt), val)

        self.cmd._get_option(opt)
        self.assertEqual(self.out.getvalue(), "%s\n" % (val,))

        self.cmd._list_options()
        self.assertEqual(self.out.getvalue(), "%s\n%s=%s\n" % (val, opt, val))

        self.cmd._unset_option(opt)
        self.assertEqual(self.cfg.get_option(opt), None)

    def test_set_default_env(self):
        """Verify that you cannot alter the default environment"""
        with self.assertRaises(ValidationError):
            self.cmd._set_env(SetEnvValues(BRKT_HOSTED_ENV_NAME))

    def test_set_env_hosts(self):
        """Verify that you can set individual services of an environment"""
        test_cases = {
            'api': {
                'host': 'api.test.com',
                'port': 1,
                'attr': 'api',
            },
            'key': {
                'host': 'key.test.com',
                'port': 2,
                'attr': 'hsmproxy',
            },
            'network': {
                'host': 'network.test.com',
                'port': 3,
                'attr': 'network',
            },
            'public_api': {
                'host': 'public.test.com',
                'port': 4,
                'attr': 'public_api',
            },
        }
        for arg, tc in test_cases.iteritems():
            kwargs = {
                arg + '_server': '%s:%d' % (tc['host'], tc['port']),
            }
            self.cmd._set_env(SetEnvValues('test', **kwargs))
            env = self.cfg.get_env('test')
            host_attr = getattr(env, tc['attr'] + '_host')
            self.assertEqual(tc['host'], host_attr)
            port_attr = getattr(env, tc['attr'] + '_port')
            self.assertEqual(tc['port'], port_attr)

    def test_list_envs_default(self):
        """Verify that the hosted environment is marked as the
        active environment by default.
        """
        self.cmd._list_envs()
        self.assertEqual(self.out.getvalue(), "* brkt-hosted\n")

    def test_use_env(self):
        """Verify that we can switch between defined environments"""
        self.cmd._set_env(SetEnvValues('test1', service_domain='foo.com'))
        self.cmd._set_env(SetEnvValues('test2', service_domain='bar.com'))
        self.cmd._list_envs()
        out = "\n".join([
            "* brkt-hosted",
            "  test1      ",
            "  test2      "
        ])
        self.assertEqual(self.out.getvalue(), out + "\n")
        self.cmd._use_env(UseEnvValues('test2'))
        self.out.truncate(0)
        self.cmd._list_envs()
        out = "\n".join([
            "  brkt-hosted",
            "  test1      ",
            "* test2      "
        ])
        self.assertEqual(self.out.getvalue(), out + "\n")

    def test_use_incomplete_env(self):
        """Verify that we raise an error if a user attempts to
        use an incomplete environment.
        """
        self.cmd._set_env(SetEnvValues('test1', api_server='test.com'))
        with self.assertRaises(ValidationError):
            self.cmd._use_env(UseEnvValues('test1'))

    def test_fallback_env(self):
        """Verify that we fall back to the hosted environment if
        the user delete the current environment.
        """
        self.cmd._set_env(SetEnvValues('test1', service_domain='test.com'))
        self.cmd._use_env(UseEnvValues('test1'))
        self.cmd._unset_env(UnsetEnvValues('test1'))
        self.cmd._list_envs()
        self.assertEqual(self.out.getvalue(), "* brkt-hosted\n")


class YetiServiceTestCase(unittest.TestCase):

    def setUp(self):
        self.original_token = os.environ.get('BRKT_API_TOKEN')

    def tearDown(self):
        if self.original_token:
            os.environ['BRKT_API_TOKEN'] = self.original_token
        else:
            del os.environ['BRKT_API_TOKEN']

    def test_get_yeti_service(self):
        cfg = CLIConfig()
        y = brkt_cli.config._get_yeti_service(cfg)
        self.assertEqual('https://api.mgmt.brkt.com:443', y.root_url)
        self.assertEqual(self.original_token, y.token)

        # Make sure the API token environment variable is picked up.
        os.environ['BRKT_API_TOKEN'] = 'abc'
        y = brkt_cli.config._get_yeti_service(cfg)
        self.assertEqual('abc', y.token)
