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
from termcolor import colored


class InnerCommand:
    """
    The command type for commands in the shell itself (e.g. `/exit`)
    :param name: the name of the command without the identifier (in this case `/`) in front of it
    :param description: the description of the command
    :param action: the action to be run when the command is entered.
    """
    def __init__(self, name, description, usage, action):
        self.name = name
        self.description = description
        self.usage = usage
        self._action = action

    def run_action(self, cmd, app):
        """
        Run the action of the inner command
        :param cmd: the entire command string
        :param app: the app it is running from
        :return: the result of the action, which will be a machine_command or None
        """
        params = cmd.split()
        del params[0]
        return self._action(params, app)


class InnerCommandError(Exception):
    """
    An error that an inner command can throw.
    """
    def __init__(self, message):
        super(InnerCommandError, self).__init__(message)
        pass

    def format_error(self):
        """
        Formats the error to be displayed in the CLI
        :return: the formatted error
        """
        return 'Error: %s' % self.message


def exit_inner_command_func(_, app):
    """
    Run exit command
    :param _: command parameters
    :param app: the app it is running from
    :return: the exit machine_command
    """
    return app.MACHINE_COMMANDS.EXIT


def manpage_inner_command_func(params, app):
    """
    Modify the app.has_manpage field depending on the parameters. If there are no parameters, toggle the field. If a
    parameter is specified and is either 'true or 'false', set it to that. If it isn't, throw error
    :param params: command parameters
    :param app: the app it is running from
    :return: None
    :raise: InnerCommandError
    """
    if params and len(params) > 0:
        if params[0].lower() == 'true':
            app.has_manpage = True
        elif params[0].lower() == 'false':
            app.has_manpage = False
        else:
            raise InnerCommandError('Unknown option entered')
    else:
        app.has_manpage = not app.has_manpage


def help_inner_command_func(params, app):
    """
    Prints help for the inner commands
    :param params: command parameters
    :param app: the app it is running from
    :return: None
    """
    print colored('Brkt CLI Shell Inner Command Help', attrs=['bold'])
    for _, cmd in app.INNER_COMMANDS.iteritems():
        print cmd.name + '\t' + cmd.description
        print '\t' + app.COMMAND_PREFIX + cmd.usage

# Commands that are prebuilt for the CLI
exit_inner_command = InnerCommand('exit', 'Exits the shell.', 'exit', exit_inner_command_func)
manpage_inner_command = InnerCommand('manpage', 'Passing "true" will enable the manpage, while "false" will disable it.'
                                                ' Passing nothing will toggle it.', 'manpage [true | false]', manpage_inner_command_func)
help_inner_command = InnerCommand('help', 'Get help for inner commands', 'help', help_inner_command_func)