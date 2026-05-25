"""Tests for Virtual Filesystem."""

import pytest
from plugins.honeypot.engine.virtual_filesystem import VirtualFilesystem


@pytest.fixture
def vfs():
    """Create a fresh virtual filesystem."""
    return VirtualFilesystem(username="testuser", hostname="test-server")


def test_initial_structure(vfs):
    """Test that filesystem initializes with realistic structure."""
    assert vfs.pwd() == "/home/testuser"
    assert vfs.exists("/home/testuser")
    assert vfs.exists("/etc/passwd")
    assert vfs.exists("/etc/hosts")
    assert vfs.is_directory("/home/testuser")
    assert vfs.is_file("/etc/passwd")


def test_pwd_cd(vfs):
    """Test pwd and cd commands."""
    assert vfs.pwd() == "/home/testuser"

    success, _ = vfs.cd("/etc")
    assert success
    assert vfs.pwd() == "/etc"

    success, _ = vfs.cd("..")
    assert success
    assert vfs.pwd() == "/"

    success, _ = vfs.cd("~")
    assert success
    assert vfs.pwd() == "/home/testuser"


def test_touch(vfs):
    """Test touch command."""
    assert not vfs.exists("test.txt")

    success, _ = vfs.touch("test.txt")
    assert success
    assert vfs.exists("test.txt")
    assert vfs.is_file("test.txt")

    # Touch again should just update timestamp
    success, _ = vfs.touch("test.txt")
    assert success


def test_mkdir(vfs):
    """Test mkdir command."""
    assert not vfs.exists("newdir")

    success, _ = vfs.mkdir("newdir")
    assert success
    assert vfs.exists("newdir")
    assert vfs.is_directory("newdir")

    # Can't create directory that exists
    success, error = vfs.mkdir("newdir")
    assert not success
    assert "exists" in error.lower()


def test_write_read_file(vfs):
    """Test writing and reading files."""
    content = "Hello, World!"

    success, _ = vfs.write_file("test.txt", content)
    assert success
    assert vfs.exists("test.txt")

    success, result = vfs.cat("test.txt")
    assert success
    assert result == content


def test_append_file(vfs):
    """Test appending to files."""
    vfs.write_file("test.txt", "Line 1\n")
    vfs.write_file("test.txt", "Line 2\n", append=True)

    success, content = vfs.cat("test.txt")
    assert success
    assert content == "Line 1\nLine 2\n"


def test_rm_file(vfs):
    """Test removing files."""
    vfs.touch("test.txt")
    assert vfs.exists("test.txt")

    success, _ = vfs.rm("test.txt")
    assert success
    assert not vfs.exists("test.txt")


def test_rm_directory(vfs):
    """Test removing directories."""
    vfs.mkdir("testdir")
    assert vfs.exists("testdir")

    # Can't remove directory without -r
    success, error = vfs.rm("testdir", recursive=False)
    assert not success
    assert "directory" in error.lower()

    # With -r it works
    success, _ = vfs.rm("testdir", recursive=True)
    assert success
    assert not vfs.exists("testdir")


def test_ls(vfs):
    """Test ls command."""
    success, output = vfs.ls()
    assert success
    assert "Documents" in output
    assert "Downloads" in output

    # Long format
    success, output = vfs.ls(long_format=True)
    assert success
    assert "drwxr-xr-x" in output


def test_ls_with_hidden(vfs):
    """Test ls -a command."""
    success, output = vfs.ls(all_files=False)
    assert success
    assert ".ssh" not in output  # Hidden file

    success, output = vfs.ls(all_files=True)
    assert success
    assert ".ssh" in output  # Now visible


def test_relative_paths(vfs):
    """Test relative path resolution."""
    vfs.mkdir("subdir")
    vfs.cd("subdir")
    assert vfs.pwd() == "/home/testuser/subdir"

    vfs.touch("test.txt")
    assert vfs.exists("test.txt")
    assert vfs.exists("/home/testuser/subdir/test.txt")


def test_parent_directory(vfs):
    """Test .. navigation."""
    vfs.mkdir("dir1")
    vfs.cd("dir1")
    vfs.mkdir("dir2")
    vfs.cd("dir2")

    assert vfs.pwd() == "/home/testuser/dir1/dir2"

    vfs.cd("..")
    assert vfs.pwd() == "/home/testuser/dir1"

    vfs.cd("..")
    assert vfs.pwd() == "/home/testuser"


def test_find(vfs):
    """Test find command."""
    vfs.mkdir("testdir")
    vfs.cd("testdir")
    vfs.touch("file1.txt")
    vfs.touch("file2.log")

    vfs.cd("..")

    success, output = vfs.find("testdir", "*.txt")
    assert success
    assert "file1.txt" in output
    assert "file2.log" not in output


def test_permissions(vfs):
    """Test permission simulation."""
    # Reading /etc/shadow should fail
    success, error = vfs.cat("/etc/shadow")
    assert not success
    assert "Permission denied" in error


def test_prompt_updates(vfs):
    """Test that prompt updates with directory changes."""
    prompt = vfs.get_prompt()
    assert "~$" in prompt

    vfs.cd("/etc")
    prompt = vfs.get_prompt()
    assert "/etc" in prompt


def test_complex_paths(vfs):
    """Test complex path operations."""
    # Create nested structure
    vfs.mkdir("a")
    vfs.cd("a")
    vfs.mkdir("b")
    vfs.cd("b")
    vfs.mkdir("c")

    assert vfs.exists("/home/testuser/a/b/c")
    assert vfs.pwd() == "/home/testuser/a/b"

    # Navigate with .. paths
    success, _ = vfs.cd("..")
    assert success
    assert vfs.pwd() == "/home/testuser/a"

    # Navigate to nested dir
    success, _ = vfs.cd("b/c")
    assert success
    assert vfs.pwd() == "/home/testuser/a/b/c"


def test_file_not_found(vfs):
    """Test error handling for non-existent files."""
    success, error = vfs.cat("nonexistent.txt")
    assert not success
    assert "No such file" in error

    success, error = vfs.cd("nonexistent")
    assert not success
    assert "No such file" in error


def test_redirection_simulation(vfs):
    """Test that files can be written like shell redirection."""
    # Simulate: echo "test" > output.txt
    vfs.write_file("output.txt", "test\n")

    success, content = vfs.cat("output.txt")
    assert success
    assert content == "test\n"

    # Simulate: echo "more" >> output.txt
    vfs.write_file("output.txt", "more\n", append=True)

    success, content = vfs.cat("output.txt")
    assert success
    assert content == "test\nmore\n"
