"""Text processing command implementations."""

from .base import CommandMixin


class TextProcessingCommands(CommandMixin):
    """Text processing commands (grep, head, tail, wc, echo)."""

    def _cmd_echo(self, args: list) -> str:
        return " ".join(args)

    def _cmd_head(self, args: list) -> str:
        if not args or args[-1].startswith("-"):
            return "head: missing file operand"

        path = args[-1]
        n = 10

        for i, arg in enumerate(args):
            if arg == "-n" and i + 1 < len(args):
                try:
                    n = int(args[i + 1])
                except ValueError:
                    pass

        success, content = self.vfs.cat(path)
        if not success:
            return content

        lines = content.split("\n")[:n]
        return "\n".join(lines)

    def _cmd_tail(self, args: list) -> str:
        if not args or args[-1].startswith("-"):
            return "tail: missing file operand"

        path = args[-1]
        n = 10

        for i, arg in enumerate(args):
            if arg == "-n" and i + 1 < len(args):
                try:
                    n = int(args[i + 1])
                except ValueError:
                    pass

        success, content = self.vfs.cat(path)
        if not success:
            return content

        lines = content.split("\n")[-n:]
        return "\n".join(lines)

    def _cmd_grep(self, args: list) -> str:
        if len(args) < 2:
            return "grep: missing pattern or file"

        pattern = args[0]
        path = args[1]

        success, content = self.vfs.cat(path)
        if not success:
            return content

        # Simple pattern matching
        lines = [line for line in content.split("\n") if pattern in line]
        return "\n".join(lines)

    def _cmd_wc(self, args: list) -> str:
        if not args:
            return "wc: missing file operand"

        path = args[-1]

        success, content = self.vfs.cat(path)
        if not success:
            return content

        lines = len(content.split("\n"))
        words = len(content.split())
        chars = len(content)

        return f"{lines} {words} {chars} {path}"
