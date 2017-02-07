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


def add_out(parser):
    """ Add the --out argument, for writing command output to a file instead
    of stdout.
    """
    parser.add_argument(
        '--out',
        metavar='PATH',
        help=(
            'Write the private key to a file instead of stdout.  This '
            'can be used to avoid character encoding issues when '
            'redirecting output on Windows.'
        )
    )
