import sys
from PIL import Image
import numpy as np
f,y0,y1=sys.argv[1],int(sys.argv[2]),int(sys.argv[3])
im=np.asarray(Image.open(f).convert('RGB')).astype(int)[y0:y1]
H,W,_=im.shape
# coloured = not near-white and not gray
mx=im.max(2);mn=im.min(2)
col=((mx-mn)>40)|(mx<60)
# column profile
cp=col.sum(0); rp=col.sum(1)
def runs(p,th):
  r=[];s=None
  for i,v in enumerate(p):
    if v>th and s is None: s=i
    if v<=th and s is not None: r.append((s,i-1)); s=None
  if s is not None: r.append((s,len(p)-1))
  return r
print('cols',runs(cp,3))
print('rows',[(a+y0,b+y0) for a,b in runs(rp,3)])
