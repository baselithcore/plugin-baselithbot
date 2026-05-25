"""Path manipulation utilities for virtual filesystem."""


class PathUtilsMixin:
    """Mixin providing path manipulation utilities."""

    def _normalize_path(self, path: str) -> str:
        """Normalize path (resolve relative paths, .., .).

        Args:
            path: Path to normalize

        Returns:
            Normalized absolute path
        """
        if not path.startswith("/"):
            # Relative path
            path = f"{self.current_dir}/{path}"

        # Resolve path components
        parts = []
        for part in path.split("/"):
            if part == "" or part == ".":
                continue
            elif part == "..":
                if parts:
                    parts.pop()
            else:
                parts.append(part)

        return "/" + "/".join(parts) if parts else "/"

    def _get_parent_path(self, path: str) -> str:
        """Get parent directory path.

        Args:
            path: File or directory path

        Returns:
            Parent directory path
        """
        path = self._normalize_path(path)
        if path == "/":
            return "/"
        return "/".join(path.split("/")[:-1]) or "/"

    def _get_filename(self, path: str) -> str:
        """Get filename from path.

        Args:
            path: Full path

        Returns:
            Filename component
        """
        return path.split("/")[-1]
