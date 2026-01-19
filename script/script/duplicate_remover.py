import os
import hashlib
import argparse
import json
from datetime import datetime
from concurrent.futures import ProcessPoolExecutor, as_completed
from functools import partial
import multiprocessing

# Larger chunk size for better I/O performance
CHUNK_SIZE = 1024 * 1024  # 1MB chunks


def get_file_hash(file_path):
    """Calculate SHA-256 hash of a file's contents."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(CHUNK_SIZE), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None


def get_file_info(file_path):
    """Get file info including size and path for a single file."""
    try:
        size = os.path.getsize(file_path)
        return {'path': file_path, 'name': os.path.basename(file_path), 'size': size}
    except Exception as e:
        print(f"Error accessing {file_path}: {e}")
        return None


def hash_file_worker(file_path):
    """Worker function for parallel hashing."""
    file_hash = get_file_hash(file_path)
    if file_hash:
        return {'path': file_path, 'name': os.path.basename(file_path), 'hash': file_hash}
    return None


def collect_files_with_sizes(path):
    """Collect all files with their sizes (fast, no hashing yet)."""
    files = []
    print(f"Scanning: {path}")
    for root, _, filenames in os.walk(path):
        for filename in filenames:
            file_path = os.path.join(root, filename)
            info = get_file_info(file_path)
            if info:
                files.append(info)
    print(f"  Found {len(files)} files")
    return files


def hash_files_parallel(file_paths, desc="Hashing"):
    """Hash multiple files in parallel using multiprocessing."""
    results = {}
    total = len(file_paths)
    
    if total == 0:
        return results
    
    # Use number of CPUs, but cap at reasonable limit
    num_workers = min(multiprocessing.cpu_count(), 8)
    
    print(f"{desc} {total} files using {num_workers} workers...")
    
    completed = 0
    with ProcessPoolExecutor(max_workers=num_workers) as executor:
        future_to_path = {executor.submit(hash_file_worker, path): path for path in file_paths}
        
        for future in as_completed(future_to_path):
            completed += 1
            if completed % 100 == 0 or completed == total:
                print(f"  Progress: {completed}/{total} ({100*completed//total}%)")
            
            result = future.result()
            if result:
                results[result['path']] = result
    
    return results


def compare_and_delete_files(path_a, path_b, dry_run=True):
    """Compare files in path_a and path_b by hash, delete or list matching files from path_a."""
    
    # Step 1: Collect files with sizes (fast)
    files_a = collect_files_with_sizes(path_a)
    files_b = collect_files_with_sizes(path_b)
    
    if not files_a or not files_b:
        print("One of the paths is empty or inaccessible.")
        return []
    
    # Step 2: Build size index for path_b (for quick lookup)
    sizes_b = {}
    for f in files_b:
        size = f['size']
        if size not in sizes_b:
            sizes_b[size] = []
        sizes_b[size].append(f)
    
    # Step 3: Filter files_a to only those with matching sizes in path_b
    candidate_files_a = []
    candidate_files_b_paths = set()
    
    for f in files_a:
        if f['size'] in sizes_b:
            candidate_files_a.append(f)
            for fb in sizes_b[f['size']]:
                candidate_files_b_paths.add(fb['path'])
    
    print(f"\nSize-based filtering:")
    print(f"  Path A candidates: {len(candidate_files_a)} (of {len(files_a)})")
    print(f"  Path B candidates: {len(candidate_files_b_paths)} (of {len(files_b)})")
    
    if not candidate_files_a:
        print("No files with matching sizes found.")
        return []
    
    # Step 4: Hash only the candidate files (parallel)
    paths_a_to_hash = [f['path'] for f in candidate_files_a]
    paths_b_to_hash = list(candidate_files_b_paths)
    
    print()
    hashed_a = hash_files_parallel(paths_a_to_hash, "Hashing Path A:")
    hashed_b = hash_files_parallel(paths_b_to_hash, "Hashing Path B:")
    
    # Step 5: Build hash lookup for path_b (O(1) lookup)
    hash_to_b = {}
    for path, info in hashed_b.items():
        h = info['hash']
        if h not in hash_to_b:
            hash_to_b[h] = []
        hash_to_b[h].append(info)
    
    # Step 6: Find matches (O(n) instead of O(n*m))
    matching_files = []
    for path, info_a in hashed_a.items():
        h = info_a['hash']
        if h in hash_to_b:
            # Match found - take first matching file from path_b
            info_b = hash_to_b[h][0]
            matching_files.append({
                'name_a': info_a['name'],
                'path_a': info_a['path'],
                'name_b': info_b['name'],
                'path_b': info_b['path']
            })
    
    # Step 7: Process matching files
    deleted_files = []
    if dry_run:
        print(f"\nDry Run: The following {len(matching_files)} files would be deleted from Path A:")
        for file in matching_files:
            print(f"  {file['path_a']}")
            print(f"    -> matches: {file['path_b']}")
    else:
        for file in matching_files:
            file_path = file['path_a']
            try:
                os.remove(file_path)
                deleted_files.append(file_path)
                print(f"Deleted: {file_path}")
            except Exception as e:
                print(f"Error deleting {file_path}: {e}")
    
    return matching_files if dry_run else deleted_files


def clean_path(path):
    """Clean up path input by removing quotes and handling escaped spaces."""
    path = path.strip()
    if (path.startswith('"') and path.endswith('"')) or \
       (path.startswith("'") and path.endswith("'")):
        path = path[1:-1]
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
    parser = argparse.ArgumentParser(
        description='Compare files in two directories by content hash and delete duplicates from Path A.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode
  python3 duplicate_remover.py
  
  # Dry-run and save results (default)
  python3 duplicate_remover.py "/path/to/source" "/path/to/reference"
  
  # Dry-run with custom output file
  python3 duplicate_remover.py "/path/to/source" "/path/to/reference" -o my_plan.json
  
  # Delete using saved results (fast - no re-scanning!)
  python3 duplicate_remover.py --from-file deletion_plan_20241006_123456.json
  
  # Direct deletion without saving (use with caution!)
  python3 duplicate_remover.py "/path/to/source" "/path/to/reference" --no-dry-run

Performance Notes:
  - Uses multiprocessing for parallel file hashing
  - Pre-filters by file size (files of different sizes can't be duplicates)
  - Uses O(1) hash lookups instead of O(n*m) comparisons
  - Uses 1MB chunks for efficient I/O
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
    if args.path_a and args.path_b:
        path_a = clean_path(args.path_a)
        path_b = clean_path(args.path_b)
        dry_run = args.dry_run
    else:
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
            output_file = save_results_to_file(result, path_a, path_b, args.output_file)
            print(f"\nTo perform the deletion, run:")
            print(f"  python3 duplicate_remover.py --from-file {output_file}")
        else:
            print(f"\nDeleted {len(result)} files from Path A.")
    else:
        print("\nNo files with identical contents found.")


if __name__ == "__main__":
    main()
