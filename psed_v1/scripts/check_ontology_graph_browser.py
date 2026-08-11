#!/usr/bin/env python3
"""Browser smoke test for the ontology relationship graph (Playwright/Chromium).

Skips cleanly (exit 0) if Playwright or its browser is unavailable, so it never
blocks a headless CI without a browser. When it runs it asserts the graph is a real
node-link view: a sized container, exactly 80 graphical edges, arrow markers, no
console errors, working type-filters, and node-focus edge highlighting.

  python3 test_ontology_graph_browser.py
"""
import sys as _sys
from pathlib import Path as _Path
_PSED_ROOT = _Path(__file__).resolve().parents[2]
_sys.path.insert(0, str(_PSED_ROOT))
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
HTML = _PSED_ROOT / "ontology" / "ontology.html"

try:
    from playwright.sync_api import sync_playwright
except Exception as e:
    print(f"SKIP  playwright unavailable ({type(e).__name__}); browser smoke test not run")
    sys.exit(0)

FAIL = []


def ok(name, cond, detail=""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}{(' — ' + str(detail)) if detail else ''}")
    if not cond:
        FAIL.append(name)


try:
    pw = sync_playwright().start()
    browser = pw.chromium.launch()
except Exception as e:
    print(f"SKIP  chromium not launchable ({type(e).__name__}: {e})")
    sys.exit(0)

errors = []
pg = browser.new_page(viewport={"width": 1280, "height": 900})
pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
pg.on("pageerror", lambda e: errors.append("PAGEERROR: " + str(e)))
pg.goto("file://" + str(HTML.resolve()))
pg.wait_for_function("window.__GRAPH_READY__===true", timeout=8000)

box = pg.eval_on_selector("#graph", "el=>({w:el.clientWidth,h:el.clientHeight})")
ok("graph container width > 0", box["w"] > 0, box["w"])
ok("graph container height > 0", box["h"] > 0, box["h"])
ncirc = pg.eval_on_selector_all("#graph circle", "e=>e.length")
nline = pg.eval_on_selector_all("#graph line.edge", "e=>e.length")
nmark = pg.eval_on_selector_all("#graph marker", "e=>e.length")
ok("graphical node count > 0", ncirc > 0, ncirc)
ok("exactly 80 graphical edges", nline == 80, nline)
ok("arrow markers rendered (4 directed types)", nmark == 4, nmark)
ok("no JavaScript console/page errors", not errors, errors)

for s_, p_, t_ in (("reactant_A_partial_pressure", "specializes", "partial_pressure"),
                   ("initial_sticking_coefficient", "specializes", "sticking_probability"),
                   ("partial_pressure", "transforms", "exposure")):
    found = pg.evaluate(f"(DATA._edges||[]).some(e=>e.source==='{s_}'&&e.kind==='{p_}'&&e.target==='{t_}')")
    ok(f"edge {s_} -{p_}-> {t_}", found)

before = pg.eval_on_selector_all("#graph line.edge", "e=>e.length")
pg.uncheck("input[data-k='in_family']")
pg.wait_for_timeout(200)
after = pg.eval_on_selector_all("#graph line.edge", "e=>e.length")
ok("relationship filter changes visible edge count", before != after, f"{before}->{after}")
pg.check("input[data-k='in_family']")

pg.evaluate("var s=document.querySelector('#gsearch');s.value='reactant_A_partial_pressure';"
            "s.dispatchEvent(new Event('input'))")
pg.wait_for_timeout(200)
dim = pg.eval_on_selector_all("#graph line.edge.dim", "e=>e.length")
tot = pg.eval_on_selector_all("#graph line.edge", "e=>e.length")
ok("selecting a node highlights its connected edges", 0 < (tot - dim) < tot, f"{tot-dim} of {tot}")

browser.close()
pw.stop()

print()
if FAIL:
    print(f"{len(FAIL)} FAILURE(S): {FAIL}")
    sys.exit(1)
print("ALL TESTS PASSED")
