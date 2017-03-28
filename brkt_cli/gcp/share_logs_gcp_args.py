# Copyright 2015 Bracket Computing, Inc. All Rights Reserved.
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


def setup_share_logs_gcp_args(parser):
    parser.add_argument(
        '--instance',
        metavar='NAME',
        dest='instance',
        help='The instance with Bracket system logs to be shared',
        required=True
    )
    parser.add_argument(
        '--zone',
        metavar='NAME',
        help='GCP zone (e.g. us-central1-a)',
        dest='zone',
        required=True
    )
    parser.add_argument(
        '--email',
        metavar='ADDRESS',
        help='Gmail address to share logs with',
        dest='email',
        required=True
    )
    parser.add_argument(
        '--bucket',
        metavar='NAME',
        help='Bucket name to store logs',
        dest='bucket',
        required=True
    )
    parser.add_argument(
        '--log-path',
        metavar='PATH',
        help='PATH in bucket to store logs file (e.g. dir/logsfile)',
        dest='path',
        default='diags.tar.gz'
    )
    parser.add_argument(
        '--project',
        metavar='NAME',
        help='Name of project',
        dest='project',
        required=True
    )
