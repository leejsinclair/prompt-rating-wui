from pathlib import Path
from typing import List, Optional

DEFAULT_PROJECTS_ROOT = Path.home() / ".claude" / "projects"


def discover_session_files(root: Optional[Path] = None) -> List[Path]:
    """Return every candidate session .jsonl under <root>/<project-dir>/, newest-modified first.

    A missing or unreadable root is not an error: it simply means no sessions exist yet.
    """
    root = Path(root) if root is not None else DEFAULT_PROJECTS_ROOT
    found: List[Path] = []
    try:
        project_dirs = [p for p in root.iterdir() if p.is_dir()]
    except OSError:
        return []
    for project_dir in project_dirs:
        try:
            found.extend(p for p in project_dir.glob("*.jsonl") if p.is_file())
        except OSError:
            continue

    def mtime(path: Path) -> float:
        try:
            return path.stat().st_mtime
        except OSError:
            return 0.0

    found.sort(key=mtime, reverse=True)
    return found
