"""Core Virtual Filesystem implementation."""

import fnmatch
from datetime import datetime
from typing import Dict

from .models import VirtualFile
from .path_utils import PathUtilsMixin
from .initialization import FilesystemInitializer


class VirtualFilesystem(PathUtilsMixin):
    """In-memory filesystem simulation with realistic structure."""

    def __init__(self, username: str = "admin", hostname: str = "ubuntu-server"):
        """Initialize virtual filesystem with realistic structure.

        Args:
            username: Username for the filesystem
            hostname: System hostname
        """
        self.username = username
        self.hostname = hostname
        self.current_dir = f"/home/{username}"
        self._fs: Dict[str, Dict[str, VirtualFile]] = {}

        # Initialize with realistic directory structure
        initializer = FilesystemInitializer(username, hostname)
        initializer.initialize(self._create_dir, self._create_file)

    def _create_dir(self, path: str) -> None:
        """Internal method to create directory.

        Args:
            path: Directory path to create
        """
        path = self._normalize_path(path)
        if path not in self._fs:
            self._fs[path] = {}

            # Create directory entry in parent
            parent = self._get_parent_path(path)
            filename = self._get_filename(path)

            if parent != path and parent in self._fs:
                self._fs[parent][filename] = VirtualFile(
                    name=filename, is_directory=True, permissions="rwxr-xr-x"
                )

    def _create_file(
        self,
        path: str,
        content: str = "",
        permissions: str = "rw-r--r--",
        owner: str = "admin",
        is_executable: bool = False,
    ) -> None:
        """Internal method to create file.

        Args:
            path: File path
            content: File content
            permissions: File permissions
            owner: File owner
            is_executable: Whether file is executable
        """
        path = self._normalize_path(path)
        parent = self._get_parent_path(path)
        filename = self._get_filename(path)

        # Ensure parent directory exists
        if parent not in self._fs:
            self._create_dir(parent)

        # Create file entry
        vfile = VirtualFile(
            name=filename,
            content=content,
            permissions=permissions,
            owner=owner,
            is_directory=False,
            is_executable=is_executable,
        )

        self._fs[parent][filename] = vfile

    def exists(self, path: str) -> bool:
        """Check if path exists.

        Args:
            path: Path to check

        Returns:
            True if path exists
        """
        path = self._normalize_path(path)

        # Check if it's a directory
        if path in self._fs:
            return True

        # Check if it's a file
        parent = self._get_parent_path(path)
        filename = self._get_filename(path)

        return parent in self._fs and filename in self._fs[parent]

    def is_directory(self, path: str) -> bool:
        """Check if path is a directory.

        Args:
            path: Path to check

        Returns:
            True if path is a directory
        """
        path = self._normalize_path(path)
        return path in self._fs

    def is_file(self, path: str) -> bool:
        """Check if path is a file.

        Args:
            path: Path to check

        Returns:
            True if path is a file
        """
        path = self._normalize_path(path)
        parent = self._get_parent_path(path)
        filename = self._get_filename(path)

        return (
            parent in self._fs
            and filename in self._fs[parent]
            and not self._fs[parent][filename].is_directory
        )

    def mkdir(self, path: str) -> tuple[bool, str]:
        """Create directory.

        Args:
            path: Directory path to create

        Returns:
            (success, error_message)
        """
        path = self._normalize_path(path)

        if self.exists(path):
            return False, f"mkdir: cannot create directory '{path}': File exists"

        parent = self._get_parent_path(path)
        if not self.is_directory(parent):
            return (
                False,
                f"mkdir: cannot create directory '{path}': No such file or directory",
            )

        self._create_dir(path)
        return True, ""

    def touch(self, path: str) -> tuple[bool, str]:
        """Create empty file or update timestamp.

        Args:
            path: File path

        Returns:
            (success, error_message)
        """
        path = self._normalize_path(path)

        if self.is_file(path):
            # Update timestamp
            parent = self._get_parent_path(path)
            filename = self._get_filename(path)
            self._fs[parent][filename].modified_at = datetime.now()
            return True, ""

        if self.is_directory(path):
            return False, f"touch: cannot touch '{path}': Is a directory"

        parent = self._get_parent_path(path)
        if not self.is_directory(parent):
            return False, f"touch: cannot touch '{path}': No such file or directory"

        self._create_file(path)
        return True, ""

    def rm(
        self, path: str, recursive: bool = False, force: bool = False
    ) -> tuple[bool, str]:
        """Remove file or directory.

        Args:
            path: Path to remove
            recursive: Remove directories recursively
            force: Force removal

        Returns:
            (success, error_message)
        """
        path = self._normalize_path(path)

        if not self.exists(path):
            if force:
                return True, ""
            return False, f"rm: cannot remove '{path}': No such file or directory"

        if self.is_directory(path):
            if not recursive:
                return False, f"rm: cannot remove '{path}': Is a directory"

            # Remove directory and contents
            if path in self._fs:
                del self._fs[path]

                # Remove from parent
                parent = self._get_parent_path(path)
                filename = self._get_filename(path)
                if parent in self._fs and filename in self._fs[parent]:
                    del self._fs[parent][filename]

            return True, ""

        # Remove file
        parent = self._get_parent_path(path)
        filename = self._get_filename(path)

        if parent in self._fs and filename in self._fs[parent]:
            del self._fs[parent][filename]

        return True, ""

    def cat(self, path: str) -> tuple[bool, str]:
        """Read file content.

        Args:
            path: File path

        Returns:
            (success, content_or_error)
        """
        path = self._normalize_path(path)

        if not self.exists(path):
            return False, f"cat: {path}: No such file or directory"

        if self.is_directory(path):
            return False, f"cat: {path}: Is a directory"

        parent = self._get_parent_path(path)
        filename = self._get_filename(path)

        # Check permissions (basic simulation)
        vfile = self._fs[parent][filename]
        if vfile.owner == "root" and vfile.permissions.startswith("rw-------"):
            return False, f"cat: {path}: Permission denied"

        return True, vfile.content

    def write_file(
        self, path: str, content: str, append: bool = False
    ) -> tuple[bool, str]:
        """Write content to file.

        Args:
            path: File path
            content: Content to write
            append: Append mode

        Returns:
            (success, error_message)
        """
        path = self._normalize_path(path)

        if self.is_directory(path):
            return False, f"bash: {path}: Is a directory"

        parent = self._get_parent_path(path)
        if not self.is_directory(parent):
            return False, f"bash: {path}: No such file or directory"

        if self.is_file(path):
            # Update existing file
            filename = self._get_filename(path)
            if append:
                self._fs[parent][filename].append_content(content)
            else:
                self._fs[parent][filename].update_content(content)
        else:
            # Create new file
            self._create_file(path, content)

        return True, ""

    def ls(
        self, path: str = "", all_files: bool = False, long_format: bool = False
    ) -> tuple[bool, str]:
        """List directory contents.

        Args:
            path: Directory path
            all_files: Include hidden files
            long_format: Long format listing

        Returns:
            (success, output_or_error)
        """
        if not path:
            path = self.current_dir

        path = self._normalize_path(path)

        if not self.exists(path):
            return False, f"ls: cannot access '{path}': No such file or directory"

        if self.is_file(path):
            # Just list the file itself
            parent = self._get_parent_path(path)
            filename = self._get_filename(path)
            vfile = self._fs[parent][filename]
            return True, vfile.get_ls_entry(long_format)

        # List directory
        if path not in self._fs:
            return False, f"ls: cannot access '{path}': No such file or directory"

        entries = []
        files = self._fs[path]

        # Sort: directories first, then files, alphabetically
        sorted_files = sorted(
            files.values(), key=lambda f: (not f.is_directory, f.name)
        )

        for vfile in sorted_files:
            # Skip hidden files unless -a
            if not all_files and vfile.name.startswith("."):
                continue

            entries.append(vfile.get_ls_entry(long_format))

        if long_format:
            # Add total line
            total_blocks = sum(
                f.size // 1024 + 1
                for f in sorted_files
                if not f.name.startswith(".") or all_files
            )
            return True, f"total {total_blocks}\n" + "\n".join(entries)

        # Column format (simple space-separated for now)
        return True, "  ".join(entries)

    def cd(self, path: str = "") -> tuple[bool, str]:
        """Change current directory.

        Args:
            path: Target directory path

        Returns:
            (success, error_message)
        """
        if not path or path == "~":
            # Go to home
            self.current_dir = f"/home/{self.username}"
            return True, ""

        target = self._normalize_path(path)

        if not self.exists(target):
            return False, f"bash: cd: {path}: No such file or directory"

        if not self.is_directory(target):
            return False, f"bash: cd: {path}: Not a directory"

        self.current_dir = target
        return True, ""

    def pwd(self) -> str:
        """Get current directory.

        Returns:
            Current directory path
        """
        return self.current_dir

    def get_prompt(self) -> str:
        """Get shell prompt.

        Returns:
            Shell prompt string
        """
        # Show ~ for home directory
        display_dir = self.current_dir
        home = f"/home/{self.username}"
        if display_dir.startswith(home):
            display_dir = "~" + display_dir[len(home) :]

        return f"{self.username}@{self.hostname}:{display_dir}$ "

    def chmod(self, permissions: str, path: str) -> tuple[bool, str]:
        """Change file permissions (simulated).

        Args:
            permissions: Permission string
            path: File path

        Returns:
            (success, error_message)
        """
        path = self._normalize_path(path)

        if not self.exists(path):
            return False, f"chmod: cannot access '{path}': No such file or directory"

        # Simulate permission change (just accept it)
        return True, ""

    def chown(self, owner: str, path: str) -> tuple[bool, str]:
        """Change file owner (simulated).

        Args:
            owner: New owner
            path: File path

        Returns:
            (success, error_message)
        """
        path = self._normalize_path(path)

        if not self.exists(path):
            return False, f"chown: cannot access '{path}': No such file or directory"

        # Simulate - in honeypot, non-root users can't actually chown
        return False, f"chown: changing ownership of '{path}': Operation not permitted"

    def find(self, start_path: str = ".", name_pattern: str = "*") -> tuple[bool, str]:
        """Simple find implementation.

        Args:
            start_path: Starting directory
            name_pattern: Filename pattern

        Returns:
            (success, output)
        """
        start_path = self._normalize_path(start_path)

        if not self.exists(start_path):
            return False, f"find: '{start_path}': No such file or directory"

        results = []

        def search_dir(dir_path: str):
            if dir_path not in self._fs:
                return

            for name, vfile in self._fs[dir_path].items():
                full_path = f"{dir_path}/{name}".replace("//", "/")

                # Pattern matching with wildcards
                if fnmatch.fnmatch(name, name_pattern):
                    results.append(full_path)

                # Recurse into subdirectories
                if vfile.is_directory:
                    search_dir(full_path)

        if self.is_directory(start_path):
            search_dir(start_path)
        else:
            results.append(start_path)

        return True, "\n".join(results) if results else ""
