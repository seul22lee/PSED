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
        reset = lambda: pg.evaluate("""() => {
            tray.length = 0; Object.keys(active).forEach(k => active[k].clear());
            RANGES.forEach(r => range[r.id] = {min:"",max:""});
            profileOnly = false; page = 0; render();
        }""")
        shot("01_initial")

        # the species-qualified range facets: TMA and H2O must be distinguishable
        pg.evaluate("""() => {
            const box = document.querySelector('#facets');
            const n = [...box.querySelectorAll('.facet')]
                .find(x => /TMA/.test(x.innerText));
            if (n) n.scrollIntoView({block:'center'});
        }""")
        shot("02_qualified_range_facets")

        # active facets plus a canonical-unit range
        pg.locator('.fbtn[data-f="material"]').click()
        pg.locator(".pop .opt").first.click()
        pg.locator('input[data-r="deposition_temperature"][data-b="min"]').fill("500")
        pg.locator('input[data-r="deposition_temperature"][data-b="min"]').dispatch_event("change")
        shot("03_active_facets")

        # a multi-case sweep under a filter only part of its span satisfies
        pg.evaluate("""() => {
            Object.keys(active).forEach(k => active[k].clear());
            const id = M.sweep_series_ids.slice()
                        .sort((a,b)=>SERIES[b].n_cases-SERIES[a].n_cases)[0];
            const r = RANGES.find(x => x.field_id === "deposition_temperature");
            range[r.id] = {min:"500", max:""}; page = 0; render();
            document.querySelectorAll('#results details.case').forEach(d => d.open = true);
            const c = document.querySelector(`[data-ser="${id}"]`);
            if (c) c.closest('details.case').scrollIntoView({block:'start'});
        }""")
        shot("04_sweep_under_filter")

        # the sweep section as a whole, then a single-case condition case
        reset()
        pg.evaluate("""() => {
            document.querySelectorAll('#results details.case')[0].open = true;
            window.scrollTo(0,0);
        }""")
        shot("05_sweep_section")
        pg.evaluate("""() => {
            page = 0; render();
            const cards = [...document.querySelectorAll('#results details.case')]
                .filter(d => /Condition Case/.test(
                    (d.querySelector('.ctitle')||{}).textContent||""));
            if (cards.length) { cards[0].open = true;
                cards[0].scrollIntoView({block:'start'}); }
        }""")
        shot("06_single_case_section")

        # per-case producer split, driven on a case given both kinds
        pg.evaluate("""() => {
            const cid = Object.keys(CASES).find(c => CASES[c].measurement_act_ids.length);
            const sim = Object.keys(ACTS).find(a => ACTS[a].kind === "SIMULATION_RUN");
            const ss = ACTS[sim].series_ids[0];
            SERIES[ss].placement = "CASE_LOCAL"; SERIES[ss].placement_case_id = cid;
            SERIES[ss].all_case_ids = [cid];
            CASES[cid].simulation_run_ids = [sim];
            CASES[cid].case_local_series_ids =
                CASES[cid].case_local_series_ids.concat(ss);
            let scope = null;
            for (page = 0; page < 40 && !scope; page++) {
                render();
                document.querySelectorAll('#results details.case').forEach(d => {
                    const t = d.querySelector('.ctitle');
                    if (!scope && t && t.textContent.trim()
                            === "Condition Case " + CASES[cid].case_id) {
                        d.open = true; scope = d; }
                });
            }
            if (scope) scope.scrollIntoView({block:'start'});
        }""")
        shot("07_per_case_producer_split")

        # a compatible two-series overlay
        pg.goto(HTML.resolve().as_uri())
        pg.wait_for_selector("#results .case", timeout=20000)
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
        shot("08_compatible_overlay")

        # an incompatible selection: the disabled state must explain itself
        pg.evaluate("""() => {
            const nat = k => (SERIES[k].y_representations||{}).native;
            const ids = Object.keys(SERIES).filter(k => nat(k) && nat(k).values);
            const a = ids[0], b = ids.find(k => nat(k).target_id !== nat(a).target_id);
            tray.length=0; tray.push(a,b); TX=null; TY=null; render();
        }""")
        shot("09_incompatible_disabled")

        # a sweep in the tray: its conditions must read as varying, not as one case's
        pg.evaluate("""() => {
            const id = M.sweep_series_ids.slice()
                        .sort((a,b)=>SERIES[b].n_cases-SERIES[a].n_cases)[0];
            tray.length = 0; tray.push(id); TX=null; TY=null; render();
            const c = document.querySelector('#conds');
            if (c) c.scrollIntoView({block:'center'});
        }""")
        shot("10_sweep_condition_summary")

        # --- case-scoped filter conjunction ---------------------------------------
        reset = lambda: pg.evaluate("""() => {
            tray.length = 0; Object.keys(active).forEach(k => active[k].clear());
            RANGES.forEach(r => range[r.id] = {min:"",max:""});
            profileOnly = false; page = 0; render();
        }""")

        # facet option counts while a case-scoped constraint is active: the counts must
        # be eligible Condition Cases, not every case a candidate sweep traverses
        reset()
        pg.evaluate("""() => {
            const r = RANGES.find(x => x.field_id === "deposition_temperature");
            range[r.id] = {min:"500", max:""}; page = 0; render();
        }""")
        pg.locator('.fbtn[data-f="material"]').click()
        shot("11_facet_counts_under_case_constraint")
        pg.evaluate("() => closePop()")

        # results with no Condition Case, before and after a case-scoped filter
        reset()
        pg.evaluate("""() => {
            for (page = 0; page < 60; page++) { render();
                if (document.body.innerText.indexOf("no Condition Case") >= 0) break; }
            const d = [...document.querySelectorAll('#results details.case')]
                .find(x => x.innerText.indexOf("no Condition Case") >= 0);
            if (d) { d.open = true; d.scrollIntoView({block:'center'}); }
        }""")
        shot("12_no_case_section_unfiltered")
        pg.evaluate("""() => {
            const f = FDEF.find(x => x.scope === "Condition Case"
                                  && Object.keys(FACETS[x.id]||{}).length);
            active[f.id].add(Object.keys(FACETS[f.id])[0]); page = 0; render();
        }""")
        shot("13_no_case_excluded_by_case_filter")

        # the cross-case contradiction. This corpus cannot show it -- every one of its
        # multi-case sweeps is categorically homogeneous -- so it is drawn from clearly
        # labelled fixture data and must not be read as a corpus state.
        reset()
        pg.evaluate("""() => {
            const A = "__fx_case_A__", B = "__fx_case_B__", S = "__fx_series__";
            const G1 = "__fixture_geometry_A__", G2 = "__fixture_geometry_B__";
            FACETS.geometry[G1] = {cases:[A], series:[S]};
            FACETS.geometry[G2] = {cases:[B], series:[S]};
            NUM[A] = {"deposition_temperature":[{raw:400,unit:"K",canonical:400,
                       quantity:"deposition_temperature",species:null}]};
            NUM[B] = {"deposition_temperature":[{raw:550,unit:"K",canonical:550,
                       quantity:"deposition_temperature",species:null}]};
            CASES[A] = {case_id:"FIXTURE-CASE-A", paper_id:"__fixture__", material:null,
                        geometry:G1, chemistry:{}, conditions:[], series_ids:[S],
                        case_local_series_ids:[], traversed_by_series_ids:[S],
                        measurement_act_ids:[], simulation_run_ids:[],
                        realization:{samples:[], source_sample_records:0,
                                     physical_specimen_identity:"unresolved"}};
            CASES[B] = Object.assign({}, CASES[A],
                                     {case_id:"FIXTURE-CASE-B", geometry:G2});
            SERIES[S] = {id:S, series_id:"FIXTURE-SERIES", all_case_ids:[A,B], n_cases:2,
                         placement:"MULTI_CASE_SWEEP", placement_case_id:null,
                         is_profile:false, act_id:null, paper_id:"__fixture__",
                         figure:"—", panel:"", series_label:"fixture",
                         data_source:"measured", y_resolution:"RESOLVED",
                         normalization_basis:null, n_points:0,
                         x:{x_quantity:null,x_unit:null,x_label:"",x_raw_unit:null},
                         y:{y_quantity:null,y_unit:null,y_label:"",y_raw_unit:null},
                         x_representations:{}, y_representations:{}};
            M.sweep_series_ids.push(S);
            const b = document.createElement("div");
            b.id = "fixture-banner";
            b.textContent = "FIXTURE DATA \u2014 not corpus. One ResultSeries over two "
                + "contradictory Condition Cases: geometry A at 400 K, geometry B at 550 K.";
            b.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:99;"
                + "padding:6px 12px;background:#8a6100;color:#fff;font:12px sans-serif";
            document.body.appendChild(b);
            active.geometry.add(G1);
            const r = RANGES.find(x => x.field_id === "deposition_temperature");
            range[r.id] = {min:"500", max:""}; page = 0; render();
        }""")
        shot("14_cross_case_contradiction_FIXTURE_excluded")
        pg.evaluate("""() => {
            active.geometry.clear();
            active.geometry.add("__fixture_geometry_B__"); page = 0; render();
            const d = document.querySelector('[data-sweep="__fx_series__"]');
            if (d) { d.open = true; d.scrollIntoView({block:'center'}); }
        }""")
        shot("15_cross_case_satisfiable_FIXTURE_included")
        pg.evaluate("""() => {
            const b = document.getElementById("fixture-banner"); if (b) b.remove();
            active.geometry.clear();
            const r = RANGES.find(x => x.field_id === "deposition_temperature");
            range[r.id] = {min:"",max:""};
            delete FACETS.geometry["__fixture_geometry_A__"];
            delete FACETS.geometry["__fixture_geometry_B__"];
            delete CASES["__fx_case_A__"]; delete CASES["__fx_case_B__"];
            delete NUM["__fx_case_A__"]; delete NUM["__fx_case_B__"];
            delete SERIES["__fx_series__"];
            M.sweep_series_ids = M.sweep_series_ids.filter(x => x !== "__fx_series__");
            page = 0; render();
        }""")

        # the tray survives a case-scoped filter change
        reset()
        pg.evaluate("""() => {
            tray.length = 0; tray.push(M.sweep_series_ids[0]); render();
            const f = FDEF.find(x => x.scope === "Condition Case"
                                  && Object.keys(FACETS[x.id]||{}).length);
            active[f.id].add(Object.keys(FACETS[f.id])[0]); page = 0; render();
        }""")
        shot("16_tray_survives_case_filter")
        b.close()
    print("page errors: %s" % (errs or "none"))
    print("wrote %d screenshots to %s" % (len(list(out.glob("*.png"))), out))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/workbench_shots")
