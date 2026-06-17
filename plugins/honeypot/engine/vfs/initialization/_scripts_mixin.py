"""Scripts mixin for FilesystemInitializer."""


class ScriptsMixin:
    """Mixin providing _create_scripts and _create_common_binaries methods."""

    def _create_scripts(self) -> None:
        """Create example scripts in user home."""
        home = f"/home/{self.username}"

        self._create_file(
            f"{home}/scripts/backup.sh",
            """#!/bin/bash
# Simple backup script
# Created: 2023-08-15
# TODO: add email notification

BACKUP_DIR="/var/backups"
DATE=$(date +%Y%m%d)

tar -czf $BACKUP_DIR/home_$DATE.tar.gz /home/
# rsync -av /var/www/ $BACKUP_DIR/www_$DATE/

echo "Backup completed"
""",
            permissions="rwxr-xr-x",
            is_executable=True,
        )

        self._create_file(
            f"{home}/scripts/check_disk.sh",
            """#!/bin/bash
# disk space check - runs from cron
THRESHOLD=90
CURRENT=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $CURRENT -gt $THRESHOLD ]; then
    echo "WARNING: Disk usage at $CURRENT%"
    # mail -s "Disk Alert" admin@localhost
fi
""",
            permissions="rwxr-xr-x",
            is_executable=True,
        )

    def _create_common_binaries(self) -> None:
        """Create common binary placeholders."""
        binaries = [
            "python3",
            "python",
            "wget",
            "curl",
            "vim",
            "nano",
            "less",
            "grep",
            "awk",
            "sed",
            "tar",
            "gzip",
            "systemctl",
            "service",
            "netstat",
            "ss",
            "ifconfig",
            "ip",
            "apt",
            "dpkg",
            "top",
            "htop",
            "ps",
        ]

        for binary in binaries:
            self._create_file(
                f"/usr/bin/{binary}",
                f"#!/bin/bash\n# {binary}\n",
                permissions="rwxr-xr-x",
                is_executable=True,
            )
