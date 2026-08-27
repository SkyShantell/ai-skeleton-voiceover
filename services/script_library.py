from __future__ import annotations

import base64
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests


class ScriptLibraryError(RuntimeError):
    pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _normalize_library(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, list):
        return []
    items: list[dict[str, Any]] = []
    for item in data:
        if isinstance(item, dict) and item.get("id"):
            items.append(item)
    return items


def _load_local(path: Path) -> list[dict[str, Any]]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("[]\n", encoding="utf-8")
        return []
    try:
        return _normalize_library(json.loads(path.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError) as exc:
        raise ScriptLibraryError(f"Could not read the local script library: {exc}") from exc


def _write_local(path: Path, scripts: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(scripts, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _github_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "ai-skeleton-voiceover-script-library",
    }


def _github_get(
    token: str,
    repo: str,
    remote_path: str,
) -> tuple[list[dict[str, Any]], str | None]:
    url = f"https://api.github.com/repos/{repo}/contents/{remote_path.lstrip('/')}"
    response = requests.get(url, headers=_github_headers(token), timeout=30)
    if response.status_code == 404:
        return [], None
    if response.status_code != 200:
        raise ScriptLibraryError(
            f"GitHub script library read failed ({response.status_code}). "
            "Check SCRIPT_LIBRARY_GITHUB_TOKEN, repository name, and Contents permission."
        )
    payload = response.json()
    encoded = str(payload.get("content") or "").replace("\n", "")
    try:
        raw = base64.b64decode(encoded).decode("utf-8") if encoded else "[]"
        scripts = _normalize_library(json.loads(raw))
    except Exception as exc:
        raise ScriptLibraryError(f"Could not decode the GitHub script library: {exc}") from exc
    return scripts, payload.get("sha")


def _github_put(
    token: str,
    repo: str,
    remote_path: str,
    scripts: list[dict[str, Any]],
    sha: str | None,
    message: str,
) -> None:
    url = f"https://api.github.com/repos/{repo}/contents/{remote_path.lstrip('/')}"
    raw = json.dumps(scripts, indent=2, ensure_ascii=False) + "\n"
    body: dict[str, Any] = {
        "message": message,
        "content": base64.b64encode(raw.encode("utf-8")).decode("ascii"),
    }
    if sha:
        body["sha"] = sha
    response = requests.put(url, headers=_github_headers(token), json=body, timeout=30)
    if response.status_code not in (200, 201):
        raise ScriptLibraryError(
            f"GitHub script library write failed ({response.status_code}). "
            "The token needs Contents: Read and write permission for this repository."
        )


def storage_mode(token: str = "", repo: str = "") -> str:
    return "github" if token.strip() and repo.strip() else "local"


def load_scripts(
    local_path: str | Path,
    github_token: str = "",
    github_repo: str = "",
    github_path: str = "data/saved_scripts.json",
) -> tuple[list[dict[str, Any]], str]:
    mode = storage_mode(github_token, github_repo)
    if mode == "github":
        scripts, _ = _github_get(github_token.strip(), github_repo.strip(), github_path)
    else:
        scripts = _load_local(Path(local_path))
    scripts.sort(key=lambda x: str(x.get("updated_at") or x.get("created_at") or ""), reverse=True)
    return scripts, mode


def upsert_script(
    entry: dict[str, Any],
    local_path: str | Path,
    github_token: str = "",
    github_repo: str = "",
    github_path: str = "data/saved_scripts.json",
    force_new: bool = False,
) -> tuple[dict[str, Any], str]:
    mode = storage_mode(github_token, github_repo)
    if mode == "github":
        scripts, sha = _github_get(github_token.strip(), github_repo.strip(), github_path)
    else:
        scripts = _load_local(Path(local_path))
        sha = None

    now = _now_iso()
    item = dict(entry)
    existing_id = str(item.get("id") or "").strip()
    if force_new or not existing_id:
        existing_id = uuid.uuid4().hex
        item["id"] = existing_id
        item["created_at"] = now
    else:
        old = next((x for x in scripts if str(x.get("id")) == existing_id), None)
        item["created_at"] = (old or {}).get("created_at", item.get("created_at", now))
    item["updated_at"] = now

    replaced = False
    for idx, current in enumerate(scripts):
        if str(current.get("id")) == existing_id:
            scripts[idx] = item
            replaced = True
            break
    if not replaced:
        scripts.append(item)

    scripts.sort(key=lambda x: str(x.get("updated_at") or ""), reverse=True)
    if mode == "github":
        _github_put(
            github_token.strip(),
            github_repo.strip(),
            github_path,
            scripts,
            sha,
            f"Save script: {item.get('title') or item.get('product_name') or existing_id}",
        )
    else:
        _write_local(Path(local_path), scripts)
    return item, mode


def delete_script(
    script_id: str,
    local_path: str | Path,
    github_token: str = "",
    github_repo: str = "",
    github_path: str = "data/saved_scripts.json",
) -> str:
    mode = storage_mode(github_token, github_repo)
    if mode == "github":
        scripts, sha = _github_get(github_token.strip(), github_repo.strip(), github_path)
    else:
        scripts = _load_local(Path(local_path))
        sha = None

    remaining = [x for x in scripts if str(x.get("id")) != str(script_id)]
    if len(remaining) == len(scripts):
        raise ScriptLibraryError("Saved script was not found.")

    if mode == "github":
        _github_put(
            github_token.strip(),
            github_repo.strip(),
            github_path,
            remaining,
            sha,
            "Delete saved script",
        )
    else:
        _write_local(Path(local_path), remaining)
    return mode
