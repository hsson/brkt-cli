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
class Enum:
    @classmethod
    def format_enum(cls, enum):
        """
        Formats an enum as a string
        :param enum: the enum integer
        :type enum: int
        :return: the string name of the enum
        :rtype: unicode
        """
        for val in filter((lambda (key, value): not key.startswith('__')), cls.__dict__.items()):
            if val[1] == enum:
                return val[0]
