#!/usr/bin/env bash
# Convert UniProt RDF/XML (.rdf.xz) to N-Triples (.nt.gz) for QLever ingestion.
# Requires raptor2: sudo apt install raptor2-utils
# Output: brick/*.nt.gz  (about 3x larger than .rdf.xz)

set -euo pipefail

if ! command -v rapper &>/dev/null; then
    echo "ERROR: 'rapper' not found. Install: sudo apt install raptor2-utils"
    exit 1
fi

mkdir -p brick

TOTAL=$(ls download/*.rdf.xz download/*.owl 2>/dev/null | wc -l)
DONE=0

for f in download/*.rdf.xz download/*.owl; do
    [[ -f "$f" ]] || continue
    base="$(basename "$f")"
    # Strip .xz if present
    stripped="${base%.xz}"
    # Change extension to .nt.gz
    out="brick/${stripped%.rdf}.nt.gz"
    # Also handle .owl
    out="${out%.owl}.nt.gz"

    if [[ -f "$out" ]]; then
        echo "  [skip] $base (exists)"
        DONE=$((DONE+1))
        continue
    fi

    echo "  [$(( DONE+1 ))/$TOTAL] Converting: $base → $(basename $out)"

    if [[ "$f" == *.xz ]]; then
        xz -dc "$f" | rapper -q -i rdfxml -o ntriples - "http://purl.uniprot.org/" 2>/dev/null | gzip -c > "$out"
    else
        rapper -q -i rdfxml -o ntriples "$f" "http://purl.uniprot.org/" 2>/dev/null | gzip -c > "$out"
    fi

    DONE=$((DONE+1))
done

echo ""
echo "Conversion complete: $DONE files in brick/"
ls -lh brick/*.nt.gz 2>/dev/null | awk '{sum+=$5; print} END {printf "Total: %.2f GB\n", sum/1e9}'
