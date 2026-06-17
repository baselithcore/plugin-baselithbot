"""Package management (apt, dpkg) mixin for SystemManagementCommands."""

from typing import List


class PackagesMixin:
    """Methods handling apt and dpkg commands."""

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
Setting up package (1.0.0-1) .."""

        return f"dpkg: error: unknown option {action}"
