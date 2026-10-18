"""P100: external identifiers, store-only. ontology/external_ids.csv (id, kind, qudt_quantity_kind, qudt_unit, pubchem_cid, confidence
sure | check, note; written from knowledge, no network; blanks allowed) is copied into ontology.yaml: a quantity entry gets the optional
lines qudt_quantity_kind and qudt_unit after its unit line, a species entry pubchem_cid after its formula line. Nothing at runtime reads
these fields (export.py does not emit them); make_report.py lists the coverage. Idempotent: an existing line is replaced. Pending
entries (pending.csv) have no yaml block; their rows stay in the csv only."""
import csv, pathlib, re

HERE = pathlib.Path(__file__).resolve().parent
FIELDS = {"quantity": ["qudt_quantity_kind", "qudt_unit"], "species": ["pubchem_cid"]}
AFTER = {"quantity": "unit", "species": "formula"}


def apply():
    rows = {r["id"]: r for r in csv.DictReader((HERE / "external_ids.csv").open(newline="", encoding="utf-8"))}
    text = (HERE / "ontology.yaml").read_text(encoding="utf-8")
    blocks = re.split(r"(?m)^(?=  - id: )", text)
    done, skipped = 0, []
    for b, blk in enumerate(blocks):
        m = re.match(r"  - id: (\S+)\n", blk)
        if not m or m.group(1) not in rows:
            continue
        r = rows[m.group(1)]; kind = r["kind"]
        lines = blk.split("\n")
        for f in FIELDS[kind]:                                                  # drop an existing line, then insert after the anchor line
            lines = [l for l in lines if not re.match(rf"    {f}:", l)]
        vals = [(f, r[f]) for f in FIELDS[kind] if r[f]]
        if not vals:
            continue
        i = next((j for j, l in enumerate(lines) if re.match(rf"    {AFTER[kind]}:", l)), None)
        if i is None:
            skipped.append(m.group(1)); continue
        ins = [f"    {f}: {v}" if f == "pubchem_cid" else f'    {f}: "{v}"' for f, v in vals]
        lines[i + 1:i + 1] = ins
        blocks[b] = "\n".join(lines); done += 1
    (HERE / "ontology.yaml").write_text("".join(blocks), encoding="utf-8")
    print(f"external ids applied to {done} entries" + (f"; no anchor line in {skipped}" if skipped else ""))


if __name__ == "__main__":
    apply()
