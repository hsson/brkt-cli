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
import getpass
import logging
import subprocess

from brkt_cli.validation import ValidationError

cryptography_library_available = True

try:
    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography import x509
except ImportError:
    cryptography_library_available = False


log = logging.getLogger(__name__)


def _check_cryptography():
    if not cryptography_library_available:
        raise Exception('Cryptography library is not installed')


class Crypto(object):
    def __init__(self):
        _check_cryptography()

        self.private_key = None
        self.public_key = None
        self.public_key_pem = None

        self.x = None
        self.y = None
        self.curve = None

    def get_private_key_pem(self, password=None):
        if password is not None:
            encryption = serialization.BestAvailableEncryption(password)
        else:
            encryption = serialization.NoEncryption()

        return self.private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            encryption
        )


def _from_private_key(private_key):
    public_key = private_key.public_key()
    numbers = public_key.public_numbers()

    crypto = Crypto()
    crypto.private_key = private_key
    crypto.public_key = public_key
    crypto.public_key_pem = public_key.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo
    )
    crypto.x = numbers.x
    crypto.y = numbers.y
    crypto.curve = numbers.curve.name

    return crypto


def from_private_key_pem(pem, password=None):
    """ Load a Crypto object from a private key PEM file.

    :raise ValueError if the PEM is malformed
    :raise TypeError if the key is encrypted but a password is not specified
    """
    _check_cryptography()

    private_key = serialization.load_pem_private_key(
        pem, password=password, backend=default_backend()
    )
    return _from_private_key(private_key)


def new():
    """ Return a new Crypto object based on a generated private key.
    """
    _check_cryptography()

    private_key = ec.generate_private_key(ec.SECP384R1(), default_backend())
    return _from_private_key(private_key)


def is_encrypted_key(pem):
    return 'ENCRYPTED' in pem


def is_private_key(pem):
    return 'PRIVATE KEY' in pem


def read_private_key(pem_path):
    """ Read a private key from a PEM file.

    :return a brkt_cli.crypto.Crypto object
    :raise ValidationError if the file cannot be read or is malformed, or
    if the PEM does not represent a 384-bit ECDSA private key.
    """
    _check_cryptography()

    key_format_err = (
        'Signing key must be a 384-bit ECDSA private key (NIST P-384)'
    )

    try:
        with open(pem_path) as f:
            pem = f.read()
        if not is_private_key(pem):
            raise ValidationError(key_format_err)

        password = None
        if is_encrypted_key(pem):
            password = getpass.getpass('Encrypted private key password: ')
        crypto = from_private_key_pem(pem, password=password)
    except (ValueError, IOError) as e:
        log.debug('Unable to load signing key from %s', pem_path, exc_info=1)
        raise ValidationError(
            'Unable to load signing key: %s' % e)

    log.debug('crypto.curve=%s', crypto.curve)
    if crypto.curve != ec.SECP384R1.name:
        raise ValidationError(key_format_err)
    return crypto


def _run_cmd(args, input_content=None):
    """ Run the given command and return a tuple of (returncode, output).
    The output contains both stdout and stderr.
    """
    p = subprocess.Popen(
        args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if input_content:
        p.stdin.write(input_content)
        p.stdin.close()
    p.wait()
    return p.returncode, p.stdout.read()


def validate_cert(cert_data):
    """ Validate that the given string is a valid x509 certificate.

    :return True if the cert is valid
    :raise ValidationError if the string has an unexpected format
    """
    # Try validating with the cryptography library, if it's installed.
    if cryptography_library_available:
        log.debug('Using the cryptography library to validate cert')
        try:
            x509.load_pem_x509_certificate(cert_data, default_backend())
            return
        except Exception as e:
            raise ValidationError('Error validating CA cert: %s' % e)

    # See if openssl is installed.
    code, _ = _run_cmd(['which', 'openssl'])
    if code != 0:
        log.info(
            'Cryptography library is not installed and openssl is not '
            'available.  Unable to verify cert.')
        return

    # Validate with openssl.
    log.debug('Using openssl to validate cert')
    code, output = _run_cmd(['openssl', 'x509'], cert_data)

    if code != 0:
        raise ValidationError('Error validating CA cert: ' + output)
