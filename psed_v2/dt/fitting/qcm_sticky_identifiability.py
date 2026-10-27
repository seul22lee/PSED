"""ADDED (A14): local identifiability (Fisher information) of the flat QCM model with the sticky-precursor term
of Yanguas-Gil, Libera, Elam, JVST A 39, 062404 (2021), Eqs. 21-22, written in site-conserving form (TMA half-cycle):
  dth/dt  = k1 p (1 - th - tha) - ka p th + kd tha        th:  reacted sites, nothing on top
  dtha/dt = ka p th - kd tha                              tha: reacted sites with a reversibly adsorbed TMA
  m = Mc (th + tha) + Ma tha + A_fast exp(-(t - t_d)/tau_fast)   (A_fast, tau_fast: empirical fast term after the dose)
p(t) = eta * shape(t): the QCM sees only k1*eta (c*eta) and ka*eta (beta_a0*eta), written k1, ka here.
Noise: 1 ng/cm2 per 1 s sample (QCM step ~2.1 ng/cm2). Truth: kd = 1/50 s, 14 ng/cm2 desorbs after a saturating
0.1 s dose. Regime R1: the reversible layer fills during the dose; R2: it stays far from full.
Designs: A = WALDO 7/02 as run; B-D = dose series at 1/10 source flow with 60 s or 180 s purges (+ full-source doses).
Relative standard errors of the log parameters and the worst pairwise correlation; written to
qcm_sticky_identifiability.json. No data needed. Not a model change: the D terms are not in reaction_model.py."""
import json, os
import numpy as np
from scipy.linalg import expm
names=['k1*eta','ka*eta','kd','Mc','Ma','A_fast','tau_fast']
def pulse(t,td,p0,tres=0.5):
    return np.where(t<td,p0,p0*np.exp(-(t-td)/tres))
def qcm(par,td,p0,tpurge,dt=0.01):
    k1,ka,kd,Mc,Ma,Af,tf=par
    t=np.arange(0,td+tpurge,dt); y=np.zeros(2); out=[]
    for ti in t:
        p=pulse(ti+dt/2,td,p0)
        # linear system y' = A y + b ; y=(th,tha)
        A=np.array([[-k1*p-ka*p, -k1*p+kd],[ka*p,-kd]]); b=np.array([k1*p,0.0])
        M=np.zeros((3,3)); M[:2,:2]=A; M[:2,2]=b; E=expm(M*dt)
        y=E[:2,:2]@y+E[:2,2]; out.append(y.copy())
    out=np.array(out); th,tha=out[:,0],out[:,1]; tt=t+dt
    m=Mc*(th+tha)+Ma*tha+np.where(tt>td,Af*np.exp(-(tt-td)/tf),0)
    keep=np.isclose((tt*100)%100,0)  # 1 Hz samples
    return m[keep]
def fisher(par,design,sig=1.0,free=None):
    free=free or list(range(len(par))); J=[]
    base=np.concatenate([qcm(par,*d) for d in design])
    for i in free:
        q=np.array(par,float); h=0.01; q[i]*=np.exp(h)
        J.append((np.concatenate([qcm(q,*d) for d in design])-base)/h)   # d m / d log(par)
    J=np.array(J).T; F=J.T@J/sig**2
    C=np.linalg.pinv(F); se=np.sqrt(np.diag(C)); R=C/np.outer(se,se)
    return se,R
RES={}
def report(label,par,design,free=None,sig=1.0):
    free=free or list(range(len(par)))
    se,R=fisher(par,design,sig,free)
    np.fill_diagonal(R,0)
    RES.setdefault(CUR[0],{})[label]=dict(rel_se={names[i]:float(se[j]) for j,i in enumerate(free)})
    s='  '.join(f'{names[i]} {100*se[j]:.0f}%' for j,i in enumerate(free))
    j,k=np.unravel_index(np.argmax(abs(R)),R.shape)
    print(f'{label}\n   rel. SE: {s}\n   worst corr {names[free[j]]}-{names[free[k]]} {R[j,k]:+.3f}')
    RES[CUR[0]][label]['worst_corr']=[names[free[j]],names[free[k]],float(R[j,k])]
# truth: 0.1 s dose saturates chemisorption; kd = 1/50 s; reversible part 14 ng/cm2 after the dose
regimes={'R1 reversible layer fills in the dose (ka*eta 10/s)':[50,10,1/50,65,14.5,3,1.0],
         'R2 reversible layer far from full (ka*eta 0.5/s)':[50,0.5,1/50,65,50,3,1.0]}
CUR=['']
for rname,par in regimes.items():
    CUR[0]=rname
    print('=====',rname)
    report('A  WALDO 7/02 as run: one 0.1 s dose, 60 s purge, one cycle',par,[(0.1,1.0,60)])
    report('A30 same, 30 identical cycles pooled',par,[(0.1,1.0,60)],sig=1/np.sqrt(30))
    report('A30 + Mc, Ma fixed (Ma from stoichiometry)',par,[(0.1,1.0,60)],free=[0,1,2,5,6],sig=1/np.sqrt(30))
    ser=[(td,0.1,60) for td in (0.1,0.2,0.4,0.8,1.6,3.2)]
    report('B  dose series at 1/10 source (6 doses), 60 s purges',par,ser)
    ser2=[(td,0.1,180) for td in (0.1,0.2,0.4,0.8,1.6,3.2)]
    report('C  dose series, 180 s purges',par,ser2)
    ser3=ser2+[(td,1.0,180) for td in (0.1,0.4,1.6)]
    report('D  C + 3 doses at full source',par,ser3)

json.dump(dict(truth={k:dict(zip(names,v)) for k,v in regimes.items()},results=RES),
          open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'qcm_sticky_identifiability.json'),'w'),indent=1)
