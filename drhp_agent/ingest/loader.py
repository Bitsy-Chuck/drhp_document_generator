"""Document discovery and loading.

Tasks 4.1-4.4: File discovery, validation, checksums, content reading.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from drhp_agent.core.exceptions import NotSupportedSourceTypeError


class DocumentLoader:
    """Discovers and loads markdown documents from a directory."""

    SUPPORTED_EXTENSIONS = {".md"}

    def __init__(self, base_path: str | Path):
        """Initialize loader with base path.

        Args:
            base_path: Directory to search for documents
        """
        self.base_path = Path(base_path)
        if not self.base_path.exists():
            raise FileNotFoundError(f"Directory not found: {base_path}")
        if not self.base_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {base_path}")

    def discover(self) -> list[Path]:
        """Recursively discover all markdown files.

        Returns:
            List of paths to markdown files

        Raises:
            NotSupportedSourceTypeError: If non-markdown files found
        """
        files = []
        for path in self.base_path.rglob("*"):
            if path.is_file():
                if path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    files.append(path)
                elif not path.name.startswith("."):
                    # Reject unsupported files (ignore hidden files)
                    raise NotSupportedSourceTypeError(
                        file_path=str(path),
                        detected_type=path.suffix,
                    )
        return sorted(files)

    def read(self, path: Path) -> str:
        """Read file content with encoding handling.

        Args:
            path: Path to file

        Returns:
            File content as string
        """
        encodings = ["utf-8", "utf-8-sig", "latin-1"]
        for encoding in encodings:
            try:
                return path.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise UnicodeDecodeError(
            "all",
            b"",
            0,
            1,
            f"Could not decode {path} with any supported encoding",
        )

    def checksum(self, path: Path) -> str:
        """Compute SHA-256 checksum of file.

        Args:
            path: Path to file

        Returns:
            Hex digest of checksum
        """
        content = path.read_bytes()
        return hashlib.sha256(content).hexdigest()

    def load_all(self) -> list[tuple[Path, str, str]]:
        """Discover and load all documents.

        Returns:
            List of (path, content, checksum) tuples
        """
        files = self.discover()
        return [(f, self.read(f), self.checksum(f)) for f in files]
