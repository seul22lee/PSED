#!/usr/bin/env python3
"""Report hygiene: what the review pages say about themselves.

Both defects these tests cover were the same mistake -- absence of evidence rendered as
evidence of success. The preservation panel read `data_source_preserved`, a key nothing
writes, and `.get(..., "ok")` turned the miss into a pass. The test tile fell back to a
literal `{"passed": 126, "failed": 0}` when its status file was absent, printing a green
count no run had produced.

So the rule under test is narrow and blunt: a passing state must be earned. Missing,
malformed, unverifiable and stale inputs each get their own visible state, and none of
them is OK.

Run:  python3 tests/test_report_status.py
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

W = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(W / "code"))
import pilot_status as PSTAT          # noqa: E402

_pass, _fail = [], []


def ok(name, cond, detail=""):
    (_pass if cond else _fail).append(name)
    print("  %s %s%s" % ("PASS" if cond else "FAIL", name,
                         "" if cond else "   -> %r" % (detail,)))


def status(payload, repo=W):
    """Run test_status over a temporary file holding `payload` (None = no file)."""
    d = Path(tempfile.mkdtemp())
    f = d / "test_status.json"
    if payload is not None:
        f.write_text(payload if isinstance(payload, str) else json.dumps(payload))
    return PSTAT.test_status(f, repo)


def main():
    sha, dirty = PSTAT.head_sha(W)

    print("=== A. missing invariant key is not a pass ===")
    # the original defect: the review asked for a key nothing emits and defaulted to "ok"
    lbl, kind = PSTAT.data_source_status({"data_source_preserved": {"status": "ok"}})
    ok("A: the legacy key alone does not produce a passing state",
       kind != PSTAT.OK and lbl == "unavailable", (lbl, kind))
    for bad in ({}, None, {"data_source_unchanged": None},
                {"data_source_unchanged": {}},
                {"data_source_unchanged": {"old": {}}},
                {"data_source_unchanged": "yes"}):
        lbl, kind = PSTAT.data_source_status(bad)
        ok("A: %-42s -> unavailable" % json.dumps(bad)[:42],
           (lbl, kind) == ("unavailable", PSTAT.WARN), (lbl, kind))

    print("=== B. a real difference is not rendered as ok ===")
    lbl, kind = PSTAT.data_source_status(
        {"data_source_unchanged": {"old": {"measured": 34},
                                   "pilot": {"measured": 27, "simulated": 7}}})
    ok("B: differing distributions are not OK", kind != PSTAT.OK, (lbl, kind))
    ok("B: the label points at the invariant that authorises overrides",
       "invariant 13" in lbl, lbl)

    print("=== C. genuinely identical distributions pass ===")
    lbl, kind = PSTAT.data_source_status(
        {"data_source_unchanged": {"old": {"measured": 21}, "pilot": {"measured": 21}}})
    ok("C: identical distributions are OK", (lbl, kind) == ("identical", PSTAT.OK),
       (lbl, kind))

    print("=== D. no dependency on the legacy key ===")
    src = (W / "code" / "build_semantic_review.py").read_text()
    ok("D: the review no longer reads 'data_source_preserved'",
       "data_source_preserved" not in src)
    ok("D: no module under code/ reads the legacy key",
       not [f.name for f in (W / "code").glob("*.py")
            if "data_source_preserved" in f.read_text()])
    # the writer's key is the one the consumer asks for
    ok("D: the consumer reads the key run_pilot actually writes",
       "data_source_unchanged" in (W / "code" / "run_pilot.py").read_text()
       and "data_source_unchanged" in (W / "code" / "pilot_status.py").read_text())

    print("=== E. missing test status is never green ===")
    s = status(None)
    ok("E: a missing file is 'unknown'", s["state"] == "unknown", s)
    ok("E: a missing file is not OK", s["kind"] != PSTAT.OK, s["kind"])
    ok("E: a missing file reports no counts", s["passed"] is None and s["failed"] is None)
    ok("E: the label does not read as a result", s["label"] == "unknown", s["label"])
    # the specific regression: a hard-coded green fallback
    ok("E: no builder carries a hard-coded pass count",
       not [f.name for f in (W / "code").glob("build_*.py")
            if '"passed": 126' in f.read_text() or "'passed': 126" in f.read_text()])

    print("=== F. malformed test status fails safely ===")
    for name, payload in (("not json", "{oh no"), ("a list", [1, 2, 3]),
                          ("a bare string", '"done"'), ("empty object", {}),
                          ("counts missing", {"suite": "x", "git_sha": sha}),
                          ("counts not numeric", {"passed": "300", "failed": "0"}),
                          ("only passed", {"passed": 300})):
        s = status(payload)
        ok("F: %-18s -> unknown, not a pass" % name,
           s["state"] == "unknown" and s["kind"] != PSTAT.OK, s)

    print("=== G. staleness is visible ===")
    s = status({"suite": "s", "passed": 300, "failed": 0, "git_sha": "0000000"})
    ok("G: a record from another commit is 'stale'", s["state"] == "stale", s["state"])
    ok("G: stale is not OK", s["kind"] != PSTAT.OK, s["kind"])
    ok("G: stale still shows the counts it has", s["passed"] == 300, s)
    ok("G: the label says stale", "stale" in s["label"], s["label"])
    ok("G: the detail names both commits",
       "0000000" in s["detail"] and (sha or "") in s["detail"], s["detail"])

    s = status({"suite": "s", "passed": 300, "failed": 0})
    ok("G: a record with no commit is 'unverifiable'", s["state"] == "unverifiable",
       s["state"])
    ok("G: unverifiable is not OK", s["kind"] != PSTAT.OK)

    print("=== H. a current record reads as current ===")
    s = status({"suite": "s", "passed": 300, "failed": 0, "git_sha": sha})
    want = "modified" if dirty else "current"
    ok("H: a record at HEAD is %r" % want, s["state"] == want, s)
    ok("H: it is OK only when the tree is also clean",
       (s["kind"] == PSTAT.OK) == (not dirty), (s["kind"], dirty))
    ok("H: the counts are reported verbatim", (s["passed"], s["failed"]) == (300, 0))

    print("=== I. a failing suite is never OK, however fresh ===")
    s = status({"suite": "s", "passed": 290, "failed": 10, "git_sha": sha})
    ok("I: failures force BAD", s["kind"] == PSTAT.BAD, s)
    ok("I: the failure count is shown", "10 failed" in s["label"], s["label"])

    print("=== J. the file has a writer, and it round-trips ===")
    d = Path(tempfile.mkdtemp())
    f = d / "logs" / "test_status.json"
    wrote = PSTAT.write_test_status(f, W, suite="unit", passed=7, failed=0, papers=8)
    ok("J: the writer creates the file and its parent", f.exists())
    ok("J: it records the commit it ran at", wrote["git_sha"] == sha, wrote)
    back = PSTAT.test_status(f, W)
    ok("J: the round-trip is current-or-modified, never unknown",
       back["state"] in ("current", "modified") and back["passed"] == 7, back)
    # deterministic: no timestamp, so re-running at one commit does not churn the artifact
    first = f.read_text()
    PSTAT.write_test_status(f, W, suite="unit", passed=7, failed=0, papers=8)
    ok("J: an identical result rewrites byte-identical content", f.read_text() == first)
    ok("J: the pilot suite is wired to the writer",
       "write_test_status" in (W / "tests" / "test_pilot_semantics.py").read_text())

    print("=== K. both review builders share one reader ===")
    both = [(W / "code" / n).read_text()
            for n in ("build_semantic_review.py", "build_identity_review.py")]
    ok("K: neither builder parses the status file itself",
       all("test_status.json" not in s.replace('W / "logs" / "test_status.json"', "")
           or "PSTAT.test_status" in s for s in both))
    ok("K: both go through the shared helper",
       all("PSTAT.test_status(" in s for s in both))
    ok("K: no builder hard-codes an expected suite size",
       not any(t in s for s in both for t in ("== 300", "300 passed", "expected_tests")))

    print("=== L. the runtime status artifact is readable and honest ===")
    # It may legitimately be ABSENT here: it is generated by running the pilot suite, not
    # shipped with the repository, so a fresh clone has none until the tests run.
    live = PSTAT.test_status(W / "logs" / "test_status.json", W)
    ok("L: the runtime artifact parses into a known state",
       live["state"] in ("current", "modified", "stale", "unverifiable", "unknown"),
       live["state"])
    ok("L: it is only OK if it was recorded at this exact clean tree",
       (live["kind"] == PSTAT.OK) == (live["state"] == "current"), live)

    print("=== M. the status file is runtime state, not repository content (§21A) ===")
    # THE self-reference: a TRACKED file that records the SHA it was generated at can
    # never be committed truthfully. Committing it creates a new HEAD, so the SHA it
    # stores is stale the instant it lands -- and re-running plus re-committing just moves
    # the problem to the next commit. It is untracked and ignored so the contract is
    # satisfiable: run the suite on a clean checkout and the record matches HEAD, with no
    # commit in between to invalidate it.
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=str(W),
                          capture_output=True, text=True).stdout.strip()
    ok("M: the audit runs inside a git checkout", bool(root), root)
    rel = str((W / "logs" / "test_status.json").relative_to(root))
    tracked = subprocess.run(["git", "ls-files", "--error-unmatch", rel],
                             cwd=root, capture_output=True).returncode == 0
    ok("M: the status file is NOT tracked", not tracked,
       "still tracked -- committing it would re-create the self-stale contract")
    ignored = subprocess.run(["git", "check-ignore", "-q", rel],
                             cwd=root, capture_output=True).returncode == 0
    ok("M: it is ignored, so generating it never dirties the tracked tree", ignored, rel)
    ok("M: the ignore rule names the file, not the whole logs directory",
       subprocess.run(["git", "check-ignore", "-q",
                       str((W / "logs" / "final_counts.json").relative_to(root))],
                      cwd=root, capture_output=True).returncode != 0)
    # §21E — writing it must leave the tracked tree exactly as it was
    porcelain = lambda: subprocess.run(["git", "status", "--porcelain", "."], cwd=str(W),
                                       capture_output=True, text=True).stdout
    before = porcelain()
    PSTAT.write_test_status(W / "logs" / "test_status.json", W,
                            suite="lifecycle_probe", passed=1, failed=0)
    ok("M: regenerating the status leaves the tracked tree unchanged",
       porcelain() == before, "writing the status file changed git status")
    # restore whatever the pilot suite last recorded, so this probe leaves no trace
    if live["passed"] is not None:
        PSTAT.write_test_status(W / "logs" / "test_status.json", W, suite=live["suite"],
                                passed=live["passed"], failed=live["failed"])

    print("=== N. committed pages carry history, not a live verdict (§20) ===")
    # A page that states "current" or "tree modified" is self-stale for the same reason:
    # committing the page changes HEAD and falsifies the claim it carries.
    for name in ("build_semantic_review.py", "build_identity_review.py"):
        s = (W / "code" / name).read_text()
        ok("N: %-26s does not bake a freshness verdict into the page" % name,
           'tests["state"]' not in s.split("def main(")[0]
           and 'tests["label"]' not in s.split("def main(")[0], name)
        ok("N: %-26s records what was run, and where from" % name,
           'tests["counts"]' in s and 'recorded_sha' in s or "generated_from" in s, name)
    for f in ("semantic_review.html", "semantic_identity_review.html"):
        p = W / "comparison" / f
        if not p.exists():
            continue
        h = p.read_text()
        ok("N: %-30s carries no live freshness claim" % f,
           not any(t in h for t in ("(tree modified)", "(stale)", ">current<",
                                    "uncommitted changes since")),
           [t for t in ("(tree modified)", "(stale)", "uncommitted changes since")
            if t in h])

    print("\n%d passed, %d failed" % (len(_pass), len(_fail)))
    if _fail:
        print("FAILED: %s" % _fail)
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
