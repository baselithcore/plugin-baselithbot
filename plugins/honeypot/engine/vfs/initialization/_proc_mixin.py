"""Proc/dev/log files mixin for FilesystemInitializer."""


class ProcMixin:
    """Mixin providing _create_proc_files, _create_dev_files, _create_log_files."""

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
