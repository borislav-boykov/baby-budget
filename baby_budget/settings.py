"""Per-user settings: the language chosen last and the list file used last per language."""

from __future__ import annotations

import json
import os
from pathlib import Path


def config_dir() -> Path:
    override = os.environ.get("BABY_BUDGET_CONFIG_DIR")
    if override:
        return Path(override)
    base = os.environ.get("APPDATA") or Path.home() / ".config"
    return Path(base) / "baby-budget"


def _settings_file() -> Path:
    return config_dir() / "settings.json"


def _read() -> dict:
    try:
        data = json.loads(_settings_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _write(data: dict) -> None:
    try:
        _settings_file().parent.mkdir(parents=True, exist_ok=True)
        _settings_file().write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError:
        pass  # not being able to remember settings must never stop the app


def file_language(path: Path) -> str | None:
    """Language stored in a list file, without loading it fully. None if unreadable."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    lang = data.get("language") if isinstance(data, dict) else None
    return lang if lang in ("bg", "en") else "bg"


def _last_files() -> dict[str, str]:
    data = _read()
    files = data.get("last_files")
    if isinstance(files, dict):
        return {k: v for k, v in files.items() if isinstance(v, str)}
    legacy = data.get("last_file")  # version 1 settings: one file, any language
    if isinstance(legacy, str):
        return {file_language(Path(legacy)) or "bg": legacy}
    return {}


def last_language() -> str | None:
    lang = _read().get("language")
    return lang if lang in ("bg", "en") else None


def last_file(language: str) -> Path | None:
    value = _last_files().get(language)
    return Path(value) if value else None


def remember(language: str, path: Path) -> None:
    files = _last_files()
    files[language] = str(path)
    _write({"language": language, "last_files": files})


def default_data_file(language: str) -> Path:
    documents = Path.home() / "Documents"
    folder = documents if documents.is_dir() else Path.home()
    return folder / f"baby-budget-{language}.json"


def choose_file(language: str) -> Path:
    """The list to open for ``language``: the last one used, else a new file for the sample list.

    A file whose stored language differs is never picked; an unreadable one is
    (opening it offers to restore a backup).
    """
    for candidate in (last_file(language), default_data_file(language)):
        if candidate and candidate.exists() and file_language(candidate) in (language, None):
            return candidate
    path = default_data_file(language)
    n = 2
    while path.exists():  # taken by a list in the other language
        path = path.with_name(f"baby-budget-{language}-{n}.json")
        n += 1
    return path
