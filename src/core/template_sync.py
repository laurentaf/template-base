import hashlib
import json
import shutil
from pathlib import Path

from src.core.config import settings

IGNORE_DIRS = {".venv", "__pycache__", ".git", ".gitignore", ".mypy_cache", ".pytest_cache"}
IGNORE_FILES = {"uv.lock", ".harness_state.json", ".template-info.json"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scan_template(root: str) -> dict[str, str]:
    root_p = Path(root)
    files = {}
    for fpath in sorted(root_p.rglob("*")):
        if not fpath.is_file():
            continue
        rel = str(fpath.relative_to(root_p))
        parts = set(rel.replace("\\", "/").split("/"))
        if IGNORE_DIRS & parts:
            continue
        if rel in IGNORE_FILES:
            continue
        files[rel] = _sha256(fpath)
    return files


def load_template_info(project_root: str) -> dict | None:
    path = Path(project_root) / ".template-info.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def save_template_info(project_root: str, source: str, commit: str, files: dict):
    path = Path(project_root) / ".template-info.json"
    info = {
        "source": source,
        "commit": commit,
        "files": files,
    }
    path.write_text(json.dumps(info, indent=2) + "\n")


def get_git_commit(path: str) -> str:
    try:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            cwd=path,
            timeout=10,
        )
        return result.stdout.strip() if result.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def sync_project(
    project_root: str,
    template_root: str | None = None,
    dry_run: bool = False,
) -> dict:
    templ = Path(template_root or settings.template_path)
    proj = Path(project_root)

    if not templ.exists():
        return {"success": False, "error": f"Template not found: {template_root}"}

    info = load_template_info(project_root)
    if info is None:
        return {"success": False, "error": "No .template-info.json found — run ltade-new first"}

    template_current = scan_template(str(templ))
    stored = info.get("files", {})

    updated: list[str] = []
    new_files: list[str] = []
    conflicts: list[str] = []
    unchanged: list[str] = []

    for rel, current_hash in template_current.items():
        proj_file = proj / rel
        if not proj_file.exists():
            new_files.append(rel)
            if not dry_run:
                proj_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(templ / rel, proj_file)
            continue

        stored_hash = stored.get(rel)
        proj_hash = _sha256(proj_file)

        if stored_hash == proj_hash:
            unchanged.append(rel)
            if current_hash != stored_hash:
                updated.append(rel)
                if not dry_run:
                    shutil.copy2(templ / rel, proj_file)
        elif current_hash != stored_hash:
            conflicts.append(rel)

    removed = [rel for rel in stored if rel not in template_current]

    if not dry_run and (updated or new_files or removed):
        save_template_info(project_root, str(templ), get_git_commit(str(templ)), template_current)

    return {
        "success": True,
        "total": len(template_current),
        "updated": updated,
        "new": new_files,
        "conflicts": conflicts,
        "removed": removed,
        "unchanged": len(unchanged),
    }
