#!/usr/bin/env python3
"""
Utility to check backup status
"""

import os
import sys
from datetime import datetime
from pathlib import Path

def check_backup_status(config_path="config.ini"):
    """Check backup status from logs"""
    import configparser
    
    config = configparser.ConfigParser()
    config.read(config_path)
    
    log_file = config['LOGGING'].get('log_file', 'log/backup.log')
    source_dir = config['LOCAL']['source_dir']
    
    print("=" * 70)
    print("BACKUP STATUS CHECK")
    print("=" * 70)
    
    # Check log file
    log_path = Path(log_file)
    if log_path.exists():
        log_size = log_path.stat().st_size / 1024 / 1024
        log_mtime = datetime.fromtimestamp(log_path.stat().st_mtime)
        print(f"Log file: {log_path}")
        print(f"  Size: {log_size:.2f} MB")
        print(f"  Last modified: {log_mtime}")
        
        # Show last 20 lines
        print("\nLast 20 lines of log:")
        print("-" * 70)
        try:
            with open(log_path, 'r') as f:
                lines = f.readlines()
                for line in lines[-20:]:
                    print(line.rstrip())
        except Exception as e:
            print(f"Error reading log: {e}")
    else:
        print(f"Log file not found: {log_path}")
    
    print("\n" + "=" * 70)
    
    # Check source directory
    source_path = Path(source_dir)
    if source_path.exists():
        print(f"Source directory: {source_path}")
        
        # Count archive files
        tar_files = list(source_path.glob("*.tar"))
        tar_part_files = list(source_path.glob("*.tar.*"))
        
        print(f"  Archive files: {len(tar_files) + len(tar_part_files)}")
        print(f"    - Complete .tar files: {len(tar_files)}")
        print(f"    - Volume parts (.tar.N): {len(tar_part_files)}")
        
        if tar_files or tar_part_files:
            print("\n  Recent archive sets:")
            archive_sets = {}
            for file in tar_files + tar_part_files:
                # Extract base name
                name = file.name
                if '.tar.' in name:
                    base = name.rsplit('.', 1)[0]
                else:
                    base = name
                
                if base not in archive_sets:
                    archive_sets[base] = []
                archive_sets[base].append(file)
            
            # Show 5 most recent sets by file modification time
            sorted_sets = sorted(
                archive_sets.items(),
                key=lambda x: max(f.stat().st_mtime for f in x[1]),
                reverse=True
            )[:5]
            
            for base_name, files in sorted_sets:
                file_count = len(files)
                newest = max(f.stat().st_mtime for f in files)
                newest_str = datetime.fromtimestamp(newest).strftime("%Y-%m-%d %H:%M:%S")
                total_size = sum(f.stat().st_size for f in files) / 1024 / 1024
                print(f"    {base_name}")
                print(f"      Files: {file_count}, Size: {total_size:.1f} MB, Newest: {newest_str}")
    else:
        print(f"Source directory not found: {source_path}")
    
    print("=" * 70)

if __name__ == "__main__":
    check_backup_status()