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


def setup_wrap_instance_args(parser, parsed_config):
    parser.add_argument(
        'instance_id',
        metavar='ID',
        help='The ID of the instance that will be wrapped with Metavisor'
    )
    parser.add_argument(
        '--wrapped-instance-name',
        metavar='NAME',
        dest='wrapped_instance_name',
        help='Specify the name of the wrapped Bracket instance',
        required=False
    )
    aws_args.add_no_validate(parser)
    aws_args.add_region(parser, parsed_config)
    aws_args.add_metavisor_version(parser)

    # Optional AMI ID that's used to launch the encryptor instance.  This
    # argument is hidden because it's only used for development.
    aws_args.add_encryptor_ami(parser)

    # Optional arguments for changing the behavior of our retry logic.  We
    # use these options internally, to avoid intermittent AWS service failures
    # when running concurrent encryption processes in integration tests.
    aws_args.add_retry_timeout(parser)
    aws_args.add_retry_initial_sleep_seconds(parser)
