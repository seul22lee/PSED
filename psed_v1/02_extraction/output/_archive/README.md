# Archive — resolved experiments before the canonicalization change

`resolved_pre_canonical/` is a byte copy of every
`output/{doi}/resolved/experiments.json` as it stood *before* the live pipeline
was fixed (unit conversion, coordinate units, axis-role granularity, scoped
context), together with `checksums.json` (sha256 per paper).

It is the "before" side of the structured migration diff:

    python3 02_extraction/canonical/kb_migration_diff.py
    -> reports/canonical/kb_migration_summary.json
       reports/canonical/granularity_before_after.{json,csv}

Keep it until the granularity change has been reviewed. Nothing reads it at
runtime; only the diff tool does, and only when pointed at it.
