import csv, json, os
P='10.1021_acs.chemmater.2c01154'; K='mat22'
OUT='/home/ftk3187/github/PSED/psed_v2/schema_pilot/'+P+'/draft'
pts=json.load(open('/home/ftk3187/github/PSED/psed_v2/cases/points.json'))['series']
pt1c=[s for s in pts if s['paper']==P and s['figure']=='1' and s['panel']=='c'][0]['points']

PREC='Mo(NtBu)2(NMe2)2'; CO='H2S/H2/Ar remote plasma'; PM='plasma'; RX='Oxford Instruments FlexAL (remote ICP 13.56 MHz)'
SUB='planar: Si(100) with 450 nm thermal SiO2'
def r2s(r): return {'0':'R000','0.20':'R020','0.35':'R035','0.50':'R050','0.65':'R065','0.80':'R080','0.94':'R094'}[r]
def gid(T,r): return f'{K}:uT{T}{r2s(r)}'
grid={'0':['250','200','150'],'0.20':['450','350','300','250','200','150','100','50'],'0.35':['250'],
 '0.50':['350','250','200','150','100'],'0.65':['250','200','150','100'],'0.80':['450','350','250','200','150','100','50'],'0.94':['250','200','150','100']}
def cyc(T): T=int(T); return '100' if T==450 else ('120' if T in (50,300,350) else '140')
flows={'0':(10,0,40),'0.20':(8,2,40),'0.35':(6.5,3.5,40),'0.50':(5,5,40),'0.65':(3.5,6.5,40),'0.80':(2,8,40),'0.94':(2,30,18)}
cryst={}
A='amorphous';C='crystalline'
for T in ['250','200','150']: cryst[('0',T)]=A
for T,v in zip(grid['0.20'],[C,C,C,A,A,A,A,A]): cryst[('0.20',T)]=v
cryst[('0.35','250')]=A
for T,v in zip(grid['0.50'],[C,C,A,A,A]): cryst[('0.50',T)]=v
for T,v in zip(grid['0.65'],[C,C,C,A]): cryst[('0.65',T)]=v
for T,v in zip(grid['0.80'],[C,C,C,C,C,C,A]): cryst[('0.80',T)]=v
for T in grid['0.94']: cryst[('0.94',T)]=C
smo={('0','250'):'2.8',('0','200'):'3.1',('0','150'):'3.6'}
smo.update(dict(zip([('0.20',T) for T in grid['0.20']],['2.0','2.1','2.3','2.7','3.0','3.5','4.6','7.3'])))
smo[('0.35','250')]='2.5'
smo.update(dict(zip([('0.50',T) for T in grid['0.50']],['2.2','2.2','2.5','3.0','3.6'])))
smo.update(dict(zip([('0.65',T) for T in grid['0.65']],['2.1','2.2','2.1','2.2'])))
smo.update(dict(zip([('0.80',T) for T in grid['0.80']],['1.9','1.9','1.9','1.9','1.9','1.8','2.0'])))
smo.update(dict(zip([('0.94',T) for T in grid['0.94']],['1.3','1.3','1.3','1.4'])))
# colour reads (heat.py in scratch; nearest colour-bar pixel, 9x9 px patch)
gpc={('0','250'):'0.58',('0','200'):'0.59',('0','150'):'0.69',('0.20','450'):'1.25',('0.20','350'):'0.84',('0.20','300'):'0.83',('0.20','250'):'0.63',('0.20','200'):'0.64',('0.20','150'):'0.71',('0.20','100'):'1.09',('0.20','50'):'>=1.7 (top of scale)',('0.35','250'):'0.79',('0.50','350'):'1.26',('0.50','250'):'0.88',('0.50','200'):'0.86',('0.50','150'):'0.83',('0.50','100'):'1.19',('0.65','250'):'1.09',('0.65','200'):'1.06',('0.65','150'):'1.05',('0.65','100'):'1.17',('0.80','450'):'1.66',('0.80','350'):'1.45',('0.80','250'):'1.35',('0.80','200'):'1.32',('0.80','150'):'1.30',('0.80','100'):'1.36',('0.80','50'):'1.37',('0.94','250'):'0.63',('0.94','200'):'0.67',('0.94','150'):'0.67',('0.94','100'):'0.68'}
res={('0','250'):'3e2',('0','200'):'>dl',('0','150'):'>dl',('0.20','450'):'2e2',('0.20','350'):'2e1',('0.20','300'):'1.6e1',('0.20','250'):'7e1',('0.20','200'):'>dl',('0.20','150'):'>dl',('0.20','100'):'>dl',('0.20','50'):'>dl',('0.35','250'):'7.5',('0.50','350'):'8e1',('0.50','250'):'1.6',('0.50','200'):'5',('0.50','150'):'1.2e3',('0.50','100'):'>dl',('0.65','250'):'0.9',('0.65','200'):'0.8',('0.65','150'):'0.5',('0.65','100'):'2.3',('0.80','450'):'0.6',('0.80','350'):'5',('0.80','250'):'1.1',('0.80','200'):'0.9',('0.80','150'):'0.4',('0.80','100'):'0.2',('0.80','50'):'0.35',('0.94','250'):'4e-3',('0.94','200'):'8e-3',('0.94','150'):'9e-3',('0.94','100'):'1.5e-2'}

samples=[]; conds=[]; series=[]; values=[]; links=[]
def S(sid,label,parent,mat,prec,co,pm,rx,sc,dims,wk,T,cy,ev): samples.append([sid,P,label,parent,mat,prec,co,pm,rx,sc,dims,wk,T,cy,ev])
def Cn(sid,q,step,v,u,dk,ev): conds.append([sid,q,step,v,u,dk,ev])
vid=[0]
def V(sid,fs,q,qual,v,u,dk,meth,rel,reg,ev):
    vid[0]+=1; values.append([f'{K}:v{vid[0]:03d}',sid,fs,q,qual,v,u,dk,meth,rel,reg,ev]); return f'{K}:v{vid[0]:03d}'
def L(sid,fig,pan,kind,si,ev): links.append([sid,fig,pan,kind,si,ev])
def SE(sid,samp,fig,pan,meth,x,xby,y,yref,dk,ps,pp,ev): series.append([sid,samp,fig,pan,meth,x,xby,y,yref,dk,ps,json.dumps(pp) if pp else '','',ev])

# ---------------- samples
for r,Ts in grid.items():
    for T in Ts:
        sid=gid(T,r)
        S(sid,'u','',  'MoSx',PREC,CO,PM,RX,'planar',SUB,'none',T,cyc(T),f'Figs. 2, 4, 7b, 8 grid cell (T={T} C, H2 ratio {r}); cycles from Exp. Film Deposition, cycle-number para (100/120/140 by temperature); captions say 100-140 cycles')
        Cn(sid,'h2_flow_ratio (new)','plasma',r,'1','stated','Figs. 2/4/7b/8 x axis; Eq. 1')
        h2s,h2,ar=flows[r]
        Cn(sid,'gas_flow_rate{gas=H2S}','plasma',h2s,'sccm','stated','Table 2 row for this ratio')
        Cn(sid,'gas_flow_rate{gas=H2}','plasma',h2,'sccm','stated','Table 2 row for this ratio')
        Cn(sid,'gas_flow_rate{gas=Ar}','plasma',ar,'sccm','stated','Table 2 row for this ratio')
        Cn(sid,'cycle_number','none',cyc(T),'cycle','stated','Exp. Film Deposition, cycle-number para (rule "in most of the depositions"; captions 100-140)')
        if int(T)>=200: Cn(sid,'wall_temperature (new)','none','150','°C','stated','Exp. Film Deposition 1st para: walls at 150 C when table at 200-450 C')
        else: Cn(sid,'wall_temperature (new)','none',T,'°C','stated','Exp. Film Deposition 1st para: walls = substrate for 50-150 C')
S(f'{K}:u1b_10c','10 cyc (0.9 nm)','', 'MoS2',PREC,CO,PM,RX,'planar',SUB,'none','150','10','Fig. 1b legend + caption; ratio 0.80 from Results "Concept" 3rd para')
S(f'{K}:u1b_20c','20 cyc (1.6 nm)','', 'MoS2',PREC,CO,PM,RX,'planar',SUB,'none','150','20','Fig. 1b legend')
S(f'{K}:u1b_30c','30 cyc (2.6 nm)','', 'MoS2',PREC,CO,PM,RX,'planar',SUB,'none','150','30','Fig. 1b legend')
S(f'{K}:u1b_50c','50 cyc (4.8 nm)','', 'MoS2',PREC,CO,PM,RX,'planar',SUB,'none','150','50','Fig. 1b legend')
S(f'{K}:u1b_sub','SiO2/Si','', 'none (bare substrate)','','','','','planar','Si with 450 nm SiO2 (inferred)','none','','0','Fig. 1b legend: bare substrate spectrum')
for c in ['10','20','30','50']:
    sid=f'{K}:u1b_{c}c'; Cn(sid,'h2_flow_ratio (new)','plasma','0.80','1','stated','Results "Concept" 3rd para (optimized 0.80, Fig. 1b)'); Cn(sid,'cycle_number','none',c,'cycle','stated','Fig. 1b legend')
S(f'{K}:W1','u','', 'MoS2',PREC,CO,PM,RX,'planar','4 inch Si wafer with 450 nm SiO2','none','150','50','Fig. 1c caption; Exp. Film Characterization, ex situ SE para')
Cn(f'{K}:W1','h2_flow_ratio (new)','plasma','0.80','1','stated','Fig. 1c caption'); Cn(f'{K}:W1','cycle_number','none','50','cycle','stated','Fig. 1c caption')
S(f'{K}:W0','u','', 'none (bare substrate)','','','','','planar','4 inch Si wafer with 450 nm SiO2','none','','0','Exp. ex situ SE para: bare wafer mapped as reference (no data shown)')
S(f'{K}:PET','u','', 'MoS2',PREC,CO,PM,RX,'planar','PET foil 15x15 cm, 125 um (Melinex ST504), uncoated','none','100','50','Fig. 1d caption; Exp. Film Deposition 2nd para')
S(f'{K}:PET_Al','u','', 'MoS2',PREC,CO,PM,RX,'planar','PET foil precoated with ALD Al2O3 (50 cycles TMA/H2O)','none','100','50','Exp. Film Deposition 2nd para: coated and uncoated PET gave similar results (inferred same recipe as Fig. 1d)')
for s in ['PET','PET_Al']:
    Cn(f'{K}:{s}','h2_flow_ratio (new)','plasma','0.80','1','stated','Fig. 1d caption'); Cn(f'{K}:{s}','cycle_number','none','50','cycle','stated','Fig. 1d caption')
Cn(f'{K}:PET_Al','substrate_precoat (new)','none','Al2O3, 50 ALD cycles AlMe3/H2O','','stated','Exp. Film Deposition 2nd para')
S(f'{K}:F100','u','', 'MoS2',PREC,CO,PM,RX,'planar','Si with 90 nm thermal SiO2 (transistor substrate)','none','100','50','Fig. 3a caption; Results "Concept" last para; FET para; Exp. TEM para (thin 100 C sample patterned into transistors)')
S(f'{K}:F350','u','', 'MoS2',PREC,CO,PM,RX,'planar','Si with 90 nm thermal SiO2 (transistor substrate)','none','350','60','Fig. 3b caption (reference after Sharma et al.); FET para')
Cn(f'{K}:F100','h2_flow_ratio (new)','plasma','0.80','1','stated','Fig. 3a caption'); Cn(f'{K}:F100','cycle_number','none','50','cycle','stated','Fig. 3a caption')
Cn(f'{K}:F350','h2_flow_ratio (new)','plasma','0.20','1','stated','Fig. 3b caption'); Cn(f'{K}:F350','cycle_number','none','60','cycle','stated','Fig. 3b caption')
Cn(f'{K}:F350','wall_temperature (new)','none','150','°C','stated','Exp. Film Deposition 1st para')
Cn(f'{K}:F100','post_process (new)','none','transistor channel patterning and Au/Ni contact deposition before FIB','','stated','Exp. TEM para')
Cn(f'{K}:F350','post_process (new)','none','transistor channel patterning and Au/Ni contact deposition before FIB','','stated','Exp. TEM para')
for r in ['0.20','0.65','0.80']:
    sid=f'{K}:uRBS{r2s(r)}'
    S(sid,'u','', 'MoSx',PREC,CO,PM,RX,'planar','glassy carbon substrate','none','150','','Table 1 footnote (~50 nm films on glassy carbon); Results "Film Composition" RBS para; cycles not stated')
    Cn(sid,'h2_flow_ratio (new)','plasma',r,'1','stated','Table 1 row')
    h2s,h2,ar=flows[r]
    Cn(sid,'gas_flow_rate{gas=H2S}','plasma',h2s,'sccm','stated','Table 2'); Cn(sid,'gas_flow_rate{gas=H2}','plasma',h2,'sccm','stated','Table 2'); Cn(sid,'gas_flow_rate{gas=Ar}','plasma',ar,'sccm','stated','Table 2')
S(f'{K}:uT150R065_500c','u','', 'MoS2',PREC,CO,PM,RX,'planar',SUB,'none','150','500','Fig. 6b caption; Exp. TEM para (thick ~50 nm sample used as deposited)')
Cn(f'{K}:uT150R065_500c','h2_flow_ratio (new)','plasma','0.65','1','stated','Fig. 6b caption'); Cn(f'{K}:uT150R065_500c','cycle_number','none','500','cycle','stated','Fig. 6b caption')
WP='W(NtBu)2(NMe2)2 (analogous to Mo precursor)'; TP='Ti(NMe2)4'
S(f'{K}:uWS_R000','0','', 'WSx',WP,'H2S/Ar remote plasma (ref. 52 process)',PM,'not stated (literature procedure, ref. 52)','planar',SUB+' (inferred, Si peak in Raman)','none','150','','Fig. 9a legend; Results "Other TMDCs" 2nd para; Exp. WS/TiS para')
S(f'{K}:uWS_R080','0.80','', 'WS2',WP,CO,PM,'not stated (literature procedure, ref. 52)','planar',SUB+' (inferred)','none','150','','Fig. 9a legend; Exp. WS/TiS para')
S(f'{K}:uTiS_R000','0','', 'TiSx',TP,'H2S/Ar remote plasma (ref. 53 process)',PM,'not stated (literature procedure, ref. 53)','planar',SUB+' (inferred)','none','100','','Fig. 9b legend')
S(f'{K}:uTiS_R050','0.50','', 'TiS2',TP,CO,PM,'not stated (literature procedure, ref. 53)','planar',SUB+' (inferred)','none','100','','Fig. 9b legend; Exp. WS/TiS para')
S(f'{K}:uTiS_thermal','Thermal ALD','', 'TiSx',TP,'H2S (thermal recipe, ref. 80; co-reactant inferred)','thermal','not stated','planar',SUB+' (inferred)','none','100 (inferred from Fig. 9b title)','','Fig. 9b legend; Exp. WS/TiS para')
S(f'{K}:uTiS_R080','u','', 'TiSx (S-poor)',TP,CO,PM,'not stated','planar','not stated','none','100 (inferred)','','Results "Other TMDCs" 3rd para: ratio 0.80 too high, S-poor (not shown)')
for sid,r in [('uWS_R000','0'),('uWS_R080','0.80'),('uTiS_R000','0'),('uTiS_R050','0.50'),('uTiS_R080','0.80')]:
    Cn(f'{K}:{sid}','h2_flow_ratio (new)','plasma',r,'1','stated','Fig. 9 legend / text')
S(f'{K}:uHplasma','u','', 'MoS2',PREC,CO+' + extra H2 plasma step',PM,RX,'planar','not stated','none','150','','Results "Role of hydrogen" 3rd para; Table S8 not in document')
S(f'{K}:uHgas','u','', 'MoSx',PREC,CO+' + extra H2 gas step',PM,RX,'planar','not stated','none','150','','Results "Role of hydrogen" 3rd para')
for s in ['uHplasma','uHgas']:
    Cn(f'{K}:{s}','h2_flow_ratio (new)','plasma','0.20','1','stated','Results "Role of hydrogen" 3rd para')
Cn(f'{K}:uHplasma','extra_step (new)','plasma','H2 plasma after H2S/H2/Ar plasma (duration not stated)','','stated','Results "Role of hydrogen" 3rd para')
Cn(f'{K}:uHgas','extra_step (new)','none','H2 gas after H2S/H2/Ar plasma (duration not stated)','','stated','Results "Role of hydrogen" 3rd para')
S(f'{K}:uLowH2S_T250','u','', 'MoS2',PREC,'H2S/Ar remote plasma, reduced H2S flow',PM,RX,'planar','not stated','none','250','','Results "Role of hydrogen" last para (Fig. S22a, not in document)')
S(f'{K}:uLowH2S_T150','u','', 'MoSx',PREC,'H2S/Ar remote plasma, reduced H2S flow',PM,RX,'planar','not stated','none','150','','Results "Role of hydrogen" last para (Fig. S22b, not in document)')
for s in ['uLowH2S_T250','uLowH2S_T150']:
    Cn(f'{K}:{s}','h2_flow_ratio (new)','plasma','0','1','stated','Results "Role of hydrogen" last para (no added H2)')
    Cn(f'{K}:{s}','gas_flow_rate{gas=H2S}','plasma','below 10 (value not stated)','sccm','stated','Results "Role of hydrogen" last para')

# ---------------- paper-wide conditions
E1='Exp. Film Deposition'
for q,st,v,u,dk,ev in [
 ('reactor','none','Oxford Instruments FlexAL','','stated',E1+' 1st para'),
 ('plasma_configuration','plasma','remote inductively coupled plasma','','stated',E1+' 1st para'),
 ('plasma_frequency (new)','plasma','13.56','MHz','stated',E1+' 1st para'),
 ('base_pressure (new)','none','1e-6','Torr','stated',E1+' 1st para (turbo pump)'),
 ('temperature_reported_as (new)','none','substrate table setpoint; actual substrate cooler at >=200 C, negligible difference at <=150 C','','stated',E1+' 1st para'),
 ('structure','none','planar','','stated',E1+' 2nd para'),
 ('substrate (new)','none','Si(100) with 450 nm thermal SiO2 (Siegert Wafer) for most depositions','','stated',E1+' 2nd para'),
 ('substrate (new)','none','fused SiO2 for some Hall samples; Si with 90 nm SiO2 for transistors; PET foil 125 um','','stated',E1+' 2nd para'),
 ('substrate_prep (new)','none','used as received; cut to size; blown with pressurized N2','','stated',E1+' 3rd para'),
 ('substrate_size (new)','none','1x1 to 3x3','cm2','stated',E1+' 3rd para'),
 ('substrate_carrier (new)','none','8 inch carrier wafer','','stated',E1+' 3rd para'),
 ('loadlock_pressure (new)','none','<1e-2','Torr','stated',E1+' 3rd para'),
 ('preheat_time (new)','none','10','min','stated',E1+' 3rd para (equilibrate under Ar)'),
 ('process_pressure','none','200','mTorr','stated',E1+' 3rd para (during the 10 min equilibration)'),
 ('reactant_A','A',PREC,'','stated','Results "Concept" 1st para; '+E1+' 5th para'),
 ('precursor_purity (new)','A','98','%','stated',E1+' 5th para (Strem)'),
 ('source_temperature','A','50','°C','stated',E1+' 5th para'),
 ('carrier_gas','A','Ar','','stated',E1+' 5th para'),
 ('gas_flow_rate{gas=Ar carrier}','A','50','sccm','stated',E1+' 5th para'),
 ('delivery_line_temperature (new)','A','70','°C','stated',E1+' 5th para'),
 ('pulse_time','A','6','s','stated',E1+' 5th para'),
 ('process_pressure','A','200','mTorr','stated',E1+' 5th para (set by automatic pressure control valve)'),
 ('stabilization_time (new)','A','4','s','stated',E1+' 5th para (before precursor pulse)'),
 ('purge_time','purge','10','s','stated',E1+' 5th para: after Mo dose, 6 s with 300 sccm Ar + 4 s pump-down without flow'),
 ('gas_flow_rate{gas=Ar purge}','purge','300','sccm','stated',E1+' 5th para'),
 ('reactant_B','plasma','H2S/H2/Ar plasma','','stated','Results "Concept" 1st para'),
 ('gas_purity (new)','plasma','H2S 99.5%; H2 99.999%; Ar 99.999% (Linde)','','stated',E1+' 4th para'),
 ('gas_flow_rate{gas=total through ICP}','plasma','50','sccm','stated',E1+' 4th para; Table 2 footnote'),
 ('gas_flow_rate{gas=H2+H2S}','plasma','10','sccm','stated',E1+' 4th para (except ratio 0.94: 32 sccm, Table 2)'),
 ('stabilization_time (new)','plasma','5','s','stated',E1+' 5th para (before plasma)'),
 ('pulse_time','plasma','20','s','stated',E1+' 5th para'),
 ('plasma_power','plasma','100','W','stated',E1+' 5th para'),
 ('process_pressure','plasma','6','mTorr','stated',E1+' 4th and 5th para (approximate, valve open)'),
 ('purge_time','purge','6','s','stated',E1+' 5th para: after plasma, 300 sccm Ar'),
 ('cycle_time (new)','none','51','s','stated',E1+' 5th para'),
 ('cycle_number','none','100 (450 C), 120 (50, 300, 350 C), 140 (100-250 C)','cycle','stated',E1+' 6th para: chosen for ~10 nm at ratio 0.20; unless noted otherwise'),
 ('h2_flow_ratio (new)','plasma','definition H2/(H2+H2S) flow','1','stated','Eq. 1; Table 2'),
 ('process_mode','none','plasma (PEALD); thermal TiSx comparison recipe','','stated','Abstract; '+E1+' 7th para'),
 ('h2_flow_ratio_reference (new)','plasma','Sharma et al. ref. 36 used 8 sccm H2S + 2 sccm H2 (ratio 0.20); erratum of that paper noted','','stated',E1+' 4th para'),
 ('alds_regime_check (new)','none','plasma alone gives no S deposition (SE); Mo precursor does not condense at 50-100 C','','stated',E1+' 6th para'),
 ]:
    Cn('*',q,st,v,u,dk,ev)
for c in conds:
    if c[1]=='h2_flow_ratio (new)' and c[0]=='*': c[3]='H2/(H2+H2S) by flow'

# ---------------- series
g='mat22:grid (all uT*R* samples)'
for r in ['0.94','0.80','0.65','0.50','0.20','0']:
    SE(f'{K}:s1a_{r2s(r)}',gid('150',r),'1','a','Raman (514 nm)','raman_shift (new)','h2_flow_ratio (new)','raman_intensity (new)','arb. units, curves offset','measured','not read',None,'Fig. 1a legend + caption (150 C, 140 cycles)')
for c,lab in [('50','50 cyc (4.8 nm)'),('30','30 cyc'),('20','20 cyc'),('10','10 cyc')]:
    SE(f'{K}:s1b_{c}c',f'{K}:u1b_{c}c','1','b','Raman (514 nm)','raman_shift (new)','cycle_number','raman_intensity (new)','normalized to Si peak, offset','measured','not read',None,'Fig. 1b legend '+lab)
SE(f'{K}:s1b_sub',f'{K}:u1b_sub','1','b','Raman (514 nm)','raman_shift (new)','','raman_intensity (new)','normalized to Si peak','measured','not read',None,'Fig. 1b legend SiO2/Si')
SE(f'{K}:s1c_map',f'{K}:W1','1','c','ex situ SE mapping (M-2000, 1.2-3.3 eV)','wafer_position (new)','','film_thickness{position=planar}','absolute nm (colour scale)','measured','from points.json',pt1c,'Fig. 1c; points = vertical diameter of the map read by eye (cases/points.json, case 6)')
SE(f'{K}:s2_map',g,'2','','Raman classification','h2_flow_ratio (new)','deposition_temperature','crystallinity','two classes','measured','not read',None,'Fig. 2 (legend Crystalline/Amorphous); cell values in value.csv')
SE(f'{K}:s4_map',g,'4','','XPS','h2_flow_ratio (new)','deposition_temperature','atomic_ratio{S/Mo} (new)','printed per cell','measured','not read',None,'Fig. 4; numbers printed in cells -> value.csv')
for pan,reg in [('a','Mo 3d / S 2s'),('b','S 2p')]:
    for r in ['0.94','0.80','0.65','0.50','0.20']:
        for part,dk in [('data','measured'),('fit envelope','fit'),('background','fit'),('components','fit')]:
            SE(f'{K}:s5{pan}_{r2s(r)}_{part.split()[0]}',gid('150',r),'5',pan,'XPS '+reg+(' (Shirley background; GL components)' if dk=='fit' else ''),'binding_energy (new)','h2_flow_ratio (new)','xps_intensity (new)','arb. units, stacked','measured' if dk=='measured' else 'fit','not read',None,f'Fig. 5{pan} legend ({part}); stack label {r}')
for r in ['0','0.20','0.50','0.65','0.80','0.94']:
    SE(f'{K}:s7a_{r2s(r)}',gid('150',r),'7','a','in situ SE (every 10 cycles)','cycle_number','h2_flow_ratio (new)','film_thickness{position=planar}','absolute nm (dense layer + half roughness layer)','measured','not read',None,'Fig. 7a legend '+r)
SE(f'{K}:s7b_map',g,'7','b','in situ SE','h2_flow_ratio (new)','deposition_temperature','growth_per_cycle{position=planar}','average over first 100 cycles, Å/cycle colour scale','measured','not read',None,'Fig. 7b; cells read from colour -> value.csv')
SE(f'{K}:s8_map',g,'8','','four-point probe x in situ SE thickness','h2_flow_ratio (new)','deposition_temperature','resistivity','log colour scale, >dl class','measured','not read',None,'Fig. 8; cells read from colour -> value.csv')
SE(f'{K}:s9a_R080',f'{K}:uWS_R080','9','a','Raman','raman_shift (new)','h2_flow_ratio (new)','raman_intensity (new)','arb. units','measured','not read',None,'Fig. 9a legend 0.80')
SE(f'{K}:s9a_R000',f'{K}:uWS_R000','9','a','Raman','raman_shift (new)','h2_flow_ratio (new)','raman_intensity (new)','arb. units','measured','not read',None,'Fig. 9a legend 0')
SE(f'{K}:s9b_R050',f'{K}:uTiS_R050','9','b','Raman','raman_shift (new)','h2_flow_ratio (new)','raman_intensity (new)','arb. units','measured','not read',None,'Fig. 9b legend 0.50')
SE(f'{K}:s9b_R000',f'{K}:uTiS_R000','9','b','Raman','raman_shift (new)','h2_flow_ratio (new)','raman_intensity (new)','arb. units','measured','not read',None,'Fig. 9b legend 0')
SE(f'{K}:s9b_thermal',f'{K}:uTiS_thermal','9','b','Raman','raman_shift (new)','process_mode','raman_intensity (new)','arb. units','measured','not read',None,'Fig. 9b legend Thermal ALD')

# ---------------- values
for (r,T),v in cryst.items(): V(gid(T,r),f'{K}:s2_map','crystallinity','Raman class',v,'','measured','Raman','','','Fig. 2 cell')
for (r,T),v in smo.items(): V(gid(T,r),f'{K}:s4_map','atomic_ratio (new)','S/Mo; XPS',v,'1','measured','XPS','','','Fig. 4 cell (printed)')
for (r,T),v in gpc.items(): V(gid(T,r),f'{K}:s7b_map','growth_per_cycle','planar; average of first 100 cycles; read from colour bar (+-0.03)',v,'Å/cycle','measured','in situ SE; colour read by script','thickness after 100 cycles / 100','','Fig. 7b cell')
for (r,T),v in res.items(): V(gid(T,r),f'{K}:s8_map','resistivity','read from log colour bar (factor ~1.5); >dl = above four-point probe limit',v,'Ω cm','measured','four-point probe sheet resistance x in situ SE thickness; colour read by script','rho = R_sheet x t','','Fig. 8 cell')
for r,v in [('0.94','1.3'),('0.80','1.9'),('0.65','2.1'),('0.50','3.0'),('0.20','3.5')]:
    V(gid('150',r),f'{K}:s5a_{r2s(r)}_data','atomic_ratio (new)','S/Mo; XPS; printed beside spectrum',v,'1','measured','XPS','','','Fig. 5a/5b stack labels')
for r,v in [('0','9.4'),('0.20','9.6'),('0.50','11.3'),('0.65','14.9'),('0.80','20.2'),('0.94','11.0')]:
    V(gid('150',r),f'{K}:s7a_{r2s(r)}','film_thickness','planar; after 140 cycles; read by eye (+-0.3 nm)',v,'nm','measured','in situ SE','','','Fig. 7a last point')
for c,t in [('10','0.9'),('20','1.6'),('30','2.6'),('50','4.8')]:
    V(f'{K}:u1b_{c}c',f'{K}:s1b_{c}c','film_thickness','planar; ex situ SE',t,'nm','measured','ex situ SE','','','Fig. 1b legend')
V(f'{K}:W1',f'{K}:s1c_map','film_thickness','mean over 4 inch wafer','5.1','nm','measured','ex situ SE mapping','','','Fig. 1c title')
V(f'{K}:W1',f'{K}:s1c_map','film_thickness','standard deviation over wafer','0.2','nm','measured','ex situ SE mapping','','','Fig. 1c title')
V(f'{K}:W1',f'{K}:s1c_map','thickness_nonuniformity','relative standard deviation (sigma)','3.3','%','measured','ex situ SE mapping','sigma / mean','','Fig. 1c title; Results "Concept" 4th para')
V(f'{K}:PET','','film_thickness','approximate','5','nm','measured','not stated','','','Fig. 1d caption')
V(f'{K}:PET','','resistivity','also unchanged after repeated bending by hand','0.3','Ω cm','measured','four-point probe','','','Results "Concept" 4th para')
V(f'{K}:PET','','optical_transparency (new)','qualitative','highly transparent','','measured','visual','','','Results "Concept" 4th para; Fig. 1d')
V(f'{K}:F100','','film_thickness','sub-5 nm / approximately 5 nm','5','nm','measured','TEM / not stated','','','Results "Concept" last para; FET para')
V(f'{K}:F100','','crystallinity','fully crystallized','crystalline','','measured','cross-sectional TEM','','','Results "Concept" last para; Fig. 3a')
V(f'{K}:F100','','monolayer_count (new)','crystallite thickness','4-5','monolayers','measured','cross-sectional TEM','','','Results "Concept" last para')
V(f'{K}:F100','','crystallite_width (new)','lateral, approximate','5-10','nm','measured','cross-sectional TEM','','','Results "Concept" last para')
V(f'{K}:F100','','surface_roughness_rq (new)','root mean square','0.75','nm','measured','AFM 500x500 nm2','','','Results "Concept" last para (continued after Fig. 3)')
V(f'{K}:F350','','monolayer_count (new)','film thickness','5-6','monolayers','measured','cross-sectional TEM','','','Results "Concept" last para; Fig. 3b')
V(f'{K}:F350','','film_thickness','similar to 100 C film (~5 nm)','5','nm','measured','not stated','','','FET para; Exp. TEM para')
for sid in ['F100','F350']:
    V(f'{K}:{sid}','','conduction_type (new)','FET','p-type','','measured','FET','','','FET para')
    V(f'{K}:{sid}','','on_off_ratio (new)','FET current','3-4','1','measured','FET (Fig. S13, not in document)','','','FET para')
V(f'{K}:F100','','output_current_ratio (new)','100 C FET vs 350 C FET','>10','1','measured','FET','','','FET para')
V(f'{K}:F100','','contact_behaviour (new)','Ni contacts','non-linear I-V (Schottky barrier)','','measured','FET','','','FET para')
V(f'{K}:F350','','contact_behaviour (new)','Ni contacts','close to Ohmic','','measured','FET','','','FET para')
V(f'{K}:F100','','interface_layer_thickness (new)','amorphous layer MoS2/Ni','2-3','nm','measured','cross-sectional TEM (Fig. S14, not in document)','','','FET para 2')
V(f'{K}:F350','','interface_layer_thickness (new)','amorphous layer MoS2/Ni','1','nm','measured','cross-sectional TEM (Fig. S14)','','','FET para 2')
for r,row in [('0.20',['3.7 ± 0.1','3.4 ± 0.2','3.2','6.4 ± 0.5','<dl (~7)','0.5 ± 0.2','0.8 ± 0.2']),('0.65',['2.1 ± 0.1','2.1 ± 0.1','4.0','11.7 ± 0.9','<dl (~7)','1.5 ± 0.4','0.5 ± 0.1']),('0.80',['1.8 ± 0.1','1.9 ± 0.1','3.1','22 ± 2','<dl (~7)','1.0 ± 0.3','5 ± 2'])]:
    sid=f'{K}:uRBS{r2s(r)}'
    V(sid,'','atomic_ratio (new)','S/Mo; RBS',row[0],'1','measured','RBS 2 MeV He+','','','Table 1')
    V(sid,'','atomic_ratio (new)','S/Mo; XPS',row[1],'1','measured','XPS','','','Table 1')
    V(sid,'','film_density','',row[2],'g/cm3','calculated','RBS areal density / SE thickness','rho = areal atom density x mass / thickness','','Table 1 + footnote')
    for el,v,m in [('H',row[3],'ERD'),('C',row[4],'RBS'),('N',row[5],'RBS'),('O',row[6],'RBS')]:
        V(sid,'','composition',f'element={el}',v,'at.%','measured',m,'','','Table 1')
    V(sid,'','film_thickness','approximate','50','nm','measured','SE','','','Table 1 footnote')
V(f'{K}:uRBS{r2s("0.20")}','','metal_atoms_per_cycle (new)','Mo; RBS','0.6','at/nm2/cycle','measured','RBS','','','Results "Film Growth" 3rd para (link to the Table 1 films inferred)')
V(f'{K}:uRBS{r2s("0.65")}','','metal_atoms_per_cycle (new)','Mo; RBS','1.6','at/nm2/cycle','measured','RBS','','','Results "Film Growth" 3rd para')
V(f'{K}:uRBS{r2s("0.80")}','','metal_atoms_per_cycle (new)','Mo; RBS; highest observed','2.2','at/nm2/cycle','measured','RBS','','','Results "Film Growth" 5th para')
V(f'{K}:uRBS{r2s("0.65")}','','hydrogen_density (new)','from 12 at.% H','6e21','atoms/cm3','calculated','ERD at.% x atom density','','','Results "Electrical" 4th para')
V(f'{K}:uRBS{r2s("0.65")}','','carrier_density','one third of H density (stated ratio); Hall link to RBS film inferred','2e21','cm-3','calculated','AC Hall','6e21 / 3','','Results "Electrical" 4th para')
V('','','film_density','bulk MoS2','5.06','g/cm3','literature','CRC Handbook (ref. 66)','','','Table 1 footnote')
V(f'{K}:uT150R065_500c','','film_thickness','approximate','50','nm','measured','TEM','','','Fig. 6b caption')
V(f'{K}:uT150R065_500c','','oriented_layer_thickness (new)','basal planes parallel to substrate near interface; random above','5','nm','measured','cross-sectional TEM','','','Results "Film Morphology" 4th para')
for r,v in [('0','0.4'),('0.20','0.7'),('0.50','0.4'),('0.65','0.9'),('0.80','3.1'),('0.94','4.0')]:
    V(gid('150',r),'','surface_roughness_rq (new)','AFM 500x500 nm2; printed on SEM image',v,'nm','measured','AFM','','','Fig. 6a label')
    V(gid('150',r),'','crystallinity','row label in Fig. 6a',C if r in ('0.65','0.80','0.94') else A,'','measured','Raman (as classed in Fig. 6a)','','','Fig. 6a row label')
V('','','film_thickness','150 C, ratios 0-0.94, 140 cycles (Fig. 6a films)','8-20','nm','measured','SE','','','Fig. 6a caption')
# XPS BEs
for comp,v in [('Mo(4-d)+','228.9'),('Mo4+','229.6'),('Mo5+','231.1'),('Mo6+','232.9')]:
    V(gid('150','0.80'),'','binding_energy (new)',f'Mo 3d5/2; {comp}',v,'eV','measured','XPS fit','','','Results "Film Composition" 4th para')
V(gid('150','0.80'),'','binding_energy (new)','S 2p3/2; S2- in MoS2','162.4','eV','measured','XPS fit','','','Results "Film Composition" 5th para')
V(gid('150','0.80'),'','binding_energy_shift (new)','S 2p electron-rich S2- doublet relative to main','-0.9','eV','measured','XPS fit','','','Results "Film Composition" 5th para')
V(gid('150','0.50'),'','binding_energy (new)','S 2p3/2; lower BE doublet','161.9','eV','measured','XPS fit','','','Results "Film Composition" 6th para')
V(gid('150','0.50'),'','binding_energy (new)','S 2p3/2; higher BE doublet','163.1','eV','measured','XPS fit','','','Results "Film Composition" 6th para')
V(gid('150','0.50'),'','peak_area_ratio (new)','S 2p high-BE / low-BE doublet','~1','1','measured','XPS fit','','','Results "Film Composition" 6th para')
V('','','binding_energy (new)','Mo 3d5/2 MoS2 literature average','229.3 ± 0.5','eV','literature','NIST XPS database (ref. 63)','','','Results "Film Composition" 4th para')
V('','','binding_energy (new)','Mo 3d5/2 MoO3 literature average','232.7 ± 0.3','eV','literature','NIST XPS database (ref. 63)','','','Results "Film Composition" 4th para')
V('','','atomic_ratio (new)','S/Mo; XPS; range of most crystalline films','1.8-2.3','1','measured','XPS','','','Results "Film Composition" 1st para')
V('','','atomic_ratio (new)','S/Mo; XPS; amorphous films at >=150 C','2.5-3.6','1','measured','XPS','','','Results "Film Composition" 1st para')
V('','','composition','element=N; range over RBS films','0.5-1.5','at.%','measured','RBS','','','Results "Film Composition" RBS para')
# electrical
V('','','resistivity','detection limit of four-point probe, 10 nm films','~1000','Ω cm','measured','four-point probe','','','Results "Electrical" 1st para')
V(gid('100','0.65'),'','resistivity','lowest for an amorphous film (MoS2.2)','2','Ω cm','measured','four-point probe','','','Results "Electrical" 1st para')
V('','','resistivity','crystalline films at ratio 0.80, lowest range','0.1-1','Ω cm','measured','four-point probe','','','Results "Electrical" 2nd para; Conclusions')
V(gid('300','0.20'),'','resistivity','','15','Ω cm','measured','four-point probe','','','Results "Electrical" 2nd para')
V(gid('450','0.20'),'','resistivity','','220','Ω cm','measured','four-point probe','','','Results "Electrical" 2nd para')
V('','','resistivity','ratio 0.94, lowest','4e-3','Ω cm','measured','four-point probe','','','Results "Electrical" 2nd para')
V('','','mobility','Hall; c-MoS2, ratios 0.50-0.80, 100-250 C','0.001-0.01','cm2/(V s)','measured','AC Hall, van der Pauw','','','Results "Electrical" 3rd para')
V('','','carrier_density','holes; c-MoS2, ratios 0.50-0.80, 100-250 C','~1e21','cm-3','measured','AC Hall','','','Results "Electrical" 3rd para')
V('','','carrier_density','holes; reference c-MoS2 350-450 C, ratio 0.20','1e17-1e18','cm-3','measured','AC Hall','','','Results "Electrical" 3rd para')
V('','','mobility','reference c-MoS2 350-450 C, ratio 0.20','~0.01','cm2/(V s)','measured','AC Hall','','','Results "Electrical" 3rd para')
V(gid('450','0.20'),'','carrier_density','link to grid cell inferred','1e17','cm-3','measured','AC Hall','','','Results "Electrical" 3rd para (450 C, 0.20 -> 0.80)')
V(gid('450','0.80'),'','carrier_density','link to grid cell inferred','1e20','cm-3','measured','AC Hall','','','Results "Electrical" 3rd para')
V('','','carrier_density','ratio 0.94','~1e22','cm-3','measured','AC Hall','','','Results "Electrical" 3rd para')
V('','','carrier_density','Mo thin films, literature','5e22-1e23','cm-3','literature','refs. 70, 71','','','Results "Electrical" 3rd para')
V('','','carrier_density','10 at.% Al-doped MoS2 at 450 C, literature (comparable)','~1e21','cm-3','literature','Vandalon et al. ref. 69','','','Results "Electrical" 3rd para')
V('','','conduction_type (new)','low-T c-MoS2','p-type','','measured','Hall','','','Results "Electrical" 3rd para; Conclusions')
V('','','anneal_stability (new)','electrical properties after annealing','no major change up to 300 C','','measured','four-point probe/Hall (Sec. S12, not in document)','','','Results "Electrical" 5th para')
V('','','oxidation_onset_temperature (new)','100 C films annealed in air','150','°C','measured','not stated (Secs. S11-S12)','','','FET para 2')
V('','','crystallinity_threshold (new)','minimum H2 flow ratio for c-MoS2 at 150 C','0.65','1','measured','Raman','','','Results "Concept" 2nd para')
V('','','crystallinity_threshold (new)','minimum H2 flow ratio for c-MoS2 at 100 C','0.80','1','measured','Raman','','','Results "Concept" 5th para')
V('','','crystallinity_threshold (new)','minimum H2 flow ratio for c-MoS2 at >=300 C','0.20','1','measured','Raman','','','Results "Concept" 5th para')
V(f'{K}:u1b_10c','','crystallinity','MoS2 Raman modes visible','crystalline','','measured','Raman','','','Results "Concept" 3rd para')
# WS2/TiS2
V(f'{K}:uWS_R000','','atomic_ratio (new)','S/W; XPS','4.0','1','measured','XPS','','','Results "Other TMDCs" 2nd para')
V(f'{K}:uWS_R000','','crystallinity','','amorphous','','measured','Raman','','','Results "Other TMDCs" 2nd para; Fig. 9a')
V(f'{K}:uWS_R000','','resistivity','qualitative','highly resistive','','measured','four-point probe','','','Results "Other TMDCs" 2nd para')
V(f'{K}:uWS_R080','','atomic_ratio (new)','S/W; XPS','2.1','1','measured','XPS','','','Results "Other TMDCs" 2nd para (Conclusions print WS2.2)')
V(f'{K}:uWS_R080','','crystallinity','','crystalline','','measured','Raman','','','Fig. 9a')
V(f'{K}:uWS_R080','','resistivity','','4','Ω cm','measured','four-point probe','','','Results "Other TMDCs" 2nd para')
V(f'{K}:uTiS_R050','','crystallinity','improved over thermal process','crystalline','','measured','Raman','','','Results "Other TMDCs" 3rd para; Fig. 9b')
V(f'{K}:uTiS_R050','','atomic_ratio (new)','S/Ti; Conclusions (Table S7 not in document)','2.2','1','measured','not stated','','','Conclusions')
V(f'{K}:uTiS_R080','','atomic_ratio (new)','S/Ti qualitative','S-poor','','measured','not stated','','','Results "Other TMDCs" 3rd para')
V('','','crystallinity_threshold (new)','lowest T for crystalline WS2 in prior process (ratio 0)','300','°C','literature','refs. 52, 67, 79','','','Results "Other TMDCs" 2nd para')
V('','','crystallinity_threshold (new)','lowest T for crystalline TiS2 in prior PEALD (ratio 0); amorphous TiS3 at 100 C','150','°C','literature','ref. 53','','','Results "Other TMDCs" 3rd para')
V(f'{K}:uHplasma','','crystallinity','extra H2 plasma step','crystalline (c-MoS2)','','measured','Raman/XPS (Table S8)','','','Results "Role of hydrogen" 3rd para')
V(f'{K}:uHgas','','crystallinity','extra H2 gas step: no change vs a-MoS3.4','amorphous','','measured','Raman/XPS (Table S8)','','','Results "Role of hydrogen" 3rd para')
V(f'{K}:uLowH2S_T250','','crystallinity','','crystalline','','measured','Raman (Fig. S22a)','','','Results "Role of hydrogen" last para')
V(f'{K}:uLowH2S_T150','','crystallinity','H2 needed at 150 C','amorphous','','measured','Raman (Fig. S22b)','','','Results "Role of hydrogen" last para')
V('','','h2_flow_ratio_upper_bound (new)','too high: metallic Mo forms','0.94','1','measured','XPS','','','Results "Concept" 5th para; "Film Composition" 2nd para')
V('','','film_thickness','intended per temperature at ratio 0.20 (cycle choice)','~10','nm','assumed','design target','','','Exp. Film Deposition 6th para')
V('','','film_thickness','typical films used for H2-ratio study','10-20','nm','measured','SE','','','Results "Concept" 3rd para')

# ---------------- links
for (r,T) in cryst:
    sid=gid(T,r)
    for f,k in [('2','map'),('4','map'),('7','map'),('8','map')]:
        L(sid,f,'b' if f=='7' else '',k,'stated','grid cell at this T and ratio')
for r in ['0','0.20','0.50','0.65','0.80','0.94']:
    sid=gid('150',r)
    L(sid,'1','a','spectrum','inferred','caption gives 150 C/140 cycles and ratio; same run as grid cell inferred')
    L(sid,'6','a','image','inferred','caption 150 C/140 cycles, ratio label; same run inferred')
    L(sid,'7','a','plot','inferred','in situ SE curve at 150 C for this ratio')
    if r!='0': L(sid,'5','a;b','spectrum','inferred','caption 150 C/140 cycles, ratio label')
for c in ['10','20','30','50']: L(f'{K}:u1b_{c}c','1','b','spectrum','stated','legend names the cycle count')
L(f'{K}:u1b_sub','1','b','spectrum','stated','legend SiO2/Si')
L(f'{K}:W1','1','c','map','stated','caption')
L(f'{K}:PET','1','d','image','stated','caption')
L(f'{K}:F100','3','a','image','stated','caption')
L(f'{K}:F350','3','b','image','stated','caption')
L(f'{K}:uT150R065_500c','6','b','image','stated','caption')
for r in ['0.20','0.65','0.80']: L(f'{K}:uRBS{r2s(r)}','Table 1','','table','stated','row')
L('*','Table 2','','table','stated','gas flows per ratio, all MoS2 depositions')
L(f'{K}:uWS_R000','9','a','spectrum','stated','legend'); L(f'{K}:uWS_R080','9','a','spectrum','stated','legend')
L(f'{K}:uTiS_R000','9','b','spectrum','stated','legend'); L(f'{K}:uTiS_R050','9','b','spectrum','stated','legend'); L(f'{K}:uTiS_thermal','9','b','spectrum','stated','legend')

def W(name,hdr,rows):
    with open(os.path.join(OUT,name),'w',newline='',encoding='utf-8') as f:
        w=csv.writer(f); w.writerow(hdr); w.writerows(rows)
W('paper.csv',['paper_id','year','topic'],[[P,'2022','PEALD of polycrystalline MoS2, WS2, TiS2 at 50-450 C; H2 fraction in H2S/H2/Ar plasma controls S content, crystallinity, GPC, morphology, resistivity (planar films; outside conformality)']])
W('sample.csv',['sample_id','paper_id','label_as_printed','parent_sample','material','precursor','coreactant','process_mode','reactor','structure_class','structure_dims','width_kind','temperature_C','cycles','evidence'],samples)
W('condition.csv',['sample_id','quantity','step','value','unit','data_kind','evidence'],conds)
W('series.csv',['series_id','sample_ids','figure','panel','method','x_id','x_by','y_id','y_reference','data_kind','points_status','points','reused_from','evidence'],series)
W('value.csv',['value_id','sample_id','from_series','quantity','qualifiers','value','unit','data_kind','method','relation','regime','evidence'],values)
W('link.csv',['sample_id','figure','panel','kind','stated_or_inferred','evidence'],links)
print(len(samples),len(conds),len(series),len(values),len(links))
