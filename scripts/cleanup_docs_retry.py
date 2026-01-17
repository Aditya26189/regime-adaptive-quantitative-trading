import os
import shutil
from pathlib import Path
import time

def cleanup_retry():
    base_dir = Path.cwd()
    docs_dir = base_dir / "docs"
    final_dir = docs_dir / "final"
    archive_dir = docs_dir / "archive"
    
    # 2. Delete archive and final directories (Retry)
    # Adding a small delay just in case
    time.sleep(1)
    
    if final_dir.exists():
        try:
            shutil.rmtree(final_dir)
            print("Deleted docs/final/")
        except Exception as e:
            print(f"Failed to delete docs/final: {e}")
        
    if archive_dir.exists():
        try:
            shutil.rmtree(archive_dir)
            print("Deleted docs/archive/")
        except Exception as e:
            print(f"Failed to delete docs/archive: {e}")
        
    # 3. Clean up loose files
    core_docs_strict = [
        "ADVANCED_METHODOLOGY.md",
        "STRATEGY_DEFENSE.md",
        "VISUAL_ANALYSIS.md",
        "USER_GUIDE.md"
    ]
    
    for file_path in docs_dir.glob("*"):
        if file_path.is_file():
            if file_path.name not in core_docs_strict:
                try:
                    os.remove(file_path)
                    print(f"Deleted old doc: {file_path.name}")
                except Exception as e:
                    print(f"Failed to delete {file_path.name}: {e}")
                
    # 4. Update links
    files_to_update = [base_dir / "README.md"] + list(docs_dir.glob("*.md"))
    
    for file_path in files_to_update:
        if not file_path.exists(): continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            new_content = content
            # Replace "docs/final/" -> "docs/"
            new_content = new_content.replace("docs/final/", "docs/")
            
            # Also fix relative links inside the docs themselves
            # e.g. in USER_GUIDE: [Methodology](final/ADVANCED...) -> [Methodology](ADVANCED...)
            new_content = new_content.replace("(final/", "(")
            new_content = new_content.replace("docs/final/", "docs/")
            
            # Fix absolute-ish links if any: "docs/final/xyz" -> "docs/xyz"
            
            if content != new_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                print(f"Updated links in {file_path.name}")
        except Exception as e:
            print(f"Failed to update links in {file_path.name}: {e}")

if __name__ == "__main__":
    cleanup_retry()
