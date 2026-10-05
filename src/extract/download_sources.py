"""Download the original INEGI sources into data/raw/ without modifying them.

Each zip is stored as published and extracted into its own folder. A manifest with
URL, download timestamp, size and SHA-256 is written to data/raw/manifest.json so
the exact source version is traceable.
"""
import hashlib
import json
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


def download(key: str, force: bool = False) -> dict:
    src = SOURCES[key]
    zip_path = DATA_RAW / f"{key}.zip"
    if force or not zip_path.exists():
        print(f"[download] {key} <- {src['url']}")
        with requests.get(src["url"], headers=HEADERS, stream=True, timeout=300) as r:
            r.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
    else:
        print(f"[download] {key} already present, skipping")

    out_dir = DATA_RAW / key
    if not out_dir.exists():
        # zipfile (not the unzip CLI) handles the non-UTF8 file names in the INEGI cartography zip
        with zipfile.ZipFile(zip_path) as z:
            z.extractall(out_dir)

    return {
        "key": key,
        "name": src["name"],
        "publisher": src["publisher"],
        "url": src["url"],
        "file": zip_path.name,
        "bytes": zip_path.stat().st_size,
        "sha256": sha256(zip_path),
        "downloaded_at": datetime.fromtimestamp(zip_path.stat().st_mtime, timezone.utc).isoformat(),
        "original_grain": src["original_grain"],
    }


def main(force: bool = False) -> None:
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    manifest_path = DATA_RAW / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for key in SOURCES:
        entry = download(key, force=force)
        previous = manifest.get(key)
        if previous and previous["sha256"] != entry["sha256"]:
            print(f"[download] WARNING: {key} differs from the version recorded in the manifest")
        manifest[key] = entry
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
    print(f"[download] manifest written to {manifest_path}")


if __name__ == "__main__":
    main()
