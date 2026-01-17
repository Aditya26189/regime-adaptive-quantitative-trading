import os
import shutil
from pathlib import Path

def cleanup_docs():
    base_dir = Path.cwd()
    docs_dir = base_dir / "docs"
    final_dir = docs_dir / "final"
    archive_dir = docs_dir / "archive"
    
    # 1. Move files from docs/final to docs/
    if final_dir.exists():
        for file_path in final_dir.glob("*"):
            if file_path.is_file():
                dest = docs_dir / file_path.name
                shutil.move(str(file_path), str(dest))
                print(f"Moved {file_path.name} to docs/")
    
    # 2. Delete archive and final directories
    if final_dir.exists():
        shutil.rmtree(final_dir)
        print("Deleted docs/final/")
        
    if archive_dir.exists():
        shutil.rmtree(archive_dir)
        print("Deleted docs/archive/")
        
    # 3. Clean up any other loose files in docs/ that are NOT the core 4
    # The core 4 are: ADVANCED_METHODOLOGY.md, STRATEGY_DEFENSE.md, VISUAL_ANALYSIS.md, USER_GUIDE.md
    # plus maybe images folder if it exists there? No, images are in reports/figures
    
    core_docs = [
        "ADVANCED_METHODOLOGY.md",
        "STRATEGY_DEFENSE.md",
        "VISUAL_ANALYSIS.md",
        "USER_GUIDE.md",
        "COMPLETE_SYSTEM_DOCUMENTATION.md" # Keeping this just in case as a backup/reference unless strictly told to del
    ]
    
    # Actually user said "delete the older ones". COMPLETE_SYSTEM_DOCUMENTATION.md is older. 
    # Let's delete everything not in the core new set.
    
    core_docs_strict = [
        "ADVANCED_METHODOLOGY.md",
        "STRATEGY_DEFENSE.md",
        "VISUAL_ANALYSIS.md",
        "USER_GUIDE.md"
    ]
    
    for file_path in docs_dir.glob("*"):
        if file_path.is_file():
            if file_path.name not in core_docs_strict:
                os.remove(file_path)
                print(f"Deleted old doc: {file_path.name}")
                
    # 4. Update links in md files
    # We need to replace "docs/final/" with "docs/" or just "" if relative
    # In README.md: "docs/final/xyz.md" -> "docs/xyz.md"
    # In docs/USER_GUIDE.md: "final/xyz.md" -> "xyz.md" (since it's in same dir now)
    
    files_to_update = [base_dir / "README.md"] + list(docs_dir.glob("*.md"))
    
    for file_path in files_to_update:
        if not file_path.exists(): continue
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        new_content = content
        # Replace "docs/final/" -> "docs/"
        new_content = new_content.replace("docs/final/", "docs/")
        # Replace "final/" -> "" (for relative links inside docs folder)
        new_content = new_content.replace("final/", "")
        
        if content != new_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Updated links in {file_path.name}")

if __name__ == "__main__":
    cleanup_docs()
