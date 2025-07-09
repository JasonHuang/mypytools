#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import shutil
from pathlib import Path
from PIL import Image
import pillow_heif
import argparse

# Register HEIF format support
pillow_heif.register_heif_opener()

def backup_files(source_dir, backup_dir):
    """Backup all files from source directory to backup directory"""
    print(f"Starting backup from {source_dir} to {backup_dir}...")
    
    # Create backup directory
    backup_path = Path(backup_dir)
    backup_path.mkdir(exist_ok=True)
    
    # Backup all files
    for item in Path(source_dir).iterdir():
        if item.is_file():
            dest_file = backup_path / item.name
            shutil.copy2(item, dest_file)
            print(f"Backed up: {item.name}")
    
    print("File backup completed!")

def convert_heic_to_jpg(input_path, output_path=None, quality=95, delete_original=False):
    """Convert a single HEIC file to JPG format
    
    Args:
        input_path: Path to input HEIC file or directory
        output_path: Path to output JPG file or directory
        quality: JPEG quality (1-100)
        delete_original: Whether to delete original HEIC file
    
    Returns:
        bool: True if conversion successful, False otherwise
    """
    try:
        input_file = Path(input_path)
        
        if input_file.is_file():
            # Single file conversion
            if not input_file.suffix.lower() in ['.heic', '.HEIC']:
                print(f"Error: {input_file} is not a HEIC file")
                return False
                
            # Determine output path
            if output_path:
                output_file = Path(output_path)
            else:
                output_file = input_file.with_suffix('.jpg')
                
            # Open and convert HEIC file
            with Image.open(input_file) as img:
                # Convert to RGB mode (JPG doesn't support transparency)
                if img.mode in ('RGBA', 'LA', 'P'):
                    img = img.convert('RGB')
                
                # Save as JPG format
                img.save(output_file, 'JPEG', quality=quality, optimize=True)
                print(f"Converted: {input_file.name} -> {output_file.name}")
                
                # Delete original HEIC file if requested
                if delete_original:
                    input_file.unlink()
                    print(f"Deleted original: {input_file.name}")
                    
            return True
            
        else:
            print(f"Error: {input_path} is not a valid file")
            return False
            
    except Exception as e:
        print(f"Conversion failed for {input_path}: {str(e)}")
        return False

def convert_heic_directory(source_dir):
    """Convert all HEIC files in directory to JPG format"""
    print(f"Starting HEIC conversion in {source_dir}...")
    
    source_path = Path(source_dir)
    converted_count = 0
    
    # Find all HEIC files (case insensitive)
    heic_files = list(source_path.glob('*.heic')) + list(source_path.glob('*.HEIC'))
    
    if not heic_files:
        print("No HEIC files found")
        return
    
    for heic_file in heic_files:
        if convert_heic_to_jpg(heic_file, delete_original=True):
            converted_count += 1
    
    print(f"Conversion completed! Processed {converted_count} files")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Backup files and convert HEIC format to JPG format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Usage examples:
  python3 convert_heic_to_jpg.py /path/to/directory
  python3 convert_heic_to_jpg.py ./uploads
  python3 convert_heic_to_jpg.py .  # current directory
        """
    )
    
    parser.add_argument(
        'directory',
        nargs='?',
        default='.',
        help='Directory path to process (default: current directory)'
    )
    
    parser.add_argument(
        '--backup-dir',
        default=None,
        help='Backup directory path (default: backup subdirectory in source)'
    )
    
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help='Skip backup step, convert files directly'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview mode, show files to be processed without executing'
    )
    
    return parser.parse_args()

def main():
    """Main function"""
    args = parse_arguments()
    
    # Validate directory path
    source_dir = Path(args.directory).resolve()
    if not source_dir.exists():
        print(f"Error: Directory '{source_dir}' does not exist")
        sys.exit(1)
    
    if not source_dir.is_dir():
        print(f"Error: '{source_dir}' is not a directory")
        sys.exit(1)
    
    # Set backup directory
    if args.backup_dir:
        backup_dir = Path(args.backup_dir).resolve()
    else:
        backup_dir = source_dir / 'backup'
    
    print("=== HEIC to JPG Converter ===")
    print(f"Source directory: {source_dir}")
    if not args.no_backup:
        print(f"Backup directory: {backup_dir}")
    print()
    
    # Preview mode
    if args.dry_run:
        print("=== Preview Mode ===")
        heic_files = list(source_dir.glob('*.heic')) + list(source_dir.glob('*.HEIC'))
        if heic_files:
            print(f"Found {len(heic_files)} HEIC files:")
            for heic_file in heic_files:
                jpg_name = heic_file.stem + '.jpg'
                print(f"  {heic_file.name} -> {jpg_name}")
        else:
            print("No HEIC files found")
        return
    
    # Ask for user confirmation
    if not args.no_backup:
        confirm_msg = "Continue with backup and conversion? (y/N): "
    else:
        confirm_msg = "Continue with conversion (no backup)? (y/N): "
    
    confirm = input(confirm_msg).strip().lower()
    if confirm not in ['y', 'yes']:
        print("Operation cancelled")
        return
    
    try:
        # Step 1: Backup files (if needed)
        if not args.no_backup:
            backup_files(source_dir, backup_dir)
            print()
        
        # Step 2: Convert HEIC files
        convert_heic_directory(source_dir)
        print()
        
        print("All operations completed!")
        
    except Exception as e:
        print(f"Error during execution: {str(e)}")
        print("Please check the error message and try again")
        sys.exit(1)

if __name__ == "__main__":
    main()
