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
from pygments.token import Text
from math import ceil
from prompt_toolkit.layout.controls import UIControl, UIContent
from prompt_toolkit.layout.screen import Char
from pygments.token import Token


class Manpage(UIControl):
    """
    :type app: brkt_cli.shell.app.App
    :type height: int
    """
    def __init__(self, app, height=10):
        """
        The manpage widget to give the user info about the command/argument they are running
        :param app: the app that is running it
        :type app: brkt_cli.shell.app.App
        :param height: the height of the widget
        :type height: int
        """
        self.app = app
        self.height = height

    def preferred_height(self, cli, width, max_available_height, wrap_lines):
        """
        Overrides function that sends the preferred height of the manpage
        :param cli: the cli
        :type cli: prompt_toolkit.CommandLineInterface
        :param width: the width
        :type width: int
        :param max_available_height: the max height
        :type max_available_height: int
        :param wrap_lines: if wrapping lines
        :type wrap_lines: bool
        :return: the preferred height
        :rtype: int
        """
        return self.height

    def create_content(self, cli, width, height):
        """
        Creates the content of the manpage widget
        :param cli: the cli
        :type cli: prompt_toolkit.CommandLineInterface
        :param width: the width of the widget
        :type width: int
        :param height: the height of the widget
        :type height: int
        :return: the content of the widget
        :rtype: prompt_toolkit.layout.controls.UIContent
        """
        manpage_text = self.get_text(cli.current_buffer.document)  # Generate the text
        manpage_split_newline = manpage_text.split('\n')  # Split all newlines
        new_manpage_split = []  # If there are any lines that are longer than the width, make the widget wrap the lines
        for txt in manpage_split_newline:
            if len(txt) > width:
                for x in range(int(ceil(float(len(txt))/width))):
                    new_manpage_split.append(txt[width*x:width*(x+1)])
            else:
                new_manpage_split.append(txt)

        token_manpage = map(lambda val: [(Text, val)], new_manpage_split)  # Put the content in the correct format

        return UIContent(
            get_line=lambda i: token_manpage[i],
            line_count=len(token_manpage),  # The line count should match the lines in the text
            show_cursor=False,
            default_char=Char(' ', Token.Toolbar))

    def get_text(self, document):
        """
        The generator that generates the widget text
        :param document: the document of the cli prompt
        :type document: prompt_toolkit.document.Document
        :return: the text of the widget
        :rtype: unicode
        """
        text_before_cursor = document.text_before_cursor.strip()
        if document.text.strip() and text_before_cursor != '':  # If there is text in prompt
            arg = self.app.completer.get_current_argument(document)  # Get current argument (if there is one)
            if arg is not None:  # If there is a current argument, display the description
                manpage = unicode(arg.description)
            elif text_before_cursor.split()[-1].startswith('-'):  # While typing an argument, don't show any
                # manpage description
                manpage = u''
            else:  # If a command is in the prompt (and no argument), display the manpage of the command
                command = self.app.completer.get_current_command(document)
                if command is not None:
                    manpage = u''
                    manpage += command.description
                    manpage += u'\n\n' + command.usage
                else:  # If there is no valid command, clear manpage
                    manpage = u''
        else:  # If there is no text in prompt, clear manpage
            manpage = u''
        return manpage