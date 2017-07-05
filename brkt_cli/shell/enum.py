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


def enum(**enums):
    """
    Creates an enumeration in Python.
    Example usage would be:
        `foo = enum(ZERO=0, ONE=1, TWO=2)`
    You would be able to match enums like this:
        `if var == foo.ONE:`
    :param enums: the enumerations matched to the number identifier
    :return: an enum type
    """
    return type(str('Enum'), (), enums)
