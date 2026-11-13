"""Versioned save system: atomic writes, backup, corruption recovery."""
import json
import os
import tempfile

SAVE_VERSION = 3
DIR_NAME = ".space_miner"


def save_dir():
    return os.environ.get("SPACE_MINER_HOME", os.path.join(os.path.expanduser("~"), DIR_NAME))


def save_path():
    return os.path.join(save_dir(), "save.json")


def backup_path():
    return os.path.join(save_dir(), "save.json.bak")


def save(s, path=None):
    path = path or save_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    s["last_save"] = s.get("last_tick", 0.0)
    if os.path.exists(path):
        try:
            os.replace(path, backup_path())
        except OSError:
            pass
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".save-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(s, f, separators=(",", ":"))
        os.replace(tmp, path)
        return True
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return False


def load(path=None):
    """Load the newest valid save: main file first, then backup. Returns (state, source)."""
    path = path or save_path()
    for candidate, source in ((path, "main"), (backup_path(), "backup")):
        if not os.path.exists(candidate):
            continue
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError):
            continue
        from .state import migrate, validate
        data = migrate(data)
        if validate(data):
            return data, source
    return None, None
