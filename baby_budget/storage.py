"""Load and save the shopping list as a JSON file, with rotating backups."""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path

from .model import ShoppingList
from .templates import default_list

KEEP_BACKUPS = 10


def load(path: Path, language: str = "bg") -> ShoppingList:
    """Load the list, or return the starter template (in ``language``) if the file is missing.

    Raises ``ValueError`` (``json.JSONDecodeError`` is one) if the file is damaged.
    """
    if not path.exists():
        return default_list(language)
    try:
        with path.open(encoding="utf-8") as f:
            return ShoppingList.from_dict(json.load(f))
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError(f"unexpected content: {exc}") from exc


def save(shopping_list: ShoppingList, path: Path) -> None:
    """Write atomically, so a crash mid-save never leaves a half-written file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(shopping_list.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    os.replace(tmp, path)


def modified_time(path: Path) -> int | None:
    """Change marker used to notice edits made elsewhere (another PC via cloud sync)."""
    try:
        return path.stat().st_mtime_ns
    except FileNotFoundError:
        return None


def backup_dir(path: Path) -> Path:
    return path.parent / f"{path.stem}-backups"


def backup(path: Path, keep: int = KEEP_BACKUPS) -> Path | None:
    """Copy the file to ``<name>-backups/<name>-<timestamp>.json`` and keep the newest ``keep``."""
    if not path.exists():
        return None
    folder = backup_dir(path)
    folder.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    target = folder / f"{path.stem}-{stamp}{path.suffix}"
    shutil.copy2(path, target)
    for old in list_backups(path)[keep:]:
        old.unlink()
    return target


def list_backups(path: Path) -> list[Path]:
    """Backups of ``path``, newest first."""
    folder = backup_dir(path)
    if not folder.is_dir():
        return []
    return sorted(folder.glob(f"{path.stem}-*{path.suffix}"), reverse=True)


def restore_latest_valid(path: Path) -> Path | None:
    """Replace a damaged file with the newest backup that loads; keep the damaged copy aside."""
    for candidate in list_backups(path):
        try:
            load(candidate)
        except ValueError:
            continue
        if path.exists():
            os.replace(path, path.with_name(path.name + ".damaged"))
        shutil.copy2(candidate, path)
        return candidate
    return None
