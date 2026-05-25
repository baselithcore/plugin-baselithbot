"""System management commands (systemctl, service, apt, etc.)."""

from typing import List
from .base import BaseCommands


class SystemManagementCommands(BaseCommands):
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

    def _systemctl_status_nginx(self) -> str:
        """Return nginx service status."""
        return """● nginx.service - A high performance web server and a reverse proxy server
     Loaded: loaded (/lib/systemd/system/nginx.service; enabled; vendor preset: enabled)
     Active: active (running) since Mon 2025-12-02 08:01:30 UTC; 3 weeks 2 days ago
       Docs: man:nginx(8)
    Process: 1234 ExecStartPre=/usr/sbin/nginx -t -q -g daemon on; master_process on; (code=exited, status=0/SUCCESS)
    Process: 1235 ExecStart=/usr/sbin/nginx -g daemon on; master_process on; (code=exited, status=0/SUCCESS)
   Main PID: 1236 (nginx)
      Tasks: 5 (limit: 4650)
     Memory: 12.3M
        CPU: 234ms
     CGroup: /system.slice/nginx.service
             ├─1236 nginx: master process /usr/sbin/nginx -g daemon on; master_process on;
             ├─1237 nginx: worker process
             ├─1238 nginx: worker process
             ├─1239 nginx: worker process
             └─1240 nginx: worker process

Jan 02 08:01:30 ubuntu-web-01 systemd[1]: Starting A high performance web server and a reverse proxy server...
Jan 02 08:01:30 ubuntu-web-01 systemd[1]: Started A high performance web server and a reverse proxy server."""

    def _systemctl_status_mysql(self) -> str:
        """Return MySQL service status."""
        return """● mysql.service - MySQL Community Server
     Loaded: loaded (/lib/systemd/system/mysql.service; enabled; vendor preset: enabled)
     Active: active (running) since Mon 2025-12-02 08:01:35 UTC; 3 weeks 2 days ago
   Main PID: 1250 (mysqld)
     Status: "Server is operational"
      Tasks: 38 (limit: 4650)
     Memory: 356.2M
        CPU: 5.234s
     CGroup: /system.slice/mysql.service
             └─1250 /usr/sbin/mysqld

Jan 02 08:01:32 ubuntu-web-01 systemd[1]: Starting MySQL Community Server...
Jan 02 08:01:35 ubuntu-web-01 systemd[1]: Started MySQL Community Server."""

    def _systemctl_status_ssh(self) -> str:
        """Return SSH service status."""
        return """● ssh.service - OpenBSD Secure Shell server
     Loaded: loaded (/lib/systemd/system/ssh.service; enabled; vendor preset: enabled)
     Active: active (running) since Mon 2025-12-02 08:01:28 UTC; 3 weeks 2 days ago
       Docs: man:sshd(8)
             man:sshd_config(5)
   Main PID: 1220 (sshd)
      Tasks: 1 (limit: 4650)
     Memory: 3.2M
        CPU: 123ms
     CGroup: /system.slice/ssh.service
             └─1220 sshd: /usr/sbin/sshd -D [listener] 0 of 10-100 startups

Jan 02 08:01:28 ubuntu-web-01 systemd[1]: Starting OpenBSD Secure Shell server...
Jan 02 08:01:28 ubuntu-web-01 sshd[1220]: Server listening on 0.0.0.0 port 22.
Jan 02 08:01:28 ubuntu-web-01 sshd[1220]: Server listening on :: port 22.
Jan 02 08:01:28 ubuntu-web-01 systemd[1]: Started OpenBSD Secure Shell server."""

    def _systemctl_status_php(self) -> str:
        """Return PHP-FPM service status."""
        return """● php8.1-fpm.service - The PHP 8.1 FastCGI Process Manager
     Loaded: loaded (/lib/systemd/system/php8.1-fpm.service; enabled; vendor preset: enabled)
     Active: active (running) since Mon 2025-12-02 08:01:40 UTC; 3 weeks 2 days ago
       Docs: man:php-fpm8.1(8)
   Main PID: 1280 (php-fpm8.1)
     Status: "Processes active: 0, idle: 2, Requests: 234, slow: 0, Traffic: 0req/sec"
      Tasks: 3 (limit: 4650)
     Memory: 15.6M
        CPU: 567ms
     CGroup: /system.slice/php8.1-fpm.service
             ├─1280 php-fpm: master process (/etc/php/8.1/fpm/php-fpm.conf)
             ├─1281 php-fpm: pool www
             └─1282 php-fpm: pool www

Jan 02 08:01:40 ubuntu-web-01 systemd[1]: Starting The PHP 8.1 FastCGI Process Manager...
Jan 02 08:01:40 ubuntu-web-01 systemd[1]: Started The PHP 8.1 FastCGI Process Manager."""

    def _systemctl_status_cron(self) -> str:
        """Return cron service status."""
        return """● cron.service - Regular background program processing daemon
     Loaded: loaded (/lib/systemd/system/cron.service; enabled; vendor preset: enabled)
     Active: active (running) since Mon 2025-12-02 08:01:25 UTC; 3 weeks 2 days ago
       Docs: man:cron(8)
   Main PID: 1200 (cron)
      Tasks: 1 (limit: 4650)
     Memory: 1.2M
        CPU: 45ms
     CGroup: /system.slice/cron.service
             └─1200 /usr/sbin/cron -f

Jan 02 08:01:25 ubuntu-web-01 systemd[1]: Started Regular background program processing daemon.
Jan 02 08:01:25 ubuntu-web-01 cron[1200]: (CRON) INFO (pidfile fd = 3)
Jan 02 08:01:25 ubuntu-web-01 cron[1200]: (CRON) INFO (Running @reboot jobs)"""

    def _systemctl_list_units(self) -> str:
        """List systemd units."""
        return """UNIT                                                  LOAD   ACTIVE SUB       DESCRIPTION
proc-sys-fs-binfmt_misc.automount                     loaded active waiting   Arbitrary Executable File Formats File System Automount Point
sys-devices-platform-serial8250-tty-ttyS0.device      loaded active plugged   /sys/devices/platform/serial8250/tty/ttyS0
sys-devices-pci0000:00-0000:00:03.0-net-eth0.device   loaded active plugged   82540EM Gigabit Ethernet Controller
sys-module-fuse.device                                 loaded active plugged   /sys/module/fuse
-.mount                                                loaded active mounted   Root Mount
boot.mount                                             loaded active mounted   /boot
dev-hugepages.mount                                    loaded active mounted   Huge Pages File System
dev-mqueue.mount                                       loaded active mounted   POSIX Message Queue File System
run-lock.mount                                         loaded active mounted   Lock Directory
ssh.service                                            loaded active running   OpenBSD Secure Shell server
nginx.service                                          loaded active running   A high performance web server and a reverse proxy server
mysql.service                                          loaded active running   MySQL Community Server
php8.1-fpm.service                                     loaded active running   The PHP 8.1 FastCGI Process Manager
cron.service                                           loaded active running   Regular background program processing daemon
systemd-journald.service                               loaded active running   Journal Service
systemd-logind.service                                 loaded active running   User Login Management
systemd-networkd.service                               loaded active running   Network Configuration
systemd-resolved.service                               loaded active running   Network Name Resolution
systemd-timesyncd.service                              loaded active running   Network Time Synchronization
systemd-udevd.service                                  loaded active running   Device Manager

LOAD   = Reflects whether the unit definition was properly loaded.
ACTIVE = The high-level unit activation state, i.e. generalization of SUB.
SUB    = The low-level unit activation state, values depend on unit type.
20 loaded units listed."""

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

    def _cmd_apt(self, args: List[str]) -> str:
        """Handle apt command."""
        if not args:
            return """apt 2.4.11 (amd64)
Usage: apt [options] command

apt is a commandline package manager and provides commands for
searching and managing as well as querying information about packages.
It provides the same functionality as the specialized APT tools,
like apt-get and apt-cache, but enables options more suitable for
interactive use by default.

Most used commands:
  list - list packages based on package names
  search - search in package descriptions
  show - show package details
  install - install packages
  reinstall - reinstall packages
  remove - remove packages
  autoremove - Remove automatically all unused packages
  update - update list of available packages
  upgrade - upgrade the system by installing/upgrading packages
  full-upgrade - upgrade the system by removing/installing/upgrading packages
  edit-sources - edit the source information file
  satisfy - satisfy dependency strings

See apt(8) for more information about the available commands."""

        action = args[0].lower()

        if action == "update":
            return """Hit:1 http://archive.ubuntu.com/ubuntu jammy InRelease
Get:2 http://security.ubuntu.com/ubuntu jammy-security InRelease [110 kB]
Get:3 http://archive.ubuntu.com/ubuntu jammy-updates InRelease [119 kB]
Get:4 http://archive.ubuntu.com/ubuntu jammy-backports InRelease [109 kB]
Fetched 338 kB in 2s (169 kB/s)
Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
12 packages can be upgraded. Run 'apt list --upgradable' to see them."""

        elif action == "upgrade":
            return """Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
Calculating upgrade... Done
The following packages will be upgraded:
  libssl3 openssl linux-image-generic
3 upgraded, 0 newly installed, 0 to remove and 0 not upgraded.
Need to get 15.2 MB of archives.
After this operation, 256 kB of additional disk space will be used.
Do you want to continue? [Y/n] """

        elif action == "install":
            if len(args) < 2:
                return "E: Command line option 'install' requires an argument"

            package = args[1]
            return f"""Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
The following NEW packages will be installed:
  {package}
0 upgraded, 1 newly installed, 0 to remove and 12 not upgraded.
Need to get 1234 kB of archives.
After this operation, 5678 kB of additional disk space will be used.
Do you want to continue? [Y/n] """

        elif action == "remove":
            if len(args) < 2:
                return "E: Command line option 'remove' requires an argument"

            package = args[1]
            return f"""Reading package lists... Done
Building dependency tree... Done
Reading state information... Done
The following packages will be REMOVED:
  {package}
0 upgraded, 0 newly installed, 1 to remove and 12 not upgraded.
After this operation, 5678 kB disk space will be freed.
Do you want to continue? [Y/n] """

        elif action == "list":
            if len(args) > 1 and args[1] == "--upgradable":
                return """Listing... Done
libssl3/jammy-updates 3.0.2-0ubuntu1.14 amd64 [upgradable from: 3.0.2-0ubuntu1.12]
openssl/jammy-updates 3.0.2-0ubuntu1.14 amd64 [upgradable from: 3.0.2-0ubuntu1.12]
linux-image-generic/jammy-updates 5.15.0.91.88 amd64 [upgradable from: 5.15.0.89.86]"""
            else:
                # Show installed packages (truncated)
                packages = [
                    "nginx-common/jammy-updates,now 1.18.0-0ubuntu1.5 all [installed]",
                    "nginx-core/jammy-updates,now 1.18.0-0ubuntu1.5 amd64 [installed]",
                    "mysql-server/jammy-updates,now 8.0.35-0ubuntu0.22.04.1 amd64 [installed]",
                    "php8.1-fpm/jammy-updates,now 8.1.2-1ubuntu2.14 amd64 [installed]",
                    "openssh-server/jammy-updates,now 1:8.9p1-3ubuntu0.6 amd64 [installed]",
                ]
                return "Listing...\n" + "\n".join(packages[:10])

        elif action == "search":
            if len(args) < 2:
                return "E: Command line option 'search' requires an argument"
            query = args[1]
            return f"""Sorting... Done
Full Text Search... Done
{query}/jammy 1.0.0-1 amd64
  Sample package matching {query}

{query}-common/jammy 1.0.0-1 all
  Common files for {query}"""

        elif action == "show":
            if len(args) < 2:
                return "E: Command line option 'show' requires an argument"

            package = args[1]
            return f"""Package: {package}
Version: 1.0.0-1ubuntu1
Priority: optional
Section: web
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Installed-Size: 1234 kB
Depends: libc6 (>= 2.34)
Homepage: https://example.com
Download-Size: 567 kB
APT-Sources: http://archive.ubuntu.com/ubuntu jammy/main amd64 Packages
Description: Sample package description
 This is a sample package description for the honeypot.
 It provides realistic output for apt commands."""

        else:
            return f"E: Invalid operation {action}"

    def _cmd_dpkg(self, args: List[str]) -> str:
        """Handle dpkg command."""
        if not args:
            return """Usage: dpkg [<option> ...] <command>

Commands:
  -i|--install       <.deb file name>... | -R|--recursive <directory>...
  -r|--remove        <package>...        | -a|--pending
  -P|--purge         <package>...        | -a|--pending
  -l|--list          [<pattern>...]      Show matching packages
  -s|--status        <package>...        Display package status details"""

        action = args[0]

        if action == "-l" or action == "--list":
            # pattern = args[1] if len(args) > 1 else ""
            return """Desired=Unknown/Install/Remove/Purge/Hold
| Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend
|/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)
||/ Name                        Version              Architecture Description
+++-===========================-====================-============-===============================================
ii  nginx-common                1.18.0-0ubuntu1.5    all          small, powerful, scalable web/proxy server
ii  nginx-core                  1.18.0-0ubuntu1.5    amd64        nginx web/proxy server (standard version)
ii  mysql-server-8.0            8.0.35-0ubuntu0.22   amd64        MySQL Server - metapackage
ii  php8.1-fpm                  8.1.2-1ubuntu2.14    amd64        server-side, HTML-embedded scripting language
ii  openssh-server              1:8.9p1-3ubuntu0.6   amd64        secure shell (SSH) server"""

        elif action == "-s" or action == "--status":
            if len(args) < 2:
                return "dpkg-query: error: --status needs a valid package name"

            package = args[1]
            return f"""Package: {package}
Status: install ok installed
Priority: optional
Section: web
Installed-Size: 1234
Maintainer: Ubuntu Developers <ubuntu-devel-discuss@lists.ubuntu.com>
Architecture: amd64
Version: 1.0.0-1ubuntu1
Description: Sample package
 This is a sample installed package."""

        elif action == "-i" or action == "--install":
            if len(args) < 2:
                return "dpkg: error: --install needs at least one package name argument"

            deb_file = args[1]
            return f"""Selecting previously unselected package.
(Reading database ... 123456 files and directories currently installed.)
Preparing to unpack {deb_file} ...
Unpacking package (1.0.0-1) ...
Setting up package (1.0.0-1) ..."""

        return f"dpkg: error: unknown option {action}"
