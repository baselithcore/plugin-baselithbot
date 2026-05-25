"""Scripting language command implementations."""

from .base import CommandMixin


class ScriptingCommands(CommandMixin):
    """Scripting language interpreters (python, perl, bash)."""

    def _cmd_python(self, args: list) -> str:
        """Simulate python interpreter."""
        if "--version" in args or "-V" in args:
            return "Python 3.8.10"

        if "-c" in args:
            # One-liner execution - return empty (success)
            return ""

        if not args:
            # Interactive mode prompt
            return """Python 3.8.10 (default, Nov 14 2022, 12:59:47) 
[GCC 9.4.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> """

        # Script execution
        script = args[-1]
        if not self.vfs.exists(script):
            return f"python: can't open file '{script}': [Errno 2] No such file or directory"

        return ""

    def _cmd_perl(self, args: list) -> str:
        """Simulate perl interpreter."""
        if "-v" in args or "--version" in args:
            return """This is perl 5, version 30, subversion 0 (v5.30.0) built for x86_64-linux-gnu-thread-multi

Copyright 1987-2019, Larry Wall

Perl may be copied only under the terms of either the Artistic License or the
GNU General Public License, which may be found in the Perl 5 source kit."""

        if "-e" in args:
            # One-liner execution - silent success
            return ""

        if not args:
            return ""

        # Script execution
        script = args[-1]
        if not self.vfs.exists(script):
            return f'Can\'t open perl script "{script}": No such file or directory'

        return ""

    def _cmd_bash(self, args: list) -> str:
        """Execute bash -c command."""
        if "-c" in args:
            # Need access to process_command from CommandProcessor
            # This will be bound dynamically in processor.py
            idx = args.index("-c")
            if idx + 1 < len(args):
                cmd = args[idx + 1]
                # Access parent processor's process_command
                if hasattr(self, "_processor"):
                    return self._processor.process_command(cmd)  # type: ignore
                return ""

        return ""  # Nested shell not supported
