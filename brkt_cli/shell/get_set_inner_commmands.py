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
from brkt_cli.shell.inner_commands import InnerCommand, InnerCommandError


def set_inner_command_func(params, app):
    """
    Sets an argument value for the shell session
    :param params: command parameters. Should have two parameters: path and value
    :type params: _sre.SRE_Match
    :param app: the app it is running from
    :type app: brkt_cli.shell.app.App
    :return: nothing
    :rtype: None
    :raises: AssertionError
    :raises: InnerCommandError
    """
    arg_name = params.group(1)
    arg_val = params.group(2)
    arg_name_split = arg_name.split('.')
    cmd_path = '.'.join(arg_name_split[:-1])  # Get the just command path, not the full path with the argument

    if cmd_path not in app.cmd.get_all_paths():
        raise InnerCommandError('Unknown command in path key')
    sc = app.cmd.get_subcommand_from_path(cmd_path)
    if arg_name_split[-1] not in map(lambda x: x.get_name(),
                                     filter(lambda v: v.type is not v.Type.Help and v.type is not v.Type.Version,
                                            sc.optional_arguments + sc.positionals)):  # Make sure the selected
        # argument is not a help or version argument
        raise InnerCommandError('Unknown argument in path key')

    if cmd_path not in app.set_args:  # If there is no command path set in the app, set it!
        app.set_args[cmd_path] = {}

    app.set_args[cmd_path][arg_name_split[-1]] = parse_set_command_arg(
        arg_val, sc.make_pos_and_arg_name_to_dict()[arg_name_split[-1]])  # Set the value


def complete_set_inner_command(arg_idx, app, full_args_text, document):
    """
    Do completion for the /set command
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
    if arg_idx == 0:  # If the user is on the first argument, suggest full paths (ones with commands and the argument)
        arg_list = []
        for path in app.cmd.get_all_paths():
            got_cmd = app.cmd.get_subcommand_from_path(path)
            if got_cmd is None or got_cmd.has_subcommands() is True:
                continue
            arg_list.extend(map(lambda x: path + '.' + x,
                                map(lambda x: x.get_name(),
                                    filter(lambda x: x.type is not x.Type.Help and x.type is not x.Type.Version,
                                           got_cmd.optional_arguments + got_cmd.positionals)
                                    )
                                ))  # Get All arguments that are not help or version and get their names and add them
            # to their command paths. This creates bunch of full paths
        return arg_list
    elif arg_idx == 1:  # If the user is on the second (and last) argument, suggest options if options are available or
        # nothing if they are not
        arg = app.cmd.get_argument_from_full_path(full_args_text[0])
        if arg is not None and arg.choices is not None and len(arg.choices) > 0:
            return arg.choices
        else:
            return []
    else:
        return []


def get_inner_command_func(params, app):
    """
    Gets an argument value for the shell session
    :param params: command parameters. Should have one parameter: a path to the command argument
    :type params: _sre.SRE_Match
    :param app: the app it is running from
    :type app: brkt_cli.shell.app.App
    :return: nothing
    :rtype: None
    :raises: InnerCommandError
    """
    arg_name = params.group(1)
    arg_name_split = arg_name.split('.')
    cmd_path = '.'.join(arg_name_split[:-1])  # Get the just command path, not the full path with the argument

    # Validate the command
    if cmd_path not in app.cmd.get_all_paths():
        raise InnerCommandError('Unknown command in path')
    sc = app.cmd.get_subcommand_from_path(cmd_path)
    if arg_name_split[-1] not in map(lambda x: x.get_name(),
                                     filter(lambda v: v.type is not v.Type.Help and v.type is not v.Type.Version,
                                            sc.optional_arguments + sc.positionals)):  # Make sure the selected
        # argument is not a help or version argument
        raise InnerCommandError('Unknown argument in path')

    if cmd_path not in app.set_args or arg_name_split[-1] not in app.set_args[cmd_path]:  # Check to see the passed
        # argument is in the app database
        print '%s: %s' % (arg_name, 'None')
    else:
        print '%s: %s' % (arg_name, app.set_args[cmd_path][arg_name_split[-1]])


def complete_get_inner_command(arg_idx, app, full_args_text, document):
    """
    Do completion for the /get command
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
    if arg_idx == 0:  # If it is the first argument, list all keys in the app
        arg_list = []
        for key, cmd in app.set_args.iteritems():
            arg_list.extend(map(lambda x: key + '.' + x, cmd.keys()))
        return arg_list
    else:
        return []


def del_inner_command_func(params, app):
    """
    Deletes an argument value for the shell session
    :param params: command parameters. Should have one parameter: a path to the command argument
    :type params: _sre.SRE_Match
    :param app: the app it is running from
    :type app: brkt_cli.shell.app.App
    :return: nothing
    :rtype: None
    :raises: InnerCommandError
    """
    arg_name = params.group(1)
    arg_name_split = arg_name.split('.')
    cmd_path = '.'.join(arg_name_split[:-1])  # Get the just command path, not the full path with the argument

    # Validate the command
    if cmd_path not in app.cmd.get_all_paths():
        raise InnerCommandError('Unknown command in path')
    sc = app.cmd.get_subcommand_from_path(cmd_path)
    if arg_name_split[-1] not in map(lambda x: x.get_name(),
                                     filter(lambda v: v.type is not v.Type.Help and v.type is not v.Type.Version,
                                            sc.optional_arguments + sc.positionals)):  # Make sure the selected
        # argument is not a help or version argument
        raise InnerCommandError('Unknown argument in path')

    if cmd_path not in app.set_args or arg_name_split[-1] not in app.set_args[cmd_path]:  # Check to see the passed
        # argument is in the app database
        raise InnerCommandError('Argument not found')
    else:
        del app.set_args[cmd_path][arg_name_split[-1]]


def complete_del_inner_command(arg_idx, app, full_args_text, document):
    """
    Do completion for the /del command
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
    if arg_idx == 0:  # If it is the first argument, list all keys in the app
        arg_list = []
        for key, cmd in app.set_args.iteritems():
            arg_list.extend(map(lambda x: key + '.' + x, cmd.keys()))
        return arg_list
    else:
        return []


def parse_set_command_arg(val, arg):
    """
    Parse values that the /set command gives
    :param val: the value that was gotten by the /set command
    :type val: unicode
    :param arg: the argument that that value must be connected to
    :type arg: brkt_cli.shell.raw_commands.ArgumentPromptToolkit
    :return: the parsed value
    :rtype: Any
    """
    if arg.type is arg.Type.Store:
        return _parse_argument_type(val, arg)
    elif arg.type is arg.Type.StoreConst or arg.type is arg.Type.StoreTrue or arg.type is arg.Type.StoreFalse or \
                    arg.type is arg.Type.AppendConst:  # If the argument is one of these, it must be either
        # true or false
        if val.lower() not in ['true', 'false']:
            raise InnerCommandError('Unknown value type. Can be either: "true", "false"')
        return val.lower() == 'true'
    elif arg.type is arg.Type.Append:
        return map(lambda x: _parse_argument_type(x.strip(), arg), val.split(','))
    else:
        return InnerCommandError('Unsupported argument type')


def _parse_argument_type(val, arg):
    """
    The meat of parse_set_command_arg. This does the parsing
    :param val: the value that was gotten by the /set command
    :type val: unicode
    :param arg: the argument that that value must be connected to
    :type arg: brkt_cli.shell.raw_commands.ArgumentPromptToolkit
    :return: the parsed value
    :rtype: Any
    """
    if arg.raw.type is not None:
        return arg.raw.type(val)
    else:
        return val


set_inner_command = InnerCommand('set', 'Sets an argument for a command', 'set PATH VALUE', set_inner_command_func,
                                 completer=complete_set_inner_command,
                                 param_regex=r'^(.+) (.+)$')
get_inner_command = InnerCommand('get', 'Gets an argument for a command', 'get PATH', get_inner_command_func,
                                 completer=complete_get_inner_command,
                                 param_regex=r'^([^ ]+)$')
del_inner_command = InnerCommand('del', 'Deletes an argument for a command', 'del PATH', del_inner_command_func,
                                 completer=complete_del_inner_command,
                                 param_regex=r'^([^ ]+)$')
