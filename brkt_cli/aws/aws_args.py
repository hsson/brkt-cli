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


def add_region(parser, parsed_config):
    parser.add_argument(
        '--region',
        metavar='NAME',
        help='The AWS region metavisors will be launched into',
        dest='region',
        default=parsed_config.get_option('aws.region')
    )


def add_no_validate(parser):
    parser.add_argument(
        '--no-validate',
        dest='validate',
        action='store_false',
        default=True,
        help="Don't validate AMIs, snapshots, subnet, or security groups"
    )


def add_security_group(parser):
    parser.add_argument(
        '--security-group',
        metavar='ID',
        dest='security_group_ids',
        action='append',
        help=(
            'Use this security group when running the encryptor instance. '
            'May be specified multiple times.'
        )
    )


def add_subnet(parser):
    parser.add_argument(
        '--subnet',
        metavar='ID',
        dest='subnet_id',
        help='Launch instances in this subnet'
    )


def add_aws_tag(parser):
    parser.add_argument(
        '--aws-tag',
        metavar='KEY=VALUE',
        dest='aws_tags',
        action='append',
        help=(
            'Set an AWS tag on resources created during encryption. '
            'May be specified multiple times.'
        )
    )


def add_key(parser, help=argparse.SUPPRESS):
    # Optional EC2 SSH key pair name to use for launching the guest
    # and encryptor instances.  This argument is hidden by default because
    # it's only used for development.
    parser.add_argument(
        '--key',
        metavar='NAME',
        help=help,
        dest='key_name'
    )


def add_encryptor_ami(parser):
    # Optional AMI ID that's used to launch the encryptor instance.  This
    # argument is hidden because it's only used for development.
    parser.add_argument(
        '--encryptor-ami',
        metavar='ID',
        dest='encryptor_ami',
        help=argparse.SUPPRESS
    )


def add_retry_timeout(parser):
    # Optional arguments for changing the behavior of our retry logic.  We
    # use these options internally, to avoid intermittent AWS service failures
    # when running concurrent encryption processes in integration tests.
    parser.add_argument(
        '--retry-timeout',
        metavar='SECONDS',
        type=float,
        help=argparse.SUPPRESS,
        default=10.0
    )


def add_retry_initial_sleep_seconds(parser):
    parser.add_argument(
        '--retry-initial-sleep-seconds',
        metavar='SECONDS',
        type=float,
        help=argparse.SUPPRESS,
        default=0.25
    )
