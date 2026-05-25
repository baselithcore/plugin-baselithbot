"""Virtual filesystem data models."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class VirtualFile:
    """A file in the virtual filesystem."""

    name: str
    content: str = ""
    permissions: str = "rw-r--r--"
    owner: str = "admin"
    group: str = "admin"
    size: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: datetime = field(default_factory=datetime.now)
    is_directory: bool = False
    is_executable: bool = False

    def __post_init__(self):
        """Update size based on content."""
        self.size = len(self.content.encode("utf-8"))
        if self.is_executable:
            self.permissions = "rwxr-xr-x"
        elif self.is_directory:
            self.permissions = "rwxr-xr-x"

    def update_content(self, content: str) -> None:
        """Update file content and metadata."""
        self.content = content
        self.size = len(content.encode("utf-8"))
        self.modified_at = datetime.now()

    def append_content(self, content: str) -> None:
        """Append to file content."""
        self.content += content
        self.size = len(self.content.encode("utf-8"))
        self.modified_at = datetime.now()

    def get_ls_entry(self, long_format: bool = False) -> str:
        """Get ls-style entry for this file."""
        if not long_format:
            return self.name if not self.is_directory else f"{self.name}/"

        # Long format: -rw-r--r-- 1 admin admin 1234 Jan 01 10:00 filename
        file_type = "d" if self.is_directory else "-"
        perms = f"{file_type}{self.permissions}"
        timestamp = self.modified_at.strftime("%b %d %H:%M")

        return f"{perms} 1 {self.owner} {self.group} {self.size:>6} {timestamp} {self.name}"
