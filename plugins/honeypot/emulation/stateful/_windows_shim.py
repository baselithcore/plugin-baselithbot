"""Windows command shim mixin for StatefulEmulator."""

from core.observability.logging import get_logger

logger = get_logger(__name__)


class WindowsShimMixin:
    """Translates Windows shell commands to VFS operations."""

    def _process_windows_command(self, command: str) -> tuple[str, bool]:
        """Shim to handle Windows commands by translating to VFS."""
        cmd_parts = command.strip().split()
        if not cmd_parts:
            return "", True

        base_cmd = cmd_parts[0].lower()
        args = cmd_parts[1:]

        # Path normalizer
        def norm_path(p: str) -> str:
            p = p.replace("\\", "/")
            if p.lower().startswith("c:"):
                p = p[2:]
            return p

        if base_cmd == "dir":
            target = args[0] if args else "."
            path = norm_path(target)

            try:
                if not self.vfs.is_directory(path):
                    if self.vfs.is_file(path):
                        return (
                            f" Volume in drive C has no label.\n Directory of C:{path}\n\n1 File(s) 100 bytes\n",
                            True,
                        )
                    return "The system cannot find the file specified.", True

                abs_path = self.vfs._normalize_path(path)
                if abs_path not in self.vfs._fs:
                    return "File Not Found", True

                entries = self.vfs._fs[abs_path]

                from datetime import datetime

                now_str = datetime.now().strftime("%m/%d/%Y  %I:%M %p")

                # Map internal VFS path to Windows display path
                win_path = abs_path.replace("/", "\\")
                if win_path.startswith("\\home"):
                    win_path = win_path.replace("\\home", "\\Users", 1)

                if not win_path.startswith("\\"):
                    win_path = "\\" + win_path

                output = f" Volume in drive C has no label.\n Volume Serial Number is A1B2-C3D4\n\n Directory of C:{win_path}\n\n"

                file_count = 0
                dir_count = 0
                byte_count = 0

                list_entries = []
                list_entries.append((now_str, "<DIR>", "", "."))
                list_entries.append((now_str, "<DIR>", "", ".."))
                dir_count += 2

                for name, vfile in entries.items():
                    is_dir = vfile.is_directory
                    size_str = f"{vfile.size:,}" if not is_dir else ""
                    type_str = "<DIR>" if is_dir else "     "
                    list_entries.append((now_str, type_str, size_str, name))
                    if is_dir:
                        dir_count += 1
                    else:
                        file_count += 1
                        byte_count += vfile.size

                for d, t, s, n in list_entries:
                    output += f"{d}    {t} {s:>14} {n}\n"

                output += (
                    f"              {file_count} File(s)    {byte_count:,} bytes\n"
                )
                output += (
                    f"              {dir_count} Dir(s)   50,234,232,112 bytes free\n"
                )
                return output, True
            except Exception:
                return "File Not Found", True

        elif base_cmd == "whoami":
            return f"{self.session.hostname}\\{self.session.username}", True

        elif base_cmd == "systeminfo":
            return (
                f"Host Name:                 {self.session.hostname.upper()}\nOS Name:                   {self.profile.os_version}\nOS Version:                10.0.20348 N/A Build 20348\nOS Manufacturer:           Microsoft Corporation\nSystem Type:               x64-based PC\nProcessor(s):              1 Processor(s) Installed.\n",
                True,
            )

        elif base_cmd == "cd":
            if not args:
                cwd = self.session.cwd.replace("/", "\\")
                if not cwd.startswith("C:"):
                    cwd = "C:" + cwd
                return cwd, True

            target = norm_path(args[0])
            try:
                success, err = self.vfs.cd(target)
                if success:
                    self.session.cwd = self.vfs.pwd()
                    return "", True
                else:
                    return "The system cannot find the path specified.", True
            except Exception:
                return "The system cannot find the path specified.", True

        elif base_cmd == "type":
            if not args:
                return "", True
            target = norm_path(args[0])
            success, content = self.vfs.cat(target)
            if success:
                return content, True
            return "The system cannot find the file specified.", True

        return "", False
