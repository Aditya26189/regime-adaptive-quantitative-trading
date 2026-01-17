"""
Organize submission files and directories.
"""
import os
import shutil
import glob
from pathlib import Path

def setup_directories():
    base_dir = Path.cwd()
    dirs = [
        "submission/final",
        "submission/archive",
        "docs/final",
        "docs/archive",
        "reports/figures"
    ]
    
    for d in dirs:
        path = base_dir / d
        path.mkdir(parents=True, exist_ok=True)
        print(f"Created: {path}")

def move_files():
    base_dir = Path.cwd()
    output_dir = base_dir / "output"
    
    # Identify latest submission files
    # We look for the generated files from the latest run
    # Pattern: 23ME3EP03_FINAL_submission_*.csv and individual symbol files
    
    files = list(output_dir.glob("*.csv"))
    if not files:
        print("No CSV files found in output/")
        return

    # Sort by modification time
    files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    # The latest combined file
    latest_combined = None
    for f in files:
        if "FINAL_submission" in f.name:
            latest_combined = f
            break
            
    if latest_combined:
        print(f"Latest combined: {latest_combined.name}")
        # Move to submission/final
        shutil.copy2(latest_combined, base_dir / "submission/final" / "FINAL_SUBMISSION.csv")
        
        # Also ensure individual symbol files typically generated alongside are moved
        # The naming convention was 23ME3EP03_NSE_SYMBOL_trades.csv
        # We should find the latest of these as well
        
        symbols = ['NIFTY50-INDEX', 'VBL-EQ', 'RELIANCE-EQ', 'SUNPHARMA-EQ', 'YESBANK-EQ']
        for sym in symbols:
            sym_pattern = f"*{sym}_trades.csv"
            sym_files = list(output_dir.glob(sym_pattern))
            if sym_files:
                sym_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                latest = sym_files[0]
                shutil.copy2(latest, base_dir / "submission/final" / latest.name)
                print(f"Moved {latest.name} to submission/final/")
    
    # Move old docs to archive
    docs_dir = base_dir / "docs"
    for f in docs_dir.glob("*"):
        if f.is_file() and f.name != "final":
             # Move to archive if it's not the new final docs (which we haven't written yet)
             # But let's be careful not to delete things we need.
             # Actually, let's copy everything to archive first for safety
             if f.suffix in ['.md', '.json']:
                 shutil.copy2(f, base_dir / "docs/archive" / f.name)
                 print(f"Archived {f.name}")

if __name__ == "__main__":
    setup_directories()
    move_files()
