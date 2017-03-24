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
import tempfile
import unittest

from brkt_cli.validation import ValidationError

import brkt_cli.crypto

if brkt_cli.crypto.cryptography_library_available:
    import cryptography.hazmat.backends.openssl.ec
    import cryptography.hazmat.primitives.asymmetric.ec


TEST_PRIVATE_KEY_PEM = """-----BEGIN EC PRIVATE KEY-----
MIGkAgEBBDBw1jk43okFLLLad4OgdsSIwsUdJ3BzxzuZWM/bBpF+GKJ7D9hJd3W7
TBKMrozqEqOgBwYFK4EEACKhZANiAASbklkQuPGQTJL37dGI0TYoSFQ8aFdogUzV
9XdUz3s5z9CDGmIuIjB+gNPplCyWJzrENC5v+ao4TLee1ZyXsnDCP25Za0UiPuU+
IpuqIVEKCSDTG96q2bCqDIT45qjOWBQ=
-----END EC PRIVATE KEY-----
"""
TEST_PRIVATE_KEY_X = int(
    '23944671740498376501544907634910018068896593728651488954476245338720275'
    '820003446148266017687349159128610913381656378'
)
TEST_PRIVATE_KEY_Y = int(
    '30198533853195572636850285556018792732205254449690882000990730634871805'
    '883491943919079902332284216113666861239785492'
)

TEST_ENCRYPTED_PRIVATE_KEY_PEM = """-----BEGIN EC PRIVATE KEY-----
Proc-Type: 4,ENCRYPTED
DEK-Info: AES-256-CBC,35BACC9F9023D5206DEC871E734B139B

TEOwSpTBoOPpwQU8u7SJaJqSIUwk6SfHZkXs205xoELtHbNcWV1vr0/DsQ1B2b3c
ZIO1bvHQOKl3X76hUxqzSBSx7kFqN2igjXGaQ2SmkZrzqhqAEo7YScpMQQgvk15B
U7wZaJcaN6RelbwRqnM7Qk9HqD5U9+lvS7g7vhP++AXhQretG7l9LYMZKxk3F/th
pZPjFPt2fjlVkJnhl6NkhsTder9rJE3qKlP9JM8zwUQ=
-----END EC PRIVATE KEY-----"""
TEST_ENCRYPTED_PRIVATE_KEY_PASSWORD = 'test123'

TEST_CERT = """-----BEGIN CERTIFICATE-----
MIIBtTCCATugAwIBAgIQZBk/5Ngmtc0sE7XGFlF11TAKBggqhkjOPQQDAzAcMRow
GAYDVQQKExFCcmFja2V0IENvbXB1dGluZzAeFw0xNjA1MTIwNDIwNDVaFw0xOTAy
MDYwNDIwNDVaMBwxGjAYBgNVBAoTEUJyYWNrZXQgQ29tcHV0aW5nMHYwEAYHKoZI
zj0CAQYFK4EEACIDYgAEAohisKTivkVGrLwSYMo17ttWnw2cBdK5ZPTun48r781/
Z1DTxrLjnc7cCFMYWq01XOsjEhy+bIZNh/82E9i/GfqAfycitfuNO1OESZ8bdD17
00SMs0y08DVB3kdTy9aNo0IwQDAOBgNVHQ8BAf8EBAMCAqwwHQYDVR0lBBYwFAYI
KwYBBQUHAwEGCCsGAQUFBwMCMA8GA1UdEwEB/wQFMAMBAf8wCgYIKoZIzj0EAwMD
aAAwZQIxAO7hEZk6O74+Vz20OCiLit7HKOFhsGgvFtQfqzsz3LiOahpGAZaAphbu
rjBoDDI8bgIwJWB24fgP6ueUOVbUQ9NaV/m3RHloIhQyY5LypcJALmnQVC7YPqwx
lu+fKEaeTQLW
-----END CERTIFICATE-----
"""


class TestCrypto(unittest.TestCase):

    def test_from_pem(self):
        if not brkt_cli.crypto.cryptography_library_available:
            return

        def _check_fields(crypto):
            self.assertEqual(
                cryptography.hazmat.primitives.asymmetric.ec.SECP384R1.name,
                crypto.curve)
            self.assertEqual(TEST_PRIVATE_KEY_X, crypto.x)
            self.assertEqual(TEST_PRIVATE_KEY_Y, crypto.y)

        # Unencrypted private key.
        crypto = brkt_cli.crypto.from_private_key_pem(TEST_PRIVATE_KEY_PEM)
        _check_fields(crypto)

        # Encrypted private key.
        crypto = brkt_cli.crypto.from_private_key_pem(
            TEST_ENCRYPTED_PRIVATE_KEY_PEM,
            TEST_ENCRYPTED_PRIVATE_KEY_PASSWORD
        )
        _check_fields(crypto)

    def test_invalid_pem(self):
        if not brkt_cli.crypto.cryptography_library_available:
            return

        with self.assertRaises(ValueError):
            brkt_cli.crypto.from_private_key_pem('foobar')

    def test_is_encrypted_key(self):
        if not brkt_cli.crypto.cryptography_library_available:
            return

        self.assertTrue(
            brkt_cli.crypto.is_encrypted_key(TEST_ENCRYPTED_PRIVATE_KEY_PEM))
        self.assertFalse(
            brkt_cli.crypto.is_encrypted_key(TEST_PRIVATE_KEY_PEM)
        )

    def test_is_private_key(self):
        if not brkt_cli.crypto.cryptography_library_available:
            return

        public_pem = TEST_PRIVATE_KEY_PEM.replace('PRIVATE', 'PUBLIC')
        self.assertTrue(brkt_cli.crypto.is_private_key(TEST_PRIVATE_KEY_PEM))
        self.assertFalse(brkt_cli.crypto.is_private_key(public_pem))
        self.assertFalse(brkt_cli.crypto.is_private_key('xyz'))

    def test_generate(self):
        """ Test generating a key pair.
        """
        if not brkt_cli.crypto.cryptography_library_available:
            return

        crypto = brkt_cli.crypto.new()
        self.assertTrue(
            isinstance(
                crypto.private_key,
                cryptography.hazmat.backends.openssl.ec._EllipticCurvePrivateKey
            )
        )
        self.assertTrue(
            isinstance(
                crypto.public_key,
                cryptography.hazmat.backends.openssl.ec._EllipticCurvePublicKey
            )
        )
        self.assertTrue('BEGIN PUBLIC KEY' in crypto.public_key_pem)

        pem = crypto.get_private_key_pem()
        self.assertTrue('BEGIN EC PRIVATE KEY' in pem)
        pem = crypto.get_private_key_pem('test123')
        self.assertTrue('Proc-Type: 4,ENCRYPTED' in pem)


# This PEM was generated by openssl, and must only be used for
# unit testing.
TEST_SECT163K1_PRIVATE_KEY_PEM = """-----BEGIN EC PRIVATE KEY-----
MFMCAQEEFQGZdbOd9KrGmynCqcy3S1QDvq67xqAHBgUrgQQAAaEuAywABAej5bYZ
ZN4/1PqYAE8Cz4aSMC8KjgCDfMkzv0VURQGcSQ5xc4aCnI7bIQ==
-----END EC PRIVATE KEY-----
"""


class TestReadPrivateKey(unittest.TestCase):

    def test_read_private_key(self):
        """ Test reading the signing key from a file. """
        if not brkt_cli.crypto.cryptography_library_available:
            return

        # Write private key to a temp file.
        key_file = tempfile.NamedTemporaryFile()
        key_file.write(TEST_PRIVATE_KEY_PEM)
        key_file.flush()

        crypto = brkt_cli.crypto.read_private_key(key_file.name)
        self.assertEqual(TEST_PRIVATE_KEY_X, crypto.x)
        key_file.close()

    def test_read_private_key_invalid_curve(self):
        """ Test that we require NIST384p for the signing key. """
        if not brkt_cli.crypto.cryptography_library_available:
            return

        # Write private key to a temp file.
        key_file = tempfile.NamedTemporaryFile()
        key_file.write(TEST_SECT163K1_PRIVATE_KEY_PEM)
        key_file.flush()

        with self.assertRaises(ValidationError):
            brkt_cli.crypto.read_private_key(key_file.name)
        key_file.close()

    def test_read_private_key_io_error(self):
        """ Test that we handle IOError when reading the signing key.
        """
        if not brkt_cli.crypto.cryptography_library_available:
            return

        # Read from a directory.
        with self.assertRaises(ValidationError):
            brkt_cli.crypto.read_private_key('.')

        # Read from a file that doesn't exist.
        with self.assertRaises(ValidationError):
            brkt_cli.crypto.read_private_key('nothing_here.pem')

        # Read from a malformed file.
        key_file = tempfile.NamedTemporaryFile()
        key_file.write('abc')
        key_file.flush()

        with self.assertRaises(ValidationError):
            brkt_cli.crypto.read_private_key(key_file.name)
        key_file.close()

    def test_validate_cert(self):
        if not brkt_cli.crypto.cryptography_library_available:
            return

        brkt_cli.crypto.validate_cert(TEST_CERT)
        with self.assertRaises(ValidationError):
            brkt_cli.crypto.validate_cert('foobar')
