import os
import hashlib
import argparse
import json
from datetime import datetime

def get_file_hash(file_path):
    """Calculate SHA-256 hash of a file's contents."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            # Read file in chunks to handle large files efficiently
            for chunk in iter(lambda: f.read(4096), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def get_files_in_path(path):
    """Recursively collect all files with their full paths and hashes in the given path."""
    file_list = []
    for root, _, files in os.walk(path):
        for file in files:
            file_path = os.path.join(root, file)
            file_hash = get_file_hash(file_path)
            if file_hash:
                file_list.append({'name': file, 'path': file_path, 'hash': file_hash})
    return file_list

def compare_and_delete_files(path_a, path_b, dry_run=True):
    """Compare files in path_a and path_b by hash only, delete or list matching files from path_a."""
    # Get file lists with hashes for both paths
    files_a = get_files_in_path(path_a)
    files_b = get_files_in_path(path_b)

    # Find files with matching hashes
    matching_files = []
    for file_a in files_a:
        for file_b in files_b:
            if file_a['hash'] == file_b['hash']:
                matching_files.append({
                    'name_a': file_a['name'],
                    'path_a': file_a['path'],
                    'name_b': file_b['name'],
                    'path_b': file_b['path']
                })
                break  # Stop checking file_b once a match is found

    # Process matching files
    deleted_files = []
    if dry_run:
        print("\nDry Run: The following files would be deleted from Path A (matched by content hash):")
        for file in matching_files:
            print(f"File in Path A: {file['name_a']} (Path: {file['path_a']})")
            print(f"  Matches File in Path B: {file['name_b']} (Path: {file['path_b']})")
    else:
        for file in matching_files:
            file_path = file['path_a']
            try:
                os.remove(file_path)
                deleted_files.append(file_path)
                print(f"Deleted: {file_path}")
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")

    return deleted_files if not dry_run else matching_files

def clean_path(path):
    """Clean up path input by removing quotes and handling escaped spaces."""
    path = path.strip()
    # Remove surrounding quotes if present
    if (path.startswith('"') and path.endswith('"')) or \
       (path.startswith("'") and path.endswith("'")):
        path = path[1:-1]
    # Replace escaped spaces with regular spaces
    path = path.replace('\\ ', ' ')
    return path

def save_results_to_file(matching_files, path_a, path_b, output_file=None):
    """Save dry-run results to a JSON file."""
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"deletion_plan_{timestamp}.json"
    
    data = {
        "timestamp": datetime.now().isoformat(),
        "path_a": path_a,
        "path_b": path_b,
        "total_matches": len(matching_files),
        "matching_files": matching_files
    }
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"\nResults saved to: {output_file}")
    return output_file

def delete_from_saved_results(results_file):
    """Load saved results and perform deletion."""
    if not os.path.exists(results_file):
        print(f"Error: Results file not found: {results_file}")
        return
    
    with open(results_file, 'r') as f:
        data = json.load(f)
    
    matching_files = data.get('matching_files', [])
    
    if not matching_files:
        print("No files to delete in the results file.")
        return
    
    print(f"Loaded deletion plan from: {results_file}")
    print(f"Created: {data.get('timestamp')}")
    print(f"Path A: {data.get('path_a')}")
    print(f"Path B: {data.get('path_b')}")
    print(f"Files to delete: {len(matching_files)}")
    print("\nProceeding with deletion...")
    
    deleted_files = []
    for file in matching_files:
        file_path = file['path_a']
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                deleted_files.append(file_path)
                print(f"Deleted: {file_path}")
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
        else:
            print(f"Skipped (not found): {file_path}")
    
    print(f"\nDeleted {len(deleted_files)} files from Path A.")
    return deleted_files

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description='Compare files in two directories by content hash and delete duplicates from Path A.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python3 compare_and_delete_files.py
  
  # Dry-run and save results (default)
  python3 compare_and_delete_files.py "/Users/laiman/Pictures/All" "/Volumes/T7 Shield/Friends/"
  
  # Dry-run with custom output file
  python3 compare_and_delete_files.py "/Users/laiman/Pictures/All" "/Volumes/T7 Shield/Friends/" -o my_plan.json
  
  # Delete using saved results (fast - no re-scanning!)
  python3 compare_and_delete_files.py --from-file deletion_plan_20241006_123456.json
  
  # Direct deletion without saving (use with caution!)
  python3 compare_and_delete_files.py "/Users/laiman/Pictures/All" "/Volumes/T7 Shield/Friends/" --no-dry-run
        """
    )
    parser.add_argument('path_a', nargs='?', help='Path A (files to check for deletion)')
    parser.add_argument('path_b', nargs='?', help='Path B (reference files)')
    parser.add_argument('--dry-run', dest='dry_run', action='store_true', default=True,
                        help='Run in dry-run mode and save results (default)')
    parser.add_argument('--no-dry-run', dest='dry_run', action='store_false',
                        help='Actually delete files immediately')
    parser.add_argument('-o', '--output', dest='output_file', 
                        help='Output file for dry-run results (default: deletion_plan_TIMESTAMP.json)')
    parser.add_argument('--from-file', dest='results_file',
                        help='Load saved results and perform deletion (skips comparison)')
    
    args = parser.parse_args()
    
    # Mode 1: Load from saved results file
    if args.results_file:
        delete_from_saved_results(args.results_file)
        return
    
    # Mode 2: Compare directories
    # Get paths from arguments or interactive input
    if args.path_a and args.path_b:
        path_a = clean_path(args.path_a)
        path_b = clean_path(args.path_b)
        dry_run = args.dry_run
    else:
        # Fall back to interactive mode
        path_a = clean_path(input("Enter Path A: "))
        path_b = clean_path(input("Enter Path B: "))
        dry_run_input = input("Run in dry-run mode? (yes/no): ").strip().lower()
        dry_run = dry_run_input in ('yes', 'y')

    # Validate paths
    if not os.path.exists(path_a) or not os.path.exists(path_b):
        print("One or both paths do not exist!")
        print(f"Path A: {path_a} - {'exists' if os.path.exists(path_a) else 'NOT FOUND'}")
        print(f"Path B: {path_b} - {'exists' if os.path.exists(path_b) else 'NOT FOUND'}")
        return

    # Compare and process files
    result = compare_and_delete_files(path_a, path_b, dry_run)

    # Summary and save results
    if result:
        if dry_run:
            print(f"\nDry Run: {len(result)} files would be deleted from Path A.")
            # Save results to file
            output_file = save_results_to_file(result, path_a, path_b, args.output_file)
            print(f"\nTo perform the deletion, run:")
            print(f"  python3 compare_and_delete_files.py --from-file {output_file}")
        else:
            print(f"\nDeleted {len(result)} files from Path A.")
    else:
        print("\nNo files with identical contents found.")

if __name__ == "__main__":
    main()
