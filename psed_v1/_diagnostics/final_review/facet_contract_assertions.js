const out = [];
const T = (n, c, d) => out.push({ name: n, ok: !!c, detail: d === undefined ? "" : String(d) });
const cases = () => matchingCases().length;
const ALL = Object.keys(E).length;

T("full corpus is unfiltered", cases() === ALL, cases());
const mats = facetOptions("material");
T("material facet has values", mats.length > 1, mats.length);
const before = { prec: facetOptions("precursor").length, core: facetOptions("coreactant").length,
                 qty: facetOptions("quantity").length };

active.material.add(mats[0].v);
const afterOne = cases();
T("single selection narrows the case set", afterOne < ALL, afterOne);
T("single selection narrows OTHER facets",
  facetOptions("precursor").length <= before.prec &&
  facetOptions("coreactant").length <= before.core, "");
T("at least one other facet actually shrank",
  facetOptions("precursor").length < before.prec ||
  facetOptions("coreactant").length < before.core ||
  facetOptions("quantity").length < before.qty, "");
T("leave-one-out: own facet still offers alternatives",
  facetOptions("material").length === mats.length, facetOptions("material").length);

active.material.add(mats[1].v);
T("OR within a facet widens the set", cases() > afterOne, cases());
const orCount = cases();

const pr = facetOptions("precursor")[0];
if (pr) {
  active.precursor.add(pr.v);
  T("AND across facets narrows the set", cases() <= orCount, cases());
  active.precursor.delete(pr.v);
  T("removing a chip restores the previous set", cases() === orCount, cases());
}

active.material.delete(mats[1].v);
T("removing one value of a multi-select keeps the other", cases() === afterOne, cases());
Object.keys(active).forEach(k => active[k].clear());
T("clear all restores the full corpus", cases() === ALL, cases());

T("no facet ever offers a zero-count value",
  !FACETS.some(f => facetOptions(f.id).some(o => o.n === 0)), "");

// result-level filtering must preserve the Case -> Measurement -> Series scope
const q = facetOptions("quantity").find(o => o.n > 1);
if (q) {
  active.quantity.add(q.v);
  const ids = matchingCases();
  T("result facet keeps the hierarchy path",
    ids.every(cid => measOf(cid).some(mid =>
      seriesOf(mid).some(sid => S[sid].y.quantity === q.v))), q.v);
  T("result facet count is in ExperimentalCases", ids.length === q.n, [ids.length, q.n]);
  // technique + quantity coupling: one measurement must satisfy both
  const t = facetOptions("technique")[0];
  if (t) {
    active.technique.add(t.v);
    const ids2 = matchingCases();
    T("technique+quantity resolve through the SAME measurement",
      ids2.every(cid => measOf(cid).some(mid =>
        M[mid].technique === t.v && seriesOf(mid).some(sid => S[sid].y.quantity === q.v))),
      t.v);
    active.technique.clear();
  }
  active.quantity.clear();
}

// numeric range uses canonical numbers and never admits unresolved values
nrange.temperature.min = "200"; nrange.temperature.max = "300";
const tids = matchingCases();
T("numeric range filters on canonical numbers",
  tids.every(cid => {
    const c = (E[cid].conditions || []).find(x => x.quantity === "deposition_temperature");
    const n = c ? parseFloat(c.value) : NaN;
    return isFinite(n) && n >= 200 && n <= 300;
  }), tids.length);
nrange.temperature.min = ""; nrange.temperature.max = "";

// the comparison tray is filter-independent
sel.push(Object.keys(S)[0]);
active.material.add(mats[0].v);
T("comparison tray survives a filter change", sel.length === 1, sel.length);
sel.length = 0; active.material.clear();

console.log(JSON.stringify(out));
