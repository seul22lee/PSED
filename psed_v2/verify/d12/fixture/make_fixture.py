"""P127 fixture: two invented run files (fix_a.jsonl: arms kb and text, runs 1 and 2; fix_b.jsonl: arms kb, text and model, run 1)
and a matching verdicts.csv. Questions, papers (alp01, bet02, gam03) and ids are made up; nothing comes from the corpus.

    python3 psed_v2/verify/d12/fixture/make_fixture.py   # writes next to itself"""
import csv, json
from pathlib import Path

HERE = Path(__file__).resolve().parent
Q = ["Fixture question one: how thick is the made-up widget layer?",
     "Fixture question two: which invented gadget grows faster?",
     "Fixture question three: what limits the pretend coating depth?"]
# cited ids per (file, arm, run, question index); kb ids carry '#n', text ids are piece ids
CITED = {
    ("fix_a.jsonl", "kb", 1, 0): ["alp01:tab1.r2c3#1", "alp01:tab1.r2c3#2", "alp01:s3.p2#1", "bet02:fig2.c1#4"],
    ("fix_a.jsonl", "text", 1, 0): ["alp01:tab1.r2c3", "alp01:s3.p2", "alp01:s4.p1"],
    ("fix_a.jsonl", "kb", 1, 1): ["bet02:s2.p5#1", "gam03:tab2.r1c1#1"],
    ("fix_a.jsonl", "text", 1, 1): ["bet02:s2.p5", "bet02:s2.p6"],
    ("fix_a.jsonl", "kb", 1, 2): [],
    ("fix_a.jsonl", "text", 1, 2): ["gam03:s5.p1", "gam03:s5.p2"],
    ("fix_a.jsonl", "kb", 2, 0): ["alp01:tab1.r2c3#1", "alp01:s3.p2#1"],
    ("fix_a.jsonl", "text", 2, 0): ["alp01:tab1.r2c3", "bet02:s1.p1"],
    ("fix_a.jsonl", "kb", 2, 1): ["bet02:s2.p5#1"],
    ("fix_a.jsonl", "text", 2, 1): ["bet02:s2.p5"],
    ("fix_a.jsonl", "kb", 2, 2): ["gam03:s5.p1#2", "alp01:cmp:B"],
    ("fix_a.jsonl", "text", 2, 2): ["gam03:s5.p1"],
    ("fix_b.jsonl", "kb", 1, 0): ["alp01:tab1.r2c3#1"],
    ("fix_b.jsonl", "text", 1, 0): ["alp01:tab1.r2c3"],
    ("fix_b.jsonl", "kb", 1, 1): ["gam03:tab2.r1c1#1"],
    ("fix_b.jsonl", "text", 1, 1): ["bet02:s2.p5"],
    ("fix_b.jsonl", "model", 1, 0): [], ("fix_b.jsonl", "model", 1, 1): [],
}
VERDICTS = {   # (file, arm, run, question_no) -> verdict; fix_a text run 2 question 3 left ungraded
    ("fix_a.jsonl", "kb", 1, 1): "right", ("fix_a.jsonl", "text", 1, 1): "right",
    ("fix_a.jsonl", "kb", 1, 2): "right", ("fix_a.jsonl", "text", 1, 2): "slips",
    ("fix_a.jsonl", "kb", 1, 3): "empty", ("fix_a.jsonl", "text", 1, 3): "right",
    ("fix_a.jsonl", "kb", 2, 1): "slips", ("fix_a.jsonl", "text", 2, 1): "material",
    ("fix_a.jsonl", "kb", 2, 2): "right", ("fix_a.jsonl", "text", 2, 2): "fabricated",
    ("fix_a.jsonl", "kb", 2, 3): "right",
    ("fix_b.jsonl", "kb", 1, 1): "right", ("fix_b.jsonl", "text", 1, 1): "right",
    ("fix_b.jsonl", "kb", 1, 2): "material", ("fix_b.jsonl", "text", 1, 2): "right",
    ("fix_b.jsonl", "model", 1, 1): "empty", ("fix_b.jsonl", "model", 1, 2): "empty",
}


def record(f, arm, run, qi, ids):
    calls = [dict(name="values", arguments={"result": "thickness", "paper": i.split(":")[0]}, error="", tokens=100, results=1,
                  delivered_tokens=50, output=f"[{i}] invented line\nbudget left: 39,950 tokens") for i in ids] if arm == "kb" else []
    n = len(ids)
    return dict(question=Q[qi], arm=arm, model="fixture:none", run=run, answer=("Invented answer. " + " ".join(f"[{i}]" for i in ids)) if arm != "model" else "",
                cited={i: "invented" for i in ids}, tool_calls=calls, error="" if arm != "model" else "fixture: no model",
                number_check=dict(numbers=n, match=max(n - 1, 0), elsewhere=0, not_seen=min(n, 1), derived=0, uncited=0, unknown_ids=0,
                                  per_number=[dict(value=float(k), status="match") for k in range(n)]),
                kind_check=dict(mismatches=0), usage=dict(input=1000 * (n + 1), output=100, cache_read=500 * n), cost=round(0.001 * (n + 1), 6),
                seconds=1.0, max_tokens=40000, max_calls=10, preamble_sha256="fixture", git_head="fixture")


for f in ("fix_a.jsonl", "fix_b.jsonl"):
    with (HERE / f).open("w", encoding="utf-8") as out:
        for (ff, arm, run, qi), ids in CITED.items():
            if ff == f:
                out.write(json.dumps(record(f, arm, run, qi, ids), ensure_ascii=False) + "\n")
with (HERE / "verdicts.csv").open("w", newline="", encoding="utf-8") as out:
    w = csv.DictWriter(out, fieldnames=["question_no", "run_file", "arm", "run", "verdict", "note"]); w.writeheader()
    for (f, arm, run, n), v in VERDICTS.items():
        w.writerow(dict(question_no=n, run_file=f, arm=arm, run=run, verdict=v, note="fixture"))
print("fixture: fix_a.jsonl, fix_b.jsonl, verdicts.csv")
