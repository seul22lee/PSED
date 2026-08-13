"""Status the review pages report ABOUT themselves, rather than about the science.

Two panels on those pages answered from the wrong place. The source-preservation panel
read an invariant key nothing writes, so a missing lookup rendered as `ok`; and the test
tile fell back to a hard-coded `{"passed": 126, "failed": 0}` when the status file was
absent, printing a green count no run had produced.

Both are the same mistake: absence of evidence displayed as evidence of success. Every
function here returns an explicit unknown instead, and reserves the passing state for
input it could actually verify.
"""
import json
import subprocess

#: pill classes, matching the two review builders
OK, WARN, BAD = "ok", "warn", "bad"

#: keys a status file must carry before it can be read as a result at all
_REQUIRED = ("passed", "failed")


def head_sha(repo_dir, ignore=None):
    """(sha, dirty) for the working tree, or (None, False) outside a checkout.

    `ignore` names a file excluded from the dirty test. The status file is written INTO
    the tree it describes, so counting it would make every freshly-recorded run report a
    tree modified since the run -- true only of the record itself.
    """
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                      cwd=str(repo_dir),
                                      stderr=subprocess.DEVNULL).decode().strip()
        porcelain = subprocess.check_output(["git", "status", "--porcelain", "."],
                                            cwd=str(repo_dir),
                                            stderr=subprocess.DEVNULL).decode()
        skip = str(ignore) if ignore else None
        lines = [l for l in porcelain.splitlines() if l.strip()
                 and not (skip and l[3:].strip().strip('"').endswith(_tail(skip)))]
        return sha or None, bool(lines)
    except Exception:
        return None, False


def _tail(p):
    """The trailing 'logs/test_status.json'-style fragment git prints paths by."""
    parts = str(p).replace("\\", "/").split("/")
    return "/".join(parts[-2:]) if len(parts) > 1 else parts[-1]


def test_status(status_file, repo_dir):
    """-> {state, label, detail, kind, passed, failed, suite, recorded_sha}

    `state` is one of:

        unknown       no file, unreadable, or not a result at all
        unverifiable  a result, but it records no commit, so nothing ties it to this tree
        stale         recorded against a different commit than the one checked out
        modified      recorded against this commit, but the tree has since changed
        current       recorded against this exact commit, tree clean

    Only `current` with no failures is `OK`. A stale green is still shown -- hiding the
    numbers would be its own kind of lie -- but it is labelled stale and never coloured as
    a pass, because a count from another commit is not evidence about this one.
    """
    out = {"state": "unknown", "label": "unknown", "detail": "", "kind": WARN,
           "counts": "unknown",
           "passed": None, "failed": None, "suite": None, "recorded_sha": None}
    try:
        raw = json.loads(status_file.read_text())
    except (OSError, ValueError):
        out["detail"] = ("no test status recorded at %s -- run the pilot suite to "
                         "produce it" % status_file.name)
        return out
    if not isinstance(raw, dict) or any(not isinstance(raw.get(k), int) for k in _REQUIRED):
        out["detail"] = "%s is present but is not a test result" % status_file.name
        return out

    out.update(passed=raw["passed"], failed=raw["failed"],
               suite=raw.get("suite"), recorded_sha=raw.get("git_sha"))
    # `counts` is what was observed; `label`/`state` add how that relates to the tree
    # RIGHT NOW. Only the former belongs in a committed artifact -- a freshness verdict
    # baked into a file decays the moment anything is committed, which is the same
    # self-reference that made a tracked status file unsatisfiable.
    counts = out["counts"] = "%d passed, %d failed" % (raw["passed"], raw["failed"])
    sha, dirty = head_sha(repo_dir, ignore=status_file)

    if not out["recorded_sha"]:
        out.update(state="unverifiable", label="%s (unverifiable)" % counts, kind=WARN,
                   detail="no commit recorded -- cannot be shown to describe this tree")
    elif sha and out["recorded_sha"] != sha:
        out.update(state="stale", label="%s (stale)" % counts, kind=WARN,
                   detail="recorded at %s, working tree is at %s"
                          % (out["recorded_sha"], sha))
    elif dirty:
        out.update(state="modified", label="%s (tree modified)" % counts, kind=WARN,
                   detail="recorded at %s, uncommitted changes since"
                          % out["recorded_sha"])
    else:
        out.update(state="current", label=counts, kind=OK,
                   detail="recorded at %s" % out["recorded_sha"])

    # a failing suite is never OK, however fresh the record is
    if raw["failed"]:
        out["kind"] = BAD
    return out


def write_test_status(status_file, repo_dir, suite, passed, failed, **extra):
    """Record a suite result against the commit it was produced at.

    Deliberately carries no timestamp: two runs of the same suite at the same commit with
    the same result write byte-identical content, so the artifact does not churn. The
    commit is what freshness is judged against, and `head_sha` re-reads the live tree.
    """
    sha, _ = head_sha(repo_dir, ignore=status_file)
    payload = {"suite": suite, "passed": int(passed), "failed": int(failed),
               "git_sha": sha}
    payload.update(extra)
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status_file.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return payload


def data_source_status(inv_entry):
    """-> (label, kind) for one paper's `data_source_unchanged` invariant.

    The invariant records two DISTRIBUTIONS -- the canonical counts and the pilot's -- and
    nothing else. It can therefore say whether they match, and cannot say whether a
    mismatch was authorised. So this reports the comparison and stops there.

    Judging a difference legitimate is the invariant-13 test's job: it checks, per
    ResultSeries, that every override is explained by positive persisted series evidence.
    Re-deciding that here from two count dictionaries would be inventing science in the
    presentation layer, and would go wrong in exactly the case that matters -- a drift
    that happens to leave the totals looking plausible.
    """
    v = (inv_entry or {}).get("data_source_unchanged")
    if not isinstance(v, dict) or "old" not in v or "pilot" not in v:
        return "unavailable", WARN
    if v["old"] == v["pilot"]:
        return "identical", OK
    return "differs — see invariant 13", WARN
