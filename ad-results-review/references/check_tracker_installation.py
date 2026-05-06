#!/usr/bin/env python3
"""
Check which MVPs have the yourdomain.com tracker.js script installed.
This script scans worker.js files for the tracker script reference.
"""

import glob
import os
import sys

def main():
    # Pattern to find worker.js files in MVP src directories
    pattern = os.path.expanduser('~/.hermes/mvps/*/src/worker.js')
    worker_files = glob.glob(pattern)
    
    if not worker_files:
        print("No worker.js files found.")
        return 1
    
    print(f"Found {len(worker_files)} worker.js files\n")
    
    mvp_tracker_status = []
    for file_path in worker_files:
        mvp_name = file_path.split(os.sep)[-2]
        with open(file_path, 'r') as f:
            content = f.read()
        
        has_tracker = 'yourdomain.com/src/tracker.js' in content
        mvp_tracker_status.append((mvp_name, has_tracker, file_path))
    
    # Print summary
    print("MVP Tracker Installation Status:")
    print("=" * 50)
    
    mvp_with_tracker = []
    for name, has_tracker, path in mvp_tracker_status:
        status = "✅ INSTALLED" if has_tracker else "❌ MISSING"
        print(f"  {name}: {status}")
        if has_tracker:
            mvp_with_tracker.append(name)
    
    print("\n" + "=" * 50)
    print(f"Total MVPs: {len(mvp_tracker_status)}")
    print(f"MVPs with tracker: {len(mvp_with_tracker)}")
    print(f"MVPs without tracker: {len(mvp_tracker_status) - len(mvp_with_tracker)}")
    
    # Optionally, list specific files that are missing the tracker
    if len(mvp_with_tracker) < len(mvp_tracker_status):
        missing = [name for name, has, _ in mvp_tracker_status if not has]
        print(f"\nMVPs missing tracker: {', '.join(missing)}")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())