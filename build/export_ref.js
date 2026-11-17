()=>{ const deg=p=>Math.atan(Math.max(0,+p||0)/100)*180/Math.PI, zone=p=>{ const d=deg(p); return d<13.5?0:(d<=18.9?1:(d<=24?2:3)); };
  const K=[['dist','d'],['off','o'],['ang','a'],['sd','dsd'],['comb','fig'],['pit','pitch']], ZK=['z0','z1','z2','z3'];
  const r3=v=> v==null||!isFinite(v)? null : Math.round(v*1000)/1000;
  const out={v:1, src:'race-venue-dossier/cs', gen:'M', updated:new Date().toISOString(),
    note:'Men race runs (all seasons, run 1 and 2). Values as shown on the course-setting page. Zones: gates by pitch at the gate: flat <13.5deg, medium 13.5-18.9, steep 18.9-24, very steep >24.', disc:{}};
  for(const D of ['SL','GS']){ const R=(__KS.all[D]||[]).filter(c=>c&&c.kind==='R'&&c.m);
    const runs=R.map(c=>{ const z=[0,0,0,0]; (c.gates||[]).forEach(g=>{ if(g&&g.p!=null&&isFinite(+g.p)) z[zone(g.p)]++; });
      const o={date:c.date, run:+c.run, tc:!!c.tc, venue:c.venue, season:c.season, n:(c.gates||[]).length, nreg:c.m.nreg};
      K.forEach(([k,s])=>{ o[k]=r3(c.m[s]); }); ZK.forEach((k,i)=>{ o[k]=z[i]; }); return o; })
      .sort((a,b)=> a.date<b.date?-1:a.date>b.date?1:a.run-b.run);
    const lab=r=>`${r.venue} ${String(r.date).slice(0,4)} · L${r.run}`;
    const ref={n:runs.length}; [...K.map(x=>x[0]),...ZK].forEach(k=>{ const pr=runs.filter(r=>r[k]!=null); if(!pr.length){ ref[k]=null; return; }
      let mi=pr[0], ma=pr[0]; pr.forEach(r=>{ if(r[k]<mi[k]) mi=r; if(r[k]>ma[k]) ma=r; });
      ref[k]={avg:r3(pr.reduce((a,r)=>a+r[k],0)/pr.length), min:mi[k], max:ma[k], n:pr.length, minL:lab(mi), maxL:lab(ma)}; });
    out.disc[D]={ref, runs}; }
  return out; }
