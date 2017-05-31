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

from brkt_cli.aws import aws_args


def setup_share_logs_args(parser, parsed_config):
    parser.add_argument(
        '--snapshot',
        metavar='ID',
        dest='snapshot_id',
        help='The snapshot with Bracket system logs to be shared'
    )
    parser.add_argument(
        '--instance',
        metavar='ID',
        dest='instance_id',
        help='The instance with Bracket system logs to be shared'
    )
    parser.add_argument(
        '--region',
        metavar='NAME',
        dest='region',
        help='The region of the instance(e.g. us-west-2)',
        required=True
    )
    parser.add_argument(
        '--bucket',
        metavar='NAME',
        dest='bucket',
        help='Bucket that logs file is uploaded to',
        required=True
    )
    parser.add_argument(
        '--log-path',
        metavar='PATH',
        dest='path',
        help='PATH in bucket to store logs file',
        default='logs.tar.gz'
    )
    parser.add_argument(
        '--subnet',
        metavar='ID',
        dest='subnet_id',
        help='Launch instances in this subnet',
        required=False
    )
    aws_args.add_no_validate(parser)
    aws_args.add_retry_timeout(parser)
    aws_args.add_retry_initial_sleep_seconds(parser)
