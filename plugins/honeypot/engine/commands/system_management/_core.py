"""System management commands (systemctl, service, journalctl)."""

from typing import List

from ..base import BaseCommands
from ._service_status import ServiceStatusMixin
from ._packages import PackagesMixin


class SystemManagementCommands(ServiceStatusMixin, PackagesMixin, BaseCommands):
    """System management and service control commands."""

    def _cmd_systemctl(self, args: List[str]) -> str:
        """Handle systemctl command."""
        if not args:
            return """Failed to list units: Permission denied
See system logs and 'systemctl status' for details."""

        action = args[0].lower()

        # Status command
        if action == "status":
            service = args[1] if len(args) > 1 else None
            if not service:
                # Show system status
                return """● ubuntu-web-01
    State: running
     Jobs: 0 queued
   Failed: 0 units
    Since: Mon 2025-12-02 08:00:15 UTC; 3 weeks 2 days ago
   CGroup: /
           ├─user.slice
           ├─system.slice
           │ ├─nginx.service
           │ ├─mysql.service
           │ ├─php8.1-fpm.service
           │ ├─ssh.service
           │ └─cron.service
           └─init.scope
             └─1 /sbin/init"""

            # Service-specific status
            service = service.replace(".service", "")
            services = {
                "nginx": self._systemctl_status_nginx,
                "mysql": self._systemctl_status_mysql,
                "ssh": self._systemctl_status_ssh,
                "sshd": self._systemctl_status_ssh,
                "php8.1-fpm": self._systemctl_status_php,
                "cron": self._systemctl_status_cron,
            }

            handler = services.get(service)
            if handler:
                return handler()
            else:
                return f"""Unit {service}.service could not be found."""

        # List services
        elif action == "list-units":
            return self._systemctl_list_units()

        # Start/stop/restart/reload service
        elif action in ("start", "stop", "restart", "reload", "enable", "disable"):
            service = args[1] if len(args) > 1 else None
            if not service:
                return "Too few arguments."

            # Simulate success
            if action in ("start", "restart", "reload"):
                return ""  # Success produces no output
            elif action == "stop":
                return ""
            elif action == "enable":
                return f"""Created symlink /etc/systemd/system/multi-user.target.wants/{service} → /lib/systemd/system/{service}"""
            elif action == "disable":
                return (
                    f"""Removed /etc/systemd/system/multi-user.target.wants/{service}"""
                )

        # Daemon-reload
        elif action == "daemon-reload":
            return ""  # Success produces no output

        # is-active/is-enabled
        elif action == "is-active":
            service = args[1] if len(args) > 1 else None
            if service and service.replace(".service", "") in [
                "nginx",
                "mysql",
                "ssh",
                "sshd",
                "cron",
            ]:
                return "active"
            else:
                return "inactive"

        elif action == "is-enabled":
            service = args[1] if len(args) > 1 else None
            if service and service.replace(".service", "") in [
                "nginx",
                "mysql",
                "ssh",
                "sshd",
            ]:
                return "enabled"
            else:
                return "disabled"

        return f"Unknown operation '{action}'."

    def _cmd_service(self, args: List[str]) -> str:
        """Handle service command (legacy init.d interface)."""
        if not args:
            return """Usage: service < option > | --status-all | [ service_name [ command | --full-restart ] ]"""

        if args[0] == "--status-all":
            return """ [ + ]  cron
 [ + ]  mysql
 [ + ]  nginx
 [ + ]  php8.1-fpm
 [ + ]  ssh
 [ - ]  apache2
 [ - ]  postgresql"""

        service = args[0]
        action = args[1] if len(args) > 1 else "status"

        # Map common services
        if service in ("nginx", "mysql", "ssh", "sshd", "cron", "php8.1-fpm"):
            if action == "status":
                # Delegate to systemctl
                return self._cmd_systemctl(["status", service])
            elif action in ("start", "stop", "restart", "reload"):
                return f"{service}: {action}ing service..."
            else:
                return f"Usage: /etc/init.d/{service} {{start|stop|restart|reload|force-reload|status}}"
        else:
            return f"{service}: unrecognized service"

    def _cmd_journalctl(self, args: List[str]) -> str:
        """Handle journalctl command."""
        # Parse common options
        unit = None
        # lines = 10
        follow = False

        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "-u" and i + 1 < len(args):
                unit = args[i + 1].replace(".service", "")
                i += 2
            elif arg == "-n" and i + 1 < len(args):
                try:
                    # lines = int(args[i + 1])
                    pass
                except ValueError:
                    pass
                i += 2
            elif arg in ("-f", "--follow"):
                follow = True
                i += 1
            else:
                i += 1

        if follow:
            return "-- Logs begin at Mon 2025-12-02 08:00:15 UTC. --\n(Following logs, press Ctrl+C to stop)"

        # Show logs for specific unit
        if unit:
            if unit == "nginx":
                return """-- Logs begin at Mon 2025-12-02 08:00:15 UTC, end at Thu Jan 02 12:34:56 2026 UTC. --
Jan 02 08:01:30 ubuntu-web-01 systemd[1]: Starting A high performance web server and a reverse proxy server...
Jan 02 08:01:30 ubuntu-web-01 nginx[1235]: nginx: configuration file /etc/nginx/nginx.conf test is successful
Jan 02 08:01:30 ubuntu-web-01 systemd[1]: Started A high performance web server and a reverse proxy server."""
            elif unit == "mysql":
                return """-- Logs begin at Mon 2025-12-02 08:00:15 UTC, end at Thu Jan 02 12:34:56 2026 UTC. --
Jan 02 08:01:32 ubuntu-web-01 systemd[1]: Starting MySQL Community Server...
Jan 02 08:01:35 ubuntu-web-01 systemd[1]: Started MySQL Community Server."""
            elif unit in ("ssh", "sshd"):
                return """-- Logs begin at Mon 2025-12-02 08:00:15 UTC, end at Thu Jan 02 12:34:56 2026 UTC. --
Jan 02 08:01:28 ubuntu-web-01 systemd[1]: Starting OpenBSD Secure Shell server...
Jan 02 08:01:28 ubuntu-web-01 sshd[1220]: Server listening on 0.0.0.0 port 22.
Jan 02 08:01:28 ubuntu-web-01 sshd[1220]: Server listening on :: port 22.
Jan 02 08:01:28 ubuntu-web-01 systemd[1]: Started OpenBSD Secure Shell server.
Jan 02 10:15:22 ubuntu-web-01 sshd[1234]: Connection from 192.168.1.100 port 54321
Jan 02 10:15:23 ubuntu-web-01 sshd[1234]: Accepted password for admin from 192.168.1.100 port 54321 ssh2"""

        # Show general system logs
        return """-- Logs begin at Mon 2025-12-02 08:00:15 UTC, end at Thu Jan 02 12:34:56 2026 UTC. --
Jan 02 08:00:15 ubuntu-web-01 kernel: Linux version 5.15.0-91-generic
Jan 02 08:00:15 ubuntu-web-01 systemd[1]: systemd 249.11-0ubuntu3.12 running in system mode.
Jan 02 08:00:15 ubuntu-web-01 systemd[1]: Detected architecture x86-64.
Jan 02 08:01:25 ubuntu-web-01 systemd[1]: Started Regular background program processing daemon.
Jan 02 08:01:28 ubuntu-web-01 systemd[1]: Started OpenBSD Secure Shell server.
Jan 02 08:01:30 ubuntu-web-01 systemd[1]: Started A high performance web server and a reverse proxy server.
Jan 02 08:01:35 ubuntu-web-01 systemd[1]: Started MySQL Community Server.
Jan 02 08:01:40 ubuntu-web-01 systemd[1]: Started The PHP 8.1 FastCGI Process Manager.
Jan 02 09:17:01 ubuntu-web-01 CRON[12345]: (root) CMD (   cd / && run-parts --report /etc/cron.hourly)
Jan 02 10:15:23 ubuntu-web-01 sshd[1234]: Accepted password for admin from 192.168.1.100 port 54321 ssh2"""
