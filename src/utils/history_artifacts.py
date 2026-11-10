"""Restore persistent likes history from GitHub Actions artifacts, without Git writes."""

import argparse
import copy
import io
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import date, datetime
from pathlib import Path

from src.core.like_history import HISTORY_PATH, IST, get_operational_date, rebuild_daily_changes


ARTIFACT_NAME = "like-history"
MAX_HISTORY_BYTES = 10 * 1024 * 1024
WORKFLOW_PATH = ".github/workflows/fleet-runner.yml"


def _timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("History observation must include its timezone")
    return result


def validate_history(data: dict) -> dict:
    if not isinstance(data, dict) or not isinstance(data.get("uids"), dict):
        raise ValueError("History must contain a uids object")
    if data.get("timezone") not in ("Asia/Kolkata", "Asia/Calcutta"):
        raise ValueError("History must use the IST calendar")
    for uid, entry in data["uids"].items():
        if not isinstance(uid, str) or not re.fullmatch(r"\d+", uid):
            raise ValueError("History contains an invalid UID")
        if not isinstance(entry, dict) or not isinstance(entry.get("daily"), dict):
            raise ValueError(f"UID {uid} has no daily history object")
        for day, sample in entry["daily"].items():
            if date.fromisoformat(day).isoformat() != day or not isinstance(sample, dict):
                raise ValueError(f"UID {uid} has an invalid daily sample")
            likes = sample.get("likes")
            if isinstance(likes, bool) or not isinstance(likes, int) or likes < 0:
                raise ValueError(f"UID {uid} has an invalid likes value")
            if get_operational_date(_timestamp(sample["observed_at"])) != day:
                raise ValueError(f"UID {uid} observation does not match its IST operational date")
    return data


def merge_history(restored: dict, seed: dict | None) -> dict:
    """Retain all history and choose the newer observation for each UID/day."""
    merged = copy.deepcopy(validate_history(restored))
    if seed is not None:
        validate_history(seed)
        for uid, seed_entry in seed["uids"].items():
            entry = merged["uids"].setdefault(uid, {"daily": {}})
            changed = False
            for day, sample in seed_entry["daily"].items():
                existing = entry["daily"].get(day)
                if not existing or _timestamp(sample["observed_at"]) > _timestamp(existing["observed_at"]):
                    entry["daily"][day] = copy.deepcopy(sample)
                    changed = True
            if changed:
                # The daily snapshots cannot reconstruct every within-day query.
                entry["change_from_previous_observation"] = None
    merged["timezone"] = "Asia/Kolkata"
    rebuild_daily_changes(merged)
    return merged


def history_from_archive(archive: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
        files = [item for item in bundle.infolist() if not item.is_dir()]
        if len(files) != 1 or files[0].filename not in ("like_history.json", "data/like_history.json"):
            raise ValueError("History artifact must contain only like_history.json")
        if files[0].file_size > MAX_HISTORY_BYTES:
            raise ValueError("History artifact exceeds the maximum history size")
        return validate_history(json.loads(bundle.read(files[0]).decode("utf-8")))


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, new_url):
        return None


class GitHubHistoryArtifacts:
    def __init__(self, repository: str, token: str, branch: str = "", run_id: str = ""):
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
            raise ValueError("GITHUB_REPOSITORY must be owner/repository")
        if not token:
            raise ValueError("GITHUB_TOKEN is required for history restoration")
        self.base = f"https://api.github.com/repos/{repository}"
        self.branch = branch
        self.run_id = run_id
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "telegram-like-history",
        }

    def get_json(self, path: str) -> dict:
        request = urllib.request.Request(self.base + path, headers=self.headers)
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)

    def latest_artifact(self) -> dict | None:
        artifacts = []
        page = 1
        while True:
            payload = self.get_json(
                f"/actions/artifacts?name={ARTIFACT_NAME}&per_page=100&page={page}"
            )
            batch = payload["artifacts"]
            artifacts.extend(item for item in batch if item.get("name") == ARTIFACT_NAME)
            if len(batch) < 100:
                break
            page += 1
        if not artifacts:
            return None
        candidates = sorted(artifacts, key=lambda item: item["created_at"], reverse=True)
        for artifact in candidates:
            run = artifact.get("workflow_run", {})
            if artifact.get("expired") or str(run.get("id")) == self.run_id:
                continue
            if self.branch and run.get("head_branch") != self.branch:
                continue
            details = self.get_json(f"/actions/runs/{int(run['id'])}")
            if details.get("status") != "completed":
                continue
            if details.get("path", "").split("@", 1)[0] != WORKFLOW_PATH:
                continue
            if details.get("event") not in ("workflow_dispatch", "schedule"):
                continue
            return artifact
        raise RuntimeError(
            "History artifacts exist, but none is an unexpired completed fleet snapshot "
            "for this branch; refusing to reset history to the seed"
        )

    def download_archive(self, artifact_id: int) -> bytes:
        request = urllib.request.Request(
            f"{self.base}/actions/artifacts/{int(artifact_id)}/zip", headers=self.headers
        )
        # GitHub returns a signed storage URL. Never forward the API token to it.
        opener = urllib.request.build_opener(_NoRedirect())
        try:
            with opener.open(request, timeout=30) as response:
                archive = response.read(MAX_HISTORY_BYTES * 2 + 1)
        except urllib.error.HTTPError as error:
            if error.code != 302:
                raise
            location = error.headers.get("Location", "")
            parsed = urllib.parse.urlsplit(location)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError("GitHub returned an invalid artifact download URL") from error
            with urllib.request.urlopen(location, timeout=30) as response:
                archive = response.read(MAX_HISTORY_BYTES * 2 + 1)
        if len(archive) > MAX_HISTORY_BYTES * 2:
            raise ValueError("History archive is too large")
        return archive


def restore_history(client: GitHubHistoryArtifacts, path: Path = HISTORY_PATH) -> str:
    seed = validate_history(json.loads(path.read_text(encoding="utf-8"))) if path.exists() else None
    artifact = client.latest_artifact()
    if artifact is None:
        if seed is None:
            raise FileNotFoundError("No prior history artifact or committed history seed was found")
        print(f"No prior history artifact; using committed seed at {path}")
        return "seed"
    restored = history_from_archive(client.download_archive(artifact["id"]))
    merged = merge_history(restored, seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.restore.tmp")
    temporary.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)
    print(f"Restored artifact {artifact['id']} and merged seed into {path}")
    return "artifact"


def main() -> None:
    parser = argparse.ArgumentParser(description="Restore likes history from GitHub Actions artifacts")
    parser.add_argument("action", choices=["restore"])
    args = parser.parse_args()
    client = GitHubHistoryArtifacts(
        os.environ.get("GITHUB_REPOSITORY", ""),
        os.environ.get("GITHUB_TOKEN", ""),
        os.environ.get("GITHUB_REF_NAME", ""),
        os.environ.get("GITHUB_RUN_ID", ""),
    )
    if args.action == "restore":
        restore_history(client)


if __name__ == "__main__":
    main()
