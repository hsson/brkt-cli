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
from prompt_toolkit import Application, AbortAction, CommandLineInterface, filters
from prompt_toolkit.buffer import Buffer, AcceptAction
from prompt_toolkit.document import Document
from prompt_toolkit.enums import EditingMode
from prompt_toolkit.filters import IsDone, Always, RendererHeightIsKnown
from prompt_toolkit.key_binding.manager import KeyBindingManager
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import HSplit, ConditionalContainer, Window, FillControl, BufferControl, TokenListControl
from prompt_toolkit.layout.dimension import LayoutDimension
from prompt_toolkit.layout.screen import Char
from prompt_toolkit.shortcuts import create_prompt_layout, create_eventloop
from pygments.token import Token

from brkt_cli.shell.enum import enum
from brkt_cli.shell.inner_commands import exit_inner_command, manpage_inner_command, InnerCommandError, \
    help_inner_command


class App:
    """
    The app that controls the console UI and anything relating to the shell.
    :param completer: the completer to suggest words
    """
    MACHINE_COMMANDS = enum(UNKNOWN=0, EXIT=1)
    COMMAND_PREFIX = '/'
    INNER_COMMANDS = {
        COMMAND_PREFIX + 'exit': exit_inner_command,
        COMMAND_PREFIX + 'manpage': manpage_inner_command,
        COMMAND_PREFIX + 'help': help_inner_command,
    }

    def __init__(self, completer):
        self.completer = completer
        self.manpage = u''
        self.has_manpage = True
        self.key_manager = None
        self.dummy = False
        self._cli = self.make_cli_interface()

    def run(self):
        """
        Runs the app in a while True loop. The app can only be broken from an error or EXIT machine_command. It catches
        all inner commands and runs them. At the end of a command, it clears the manpage screen.
        """
        while True:
            try:
                ret = self._cli.run(reset_current_buffer=True)
            except (KeyboardInterrupt, EOFError):
                self._cli.eventloop.close()
                break
            else:
                if ret is self.MACHINE_COMMANDS.EXIT:
                    self._cli.eventloop.close()
                    break
                if ret.text.startswith(self.COMMAND_PREFIX):
                    try:
                        cmd = self.INNER_COMMANDS[ret.text.split()[0]]
                        mac_cmd = cmd.run_action(ret.text, self)
                        if mac_cmd == self.MACHINE_COMMANDS.EXIT:
                            self._cli.eventloop.close()
                            break
                    except KeyError:
                        print "Error: Unknown command."
                    except InnerCommandError as err:
                        print err.format_error()
                    continue
                self.manpage = u''
                self._cli.buffers['manpage'].reset(initial_document=Document(self.manpage, cursor_position=0))
                self._cli.request_redraw()

                if not self.dummy:
                    p = subprocess.Popen(sys.argv[0] + ' ' + ret.text, shell=True, env=os.environ.copy())
                    p.communicate()

    def get_bottom_toolbar_tokens(self, _):
        """
        Constructs the bottom toolbar
        :param _:
        :return: A list of all elements in the toolbar
        """
        ret = [
            (Token.Toolbar.Help, 'Press ctrl q to quit'),
            (Token.Toolbar.Separator, ' | '),
            (Token.Toolbar.Help, 'Manpage Window: ' + ('ON' if self.has_manpage else 'OFF')),
        ]
        if self.dummy:
            ret.extend([(Token.Toolbar.Separator, ' | '), (Token.Toolbar.Help, 'Dummy Mode: ON')])
        return ret

    def make_layout(self):
        """
        Constructs the layout of the CLI UI
        :return: The layout in horizontal sections
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
                filter=~IsDone() & filters.Condition(lambda _: self.has_manpage)
            ),  # A separator between the command prompt and the manpage view. This disappears when
            # self.has_manpage is False
            ConditionalContainer(
                content=Window(
                    content=BufferControl(
                        buffer_name='manpage',
                    ),
                    height=LayoutDimension(max=15),
                ),
                filter=~IsDone() & filters.Condition(lambda _: self.has_manpage),
            ),  # The manpage help display. This disappears when self.has_manpage is False
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

    def make_buffer(self, completer):
        """
        This function makes a buffer for the app to use
        :param completer: the completer to suggest words
        :return: the generated buffer
        """
        return Buffer(
            enable_history_search=True,  # Allows the user to search through command history via the up and down arrows
            completer=completer,  # The completer to suggest words to the user
            complete_while_typing=Always(),  # Always give suggestions while typing
            accept_action=AcceptAction.RETURN_DOCUMENT,  # Return the document (and the text) on enter/
            on_text_changed=self.on_text_changed  # If the text in the user prompt is changed, run this function
        )

    def on_text_changed(self, buff):
        """
        Called every time the user changes the text (via input, delete, etc.) in the prompt.
        It gets the manpage of the command in progress and writes it to the manpage buffer area
        :param buff: the buffer that is changed
        """
        document = buff.document
        if document.text.strip() and document.text_before_cursor != '':  # If there is text in prompt
            arg = self.completer.get_current_argument(document)  # Get current argument (if there is one)
            if arg is not None:  # If there is a current argument, display the description
                self.manpage = unicode(arg.description)
            elif document.text_before_cursor.split()[-1].startswith('-'):  # While typing an argument, don't show any
                # manpage description
                self.manpage = u''
            else:  # If a command is in the prompt (and no argument), display the manpage of the command
                command = self.completer.get_current_command(document)
                if command is not None:
                    self.manpage = u''
                    self.manpage += command.description
                    self.manpage += u'\n\n' + command.usage
                else:  # If there is no valid command, clear manpage
                    self.manpage = u''
        else:  # If there is no text in prompt, clear manpage
            self.manpage = u''

        # Update the manpage UI with the values
        self._cli.buffers['manpage'].reset(
            initial_document=Document(self.manpage, cursor_position=0))
        self._cli.request_redraw()

    def make_app(self, completer):
        """
        Makes the application needed for the App. Creates a KeyBindingManager that traps key commands and pipes them to
        functions.
        :param completer: the completer to suggest words
        :return: Application
        """
        self.key_manager = KeyBindingManager()

        @self.key_manager.registry.add_binding(Keys.ControlQ, eager=True)
        def exit_(event):
            """
            When ctrl q is pressed, return the EXIT machine_command to the cli.run() command.
            :param event:
            """
            event.cli.set_return_value(self.MACHINE_COMMANDS.EXIT)

        return Application(
            buffer=self.make_buffer(completer),
            buffers={
                'manpage': Buffer(read_only=True)
            },
            key_bindings_registry=self.key_manager.registry,
            on_abort=AbortAction.RETRY,
            layout=self.make_layout(),
            editing_mode=EditingMode.EMACS,
        )

    def make_cli_interface(self):
        """
        Makes the CLI interface needed for the App
        :return: CommandLineInterface
        """
        loop = create_eventloop()
        app = self.make_app(self.completer)

        return CommandLineInterface(application=app, eventloop=loop)
