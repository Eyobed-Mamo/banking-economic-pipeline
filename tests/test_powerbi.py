"""Check that report field references match the delivered semantic model."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "powerbi"


def test_visual_fields_exist_in_model():
    tables = {t["name"]:t for t in json.loads((ROOT/"Banking.SemanticModel/model.bim").read_text())["model"]["tables"]}
    for path in (ROOT/"Banking.Report").rglob("visual.json"):
        v = json.loads(path.read_text())["visual"]
        for state in v.get("query",{}).get("queryState",{}).values():
            for p in state["projections"]:
                kind = next(iter(p["field"]))
                expr = p["field"][kind]
                table = tables[expr["Expression"]["SourceRef"]["Entity"]]
                members = table["measures" if kind == "Measure" else "columns"]
                assert expr["Property"] in {m["name"] for m in members}, str(path)


def test_relationships_reference_existing_columns():
    model = json.loads((ROOT/"Banking.SemanticModel/model.bim").read_text())["model"]
    columns = {t["name"]:{c["name"] for c in t["columns"]} for t in model["tables"]}
    for rel in model["relationships"]:
        assert rel["fromColumn"] in columns[rel["fromTable"]]
        assert rel["toColumn"] in columns[rel["toTable"]]
