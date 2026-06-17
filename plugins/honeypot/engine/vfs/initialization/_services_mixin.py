"""Service configs mixin for FilesystemInitializer."""


class ServicesMixin:
    """Mixin providing _create_service_configs method."""

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
