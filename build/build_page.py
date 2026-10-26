"""Builds _build/page.html (English men's SL/GS course-setting page) from the frozen base data set, the survey
PDFs added automatically from Dropbox (data/auto/) and the sync status (data/status.json).
Derived from build_all_html.py of the original workshop; the page itself is unchanged."""
import json, re, sys, os, glob, html, datetime
B=os.path.dirname(os.path.abspath(__file__)); ROOT=os.path.dirname(B); DATA=os.path.join(ROOT,'data')
PG=os.path.join(DATA,'page')   # page template, modules and English texts: in the encrypted data store (they name training venues and dates)
old=open(PG+'/template.html',encoding='utf-8').read().split('\n')
def L(a,b): return '\n'.join(old[a-1:b])
def js(name):
    t=open(PG+'/js/'+name,encoding='utf-8').read()
    return re.sub(r'/\*@OLD (\d+)-(\d+)@\*/',lambda m:L(int(m.group(1)),int(m.group(2))),t)
head=L(1,221)
head=head.replace('<title>Kurssetzungen 2025/26</title>','<title>Kurssetzungen Männer · Slalom</title>')
head=head.replace('<span>Kurssetzungs-Analyse</span>','<span>Kurssetzungen · Männer</span>')
a='<nav class="tabs"'; assert head.count(a)==1
head=head.replace(a,'<div class="seg disc" id="discSw" role="group" aria-label="Disziplin"></div>\n    '+a)
css_add='''.minis3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px 24px}
@media (max-width:1000px){.minis3{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:640px){.minis3{grid-template-columns:minmax(0,1fr)}}
.minis4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px 22px}
@media (max-width:1100px){.minis4{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:560px){.minis4{grid-template-columns:minmax(0,1fr)}}
.grid2{align-items:stretch}
.grid2>.card.shut{align-self:start}
.card.fold{display:flex;flex-direction:column}
.chart.fill{flex:1 1 auto;min-height:var(--minh,400px)}
.tw.grow{flex:1 1 auto;max-height:none;min-height:0}
.kpi .rows{display:grid;grid-template-columns:max-content 1fr;gap:5px 8px;align-items:baseline}
.kpi .row{display:contents}
.kpi .row .tag{justify-self:stretch}
.kpi .v{font-variant-numeric:tabular-nums}
.tbl.gl td,.tbl.gl th{padding-inline:7px}
.tbl.gl td.bar{min-width:56px}
.tbl.gl .st{font-size:11px;color:var(--muted)}
.tbl.gl .st.ok{color:var(--txt2)}
.tbl.gl tr.nc .pill{border-style:dashed;color:var(--muted);background:transparent}
.ch>.ctl{max-width:100%;min-width:0}
.btn.reset{align-self:flex-end;height:34px;margin-left:auto}
.btn.reset+.count{margin-left:0}
@media (max-width:760px){.bar-meta .season{display:none}}
/* tables adapt to the width of their own card, not of the window */
.tw.cq{container-type:inline-size}
@container (max-width:620px){.cq .tbl.gl .w-hide{display:none}}
@container (max-width:720px){
  .cq .tbl.cmpt .strip{display:none}.cq .tbl.cmpt td.l{white-space:normal}
}
@container (max-width:520px){
  .cq .tbl.gl .xs-hide{display:none}.cq .tbl.cmpt td,.cq .tbl.cmpt th{padding:6px 4px}
  .cq .tbl.cmpt th{white-space:normal;font-size:10px;letter-spacing:0;line-height:1.15;vertical-align:bottom}
  .cq .tbl.cmpt th .gd{display:block;width:8px;height:8px;margin:0 0 3px auto}
  .cq .tbl.cmpt td{font-size:12px}.cq .tbl.cmpt td.strong{font-size:12.5px}
  .cq .tbl.cmpt td:not(.l),.cq .tbl.cmpt th:not(.l){width:1%}
  .cq .tbl.cmpt td.l{white-space:normal;hyphens:auto;overflow-wrap:break-word;padding-left:10px}.cq .tbl.cmpt th.l{padding-left:10px}
}
@container (max-width:400px){
  .cq .tbl.gl{font-size:11.5px}.cq .tbl.gl td,.cq .tbl.gl th{padding-inline:4px}.cq .tbl.gl th{font-size:10px;letter-spacing:0}.cq .tbl.gl td.bar{min-width:38px}.cq .tbl.gl .gd{margin-right:4px}.cq .tbl.gl .pill{font-size:10px;padding:1px 6px}
}
@container (max-width:320px){.cq .tbl.gl td,.cq .tbl.gl th{padding-inline:3px}.cq .tbl.gl td.bar{min-width:33px}.cq .tbl.gl .pill{padding:1px 4px}.cq .tbl.gl .gd{margin-right:3px;width:7px;height:7px}}
@media (max-width:520px){.tabs{justify-content:space-between;gap:0}.tab{font-size:11.5px;padding:0 4px}.tab svg{display:none}}
@media print{
  .bar,.card.filters,.icon-btn,.btn,.tip{display:none!important}
  body{background:#fff}.page{padding:0;max-width:none}
  .card,.kpi{box-shadow:none;border:1px solid #d9dee5;break-inside:avoid}
  .card.shut{display:none}.fold-b svg{display:none}
  .tw.tall,.scrolly,.tw.grow{max-height:none!important;overflow:visible!important;flex-basis:auto!important}
  .grid2{grid-template-columns:minmax(0,1fr)}
}
.tbl.cmpt td,.tbl.cmpt th{padding:8px 12px}
.tbl.cmpt td.strong{font-weight:760;font-size:13.5px}
.tbl.cmpt .strip{width:38%;min-width:200px;padding-block:3px}
.tbl.cmpt th .gd{margin-right:6px}
.tbl.cmpt tbody tr:hover td{background-color:transparent}
.fold-b{all:unset;cursor:pointer;display:inline-flex;align-items:center;gap:8px;max-width:100%}
.fold-b svg{width:15px;height:15px;color:var(--muted);flex:none;transition:transform .15s}
.fold-b h2{font-size:15.5px;text-wrap:balance}
.fold-b:hover svg{color:var(--ink)}
.fold-b:focus-visible{outline:2px solid var(--red);outline-offset:4px;border-radius:4px}
.card.shut{padding-block:13px}
.card.shut .ch{margin-bottom:0}
.card.shut .fold-b svg{transform:rotate(-90deg)}
.card.shut .fold-b h2{color:var(--ink-2)}
.scrolly{max-height:580px;overflow-y:auto;overscroll-behavior:contain;margin-right:-6px;padding-right:6px}
.tbl.dense th,.tbl.dense td{padding:7px 10px}
.tbl tr.sum td{font-weight:700;background:var(--surface-2)}
.ch p{max-width:78ch}
.seg.disc{align-self:center;height:36px;margin:0 6px 0 10px;flex:none}
.seg.disc button{font-size:13px;padding:0 16px}
@media (max-width:760px){.seg.disc{margin:0 0 0 auto;order:2}.bar-meta{order:3;margin-left:6px}.bar-meta .season{display:none}}
@media (max-width:400px){.seg.disc button{padding:0 10px;font-size:12px}.brand span{display:none}}
@media (prefers-reduced-motion:reduce){.fold-b svg{transition:none}}
:root{--ca:#3a4350}
:root[data-ks="dark"]{--ca:#e6ebf2}
'''
assert '\n</style>' in head
head=head.replace('\n</style>','\n'+css_add+'</style>',1)
page=head+'\n'+js('js_a.js')+'\n/* ---------- helpers ---------- */\n'+L(263,296)+'\n'+js('js_b.js')+'\n'+L(378,567)+'\n'+js('js_c.js')+js('js_d.js')+js('js_e.js')+'</script>\n'
a="else if(k==='class')e.className=attrs[k];"; assert a in page; page=page.replace(a,"else if(k==='class'){if(attrs[k])e.className=attrs[k]}")
a="if(s.pts.length>1)sv('path',{d:dd"; assert a in page; page=page.replace(a,"if(s.pts.length>1&&s.line!==false)sv('path',{d:dd")
# ---- scatter: mean labels outside the plot, point labels placed where they cover no dot
def rep(page,a,b):
    assert a in page,a[:60]; return page.replace(a,b)
page=rep(page,"function chartBox(draw){var box=el('div',{class:'chart'});charts.push({el:box,draw:draw});return box}","function chartBox(draw,fill){var box=el('div',{class:'chart'+(fill?' fill':''),style:fill>1?'--minh:'+fill+'px':null});charts.push({el:box,draw:draw,fill:!!fill});return box}")
page=rep(page,"function drawAll(){charts.forEach(function(c){var w=c.el.clientWidth;if(w>40){c.el.replaceChildren();c.draw(c.el,w)}})}","""function drawAll(){
  // charts marked «fill» are drawn last, at the height their card got from its neighbour in the row
  charts.forEach(function(c){if(c.fill){c.el.replaceChildren();return}var w=c.el.clientWidth;if(w>40){c.el.replaceChildren();c.draw(c.el,w)}});
  charts.forEach(function(c){if(!c.fill)return;var w=c.el.clientWidth,h=c.el.clientHeight;if(w>40)c.draw(c.el,w,h)});
  // name every chart for screen readers: card title plus panel title
  charts.forEach(function(c){var s=c.el.querySelector('svg');if(!s)return;var card=c.el.closest('.card'),h2=card&&card.querySelector('h2'),pn=c.el.closest('.panel'),pt=pn&&pn.querySelector('.ptitle'),row=c.el.closest('tr');
    var name=[h2&&h2.textContent,pt?pt.textContent:(row&&row.cells[0]?row.cells[0].textContent:null)].filter(Boolean).join(': ');if(name)s.setAttribute('aria-label',name)});
}""")
page=rep(page,"var h=o.h||336,m={l:46,r:18,t:24,b:40}","var h=o.h||336,m={l:46,r:58,t:30,b:40}")
page=rep(page,"sv('text',{x:x1-2,y:Y(my)-5,'text-anchor':'end'},svg,'Ø '+fmt(my,o.yDec));","sv('text',{x:x1+7,y:Y(my)+3.5,class:'axt'},svg,'Ø '+fmt(my,o.yDec));")
page=rep(page,"sv('text',{x:X(mx)+5,y:y1+10},svg,'Ø '+fmt(mx,o.xDec));","sv('text',{x:X(mx),y:y1-8,'text-anchor':'middle',class:'axt'},svg,'Ø '+fmt(mx,o.xDec));")
page=rep(page,"sv('text',{x:0,y:y1-6,class:'axt'},svg,o.yLabel);","sv('text',{x:0,y:y1-20,class:'axt'},svg,o.yLabel);")
old_lab="""  lab.forEach(function(p){
    var right=X(p.x)<x0+(x1-x0)*.72;
    sv('text',{x:X(p.x)+(right?9:-9),y:Y(p.y)+4,'text-anchor':right?'start':'end',class:'lbl'},svg,p.label);
  });"""
new_lab="""  var boxes=[],lg=sv('g',null,svg);
  lab.forEach(function(p){
    var px=X(p.x),py=Y(p.y),tw=p.label.length*6.3+6,th=13,best=null;
    // candidate anchors around the dot, near ring first, then a wider ring with a leader line
    [9,24,40].forEach(function(r,ri){
      [[1,0],[-1,0],[0,-1],[0,1],[.75,-.75],[-.75,-.75],[.75,.75],[-.75,.75]].forEach(function(d,di){
        var ax=px+d[0]*r,ay=py+d[1]*r,bx0=d[0]>0.1?ax:d[0]<-0.1?ax-tw:ax-tw/2,by0=d[1]<-0.1?ay-th:d[1]>0.1?ay:ay-th/2,bx1=bx0+tw,by1=by0+th,cost=ri*4+di*.5;
        if(bx0<x0+2||bx1>x1-2||by0<y1+1||by1>y0-2)cost+=1000;
        P.forEach(function(q){var qx=X(q.x),qy=Y(q.y);if(q!==p&&qx>bx0-7&&qx<bx1+7&&qy>by0-7&&qy<by1+7)cost+=100});
        boxes.forEach(function(b){if(bx0<b[2]+3&&bx1>b[0]-3&&by0<b[3]+2&&by1>b[1]-2)cost+=300});
        if(!best||cost<best.cost)best={cost:cost,x0:bx0,y0:by0,x1:bx1,y1:by1,ax:ax,ay:ay,far:ri>0};
      });
    });
    if(best.cost>=100)return;   // no free spot: better no label than one on top of a dot
    boxes.push([best.x0,best.y0,best.x1,best.y1]);
    if(best.far)sv('line',{x1:px,y1:py,x2:Math.max(best.x0,Math.min(best.x1,px)),y2:Math.max(best.y0,Math.min(best.y1,py)),stroke:'var(--txt2)','stroke-width':1},lg);
    sv('text',{x:best.x0+3,y:best.y0+th-3,class:'lbl'},lg,p.label);
  });"""
page=rep(page,old_lab,new_lab)
TY={'Open':0,'Delayed':1,'Hairpin':2,'V.Comb':3}
def num(v):
    v=round(v,2); return int(v) if v==int(v) else v
def pack(C):
    data=[]
    for c in C:
        G=[]
        for g in c['gates']:
            if c['src']=='M':
                row=[TY[g['t']],g['d'],g['o'],num(g['p']),num(g['a']),g['x'],g['y'],1 if g['c']=='r' else 0,g.get('w') or 0,g.get('cd') or 0,g['fl']]
            else:
                row=[TY[g['t']],g['d'],g['o'],num(g['p']),num(g['a']),0,0,2,0,0,g['fl']]
            while row and row[-1]==0: row.pop()
            G.append(row)
        f=c['fin']; fin=None
        if f: fin=[f['d'],num(f['p']),f.get('x',0),f.get('y',0),1 if f.get('pf') else 0]
        data.append({'f':c['file'],'dt':c['date'],'v':c['venue'],'nat':c['nat'],'ser':c['series'],'k':c['kind'],'se':c['season'],'tc':1 if c['tc'] else 0,'r':c['run'],
                     'lab':c['label'],'pi':c['piste'],'st':c['setter'],'src':c['src'],'fin':fin,'G':G,'rc':1 if c.get('recon') else 0})
    return data
def courses(d):
    C=json.load(open(DATA+'/base/courses_%s.json'%d.lower(),encoding='utf-8'))
    for f in sorted(glob.glob(DATA+'/auto/%s/*.json'%d)):
        C.append(json.load(open(f,encoding='utf-8')))
    C.sort(key=lambda c:(c['date'],c['kind'],c['venue'],c['run'],c['label'],c['file']))
    return C
COURSES={'SL':courses('SL'),'GS':courses('GS')}
data={'SL':pack(COURSES['SL']),'GS':pack(COURSES['GS'])}
meta={'SL':json.load(open(DATA+'/base/meta_sl.json')),'GS':json.load(open(DATA+'/base/meta_gs.json'))}
dj=json.dumps(data,ensure_ascii=False,separators=(',',':')); mj=json.dumps(meta,separators=(',',':'))
svg=open(ROOT+'/assets/logo.svg',encoding='utf-8').read()
vb=re.search(r'viewBox="([^"]+)"',svg).group(1)
paths=re.findall(r'<path\s+d="([^"]+)"\s+id="[^"]+"\s+style="fill:(#[0-9a-f]{6})',svg); assert len(paths)==11
def shorten(d): return re.sub(r'-?\d+\.\d+',lambda m:('%.2f'%float(m.group(0))).rstrip('0').rstrip('.'),d)
logo='<svg viewBox="%s" role="img" aria-label="Swiss-Ski">%s</svg>'%(vb,''.join('<path d="%s" fill="%s"/>'%(shorten(d),col) for d,col in paths))
assert '/*__DATA__*/null' in page and '/*__META__*/null' in page and '<!--__LOGO__-->' in page
ZONES={'SL':{'d':[4,4.5,5,5.5,6,8,9,9.5,10,10.5,11,11.5],'o':[0.5,1,1.7,2.4,3,3.4,4],'a':[15,25,35,40,45,50]},'GS':{'d':[22,24,25,26,27,28,30],'o':[2,4,6,7,8,9,10,12],'a':[15,25,30,35,40,45,50]}}
page=page.replace('/*__ZONES__*/null',json.dumps(ZONES,separators=(',',':')))
# seasons offered in the filters follow the data (a race of a new season added from Dropbox shows up there too)
for d,lit in (('SL',"seasons:['23/24','24/25','25/26']"),('GS',"seasons:['24/25','25/26']")):
    assert page.count(lit)==1,lit
    ss=sorted({c['season'] for c in COURSES[d]},key=lambda x:int(x[:2]))
    page=page.replace(lit,'seasons:'+json.dumps(ss).replace('"',"'").replace(', ',','))
    yl={'SL':"years:'2023/24–2025/26'",'GS':"years:'2024/25–2025/26'"}[d]; assert page.count(yl)==1,yl
    y=lambda x:'20%s/%s'%(x[:2],x[3:])
    page=page.replace(yl,"years:'%s–%s'"%(y(ss[0]),y(ss[-1])))
def status_html():
    """small status line at the end of the page: data basis, last Dropbox check, files waiting for review"""
    try: S_=json.load(open(DATA+'/status.json',encoding='utf-8'))
    except FileNotFoundError: S_={}
    n={d:len(C) for d,C in COURSES.items()}
    auto=sum(len(glob.glob(DATA+'/auto/%s/*.json'%d)) for d in ('SL','GS'))
    def ts(v):
        if not v: return None
        t=datetime.datetime.fromisoformat(v.replace('Z','+00:00'))
        return t.astimezone(datetime.timezone(datetime.timedelta(hours=1))).strftime('%d.%m.%Y %H:%M')
    parts=['Data: %d slalom and %d giant slalom courses'%(n['SL'],n['GS'])]
    if auto: parts.append('%d added automatically from survey PDFs'%auto)
    if ts(S_.get('checked')): parts.append('Dropbox checked %s'%ts(S_['checked']))
    pend=S_.get('pending',[])
    out='<style>.ks-status{max-width:1440px;margin:0 auto;padding:4px 24px 28px;font-size:11.5px;color:var(--muted);line-height:1.6}.ks-status details{margin-top:4px}.ks-status summary{cursor:pointer;color:var(--ink-2);font-weight:700}.ks-status ul{margin:4px 0 0;padding-left:18px}@media print{.ks-status{display:none}}</style>\n'
    out+='<footer class="ks-status">'+html.escape(' · '.join(parts))
    if pend:
        out+='<details><summary>%d new file%s in Dropbox under review (not yet in the analysis)</summary><ul>'%(len(pend),'' if len(pend)==1 else 's')
        out+=''.join('<li>%s</li>'%html.escape(p['path']) for p in pend)+'</ul></details>'
    return out+'</footer>\n'
def finish(page,dj,lang):
    page=page.replace('<!--__LOGO__-->',logo).replace('/*__DATA__*/null',dj).replace('/*__META__*/null',mj)
    full=('<!DOCTYPE html>\n<html lang="%s">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'%lang
          +page.replace('</style>\n\n<header','</style>\n</head>\n<body>\n<header',1)+'</body>\n</html>\n')
    assert '</head>\n<body>' in full
    return page,full
# ---- English
sys.path.insert(0,PG); import i18n_all_en as T
en=page
for a,b in T.RAW: assert a in en,a; en=en.replace(a,b)
for a,b in T.HEAD: assert a in en,a; en=en.replace(a,b)
i=en.index('<script>'); hd,body=en[:i],en[i:]
unused=[]
for de,e in sorted(T.EN.items(),key=lambda kv:-len(kv[0])):
    q="'"+de+"'"
    if q not in body: unused.append(de); continue
    body=body.replace(q,"'"+e.replace("'","\\'")+"'")
en=hd+body
den={}
for k,L in data.items():
    den[k]=[]
    for c in L:
        c=dict(c); c['lab']=T.DATA.get(c['lab'],c['lab']); c['pi']=T.DATA.get(c['pi'],c['pi']); den[k].append(c)
en_page,en_full=finish(en,json.dumps(den,ensure_ascii=False,separators=(',',':')),'en')
en_full=en_full.replace('</body>\n</html>\n',status_html()+'</body>\n</html>\n',1)
os.makedirs(ROOT+'/_build',exist_ok=True)
open(ROOT+'/_build/page.html','w',encoding='utf-8').write(en_full)   # plain page; published only encrypted (build/encrypt.py)
# leftovers: literals that still look German
lits=sorted(set(re.findall(r"'((?:[^'\\\n]|\\.)*)'",body)))
rx=re.compile(r"[äöüÄÖÜß]|\b(der|die|das|und|mit|von|für|nicht|Tor|Tore|Toren|Kurs|Kurse|Lauf|Läufe|Rennen|Abstand|Winkel|Neigung|Saison|Ort|Alle|kein|keine|pro|zum|im|als|aus|auf|Figur|Figuren|Teil|Datum|Quelle|Mittel|Auswahl|Klick|gewertet|Vergleich)\b")
left=[l for l in lits if rx.search(l) and not l.startswith('<')]
print('courses SL',len(COURSES['SL']),'GS',len(COURSES['GS']),'page',len(en_full))
if left: sys.exit('German text left on the English page: %r'%left)
