"""Advanced monitoring and troubleshooting commands."""

from typing import List
from .base import BaseCommands


class MonitoringCommands(BaseCommands):
    """Advanced system monitoring and network troubleshooting commands."""

    def _cmd_netstat(self, args: List[str]) -> str:
        """Handle netstat command."""
        # Parse options
        show_listening = "-l" in args or "-a" in args
        show_all = "-a" in args
        # show_numeric = "-n" in args
        show_programs = "-p" in args

        if show_listening or show_all:
            output = "Active Internet connections (servers and established)\n"
            output += "Proto Recv-Q Send-Q Local Address           Foreign Address         State"
            if show_programs:
                output += "       PID/Program name"
            output += "\n"

            # Listening services
            services = [
                ("tcp", "0.0.0.0:22", "0.0.0.0:*", "LISTEN", "1220/sshd"),
                ("tcp", "127.0.0.1:3306", "0.0.0.0:*", "LISTEN", "1250/mysqld"),
                ("tcp", "0.0.0.0:80", "0.0.0.0:*", "LISTEN", "1236/nginx"),
                ("tcp", "0.0.0.0:443", "0.0.0.0:*", "LISTEN", "1236/nginx"),
                ("tcp6", ":::22", ":::*", "LISTEN", "1220/sshd"),
                ("tcp6", ":::80", ":::*", "LISTEN", "1236/nginx"),
            ]

            for proto, local, foreign, state, pid in services:
                line = f"{proto:6} 0      0      {local:23} {foreign:23} {state:11}"
                if show_programs:
                    line += f" {pid}"
                output += line + "\n"

            # Established connections
            if show_all:
                established = [
                    (
                        "tcp",
                        "10.0.2.15:22",
                        "192.168.1.100:54321",
                        "ESTABLISHED",
                        "1234/sshd",
                    ),
                    (
                        "tcp",
                        "10.0.2.15:80",
                        "192.168.1.50:45678",
                        "ESTABLISHED",
                        "1237/nginx",
                    ),
                ]

                for proto, local, foreign, state, pid in established:
                    line = f"{proto:6} 0      0      {local:23} {foreign:23} {state:11}"
                    if show_programs:
                        line += f" {pid}"
                    output += line + "\n"

            return output

        return "Active Internet connections (w/o servers)\nProto Recv-Q Send-Q Local Address           Foreign Address         State"

    def _cmd_ss(self, args: List[str]) -> str:
        """Handle ss command (modern netstat replacement)."""
        # Parse options
        show_listening = "-l" in args or "-a" in args
        show_all = "-a" in args
        # show_numeric = "-n" in args
        show_processes = "-p" in args
        show_tcp = "-t" in args or len(args) == 0
        show_udp = "-u" in args

        output = "Netid  State      Recv-Q Send-Q Local Address:Port        Peer Address:Port"
        if show_processes:
            output += "        Process"
        output += "\n"

        if show_tcp or not show_udp:
            # TCP listening
            if show_listening or show_all:
                tcp_services = [
                    (
                        "tcp",
                        "LISTEN",
                        "0.0.0.0:22",
                        "0.0.0.0:*",
                        'users:(("sshd",pid=1220,fd=3))',
                    ),
                    (
                        "tcp",
                        "LISTEN",
                        "127.0.0.1:3306",
                        "0.0.0.0:*",
                        'users:(("mysqld",pid=1250,fd=21))',
                    ),
                    (
                        "tcp",
                        "LISTEN",
                        "0.0.0.0:80",
                        "0.0.0.0:*",
                        'users:(("nginx",pid=1236,fd=6))',
                    ),
                    (
                        "tcp",
                        "LISTEN",
                        "0.0.0.0:443",
                        "0.0.0.0:*",
                        'users:(("nginx",pid=1236,fd=7))',
                    ),
                ]

                for proto, state, local, peer, process in tcp_services:
                    line = f"{proto:7} {state:10} 0      0      {local:20} {peer:20}"
                    if show_processes:
                        line += f" {process}"
                    output += line + "\n"

            # TCP established
            if show_all:
                tcp_established = [
                    (
                        "tcp",
                        "ESTAB",
                        "10.0.2.15:22",
                        "192.168.1.100:54321",
                        'users:(("sshd",pid=1234,fd=3))',
                    ),
                ]

                for proto, state, local, peer, process in tcp_established:
                    line = f"{proto:7} {state:10} 0      0      {local:20} {peer:20}"
                    if show_processes:
                        line += f" {process}"
                    output += line + "\n"

        return output

    def _cmd_lsof(self, args: List[str]) -> str:
        """Handle lsof command (list open files)."""
        if "-i" in args:
            # Network connections
            return """COMMAND    PID     USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
sshd      1220     root    3u  IPv4  12345      0t0  TCP *:ssh (LISTEN)
sshd      1220     root    4u  IPv6  12346      0t0  TCP *:ssh (LISTEN)
nginx     1236 www-data    6u  IPv4  12347      0t0  TCP *:http (LISTEN)
nginx     1236 www-data    7u  IPv4  12348      0t0  TCP *:https (LISTEN)
mysqld    1250    mysql   21u  IPv4  12349      0t0  TCP localhost:mysql (LISTEN)
sshd      1234     root    3u  IPv4  12350      0t0  TCP ubuntu-web-01:ssh->192.168.1.100:54321 (ESTABLISHED)"""

        # Show all open files (truncated)
        return """COMMAND     PID   USER   FD      TYPE             DEVICE SIZE/OFF       NODE NAME
systemd       1   root  cwd       DIR                8,1     4096          2 /
systemd       1   root  rtd       DIR                8,1     4096          2 /
systemd       1   root  txt       REG                8,1  1620224     262186 /usr/lib/systemd/systemd
sshd       1220   root  cwd       DIR                8,1     4096          2 /
sshd       1220   root  txt       REG                8,1   876432     393283 /usr/sbin/sshd
nginx      1236   root  cwd       DIR                8,1     4096          2 /
nginx      1236   root  txt       REG                8,1  1442600     393452 /usr/sbin/nginx
mysqld     1250  mysql  cwd       DIR                8,1     4096     524386 /var/lib/mysql"""

    def _cmd_iostat(self, args: List[str]) -> str:
        """Handle iostat command."""
        return """Linux 5.15.0-91-generic (ubuntu-web-01)     01/02/2026      _x86_64_        (4 CPU)

avg-cpu:  %user   %nice %system %iowait  %steal   %idle
           2.34    0.00    0.89    0.12    0.00   96.65

Device             tps    kB_read/s    kB_wrtn/s    kB_read    kB_wrtn
sda               4.23       123.45        67.89    2345678    1234567"""

    def _cmd_vmstat(self, args: List[str]) -> str:
        """Handle vmstat command."""
        return """procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
 r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
 1  0      0 1234568 234567 1234567  0    0    12    34  567  890  2  1 97  0  0"""

    def _cmd_free(self, args: List[str]) -> str:
        """Handle free command."""
        show_human = "-h" in args or "-m" in args

        if show_human:
            return """              total        used        free      shared  buff/cache   available
Mem:           3.9G        934M        1.2G         12M        1.8G        3.0G
Swap:          2.0G          0B        2.0G"""
        else:
            return """              total        used        free      shared  buff/cache   available
Mem:        4039172      934568     1234568       12345     1870036     3123456
Swap:       2097148           0     2097148"""

    def _cmd_df(self, args: List[str]) -> str:
        """Handle df command."""
        show_human = "-h" in args

        if show_human:
            return """Filesystem      Size  Used Avail Use% Mounted on
/dev/sda1        20G  6.9G   12G  37% /
tmpfs           2.0G     0  2.0G   0% /dev/shm
tmpfs           395M  1.2M  394M   1% /run
tmpfs           5.0M     0  5.0M   0% /run/lock
tmpfs           2.0G     0  2.0G   0% /sys/fs/cgroup"""
        else:
            return """Filesystem     1K-blocks     Used Available Use% Mounted on
/dev/sda1       20511356  6891234  13620122  34% /
tmpfs            2019588        0   2019588   0% /dev/shm
tmpfs             403920     1156    402764   1% /run
tmpfs               5120        0      5120   0% /run/lock
tmpfs            2019588        0   2019588   0% /sys/fs/cgroup"""

    def _cmd_du(self, args: List[str]) -> str:
        """Handle du command."""
        show_human = "-h" in args
        show_summary = "-s" in args

        path = "."
        for arg in args:
            if not arg.startswith("-"):
                path = arg
                break

        if show_summary:
            if show_human:
                return f"6.9G\t{path}"
            else:
                return f"6891234\t{path}"

        # Show directory sizes
        if show_human:
            return """123M    ./home
456M    ./var
234M    ./usr
89M     ./etc
12M     ./tmp
6.9G    ."""
        else:
            return """123456  ./home
456789  ./var
234567  ./usr
89012   ./etc
12345   ./tmp
6891234 ."""

    def _cmd_top(self, args: List[str]) -> str:
        """Handle top command."""
        return """top - 12:34:56 up 24 days,  4:33,  1 user,  load average: 0.08, 0.12, 0.09
Tasks: 142 total,   1 running, 141 sleeping,   0 stopped,   0 zombie
%Cpu(s):  2.3 us,  0.9 sy,  0.0 ni, 96.7 id,  0.1 wa,  0.0 hi,  0.0 si,  0.0 st
MiB Mem :   3944.5 total,   1234.5 free,    934.6 used,   1775.4 buff/cache
MiB Swap:   2048.0 total,   2048.0 free,      0.0 used.   3123.5 avail Mem

    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
   1250 mysql     20   0 1876432 345678  23456 S   1.3   8.6   5:23.45 mysqld
   1236 www-data  20   0  345678  45678  12345 S   0.7   1.1   2:34.56 nginx
   1220 root      20   0  234567  12345   8901 S   0.3   0.3   0:45.67 sshd
   1234 root      20   0  123456   9876   5432 S   0.0   0.2   0:01.23 sshd
      1 root      20   0  167892   9876   6543 S   0.0   0.2   0:12.34 systemd
   1200 root      20   0   23456   2345   2000 S   0.0   0.1   0:00.45 cron"""

    def _cmd_htop(self, args: List[str]) -> str:
        """Handle htop command."""
        return """htop requires terminal mode. Use 'top' instead or install htop.
Alternatively, showing simplified process list:

  CPU[|||||                                              8.2%]   Tasks: 142, 234 thr; 1 running
  Mem[|||||||||||||||                              934M/3.9G]   Load average: 0.08 0.12 0.09
  Swp[                                                0K/2.0G]   Uptime: 24 days, 04:33:21

    PID USER      PRI  NI  VIRT   RES   SHR S CPU% MEM%   TIME+  Command
   1250 mysql      20   0 1827M  337M 22.9M S  1.3  8.6  5:23.45 /usr/sbin/mysqld
   1236 www-data   20   0  337M 44.6M 12.1M S  0.7  1.1  2:34.56 nginx: worker process
   1220 root       20   0  229M 12.1M 8.7M  S  0.3  0.3  0:45.67 sshd: /usr/sbin/sshd -D"""

    def _cmd_iotop(self, args: List[str]) -> str:
        """Handle iotop command."""
        return """Total DISK READ :       2.34 M/s | Total DISK WRITE :       1.23 M/s
Actual DISK READ:       2.34 M/s | Actual DISK WRITE:       1.23 M/s
    TID  PRIO  USER     DISK READ  DISK WRITE  SWAPIN     IO>    COMMAND
   1250 be/4 mysql       2.12 M/s    1.01 M/s  0.00 % 12.34 % mysqld
   1236 be/4 www-data    0.22 M/s    0.22 M/s  0.00 %  1.23 % nginx
      1 be/4 root        0.00 B/s    0.00 B/s  0.00 %  0.00 % systemd"""

    def _cmd_dmesg(self, args: List[str]) -> str:
        """Handle dmesg command."""
        return """[    0.000000] Linux version 5.15.0-91-generic (buildd@lcy02-amd64-089)
[    0.000000] Command line: BOOT_IMAGE=/boot/vmlinuz-5.15.0-91-generic root=UUID=12345678
[    0.000000] KERNEL supported cpus:
[    0.000000]   Intel GenuineIntel
[    0.000000]   AMD AuthenticAMD
[    1.234567] Freeing SMP alternatives memory: 36K
[    1.345678] smpboot: CPU0: Intel(R) Core(TM) i5-8250U CPU @ 1.60GHz
[    2.456789] smp: Bringing up secondary CPUs ...
[    3.567890] smp: Brought up 1 node, 4 CPUs
[   12.345678] EXT4-fs (sda1): mounted filesystem with ordered data mode
[   15.678901] systemd[1]: Started OpenBSD Secure Shell server.
[   16.789012] nginx: configuration file /etc/nginx/nginx.conf test is successful"""

    def _cmd_strace(self, args: List[str]) -> str:
        """Handle strace command."""
        if not args:
            return "usage: strace [-CdffhiqrtttTvVwxxy] [-I n] [-e expr]..."

        return """strace: attach: ptrace(PTRACE_SEIZE, 1234): Operation not permitted
Could not attach to process.  If your uid matches the uid of the target
process, check the setting of /proc/sys/kernel/yama/ptrace_scope, or try
again as the root user."""

    def _cmd_tcpdump(self, args: List[str]) -> str:
        """Handle tcpdump command."""
        return """tcpdump: eth0: You don't have permission to capture on that device
(socket: Operation not permitted)"""

    def _cmd_iftop(self, args: List[str]) -> str:
        """Handle iftop command."""
        return """interface: eth0
IP address is: 10.0.2.15
MAC address is: 08:00:27:12:34:56

   10.0.2.15        =>  192.168.1.100               1.23Kb  2.34Kb  1.56Kb
                    <=                              4.56Kb  5.67Kb  3.45Kb
   10.0.2.15        =>  8.8.8.8                      234b    567b    345b
                    <=                               456b    678b    456b

TX:             cum:   12.3KB   peak:   34.5Kb                    rates:   1.45Kb  2.56Kb  1.78Kb
RX:                    45.6KB           67.8Kb                             5.67Kb  6.78Kb  4.56Kb
TOTAL:                 57.9KB            102Kb                             7.12Kb  9.34Kb  6.34Kb"""

    def _cmd_sar(self, args: List[str]) -> str:
        """Handle sar command (system activity reporter)."""
        return """Linux 5.15.0-91-generic (ubuntu-web-01)     01/02/2026      _x86_64_        (4 CPU)

12:00:01 PM     CPU     %user     %nice   %system   %iowait    %steal     %idle
12:10:01 PM     all      2.34      0.00      0.89      0.12      0.00     96.65
12:20:01 PM     all      2.45      0.00      0.95      0.15      0.00     96.45
12:30:01 PM     all      2.12      0.00      0.78      0.08      0.00     97.02
Average:        all      2.30      0.00      0.87      0.12      0.00     96.71"""

    def _cmd_nmap(self, args: List[str]) -> str:
        """Handle nmap command."""
        if not args:
            return """Nmap 7.80 ( https://nmap.org )
Usage: nmap [Scan Type(s)] [Options] {target specification}"""

        target = args[-1] if args else "localhost"
        return f"""Starting Nmap 7.80 ( https://nmap.org ) at {self._get_current_time()}
Nmap scan report for {target}
Host is up (0.00012s latency).
Not shown: 997 closed ports
PORT     STATE SERVICE
22/tcp   open  ssh
80/tcp   open  http
3306/tcp open  mysql

Nmap done: 1 IP address (1 host up) scanned in 0.23 seconds"""

    def _cmd_lscpu(self, args: List[str]) -> str:
        """Handle lscpu command."""
        return """Architecture:                    x86_64
CPU op-mode(s):                  32-bit, 64-bit
Byte Order:                      Little Endian
Address sizes:                   39 bits physical, 48 bits virtual
CPU(s):                          4
On-line CPU(s) list:             0-3
Thread(s) per core:              1
Core(s) per socket:              4
Socket(s):                       1
NUMA node(s):                    1
Vendor ID:                       GenuineIntel
CPU family:                      6
Model:                           142
Model name:                      Intel(R) Core(TM) i5-8250U CPU @ 1.60GHz
Stepping:                        10
CPU MHz:                         1800.000
BogoMIPS:                        3600.00
Hypervisor vendor:               KVM
Virtualization type:             full
L1d cache:                       128 KiB
L1i cache:                       128 KiB
L2 cache:                        1 MiB
L3 cache:                        6 MiB
NUMA node0 CPU(s):               0-3"""

    def _cmd_lsblk(self, args: List[str]) -> str:
        """Handle lsblk command."""
        return """NAME   MAJ:MIN RM  SIZE RO TYPE MOUNTPOINT
sda      8:0    0   20G  0 disk
├─sda1   8:1    0   19G  0 part /
├─sda2   8:2    0    1K  0 part
└─sda5   8:5    0  2.0G  0 part [SWAP]
sr0     11:0    1 1024M  0 rom"""

    def _cmd_lspci(self, args: List[str]) -> str:
        """Handle lspci command."""
        return """00:00.0 Host bridge: Intel Corporation 440FX - 82441FX PMC [Natoma] (rev 02)
00:01.0 ISA bridge: Intel Corporation 82371SB PIIX3 ISA [Natoma/Triton II]
00:01.1 IDE interface: Intel Corporation 82371AB/EB/MB PIIX4 IDE (rev 01)
00:02.0 VGA compatible controller: InnoTek Systemberatung GmbH VirtualBox Graphics Adapter
00:03.0 Ethernet controller: Intel Corporation 82540EM Gigabit Ethernet Controller (rev 02)
00:04.0 System peripheral: InnoTek Systemberatung GmbH VirtualBox Guest Service
00:05.0 Multimedia audio controller: Intel Corporation 82801AA AC'97 Audio Controller (rev 01)
00:06.0 USB controller: Apple Inc. KeyLargo/Intrepid USB
00:07.0 Bridge: Intel Corporation 82371AB/EB/MB PIIX4 ACPI (rev 08)"""

    def _cmd_lsusb(self, args: List[str]) -> str:
        """Handle lsusb command."""
        return """Bus 001 Device 001: ID 1d6b:0001 Linux Foundation 1.1 root hub
Bus 002 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub"""

    def _get_current_time(self) -> str:
        """Get current time in readable format."""
        from datetime import datetime

        return datetime.now().strftime("%Y-%m-%d %H:%M %Z")
