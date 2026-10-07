"""Download the original sources into data/raw/ without modifying them.

Each file is stored as published; zips are extracted into their own folder and
plain files (e.g. the FGJ crime CSV) are copied into one. A manifest with
URL, download timestamp, size and SHA-256 is written to data/raw/manifest.json so
the exact source version is traceable.
"""
import hashlib
import json
import shutil
import zipfile
from datetime import datetime, timezone

import requests

from src.config import DATA_RAW, SOURCES

HEADERS = {"User-Agent": "Mozilla/5.0 (merida-urban-intelligence ETL)"}


def sha256(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def download(key: str, force: bool = False, previous_url: str | None = None) -> dict:
    src = SOURCES[key]
    fmt = src.get("format", "zip")
    file_path = DATA_RAW / f"{key}.{fmt}"
    out_dir = DATA_RAW / key
    if previous_url and previous_url != src["url"]:
        print(f"[download] {key}: URL changed since the last download, replacing the local copy")
        force = True
        shutil.rmtree(out_dir, ignore_errors=True)
    if force or not file_path.exists():
        print(f"[download] {key} <- {src['url']}")
        with requests.get(src["url"], headers=HEADERS, stream=True, timeout=300) as r:
            r.raise_for_status()
            with open(file_path, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
    else:
        print(f"[download] {key} already present, skipping")

    if not out_dir.exists():
        if fmt == "zip":
            # zipfile (not the unzip CLI) handles the non-UTF8 file names in the INEGI cartography zip
            with zipfile.ZipFile(file_path) as z:
                z.extractall(out_dir)
        else:
            out_dir.mkdir()
            shutil.copy2(file_path, out_dir / file_path.name)

    return {
        "key": key,
        "name": src["name"],
        "publisher": src["publisher"],
        "url": src["url"],
        "file": file_path.name,
        "bytes": file_path.stat().st_size,
        "sha256": sha256(file_path),
        "downloaded_at": datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc).isoformat(),
        "original_grain": src["original_grain"],
        "licence": src.get("licence"),
    }


def main(force: bool = False) -> None:
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    manifest_path = DATA_RAW / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for stale in set(manifest) - set(SOURCES):
        print(f"[download] {stale} is no longer a source, removed from the manifest")
        del manifest[stale]
    failed = {}
    for key in SOURCES:
        previous = manifest.get(key)
        try:
            entry = download(key, force=force, previous_url=previous and previous["url"])
        except requests.RequestException as e:
            failed[key] = e
            print(f"[download] ERROR: {key} could not be downloaded: {e}")
            continue
        if previous and previous["sha256"] != entry["sha256"]:
            print(f"[download] WARNING: {key} differs from the version recorded in the manifest")
        manifest[key] = entry
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"[download] manifest written to {manifest_path}")
    if failed:
        raise SystemExit(f"[download] failed sources: {', '.join(failed)}")


if __name__ == "__main__":
    main()
