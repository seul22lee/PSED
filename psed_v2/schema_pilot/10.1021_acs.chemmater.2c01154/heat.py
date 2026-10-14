import sys, math
from PIL import Image
import numpy as np
F='/home/ftk3187/github/PSED/psed_v2/ingest/final/10.1021_acs.chemmater.2c01154/figures/'
def patch(im,x,y,r=4):
    return im[y-r:y+r+1,x-r:x+r+1].reshape(-1,3).mean(0)
def bar(im,x,ya,yb):
    return [(y,im[y,x-3:x+4].mean(0)) for y in range(ya,yb+1)]
def nearest(c,b):
    d=[(np.linalg.norm(c-v),y) for y,v in b]; d.sort(); return d[0]
cols=['0','0.20','0.35','0.50','0.65','0.80','0.94']
rows=['450','350','300','250','200','150','100','50']
grid={'0':['250','200','150'],'0.20':rows,'0.35':['250'],'0.50':['350','250','200','150','100'],'0.65':['250','200','150','100'],'0.80':['450','350','250','200','150','100','50'],'0.94':['250','200','150','100']}
which=sys.argv[1]
if which=='8':
    im=np.asarray(Image.open(F+'_page_6_Figure_5.jpeg').convert('RGB')).astype(float)
    cx=dict(zip(cols,[100,137,175,213,250,288,326])); ry=dict(zip(rows,[55,112,137,168,197,225,252,280]))
    b=bar(im,363,44,286)
    # ticks: 1e3 at 77, 1e-3 at 289 -> log10 = 3 - (y-77)/35.3
    for c in cols:
        for r in grid[c]:
            d,y=nearest(patch(im,cx[c],ry[r]),b)
            v=3-(y-77)/35.33
            print(c,r,y,round(d),'>dl' if y<62 else '%.2g'%(10**v))
else:
    im=np.asarray(Image.open(F+'_page_5_Figure_7.jpeg').convert('RGB')).astype(float)
    cx=dict(zip(cols,[103,143,183,223,263,303,343])); ry=dict(zip(rows,[433,493,522,552,581,611,641,671]))
    b=bar(im,386,424,680)
    for c in cols:
        for r in grid[c]:
            d,y=nearest(patch(im,cx[c],ry[r]),b)
            v=1.75-(y-422)*(1.25/(682-422))
            print(c,r,y,round(d),'%.2f'%v)
