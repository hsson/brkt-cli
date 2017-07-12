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
import re

from prompt_toolkit.document import Document

from brkt_cli.shell.inner_commands import InnerCommand, InnerCommandError


class Setting(object):
    """
    :type name: unicode
    :type default: T
    :type _value: T
    :type _on_changed: (T) -> None
    :type _validate_change: (T) -> None
    :type _parse_value: (unicode) -> T
    :type type: type
    :type description: unicode
    :type str_acceptable_values: list[unicode]
    :type suggestions: list[unicode]
    """
    def __init__(self, name, default, on_changed=None, validate_change=None, parse_value=None, description='',
                 str_acceptable_values=None, suggestions=None):
        """
        An app setting
        :param name: the name of the setting
        :type name: unicode
        :param default: the default value
        :type default: T
        :param on_changed: called when there is a change to the value
        :type on_changed: (T) -> None
        :param validate_change: called to validate the new change
        :type validate_change: (T) -> None
        :param parse_value: called to parse a new string as a value
        :type parse_value: (unicode) -> T
        :param description: description of setting
        :type description: unicode
        :param str_acceptable_values: only these values will be accepted via the string method
        :type str_acceptable_values: list[unicode]
        :param suggestions: things to suggest in the completer
        :type suggestions: list[unicode]
        """
        self.name = name
        self.default = default
        self._value = default
        self._on_changed = on_changed
        self._validate_change = validate_change
        self._parse_value = parse_value
        self.type = type(default) if default is not None else unicode
        self.description = description
        self.str_acceptable_values = str_acceptable_values
        if str_acceptable_values is not None:
            suggestions = str_acceptable_values
        self.suggestions = suggestions

    @property
    def value(self):
        """
        Getter for the value
        :return: the value
        :rtype: T
        """
        return self._value

    @value.setter
    def value(self, val):
        """
        Setter for the value
        :param val: the new value
        :type val: T
        """
        validated = True
        if self._validate_change is not None:
            validated = self._validate_change(val)

        if validated:
            self._value = val
            if self._on_changed is not None:
                self._on_changed(self._value)
        else:
            raise InnerCommandError('Setting value was not validated')


    def set_value_with_str(self, val):
        """
        Sets the value of the setting from a unicode input
        :param val: the new value string
        :type val: unicode
        """
        if self.str_acceptable_values is not None and val.lower() not in self.str_acceptable_values:
            raise InnerCommandError('Value is not an acceptable value')
        if self._parse_value is not None:
            self.value = self._parse_value(val)
        else:
            self.value = self.type(val)


def bool_parse_value(val):
    """
    Setting parse for booleans. Must also make the str_acceptable_values=['true','false']
    :param val: the string value
    :type val: unicode
    :return: the parsed value
    :rtype: bool
    """
    return val.lower() == 'true'


def bool_validate_change(val):
    """
    Setting validate change for booleans. Must also set up bool_parse_value.
    :param val: the value
    :type val: Any
    :return: if it is validated
    :rtype: bool
    """
    return isinstance(val, bool)


def setting_inner_command_func(params, app):
    """
    Displays or modifies a setting
    :param params: command parameters
    :type params: _sre.SRE_Match
    :param app: the app it is running from
    :type app: brkt_cli.shell.app.App
    :return: nothing
    :rtype: None
    :raises: InnerCommandError
    """
    setting_name = params.group(1)
    if setting_name not in app.settings:
        raise InnerCommandError('Unknown setting name')
    setting = app.settings[setting_name]
    setting_value = params.group(2)
    if setting_value is None or setting_value == '':
        accepted_values = ''
        if setting.str_acceptable_values is not None:
            accepted_values = '\n    Accepted Values: ' + ', '.join(setting.str_acceptable_values)
        print '%s - %s\n    Suggestions: %s' % (
            setting.name, 
            str(setting.value) + accepted_values,
            ', '.join(setting.suggestions)
        )
    else:
        setting.set_value_with_str(setting_value)


def complete_setting_inner_command(arg_idx, app, full_args_text, document):
    """
    Suggests suggestions when typing in the setting command
    :param arg_idx: the index of the current and selected argument
    :type arg_idx: int
    :param app: the app that is running
    :type app: brkt_cli.shell.app.App
    :param full_args_text: the text arguments that are finished
    :type full_args_text: list[unicode]
    :param document: the document of the current prompt/buffer
    :type document: prompt_toolkit.document.Document
    :return: a list of acceptable suggestions
    :rtype: list[unicode]
    """
    if arg_idx == 0:
        return app.settings.keys()
    elif arg_idx == 1:
        setting_name = full_args_text[0]
        if setting_name not in app.settings:
            return []
        setting = app.settings[setting_name]
        return setting.suggestions if setting.suggestions is not None else []
    else:
        return []


setting_inner_command = InnerCommand('setting', 'Edit or view a setting', 'setting NAME [value]', setting_inner_command_func,
                                 completer=complete_setting_inner_command,
                                 param_regex=r'^([^ ]+)(?: (.+))?$')