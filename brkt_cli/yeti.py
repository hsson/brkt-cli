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
import httplib
import logging

import requests

log = logging.getLogger(__name__)


class Customer(object):
    def __init__(self, uuid=None, name=None, email=None):
        self.uuid = uuid
        self.name = name
        self.email = email


class YetiError(Exception):
    def __init__(self, http_status, message=None):
        if not message:
            if http_status == 401:
                message = httplib.responses[http_status]

        super(YetiError, self).__init__(message)
        self.http_status = http_status


def make_json_headers(token=None):
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    if token:
        headers['Authorization'] = 'Bearer %s' % token
    return headers


def _get_reason(d):
    reason = None
    if 'reason' in d:
        reason = d['reason']
    if 'error_description' in d:
        reason = d['error_description']
    return reason


def get_json(url, token=None, timeout=10.0):
    """ Send an HTTP GET to the given endpoint and return the response
    payload as a dictionary.

    :param token the API token (JWT)
    :raise YetiError if the endpoint returns an HTTP error status
    :raise IOError if a network error or timeout occurred
    """
    log.debug('Sending HTTP GET to %s', url)

    headers = make_json_headers(token=token)
    r = requests.get(url, headers=headers, timeout=timeout)
    if r.status_code / 100 != 2:
        msg = None
        if r.status_code == 400:
            msg = _get_reason(r.json())
        raise YetiError(http_status=r.status_code, message=msg)

    return r.json()


def post_json(url, token=None, json=None, timeout=10.0):
    """ Send an HTTP POST to the given endpoint and return the response
    payload as a dictionary.

    :param token the API token (JWT)
    :param json an optional dictionary to post as JSON
    :raise YetiError if the endpoint returns an HTTP error status
    :raise IOError if a network error or timeout occurred
    """
    log.debug('Sending HTTP POST to %s', url)

    headers = make_json_headers(token=token)

    r = requests.post(url, headers=headers, json=json, timeout=timeout)
    if r.status_code / 100 != 2:
        msg = None
        if r.status_code == 400:
            msg = _get_reason(r.json())
        raise YetiError(http_status=r.status_code, message=msg)

    return r.json()


class YetiService(object):

    def __init__(self, root_url, token=None):
        self.root_url = root_url
        self.token = token

    def auth(self, email, password):
        """ Authenticate with the Yeti service.

        :return the API token (JWT)
        :raise YetiError if authentication failed
        :raise IOError if a network error or timeout occurred
        """
        payload = {
            'username': email,
            'password': password,
            'grant_type': 'password'
        }
        d = post_json(
            self.root_url + '/oauth/credentials',
            json=payload
        )
        self.token = str(d['id_token'])  # Convert Unicode to ASCII
        return self.token

    def get_customer_json(self):
        """ Return the Customer object response from the server as a
        dictionary.
        """
        return get_json(
            self.root_url + '/api/v1/customer/self',
            token=self.token
        )

    def get_customer(self):
        """ Return the Customer object.

        :raise YetiError if Yeti returns an HTTP error status.
        """
        d = self.get_customer_json()
        return Customer(
            uuid=d['uuid'],
            name=d['name'],
            email=d['email']
        )

    def get_launch_token(self, tags=None):
        """ Return a Metavisor launch token (JWT).

        :param tags a string map that specifies Bracket tags that will be
        added to the JWT payload.
        """
        tags = tags or {}
        payload = {}
        if tags:
            payload['tags'] = []
            for key, value in tags.iteritems():
                tag_dict = {'key': key, 'value': value}
                payload['tags'].append(tag_dict)

        d = post_json(
            self.root_url + '/api/v1/token',
            token=self.token,
            json=payload
        )
        return d['jwt']
