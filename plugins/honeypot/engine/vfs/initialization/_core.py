"""Core FilesystemInitializer class."""

from ._user_mixin import UserFilesMixin
from ._scripts_mixin import ScriptsMixin
from ._services_mixin import ServicesMixin
from ._proc_mixin import ProcMixin


class FilesystemInitializer(UserFilesMixin, ScriptsMixin, ServicesMixin, ProcMixin):
    """Handles initialization of a realistic virtual filesystem."""

    def __init__(self, username: str, hostname: str):
        """Initialize the filesystem initializer.

        Args:
            username: Username for the filesystem
            hostname: Hostname for the system
        """
        self.username = username
        self.hostname = hostname

    def initialize(self, create_dir_func, create_file_func) -> None:
        """Initialize filesystem with realistic structure.

        Args:
            create_dir_func: Function to create directories
            create_file_func: Function to create files
        """
        self._create_dir = create_dir_func
        self._create_file = create_file_func

        self._create_directory_structure()
        self._create_system_files()
        self._create_user_files()
        self._create_scripts()
        self._create_common_binaries()
        self._create_service_configs()
        self._create_proc_files()
        self._create_dev_files()
        self._create_log_files()

    def _create_directory_structure(self) -> None:
        """Create base directory structure."""
        # Root directories
        self._create_dir("/")
        self._create_dir("/home")
        self._create_dir("/etc")
        self._create_dir("/var")
        self._create_dir("/var/log")
        self._create_dir("/var/tmp")  # nosec B108
        self._create_dir("/var/cache")
        self._create_dir("/var/run")
        self._create_dir("/tmp")  # nosec B108
        self._create_dir("/usr")
        self._create_dir("/usr/bin")
        self._create_dir("/usr/local")
        self._create_dir("/usr/local/bin")
        self._create_dir("/usr/share")
        self._create_dir("/bin")
        self._create_dir("/sbin")
        self._create_dir("/opt")
        self._create_dir("/root")
        self._create_dir("/proc")
        self._create_dir("/dev")

        # User home
        home = f"/home/{self.username}"
        self._create_dir(home)
        self._create_dir(f"{home}/.ssh")
        self._create_dir(f"{home}/.config")
        self._create_dir(f"{home}/.cache")
        self._create_dir(f"{home}/.local")
        self._create_dir(f"{home}/.local/share")
        self._create_dir(f"{home}/Documents")
        self._create_dir(f"{home}/Downloads")
        self._create_dir(f"{home}/scripts")

    def _create_system_files(self) -> None:
        """Create realistic system configuration files."""
        # /etc/passwd with all system users
        self._create_file(
            "/etc/passwd",
            f"""root:x:0:0:root:/root:/bin/bash
daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin
bin:x:2:2:bin:/bin:/usr/sbin/nologin
sys:x:3:3:sys:/dev:/usr/sbin/nologin
sync:x:4:65534:sync:/bin:/bin/sync
games:x:5:60:games:/usr/games:/usr/sbin/nologin
man:x:6:12:man:/var/cache/man:/usr/sbin/nologin
lp:x:7:7:lp:/var/spool/lpd:/usr/sbin/nologin
mail:x:8:8:mail:/var/mail:/usr/sbin/nologin
news:x:9:9:news:/var/spool/news:/usr/sbin/nologin
uucp:x:10:10:uucp:/var/spool/uucp:/usr/sbin/nologin
proxy:x:13:13:proxy:/bin:/usr/sbin/nologin
www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin
backup:x:34:34:backup:/var/backups:/usr/sbin/nologin
list:x:38:38:Mailing List Manager:/var/list:/usr/sbin/nologin
irc:x:39:39:ircd:/var/run/ircd:/usr/sbin/nologin
gnats:x:41:41:Gnats Bug-Reporting System (admin):/var/lib/gnats:/usr/sbin/nologin
nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin
systemd-network:x:100:102:systemd Network Management,,,:/run/systemd:/usr/sbin/nologin
systemd-resolve:x:101:103:systemd Resolver,,,:/run/systemd:/usr/sbin/nologin
syslog:x:102:106::/home/syslog:/usr/sbin/nologin
messagebus:x:103:107::/nonexistent:/usr/sbin/nologin
_apt:x:104:65534::/nonexistent:/usr/sbin/nologin
sshd:x:105:65534::/run/sshd:/usr/sbin/nologin
{self.username}:x:1000:1000:{self.username}:/home/{self.username}:/bin/bash
mysql:x:111:116:MySQL Server,,,:/nonexistent:/bin/false""",
        )

        self._create_file("/etc/shadow", "", permissions="rw-------", owner="root")
        self._create_file("/etc/hostname", f"{self.hostname}\n")

        self._create_file(
            "/etc/hosts",
            f"""127.0.0.1\tlocalhost
127.0.1.1\t{self.hostname}

# The following lines are desirable for IPv6 capable hosts
::1     localhost ip6-localhost ip6-loopback
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
""",
        )

        self._create_file("/etc/issue", "Ubuntu 20.04.6 LTS \\n \\l\n\n")

        self._create_file(
            "/etc/os-release",
            """NAME="Ubuntu"
VERSION="20.04.6 LTS (Focal Fossa)"
ID=ubuntu
ID_LIKE=debian
PRETTY_NAME="Ubuntu 20.04.6 LTS"
VERSION_ID="20.04"
HOME_URL="https://www.ubuntu.com/"
SUPPORT_URL="https://help.ubuntu.com/"
BUG_REPORT_URL="https://bugs.launchpad.net/ubuntu/"
PRIVACY_POLICY_URL="https://www.ubuntu.com/legal/terms-and-policies/privacy-policy"
VERSION_CODENAME=focal
UBUNTU_CODENAME=focal
""",
        )

        self._create_file(
            "/etc/crontab",
            """# /etc/crontab: system-wide crontab
# Unlike any other crontab you don't have to run the `crontab'
# command to install the new version when you edit this file
# and files in /etc/cron.d. These files also have username fields,
# that none of the other crontabs do.

SHELL=/bin/sh
PATH=/usr/local/sbin:/usr/local/bin:/sbin:/bin:/usr/sbin:/usr/bin

# m h dom mon dow user  command
17 *    * * *   root    cd / && run-parts --report /etc/cron.hourly
25 6    * * *   root    test -x /usr/sbin/anacron || ( cd / && run-parts --report /etc/cron.daily )
47 6    * * 7   root    test -x /usr/sbin/anacron || ( cd / && run-parts --report /etc/cron.weekly )
52 6    1 * *   root    test -x /usr/sbin/anacron || ( cd / && run-parts --report /etc/cron.monthly )
#
""",
        )

        #  /var/log files
        self._create_file(
            "/var/log/auth.log", "", permissions="rw-r-----", owner="root"
        )
        self._create_file("/var/log/syslog", "", permissions="rw-r-----", owner="root")
