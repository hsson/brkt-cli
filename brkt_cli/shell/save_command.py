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


def alias_inner_command_func(params, app):
    """
    Creates an alias to a command
    :param params: command parameters
    :type params: _sre.SRE_Match
    :param app: the app it is running from
    :type app: brkt_cli.shell.app.App
    :return: nothing
    :rtype: None
    :raises: InnerCommandError
    """
    arg_name = params.group(1)
    app.saved_commands[arg_name] = params.group(2)


def complete_alias_inner_command(arg_idx, app, full_args_text, document):
    """
    Suggests suggestions when typing in the alias command
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
    split_doc = re.split(r'([ ]+)', document.text)
    if len(split_doc) == 3:
        return []
    elif len(split_doc) >= 5:
        text = ''.join(split_doc[3:])
        cursor = document.cursor_position - len(''.join(split_doc[:3]))
        if cursor < 0:
            cursor = 0
        return app.completer.get_completions_list(Document(text=unicode(text), cursor_position=cursor), include_aliases=False)
    return []


def get_alias_inner_command_func(params, app):
    """
    Gets an alias
    :param params: command parameters
    :type params: _sre.SRE_Match
    :param app: the app it is running from
    :type app: brkt_cli.shell.app.App
    :return: nothing
    :rtype: None
    :raises: InnerCommandError
    """
    arg_name = params.group(1)
    if arg_name not in app.saved_commands:
        raise InnerCommandError('Could not find the saved command')
    print app.saved_commands[arg_name]


def complete_get_alias_inner_command(arg_idx, app, full_args_text, document):
    """
    Suggest an alias name
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
        return app.saved_commands.keys()
    else:
        return []


def unalias_inner_command_func(params, app):
    """
    Delete an alias by alias name
    :param params: command parameters
    :type params: _sre.SRE_Match
    :param app: the app it is running from
    :type app: brkt_cli.shell.app.App
    :return: nothing
    :rtype: None
    :raises: InnerCommandError
    """
    arg_name = params.group(1)
    if arg_name not in app.saved_commands:
        raise InnerCommandError('Could not find the saved command')
    del app.saved_commands[arg_name]


def complete_unalias_inner_command(arg_idx, app, full_args_text, document):
    """
    Suggest an alias name
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
        return app.saved_commands.keys()
    else:
        return []

alias_inner_command = InnerCommand('alias', 'Creates an alias to a command', 'alias NAME COMMAND', alias_inner_command_func,
                                 completer=complete_alias_inner_command,
                                 param_regex=r'^([^ ]+) (.+)$')
get_alias_inner_command = InnerCommand('get_alias', 'Gets an alias to a command', 'get_alias NAME', get_alias_inner_command_func,
                                 completer=complete_get_alias_inner_command,
                                 param_regex=r'^(.+)$')
unalias_inner_command = InnerCommand('unalias', 'Removes alias to a command', 'unalias NAME', unalias_inner_command_func,
                                 completer=complete_unalias_inner_command,
                                 param_regex=r'^(.+)$')