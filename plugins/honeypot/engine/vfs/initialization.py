"""Filesystem initialization logic with realistic file structure."""


class FilesystemInitializer:
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

    def _create_user_files(self) -> None:
        """Create realistic user home directory files."""
        home = f"/home/{self.username}"

        # Bash history with realistic commands
        self._create_file(
            f"{home}/.bash_history",
            """sudo apt update
sudo apt upgrade -y
cd /var/log
tail -f syslog
ps aux | grep nginx
systemctl status mysql
df -h
free -m
htop
cd ~
ls -la
cat /etc/passwd
netstat -tulpn
ss -tulpn
docker ps
# failed here, docker not installed
sudo apt install docker.io
# forgot sudo, trying again
history
vim /etc/nginx/nginx.conf
# q! to exit without saving
systemctl reload nginx
curl localhost
wget http://localhost/test
ping 8.8.8.8
traceroute google.com
nslookup google.com
dig google.com
ip a
ifconfig
route -n
cat /proc/cpuinfo
uname -a
uptime
who
w
last
""",
            permissions="rw-------",
        )

        # Comprehensive .bashrc
        self._create_file(
            f"{home}/.bashrc",
            """# ~/.bashrc: executed by bash(1) for non-login shells.
# see /usr/share/doc/bash/examples/startup-files (in the package bash-doc)
# for examples

# If not running interactively, don't do anything
case $- in
    *i*) ;;
      *) return;;
esac

# don't put duplicate lines or lines starting with space in the history.
HISTCONTROL=ignoreboth

# append to the history file, don't overwrite it
shopt -s histappend

# for setting history length see HISTSIZE and HISTFILESIZE in bash(1)
HISTSIZE=1000
HISTFILESIZE=2000

# check the window size after each command
shopt -s checkwinsize

# make less more friendly for non-text input files, see lesspipe(1)
[ -x /usr/bin/lesspipe ] && eval "$(SHELL=/bin/sh lesspipe)"

# set a fancy prompt (non-color, unless we know we "want" color)
case "$TERM" in
    xterm-color|*-256color) color_prompt=yes;;
esac

if [ "$color_prompt" = yes ]; then
    PS1='${debian_chroot:+($debian_chroot)}\\[\\033[01;32m\\]\\u@\\h\\[\\033[00m\\]:\\[\\033[01;34m\\]\\w\\[\\033[00m\\]\\$ '
else
    PS1='${debian_chroot:+($debian_chroot)}\\u@\\h:\\w\\$ '
fi

# enable color support of ls and also add handy aliases
if [ -x /usr/bin/dircolors ]; then
    test -r ~/.dircolors && eval "$(dircolors -b ~/.dircolors)" || eval "$(dircolors -b)"
    alias ls='ls --color=auto'
    alias grep='grep --color=auto'
fi

# some more ls aliases
alias ll='ls -alF'
alias la='ls -A'
alias l='ls -CF'

# Add an "alert" alias for long running commands
alias alert='notify-send --urgency=low -i "$([ $? = 0 ] && echo terminal || echo error)" "$(history|tail -n1|sed -e '\\''s/^\\s*[0-9]\\+\\s*//;s/[;&|]\\s*alert$//'\\'')"'

# enable programmable completion features
if ! shopt -oq posix; then
  if [ -f /usr/share/bash-completion/bash_completion ]; then
    . /usr/share/bash-completion/bash_completion
  elif [ -f /etc/bash_completion ]; then
    . /etc/bash_completion
  fi
fi
""",
            permissions="rw-r--r--",
        )

        # .profile
        self._create_file(
            f"{home}/.profile",
            """# ~/.profile: executed by the command interpreter for login shells.
# This file is not read by bash(1), if ~/.bash_profile or ~/.bash_login
# exists.

# if running bash
if [ -n "$BASH_VERSION" ]; then
    # include .bashrc if it exists
    if [ -f "$HOME/.bashrc" ]; then
        . "$HOME/.bashrc"
    fi
fi

# set PATH so it includes user's private bin if it exists
if [ -d "$HOME/bin" ] ; then
    PATH="$HOME/bin:$PATH"
fi

if [ -d "$HOME/.local/bin" ] ; then
    PATH="$HOME/.local/bin:$PATH"
fi
""",
            permissions="rw-r--r--",
        )

        # SSH config
        self._create_file(
            f"{home}/.ssh/config",
            """# SSH client config

Host *
    ServerAliveInterval 60
    ServerAliveCountMax 3
    AddKeysToAgent yes
    IdentitiesOnly yes

# Example host
#Host myserver
#    HostName 192.168.1.100
#    User admin
#    Port 22
""",
            permissions="rw-------",
        )

        # SSH known hosts
        self._create_file(
            f"{home}/.ssh/known_hosts",
            """github.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl
gitlab.com ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAfuCHKVTjquxvt6CM6tdG4SLp1Btn/nOeHHE5UOzRdf
""",
            permissions="rw-------",
        )

        # Viminfo
        self._create_file(
            f"{home}/.viminfo",
            """# This viminfo file was generated by Vim 8.1.
# You may edit it if you're careful!

# Viminfo version
|1,4

# Value of 'encoding' when this file was written
*encoding=utf-8

# hlsearch on (langstrings)
~h

# Command Line History (newest to oldest):
:q!
:wq
:w
:set number
:syntax on

# Search String History (newest to oldest):
?error
?password
?config

# Expression History (newest to oldest):

# Input Line History (newest to oldest):

# Debug Line History (newest to oldest):

# Registers:

# File marks:
'0  1  0  ~/.bashrc
'1  15  0  /etc/nginx/nginx.conf
'2  1  0  /var/log/syslog

# Jumplist (newest first):
-'  1  0  ~/.bashrc
-'  15  0  /etc/nginx/nginx.conf
""",
            permissions="rw-------",
        )

        # Less history
        self._create_file(
            f"{home}/.lesshst",
            """.less-history-file:
.search
"error"
"warning"
"fail"
""",
            permissions="rw-------",
        )

        # Old bashrc backup
        self._create_file(
            f"{home}/.bashrc.bak",
            "# old bashrc backup from migration\n",
            permissions="rw-r--r--",
        )

        # Downloads with notes
        self._create_file(
            f"{home}/Downloads/notes.txt",
            """server credentials:
- dev server: 192.168.1.50
- staging: check with ops team

TODO:
- finish migration script
- update SSL certs (expires march)
- clean up old logs
""",
            permissions="rw-r--r--",
        )

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

    def _create_service_configs(self) -> None:
        """Create realistic service configuration files."""
        # Create nginx config directories
        self._create_dir("/etc/nginx")
        self._create_dir("/etc/nginx/sites-available")
        self._create_dir("/etc/nginx/sites-enabled")
        self._create_dir("/etc/nginx/conf.d")
        self._create_dir("/var/www")
        self._create_dir("/var/www/html")

        # Nginx main config
        self._create_file(
            "/etc/nginx/nginx.conf",
            """user www-data;
worker_processes auto;
pid /run/nginx.pid;
include /etc/nginx/modules-enabled/*.conf;

events {
    worker_connections 768;
}

http {
    sendfile on;
    tcp_nopush on;
    types_hash_max_size 2048;

    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    access_log /var/log/nginx/access.log;
    error_log /var/log/nginx/error.log;

    gzip on;

    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
""",
            permissions="rw-r--r--",
        )

        # Default nginx site
        self._create_file(
            "/etc/nginx/sites-available/default",
            """server {
    listen 80 default_server;
    listen [::]:80 default_server;

    root /var/www/html;
    index index.html index.htm index.nginx-debian.html index.php;

    server_name _;

    location / {
        try_files $uri $uri/ =404;
    }

    location ~ \\.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/php8.1-fpm.sock;
    }

    location ~ /\\.ht {
        deny all;
    }
}
""",
            permissions="rw-r--r--",
        )

        # Web root index
        self._create_file(
            "/var/www/html/index.html",
            """<!DOCTYPE html>
<html>
<head>
    <title>Welcome to nginx!</title>
</head>
<body>
    <h1>Welcome to nginx!</h1>
    <p>If you see this page, the nginx web server is successfully installed and working.</p>
</body>
</html>
""",
            permissions="rw-r--r--",
        )

        # MySQL config
        self._create_dir("/etc/mysql")
        self._create_dir("/etc/mysql/conf.d")
        self._create_file(
            "/etc/mysql/my.cnf",
            """[client]
port = 3306
socket = /var/run/mysqld/mysqld.sock

[mysqld_safe]
socket = /var/run/mysqld/mysqld.sock
nice = 0

[mysqld]
user = mysql
pid-file = /var/run/mysqld/mysqld.pid
socket = /var/run/mysqld/mysqld.sock
port = 3306
basedir = /usr
datadir = /var/lib/mysql
tmpdir = /tmp
bind-address = 127.0.0.1
key_buffer_size = 16M
max_allowed_packet = 16M
thread_stack = 192K
thread_cache_size = 8

[mysqldump]
quick
quote-names
max_allowed_packet = 16M
""",
            permissions="rw-r--r--",
        )

        # PHP config
        self._create_dir("/etc/php")
        self._create_dir("/etc/php/8.1")
        self._create_dir("/etc/php/8.1/cli")
        self._create_file(
            "/etc/php/8.1/cli/php.ini",
            """[PHP]
engine = On
short_open_tag = Off
precision = 14
output_buffering = 4096
zlib.output_compression = Off
implicit_flush = Off
serialize_precision = -1
disable_functions =
disable_classes =
zend.enable_gc = On
zend.exception_ignore_args = On
expose_php = On

max_execution_time = 30
max_input_time = 60
memory_limit = 128M

error_reporting = E_ALL & ~E_DEPRECATED & ~E_STRICT
display_errors = Off
display_startup_errors = Off
log_errors = On
error_log = /var/log/php_errors.log

post_max_size = 8M
upload_max_filesize = 2M
max_file_uploads = 20

[Date]
date.timezone = UTC

[Session]
session.save_handler = files
session.save_path = "/var/lib/php/sessions"
session.use_strict_mode = 0
session.cookie_lifetime = 0
session.gc_maxlifetime = 1440
""",
            permissions="rw-r--r--",
        )

        # SSH config
        self._create_dir("/etc/ssh")
        self._create_file(
            "/etc/ssh/sshd_config",
            """# This is the sshd server system-wide configuration file.
Include /etc/ssh/sshd_config.d/*.conf

Port 22
#AddressFamily any
#ListenAddress 0.0.0.0
#ListenAddress ::

HostKey /etc/ssh/ssh_host_rsa_key
HostKey /etc/ssh/ssh_host_ecdsa_key
HostKey /etc/ssh/ssh_host_ed25519_key

# Ciphers and keying
#RekeyLimit default none

# Logging
SyslogFacility AUTH
LogLevel INFO

# Authentication:
LoginGraceTime 2m
PermitRootLogin yes
StrictModes yes
MaxAuthTries 6
MaxSessions 10

PubkeyAuthentication yes
AuthorizedKeysFile .ssh/authorized_keys .ssh/authorized_keys2

# For this to work you will also need host keys in /etc/ssh/ssh_known_hosts
HostbasedAuthentication no

# To disable tunneled clear text passwords, change to no here!
PasswordAuthentication yes
PermitEmptyPasswords no

ChallengeResponseAuthentication no

UsePAM yes

X11Forwarding yes
PrintMotd no
PrintLastLog yes
TCPKeepAlive yes

AcceptEnv LANG LC_*

Subsystem sftp /usr/lib/openssh/sftp-server
""",
            permissions="rw-r--r--",
        )

        # Systemd service files
        self._create_dir("/etc/systemd")
        self._create_dir("/etc/systemd/system")
        self._create_file(
            "/etc/systemd/system/nginx.service",
            """[Unit]
Description=A high performance web server and a reverse proxy server
Documentation=man:nginx(8)
After=network.target nss-lookup.target

[Service]
Type=forking
PIDFile=/run/nginx.pid
ExecStartPre=/usr/sbin/nginx -t -q -g 'daemon on; master_process on;'
ExecStart=/usr/sbin/nginx -g 'daemon on; master_process on;'
ExecReload=/usr/sbin/nginx -g 'daemon on; master_process on;' -s reload
ExecStop=/sbin/start-stop-daemon --quiet --stop --retry QUIT/5 --pidfile /run/nginx.pid
TimeoutStopSec=5
KillMode=mixed

[Install]
WantedBy=multi-user.target
""",
            permissions="rw-r--r--",
        )

    def _create_proc_files(self) -> None:
        """Create realistic /proc files."""
        # /proc/cpuinfo
        self._create_file(
            "/proc/cpuinfo",
            """processor	: 0
vendor_id	: GenuineIntel
cpu family	: 6
model		: 142
model name	: Intel(R) Core(TM) i5-8250U CPU @ 1.60GHz
stepping	: 10
microcode	: 0xf0
cpu MHz		: 1800.000
cache size	: 6144 KB
physical id	: 0
siblings	: 4
core id		: 0
cpu cores	: 4
apicid		: 0
initial apicid	: 0
fpu		: yes
fpu_exception	: yes
cpuid level	: 22
wp		: yes
flags		: fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pge mca cmov pat pse36 clflush mmx fxsr sse sse2 ss ht syscall nx pdpe1gb rdtscp lm constant_tsc arch_perfmon nopl xtopology tsc_reliable nonstop_tsc cpuid pni pclmulqdq ssse3 fma cx16 pcid sse4_1 sse4_2 x2apic movbe popcnt tsc_deadline_timer aes xsave avx f16c rdrand hypervisor lahf_lm abm 3dnowprefetch invpcid_single pti fsgsbase tsc_adjust bmi1 avx2 smep bmi2 invpcid mpx rdseed adx smap clflushopt xsaveopt xsavec xgetbv1 xsaves arat md_clear flush_l1d arch_capabilities
bugs		: cpu_meltdown spectre_v1 spectre_v2 spec_store_bypass l1tf mds swapgs itlb_multihit srbds mmio_stale_data retbleed gds
bogomips	: 3600.00
clflush size	: 64
cache_alignment	: 64
address sizes	: 39 bits physical, 48 bits virtual
power management:
""",
            permissions="r--r--r--",
        )

        # /proc/meminfo
        self._create_file(
            "/proc/meminfo",
            """MemTotal:        4039172 kB
MemFree:         1234568 kB
MemAvailable:    3123456 kB
Buffers:          234567 kB
Cached:          1234567 kB
SwapCached:            0 kB
Active:          1345678 kB
Inactive:         987654 kB
Active(anon):     654321 kB
Inactive(anon):    12345 kB
Active(file):     691357 kB
Inactive(file):   975309 kB
Unevictable:           0 kB
Mlocked:               0 kB
SwapTotal:       2097148 kB
SwapFree:        2097148 kB
Dirty:                64 kB
Writeback:             0 kB
AnonPages:        654321 kB
Mapped:           234567 kB
Shmem:             12345 kB
KReclaimable:     123456 kB
Slab:             234567 kB
SReclaimable:     123456 kB
SUnreclaim:       111111 kB
""",
            permissions="r--r--r--",
        )

        # /proc/version
        self._create_file(
            "/proc/version",
            "Linux version 5.15.0-91-generic (buildd@lcy02-amd64-089) (gcc (Ubuntu 11.4.0-1ubuntu1~22.04) 11.4.0, GNU ld (GNU Binutils for Ubuntu) 2.38) #101-Ubuntu SMP Tue Nov 14 13:30:08 UTC 2023\n",
            permissions="r--r--r--",
        )

        # /proc/uptime
        self._create_file(
            "/proc/uptime",
            "2345678.90 9876543.21\n",
            permissions="r--r--r--",
        )

        # /proc/loadavg
        self._create_file(
            "/proc/loadavg",
            "0.08 0.12 0.09 2/142 1234\n",
            permissions="r--r--r--",
        )

        # /proc/mounts
        self._create_file(
            "/proc/mounts",
            """sysfs /sys sysfs rw,nosuid,nodev,noexec,relatime 0 0
proc /proc proc rw,nosuid,nodev,noexec,relatime 0 0
udev /dev devtmpfs rw,nosuid,relatime,size=2002484k,nr_inodes=500621,mode=755 0 0
devpts /dev/pts devpts rw,nosuid,noexec,relatime,gid=5,mode=620,ptmxmode=000 0 0
tmpfs /run tmpfs rw,nosuid,nodev,noexec,relatime,size=403920k,mode=755 0 0
/dev/sda1 / ext4 rw,relatime,errors=remount-ro 0 0
tmpfs /dev/shm tmpfs rw,nosuid,nodev 0 0
tmpfs /run/lock tmpfs rw,nosuid,nodev,noexec,relatime,size=5120k 0 0
tmpfs /sys/fs/cgroup tmpfs ro,nosuid,nodev,noexec,mode=755 0 0
""",
            permissions="r--r--r--",
        )

    def _create_dev_files(self) -> None:
        """Create realistic /dev device files."""
        devices = [
            "null",
            "zero",
            "random",
            "urandom",
            "tty",
            "console",
            "stdin",
            "stdout",
            "stderr",
            "sda",
            "sda1",
            "sda2",
        ]

        for device in devices:
            self._create_file(
                f"/dev/{device}",
                "",
                permissions="rw-rw-rw-",
            )

    def _create_log_files(self) -> None:
        """Create realistic log files with sample entries."""
        # Auth log with realistic entries
        self._create_file(
            "/var/log/auth.log",
            """Jan 02 10:15:23 ubuntu-web-01 sshd[1234]: Accepted password for admin from 192.168.1.100 port 54321 ssh2
Jan 02 10:15:23 ubuntu-web-01 sshd[1234]: pam_unix(sshd:session): session opened for user admin by (uid=0)
Jan 02 11:23:45 ubuntu-web-01 sshd[1456]: Accepted password for admin from 192.168.1.100 port 54567 ssh2
Jan 02 11:23:45 ubuntu-web-01 sshd[1456]: pam_unix(sshd:session): session opened for user admin by (uid=0)
Jan 02 12:30:01 ubuntu-web-01 CRON[1567]: pam_unix(cron:session): session opened for user root by (uid=0)
Jan 02 12:30:01 ubuntu-web-01 CRON[1567]: pam_unix(cron:session): session closed for user root
""",
            permissions="rw-r-----",
        )

        # Syslog with system messages
        self._create_file(
            "/var/log/syslog",
            """Jan 02 08:00:01 ubuntu-web-01 systemd[1]: Starting Daily apt download activities...
Jan 02 08:00:02 ubuntu-web-01 systemd[1]: apt-daily.service: Succeeded.
Jan 02 08:00:02 ubuntu-web-01 systemd[1]: Finished Daily apt download activities.
Jan 02 09:17:01 ubuntu-web-01 CRON[12345]: (root) CMD (   cd / && run-parts --report /etc/cron.hourly)
Jan 02 10:15:22 ubuntu-web-01 sshd[1234]: Connection from 192.168.1.100 port 54321
Jan 02 10:15:23 ubuntu-web-01 sshd[1234]: Accepted password for admin from 192.168.1.100 port 54321 ssh2
Jan 02 10:17:01 ubuntu-web-01 CRON[12456]: (root) CMD (   cd / && run-parts --report /etc/cron.hourly)
Jan 02 11:23:45 ubuntu-web-01 sshd[1456]: Accepted password for admin from 192.168.1.100 port 54567 ssh2
""",
            permissions="rw-r-----",
        )

        # Create nginx log directory and files
        self._create_dir("/var/log/nginx")
        self._create_file(
            "/var/log/nginx/access.log",
            """192.168.1.50 - - [02/Jan/2026:09:15:23 +0000] "GET / HTTP/1.1" 200 612 "-" "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
192.168.1.50 - - [02/Jan/2026:09:15:24 +0000] "GET /favicon.ico HTTP/1.1" 404 153 "http://localhost/" "Mozilla/5.0"
192.168.1.75 - - [02/Jan/2026:09:30:12 +0000] "GET /index.php HTTP/1.1" 200 1234 "-" "curl/7.68.0"
""",
            permissions="rw-r-----",
        )

        self._create_file(
            "/var/log/nginx/error.log",
            """2026/01/02 09:15:24 [error] 1234#1234: *1 open() "/var/www/html/favicon.ico" failed (2: No such file or directory)
""",
            permissions="rw-r-----",
        )

        # Kernel log
        self._create_file(
            "/var/log/kern.log",
            """Jan 02 00:00:15 ubuntu-web-01 kernel: [    0.000000] Linux version 5.15.0-91-generic (buildd@lcy02-amd64-089)
Jan 02 00:00:15 ubuntu-web-01 kernel: [    0.000000] Command line: BOOT_IMAGE=/boot/vmlinuz-5.15.0-91-generic root=UUID=12345
Jan 02 00:00:15 ubuntu-web-01 kernel: [    0.000000] KERNEL supported cpus:
""",
            permissions="rw-r-----",
        )

        # APT history
        self._create_dir("/var/log/apt")
        self._create_file(
            "/var/log/apt/history.log",
            """Start-Date: 2025-12-15  10:30:45
Commandline: apt upgrade
Upgrade: nginx-common:amd64 (1.18.0-0ubuntu1.4, 1.18.0-0ubuntu1.5), nginx-core:amd64 (1.18.0-0ubuntu1.4, 1.18.0-0ubuntu1.5)
End-Date: 2025-12-15  10:32:12

Start-Date: 2025-12-20  14:15:30
Commandline: apt install php8.1-fpm
Install: php8.1-fpm:amd64 (8.1.2-1ubuntu2.14), php8.1-common:amd64 (8.1.2-1ubuntu2.14)
End-Date: 2025-12-20  14:16:45
""",
            permissions="rw-r-----",
        )
