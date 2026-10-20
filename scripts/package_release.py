"""
Package Release Tool for AI Job Agent
Creates a clean, security-audited distributable ZIP archive:
- EXCLUDES: .git, .venv, *.db, *.sqlite, *.env (preserves .env.example), uploads/resumes/*, __pycache__, .pytest_cache
- INCLUDES: All core source code, collectors, models, routes, services, templates, static, tests, extension, Docker files, requirements.txt, and documentation.
"""

import os
import zipfile
from pathlib import Path
from datetime import datetime

ROOT_DIR = Path(__file__).resolve().parent.parent

EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    ".idea",
    ".vscode",
    "instance"
}

EXCLUDE_FILES = {
    ".env",
    ".env.local"
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".log"
}

def is_excluded(rel_path: Path) -> bool:
    parts = rel_path.parts
    # Check directory exclusion
    for d in EXCLUDE_DIRS:
        if d in parts:
            return True

    # Check filename exclusion
    if rel_path.name in EXCLUDE_FILES:
        return True

    # Check extension exclusion
    if rel_path.suffix.lower() in EXCLUDE_EXTENSIONS:
        return True

    # Check uploads exclusion: keep .gitkeep, exclude user resumes
    if len(parts) >= 2 and parts[0] == "uploads" and parts[1] == "resumes":
        if rel_path.name != ".gitkeep":
            return True

    if len(parts) >= 2 and parts[0] == "uploads" and parts[1] == "test_resumes":
        if rel_path.name != ".gitkeep":
            return True

    return False

def build_clean_release(output_path: str = None) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if not output_path:
        output_path = str(ROOT_DIR / f"ai_job_agent_clean_release_{timestamp}.zip")

    print(f"Building clean release archive: {output_path}")
    total_files = 0

    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zip_out:
        for root, dirs, files in os.walk(ROOT_DIR):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(ROOT_DIR)

                if is_excluded(rel_path):
                    continue

                zip_out.write(full_path, arcname=str(rel_path))
                total_files += 1

    file_size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    print(f"Successfully packaged {total_files} files into clean archive ({file_size_mb:.2f} MB).")
    return output_path

if __name__ == "__main__":
    archive_path = build_clean_release()
    print("Archive ready at:", archive_path)
