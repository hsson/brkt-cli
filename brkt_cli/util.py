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
import abc
import base64
import json
import logging
import re
import time
import uuid

from brkt_cli.validation import ValidationError

SLEEP_ENABLED = True
MAX_BACKOFF_SECS = 10

# Supported crypto options for the disks
CRYPTO_GCM = 'gcm'
CRYPTO_XTS = 'xts'


log = logging.getLogger(__name__)


class BracketError(Exception):
    pass


class Deadline(object):
    """Convenience class for bounding how long execution takes."""

    def __init__(self, secs_from_now, clock=time):
        self.deadline = clock.time() + secs_from_now
        self.clock = clock

    def is_expired(self):
        """Return whether or not the deadline has passed.

        Returns:
            True if the deadline has passed. False otherwise.
        """
        return self.clock.time() >= self.deadline


class RetryExceptionChecker(object):
    """ Abstract class, implemented by callsites that need custom
    exception checking for the retry() function.
    """

    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def is_expected(self, exception):
        pass


def sleep(seconds):
    if SLEEP_ENABLED:
        time.sleep(seconds)


def retry(function, on=None, exception_checker=None, timeout=15.0,
          initial_sleep_seconds=0.25):
    """ Retry the given function until it completes successfully.  Before
    retrying, sleep for initial_sleep_seconds. Double the sleep time on each
    retry.  If the timeout is exceeded or an unexpected exception is raised,
    raise the underlying exception.

    :param function the function that will be retried
    :param on a list of expected Exception classes
    :param exception_checker an instance of RetryExceptionChecker that is
        used to determine if the exception is expected
    :param timeout stop retrying if this number of seconds have lapsed
    :param initial_sleep_seconds
    """
    start_time = time.time()

    def _wrapped(*args, **kwargs):
        for attempt in xrange(1, 1000):
            try:
                return function(*args, **kwargs)
            except Exception as e:
                now = time.time()

                expected = False
                if exception_checker and exception_checker.is_expected(e):
                    expected = True
                if on and e.__class__ in on:
                    expected = True

                if not expected:
                    raise
                if now - start_time > timeout:
                    log.error(
                        'Exceeded timeout of %s seconds for %s',
                        timeout,
                        function.__name__)
                    raise
                else:
                    sleep(initial_sleep_seconds * float(attempt))
    return _wrapped


def get_domain_from_brkt_env(brkt_env):
    """Return the domain string from the api_host in the brkt_env. """

    api_host = brkt_env.api_host
    if not api_host:
        raise ValidationError('api_host endpoint not in brkt_env: %s' %
                              brkt_env)

    # Consider the domain to be everything after the first '.' in
    # the api_host.
    return api_host.split('.', 1)[1]


def make_nonce():
    """Returns a 32bit nonce in hex encoding"""
    return str(uuid.uuid4()).split('-')[0]


def validate_dns_name_ip_address(hostname):
    """ Verifies that the input hostname is indeed a valid
    host name or ip address

    :return True if valid, returns False otherwise
    """
    # ensure length does not exceed 255 characters
    if len(hostname) > 255:
        return False
    # remove the last dot from the end
    if hostname[-1] == ".":
        hostname = hostname[:-1]
    valid = re.compile("(?!-)[A-Z\d-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(valid.match(x) for x in hostname.split("."))


def append_suffix(name, suffix, max_length=None):
    """ Append the suffix to the given name.  If the appended length exceeds
    max_length, truncate the name to make room for the suffix.

    :return: The possibly truncated name with the suffix appended
    """
    if not suffix:
        return name
    if max_length:
        truncated_length = max_length - len(suffix)
        name = name[:truncated_length]
    return name + suffix


def urlsafe_b64encode(content):
    """ Encode the given content as URL-safe base64 and remove padding. """
    return base64.urlsafe_b64encode(content).replace(b'=', b'')


def urlsafe_b64decode(base64_string):
    """ Decode the given base64 string, generated by urlsafe_b64encode().
    """
    # Reinstate removed padding.
    removed = len(base64_string) % 4
    if removed > 0:
        base64_string += b'=' * (4 - removed)

    return base64.urlsafe_b64decode(base64_string)


def parse_name_value(name_value):
    """ Parse a string in NAME=VALUE format.

    :return: a tuple of name, value
    :raise: ValidationError if name_value is malformed
    """
    m = re.match(r'([^=]+)=(.+)', name_value)
    if not m:
        raise ValidationError(
            '%s is not in the format NAME=VALUE' % name_value)
    return m.group(1), m.group(2)


def render_table_rows(rows, row_prefix=''):
    """ Render the supplied rows as a table. This computes the maximum width
    of each column and renders each row such that all columns are left
    justified. Each value must be formattable as a string.

    An example:

    >>> from brkt_cli.util import render_table_rows
    >>> rows = [["foo", "bar", "baz"], ["foofoo", "barbarbar", "baz"]]
    >>> print render_table_rows(rows)
    foo    bar       baz
    foofoo barbarbar baz
    >>>

    :param rows a list of lists that represent the rows that are to be
    rendered.
    :param row_prefix an optional string that will be prepended to each
    row after it has been rendered.

    :return the rows rendered as a string.
    """
    if len(rows) == 0:
        return ''
    widths = [0 for _ in rows[0]]
    for row in rows:
        for ii, col in enumerate(row):
            widths[ii] = max(widths[ii], len(col))
    fmts = []
    for width in widths:
        fmts.append('{:' + str(width) + '}')
    fmt = " ".join(fmts)
    lines = []
    for row in rows:
        lines.append(row_prefix + fmt.format(*row))
    table = "\n".join(lines)
    return table


def parse_endpoint(endpoint):
    """Parse a <host>[:<port>] string into its constituent parts.

    :param endpoint a string of the form <host>[:<port>]
    :return a tuple of (host, port).  port is None if not specified.
    :raises ValidationError if an invalid string is supplied.
    """

    parts = endpoint.split(':')
    if len(parts) > 2:
        raise ValidationError(endpoint + ' must be in the form host[:port]')
    host = parts[0]
    port = None
    if len(parts) == 2:
        try:
            port = int(parts[1])
        except ValueError:
            raise ValidationError('Invalid port: %s' % parts[1])
    if not validate_dns_name_ip_address(host):
        raise ValidationError('Invalid hostname: ' + host)

    return host, port


def write_to_file_or_stdout(content, path=None):
    """ Write a content to either the given path, or stdout if path is None.
    :raise ValidationError if the file can't be written
    """
    if not path:
        print content
        return

    try:
        with open(path, 'w') as f:
            f.write(content)
    except IOError as e:
        raise ValidationError('Unable to write to %s: %s' % (path, e))


def pretty_print_json(d, indent=4):
    """ Format the given dictionary as a JSON string.
    """
    return json.dumps(
        d, sort_keys=True, indent=indent, separators=(',', ': '))
