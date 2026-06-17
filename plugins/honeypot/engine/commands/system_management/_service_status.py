"""Service status mixin for SystemManagementCommands."""


class ServiceStatusMixin:
    """Methods returning per-service systemctl status output."""

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
