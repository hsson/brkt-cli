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
import os
import sys

import subprocess
from argparse import Namespace

import pickle
from prompt_toolkit import Application, AbortAction, CommandLineInterface, filters
from prompt_toolkit.buffer import Buffer, AcceptAction
from prompt_toolkit.document import Document
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters import IsDone, Always, RendererHeightIsKnown
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding.manager import KeyBindingManager
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import HSplit, ConditionalContainer, Window, FillControl, TokenListControl
from prompt_toolkit.layout.dimension import LayoutDimension
from prompt_toolkit.layout.screen import Char
from prompt_toolkit.shortcuts import create_prompt_layout, create_eventloop
from pygments.token import Token

from brkt_cli.shell.enum import Enum
from brkt_cli.shell.get_set_inner_commmands import set_inner_command, get_inner_command, del_inner_command
from brkt_cli.shell.inner_commands import exit_inner_command, InnerCommandError, \
    help_inner_command, dev_inner_command
from brkt_cli.shell.manpage import Manpage
from brkt_cli.shell.save_command import alias_inner_command, get_alias_inner_command, unalias_inner_command
from brkt_cli.shell.settings import Setting, setting_inner_command, bool_parse_value, bool_validate_change


class App(object):
    """
    :type COMMAND_PREFIX: unicode
    :type completer: brkt_cli.shell.completer.ShellCompleter
    :type cmd: brkt_cli.shell.raw_commands.CommandPromptToolkit
    :type _has_manpage: bool
    :type key_manager: prompt_toolkit.key_binding.manager.KeyBindingManager
    :type dummy: bool
    :type set_args: dict[unicode, dict[unicode, Any]]
    :type manual_args: dict[unicode, dict[unicode, ((Any) -> None, () -> None)]]
    :type saved_commands: dict[unicode, unicode]
    :type _vi_mode: bool
    :type mouse_support: bool
    :type dev_mode: bool
    :type inner_commands: dict[unicode, brkt_cli.shell.inner_commands.InnerCommand]
    :type _cli: prompt_toolkit.CommandLineInterface
    """

    class MachineCommands(Enum):
        """
        An enumeration of the machine commands that are returned after a inner command
        :type Unknown: int
        :type Exit: int
        """
        Unknown, Exit = range(2)

    COMMAND_PREFIX = u'/'

    def __init__(self, completer, cmd, mouse_support=False):
        """
        The app that controls the console UI and anything relating to the shell.
        :param completer: the completer to suggest words
        :type completer: brkt_cli.shell.completer.ShellCompleter
        :param cmd: the top command of the app.
        :type cmd: brkt_cli.shell.raw_commands.CommandPromptToolkit
        """
        self.completer = completer
        self.completer.app = self
        self.cmd = cmd
        self._has_manpage = True
        self.key_manager = None
        self.dummy = False
        self.set_args = {}
        self.saved_commands = {}
        self._vi_mode = False
        self.mouse_support = mouse_support
        self.dev_mode = False
        self.inner_commands = {
            self.COMMAND_PREFIX + u'exit': exit_inner_command,
            self.COMMAND_PREFIX + u'help': help_inner_command,
            self.COMMAND_PREFIX + u'set': set_inner_command,
            self.COMMAND_PREFIX + u'get': get_inner_command,
            self.COMMAND_PREFIX + u'del': del_inner_command,
            self.COMMAND_PREFIX + u'alias': alias_inner_command,
            self.COMMAND_PREFIX + u'get_alias': get_alias_inner_command,
            self.COMMAND_PREFIX + u'unalias': unalias_inner_command,
            self.COMMAND_PREFIX + u'setting': setting_inner_command,
        }
        if self.dev_mode:
            self.inner_commands[self.COMMAND_PREFIX + u'dev'] = dev_inner_command

        def token_on_changed(val):
            token_list = []
            for path in self.cmd.get_all_paths():
                got_cmd = self.cmd.get_subcommand_from_path(path)
                if got_cmd is None or got_cmd.has_subcommands() is True:
                    continue
                token_list.extend(map(lambda x: (path, x.get_name()),
                                      filter(lambda x: x.type is not x.Type.Help and x.type is not x.Type.Version and
                                             x.get_name() == 'token' and (x.dev is False or self.dev_mode is True),
                                             got_cmd.optional_arguments + got_cmd.positionals))
                                  )  # Get All arguments that are not help or version and get their names and add them
                # to their command paths. This creates bunch of full paths
            for cmd_path, token_arg in token_list:
                if cmd_path not in self.set_args:
                    self.set_args[cmd_path] = {}
                self.set_args[cmd_path][token_arg] = val

        def token_on_delete():
            for cmd_path, val in self.set_args.iteritems():
                for k in val.keys():
                    if k == 'token':
                        del self.set_args[cmd_path][k]

        self.manual_args = {
            'app': {
                'token': (token_on_changed, token_on_delete),
            }
        }

        def manpage_on_changed(val):
            self._has_manpage = val

        def editing_mode_on_changed(val):
            if val == 'vi':
                self._vi_mode = True
                self._cli.application.editing_mode = EditingMode.VI
                self._cli.editing_mode = EditingMode.VI
            else:
                self._vi_mode = False
                self._cli.application.editing_mode = EditingMode.EMACS
                self._cli.editing_mode = EditingMode.EMACS

        self.settings = {
            'manpage': Setting('manpage', self._has_manpage, on_changed=manpage_on_changed,
                               str_acceptable_values=['true', 'false'],
                               parse_value=bool_parse_value,
                               validate_change=bool_validate_change,
                               description='If "true" the manpage will be enabled so you can see command descriptions'),
            'editing_mode': Setting('editing_mode', 'vi' if self._vi_mode else 'emacs',
                                    on_changed=editing_mode_on_changed,
                                    str_acceptable_values=['vi', 'emacs'],
                                    description='The editing mode type for the prompt'),
        }

        app_info = self.get_app_info()
        if app_info is not None:
            self.set_args = app_info['set_args']
            self.saved_commands = app_info['saved_commands']

        self._cli = self.make_cli_interface()

    def run(self):
        """
        Runs the app in a while True loop. The app can only be broken from an error or EXIT machine_command. It catches
        all inner commands and runs them. At the end of a command, it clears the manpage screen.
        """
        while True:
            try:
                ret_doc = self._cli.run(reset_current_buffer=True)
            except (KeyboardInterrupt, EOFError):
                self.run_shutdown()
                self._cli.eventloop.close()
                break
            else:
                if ret_doc is self.MachineCommands.Exit:
                    self.run_shutdown()
                    self._cli.eventloop.close()
                    break
                if ret_doc.text == '':
                    continue

                try:
                    cmd_text = self.parse_command(ret_doc).replace('\\$', '$').replace('\\(', '(').replace('\\)', ')')
                except InnerCommandError as err:
                    print err.format_error()
                    continue

                if cmd_text.startswith(self.COMMAND_PREFIX):
                    try:
                        inner_cmd = self.inner_commands[ret_doc.text.split()[0]]
                    except KeyError:
                        print UnknownCommandError().format_error()
                    else:
                        try:
                            machine_cmd = inner_cmd.run_action(cmd_text, self)
                            if machine_cmd == self.MachineCommands.Exit:
                                self.run_shutdown()
                                self._cli.eventloop.close()
                                break
                        except InnerCommandError as err:
                            print err.format_error()
                        except AssertionError as err:
                            print InnerCommandError.format(err.message)
                        except:
                            exec_info = sys.exc_info()
                            print InnerCommandError.format(
                                "unknown error - %s\n%s\n%s" % (exec_info[0], exec_info[1], exec_info[2]))
                    continue

                if self.dummy:
                    print sys.argv[0] + ' ' + cmd_text
                else:
                    p = subprocess.Popen(sys.argv[0] + ' ' + cmd_text, shell=True, env=os.environ.copy())
                    p.communicate()

    def run_shutdown(self):
        app_info = {
            'set_args': self.set_args,
            'saved_commands': self.saved_commands,
        }
        with open('.brkt_shell_info.pkl', 'wb') as f:
            pickle.dump(app_info, f, pickle.HIGHEST_PROTOCOL)

    def parse_command(self, ret_doc):
        """
        Parses and formats a raw command. This is the function that makes commands use aliases and embedded commands.
        It also is responsible for replacing arguments with set arguments.
        :param ret_doc: the document gotten from the returned command
        :type ret_doc: prompt_toolkit.document.Document
        :return: the parsed command
        :rtype: unicode
        :raises: InnerCommandError
        :raises: UnknownCommandError
        """
        cmd_text = ret_doc.text
        embedded_commands = self.parse_embedded_command_text(cmd_text)  # Parse embedded commands

        if len(embedded_commands) > 0:
            cmd_text = self._parse_embedded_commands(cmd_text, embedded_commands)

        if cmd_text.startswith(self.COMMAND_PREFIX):  # If it is an inner command
            return cmd_text
        elif cmd_text in self.saved_commands:  # If it is a saved command, run again with the saved command
            return self.parse_command(Document(text=self.saved_commands[cmd_text]))
        else:  # If it is a command
            cmd_text_doc = Document(cmd_text)  # Make another document with the new parsed command
            command = self.completer.get_current_command(cmd_text_doc, text_done=True)
            if command is None:  # If command is none, error
                raise UnknownCommandError()

            if command.path in self.set_args:  # if there is the possibility of set args in this command, parse it
                cmd_text = self._parse_set_args_commands(cmd_text_doc, command)
            return cmd_text

    def _parse_embedded_commands(self, cmd_text, embedded_commands):
        """
        Parses embedded commands (`$(COMMAND)`) from a text.
        :param cmd_text: the raw command text with raw embedded command
        :type cmd_text: unicode
        :param embedded_commands: the list of embedded commands
        :type embedded_commands: list[(int, int)]
        :return: the command text with the embedded commands replaced with their outputs
        :rtype: unicode
        :raises: InnerCommandError
        """
        mod_len = 0  # The modified length index of the text. This is because the output of an embedded command could 
        # be smaller or larger than the raw embedded command. For example, `$(foo)` is smaller than `helloworld`
        for emb_cmd in embedded_commands:
            adj_cmd_start = emb_cmd[0] - mod_len  # Adjusted command indexes based on the modified length
            adj_cmd_end = emb_cmd[1] - mod_len
            in_text = cmd_text[adj_cmd_start + 2:adj_cmd_end]  # The text inside of the `$()`
            try:  # Try to parse the inner command
                parsed_emb_cmd = self.parse_command(Document(text=in_text))
            except UnknownCommandError:  # If you find an unknown command error, make it a bit more verbose
                raise InnerCommandError('Unknown embedded command: $(%s)' % cmd_text[adj_cmd_start + 2:adj_cmd_end])

            if self.dummy:  # If dummy mode enabled, don't acutually run the command
                new_text = sys.argv[0] + ' ' + parsed_emb_cmd
            else:
                print 'RUN: "' + sys.argv[0] + ' ' + parsed_emb_cmd + '"'
                p = subprocess.Popen(sys.argv[0] + ' ' + parsed_emb_cmd, shell=False, env=os.environ.copy(),
                                     stdout=subprocess.PIPE)  # Run the command and get the output
                out, err = p.communicate()
                if err is not None:
                    raise InnerCommandError(
                        'Could not run embedded command: $(%s)' % cmd_text[adj_cmd_start + 2:adj_cmd_end])
                new_text = out

            cmd_text = cmd_text[:adj_cmd_start] + new_text + cmd_text[adj_cmd_end + 1:]  # Replace the `$()` in the
            # command text with the output of the command
            cmd_len = emb_cmd[1] - emb_cmd[0] + 1
            mod_len += cmd_len - len(new_text)  # Adjust the modified length index
        return cmd_text

    def _parse_set_args_commands(self, doc, command):
        """
        Parses the command and builds the set arguments into the command. Manually specified arguments trump overridden
        arguments (set_args) and overridden arguments trump default arguments.
        :param doc: the document with the raw text. Usually manually created for this function to parse.
        :type doc: prompt_toolkit.document.Document
        :param command: the command of the text
        :type command: brkt_cli.shell.raw_commands.CommandPromptToolkit
        :return: the parsed text
        :rtype: unicode
        """
        args_text = doc.text[self.completer.get_current_command_location(doc)[1]:].strip()  # Get the arguments part of
        # the text
        try:  # Try to parse the manually specified arguments via the actual raw argparse function
            existing_args = command.parse_args(args_text.split())
        except:
            existing_args = Namespace()

        set_args_dict = self.set_args[command.path]  # Get the set arguments from the app
        positional_idx = 0  # Count the number of positional (required too) arguments there are in a argparse command
        final_args = []
        final_arg_texts = []
        for arg in command.optional_arguments + command.positionals:  # Go through every argument in a command that is
            # not help or version or dev mode when dev mode is off
            if arg.type == arg.Type.Help or arg.type == arg.Type.Version:
                continue

            if arg.dev is True and self.dev_mode is False:
                continue

            new_arg = {
                'positional': None,
                'arg': arg,
                'value': None,
                'specified': False,
            }

            if arg.__class__.__name__ == 'PositionalArgumentPromptToolkit':  # If positional, mark its place
                new_arg['positional'] = positional_idx
                positional_idx += 1

            if hasattr(existing_args, arg.dest):  # If the argument is manually specified
                spec_arg_val = getattr(existing_args, arg.dest)
                if arg.default == spec_arg_val and spec_arg_val is not None:  # If the default is the specified
                    # argument value. In positionals, we don't know if this is the user specifying the value or the
                    # parser is. Ideally, the user would trump the override (set_args) and the override would trump
                    # the parser
                    if new_arg['positional'] is None:  # If the argument is an optional argument, look for the tag in
                        # the text. If the tag is found, mark it as specified, trumping the override
                        new_arg['specified'] = arg.tag in args_text
                    else:  # If the argument is a positional, look for the value in the text. This is not the most
                        # ideal way to do it, but it is the only way
                        new_arg['specified'] = spec_arg_val in args_text
                else:
                    new_arg['specified'] = True

                new_arg['value'] = spec_arg_val  # Set the value to the manual value
                if arg.type == arg.Type.AppendConst and new_arg['value'] is not None:  # If the argument type is
                    # AppendConst, set the value to be either true or false, depending on if the flag was specified
                    new_arg['value'] = arg.raw.const in new_arg['value']
                elif arg.type == arg.Type.StoreFalse and new_arg['value'] is not None:  # If the argument type is
                    # StoreFalse, it has been specified and therefore, set the value to True
                    new_arg['value'] = True
            if arg.get_name() in set_args_dict and (not (
                        hasattr(existing_args, arg.dest) and getattr(existing_args, arg.dest) is not None) or not
                        new_arg['specified']):  # If the value is in the overrides (set_args) and not already
                # specified manually, set the value
                new_arg['value'] = set_args_dict[arg.get_name()]
                new_arg['specified'] = True

            if new_arg['value'] is not None and new_arg['specified']:  # Add all specified arguments with values
                final_args.append(new_arg)

        for final_opt_arg in filter(lambda x: x['positional'] is None, final_args):  # Go through each specified
            # optional argument and add it to the new command in its own way
            arg = final_opt_arg['arg']
            if arg.type == arg.Type.Store:  # Adds the tag and value: `{tag} {value}`
                final_arg_texts.append(arg.tag + ' ' + str(final_opt_arg['value']))
            elif arg.type == arg.Type.StoreConst and final_opt_arg['value'] is not None:
                final_arg_texts.append(arg.tag)  # Adds the tag if the value is not none: `{tag}`
            elif arg.type == arg.Type.StoreFalse and final_opt_arg['value'] is True:
                final_arg_texts.append(arg.tag)  # Adds the tag if the value passed says it can be specified: `{tag}`
            elif arg.type == arg.Type.StoreTrue and final_opt_arg['value'] is True:
                final_arg_texts.append(arg.tag)  # Adds the tag if the value passed says it can be specified: `{tag}`
            elif arg.type == arg.Type.Append:  # Adds the tag and value multiple times:
                # `{tag} {value1} {tag} {value2}...`
                final_arg_texts.append(
                    ' '.join(map(lambda val: arg.tag + ' ' + val, final_opt_arg['value'])))
            elif arg.type == arg.Type.Count:  # Adds the tag multiple times: `{tag} {tag}...`
                final_arg_texts.append(' '.join([arg.tag] * final_opt_arg['value']))
            elif arg.type == arg.Type.AppendConst and final_opt_arg['value'] is True:
                final_arg_texts.append(arg.tag)  # Adds the tag if the value passed says it can be specified: `{tag}`

        final_arg_texts.extend(map(lambda x: x['value'],
                                   sorted(filter(lambda x: x['positional'] is not None, final_args),
                                          key=lambda x: x['positional'])))  # Add positionals in order

        return doc.text[:self.completer.get_current_command_location(doc)[1]] + ' ' + ' '.join(
            final_arg_texts)

    @staticmethod
    def parse_embedded_command_text(text):
        """
        Parses embedded commands (`foo $(embedded) bar`) and returns the locations of them.
        :param text: the text to parse
        :type text: unicode
        :return: a list of embedded command start and end indexes
        :rtype: list[(int, int)]
        :raises: Exception
        """
        recording_depth = 0
        recording_start_idx = None
        embedded_commands = []
        for idx, letter in enumerate(text):
            next_letter = text[idx + 1] if len(text) > idx + 1 else None
            prev_letter = text[idx - 1] if idx != 0 else None
            if letter == '$' and next_letter == '(' and prev_letter != '\\':
                if recording_depth == 0:
                    recording_start_idx = idx
                    recording_depth = recording_depth + 1
                else:
                    recording_depth = recording_depth + 1
            elif letter == ')' and prev_letter != '\\':
                if recording_depth == 1:
                    embedded_commands.append((recording_start_idx, idx))
                    recording_start_idx = None
                    recording_depth = 0
                else:
                    recording_depth = recording_depth - 1

        if recording_depth != 0:
            raise Exception('Parentheses do not match and close')

        return embedded_commands

    def get_app_info(self):
        try:
            with open('.brkt_shell_info.pkl', 'rb') as f:
                return pickle.load(f)
        except IOError:
            return None

    def get_bottom_toolbar_tokens(self, _):
        """
        Constructs the bottom toolbar
        :param _:
        :return: A list of all elements in the toolbar
        :rtype: list[(pygments.token._TokenType, unicode)]
        """
        ret = [
            (Token.Toolbar.Help, 'Press ctrl q to quit'),
            (Token.Toolbar.Separator, ' | '),
            (Token.Toolbar.Help, 'Manpage Window: ' + ('ON' if self._has_manpage else 'OFF')),
            (Token.Toolbar.Separator, ' | '),
            (Token.Toolbar.Help, 'Editing Mode: ' + ('VI' if self._vi_mode else 'Emacs')),
        ]
        if self.dev_mode:
            ret.extend([(Token.Toolbar.Separator, ' | '), (Token.Toolbar.Help, 'Dev Mode: ON')])
        if self.dummy:
            ret.extend([(Token.Toolbar.Separator, ' | '), (Token.Toolbar.Help, 'Dummy Mode: ON')])
        return ret

    def make_layout(self):
        """
        Constructs the layout of the CLI UI
        :return: The layout in horizontal sections
        :rtype: prompt_toolkit.layout.HSplit
        """
        return HSplit([
            create_prompt_layout(
                message=u'brkt> ',
                reserve_space_for_menu=8,
                wrap_lines=True,

            ),  # The command prompt
            ConditionalContainer(
                content=Window(height=LayoutDimension.exact(1),
                               content=FillControl(u'\u2500',
                                                   token=Token.Separator)),
                filter=~IsDone() & filters.Condition(
                    lambda _: self._has_manpage and self._cli.current_buffer.document.text != ''),
            ),  # A separator between the command prompt and the manpage view. This disappears when
            # self._has_manpage is False
            ConditionalContainer(
                content=Window(
                    content=Manpage(self),
                    height=LayoutDimension(max=15),
                ),
                filter=~IsDone() & filters.Condition(
                    lambda _: self._has_manpage and self._cli.current_buffer.document.text != ''),
            ),
            ConditionalContainer(
                content=Window(
                    TokenListControl(
                        self.get_bottom_toolbar_tokens,
                        default_char=Char(' ', Token.Toolbar)
                    ),
                    height=LayoutDimension.exact(1)
                ),
                filter=~IsDone() & RendererHeightIsKnown()
            )  # The bottom toolbar, which displays useful info to the user
        ])

    @staticmethod
    def make_buffer(completer):
        """
        This function makes a buffer for the app to use
        :param completer: the completer to suggest words
        :type completer: prompt_toolkit.completion.Completer
        :return: the generated buffer
        :rtype: prompt_toolkit.buffer.Buffer
        """
        return Buffer(
            enable_history_search=True,  # Allows the user to search through command history via the up and down arrows
            completer=completer,  # The completer to suggest words to the user
            complete_while_typing=Always(),  # Always give suggestions while typing
            accept_action=AcceptAction.RETURN_DOCUMENT,  # Return the document (and the text) on enter
            history=FileHistory('.brkt_cli_history')
        )

    def make_app(self, completer):
        """
        Makes the application needed for the App. Creates a KeyBindingManager that traps key commands and pipes them to
        functions.
        :param completer: the completer to suggest words
        :type completer: prompt_toolkit.completion.Completer
        :return: Application
        :rtype: prompt_toolkit.Application
        """
        self.key_manager = KeyBindingManager()

        @self.key_manager.registry.add_binding(Keys.ControlQ, eager=True)
        @self.key_manager.registry.add_binding(Keys.ControlD, eager=True)
        def exit_(event):
            """
            When ctrl q or ctrl d is pressed, return the EXIT machine_command to the cli.run() command.
            :param event:
            """
            event.cli.set_return_value(self.MachineCommands.Exit)

        return Application(
            buffer=self.make_buffer(completer),
            key_bindings_registry=self.key_manager.registry,
            on_abort=AbortAction.RETRY,
            layout=self.make_layout(),
            editing_mode=EditingMode.VI if self._vi_mode else EditingMode.EMACS,
            mouse_support=self.mouse_support,
        )

    def make_cli_interface(self):
        """
        Makes the CLI interface needed for the App
        :return: command line interface
        :rtype: prompt_toolkit.CommandLineInterface
        """
        loop = create_eventloop()
        app = self.make_app(self.completer)

        return CommandLineInterface(application=app, eventloop=loop)


class UnknownCommandError(InnerCommandError):
    def __init__(self):
        super(UnknownCommandError, self).__init__('Unknown command')
