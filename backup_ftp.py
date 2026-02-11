#!/usr/bin/env python3
"""
FTP Backup Script for existing multi-volume archives with enhanced error handling and log rotation
"""

import os
import sys
import configparser
import ftplib
import logging
import logging.handlers
import time
import re
from datetime import datetime
from pathlib import Path, PurePosixPath
import hashlib
from typing import List, Dict, Set, Tuple, Optional
import socket
import traceback
import gzip
import shutil


class RotatingLogHandler:
    """Custom log rotation handler"""

    def __init__(self, log_file: str, max_size_mb: int = 10, backup_count: int = 10):
        self.log_file = Path(log_file)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.backup_count = backup_count
        self.current_handler = None

    def get_handler(self):
        """Get logging handler with rotation"""
        # Create log directory if needed
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Use RotatingFileHandler with rotation on startup
        handler = logging.handlers.RotatingFileHandler(
            self.log_file,
            maxBytes=self.max_size_bytes,
            backupCount=self.backup_count,
            encoding='utf-8'
        )

        # Check if current log file exceeds size limit
        if self.log_file.exists() and self.log_file.stat().st_size > self.max_size_bytes:
            handler.doRollover()

        return handler

    def archive_current_log(self):
        """Archive current log file if it exists and is not empty"""
        if self.log_file.exists() and self.log_file.stat().st_size > 0:
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_name = self.log_file.with_suffix(f".{timestamp}.log.gz")

                # Compress current log
                with open(self.log_file, 'rb') as f_in:
                    with gzip.open(archive_name, 'wb') as f_out:
                        shutil.copyfileobj(f_in, f_out)

                # Clear current log
                open(self.log_file, 'w').close()

                # Clean up old archived logs
                self._cleanup_old_archives()

                return True
            except Exception as e:
                print(f"Warning: Could not archive log: {e}")
        return False

    def _cleanup_old_archives(self):
        """Remove old archived logs keeping only backup_count"""
        try:
            log_dir = self.log_file.parent
            archive_pattern = f"{self.log_file.stem}.*.log.gz"

            archives = sorted(log_dir.glob(archive_pattern), key=lambda x: x.stat().st_mtime)

            if len(archives) > self.backup_count:
                to_remove = archives[:-self.backup_count]
                for archive in to_remove:
                    archive.unlink()
        except Exception as e:
            print(f"Warning: Could not clean up old logs: {e}")


class FTPBackup:
    def __init__(self, config_path: str = "config.ini"):
        """Initialize backup system with configuration"""
        self.config = self._load_config(config_path)
        self.log_rotator = None
        self._setup_logging()
        self.ftp = None
        self.ignore_patterns = self._load_ignore_patterns()
        self.successful_uploads = set()  # Track successfully uploaded archive sets
        self.failed_uploads = set()  # Track failed archive sets

    def _load_config(self, config_path: str) -> configparser.ConfigParser:
        """Load configuration from INI file"""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")

        config = configparser.ConfigParser()
        config.read(config_path)

        # Set defaults
        if 'LOGGING' not in config:
            config.add_section('LOGGING')
        if 'log_file' not in config['LOGGING']:
            script_dir = Path(__file__).parent
            log_dir = script_dir / "log"
            log_dir.mkdir(exist_ok=True)
            config['LOGGING']['log_file'] = str(log_dir / "backup.log")

        return config

    def _setup_logging(self):
        """Configure logging system with rotation"""
        log_file = self.config['LOGGING'].get('log_file', 'backup.log')
        log_level = self.config['LOGGING'].get('level', 'INFO').upper()

        # Create log rotator
        self.log_rotator = RotatingLogHandler(
            log_file,
            max_size_mb=int(self.config['LOGGING'].get('max_size_mb', 10)),
            backup_count=int(self.config['LOGGING'].get('backup_count', 10))
        )

        # Get handler
        file_handler = self.log_rotator.get_handler()

        # Setup logging
        logger = logging.getLogger()
        logger.setLevel(getattr(logging, log_level))

        # Remove existing handlers
        for handler in logger.handlers[:]:
            logger.removeHandler(handler)

        # Add file handler with custom formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)-8s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        self.logger = logging.getLogger(__name__)

        # Log startup
        self.logger.info("=" * 70)
        self.logger.info("FTP Backup Script Started")
        self.logger.info(f"Log file: {log_file}")
        self.logger.info(f"Log level: {log_level}")

    def _load_ignore_patterns(self) -> Set[str]:
        """Load ignore patterns from .ftpignore file"""
        ignore_file = ".ftpignore"
        patterns = set()

        if os.path.exists(ignore_file):
            with open(ignore_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.add(line)

        return patterns

    def _should_ignore(self, filename: str) -> bool:
        """Check if file should be ignored"""
        for pattern in self.ignore_patterns:
            if pattern.startswith('*'):
                # Wildcard pattern like *.log
                if filename.endswith(pattern[1:]):
                    return True
            elif pattern in filename:
                return True
        return False

    def _connect_ftp(self) -> ftplib.FTP:
        """Connect to FTP server with retry logic"""
        max_retries = 3
        retry_delay = 5

        for attempt in range(max_retries):
            try:
                ftp_config = self.config['FTP']
                ftp = ftplib.FTP(
                    ftp_config['server'],
                    ftp_config['username'],
                    ftp_config['password']
                )
                ftp.encoding = 'utf-8'

                # Set longer timeout for large files
                ftp.sock.settimeout(300)

                self.logger.info(f"Connected to FTP server: {ftp_config['server']}")
                return ftp

            except Exception as e:
                self.logger.warning(f"FTP connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                else:
                    raise ConnectionError(f"Failed to connect to FTP after {max_retries} attempts: {e}")

    def _ensure_remote_directory(self, ftp: ftplib.FTP, remote_path: str):
        """Ensure remote directory exists, create if needed"""
        try:
            ftp.cwd(remote_path)
            self.logger.info(f"Using remote directory: {remote_path}")
        except ftplib.error_perm:
            # Directory doesn't exist, create it
            parts = PurePosixPath(remote_path).parts
            current_path = ""
            for part in parts:
                current_path = f"{current_path}/{part}" if current_path else part
                try:
                    ftp.cwd(current_path)
                except ftplib.error_perm:
                    try:
                        ftp.mkd(current_path)
                        self.logger.info(f"Created remote directory: {current_path}")
                    except Exception as e:
                        self.logger.warning(f"Could not create directory {current_path}: {e}")
                        raise
            try:
                ftp.cwd(remote_path)
            except:
                pass

    def _get_multi_volume_archives(self, source_dir: str) -> Dict[str, List[Path]]:
        """
        Find all multi-volume archive sets in source directory.
        Returns dict with base_name as key and list of volume paths as value.
        """
        source_path = Path(source_dir)
        archive_files = {}

        # Pattern for archive files: name_date_*_hash.tar or .tar.N
        archive_patterns = ['*.tar', '*.tar.*']

        for pattern in archive_patterns:
            for file_path in source_path.glob(pattern):
                if self._should_ignore(file_path.name):
                    continue

                # Extract base name (without volume number)
                base_name = self._get_archive_base_name(file_path.name)
                if base_name:
                    if base_name not in archive_files:
                        archive_files[base_name] = []
                    archive_files[base_name].append(file_path)

        # Sort volumes for each archive set
        for base_name in archive_files:
            archive_files[base_name].sort(key=lambda x: self._get_volume_number(x.name))

        return archive_files

    def _get_archive_base_name(self, filename: str) -> Optional[str]:
        """Extract base name from multi-volume archive filename"""
        # Pattern: crm.rusvek29.ru_20260127_020401_full_6mq5xw84z01osj0q.tar
        # Or: crm.rusvek29.ru_20260127_020401_full_6mq5xw84z01osj0q.tar.1

        # Check if it's a tar file
        if not filename.endswith('.tar') and '.tar.' not in filename:
            return None

        # Remove volume number
        if '.tar.' in filename:
            # Multi-volume: remove .N suffix
            base = filename.rsplit('.', 1)[0]
            # Verify it ends with .tar
            if not base.endswith('.tar'):
                return None
            return base
        else:
            # Single volume or first volume
            return filename

    def _get_volume_number(self, filename: str) -> int:
        """Extract volume number from filename, returns 0 for first volume"""
        if '.tar.' in filename:
            try:
                return int(filename.split('.')[-1])
            except ValueError:
                return 0
        return 0

    def _check_archive_exists_on_ftp(self, ftp: ftplib.FTP, base_name: str, remote_dir: str) -> Tuple[bool, List[str]]:
        """Check if archive set exists on FTP and return list of existing files"""
        try:
            ftp.cwd(remote_dir)
            files = []
            ftp.retrlines('NLST', files.append)

            existing_files = []
            for file in files:
                if file.startswith(base_name):
                    existing_files.append(file)

            return len(existing_files) > 0, existing_files

        except Exception as e:
            self.logger.error(f"Error checking FTP for {base_name}: {e}")
            return False, []

    def _verify_file_integrity(self, ftp: ftplib.FTP, local_file: Path, remote_filename: str) -> bool:
        """Verify that file was uploaded correctly by comparing size and checksum"""
        try:
            local_size = local_file.stat().st_size

            # Get remote file size
            remote_size = ftp.size(remote_filename)
            if remote_size is None:
                self.logger.error(f"Could not get size for {remote_filename}")
                return False

            remote_size = int(remote_size)

            if local_size != remote_size:
                self.logger.error(
                    f"Size mismatch for {remote_filename}: local={local_size:,} bytes, remote={remote_size:,} bytes")
                return False

            # Optional: Calculate and compare checksums (requires additional FTP command support)
            # This is commented out as not all FTP servers support checksum commands
            # if self._verify_checksum(ftp, local_file, remote_filename):
            #     return True

            self.logger.info(f"Size verified: {remote_filename} ({remote_size:,} bytes)")
            return True

        except Exception as e:
            self.logger.error(f"Error verifying {remote_filename}: {e}")
            return False

    def _upload_file_to_ftp_with_retry(self, ftp: ftplib.FTP, local_file: Path, remote_filename: str, remote_dir: str,
                                       max_retries: int = 3) -> bool:
        """Upload single file to FTP with retry logic"""
        for attempt in range(max_retries):
            try:
                # Ensure we're in the right directory
                ftp.cwd(remote_dir)

                file_size_mb = local_file.stat().st_size / 1024 / 1024
                self.logger.info(f"Uploading [{attempt + 1}/{max_retries}]: {local_file.name} ({file_size_mb:.2f} MB)")

                # Store file
                with open(local_file, 'rb') as f:
                    ftp.storbinary(f"STOR {remote_filename}", f)

                # Verify upload
                if self._verify_file_integrity(ftp, local_file, remote_filename):
                    self.logger.info(f"✓ Upload successful: {remote_filename}")
                    return True
                else:
                    self.logger.warning(f"Upload verification failed, retrying...")

            except ftplib.error_temp as e:
                self.logger.warning(f"Temporary FTP error on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    # Reconnect if needed
                    try:
                        ftp.quit()
                    except:
                        pass
                    ftp = self._connect_ftp()
                    continue
                else:
                    self.logger.error(f"Failed after {max_retries} attempts: {e}")
                    return False

            except Exception as e:
                self.logger.error(f"Upload failed on attempt {attempt + 1}: {e}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return False

        return False

    def _process_archive_set(self, ftp: ftplib.FTP, base_name: str, archive_set: List[Path], remote_dir: str) -> bool:
        """Process and upload an archive set with error handling"""
        self.logger.info(f"Processing archive set: {base_name}")
        self.logger.info(f"  Volumes: {len(archive_set)} files")

        try:
            # Check if archive exists on FTP
            exists, existing_files = self._check_archive_exists_on_ftp(ftp, base_name, remote_dir)

            if exists:
                self.logger.info(f"  Archive set already exists on FTP ({len(existing_files)} files)")

                # Verify all volumes are present
                if len(existing_files) == len(archive_set):
                    self.logger.info("  All volumes present on FTP, skipping upload")
                    return True
                else:
                    self.logger.warning(f"  Volume count mismatch: FTP={len(existing_files)}, local={len(archive_set)}")

                    # Re-upload missing volumes
                    local_filenames = {f.name for f in archive_set}
                    missing = local_filenames - set(existing_files)

                    if missing:
                        self.logger.info(f"  Uploading {len(missing)} missing volumes")
                        for volume in archive_set:
                            if volume.name in missing:
                                if not self._upload_file_to_ftp_with_retry(ftp, volume, volume.name, remote_dir):
                                    self.logger.error(f"  Failed to upload missing volume: {volume.name}")
                                    return False
            else:
                # Archive doesn't exist on FTP, upload all volumes
                self.logger.info("  Archive set not found on FTP, uploading all volumes...")
                for volume in archive_set:
                    if not self._upload_file_to_ftp_with_retry(ftp, volume, volume.name, remote_dir):
                        self.logger.error(f"  Failed to upload volume: {volume.name}")
                        return False

            self.logger.info(f"  ✓ Archive set '{base_name}' processed successfully")
            return True

        except Exception as e:
            self.logger.error(f"  ✗ Error processing archive set '{base_name}': {e}")
            self.logger.debug(f"  Traceback: {traceback.format_exc()}")
            return False

    def _get_archive_timestamp(self, base_name: str) -> Optional[datetime]:
        """Extract timestamp from archive base name"""
        # Pattern: crm.rusvek29.ru_20260127_020401_full_6mq5xw84z01osj0q.tar
        match = re.search(r'_(\d{8}_\d{6})_', base_name)
        if match:
            try:
                return datetime.strptime(match.group(1), "%Y%m%d_%H%M%S")
            except ValueError:
                pass
        return None

    def _cleanup_old_ftp_backups(self, ftp: ftplib.FTP, remote_dir: str, max_copies: int):
        """Remove old backup sets from FTP server (only successful ones)"""
        try:
            ftp.cwd(remote_dir)
            files = []
            ftp.retrlines('NLST', files.append)

            # Group files by archive set
            archive_sets = {}
            for filename in files:
                base_name = self._get_archive_base_name(filename)
                if base_name and base_name in self.successful_uploads:
                    if base_name not in archive_sets:
                        archive_sets[base_name] = []
                    archive_sets[base_name].append(filename)

            # Get timestamp for each archive set
            archive_timestamps = []
            for base_name, file_list in archive_sets.items():
                timestamp = self._get_archive_timestamp(base_name)
                if timestamp:
                    # Sort files in set for consistent logging
                    file_list.sort(key=lambda x: self._get_volume_number(x))
                    archive_timestamps.append((timestamp, base_name, file_list))

            # Sort by timestamp (oldest first)
            archive_timestamps.sort(key=lambda x: x[0])

            # Remove excess backups
            if len(archive_timestamps) > max_copies:
                to_remove = archive_timestamps[:-max_copies]
                for timestamp, base_name, file_list in to_remove:
                    self.logger.info(f"Removing old FTP backup set: {base_name} ({timestamp})")
                    for filename in file_list:
                        try:
                            ftp.delete(filename)
                            self.logger.info(f"  Removed: {filename}")
                        except Exception as e:
                            self.logger.error(f"  Failed to remove {filename}: {e}")

            self.logger.info(f"Kept {min(len(archive_timestamps), max_copies)} backup sets on FTP")

        except Exception as e:
            self.logger.error(f"Error cleaning up old FTP backups: {e}")

    def _cleanup_local_archives(self, source_dir: str):
        """Remove local archive sets, but only successful ones and keep only the most recent successful one"""
        try:
            source_path = Path(source_dir)

            # Get only successful archive sets
            successful_sets = {}
            for base_name in self.successful_uploads:
                # Find local files for this base_name
                pattern = f"{base_name}*"
                files = list(source_path.glob(pattern))
                if files:
                    successful_sets[base_name] = files

            if len(successful_sets) <= 1:
                self.logger.info("Only one successful archive set found locally, nothing to clean up")
                return

            # Get timestamp for each successful archive set
            sets_with_timestamp = []
            for base_name, file_list in successful_sets.items():
                timestamp = self._get_archive_timestamp(base_name)
                if timestamp:
                    sets_with_timestamp.append((timestamp, base_name, file_list))

            if not sets_with_timestamp:
                self.logger.warning("Could not extract timestamps from archive names")
                return

            # Sort by timestamp (oldest first)
            sets_with_timestamp.sort(key=lambda x: x[0])

            # Keep only the most recent successful set
            to_keep = sets_with_timestamp[-1]
            to_remove = sets_with_timestamp[:-1]

            # Remove old successful sets
            removed_count = 0
            for timestamp, base_name, file_list in to_remove:
                self.logger.info(f"Removing local successful archive set: {base_name} ({timestamp})")
                for file_path in file_list:
                    try:
                        if file_path.exists():
                            file_size = file_path.stat().st_size / 1024 / 1024
                            file_path.unlink()
                            self.logger.info(f"  Removed: {file_path.name} ({file_size:.2f} MB)")
                            removed_count += 1
                    except Exception as e:
                        self.logger.error(f"  Failed to remove {file_path}: {e}")

            self.logger.info(f"Kept local successful archive set: {to_keep[1]} ({to_keep[0]})")
            self.logger.info(f"Removed {removed_count} files from old successful sets")

            # Don't remove failed sets - they remain for manual investigation

        except Exception as e:
            self.logger.error(f"Error cleaning local archives: {e}")

    def _get_ftp_files_set(self, ftp: ftplib.FTP, remote_dir: str) -> Set[str]:
        """Get set of all files on FTP"""
        try:
            ftp.cwd(remote_dir)
            files = []
            ftp.retrlines('NLST', files.append)
            return set(files)
        except Exception as e:
            self.logger.error(f"Error getting FTP file list: {e}")
            return set()

    def _log_summary(self):
        """Log summary of backup operation"""
        self.logger.info("=" * 70)
        self.logger.info("BACKUP SUMMARY")
        self.logger.info(f"Successful uploads: {len(self.successful_uploads)} set(s)")
        self.logger.info(f"Failed uploads: {len(self.failed_uploads)} set(s)")

        if self.successful_uploads:
            self.logger.info("Successfully processed sets:")
            for base_name in sorted(self.successful_uploads):
                self.logger.info(f"  ✓ {base_name}")

        if self.failed_uploads:
            self.logger.warning("Failed sets (require manual attention):")
            for base_name in sorted(self.failed_uploads):
                self.logger.warning(f"  ✗ {base_name}")

        self.logger.info("=" * 70)

    def run(self):
        """Execute backup process with comprehensive error handling"""
        start_time = time.time()

        try:
            # Load configuration
            ftp_config = self.config['FTP']
            local_config = self.config['LOCAL']
            settings = self.config['SETTINGS']

            source_dir = local_config['source_dir']
            remote_dir = ftp_config['remote_dir']
            max_copies = int(settings.get('max_copies', 5))

            # Connect to FTP
            self.ftp = self._connect_ftp()

            # Ensure remote directory exists
            self._ensure_remote_directory(self.ftp, remote_dir)

            # Find all multi-volume archives locally
            archive_sets = self._get_multi_volume_archives(source_dir)

            if not archive_sets:
                self.logger.warning("No archive files found in source directory")
                return

            self.logger.info(f"Found {len(archive_sets)} archive set(s) locally")

            # Process each archive set
            processed_count = 0
            for base_name, file_list in archive_sets.items():
                processed_count += 1
                self.logger.info(f"Processing set {processed_count}/{len(archive_sets)}")

                try:
                    success = self._process_archive_set(self.ftp, base_name, file_list, remote_dir)

                    if success:
                        self.successful_uploads.add(base_name)
                        self.logger.info(f"Set {processed_count}/{len(archive_sets)}: SUCCESS")
                    else:
                        self.failed_uploads.add(base_name)
                        self.logger.error(
                            f"Set {processed_count}/{len(archive_sets)}: FAILED - set will not be removed locally")

                        # Continue with next set despite failure
                        continue

                except Exception as e:
                    self.failed_uploads.add(base_name)
                    self.logger.error(f"Critical error processing set {base_name}: {e}")
                    self.logger.error("Continuing with next set...")
                    continue

            # Only perform cleanup if we have successful uploads
            if self.successful_uploads:
                # Clean up old backups on FTP (only from successful sets)
                self._cleanup_old_ftp_backups(self.ftp, remote_dir, max_copies)

                # Clean up local archives (only successful sets)
                self._cleanup_local_archives(source_dir)
            else:
                self.logger.warning("No successful uploads - skipping cleanup operations")

            # Log summary
            self._log_summary()

            elapsed_time = time.time() - start_time
            self.logger.info(f"Total execution time: {elapsed_time:.2f} seconds")

            if self.failed_uploads:
                self.logger.warning("Backup completed with errors - check failed sets above")
                return 1  # Return error code
            else:
                self.logger.info("Backup completed successfully")
                return 0

        except Exception as e:
            elapsed_time = time.time() - start_time
            self.logger.error(f"FATAL ERROR: Backup process failed: {e}")
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            self.logger.error(f"Script terminated after {elapsed_time:.2f} seconds")
            return 2  # Return fatal error code

        finally:
            # Archive log file if it's large
            if self.log_rotator and self.log_rotator.log_file.exists():
                if self.log_rotator.log_file.stat().st_size > self.log_rotator.max_size_bytes:
                    self.logger.info("Log file exceeds size limit, archiving...")
                    self.log_rotator.archive_current_log()

            if self.ftp:
                try:
                    self.ftp.quit()
                    self.logger.info("FTP connection closed")
                except:
                    pass


def main():
    """Main entry point"""
    try:
        backup = FTPBackup()
        return_code = backup.run()
        sys.exit(return_code)
    except KeyboardInterrupt:
        print("\nBackup interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Fatal error: {e}")
        traceback.print_exc()
        sys.exit(2)


if __name__ == "__main__":
    main()