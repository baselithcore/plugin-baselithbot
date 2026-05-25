"""System information command implementations."""

import random
from datetime import datetime

from .base import CommandMixin


class SystemInfoCommands(CommandMixin):
    """System info commands (uname, uptime, ps, whoami, id, hostname, date)."""

    def _cmd_whoami(self, _args: list) -> str:
        return self.vfs.username

    def _cmd_id(self, args: list) -> str:
        """User identity with session-consistent UID."""
        username = self.vfs.username
        uid = self._uid

        if "-u" in args:
            return str(uid)
        if "-g" in args:
            return str(uid)
        if "-n" in args:
            return username

        groups = f"{uid}({username})"
        if uid == 1000:
            groups += ",27(sudo),4(adm)"
        elif uid == 1001:
            groups += ",27(sudo)"

        return f"uid={uid}({username}) gid={uid}({username}) groups={groups}"

    def _cmd_hostname(self, _args: list) -> str:
        return self.fingerprint.get("hostname", self.vfs.hostname)

    def _cmd_uname(self, args: list) -> str:
        if "-a" in args:
            return self.fingerprint.get(
                "kernel",
                "Linux ubuntu-server 5.4.0-42-generic #46-Ubuntu SMP x86_64 GNU/Linux",
            )
        elif "-m" in args:
            return "x86_64"
        elif "-r" in args:
            return "5.4.0-42-generic"
        elif "-s" in args:
            return "Linux"
        return "Linux"

    def _cmd_date(self, _args: list) -> str:
        return datetime.now().strftime("%a %b %d %H:%M:%S UTC %Y")

    def _cmd_uptime(self, _args: list) -> str:
        """Dynamic uptime based on simulated boot time."""
        now = datetime.now()
        delta = now - self._boot_time
        days = delta.days
        hours = delta.seconds // 3600
        mins = (delta.seconds % 3600) // 60

        time_str = now.strftime("%H:%M:%S")
        up_str = (
            f"{days} days, {hours:2d}:{mins:02d}"
            if days > 0
            else f"{hours:2d}:{mins:02d}"
        )

        # Slight variation in load avg
        l1 = round(self._load_avg[0] + random.uniform(-0.02, 0.03), 2)
        l5 = round(self._load_avg[1] + random.uniform(-0.01, 0.02), 2)
        l15 = round(self._load_avg[2] + random.uniform(-0.01, 0.01), 2)

        users = random.choice([1, 1, 1, 2])
        return f" {time_str} up {up_str},  {users} user,  load average: {l1:.2f}, {l5:.2f}, {l15:.2f}"

    def _cmd_ps(self, args: list) -> str:
        """Dynamic process listing."""
        username = self.vfs.username
        pid_base = self._pid_base

        full_format = "aux" in "".join(args) or "-ef" in args or "-e" in args

        if full_format:
            boot_str = self._boot_time.strftime("%b%d")
            now_str = datetime.now().strftime("%H:%M")

            lines = [
                "USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND",
                f"root         1  0.0  0.1 169236 11920 ?        Ss   {boot_str}   0:08 /sbin/init",
                f"root         2  0.0  0.0      0     0 ?        S    {boot_str}   0:00 [kthreadd]",
                f"root       {random.randint(200, 400)}  0.0  0.0      0     0 ?        I<   {boot_str}   0:00 [kworker/0:1H]",
                f"root       {random.randint(450, 650)}  0.0  0.2  72308  6420 ?        Ss   {boot_str}   0:01 /usr/sbin/sshd -D",
                f"root       {random.randint(700, 850)}  0.0  0.1 107984  5624 ?        Ss   {boot_str}   0:00 /usr/sbin/cron -f",
                f"syslog     {random.randint(500, 680)}  0.0  0.1 224344  4816 ?        Ssl  {boot_str}   0:02 /usr/sbin/rsyslogd -n",
                f"{username}  {pid_base}  0.0  0.1  21464  5080 ?        Ss   {now_str}   0:00 sshd: {username}@pts/0",
                f"{username}  {pid_base + 1}  0.0  0.0  10068  1620 pts/0    Ss   {now_str}   0:00 -bash",
                f"{username}  {pid_base + random.randint(15, 45)}  0.0  0.0  11492  1016 pts/0    R+   {now_str}   0:00 ps aux",
            ]
            return "\n".join(lines)

        return f"""  PID TTY          TIME CMD
{pid_base + 1} pts/0    00:00:00 bash
{pid_base + random.randint(15, 45)} pts/0    00:00:00 ps"""
