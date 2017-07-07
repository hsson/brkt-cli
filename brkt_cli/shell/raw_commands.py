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
from copy import copy

from argparse import ArgumentParser

from brkt_cli.shell.enum import Enum


def traverse_tree(name, node, arguments, description, usage, positionals, path, parse_args):
    """
    Traverse the entire raw command tree (raw command tree being the argparse tree generated in `brkt_cli/__init__.py`)
    and convert each command and argument from the raw types to the types defined in this file.
    :param name: the name of the command ("encrypt" in the `brkt aws encrypt`)
    :type name: unicode
    :param node: the node in the tree (aka the raw command)
    :type node: argparse._SubParsersAction | None
    :param arguments: the optional arguments (the ones that start with "--" of the raw command)
    :type arguments: list[argparse.Action] | None
    :param description: the description of the raw command
    :type description: unicode
    :param usage: the usage of the raw command
    :type usage: unicode
    :param positionals: the positional arguments of the raw command (the ID in `brkt aws encrypt`)
    :type positionals: list[argparse.Action] | None
    :param path: the command path. For example, `brkt.aws.encrypt`
    :type path: unicode
    :param parse_args: the raw argparse class parse_args function
    :type parse_args: ((Any, Any) -> Any) | None
    :return: a new converted node tree
    :rtype: CommandPromptToolkit
    """
    if path == '' or path is None:
        path = name
    else:
        path = path + '.' + name
    new_node = CommandPromptToolkit(name, description, usage, path, parse_args)  # Create a new command for the
    # inputted info
    if arguments is not None:  # If there are optional arguments, add them to the new node
        for argument in arguments:
            new_arg = ArgumentPromptToolkit(argument)
            new_node.optional_arguments.append(new_arg)
    if positionals is not None:  # If there are positional arguments, add them to the new node
        for positional in positionals:
            if positional.__class__.__name__ == '_SubParsersAction':  # If those positional arguments are actually
                # subcommands, don't include them
                break
            new_pos = PositionalArgumentPromptToolkit(positional)
            new_node.positionals.append(new_pos)

    if node and node.choices:  # If there is a node passed and that node (command) has subnodes (subcommands)
        for choice in node.choices.items():  # Go through each subcommand
            if choice[1]._subparsers and choice[1]._subparsers._group_actions:  # If there are subcommands to that
                # subcommand, run the function again but this time with the new subcommand and include the
                # subcommand's subcommands
                new_node.subcommands.append(traverse_tree(choice[0], choice[1]._subparsers._group_actions[0],
                                                          choice[1]._get_optional_actions(), choice[1].description,
                                                          choice[1].format_usage(),
                                                          choice[1]._positionals._group_actions, path,
                                                          ShellArgumentParser.convert_to_shell(choice[1]).parse_args))
                # Append the new subcommand to the current command
            else:  # If this subcommand has no subcommands (aka a leaf node), run the function again but this time only
                # with the intention to create a new subcommand object, not to traverse
                new_node.subcommands.append(
                    traverse_tree(choice[0], None, choice[1]._get_optional_actions(), choice[1].description,
                                  choice[1].format_usage(), choice[1]._positionals._group_actions, path,
                                  ShellArgumentParser.convert_to_shell(choice[1]).parse_args))
                # Append the new subcommand to the current command
    return new_node


class CommandPromptToolkit:
    """
    :type name: unicode
    :type description: unicode
    :type usage: unicode
    :type path: unicode
    :type parse_args: (list[unicode], argparse.Namespace) -> argparse.Namespace
    :type subcommands: list[CommandPromptToolkit]
    :type optional_arguments: list[ArgumentPromptToolkit]
    :type positionals: list[ArgumentPromptToolkit]
    """
    def __init__(self, name, description, usage, path, parse_args):
        """
        The new version of a command. Has a name, optional subcommands, description, usage, optional arguments, and
        positional arguments.
        :param name: the name of the command
        :type name: unicode
        :param description: the description of the command
        :type description: unicode
        :param usage: the usage of the command
        :type usage: unicode
        :param path: the path of the command. For example, `brkt.aws.encrypt`
        :type path: unicode
        :param parse_args: the parse arguments function from the raw argparse class
        :type parse_args: (list[unicode], argparse.Namespace) -> argparse.Namespace
        """
        self.name = name
        self.description = description
        self.usage = usage
        self.path = path
        self.parse_args = parse_args
        self.subcommands = []
        self.optional_arguments = []
        self.positionals = []

    def list_subcommand_names(self):
        """
        Lists names of all subcommands
        :return: a list of subcommand name strings
        :rtype: list[unicode]
        """
        return map(lambda x: x.name, self.subcommands)

    def get_all_paths(self):
        """
        Get all paths and subpaths of that command
        :return: a list of path strings
        :rtype: list[unicode]
        """
        return _get_all_subpaths(self)

    def get_subcommand_from_path(self, path):
        """
        Gets a subcommand from the path specified. For example, it would return the aws encrypt command from
        `brkt.aws.encrypt`
        :param path: the path to the command. May NOT have an argument appended to the end of the path
        :type path: unicode
        :return: the subcommand or the closest the function could get to the subcommand. (so `brkt.aws.foobar` would
        return the aws subcommand (path at `brkt.aws`)
        :rtype: CommandPromptToolkit
        """
        path_split = path.split('.')
        if len(path_split) <= 1:
            return self
        path_split = path_split[1:]
        if self.has_subcommands():
            for sc in self.subcommands:
                if sc.name == path_split[0]:
                    return sc.get_subcommand_from_path('.'.join(path_split))
        else:
            return self

    def get_argument_from_full_path(self, path):
        """
        Gets an argument from the full path (`brkt.aws.encrypt.ID` is a full path as 'ID' is an argument)
        :param path: the path to the argument
        :type path: unicode
        :return: the argument found
        :rtype: ArgumentPromptToolkit | None
        """
        cmd = self.get_subcommand_from_path(path[:-1])
        return cmd.__get_argument_from_direct_path(path)

    def __get_argument_from_direct_path(self, path):
        """
        Private function to get an argument based on the path. The function MUST be run from the command that is the
        direct parent to the child
        :param path: the path to the argument
        :type path: unicode
        :return: the argument found
        :rtype: ArgumentPromptToolkit | None
        """
        path_split = path.split('.')
        if len(path_split) < 2:
            return None
        path_split = path_split[1:]
        arg_name = path_split[-1]
        args_dict = self.make_pos_and_arg_name_to_dict()
        if arg_name in args_dict:
            return args_dict[arg_name]
        else:
            return None

    def has_subcommands(self):
        """
        Checks if command has subcommands
        :return: if the command has subcommands
        :rtype: bool
        """
        return self.subcommands and len(self.subcommands) > 0

    def list_argument_names(self):
        """
        Lists names of all optional arguments
        :return: a list of optional argument name strings
        :rtype: list[unicode]
        """
        ret = []
        for arg in self.optional_arguments:
            ret.append(arg.tag)
        return ret

    def make_pos_and_arg_name_to_dict(self):
        """
        Makes the positional and optional arguments into a dictionary of names as keys and the argument object as values
        :return: dictionary of names to arguments
        :rtype: dict[unicode, ArgumentPromptToolkit]
        """
        ret = {}
        for arg in self.optional_arguments:
            ret[arg.get_name()] = arg
        for arg in self.positionals:
            ret[arg.get_name()] = arg
        return ret

    def make_tag_to_args_dict(self):
        """
        Makes the optional arguments into a dictionary of tags (names) as keys and the argument object as values
        :return: dictionary of tags to optional arguments
        :rtype: dict[str, ArgumentPromptToolkit]
        """
        ret = {}
        for arg in self.optional_arguments:
            ret[arg.tag] = arg
        return ret


def _get_all_subpaths(cmd):
    """
    Recursive inner function that gets all subcommands based on a command.
    :param cmd: the command to get subcommands from
    :type cmd: CommandPromptToolkit
    :return: list of subcommand paths
    :rtype: list[unicode]
    """
    ret = [cmd.path]
    for subcmd in cmd.subcommands:
        ret.extend(_get_all_subpaths(subcmd))

    return ret


class ArgumentPromptToolkit:
    """
    :type raw: argparse.Action
    :type tag: unicode
    :type description: unicode
    :type metavar: unicode
    :type dest: unicode
    :type default: Any
    :type choices: list[unicode] | None
    :type type: int
    """
    class Type(Enum):
        """
        An enumeration of the argument type
        :type Unknown: int
        :type Store: int
        :type StoreConst: int
        :type StoreFalse: int
        :type StoreTrue: int
        :type Append: int
        :type AppendConst: int
        :type Count: int
        :type Help: int
        """
        Unknown, Store, StoreConst, StoreFalse, StoreTrue, Append, AppendConst, Count, Help, Version = range(10)

    def __init__(self, raw):
        """
        The new version of arguments. Has a raw value, a tag (name), description, metavar, optional choices, and type.
        :param raw: the raw value to be unpacked
        :type raw: argparse.Action
        """
        self.raw = copy(raw)
        self.tag = raw.option_strings[-1]
        self.description = raw.help
        self.metavar = raw.metavar
        self.dest = raw.dest
        self.default = raw.default
        self.choices = raw.choices  # choices can be either None or an array of strings. If it is not None, than the
        # completer will suggest those choices

        try:
            raw_type = {
                '_StoreAction': self.Type.Store,
                '_StoreConstAction': self.Type.StoreConst,
                '_StoreFalseAction': self.Type.StoreFalse,
                '_StoreTrueAction': self.Type.StoreTrue,
                '_AppendAction': self.Type.Append,
                '_AppendConstAction': self.Type.AppendConst,
                '_CountAction': self.Type.Count,
                '_HelpAction': self.Type.Help,
                '_VersionAction': self.Type.Version,
            }[raw.__class__.__name__]  # Try to match the type of argument (found in the class name) to the enum type
            self.type = raw_type
        except KeyError:
            self.type = self.Type.Unknown

    def get_name(self):
        """
        Gets the name of the argument. If the argument is positional or has no tag (ID in `brkt.aws.encrypt`), the name
        would be the metavar ('ID'). If it is an optional argument (--aws-tag in `brkt.aws.encrypt`), the name would be
        a stripped tag ('aws-tag'). Else, it would be the destination.
        :return: the name
        :rtype: unicode
        """
        if (self.tag is None or self.tag == '') and self.metavar:
            return self.metavar
        elif self.tag.startswith('-'):
            return self.tag[2 if self.tag.startswith('--') else 1:]
        else:
            return self.dest


class PositionalArgumentPromptToolkit(ArgumentPromptToolkit):
    """
    :type raw: argparse.Action
    """
    def __init__(self, raw):
        """
        The parameter type for positional arguments (like ID in `aws encrypt`)
        :param raw: the raw value to be unpacked
        :type raw: argparse.Action
        """
        new_raw = copy(raw)
        if len(new_raw.option_strings) == 0:
            new_raw.option_strings = ['']
        ArgumentPromptToolkit.__init__(self, new_raw)


class ShellArgumentParser(ArgumentParser):
    """
    A wrapper around the argparse.ArgumentParser so that commands can be parsed without the default mechanics of
    argparse being utilized
    """
    def error(self, message):
        """
        Silenced error method so it does not disturb the shell
        :param message: The error message
        :type message: str
        """
        pass

    @classmethod
    def convert_to_shell(cls, obj):
        """
        Converts an object to the ShellArgumentParser
        :param obj: the old object which should be a regular ArgumentParser
        :type obj: argparse.ArgumentParser
        :return: the new object as a ShellArgumentParser
        :rtype: ShellArgumentParser
        """
        obj.__class__ = ShellArgumentParser
        return obj
