"""
Repository security guard.
Enforces limits, sanitizes archive extraction, and prevents path traversal vulnerabilities.
"""
import os
import zipfile
import tarfile
from typing import Tuple

MAX_ARCHIVE_BYTES = 25 * 1024 * 1024       # 25 MB
MAX_UNCOMPRESSED_BYTES = 75 * 1024 * 1024  # 75 MB
MAX_FILE_COUNT = 1000
MAX_SINGLE_FILE_BYTES = 10 * 1024 * 1024   # 10 MB

class SecurityValidationError(Exception):
    pass

class RepoSecurityGuard:
    @staticmethod
    def is_safe_path(base_dir: str, target_path: str) -> bool:
        """
        Ensures target_path resolves strictly within base_dir, preventing path traversal.
        """
        base = os.path.abspath(base_dir)
        target = os.path.abspath(target_path)
        return target.startswith(base) and not os.path.relpath(target, base).startswith("..")

    @classmethod
    def safe_extract_zip(cls, zip_path: str, extract_to: str) -> Tuple[int, int]:
        """
        Safely extracts a zip archive enforcing limits and preventing Zip Slip.
        Returns (file_count, total_uncompressed_bytes).
        """
        if not os.path.exists(zip_path):
            raise SecurityValidationError("Archive file does not exist")

        archive_size = os.path.getsize(zip_path)
        if archive_size > MAX_ARCHIVE_BYTES:
            raise SecurityValidationError(f"Archive exceeds maximum size limit of {MAX_ARCHIVE_BYTES // (1024*1024)}MB")

        dest_dir = os.path.abspath(extract_to)
        os.makedirs(dest_dir, exist_ok=True)

        file_count = 0
        total_bytes = 0

        with zipfile.ZipFile(zip_path, "r") as zf:
            for member in zf.infolist():
                # Check path traversal
                member_path = os.path.normpath(member.filename)
                if member_path.startswith("/") or member_path.startswith("\\") or ".." in member_path.split(os.sep):
                    raise SecurityValidationError(f"Unsafe archive entry detected (path traversal): {member.filename}")

                target_dest = os.path.join(dest_dir, member_path)
                if not cls.is_safe_path(dest_dir, target_dest):
                    raise SecurityValidationError(f"Target path escapes extraction directory: {member.filename}")

                # Reject dangerous symlinks or device files
                # Note: upper 16 bits of external_attr represent unix file mode
                unix_mode = member.external_attr >> 16
                if (unix_mode & 0o170000) == 0o120000:  # Symlink
                    raise SecurityValidationError(f"Symbolic links are prohibited in repository archive: {member.filename}")

                file_count += 1
                if file_count > MAX_FILE_COUNT:
                    raise SecurityValidationError(f"Archive exceeds maximum file count limit of {MAX_FILE_COUNT}")

                if member.file_size > MAX_SINGLE_FILE_BYTES:
                    raise SecurityValidationError(f"File {member.filename} exceeds maximum single file size of {MAX_SINGLE_FILE_BYTES // (1024*1024)}MB")

                total_bytes += member.file_size
                if total_bytes > MAX_UNCOMPRESSED_BYTES:
                    raise SecurityValidationError(f"Uncompressed archive exceeds total limit of {MAX_UNCOMPRESSED_BYTES // (1024*1024)}MB")

            zf.extractall(dest_dir)

        return file_count, total_bytes

    @classmethod
    def safe_extract_tar(cls, tar_path: str, extract_to: str) -> Tuple[int, int]:
        """
        Safely extracts tar.gz archive enforcing limits and preventing traversal.
        """
        if not os.path.exists(tar_path):
            raise SecurityValidationError("Archive file does not exist")

        archive_size = os.path.getsize(tar_path)
        if archive_size > MAX_ARCHIVE_BYTES:
            raise SecurityValidationError("Archive exceeds maximum allowed size")

        dest_dir = os.path.abspath(extract_to)
        os.makedirs(dest_dir, exist_ok=True)

        file_count = 0
        total_bytes = 0

        with tarfile.open(tar_path, "r:*") as tf:
            for member in tf.getmembers():
                if member.islnk() or member.issym():
                    raise SecurityValidationError(f"Hardlinks and symlinks prohibited in archives: {member.name}")

                if member.name.startswith("/") or ".." in member.name.split("/"):
                    raise SecurityValidationError(f"Unsafe tar entry path traversal: {member.name}")

                target_dest = os.path.join(dest_dir, member.name)
                if not cls.is_safe_path(dest_dir, target_dest):
                    raise SecurityValidationError(f"Tar entry escapes extraction directory: {member.name}")

                file_count += 1
                if file_count > MAX_FILE_COUNT:
                    raise SecurityValidationError("Archive exceeds maximum file count")

                if member.size > MAX_SINGLE_FILE_BYTES:
                    raise SecurityValidationError("Single file in archive exceeds size limit")

                total_bytes += member.size
                if total_bytes > MAX_UNCOMPRESSED_BYTES:
                    raise SecurityValidationError("Archive uncompressed total exceeds limit")

            tf.extractall(dest_dir)

        return file_count, total_bytes
