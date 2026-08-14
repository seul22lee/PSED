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
            profileOnly = false; page = 0; mode = "plot"; render();
            // a fixture banner must never survive into a shot of real corpus data
            document.querySelectorAll('[data-fixture-banner]').forEach(n => n.remove());
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
            profileOnly = false; page = 0; mode = "plot"; render();
            // a fixture banner must never survive into a shot of real corpus data
            document.querySelectorAll('[data-fixture-banner]').forEach(n => n.remove());
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
            b.setAttribute("data-fixture-banner", "1");
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

        # --- condition display: colour chips and the qualified-only state ----------
        reset()
        pg.evaluate("""() => {
            // the reported state: one column records the bare quantity, another records
            // it only against a reactant role
            const records = (cs, q) => cs.some(c => (CASES[c]||{conditions:[]}).conditions
                .some(x => x.quantity === q && !x.species));
            const q = "pulse_time";
            let withBare = null, withQualified = null;
            for (const sid in SERIES) {
                const cs = SERIES[sid].all_case_ids || [];
                if (!cs.length) continue;
                if (!withBare && records(cs, q)) withBare = sid;
                if (!withQualified && !records(cs, q) && qualifiedSiblings(cs, q).length)
                    withQualified = sid;
                if (withBare && withQualified) break;
            }
            tray.length = 0; tray.push(withBare, withQualified); render();
            document.querySelectorAll('#conds details').forEach(d => d.open = true);
            const c = document.querySelector('#conds');
            if (c) c.scrollIntoView({block:'start'});
        }""")
        shot("17_condition_table_qualified_only_and_chips")

        # three series: chips in tray, legend and table must agree
        reset()
        pg.evaluate("""() => {
            const nat = k => (SERIES[k].y_representations||{}).native;
            const ok = Object.keys(SERIES).filter(k => nat(k) && nat(k).values
                                                    && SERIES[k].is_profile);
            const pick = [];
            for (const a of ok) {
                if (!pick.length) { pick.push(a); continue; }
                if (pick.every(b => { const p = pairOf(a,b);
                    return p && p.physical_overlay_allowed
                        && nat(a).target_id === nat(b).target_id; })) pick.push(a);
                if (pick.length === 3) break;
            }
            tray.length = 0; pick.forEach(x => tray.push(x)); TX=null; TY=null; render();
            const c = document.querySelector('#cmp');
            if (c) c.scrollIntoView({block:'start'});
        }""")
        shot("18_colour_chips_tray_legend_table")

        # --- case-resolved data ----------------------------------------------------
        reset()
        pg.evaluate("""() => {
            const id = Object.keys(PCL).find(k => PCL[k].status === "POINT_CASE_RESOLVED"
                           && SERIES[k].native_result_status === "NATIVE_ONLY");
            tray.length = 0; tray.push(id); mode = "case"; render();
            const t = document.querySelector('#casedata tr[data-sid]');
            if (t) t.click();
            document.querySelector('#workspace').scrollTop = 0;
        }""")
        shot("19_case_data_resolved_sweep")

        reset()
        pg.evaluate("""() => {
            const res = Object.keys(PCL).filter(k => PCL[k].status === "POINT_CASE_RESOLVED");
            for (const a of res) for (const b of res) {
                if (a === b) continue;
                const ca = new Set(SERIES[a].all_case_ids);
                if (SERIES[b].all_case_ids.filter(c => ca.has(c)).length < 2) continue;
                tray.length = 0; tray.push(a,b); mode = "case"; render();
                document.querySelector('#workspace').scrollTop = 0;
                return;
            }
        }""")
        shot("20_case_data_two_series_aligned")

        reset()
        pg.evaluate("""() => {
            const res = Object.keys(PCL).filter(k => PCL[k].status === "POINT_CASE_RESOLVED");
            for (const a of res) for (const b of res) {
                if (a === b) continue;
                const p = pairOf(a,b);
                if (p && p.physical_overlay_allowed) continue;
                tray.length = 0; tray.push(a,b); mode = "plot"; render();
                return;
            }
        }""")
        shot("21_overlay_blocked_plot_tab")
        pg.evaluate("() => { mode = 'case'; render(); }")
        shot("22_overlay_blocked_case_data_still_available")

        reset()
        pg.evaluate("""() => {
            const id = Object.keys(PCL).find(k => PCL[k].status === "CASE_SET_ONLY"
                                                && SERIES[k].n_cases > 1);
            tray.length = 0; tray.push(id); mode = "case"; render();
            document.querySelector('#workspace').scrollTop = 0;
        }""")
        shot("23_case_set_only_refusal")

        reset()
        pg.evaluate("""() => {
            const id = Object.keys(PCL).find(k => PCL[k].status === "NO_CASE_CONTEXT");
            tray.length = 0; tray.push(id); mode = "case"; render();
            document.querySelector('#workspace').scrollTop = 0;
        }""")
        shot("24_no_case_context")

        # a resolved series whose y axis DID canonicalise: both representations shown
        reset()
        pg.evaluate("""() => {
            const id = Object.keys(PCL).find(k => PCL[k].status === "POINT_CASE_RESOLVED"
                 && SERIES[k].native_result_status === "NATIVE_AND_CANONICAL_AVAILABLE");
            tray.length = 0; tray.push(id); mode = "case"; render();
            const t = document.querySelector('#casedata tr[data-sid]');
            if (t) t.click();
            document.querySelector('#workspace').scrollTop = 0;
        }""")
        shot("25_case_data_native_and_canonical")

        # A source point carrying no observation. This corpus has none (0 of 4027), so
        # the state is injected and the shot is labelled: it is not a corpus claim.
        reset()
        pg.evaluate("""() => {
            const id = Object.keys(PCL).find(k => PCL[k].status === "POINT_CASE_RESOLVED"
                           && SERIES[k].native_result_status === "NATIVE_ONLY"
                           && SERIES[k].native_points.points.length >= 4);
            const links = PCL[id].links.filter(l => l.resolution_status === "RESOLVED");
            const v = links[1].point_index;
            SERIES[id].native_points.points[v].y = null;
            SERIES[id].native_points.y.values[v] = null;
            tray.length = 0; tray.push(id); mode = "case"; render();
            const b = document.createElement("div");
            b.textContent = "FIXTURE \u2014 not corpus. One source point's observation is "
                + "blanked to show that its neighbours keep their own values.";
            b.setAttribute("data-fixture-banner", "1");
            b.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:99;"
                + "padding:6px 12px;background:#8a6100;color:#fff;font:12px sans-serif";
            document.body.appendChild(b);
            document.querySelector('#workspace').scrollTop = 0;
        }""")
        shot("26_missing_observation_row_FIXTURE")

        # aligned multi-output table, both tray orders: the ROW order must not move
        for tag, flip in (("27_aligned_A_then_B", False), ("28_aligned_B_then_A", True)):
            reset()
            pg.evaluate("""(flip) => {
                const res = Object.keys(PCL).filter(k =>
                    PCL[k].status === "POINT_CASE_RESOLVED");
                for (const a of res) for (const b of res) {
                    if (a === b) continue;
                    const ca = new Set(SERIES[a].all_case_ids);
                    if (SERIES[b].all_case_ids.filter(c => ca.has(c)).length < 2) continue;
                    tray.length = 0;
                    if (flip) tray.push(b, a); else tray.push(a, b);
                    mode = "case"; render();
                    document.querySelector('#workspace').scrollTop = 0;
                    return;
                }
            }""", flip)
            shot(tag)

        # a source point whose index cannot be proven: no rows, and it says why
        reset()
        pg.evaluate("""() => {
            const id = Object.keys(PCL).find(k => PCL[k].status === "POINT_CASE_RESOLVED"
                           && SERIES[k].native_points.points.length >= 3);
            const s = SERIES[id];
            s.native_points.points[1].x = null;
            s.native_points.x.values[1] = null;
            s.x_canonical.values = s.x_canonical.values.filter((_, i) => i !== 1);
            s.point_index_contract = {aligned: false,
                reason: "source point 1 has no x, so its canonical counterpart cannot be identified"};
            PCL[id] = Object.assign({}, PCL[id], {links: PCL[id].links.map(l =>
                Object.assign({}, l, {resolution_status: "UNRESOLVED_POINT_INDEX_IDENTITY",
                                      evidence: "SOURCE_POINT_INDEX_NOT_PROVEN",
                                      case_id: null}))});
            tray.length = 0; tray.push(id); mode = "case"; render();
            const bn = document.createElement("div");
            bn.textContent = "FIXTURE \u2014 not corpus. One source point's x is removed so "
                + "canonical x no longer indexes the same points; no point may then be "
                + "reported as resolved.";
            bn.setAttribute("data-fixture-banner", "1");
            bn.style.cssText = "position:fixed;top:0;left:0;right:0;z-index:99;"
                + "padding:6px 12px;background:#8a6100;color:#fff;font:12px sans-serif";
            document.body.appendChild(bn);
            document.querySelector('#workspace').scrollTop = 0;
        }""")
        shot("29_unproven_source_index_FIXTURE")

        # a real curve that no page could draw before: canonical x never produced
        reset()
        pg.evaluate("""() => {
            const id = Object.keys(SERIES).find(k => !SERIES[k].x_canonical.values.length
                           && SERIES[k].x_representations.native_source
                           && SERIES[k].native_points.points.length >= 5);
            tray.length = 0; tray.push(id); mode = "plot"; render();
            document.querySelector('#workspace').scrollTop = 0;
        }""")
        shot("30_native_source_plot_no_canonical_x")

        # two source axes whose units never resolved: no false shared axis
        reset()
        pg.evaluate("""() => {
            const blanks = Object.keys(SERIES).filter(k => {
                const r = SERIES[k].x_representations.native_source;
                return r && !r.unit; });
            tray.length = 0; tray.push(blanks[0], blanks[1]); mode = "plot"; render();
            document.querySelector('#workspace').scrollTop = 0;
        }""")
        shot("31_unresolved_units_no_false_overlay")

        # two branches of one sweep whose Condition Cases are disjoint
        reset()
        pg.evaluate("""() => {
            const res = Object.keys(PCL).filter(k =>
                PCL[k].status === "POINT_CASE_RESOLVED");
            for (const a of res) for (const b of res) {
                if (a === b) continue;
                const ca = new Set(SERIES[a].all_case_ids);
                if (SERIES[b].all_case_ids.some(c => ca.has(c))) continue;
                if (!sweepAxisOf(a) || sweepAxisOf(a) !== sweepAxisOf(b)) continue;
                tray.length = 0; tray.push(a, b); mode = "case"; render();
                document.querySelector('#workspace').scrollTop = 0;
                return;
            }
        }""")
        shot("32_cross_case_sweep_branches")
        b.close()
    print("page errors: %s" % (errs or "none"))
    print("wrote %d screenshots to %s" % (len(list(out.glob("*.png"))), out))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/workbench_shots")
