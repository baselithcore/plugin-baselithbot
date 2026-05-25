"""Filesystem command implementations."""

from .base import CommandMixin


class FilesystemCommands(CommandMixin):
    """Filesystem-related commands (ls, cd, cat, touch, mkdir, rm, etc)."""

    def _cmd_pwd(self, _args: list) -> str:
        return self.vfs.pwd()

    def _cmd_cd(self, args: list) -> str:
        path = args[0] if args else ""
        success, error = self.vfs.cd(path)
        return error if not success else ""

    def _cmd_ls(self, args: list) -> str:
        all_files = "-a" in args or "-la" in args or "-al" in args
        long_format = "-l" in args or "-la" in args or "-al" in args

        # Get path (last non-option argument)
        path = ""
        for arg in args:
            if not arg.startswith("-"):
                path = arg
                break

        success, output = self.vfs.ls(
            path, all_files=all_files, long_format=long_format
        )
        return output

    def _cmd_cat(self, args: list) -> str:
        if not args:
            return "cat: missing operand"

        outputs = []
        for path in args:
            success, output = self.vfs.cat(path)
            if not success:
                outputs.append(output)
            else:
                outputs.append(output)

        return "\n".join(outputs)

    def _cmd_touch(self, args: list) -> str:
        if not args:
            return "touch: missing file operand"

        for path in args:
            success, error = self.vfs.touch(path)
            if not success:
                return error

        return ""

    def _cmd_mkdir(self, args: list) -> str:
        if not args:
            return "mkdir: missing operand"

        for path in args:
            if path.startswith("-"):
                continue  # Skip options like -p
            success, error = self.vfs.mkdir(path)
            if not success:
                return error

        return ""

    def _cmd_rm(self, args: list) -> str:
        if not args:
            return "rm: missing operand"

        recursive = "-r" in args or "-rf" in args or "-fr" in args
        force = "-f" in args or "-rf" in args or "-fr" in args

        paths = [arg for arg in args if not arg.startswith("-")]

        for path in paths:
            success, error = self.vfs.rm(path, recursive=recursive, force=force)
            if not success:
                return error

        return ""

    def _cmd_rmdir(self, args: list) -> str:
        if not args:
            return "rmdir: missing operand"

        for path in args:
            # rmdir only removes empty directories
            success, error = self.vfs.rm(path, recursive=False)
            if not success:
                return error

        return ""

    def _cmd_cp(self, args: list) -> str:
        return "cp: operation not yet supported"

    def _cmd_mv(self, args: list) -> str:
        return "mv: operation not yet supported"

    def _cmd_chmod(self, args: list) -> str:
        if len(args) < 2:
            return "chmod: missing operand"

        permissions = args[0]
        path = args[1]

        success, error = self.vfs.chmod(permissions, path)
        return error if not success else ""

    def _cmd_chown(self, args: list) -> str:
        if len(args) < 2:
            return "chown: missing operand"

        owner = args[0]
        path = args[1]

        success, error = self.vfs.chown(owner, path)
        return error if not success else ""

    def _cmd_find(self, args: list) -> str:
        path = "."
        name_pattern = "*"

        # Simple parsing
        if args:
            if not args[0].startswith("-"):
                path = args[0]

        # Look for -name pattern
        if "-name" in args:
            idx = args.index("-name")
            if idx + 1 < len(args):
                name_pattern = args[idx + 1]

        success, output = self.vfs.find(path, name_pattern)
        return output
