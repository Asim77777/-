import numpy as np, subprocess, sys
from numpy.lib.stride_tricks import sliding_window_view as swv
f=sys.argv[1]
sr=22050
x=np.frombuffer(subprocess.run(["ffmpeg","-v","error","-i",f,"-ac","2","-ar",str(sr),"-f","f32le","-"],capture_output=True).stdout,np.float32).reshape(-1,2)
L,R=x[:,0],x[:,1]
hop=256; win=2048; fps=sr/hop
def spec(s):
    fr=swv(s,win)[::hop]; return np.abs(np.fft.rfft(fr*np.hanning(win),axis=1)).astype(np.float32)
M=spec((L+R)/2); Sd=spec((L-R)/2)
fq=np.fft.rfftfreq(win,1/sr)
lo,hi=np.searchsorted(fq,[180,3200])
C=np.clip(M[:,lo-12:hi+12]-1.2*Sd[:,lo-12:hi+12],0,None)
k=12
Hm=np.median(swv(np.pad(C,((k,k),(0,0)),mode='edge'),2*k+1,axis=0),axis=-1)
Pm=np.median(swv(np.pad(C,((0,0),(k,k)),mode='edge'),2*k+1,axis=1),axis=-1)
Hc=(C*Hm**2/(Hm**2+Pm**2+1e-9))[:,12:-12]
e=np.log1p(Hc.sum(1)*0.05)
e=np.convolve(e,np.ones(7)/7,'same')
np.save(sys.argv[2],np.stack([np.arange(len(e))/fps,e]))
