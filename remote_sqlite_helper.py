"""
Remote SQLite Helper Module
Handles downloading and syncing SQLite databases from remote URLs
"""
import os
import logging
import requests
import shutil
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Maximum size for remote database downloads (100 MB by default)
# Can be overridden via environment variable SQLITE_MAX_DOWNLOAD_BYTES
DEFAULT_MAX_REMOTE_DB_BYTES = 100 * 1024 * 1024  # 100 MB


class RemoteSQLiteHelper:
    """Helper class to manage remote SQLite database access"""

    def __init__(self, remote_url: Optional[str] = None, local_path: str = './logdir', max_db_bytes: Optional[int] = None):
        """
        Initialize the remote SQLite helper

        Args:
            remote_url: URL to the remote SQLite database file
            local_path: Local path to store the database (default: './logdir')
            max_db_bytes: Maximum allowed size for remote database in bytes (default: 100 MB)
        """
        self.remote_url = remote_url if remote_url is not None else os.getenv('SQLITE_URL')
        self.local_path = local_path

        # Set maximum download size with fallback chain
        if max_db_bytes is not None:
            self.max_db_bytes = max_db_bytes
        else:
            env_max = os.getenv('SQLITE_MAX_DOWNLOAD_BYTES')
            if env_max:
                try:
                    self.max_db_bytes = int(env_max)
                except ValueError:
                    logger.warning(f"Invalid SQLITE_MAX_DOWNLOAD_BYTES value: {env_max}, using default")
                    self.max_db_bytes = DEFAULT_MAX_REMOTE_DB_BYTES
            else:
                self.max_db_bytes = DEFAULT_MAX_REMOTE_DB_BYTES

        self._ensure_local_dir()

    def _ensure_local_dir(self):
        """Ensure the local directory exists"""
        Path(self.local_path).mkdir(parents=True, exist_ok=True)

    def get_store_path(self) -> str:
        """
        Get the store path for ell.init()

        If SQLITE_URL is set, downloads the remote database to local path.
        Otherwise, returns the local path for standard local SQLite usage.

        Returns:
            str: Path to use for ell.init() store parameter
        """
        if not self.remote_url:
            logger.info(f"No remote SQLite URL configured, using local path: {self.local_path}")
            return self.local_path

        logger.info(f"Remote SQLite URL configured: {self.remote_url}")

        try:
            self._download_remote_db()
            logger.info(f"Successfully downloaded remote database to: {self.local_path}")
        except Exception as e:
            logger.warning(f"Failed to download remote database: {str(e)}")
            logger.warning(f"Falling back to local path: {self.local_path}")

        return self.local_path

    def _download_remote_db(self):
        """Download the remote SQLite database to local path with size limit enforcement"""
        if not self.remote_url:
            raise ValueError("No remote URL configured")

        logger.info(f"Downloading remote SQLite database from: {self.remote_url}")
        logger.info(f"Maximum allowed size: {self.max_db_bytes} bytes ({self.max_db_bytes / (1024*1024):.2f} MB)")

        # Create a temporary file first
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_path = temp_file.name
        temp_file.close()

        try:
            # Download the database file with streaming
            response = requests.get(self.remote_url, timeout=30, stream=True)
            response.raise_for_status()

            # Check Content-Length header if available
            content_length = response.headers.get('Content-Length')
            if content_length:
                try:
                    content_length_int = int(content_length)
                    if content_length_int > self.max_db_bytes:
                        raise ValueError(
                            f"Remote database size ({content_length_int} bytes, "
                            f"{content_length_int / (1024*1024):.2f} MB) exceeds maximum allowed size "
                            f"({self.max_db_bytes} bytes, {self.max_db_bytes / (1024*1024):.2f} MB)"
                        )
                    logger.info(f"Remote database size: {content_length_int} bytes ({content_length_int / (1024*1024):.2f} MB)")
                except ValueError as e:
                    if "exceeds maximum" in str(e):
                        raise
                    logger.warning(f"Could not parse Content-Length header: {content_length}")
            else:
                logger.warning("Content-Length header not available, will check size during streaming")

            # Write to temporary file with streaming size check
            bytes_written = 0
            with open(temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive chunks
                        bytes_written += len(chunk)

                        # Enforce size limit during streaming
                        if bytes_written > self.max_db_bytes:
                            raise ValueError(
                                f"Downloaded data size ({bytes_written} bytes) exceeded maximum allowed size "
                                f"({self.max_db_bytes} bytes, {self.max_db_bytes / (1024*1024):.2f} MB) during streaming"
                            )

                        f.write(chunk)

            logger.info(f"Successfully downloaded {bytes_written} bytes ({bytes_written / (1024*1024):.2f} MB)")

            # Move to final location (the ell library expects a directory path)
            # We'll store it as db.sqlite in the local_path directory
            db_file = os.path.join(self.local_path, 'db.sqlite')

            # Remove existing file if present (required for cross-platform compatibility)
            if os.path.exists(db_file):
                os.remove(db_file)

            # Use shutil.move for cross-platform compatibility (works on Windows)
            shutil.move(temp_path, db_file)
            logger.info(f"Database saved to: {db_file}")

        except Exception as e:
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
                logger.debug(f"Cleaned up temporary file: {temp_path}")
            raise Exception(f"Failed to download remote database: {str(e)}")

    def sync_to_remote(self):
        """
        Upload the local SQLite database back to the remote URL

        Note: This requires the remote URL to support PUT/POST operations.
        This is a placeholder implementation that would need to be customized
        based on your specific remote storage solution (S3, HTTP server, etc.)
        """
        if not self.remote_url:
            logger.info("No remote URL configured, skipping sync")
            return

        logger.warning("Sync to remote not implemented - this requires a writable remote endpoint")
        logger.info("Consider using a cloud storage solution with proper upload APIs")


def get_ell_store_path() -> str:
    """
    Convenience function to get the appropriate store path for ell.init()

    Returns:
        str: Path to use for ell.init() store parameter
    """
    helper = RemoteSQLiteHelper()
    return helper.get_store_path()