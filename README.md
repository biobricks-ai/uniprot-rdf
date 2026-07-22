# uniprot-rdf

UniProt RDF complete dump as a BioBrick.

Downloads UniProtKB (Swiss-Prot reviewed entries + optionally TrEMBL) in
Turtle/RDF format from the official UniProt FTP server.

## Contents

| File | Size | Description |
|------|------|-------------|
| `uniprot_sprot.ttl.gz` | ~4 GB | Swiss-Prot reviewed entries (~570k proteins) |
| `uniprot_sprot_varsplic.ttl.gz` | ~100 MB | Splice isoforms |
| `enzyme.ttl.gz` | ~10 MB | Enzyme classification |
| `core.ttl.gz` | ~1 MB | Core ontology |
| `uniprot_trembl.ttl.gz` | ~70 GB | TrEMBL unreviewed (set `UNIPROT_FULL=1`) |

## SPARQL Endpoint

Official: https://sparql.uniprot.org/

## Usage

```bash
# Download core Swiss-Prot files (~5GB)
uv run python stages/01_download.py

# Download full dataset including TrEMBL (~75GB)
UNIPROT_FULL=1 uv run python stages/01_download.py

# Via DVC
dvc repro
```

For a bounded check that does not download the multi-gigabyte release, run
`python stages/00_probe_reference.py`. It records the official release version,
selected file sizes, and source MD5 checksums in `reports/remote-manifest.json`.
This establishes source discoverability only; it deliberately does not claim
that the local RDF conversion is complete or healthy.

## Schema

UniProt RDF uses the `up:` namespace (`http://purl.uniprot.org/core/`).
Key classes: `up:Protein`, `up:Gene`, `up:Taxon`.
Key properties: `up:recommendedName`, `up:organism`, `up:encodedBy`, `up:annotation`.
