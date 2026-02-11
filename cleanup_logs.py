#!/usr/bin/env python3
"""
Utility to manually clean up old log files
"""

import os
import sys
from pathlib import Path
import gzip
import shutil


def cleanup_logs(log_dir="log", keep_count=10):
    """Clean up old log files"""
    log_path = Path(log_dir)

    if not log_path.exists():
        print(f"Log directory not found: {log_dir}")
        return

    # Find all log files
    log_files = list(log_path.glob("*.log")) + list(log_path.glob("*.log.gz"))

    # Sort by modification time (oldest first)
    log_files.sort(key=lambda x: x.stat().st_mtime)

    # Remove old files
    if len(log_files) > keep_count:
        to_remove = log_files[:-keep_count]
        for file in to_remove:
            try:
                file_size = file.stat().st_size / 1024
                file.unlink()
                print(f"Removed: {file.name} ({file_size:.1f} KB)")
            except Exception as e:
                print(f"Error removing {file}: {e}")

    print(f"Kept {min(len(log_files), keep_count)} log files")


if __name__ == "__main__":
    cleanup_logs()