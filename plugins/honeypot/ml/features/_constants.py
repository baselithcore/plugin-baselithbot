"""Feature extraction constants."""

# Command categories for feature encoding
COMMAND_CATEGORIES = {
    "filesystem": {"ls", "cat", "head", "tail", "find", "grep", "less", "more", "tree"},
    "navigation": {"cd", "pwd", "pushd", "popd"},
    "file_ops": {"touch", "mkdir", "rm", "rmdir", "cp", "mv", "chmod", "chown"},
    "network": {
        "curl",
        "wget",
        "nc",
        "ncat",
        "ssh",
        "scp",
        "ping",
        "netstat",
        "ss",
        "ip",
        "ifconfig",
    },
    "process": {"ps", "top", "htop", "kill", "pkill", "pgrep", "jobs", "bg", "fg"},
    "system": {"uname", "hostname", "id", "whoami", "uptime", "w", "who", "last"},
    "user": {"useradd", "usermod", "userdel", "passwd", "su", "sudo"},
    "package": {"apt", "yum", "dnf", "pip", "npm", "gem"},
    "scripting": {"bash", "sh", "python", "perl", "ruby", "php", "awk", "sed"},
    "encoding": {"base64", "xxd", "od", "openssl"},
    "archive": {"tar", "zip", "unzip", "gzip", "gunzip", "bzip2"},
    "editor": {"vi", "vim", "nano", "emacs", "cat"},
}

# Suspicious patterns for feature extraction
SUSPICIOUS_PATTERNS = [
    r"base64\s+-d",  # Base64 decoding
    r"\|.*sh",  # Piping to shell
    r"chmod\s+\+x",  # Making executable
    r"wget.*\|.*sh",  # Download and execute
    r"curl.*\|.*sh",  # Download and execute
    r"/etc/shadow",  # Credential access
    r"/etc/passwd",  # User enumeration
    r"\.ssh/",  # SSH key access
    r"\.aws/",  # AWS credentials
    r"\.kube/",  # Kubernetes config
    r"nc\s+-[el]",  # Netcat listener/exec
    r"python\s+-c",  # Python one-liner
    r"bash\s+-i",  # Interactive bash
    r"rm\s+-rf",  # Dangerous deletion
    r">/dev/null",  # Output suppression
    r"2>&1",  # Error redirection
    r"history\s+-c",  # History clearing
    r"\.bash_history",  # History access
]
