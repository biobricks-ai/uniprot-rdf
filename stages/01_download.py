#!/usr/bin/env python3
"""
Download UniProt RDF complete dump files.

Downloads the current UniProt release in RDF/XML format from the official
FTP server. The dump contains all UniProtKB (Swiss-Prot + TrEMBL) entries
as RDF.

Approximate sizes:
  - uniprot_sprot.ttl.gz  ~  4 GB  (Swiss-Prot ~570k reviewed entries)
  - uniprot_trembl.ttl.gz ~ 70 GB  (TrEMBL ~250M unreviewed entries)
  - Full RDF set (all files) ~ 120 GB compressed

This script downloads the Swiss-Prot reviewed entries by default for
reasonable size. Set UNIPROT_FULL=1 to download all TrEMBL entries too.
"""

import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests
from tqdm import tqdm

BASE_URL = "https://ftp.ebi.ac.uk/pub/databases/uniprot/current_release/rdf"
CHUNK_SIZE = 8 * 1024 * 1024  # 8MB

# Files to download. Set UNIPROT_FULL=1 to also download TrEMBL (~70GB).
CORE_FILES = [
    "uniprot_sprot.ttl.gz",       # Swiss-Prot reviewed (~4GB)
    "uniprot_sprot_varsplic.ttl.gz",
    "enzyme.ttl.gz",
    "core.ttl.gz",
]

FULL_FILES = CORE_FILES + [
    "uniprot_trembl.ttl.gz",      # TrEMBL unreviewed (~70GB)
]


def get_release_info():
    """Fetch the release version from the notes file."""
    url = f"{BASE_URL}/../../docs/relnotes.txt"
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        for line in r.text.splitlines():
            if "UniProt Release" in line:
                return line.strip()
    except Exception:
        pass
    return datetime.now().strftime("release-%Y%m")


def get_file_size(url):
    """Get Content-Length for a URL."""
    r = requests.head(url, timeout=30, allow_redirects=True)
    r.raise_for_status()
    return int(r.headers.get("content-length", 0))


def download_file(url, dest: Path, expected_size: int = 0):
    """Download with resume support and progress bar."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    existing = dest.stat().st_size if dest.exists() else 0

    if existing and existing == expected_size:
        print(f"  Already complete: {dest.name}")
        return

    headers = {}
    mode = "wb"
    if existing and expected_size and existing < expected_size:
        print(f"  Resuming from {existing:,} bytes: {dest.name}")
        headers["Range"] = f"bytes={existing}-"
        mode = "ab"

    r = requests.get(url, headers=headers, stream=True, timeout=60)
    r.raise_for_status()

    total = expected_size or int(r.headers.get("content-length", 0))
    bar = tqdm(
        total=total,
        initial=existing,
        unit="B",
        unit_scale=True,
        unit_divisor=1024,
        desc=dest.name,
    )
    with open(dest, mode) as f:
        for chunk in r.iter_content(chunk_size=CHUNK_SIZE):
            if chunk:
                f.write(chunk)
                bar.update(len(chunk))
    bar.close()


def main():
    download_dir = Path("download")
    download_dir.mkdir(exist_ok=True)

    full = os.environ.get("UNIPROT_FULL", "0") == "1"
    files = FULL_FILES if full else CORE_FILES

    print(f"UniProt RDF download ({'full' if full else 'core Swiss-Prot'} mode)")
    print(f"Source: {BASE_URL}")
    print()

    release = get_release_info()
    print(f"Release: {release}\n")

    metadata = {"release": release, "files": [], "download_date": datetime.now().isoformat()}

    for fname in files:
        url = f"{BASE_URL}/{fname}"
        dest = download_dir / fname
        print(f"Downloading {fname}...")
        try:
            size = get_file_size(url)
            download_file(url, dest, size)
            metadata["files"].append({"name": fname, "url": url, "size_bytes": size})
            print(f"  Done: {dest}")
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            sys.exit(1)

    meta_path = download_dir / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nDownload complete. Metadata: {meta_path}")


if __name__ == "__main__":
    main()
