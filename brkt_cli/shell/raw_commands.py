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
from brkt_cli.shell.enum import enum


def traverse_tree(name, node, arguments, description, usage, positionals):
    """
    Traverse the entire raw command tree (raw command tree being the argparse tree generated in `brkt_cli/__init__.py`)
    and convert each command and argument from the raw types to the types defined in this file.
    :param name: the name of the command ("encrypt" in the `brkt aws encrypt`)
    :param node: the node in the tree (aka the raw command)
    :param arguments: the optional arguments (the ones that start with "--" of the raw command)
    :param description: the description of the raw command
    :param usage: the usage of the raw command
    :param positionals: the positional arguments of the raw command (the ID in `brkt aws encrypt`)
    :return: a new converted node tree
    """
    new_node = CommandPromptToolkit(name, description, usage)  # Create a new command for the inputted info
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
                                                          choice[1]._positionals._group_actions))  # Append the new
                # subcommand to the current command
            else:  # If this subcommand has no subcommands (aka a leaf node), run the function again but this time only
                # with the intention to create a new subcommand object, not to traverse
                new_node.subcommands.append(
                    traverse_tree(choice[0], None, choice[1]._get_optional_actions(), choice[1].description,
                                  choice[1].format_usage(), choice[1]._positionals._group_actions))  # Append the new
                # subcommand to the current command
    return new_node


class CommandPromptToolkit:
    """
    The new version of a command. Has a name, optional subcommands, description, usage, optional arguments, and
    positional arguments.
    :param name: the name of the command
    :param description: the description of the command
    :param usage: the usage of the command
    """
    def __init__(self, name, description, usage):
        self.name = name
        self.subcommands = []
        self.description = description
        self.usage = usage
        self.optional_arguments = []
        self.positionals = []

    def list_subcommand_names(self):
        """
        Lists names of all subcommands
        :return: a list of subcommand name strings
        """
        ret = []
        for sc in self.subcommands:
            ret.append(sc.name)

        return ret

    def has_subcommands(self):
        """
        Checks if command has subcommands
        :return: boolean
        """
        return self.subcommands and len(self.subcommands) > 0

    def list_argument_names(self):
        """
        Lists names of all optional arguments
        :return: a list of optional argument name strings
        """
        ret = []
        for arg in self.optional_arguments:
            ret.append(arg.tag)
        return ret

    def make_tag_to_args_dict(self):
        """
        Makes the optional arguments into a dictionary of tags (names) as keys and the argument object as values
        :return: dictionary of tag strings to argument ArgumentPromptToolkits
        """
        ret = {}
        for arg in self.optional_arguments:
            ret[arg.tag] = arg
        return ret


class ArgumentPromptToolkit:
    """
    The new version of arguments. Has a raw value, a tag (name), description, metavar, optional choices, and type.
    :param raw: the raw value to be unpacked
    """
    TYPE_ENUM = enum(UNKNOWN=0, STORE=1, STORE_CONST=2, STORE_FALSE=3, STORE_TRUE=4, APPEND=5, APPEND_CONST=6, COUNT=7,
                     HELP=8, VERSION=9)

    def __init__(self, raw):
        self.raw = raw
        self.tag = raw.option_strings[-1]
        self.description = raw.help
        self.metavar = raw.metavar
        self.choices = raw.choices  # choices can be either None or an array of strings. If it is not None, than the
        # completer will suggest those choices

        try:
            raw_type = {
                '_StoreAction': self.TYPE_ENUM.STORE,
                '_StoreConstAction': self.TYPE_ENUM.STORE_CONST,
                '_StoreFalseAction': self.TYPE_ENUM.STORE_FALSE,
                '_StoreTrueAction': self.TYPE_ENUM.STORE_TRUE,
                '_AppendAction': self.TYPE_ENUM.APPEND,
                '_AppendConstAction': self.TYPE_ENUM.APPEND_CONST,
                '_CountAction': self.TYPE_ENUM.COUNT,
                '_HelpAction': self.TYPE_ENUM.HELP,
                '_VersionAction': self.TYPE_ENUM.VERSION,
            }[raw.__class__.__name__]  # Try to match the type of argument (found in the class name) to the enum type
            self.type = raw_type
        except KeyError:
            self.type = self.TYPE_ENUM.UNKNOWN


class PositionalArgumentPromptToolkit(ArgumentPromptToolkit):
    """
    The parameter type for positional arguments (like ID in `aws encrypt`)
    :param raw: the raw value to be unpacked
    """
    def __init__(self, raw):
        if len(raw.option_strings) == 0:
            raw.option_strings = [""]
        ArgumentPromptToolkit.__init__(self, raw)
