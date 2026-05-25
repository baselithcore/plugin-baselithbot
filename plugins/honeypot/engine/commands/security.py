"""Security and privilege-related commands (sudo, su, etc.)."""

from typing import List
from .base import BaseCommands


class SecurityCommands(BaseCommands):
    """Security and privilege escalation commands."""

    def _cmd_sudo(self, args: List[str]) -> str:
        """Handle sudo command."""
        if not args:
            return """usage: sudo -h | -K | -k | -V
usage: sudo -v [-AknS] [-g group] [-h host] [-p prompt] [-u user]
usage: sudo -l [-AknS] [-g group] [-h host] [-p prompt] [-U user] [-u user] [command]
usage: sudo [-AbEHknPS] [-r role] [-t type] [-C num] [-g group] [-h host] [-p prompt] [-T timeout] [-u user] [VAR=value] [-i|-s] [<command>]
usage: sudo -e [-AknS] [-r role] [-t type] [-C num] [-g group] [-h host] [-p prompt] [-T timeout] [-u user] file ..."""

        # Parse sudo options
        user = "root"
        interactive = False
        command_args = []

        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "-u" and i + 1 < len(args):
                user = args[i + 1]
                i += 2
            elif arg == "-i":
                interactive = True
                i += 1
            elif arg == "-s":
                interactive = True
                i += 1
            elif arg == "-l":
                # List user privileges
                return self._sudo_list()
            elif arg == "-v":
                # Validate credentials
                return ""  # Success, no output
            elif arg == "-k":
                # Invalidate credentials
                return ""
            elif not arg.startswith("-"):
                command_args = args[i:]
                break
            else:
                i += 1

        # If interactive shell requested
        if interactive:
            return f"[sudo] password for {self.vfs.username}: \n# (Interactive shell - type 'exit' to return)"

        # If no command specified
        if not command_args:
            return "sudo: a password is required"

        # Simulate password prompt (in real honeypot, this would be interactive)
        # For now, we pretend the password was entered correctly

        # Execute the command as root
        command = " ".join(command_args)

        # Handle common sudo commands
        if command.startswith("su"):
            return self._cmd_su(command_args[1:] if len(command_args) > 1 else [])

        # Special handling for certain commands
        if command_args[0] in ("apt", "apt-get", "systemctl", "service"):
            # These would be handled by their respective command handlers
            # For now, simulate successful execution
            return f"[sudo] executing: {command}\n(Command would execute with root privileges)"

        # Simulate command execution with root privileges
        return f"[sudo] password for {self.vfs.username}: \n(Command '{command}' executed as {user})"

    def _sudo_list(self) -> str:
        """List sudo privileges."""
        username = self.vfs.username
        return f"""[sudo] password for {username}:
Matching Defaults entries for {username} on ubuntu-web-01:
    env_reset, mail_badpass,
    secure_path=/usr/local/sbin\\:/usr/local/bin\\:/usr/sbin\\:/usr/bin\\:/sbin\\:/bin\\:/snap/bin,
    use_pty

User {username} may run the following commands on ubuntu-web-01:
    (ALL : ALL) ALL"""

    def _cmd_su(self, args: List[str]) -> str:
        """Handle su (switch user) command."""
        target_user = "root"

        if args and not args[0].startswith("-"):
            target_user = args[0]

        # Simulate password prompt
        return f"Password: \n{target_user}@{self.vfs.hostname}:~# (Switched to {target_user} - type 'exit' to return)"

    def _cmd_sudo_su(self, args: List[str]) -> str:
        """Handle 'sudo su' command combination."""
        return "[sudo] password for admin: \nroot@ubuntu-web-01:~# (Root shell - type 'exit' to return)"

    def _cmd_visudo(self, args: List[str]) -> str:
        """Handle visudo command."""
        return """visudo: /etc/sudoers busy, try again later"""

    def _cmd_passwd(self, args: List[str]) -> str:
        """Handle passwd command."""
        if not args:
            # Change own password
            return f"""Changing password for {self.vfs.username}.
Current password:
New password:
Retype new password:
passwd: password updated successfully"""

        # Change another user's password (requires root)
        target_user = args[0]
        return f"""passwd: You may not view or modify password information for {target_user}."""

    def _cmd_chage(self, args: List[str]) -> str:
        """Handle chage (password aging) command."""
        if not args or args[0] in ("-h", "--help"):
            return """Usage: chage [options] LOGIN

Options:
  -d, --lastday LAST_DAY        set date of last password change to LAST_DAY
  -E, --expiredate EXPIRE_DATE  set account expiration date to EXPIRE_DATE
  -h, --help                    display this help message and exit
  -I, --inactive INACTIVE       set password inactive after expiration
  -l, --list                    show account aging information
  -m, --mindays MIN_DAYS        set minimum number of days before password
  -M, --maxdays MAX_DAYS        set maximum number of days before password"""

        if "-l" in args or "--list" in args:
            # user = args[-1] if len(args) > 1 else self.vfs.username
            return """Last password change					: Jan 02, 2026
Password expires					: never
Password inactive					: never
Account expires						: never
Minimum number of days between password change		: 0
Maximum number of days between password change		: 99999
Number of days of warning before password expires	: 7"""

        return "chage: Permission denied."

    def _cmd_usermod(self, args: List[str]) -> str:
        """Handle usermod command."""
        if not args:
            return """Usage: usermod [options] LOGIN

Options:
  -a, --append                  append the user to the supplemental GROUPS
  -c, --comment COMMENT         new value of the GECOS field
  -d, --home HOME_DIR           new home directory for the user account
  -e, --expiredate EXPIRE_DATE  set account expiration date to EXPIRE_DATE
  -g, --gid GROUP               force use GROUP as new primary group
  -G, --groups GROUPS           new list of supplementary GROUPS
  -l, --login NEW_LOGIN         new value of the login name
  -L, --lock                    lock the user account
  -s, --shell SHELL             new login shell for the user account
  -u, --uid UID                 new UID for the user account
  -U, --unlock                  unlock the user account"""

        return "usermod: Permission denied."

    def _cmd_useradd(self, args: List[str]) -> str:
        """Handle useradd command."""
        if not args:
            return """Usage: useradd [options] LOGIN
       useradd -D
       useradd -D [options]

Options:
  -b, --base-dir BASE_DIR       base directory for the home directory
  -c, --comment COMMENT         GECOS field of the new account
  -d, --home-dir HOME_DIR       home directory of the new account
  -D, --defaults                print or change default useradd configuration
  -e, --expiredate EXPIRE_DATE  expiration date of the new account
  -g, --gid GROUP               name or ID of the primary group
  -G, --groups GROUPS           list of supplementary groups
  -m, --create-home             create the user's home directory
  -s, --shell SHELL             login shell of the new account
  -u, --uid UID                 user ID of the new account"""

        return "useradd: Permission denied."

    def _cmd_userdel(self, args: List[str]) -> str:
        """Handle userdel command."""
        if not args:
            return """Usage: userdel [options] LOGIN

Options:
  -f, --force                   force removal of files,
                                even if not owned by user
  -h, --help                    display this help message and exit
  -r, --remove                  remove home directory and mail spool"""

        return "userdel: Permission denied."

    def _cmd_groupadd(self, args: List[str]) -> str:
        """Handle groupadd command."""
        if not args:
            return """Usage: groupadd [options] GROUP

Options:
  -f, --force                   exit successfully if the group already exists
  -g, --gid GID                 use GID for the new group
  -h, --help                    display this help message and exit
  -K, --key KEY=VALUE           override /etc/login.defs defaults
  -o, --non-unique              allow to create groups with duplicate GID
  -r, --system                  create a system account"""

        return "groupadd: Permission denied."

    def _cmd_adduser(self, args: List[str]) -> str:
        """Handle adduser command (Debian/Ubuntu wrapper)."""
        if not args:
            return """adduser [--home DIR] [--shell SHELL] [--no-create-home] [--uid ID]
[--firstuid ID] [--lastuid ID] [--gecos GECOS] [--ingroup GROUP | --gid ID]
[--disabled-password] [--disabled-login] [--encrypt-home] USER
   Add a normal user"""

        username = args[-1]
        return f"""Adding user `{username}' ...
adduser: Only root may add a user or group to the system."""
