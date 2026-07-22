#!/usr/bin/env python3
"""Collect bounded, metadata-only evidence for the current UniProt RDF release."""

import argparse
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

METALINK = "https://ftp.ebi.ac.uk/pub/databases/uniprot/current_release/rdf/RELEASE.metalink"
ALWAYS = {
    "core.owl", "diseases.rdf.xz", "enzyme.rdf.xz",
    "enzyme-hierarchy.rdf.xz", "keywords.rdf.xz", "taxonomy.rdf.xz",
    "tissues.rdf.xz", "pathways.rdf.xz",
}
NS = {"m": "http://www.metalinker.org/"}
UA = "BioBricks reference-integrity probe/1.0 (https://biobricks.ai)"


def fetch(url: str) -> bytes:
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60).read()


def build_report(xml: bytes) -> dict:
    root = ET.fromstring(xml)
    files = []
    for node in root.findall(".//m:file", NS):
        name = node.attrib["name"]
        if name not in ALWAYS and "uniprotkb_reviewed_" not in name:
            continue
        size = int(node.findtext("m:size", namespaces=NS))
        checksum = node.findtext("m:verification/m:hash[@type='md5']", namespaces=NS)
        files.append({"name": name, "size_bytes": size, "md5": checksum})
    files.sort(key=lambda item: item["name"])
    return {
        "status": "remote-manifest-verified",
        "profile": "reference-rdf-import",
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "release": root.findtext("m:version", namespaces=NS),
        "release_updated": root.findtext("m:updated", namespaces=NS),
        "manifest_url": METALINK,
        "manifest_bytes": len(xml),
        "selected_mode": "reviewed-plus-reference",
        "selected_file_count": len(files),
        "selected_bytes": sum(item["size_bytes"] for item in files),
        "files_with_md5": sum(bool(item["md5"]) for item in files),
        "files": files,
        "limitations": [
            "Remote metadata does not prove that brick artifacts are materialized.",
            "Source bytes, converted statements, and complete subjects were not parsed.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("reports/remote-manifest.json"))
    args = parser.parse_args()
    report = build_report(fetch(METALINK))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "release", "selected_file_count", "selected_bytes", "files_with_md5")}, indent=2))


if __name__ == "__main__":
    main()
