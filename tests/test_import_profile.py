import json
from pathlib import Path
import importlib.util

ROOT=Path(__file__).resolve().parents[1]

def test_dvc_pipeline_declares_materialized_outputs():
    pipeline=(ROOT/"dvc.yaml").read_text()
    assert "outs:" in pipeline
    assert any(token in pipeline for token in ("download","brick"))

def test_reference_profile_does_not_claim_tabular_coverage():
    coverage=json.loads((ROOT/"health/source-coverage.json").read_text())
    policy=json.loads((ROOT/"health/ontology-policy.json").read_text())
    status=json.loads((ROOT/"health/build-status.json").read_text())
    assert coverage["profile"]=="reference-rdf-import"
    assert coverage["tabular_conversion_coverage"]=="not-applicable"
    assert "source_checksum" in coverage["integrity_metrics"]
    assert policy["schema_ownership"]=="upstream"
    assert status["profile"]=="reference-rdf-import"

def test_remote_manifest_report_is_complete_but_not_artifact_validation():
    report=json.loads((ROOT/"reports/remote-manifest.json").read_text())
    assert report["status"]=="remote-manifest-verified"
    assert report["selected_file_count"] > 8
    assert report["files_with_md5"]==report["selected_file_count"]
    assert report["selected_bytes"]==sum(f["size_bytes"] for f in report["files"])
    assert all(len(f["md5"])==32 for f in report["files"])
    integrity=json.loads((ROOT/"reports/reference-integrity.json").read_text())
    assert integrity["status"]=="insufficient-evidence"

def test_manifest_parser_selects_only_reviewed_and_reference_files():
    spec=importlib.util.spec_from_file_location("probe",ROOT/"stages/00_probe_reference.py")
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    fixture=b'''<metalink xmlns="http://www.metalinker.org/" version="3.0"><updated>2026-01-01</updated><version>v1</version><files>
    <file name="core.owl"><size>10</size><verification><hash type="md5">00000000000000000000000000000000</hash></verification></file>
    <file name="uniprotkb_reviewed_a.rdf.xz"><size>20</size><verification><hash type="md5">11111111111111111111111111111111</hash></verification></file>
    <file name="uniprotkb_unreviewed_a.rdf.xz"><size>30</size><verification><hash type="md5">22222222222222222222222222222222</hash></verification></file>
    </files></metalink>'''
    report=module.build_report(fixture)
    assert [f["name"] for f in report["files"]]==["core.owl","uniprotkb_reviewed_a.rdf.xz"]
    assert report["selected_bytes"]==30
