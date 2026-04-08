#!/usr/bin/env python3
"""
Download UniProt RDF complete dump files.

Downloads the current UniProt release in RDF/XML format from the official
FTP server. Uses reviewed (Swiss-Prot) entries by default for a manageable
size. Set UNIPROT_FULL=1 to also download unreviewed TrEMBL entries.

Approximate sizes:
  - Reviewed (Swiss-Prot): ~30 files, ~3-5 GB compressed total
  - Full (+ TrEMBL): ~700+ files, ~150 GB compressed total
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from tqdm import tqdm

BASE_URL = "https://ftp.ebi.ac.uk/pub/databases/uniprot/current_release/rdf"
CHUNK_SIZE = 8 * 1024 * 1024  # 8MB

# Always download these ontology/reference files
ALWAYS_FILES = [
    "core.owl",
    "diseases.rdf.xz",
    "enzyme.rdf.xz",
    "enzyme-hierarchy.rdf.xz",
    "keywords.rdf.xz",
    "taxonomy.rdf.xz",
    "tissues.rdf.xz",
    "pathways.rdf.xz",
]


def list_rdf_files():
    """List all .rdf.xz and .owl files from the UniProt FTP directory."""
    r = requests.get(BASE_URL + "/", timeout=30)
    r.raise_for_status()
    return re.findall(r'href="([^"]+\.(?:rdf\.xz|owl))"', r.text)


def get_file_size(url):
    r = requests.head(url, timeout=30, allow_redirects=True)
    r.raise_for_status()
    return int(r.headers.get("content-length", 0))


def download_file(url, dest: Path, expected_size: int = 0):
    dest.parent.mkdir(parents=True, exist_ok=True)
    existing = dest.stat().st_size if dest.exists() else 0

    if existing and expected_size and existing == expected_size:
        print(f"  Already complete: {dest.name}")
        return

    headers = {}
    mode = "wb"
    if existing and expected_size and 0 < existing < expected_size:
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
    print(f"UniProt RDF download ({'full incl. TrEMBL' if full else 'reviewed Swiss-Prot only'} mode)")
    print(f"Source: {BASE_URL}\n")

    print("Scanning FTP directory...")
    all_files = list_rdf_files()

    # Select files based on mode
    to_download = list(ALWAYS_FILES)
    for f in all_files:
        if "uniprotkb_reviewed_" in f:
            # Reviewed (Swiss-Prot) — always include
            to_download.append(f)
        elif full and "uniprotkb_unreviewed_" in f:
            # TrEMBL only in full mode
            to_download.append(f)

    # Deduplicate while preserving order
    seen = set()
    to_download = [f for f in to_download if not (f in seen or seen.add(f))]

    print(f"Files to download: {len(to_download)}")

    metadata = {
        "mode": "full" if full else "reviewed",
        "source": BASE_URL,
        "files": [],
        "download_date": datetime.now().isoformat(),
    }

    total_size = 0
    for fname in to_download:
        url = f"{BASE_URL}/{fname}"
        dest = download_dir / fname
        try:
            size = get_file_size(url)
        except Exception:
            size = 0

        total_size += size
        print(f"\nDownloading {fname} ({size/1e6:.0f} MB)...")
        try:
            download_file(url, dest, size)
            metadata["files"].append({"name": fname, "url": url, "size_bytes": size})
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            sys.exit(1)

    meta_path = download_dir / "metadata.json"
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"\nDownload complete: {len(to_download)} files, {total_size/1e9:.2f} GB total")
    print(f"Metadata: {meta_path}")


if __name__ == "__main__":
    main()
