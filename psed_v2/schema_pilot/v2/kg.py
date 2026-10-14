#!/usr/bin/env python3
"""Builds a knowledge graph from the five v2 tables of the pilot papers (the tables stay the source of truth).

    python3 psed_v2/schema_pilot/v2/kg.py

Writes v2/kg/graph.json (nodes, edges with attributes) and v2/kg/graph.graphml.
Nodes: paper, sample, group, condition, series, value, and shared quantity, material, chemical, method, structure_class,
process_mode. Edges: in_paper (sample→paper), member_of (sample→group), child_of (piece→parent), of_sample / of_paper
(condition→sample, or →paper for "*"), has_quantity (condition/value→quantity), of_sample (series/value→sample),
uses_method (series→method), axis_x / axis_y / axis_z (series→quantity), from_series (value→series), made_of (sample→material),
uses_chemical (sample→chemical, role precursor or coreactant), has_structure (sample→structure_class), has_process (sample→process_mode).
Qualifiers, data_kind, step, unit, evidence and the other columns are attributes.
"""
import csv, json, re, sys
from pathlib import Path
from xml.sax.saxutils import escape

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from inventory import PAPERS

CHEM = {"trimethylaluminum": "TMA", "trimethylaluminium": "TMA", "al(ch3)3": "TMA", "tma": "TMA", "water": "H2O", "h2o": "H2O",
        "diethylzinc": "DEZ", "dez": "DEZ", "zn(c2h5)2": "DEZ", "ozone": "O3"}


def chemicals(text):
    out = []
    for part in re.split(r"[/,;+]| and ", text or ""):
        p = re.sub(r"\b(remote|plasma|ICP|gas|vapou?r|mixed|mixture|pulse|exposure|\(.*?\))\b", " ", part, flags=re.I).strip(" .")
        if not p or len(p) > 40:
            continue
        out.append(CHEM.get(p.lower(), p))
    return list(dict.fromkeys(out))


def build():
    nodes, edges = {}, []

    def node(nid, ntype, paper="", **attrs):
        if nid not in nodes:
            nodes[nid] = {"id": nid, "type": ntype, "paper": paper, **{k: v for k, v in attrs.items() if v not in ("", None)}}
        return nid

    def edge(a, b, etype, **attrs):
        edges.append({"source": a, "target": b, "type": etype, **{k: v for k, v in attrs.items() if v not in ("", None)}})

    def qnode(q, label):
        return node(f"quantity:{q}" if q != "other" else f"quantity:other:{re.sub(r'{.*', '', label).strip()}", "quantity", "", label=q if q != "other" else label)
    for pid, key in PAPERS.items():
        D = HERE / pid
        T = {t: list(csv.DictReader((D / f"{t}.csv").open(encoding="utf-8"))) for t in ("paper", "sample", "condition", "series", "value") if (D / f"{t}.csv").exists()}
        if not T.get("sample"):
            continue
        p = T["paper"][0]
        pn = node(f"paper:{pid}", "paper", key, label=key, year=p.get("year"), topic=p.get("topic"))
        for s in T["sample"]:
            sn = node(f"sample:{s['sample_id']}", "group" if s["kind"] == "group" else "sample", key, label=s["sample_id"],
                      **{k: v for k, v in s.items() if k not in ("sample_id", "paper_id")})
            edge(sn, pn, "in_paper")
            if s["parent_sample"]:
                edge(sn, f"sample:{s['parent_sample']}", "child_of")
            for m in filter(None, s["members"].split(";")):
                edge(f"sample:{m}", sn, "member_of")
            if s["material"]:
                edge(sn, node(f"material:{s['material']}", "material", "", label=s["material"]), "made_of")
            for role in ("precursor", "coreactant"):
                for c in chemicals(s[role]):
                    edge(sn, node(f"chemical:{c}", "chemical", "", label=c), "uses_chemical", role=role)
            if s["structure_class"]:
                sc = s["structure_class"].split("(")[0].split(",")[0].strip()
                edge(sn, node(f"structure_class:{sc}", "structure_class", "", label=sc), "has_structure")
            if s["process_mode"]:
                edge(sn, node(f"process_mode:{s['process_mode']}", "process_mode", "", label=s["process_mode"]), "has_process")
        for c in T["condition"]:
            cn = node(f"condition:{c['condition_id']}", "condition", key, label=f"{c['quantity'] if c['quantity'] != 'other' else c['label_as_printed']} = {c['value']} {c['unit']}".strip(),
                      **{k: v for k, v in c.items() if k != "condition_id"})
            if c["sample_id"] == "*":
                edge(cn, pn, "of_paper", scope="all samples")
            else:
                edge(cn, f"sample:{c['sample_id']}", "of_sample")
            step = re.search(r"step=(\w+)", c["qualifiers"] or "")
            edge(cn, qnode(c["quantity"], c["label_as_printed"]), "has_quantity", qualifiers=c["qualifiers"], step=step.group(1) if step else "", unit=c["unit"])
        for s in T["series"]:
            sn = node(f"series:{s['series_id']}", "series", key, label=f"Fig. {s['figure']}{s['panel']} {s['series_id'].split(':', 1)[1]}",
                      **{k: v for k, v in s.items() if k not in ("series_id", "points")}, n_points=len(json.loads(s["points"])) if s["points"] else 0)
            if s["sample_id"]:
                edge(sn, f"sample:{s['sample_id']}", "of_sample")
            if s["method"]:
                edge(sn, node(f"method:{s['method']}", "method", "", label=s["method"]), "uses_method")
            for ax in ("x", "y", "z"):
                if s.get(f"{ax}_id"):
                    edge(sn, qnode(s[f"{ax}_id"], s.get(f"{ax}_label", "")), f"axis_{ax}", qualifiers=s.get(f"{ax}_qualifiers", ""))
        for v in T["value"]:
            vn = node(f"value:{v['value_id']}", "value", key, label=f"{v['quantity'] if v['quantity'] != 'other' else v['label_as_printed']} = {v['value'] or (v['value_min'] + '–' + v['value_max'])} {v['unit']}".strip(),
                      **{k: x for k, x in v.items() if k != "value_id"})
            if v["sample_id"]:
                edge(vn, f"sample:{v['sample_id']}", "of_sample")
            else:
                edge(vn, pn, "of_paper", scope="literature")
            if v["from_series"]:
                edge(vn, f"series:{v['from_series']}", "from_series")
            edge(vn, qnode(v["quantity"], v["label_as_printed"]), "has_quantity", qualifiers=v["qualifiers"], unit=v["unit"], data_kind=v["data_kind"])
    for e in edges:                                                        # every edge end must be a node
        for end in ("source", "target"):
            if e[end] not in nodes:
                raise SystemExit(f"edge {e['type']} to missing node {e[end]}")
    return nodes, edges


def graphml(nodes, edges):
    keys = sorted({k for n in nodes.values() for k in n if k != "id"}); ekeys = sorted({k for e in edges for k in e if k not in ("source", "target")})
    out = ['<?xml version="1.0" encoding="UTF-8"?>', '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">']
    out += [f'<key id="n_{k}" for="node" attr.name="{k}" attr.type="string"/>' for k in keys]
    out += [f'<key id="e_{k}" for="edge" attr.name="{k}" attr.type="string"/>' for k in ekeys]
    out.append('<graph id="pilot" edgedefault="directed">')
    for n in nodes.values():
        out.append(f'<node id="{escape(n["id"], {chr(34): "&quot;"})}">' + "".join(f'<data key="n_{k}">{escape(str(v))}</data>' for k, v in n.items() if k != "id") + "</node>")
    for i, e in enumerate(edges):
        out.append(f'<edge id="e{i}" source="{escape(e["source"], {chr(34): "&quot;"})}" target="{escape(e["target"], {chr(34): "&quot;"})}">'
                   + "".join(f'<data key="e_{k}">{escape(str(v))}</data>' for k, v in e.items() if k not in ("source", "target")) + "</edge>")
    out.append("</graph></graphml>")
    return "\n".join(out)


if __name__ == "__main__":
    import collections
    nodes, edges = build()
    (HERE / "kg").mkdir(exist_ok=True)
    (HERE / "kg" / "graph.json").write_text(json.dumps({"nodes": list(nodes.values()), "edges": edges}, ensure_ascii=False, indent=0), encoding="utf-8")
    (HERE / "kg" / "graph.graphml").write_text(graphml(nodes, edges), encoding="utf-8")
    print(len(nodes), "nodes", dict(collections.Counter(n["type"] for n in nodes.values())))
    print(len(edges), "edges", dict(collections.Counter(e["type"] for e in edges)))
