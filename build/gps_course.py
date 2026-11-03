"""GPS course-setting sheets -> course gates, taken over unchanged from the workshop (sl_build.py / gs_build.py):
merge points measured twice (< 2.5 m), rebuild angles > 90 deg from offset, replace implausible pitches by their
neighbours, convert angle and offset from slope to plan view (as in the surveyed race documents), infer figure types
from the distances (SL: delay / hairpin / vertical combination; GS: delay only)."""
import math, statistics as st, collections
RANGE = 0.20
log = collections.defaultdict(list)

def foff(h1,h2,a):
    r=math.radians(a); ch=math.sqrt(max(1e-9,h1*h1+h2*h2+2*h1*h2*math.cos(r))); return h1*h2*math.sin(r)/ch
def solve_a(h1,h2,o):
    lo,hi=0.0,90.0
    if foff(h1,h2,hi)<o: return None
    for _ in range(50):
        mid=(lo+hi)/2
        if foff(h1,h2,mid)<o: lo=mid
        else: hi=mid
    return (lo+hi)/2

def gps_course(rows, dec, name, infer_types):
    """rows: sheet lines [{d,a,o,p}] (p = pitch % in the MBCD sense, signed). Line i holds the distance of segment i and the
    turn (angle, offset) at the START of that segment, so the turn of gate k sits on line k+1. The last line is the end segment."""
    rows=[r for r in rows if r['d'] is not None]
    # points measured twice (segments under 2.5 m) are not gates: merge the segment into the following one
    out=[]; merged=0; i=0
    while i<len(rows):
        r=dict(rows[i])
        if r['d']<2.5 and i+1<len(rows):
            n=dict(rows[i+1]); tot=r['d']+n['d']
            n['p']=None if (r['p'] is None or n['p'] is None) else (r['p']*r['d']+n['p']*n['d'])/tot
            n['d']=round(tot,dec); n['a']=r['a']; n['o']=r['o']; n['mg']=1       # keep the turn of the first of the two points
            rows[i+1]=n; merged+=1; i+=1; continue
        out.append(r); i+=1
    rows=out
    if merged: log['merged'].append((name,merged))
    N=len(rows); gates=[]
    for k in range(N-1):
        r=rows[k]; nx=rows[k+1]; fl=0
        a=nx['a']; o=nx['o']
        if a is None: a=0.0; fl|=1
        if o is None: o=0.0; fl|=2
        if a>90:         # artefact of the sheet's angle formula (offset stays small): rebuild from offset and distances
            a2=solve_a(r['d'],nx['d'],o)
            log['angle>90'].append((name,k+1,a,o,None if a2 is None else round(a2,1)))
            a=round(a2,dec) if a2 is not None else 0.0; fl|=8
        gates.append({'n':k+1,'d':r['d'],'o':o,'a':a,'p':r['p'],'fl':fl})
    fin={'d':rows[-1]['d'],'p':rows[-1]['p']}
    # implausible pitch (GPS height glitch): take the mean of the valid neighbours
    segs=gates+[fin]; ok=[s['p'] is not None and 1.0<=s['p']<=75.0 for s in segs]
    for i,s in enumerate(segs):
        if ok[i]: continue
        nb=[segs[j]['p'] for j in list(range(i-1,-1,-1))[:6] if ok[j]][:1]+[segs[j]['p'] for j in range(i+1,min(len(segs),i+7)) if ok[j]][:1]
        log['pitch'].append((name,i+1,s['p']))
        s['p']=round(sum(nb)/len(nb),1) if nb else 0.0
        if 'fl' in s: s['fl']|=16
        else: s['pf']=1
    for s in segs: s['p']=round(s['p'],1)
    # The GPS sheet measures angle and offset in the slope (3D between the segments), the surveyed race documents in
    # plan view. Convert to plan view so both sources mean the same: exact for given distances, pitches and 3D angle.
    for k,g in enumerate(gates):
        nx=segs[k+1]; t1=math.asin(max(-.99,min(.99,g['p']/100))); t2=math.asin(max(-.99,min(.99,nx['p']/100)))
        a3=g['a']; o3=g['o']
        ch=(math.cos(math.radians(a3))-math.sin(t1)*math.sin(t2))/(math.cos(t1)*math.cos(t2))
        ap=math.degrees(math.acos(max(-1.0,min(1.0,ch))))
        f3=foff(g['d'],nx['d'],a3); fp=foff(g['d']*math.cos(t1),nx['d']*math.cos(t2),ap)
        g['a3']=a3; g['o3']=o3
        g['a']=round(ap,1); g['o']=round(o3*fp/f3,2) if f3>0.05 else round(fp,2)
    infer_types(gates)
    return gates,fin

def dmed(G):
    v=[g['d'] for g in G[1:]] or [g['d'] for g in G]
    med=st.median(v); lo,hi=med*(1-RANGE),med*(1+RANGE)
    w=[x for x in v if lo<=x<=hi]
    return st.median(w) if w else med

def infer_types_sl(G):
    """figure types from the distances alone (calibrated on the typed race courses)"""
    med=dmed(G); lo=med*(1-RANGE)
    for g in G: g['t']='Open'; g['fl']|=4
    i=1
    while i<len(G):
        if G[i]['d']<lo:
            j=i
            while j+1<len(G) and G[j+1]['d']<lo: j+=1
            L=j-i+1
            if L==1:
                if G[i]['d']/med<0.54: G[i]['t']='Delayed'
                else: G[i-1]['t']=G[i]['t']='Hairpin'
            else:
                for q in range(i-1,j+1): G[q]['t']='V.Comb'
            i=j+1
        else: i+=1

def infer_types_gs(G):
    """GS: a gate is a delay gate when its distance is clearly short (race documents: delay 10.0-15.6 m at median 24-28 m,
    shortest open gate 0.71 x median); everything else stays open (irregular open gates are excluded by the normal-gate rule)"""
    med=dmed(G)
    for i,g in enumerate(G):
        g['t']='Delayed' if (i>0 and g['d']<0.62*med) else 'Open'; g['fl']|=4
