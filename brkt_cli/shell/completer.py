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
from prompt_toolkit.completion import Completer, Completion

from brkt_cli.shell import App


class ShellCompleter(Completer):
    """
    The completer for the brkt-cli
    :param command: the overall brkt command as a CommandPromptToolkit object
    """
    def __init__(self, command):
        self.command = command

    def get_completions(self, document, complete_event):
        """
        Called when the App needs to suggest words for the user
        :param document: the document of the UI (has the text, etc.)
        :param complete_event:
        :return: Completion objects that contain all matching suggestions
        """
        word_before_cursor = document.get_word_before_cursor(WORD=True).lower()
        all_text = document.text_before_cursor

        split_text = all_text.split()  # list of all values (commands, subcommands, arguments, etc.) separated by space
        full_split_text = split_text  # full_split_text is all values (see above for example) separated by space that
        # are complete.
        if not all_text.endswith(' ') and full_split_text:
            del full_split_text[-1]
        # The difference between these two is shown in this example:
        # In `aws encrypt --aws-tag foo --encry` (with `--encry` being unfinished for `--encryptor-ami`), the result of
        # split_text would be `['aws', 'encrypt', '--aws-tag', 'foo', '--encry']`, while the result of full_split_text
        # would be `['aws', 'encrypt', '--aws-tag', 'foo']`

        if all_text.startswith(App.COMMAND_PREFIX):
            completions = App.INNER_COMMANDS.keys()
        else:
            completions = self.command.list_subcommand_names()  # Possible completion values

            tree_location = self.command  # Tree location is the current selected command that is narrowed down to the exact
            #  command the user has typed in the prompt

            has_started_args = False  # Flag to see if the prompt has started to list arguments
            for word_idx, word in enumerate(split_text):  # iterate through all words
                try:
                    idx = None  # If the selected word is a subcommand, mark that by setting idx
                    for index, name in enumerate(tree_location.list_subcommand_names()):
                        if name == word:
                            idx = index
                    if word.startswith('-'):  # Mark that we have started parsing arguments if the selected word starts
                        # with '-'
                        has_started_args = True
                    if (word_idx != len(split_text) - 1 or word_before_cursor == '') \
                            and idx is None and not has_started_args:  # if (the word is not last or the word right before
                        # the curser is blank) and there is no index and we have not started parsing arguments, set
                        # completions to blank. This is to catch any unknown command that would have been in the prompt.
                        # For example, `aws foobar` would return no completions because foobar is not a command.
                        completions = []
                        break
                    if idx is not None:  # If an index was found
                        tree_location = tree_location.subcommands[
                            idx]  # Set the new tree location (aka current command in
                        # tree) to the new one that has been found
                        if tree_location.has_subcommands():  # If there are subcommands, list them
                            completions = tree_location.list_subcommand_names()
                        else:  # If there are no subcommands, suggest optional arguments
                            completions = []  # Reset completions because they are gonna be arguments now
                            for arg in tree_location.optional_arguments:  # Go through all arguments in the command and add
                                # the arguments allowed to the suggested completions. Arguments are disallowed if they are
                                # specified already. The exception to that is if the argument is a type that can be
                                # specified multiple times. No arguments are suggested if there is a death argument
                                # (one that does something completely different than what the command is supposed to do,
                                # and therefore kills all the other arguments. An example of this is "--help").
                                arg_specified = False  # Flag to see if an argument has been specified yet by the user
                                # in the prompt
                                for parts in split_text:
                                    if parts.startswith('-') and parts == arg.tag:
                                        arg_specified = True
                                if not arg_specified:  # If the argument hasn't been specified, add it to the suggested list
                                    #  and go to next argument
                                    completions.append(arg.tag)
                                    continue
                                if arg.type is arg.TYPE_ENUM.APPEND or arg.type is arg.TYPE_ENUM.APPEND_CONST or \
                                                arg.type is arg.TYPE_ENUM.COUNT:  # If the argument is an append or count type, add
                                    # it regardless of if it has been specified by the user already
                                    completions.append(arg.tag)
                                    continue
                                if arg.type is arg.TYPE_ENUM.HELP or arg.type is arg.TYPE_ENUM.VERSION:  # If a death
                                    # argument has been specified ("--help" or "--version"), then delete all suggested
                                    # completions and break the loop.
                                    completions = []
                                    break

                            last_full_arg = full_split_text[-1]  # Get the last fully specified argument in the list
                            if last_full_arg and last_full_arg.startswith(
                                    '-'):  # If there is a last argument and it is an
                                # argument (this _should_ always be the case), then change some suggestions
                                try:
                                    arg = tree_location.make_tag_to_args_dict()[
                                        last_full_arg]  # Get the argument object
                                    # from the tag
                                    if arg.type is arg.TYPE_ENUM.STORE or arg.type is arg.TYPE_ENUM.APPEND \
                                            or arg.type is arg.TYPE_ENUM.COUNT:  # If an argument is one where you manually
                                        # specify the value (most arguments, just not the death arguments or the constant
                                        # arguments)
                                        if arg.choices is not None:  # If the argument has specified choices, suggest those
                                            completions = arg.choices
                                        else:  # Otherwise, suggest nothing
                                            completions = []
                                except KeyError:  # Do nothing if the argument is wrong/unknown. Nothing in this case would
                                    # suggest the arguments for the command.
                                    pass
                except KeyError:  # If there is a key error somewhere, make the completions be empty
                    if completions is None:
                        completions = []

        completions.sort()  # Alphabetize the completions

        for completion in completions:  # Go through suggested completions
            if completion.startswith(word_before_cursor):  # If a suggested completion starts with the unfinished word
                # that is being written by the user right now, use it
                yield Completion(completion, -len(word_before_cursor))  # Return (yield) all completions with the
                # completion name and the start position of the completion

    def get_current_command(self, document):
        """
        Gets the current command that the user is in. For example, if the user enters `aws encrypt`, the command would
        be the AWS Encrypt command object. Does not matter if arguments are specified in the text. If the user enters
        `aws enc` (`enc` as in an unfinished command or an unknown subcommand), the command would be AWS. However, if
        the user enters an unknown top level command `foo`, for example, the command would be None.
        :param document: the object containing useful stuff like text
        :return: CommandPromptToolkit object with the current and selected command
        """
        all_text = document.text_before_cursor

        tree_location = self.command  # Tree location is the current selected command that is narrowed down to the exact
        #  command the user has typed in the prompt

        for word in all_text.split():  # Go through all words in the prompt and attempt to narrow down to the exact
            # command being used
            idx = None
            for index, name in enumerate(tree_location.list_subcommand_names()):
                if name == word:
                    idx = index
            if idx is not None:
                tree_location = tree_location.subcommands[idx]

        if tree_location == self.command:  # If there was no command that could be found and tree_location is still at
            # the top command, return None
            return None

        return tree_location

    def get_current_argument(self, document):
        """
        Gets the current argument that the user is in. For example, if the user enters `auth --password`, the argument
        would be the Auth Password argument object. If the user enters `auth --password --email`, the argument is Email.
        If the user enters `auth --password --ema` (`--ema` as in an unfinished parameter), the argument is None.
        :param document: the object containing useful stuff like text
        :return: ArgumentPromptToolkit object with the current and selected argument
        """
        all_text = document.text_before_cursor

        tree_location = self.command  # Tree location is the current selected command that is narrowed down to the exact
        #  command the user has typed in the prompt

        split_text = all_text.split()  # list of all values (commands, subcommands, arguments, etc.) separated by space
        full_split_text = split_text  # full_split_text is all values (see above for example) separated by space that
        # are complete.
        if not all_text.endswith(' ') and not split_text[-1].startswith('-'):  # If the last word is unfinished and the
            # last word is not an argument, shorten the full text by one. This is to keep the manpage suggestions for
            # arguments with values. For example, `aws encrypt --aws-tag foob` (with `foob` being unfinished for
            # `foobar`), the manpage would be "--aws-tag" the entire time.
            del full_split_text[-1]
        # The difference between these two is shown in this example:
        # In `aws encrypt --aws-tag foob` (with `foob` being unfinished for `foobar`), the result of split_text would
        # be `['aws', 'encrypt', '--aws-tag', 'foob']`, while the result of full_split_text would
        # be `['aws', 'encrypt', '--aws-tag']`

        for word in split_text:  # Go through all words in the prompt and attempt to narrow down to the exact
            # command being used
            idx = None
            for index, name in enumerate(tree_location.list_subcommand_names()):
                if name == word:
                    idx = index
            if idx is not None:
                tree_location = tree_location.subcommands[idx]

        if full_split_text and full_split_text[-1].startswith('-'):  # If the last full word exists and is an argument,
            # return the argument object the word/tag matched
            for arg in tree_location.optional_arguments:  # Go though each argument and match it to the word/tag
                if full_split_text[-1] == arg.tag:  # If the last word is equal to the argument tag, return it
                    return arg

        return None
