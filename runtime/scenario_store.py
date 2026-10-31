"""Persist scenario revision identities for the single-process demo runtime."""
import json
import threading
from pathlib import Path
from uuid import uuid4

from runtime.scenario_loader import InputError

_LOCK = threading.Lock()


def claim_revision(directory: Path, scenario_id: str, version: int, digest: str):
    """An existing (scenario ID, version) can be replayed only with identical data.

    A changed environment needs a new version and a fresh run. One process is the
    supported deployment: this file is not a distributed lock or database.
    """
    path = directory / "scenario-revisions.json"
    with _LOCK:
        index = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        versions = index.setdefault(scenario_id, {})
        existing = versions.get(str(version))
        if existing is not None:
            if existing != digest:
                raise InputError("SCENARIO_VERSION_CONFLICT", "Scenario data changed: increment scenario_version and start a new run")
            return
        if versions and version <= max(map(int, versions)):
            raise InputError("SCENARIO_VERSION_CONFLICT", "New scenario revisions must increase scenario_version")
        versions[str(version)] = digest
        temporary = directory / f".{uuid4().hex}.revisions.tmp"
        temporary.write_text(json.dumps(index, sort_keys=True), encoding="utf-8")
        temporary.replace(path)
