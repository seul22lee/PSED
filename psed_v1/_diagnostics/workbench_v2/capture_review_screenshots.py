#!/usr/bin/env python3
"""Capture the workbench states a reviewer must actually look at.

A passing DOM assertion says a number changed. It does not say the page reads correctly:
whether a disabled axis explains itself, whether a multi-case curve looks like one result,
whether the range box asks for the unit it filters on. Those are decided by looking.

Usage: python3 _diagnostics/workbench_v2/capture_review_screenshots.py <outdir>
"""
import sys
from pathlib import Path

W = Path(__file__).resolve().parent.parent.parent
HTML = Path(__file__).resolve().parent / "psed_scientific_comparison_workbench.html"


def main(outdir):
    from playwright.sync_api import sync_playwright
    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=2)
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.goto(HTML.resolve().as_uri())
        pg.wait_for_selector("#results .case", timeout=20000)

        shot = lambda n: pg.screenshot(path=str(out / ("%s.png" % n)))
        shot("01_initial")

        # active facets + a canonical-unit range
        pg.locator('.fbtn[data-f="material"]').click()
        pg.locator(".pop .opt").first.click()
        pg.locator('.fbtn[data-f="technique"]').click()
        pg.locator(".pop .opt").first.click()
        pg.locator('input[data-r="deposition_temperature"][data-b="min"]').fill("400")
        pg.locator('input[data-r="deposition_temperature"][data-b="min"]').dispatch_event("change")
        shot("02_active_facets")

        # an expanded condition case
        pg.evaluate("() => { Object.keys(active).forEach(k=>active[k].clear());"
                    " RANGES.forEach(r=>range[r.id]={min:'',max:''}); page=0; render(); }")
        pg.locator("#results .case").first.click()
        shot("03_case_expanded")

        # a compatible two-series overlay
        pg.evaluate("""() => {
            const nat = k => (SERIES[k].y_representations||{}).native;
            for (const a of Object.keys(SERIES)) {
              if (!nat(a) || !nat(a).values || !SERIES[a].is_profile) continue;
              for (const b of Object.keys(SERIES)) {
                if (b===a || !nat(b) || !nat(b).values || !SERIES[b].is_profile) continue;
                const p = pairOf(a,b);
                if (!p || !p.physical_overlay_allowed) continue;
                if (nat(a).target_id !== nat(b).target_id) continue;
                tray.length=0; tray.push(a,b); TX=null; TY=null; render();
                if (document.querySelectorAll('#plot polyline').length>=2) return;
              }
            }
        }""")
        shot("04_compatible_overlay")

        # an incompatible selection: the disabled state must explain itself
        pg.evaluate("""() => {
            const nat = k => (SERIES[k].y_representations||{}).native;
            const ids = Object.keys(SERIES).filter(k => nat(k) && nat(k).values);
            const a = ids[0], b = ids.find(k => nat(k).target_id !== nat(a).target_id);
            tray.length=0; tray.push(a,b); TX=null; TY=null; render();
        }""")
        shot("05_incompatible_disabled")

        # a multi-case sweep: one curve must read as one result
        pg.evaluate("""() => {
            tray.length=0;
            const id = Object.keys(SERIES).sort((x,y)=>SERIES[y].n_cases-SERIES[x].n_cases)[0];
            for (page=0; page<40; page++) { render();
                if (document.querySelector(`[data-ser="${id}"]`)) break; }
            document.querySelectorAll('#results details.case').forEach(d=>d.open=true);
            document.querySelectorAll('#results details.pv').forEach(d=>d.open=true);
            const row = document.querySelector(`[data-ser="${id}"]`);
            if (row) row.scrollIntoView({block:'center'});
        }""")
        shot("06_multi_case_expanded")
        b.close()
    print("page errors: %s" % (errs or "none"))
    print("wrote %d screenshots to %s" % (len(list(out.glob("*.png"))), out))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/workbench_shots")
