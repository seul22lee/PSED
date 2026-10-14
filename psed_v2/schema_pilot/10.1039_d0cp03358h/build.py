"""Write the six schema-pilot tables for 10.1039_d0cp03358h (Yim et al. 2020, PCCP).
Hand-read content; points reused from cases/points.json."""
import csv, json, os

REPO = '/home/ftk3187/github/PSED/psed_v2'
PID = '10.1039_d0cp03358h'
OUT = f'{REPO}/schema_pilot/{PID}'
K = 'yim20'

def sid(x):
    return f'{K}:{x}'

def write(name, header, rows):
    with open(f'{OUT}/{name}', 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            assert len(r) == len(header), (name, r)
            w.writerow(r)
    return len(rows)

counts = {}

# ---------------------------------------------------------------- paper
counts['paper.csv'] = write('paper.csv', ['paper_id', 'year', 'topic'], [[
    PID, 2020,
    'Benchmark of saturation-profile conformality analysis: thermal TMA/H2O Al2O3 at 300 C in PillarHall-3 '
    'lateral channels (H 100/500/2000 nm); spot size, repeatability, channel height, cycles, TMA pulse and '
    'purge series; diffusion-reaction simulations; lumped sticking coefficients by the slope method']])

# ---------------------------------------------------------------- Table 1 (hand-checked against the page image)
# code: series, seq (tA, purgeA, tB, purgeB), H nm, layout, N, mag, S_I, S_IIb, S_I/N, S_IIb/N, x50 um, x~50, slope S/N, slope theta, R2
T1 = {
    1: ('A', (0.1, 4.0, 0.1, 4.0), 500, 'v1a', 500, 50, 49.8, 53.3, 0.100, 0.107, 140, 280, -0.0013, -0.013, 0.983),
    2: ('A', (0.1, 4.0, 0.1, 4.0), 500, 'v1b', 500, 50, 49.6, 54.5, 0.0993, 0.109, 140, 280, -0.0013, -0.011, 0.991),
    3: ('A', (0.1, 4.0, 0.1, 4.0), 500, 'v2a', 500, 50, 50.5, 53.4, 0.101, 0.107, 110, 220, -0.0018, -0.018, 0.997),
    4: ('B', (0.1, 4.0, 0.1, 4.0), 500, 'v1b', 500, 50, 47.4, 47.8, 0.0949, 0.0956, 105, 208, -0.0018, -0.019, 0.993),
    5: ('B', (0.1, 4.0, 0.1, 4.0), 500, 'v1b', 500, 10, 49.1, 50.0, 0.0983, 0.100, 103, 208, -0.0015, -0.015, 0.998),
    6: ('B', (0.1, 4.0, 0.1, 4.0), 500, 'v1b', 500, 5, 51.4, 52.9, 0.103, 0.106, 109, 214, -0.00087, -0.0083, 0.998),
    7: ('C', (0.1, 4.0, 0.1, 4.0), 100, 'v1b', 500, 50, None, 47.8, None, 0.0955, 10, 100, -0.00048, -0.0050, 0.995),
    8: ('C;D', (0.1, 4.0, 0.1, 4.0), 500, 'v1b', 500, 50, 46.7, 51.1, 0.0934, 0.102, 106, 214, -0.0020, -0.019, 0.993),
    9: ('C', (0.1, 4.0, 0.1, 4.0), 2000, 'v1b', 500, 50, 45.3, 48.8, 0.0906, 0.0976, 375, 188, -0.0046, -0.047, 0.995),
    10: ('D', (0.1, 4.0, 0.1, 4.0), 500, 'v1b', 250, 50, 24.3, 26.0, 0.0970, 0.104, 115, 230, -0.0022, -0.021, 0.982),
    11: ('D', (0.1, 4.0, 0.1, 4.0), 500, 'v1b', 1000, 50, 94.7, 99.3, 0.0947, 0.0993, 95, 190, -0.00099, -0.010, 0.996),
    12: ('E;F', (0.1, 4.0, 0.1, 4.0), 500, 'v1b', 500, 50, 47.5, 50.2, 0.0951, 0.100, 96, 192, -0.0021, -0.021, 0.971),
    13: ('E', (0.2, 4.0, 0.1, 4.0), 500, 'v1b', 500, 50, 48.2, 49.8, 0.0962, 0.100, 133, 266, -0.0014, -0.014, 0.996),
    14: ('E', (0.4, 4.0, 0.1, 4.0), 500, 'v2a', 500, 50, 48.6, 51.0, 0.0972, 0.102, 197, 386, -0.00045, -0.0044, 0.996),
    15: ('F', (0.1, 1.0, 0.1, 1.0), 500, 'v1b', 500, 50, 50.4, 51.9, 0.101, 0.104, 99, 198, -0.0017, -0.016, 0.983),
    16: ('F', (0.1, 10.0, 0.1, 10.0), 500, 'v1b', 500, 50, 44.8, 48.9, 0.0897, 0.0978, 109, 218, -0.0017, -0.018, 0.999),
}
SPOT = {50: '5-6 um (x50)', 10: '25 um (x10)', 5: '50 um (x5)'}
REACTOR = 'Picosun R-150'
STRUCT = 'lateral channel, PillarHall-3 (pillar-supported polysilicon membrane over Si)'

def t1ev(c):
    s = T1[c][0]
    rows = ' and '.join(f'Series {x}' for x in s.split(';'))
    return f'Table 1, sample {c} ({rows})'

# ---------------------------------------------------------------- samples
S = []
for c, r in T1.items():
    S.append([sid(c), PID, str(c), '', 'Al2O3', 'TMA', 'H2O', 'thermal', REACTOR, STRUCT,
              f'H {r[2]} nm (design); channels L 0.1-5 mm on the chip; pillar layout {r[3]}',
              'H', 300, r[4], t1ev(c) + '; Sec. C.B'])
S.append([sid('u1'), PID, 'u', '', 'Al2O3', 'TMA', 'H2O', 'thermal', REACTOR, STRUCT,
          'H 500 nm (design)', 'H', 300, 500,
          'Fig. 6 caption: AFM sample, details only in ESI Table S4 (not one of the 16 Table 1 samples as far as the main text says)'])
for u, L in (('u2', '0.1'), ('u3', '0.5'), ('u4', '1'), ('u5', '5')):
    S.append([sid(u), PID, L, sid(8), 'Al2O3', 'TMA', 'H2O', 'thermal', REACTOR, STRUCT,
              f'H 500 nm (design); channel L {L} mm; pillar layout v1b', 'H', 300, 500,
              f'Fig. 8a legend L (mm) = {L}; caption: channels of sample 8; Sec. D.C'])
S.append([sid('u6'), PID, 'u', '', 'Al2O3', 'TMA', 'H2O', 'thermal', REACTOR, STRUCT, '', 'H', '', '',
          'Fig. 3b caption: an experimental Al2O3 profile; which sample is not said; no axis numbers'])
counts['sample.csv'] = write('sample.csv', ['sample_id', 'paper_id', 'label_as_printed', 'parent_sample', 'material',
                                            'precursor', 'coreactant', 'process_mode', 'reactor', 'structure_class',
                                            'structure_dims', 'width_kind', 'temperature_C', 'cycles', 'evidence'], S)

# ---------------------------------------------------------------- conditions
C = []
def cond(s, q, step, v, u, dk, ev):
    C.append([s, q, step, v, u, dk, ev])

# paper-wide process conditions
cond('*', 'deposition_temperature', 'none', 300, '°C', 'stated', 'Sec. C.B 1st para; Table 1 title; Figs. 4, 6, 9, 11 captions')
cond('*', 'process_pressure', 'none', 300, 'Pa', 'stated', 'Sec. C.B 1st para: about 3 hPa')
cond('*', 'carrier_gas', 'none', 'n2 (purity 6.0)', '', 'stated', 'Sec. C.B 1st para: carrier and purge gas')
cond('*', 'gas_flow_rate{gas=n2}', 'none', 150, 'sccm', 'stated', 'Sec. C.B 1st para: constant flow through four reactant lines (total or per line not said)')
cond('*', 'reactor', 'none', REACTOR, '', 'stated', 'Sec. C.B 1st para')
cond('*', 'target_film_thickness (new)', 'none', 50, 'nm', 'stated', 'Sec. C.B 1st para: about 50 nm targeted in 500 cycles')
cond('*', 'precursor_handling (new)', 'A', 'TMA handled inertly (pyrophoric)', '', 'stated', 'Sec. C.B 1st para')
cond('*', 'substrate (new)', 'none', 'low-doped Si(100), 150 mm wafers', '', 'stated', 'Sec. C.A 1st para')
cond('*', 'structure_fabrication (new)', 'none', 'thermal SiO2 to target H; multi-step poly-Si membrane from SiH4; photolithography; plug-up; HF vapour release', '', 'stated', 'Sec. C.A 1st para')
cond('*', 'chip_size (new)', 'none', '15 x 20', 'mm', 'stated', 'Sec. C.A 1st para (dicing optional)')
cond('*', 'sample_prep (new)', 'none', 'top membrane peeled off with adhesive tape before analysis', '', 'stated', 'Sec. C.C 1st para; Fig. 1c; Fig. 6 caption')
# measurement settings (no other home in the six tables)
cond('*', 'measurement_instrument (new)', 'none', 'FilmTek 2000M spectroscopic reflectometer, 380-800 nm', '', 'stated', 'Sec. C.C 4th para')
cond('*', 'scan_start_offset (new)', 'none', -13, 'µm', 'stated', 'Sec. C.C 4th para: line scan starts about 13 um before the entrance (Region I)')
cond('*', 'scan_length (new)', 'none', '198 or 398', 'µm', 'stated', 'Sec. C.C 4th para')
cond('*', 'scan_step (new)', 'none', 2, 'µm', 'stated', 'Sec. C.C 4th para; 100-200 points per scan')
cond('*', 'scan_averaging (new)', 'none', 'several scans per L (0.1-5 mm) averaged after outlier removal; Series B uses the L 5 mm scan only', '', 'stated', 'Sec. C.C 4th para; Table 1 footnote f')
cond('*', 'measurement_instrument (new)', 'none', 'Tescan Mira3 SEM with Thermo Scientific EDS', '', 'stated', 'Sec. C.C 2nd para')
cond('*', 'accelerating_voltage (new)', 'none', 5, 'kV', 'stated', 'Sec. C.C 2nd para (SEM-EDS line scan)')
cond('*', 'eds_line_scan (new)', 'none', '500 um line, 1 um interval, average of 5 scans, pillar/edge outliers removed', '', 'stated', 'Sec. C.C 2nd-3rd para')
cond('*', 'measurement_instrument (new)', 'none', 'PSIA XE-100 AFM, non-contact mode', '', 'stated', 'Sec. C.C 3rd para')
cond('*', 'afm_scan_area (new)', 'none', '10x10 to 90x90', 'µm2', 'stated', 'Sec. C.C 3rd para; 1024 x 256 pixels; first-order line-wise tilt correction')
cond('*', 'measurement_instrument (new)', 'none', 'optical microscope (top view, before and after membrane removal)', '', 'stated', 'Sec. C.C 1st para')
cond(';'.join(sid(i) for i in (1, 2, 3)), 'ald_run (new)', 'none', 'one ALD run, chips from one wafer', '', 'stated', 'Sec. C.B 2nd para (Series A)')
cond(sid('u1'), 'cycle_number', 'none', 500, 'cycle', 'stated', 'Fig. 6 caption')

for c, r in T1.items():
    tA, pA, tB, pB = r[1]
    ev = t1ev(c)
    cond(sid(c), 'pulse_time{step=reactant_A}', 'A', tA, 's', 'stated', ev + ', pulse-purge sequence (TMA pulse)')
    cond(sid(c), 'purge_time{step=purge_A}', 'purge', pA, 's', 'stated', ev + ', pulse-purge sequence (purge after TMA)')
    cond(sid(c), 'pulse_time{step=reactant_B}', 'B', tB, 's', 'stated', ev + ', pulse-purge sequence (H2O pulse)')
    cond(sid(c), 'purge_time{step=purge_B}', 'purge', pB, 's', 'stated', ev + ', pulse-purge sequence (purge after H2O)')
    cond(sid(c), 'cycle_number', 'none', r[4], 'cycle', 'stated', ev)
    cond(sid(c), 'pillar_layout (new)', 'none', r[3], '', 'stated', ev + '; layouts in ESI Table S2')
    cond(sid(c), 'reflectometer_magnification (new)', 'none', f'x{r[5]}', '', 'stated', ev + f'; spot {SPOT[r[5]]} (Sec. C.C)')
counts['condition.csv'] = write('condition.csv', ['sample_id', 'quantity', 'step', 'value', 'unit', 'data_kind', 'evidence'], C)

# ---------------------------------------------------------------- series
P = {s['series'] + '|' + s['figure'].__str__() + s['panel'] + '|' + str(s['case']): s['points']
     for s in json.load(open(f'{REPO}/cases/points.json'))['series'] if s['paper'] == PID}
def pts(key):
    return json.dumps(P[key], separators=(',', ':'))

SER = []
REFL = 'spectroscopic reflectometer line scan'
def ser(id_, samples, fig, panel, method, x, xby, y, yref, dk, pkey=None, reuse='', ev=''):
    SER.append([f'{K}:F{fig}{panel}-{id_}', samples, fig, panel, method, x, xby, y, yref, dk,
                'from points.json' if pkey else 'not read', pts(pkey) if pkey else '', reuse, ev])

# Fig. 2: four sketches
for p, x, xby, y, yref in (('a', 'distance', '', 'film_thickness (total growth, any unit)', ''),
                           ('b', 'dimensionless_distance', 'H', 'growth_per_cycle{position=local}', ''),
                           ('c', 'dimensionless_distance', 'H', 'normalized_thickness', 'entrance'),
                           ('d', 'normalized_distance (new)', 'L', 'normalized_thickness', 'entrance')):
    ser('sketch', '', 2, p, 'none (illustration)', x, xby, y, yref, 'schematic', ev='Fig. 2 caption; curve without axis numbers')
ser('ideal', '', 3, 'a', 'simulation (ideal profile, model not named)', 'dimensionless_distance', 'H', 'growth_per_cycle{position=local}', '', 'simulation', ev='Fig. 3a caption; no axis numbers; marks knee, PD50, slope, leading edge')
ser('exp', sid('u6'), 3, 'b', 'not stated (thickness-type profile)', 'dimensionless_distance', 'H', 'growth_per_cycle{position=local}', '', 'measured', ev='Fig. 3b caption; no axis numbers; shows nanostep and spikes')
ser('AlKa-map', sid(11), 5, 'a', 'SEM image with EDS Al-Ka count map (top view)', 'distance', '', 'lateral_position (new)', '', 'measured', ev='Fig. 5a caption; colour = Al X-ray counts; 100 um scale bar')
for el in ('O', 'Al', 'Si'):
    ser(el, sid(11), 5, 'b', 'SEM-EDS line scan, 5 kV', 'distance (origin mid-opening, both channel sides)', '', f'xray_intensity{{element={el}}} (new)', '', 'measured', ev='Fig. 5b caption and legend; a.u.')
ser('AFM-map', sid('u1'), 6, '', 'AFM height map, non-contact', 'distance', '', 'lateral_position (new)', '', 'measured', ev='Fig. 6 caption; colour = height; Z range printed')
for lab, s, mag in (('x5', 6, 'x5, spot 50 um'), ('x10', 5, 'x10, spot 25 um'), ('x50', 4, 'x50, spot 5 um')):
    ser(lab, sid(s), 7, '', f'{REFL}, {mag}', 'distance', '', 'film_thickness', '', 'measured', ev=f'Fig. 7 legend {lab.upper()}; caption samples 4-6; spot-to-sample by Table 1 magnification column')
i = 0
for u, L, n in (('u2', '0.1', 3), ('u3', '0.5', 3), ('u4', '1', 2), ('u5', '5', 1)):
    for k in range(n):
        i += 1
        ser(f'L{L}-scan{k+1}', sid(u), 8, 'a', REFL + ', x50, repeated scans', 'distance', '', 'film_thickness', '', 'measured',
            ev=f'Fig. 8a legend L = {L} mm (entry {k+1} of {n}); caption sample 8')
for s in (2, 4, 8, 12):
    reuse = {8: f'{K}:F9a-H500 (same sample; curve looks identical, inferred)', 12: f'{K}:F11a-0.1s (same sample; curve looks identical, inferred)'}.get(s, '')
    ser(f'S{s}', sid(s), 8, 'b', REFL + ', x50', 'distance', '', 'film_thickness', '', 'measured', reuse=reuse, ev=f'Fig. 8b legend Sample {s}')
# Fig. 9
for top, lab, smp in (('H', ('H100', 'H500', 'H2000'), (7, 8, 9)), ('N', ('N250', 'N500', 'N1000'), (10, 8, 11))):
    pa, pb, pc = ('a', 'b', 'c') if top == 'H' else ('d', 'e', 'f')
    for l, s in zip(lab, smp):
        leg = (l[1:] + ' nm') if top == 'H' else (l[1:] + ' cycles')
        base = f'{K}:F9{pa}-{l}'
        reuse_a = f'{K}:F9a-H500 (same sample 8 data)' if (top == 'N' and s == 8) else ''
        if top == 'H' and s == 8:
            reuse_a = f'average of {K}:F8a scans (inferred from Table 1 footnote f)'
        ser(l, sid(s), 9, pa, REFL + ', x50', 'distance', '', 'film_thickness', '', 'measured', reuse=reuse_a, ev=f'Fig. 9{pa} legend {leg}; caption samples')
        ser(l, sid(s), 9, pb, REFL + ', x50', 'dimensionless_distance', 'H (design)', 'growth_per_cycle{position=local}', 'divided by N', 'measured',
            reuse=f'{base} (y/N, x/H)', ev=f'Fig. 9{pb} legend {leg}')
        ref = 'entrance (no plateau)' if s == 7 else 'plateau (Region IIb)'
        if top == 'H':
            key = {7: 'H 100 nm, 500 cycles (sample 7)|9c|9', 8: 'H 500 nm, 500 cycles (sample 8)|9c|9', 9: 'H 2000 nm, 500 cycles (sample 9)|9c|9'}[s]
        else:
            key = {10: 'H 500 nm, 250 cycles (sample 10)|9f|9', 8: 'H 500 nm, 500 cycles (sample 8, same as 9c)|9f|9', 11: 'H 500 nm, 1000 cycles (sample 11)|9f|9'}[s]
        ser(l, sid(s), 9, pc, REFL + ', x50', 'dimensionless_distance', 'H (design)', 'normalized_thickness', ref, 'measured', pkey=key,
            reuse=f'{base} (y/plateau, x/H)', ev=f'Fig. 9{pc} legend {leg}; points.json case 9 (case 1/4 copies agree)' if pc == 'c' else f'Fig. 9{pc} legend {leg}; points.json case 9')
# Fig. 10 simulations
SIMKEY = {'H100': 'H 100 nm, simulated|10c|4', 'H500': 'H 500 nm, simulated|10c|4', 'H2000': 'H 2000 nm, simulated|10c|4'}
for top, labs in (('H', ('H100', 'H200', 'H500', 'H1000', 'H2000')), ('N', ('N100', 'N250', 'N500', 'N1000', 'N2000'))):
    pa, pb, pc = ('a', 'b', 'c') if top == 'H' else ('d', 'e', 'f')
    for l in labs:
        leg = (l[1:] + ' nm') if top == 'H' else (l[1:] + ' cycles')
        M = 'ylilammi_diffusion_reaction (MATLAB re-implementation)'
        ser(l, '', 10, pa, M, 'distance', '', 'film_thickness', '', 'simulation', ev=f'Fig. 10{pa} legend {leg}; inputs in caption')
        ser(l, '', 10, pb, M, 'dimensionless_distance', 'H', 'growth_per_cycle{position=local}', 'divided by N', 'simulation', reuse=f'{K}:F10{pa}-{l} (y/N, x/H)', ev=f'Fig. 10{pb} legend {leg}')
        key = SIMKEY.get(l) if top == 'H' else None
        ser(l, '', 10, pc, M, 'dimensionless_distance', 'H', 'normalized_thickness', 'entrance', 'simulation', pkey=key,
            reuse=f'{K}:F10{pa}-{l} (y/entrance, x/H)', ev=f'Fig. 10{pc} legend {leg}' + ('; points.json case 4' if key else ''))
for lab, s in (('0.1s', 12), ('0.2s', 13), ('0.4s', 14)):
    ser(lab, sid(s), 11, 'a', REFL + ', x50', 'distance', '', 'film_thickness', '', 'measured', ev=f'Fig. 11a legend TMA pulse {lab}; caption samples 12-14')
for lab, s in (('1s', 15), ('4s', 12), ('10s', 16)):
    ser(lab, sid(s), 11, 'b', REFL + ', x50', 'distance', '', 'film_thickness', '', 'measured',
        reuse=f'{K}:F11a-0.1s (same sample 12; curve looks identical, inferred)' if s == 12 else '', ev=f'Fig. 11b legend purge {lab}; caption samples 12, 15, 16')
counts['series.csv'] = write('series.csv', ['series_id', 'sample_ids', 'figure', 'panel', 'method', 'x_id', 'x_by', 'y_id', 'y_reference',
                                            'data_kind', 'points_status', 'points', 'reused_from', 'evidence'], SER)

# ---------------------------------------------------------------- values
V = []
def val(s, fs, q, qual, v, u, dk, m, rel, reg, ev):
    V.append([f'{K}:v{len(V)+1:03d}', s, fs, q, qual, v, u, dk, m, rel, reg, ev])

RM = 'reflectometer line scan'
for c, r in T1.items():
    ev = t1ev(c)
    sp = SPOT[r[5]]
    if r[6] is not None:
        val(sid(c), '', 'film_thickness', 'position=planar (Region I, outside the channel)', r[6], 'nm', 'measured', f'{RM}, {sp}', '', '', ev + ', column S_I')
    val(sid(c), '', 'film_thickness', 'position=top (Region IIb, mean of first five points; single point for H 100 nm); includes native SiO2',
        r[7], 'nm', 'measured', f'{RM}, {sp}', 'mean of first five Region IIb points', '', ev + ', column S_IIb; footnote c')
    if r[8] is not None:
        val(sid(c), '', 'growth_per_cycle', 'position=planar (GPC_I)', r[8], 'nm/cycle', 'calculated', f'{RM}, {sp}', 'S_I / N', '', ev + ', column S_I/N')
    val(sid(c), '', 'growth_per_cycle', 'position=top (GPC_IIb)', r[9], 'nm/cycle', 'calculated', f'{RM}, {sp}', 'S_IIb / N', '', ev + ', column S_IIb/N')
    val(sid(c), '', 'penetration_depth', 'level=50%', r[10], 'µm', 'measured', f'{RM}, {sp}', 'x where thickness = 50% of S_IIb', '', ev + ', column x50% (PD50%)')
    val(sid(c), '', 'coated_aspect_ratio', 'basis=AR; level=50%; w = design H (printed as x~50%)', r[11], '1', 'calculated', f'{RM}, {sp}', 'PD50 / H', '', ev + ', column x~50%')
    val(sid(c), '', 'front_slope (new)', 'y = S/N vs x~; Region III at PD50', r[12], 'nm', 'fit', 'linear fit to scaled profile', 'best straight line', '', ev + ', column slope d(S/N)/dx~; footnote d')
    val(sid(c), '', 'front_slope (new)', 'y = theta (normalized) vs x~; Region III at PD50', r[13], '1', 'fit', 'linear fit to normalized profile', 'best straight line', '', ev + ', column slope dtheta/dx~')
    val(sid(c), '', 'fit_r_squared (new)', 'of the front-slope line', r[14], '1', 'fit', 'linear fit', '', '', ev + ', column R^2')

# values in text / captions / on figures
val(';'.join(sid(i) for i in (1, 2)), '', 'penetration_depth', 'visual coated extent from the entrance (layouts v1a, v1b; L 1 mm)', 140, 'µm', 'measured', 'optical microscopy (by eye)', '', '', 'Sec. D.A 2nd para; Fig. 4a-b')
val(sid(3), '', 'penetration_depth', 'visual coated extent (layout v2a; wavy front; L 1 mm)', 100, 'µm', 'measured', 'optical microscopy (by eye)', '', '', 'Sec. D.A 2nd para; Fig. 4c')
val(sid(11), f'{K}:F5a-AlKa-map', 'penetration_depth', 'Al extent under the membrane', 125, 'µm', 'measured', 'SEM-EDS Al-Ka map', '', '', 'Sec. D.A 3rd para; Fig. 5a; ESI Fig. S5')
val(sid(11), f'{K}:F5b-Al', 'distance', 'extent of constant Region I signal in front of the channel', '-40 to 40', 'µm', 'measured', 'SEM-EDS line scan', '', '', 'Sec. D.A 4th para; Fig. 5b')
val(sid('u1'), f'{K}:F6-AFM-map', 'height_range (new)', 'Z range of the AFM map (membrane remnants and pillar holes included)', 3.081, 'µm', 'measured', 'AFM', '', '', 'Fig. 6, printed on the image')
val(sid('u1'), f'{K}:F6-AFM-map', 'afm_scan_area (new)', 'X and Y range', '90 x 90', 'µm', 'measured', 'AFM', '', '', 'Fig. 6, printed on the axes')
val(';'.join(sid(i) for i in (4, 5, 6)), f'{K}:F7-x50', 'front_width (new)', 'adsorption front width, x50 scan', 30, 'µm', 'measured', RM, '', '', 'Sec. D.B: front about 30 um wide, larger than the 5 um spot')
for s, sp in ((4, 5.5), (5, 25), (6, 50)):
    val(sid(s), '', 'spot_size (new)', {4: 'x50, stated as 5-6 um', 5: 'x10', 6: 'x5'}[s], {4: '5-6', 5: 25, 6: 50}[s], 'µm', 'assumed', 'estimated by the authors', '', '', 'Sec. C.C 4th para; Fig. 7 legend')
for s, f in ((10, 10), (8, 20), (11, 40)):
    val(sid(s), '', 'channel_filling_fraction (new)', 'share of the 500 nm channel filled by the film', f, '%', 'calculated', '', '2 S / H (matches Table 1 S_IIb, inferred)', '', 'Sec. D.D 2nd para')
val(sid(7), '', 'film_thickness', 'thickness that plugs the 100 nm entrance', 50, 'nm', 'calculated', '', 'H / 2', '', 'Sec. D.D 1st para')
val('', '', 'nanostep_height (new)', 'step at the channel entrance of PillarHall-3', '2-5', 'nm', 'measured', 'AFM (Fig. S6)', '', '', 'Sec. E.A (iv)')
for H, tol in ((100, 10), (500, 20), (2000, 30)):
    val('', '', 'feature_width', f'tolerance of design H {H} nm (oxide thickness during fabrication)', f'±{tol}', 'nm', 'measured', 'oxide thickness in fabrication (ESI Table S5)', '', '', 'Sec. E.A, (i)')
val('', '', 'pd_sensitivity_to_height (new)', 'relative PD error per 1% H error, H 500 nm', 1.5, '%/%', 'calculated', 'estimate (ESI Fig. S10)', '', '', 'Sec. E.A, (i)')
val('', '', 'pillar_effect_on_pd (new)', 'H 500 nm; pillar diameter 4 um, spacing 49 um, triangular', '<1', '%', 'calculated', 'ESI Sec. 3.2, Figs. S11-S12', '', '', 'Sec. E.A, (ii)')
val('', '', 'pillar_diameter (new)', 'typical', 4, 'µm', 'measured', '', '', '', 'Sec. E.A, (ii)')
val('', '', 'pillar_spacing (new)', 'typical interdistance, triangular symmetry', 49, 'µm', 'measured', '', '', '', 'Sec. E.A, (ii)')
for H, b in ((500, 25), (2000, 25), (100, 40)):
    val('', '', 'membrane_deflection (new)', f'inward bending of the roof, design H {H} nm' + (' (about the same as 500 nm)' if H == 2000 else ''), b, 'nm', 'measured', 'AFM (ESI Fig. S13)', '', '', 'Sec. E.A, (iii)')
val('', '', 'positioning_uncertainty (new)', 'start position of the line scan', 2, 'µm', 'assumed', 'estimated', '', '', 'Sec. E.A b, (i)')
grp = ';'.join(sid(i) for i in (2, 4, 8, 12))
val(grp, '', 'penetration_depth', 'level=50%; standard deviation over samples 2, 4, 8, 12', 19.4, 'µm', 'calculated', 'from Table 1', 'sample SD', '', 'Sec. E.A c, 2nd para (checked: 19.4)')
val(grp, '', 'front_slope (new)', 'd(S/N)/dx~ at PD50; standard deviation over samples 2, 4, 8, 12', 0.0003, 'nm', 'calculated', 'from Table 1', 'sample SD', '', 'Sec. E.A c, 2nd para')
val(grp, '', 'film_thickness', 'position=top (Region IIb); standard deviation over samples 2, 4, 8, 12', 2.8, 'nm', 'calculated', 'from Table 1', 'sample SD', '', 'Sec. E.A c, 2nd para')
val('', '', 'mean_free_path{species=tma} (new)', '300 C, process conditions', 40, 'µm', 'calculated', 'Cremers 2019 eqn (3)', '', 'Knudsen', 'Sec. E.D 2nd para; Sec. C.D (simulated conditions)')
val('', '', 'mean_free_path{species=h2o} (new)', '300 C, process conditions', 100, 'µm', 'calculated', 'Cremers 2019 eqn (3)', '', 'Knudsen', 'Sec. E.D 2nd para')
val('', '', 'hydraulic_diameter (new)', 'H 500 nm channel', 1.0, 'µm', 'calculated', '', 'h = 2/(1/H + 1/W)', '', 'Sec. E.D 2nd para')
val('', '', 'knudsen_number (new)', 'TMA, H 500 nm', 40, '1', 'calculated', '', 'Kn = lambda / h', 'Knudsen (Kn >> 1)', 'Sec. E.D 2nd para')
val('', '', 'knudsen_number (new)', 'H2O, H 500 nm', 100, '1', 'calculated', '', 'Kn = lambda / h', 'Knudsen (Kn >> 1)', 'Sec. E.D 2nd para')
val(grp, '', 'initial_sticking_coefficient', 'species=tma; lumped; averaged over samples 2, 4, 8, 12; 300 C', 4e-3, '1', 'calculated', 'arts_slope on Type 1 normalized profiles', '|dtheta/dx~| = sqrt(c/13.9)', 'Knudsen; TMA-dose-limited', 'Table 2 row This work, footnote f; Sec. E.D 3rd para')
val(sid(14), '', 'initial_sticking_coefficient', 'species=h2o; lumped; 300 C', 3e-4, '1', 'calculated', 'arts_slope on Type 1 normalized profile', '|dtheta/dx~| = sqrt(c/13.9)', 'Knudsen; H2O-dose-limited (TMA pulse 0.4 s)', 'Table 2 row This work, footnote g; Sec. E.D 3rd para; Sec. D.E')
val('', '', 'aspect_ratio', 'max design AR, L 5000 um, H 500 nm', 10000, '1', 'calculated', '', 'L / H', '', 'Sec. C.A 2nd para; Table 2 This work')
val('', '', 'feature_depth', 'range of channel lengths L measured', '100-5000', 'µm', 'measured', '', '', '', 'Sec. C.C 4th para; Sec. F 3rd para (Table 1 footnote f prints nm, a typo)')
val('', '', 'channel_filling_fraction (new)', 'recommended upper bound for a fingerprint profile', '<10', '%', 'assumed', '', '', 'Knudsen', 'Sec. F 2nd para')
# Fig. 10 simulation inputs
SIM = [('deposition_temperature', '', 300, '°C'), ('pulse_time{step=reactant_A}', 't_p', 0.10, 's'),
       ('partial_pressure{species=tma}', 'p_A0, inlet', 65, 'Pa'), ('partial_pressure{species=n2}', 'p_B, carrier', 300, 'Pa'),
       ('molar_mass{species=tma} (new)', 'M_A', 0.075, 'kg/mol'), ('molar_mass{species=n2} (new)', 'M_B', 0.028, 'kg/mol'),
       ('molecular_diameter{species=tma} (new)', 'd_A, from Ylilammi 2018', 591, 'pm'), ('molecular_diameter{species=n2} (new)', 'd_B', 374, 'pm'),
       ('metal_atoms_per_molecule{species=al2o3} (new)', 'b_film', 2, '1'), ('metal_atoms_per_molecule{species=tma} (new)', 'b_TMA', 1, '1'),
       ('saturation_growth_per_cycle', 'gpc_sat', 0.098, 'nm/cycle'), ('film_density', 'rho, from Ylivaara 2014', 3.1, 'g/cm3'),
       ('saturation_adsorption_density (new)', 'q', 3.6, '1/nm2'), ('adsorption_equilibrium_constant', 'K', 1000.0, '1/Pa'),
       ('initial_sticking_coefficient', 'species=tma; c_TMA', 0.012, '1'), ('desorption_probability (new)', 'P_d, per unit time', 0.043, '1/s'),
       ('solver_tolerance (new)', 'ODE23 relative', 1e-3, '1'), ('solver_tolerance (new)', 'ODE23 absolute', 1e-5, '1')]
for q, qual, v, u in SIM:
    ev = 'Fig. 10 caption, parameter list' if 'solver' not in q else 'Sec. C.D'
    val('', f'{K}:F10a-H500', q, '; '.join(x for x in (qual, 'all Fig. 10 curves' if 'solver' not in q else '') if x), v, u, 'chosen input', 'ylilammi_diffusion_reaction', '', 'Knudsen', ev)
for l in ('H100', 'H200', 'H500', 'H1000', 'H2000'):
    val('', f'{K}:F10a-{l}', 'feature_width', 'simulated H; N = 500; same curve in 10b, 10c', int(l[1:]) / 1000, 'µm', 'chosen input', 'ylilammi_diffusion_reaction', '', '', 'Fig. 10a legend; caption top row')
for l in ('N100', 'N250', 'N500', 'N1000', 'N2000'):
    val('', f'{K}:F10d-{l}', 'cycle_number', 'simulated N; H = 500 nm; same curve in 10e, 10f', int(l[1:]), 'cycle', 'chosen input', 'ylilammi_diffusion_reaction', '', '', 'Fig. 10d legend; caption bottom row')

# values read from series (points.json), linear interpolation at normalized thickness 0.5
def x_at(points, y0=0.5):
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        if y1 >= y0 >= y2 and y1 != y2:
            return round(x1 + (y1 - y0) * (x2 - x1) / (y1 - y2), 1)
for row in SER:
    if row[10] == 'from points.json':
        x = x_at(json.loads(row[11]))
        if x is None:
            continue
        s = row[1]
        dk = 'measured' if row[9] == 'measured' else 'calculated'
        note = 'read from points.json by linear interpolation at 0.5 (this pilot); Table 1 x~50% for comparison' if s else 'read from points.json by linear interpolation at 0.5 (this pilot); model output'
        val(s, row[0], 'coated_aspect_ratio', 'basis=AR; level=50%; w = H', x, '1', dk, 'by-eye points', 'x~ at normalized thickness 0.5', 'Knudsen' if not s else '', note)

# literature quoted (Table 2 and intro)
LIT = [('initial_sticking_coefficient', 'species=tma; 200 C; macroscopic rectangular LHAR, H 100 um, AR 200:1; 150 cycles; home-built reactor', 0.1, 'Dendooven 2009 (ref 31)'),
       ('initial_sticking_coefficient', 'species=tma; 200 C; microscopic centrosymmetric cavity, gap 4.5 um (cavity 5 um high, 2000 um long, access hole 4-100 um), AR ~100:1 (order); cross-flow hot-wall reactor', 2e-2, 'Schwille 2016 (ref 41)'),
       ('initial_sticking_coefficient', 'species=tma; 100-300 C; planar Si(100), not LHAR; order of magnitude', 1e-3, 'Vandalon 2016 (ref 60)'),
       ('initial_sticking_coefficient', 'species=h2o; 100-300 C; planar Si(100); order of magnitude', 1e-4, 'Vandalon 2016 (ref 60)'),
       ('initial_sticking_coefficient', 'species=h2o; 300 C; planar', 1e-4, 'Vandalon 2017 (ref 54), Table 2 footnote d'),
       ('initial_sticking_coefficient', 'species=h2o; 100 C; planar', 1e-6, 'Vandalon 2017 (ref 54), Table 2 footnote d'),
       ('initial_sticking_coefficient', 'species=tma; temperature-independent; planar', 2e-3, 'Vandalon 2017 (ref 54), Table 2 footnote d'),
       ('initial_sticking_coefficient', 'species=tma; 300 C; PillarHall-3, H 0.50 um, AR 2000:1; 500 cycles; Picosun R-150', 5.72e-3, 'Ylilammi 2018 (ref 33)'),
       ('film_density', 'Al2O3 density used by Ylilammi 2018 (not printed there)', 4.0, 'Table 2 footnote e'),
       ('initial_sticking_coefficient', 'species=tma; 275 C; PillarHall-3, H 0.50 um, AR 10000:1; 400 cycles; Oxford Instruments OpAL', '0.5e-3 to 2e-3', 'Arts 2019 (ref 36)'),
       ('initial_sticking_coefficient', 'species=h2o; 275 C; PillarHall-3, H 0.50 um, AR 10000:1; 400 cycles; Oxford Instruments OpAL', '0.8e-4 to 2e-4', 'Arts 2019 (ref 36)'),
       ('feature_width', 'PillarHall-1 design cavity heights; AR above 10000:1', '0.2; 0.5; 1.0', 'Gao 2015 (ref 40), Sec. A 4th para'),
       ('feature_width', 'centrosymmetric MEMS cavity limiting gap', 4.5, 'Schwille 2016/2017 (refs 30, 41), Sec. A 4th para'),
       ('macroscopic_lateral_height (new)', 'Dendooven macroscopic LHAR channel height', 'hundreds of um', 'refs 31, 39, Sec. A 4th para'),
       ('aspect_ratio', 'typical lower bound of LHAR structures', 200, 'Fig. 1 caption'),
       ('process_count (new)', 'published ALD processes', '>700', 'ref 45, Sec. A 4th para'),
       ('purge_time', 'GPC fell as purge rose from 1 to 4 s (planar Al2O3)', '1 to 4', 'Ylivaara 2014 (ref 51), Sec. E.C')]
for q, qual, v, ref in LIT:
    unit = {'feature_width': 'µm', 'film_density': 'g/cm3', 'macroscopic_lateral_height (new)': 'µm', 'purge_time': 's'}.get(q, '1')
    val('', '', q, qual, v, unit, 'literature', '', '', 'Knudsen' if 'PillarHall' in qual else '', ref + ('; Table 2' if 'ref' in ref and 'Sec.' not in ref and 'footnote' not in ref else ''))
counts['value.csv'] = write('value.csv', ['value_id', 'sample_id', 'from_series', 'quantity', 'qualifiers', 'value', 'unit', 'data_kind',
                                          'method', 'relation', 'regime', 'evidence'], V)

# ---------------------------------------------------------------- links
LK = []
def lk(s, fig, panel, kind, st, ev):
    LK.append([sid(s), fig, panel, kind, st, ev])
for c in T1:
    lk(c, 'Table 1', '', 'table', 'stated', t1ev(c) + ('; row printed twice' if c in (8, 12) else ''))
for c in (2, 4, 8, 12):
    lk(c, 'Table 2', '', 'table', 'stated', 'Table 2 footnote f: c_TMA averaged over samples 2, 4, 8, 12')
lk(14, 'Table 2', '', 'table', 'stated', 'Table 2 footnote g: c_H2O from sample 14')
for c, p in ((1, 'a'), (2, 'b'), (3, 'c')):
    lk(c, 'Fig. 4', p, 'image', 'stated', 'Fig. 4 caption: samples 1, 2, 3 = panels a, b, c (L 1 mm channel)')
lk(11, 'Fig. 5', 'a', 'map', 'stated', 'Fig. 5 caption: sample 11')
lk(11, 'Fig. 5', 'b', 'plot', 'stated', 'Fig. 5 caption: same sample')
lk('u1', 'Fig. 6', '', 'map', 'stated', 'Fig. 6 caption: sample in ESI Table S4')
for c in (4, 5, 6):
    lk(c, 'Fig. 7', '', 'plot', 'stated', 'Fig. 7 caption: samples 4, 5, 6; curve per sample via Table 1 magnification')
lk(8, 'Fig. 8', 'a', 'plot', 'stated', 'Fig. 8 caption: sample 8')
for u in ('u2', 'u3', 'u4', 'u5'):
    lk(u, 'Fig. 8', 'a', 'plot', 'stated', 'Fig. 8a legend L (channel of sample 8)')
for c in (2, 4, 8, 12):
    lk(c, 'Fig. 8', 'b', 'plot', 'stated', 'Fig. 8b legend Sample N')
for p in 'abc':
    for c in (7, 8, 9):
        lk(c, 'Fig. 9', p, 'plot', 'stated', 'Fig. 9 caption: samples 7, 8, 9; curve by H legend')
for p in 'def':
    for c in (8, 10, 11):
        lk(c, 'Fig. 9', p, 'plot', 'stated', 'Fig. 9 caption: samples 8, 10, 11; curve by N legend')
for c in (12, 13, 14):
    lk(c, 'Fig. 11', 'a', 'plot', 'stated', 'Fig. 11 caption (a): samples 12, 13, 14; curve by TMA pulse legend')
for c in (12, 15, 16):
    lk(c, 'Fig. 11', 'b', 'plot', 'stated', 'Fig. 11 caption (b): samples 12, 15, 16; curve by purge legend')
lk('u6', 'Fig. 3', 'b', 'plot', 'stated', 'Fig. 3 caption: experimental Al2O3 data, sample not named')
counts['link.csv'] = write('link.csv', ['sample_id', 'figure', 'panel', 'kind', 'stated_or_inferred', 'evidence'], LK)

print(json.dumps(counts))
