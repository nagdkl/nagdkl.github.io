import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11.17.2/dist/mermaid.esm.min.mjs';

const $ = (s) => document.querySelector(s);
const canvas = $('#canvas'), stage = $('#stage'), loading = $('#loading'), errorBox = $('#error');
const q = $('#q'), count = $('#count'), sourceDialog = $('#sourceDialog'), sourcePre = $('#source');
let svg=null, original=null, view=null, matches=[], matchIndex=-1, drag=null;

const statusError = (message) => {
  loading.hidden = true; errorBox.hidden = false; errorBox.replaceChildren();
  const p = document.createElement('p');
  p.textContent = `Не удалось отрисовать диаграмму: ${message}. `;
  const a = document.createElement('a'); a.href='diagram.mmd'; a.textContent='Открыть MMD source';
  p.append(a); errorBox.append(p);
};

async function fetchText(url, timeoutMs=10000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const r = await fetch(url, {cache:'no-store', signal:controller.signal});
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return await r.text();
  } finally { clearTimeout(timer); }
}
const setView=(n)=>{ if(!svg)return; view=n; svg.setAttribute('viewBox',`${view.x} ${view.y} ${view.w} ${view.h}`); };
const fit=()=>original&&setView({...original});
const zoom=(factor,cx=.5,cy=.5)=>{ if(!view)return; const nw=view.w*factor,nh=view.h*factor; setView({x:view.x+(view.w-nw)*cx,y:view.y+(view.h-nh)*cy,w:nw,h:nh}); };
const centerNode=(node)=>{ if(!svg||!node)return; const b=node.getBBox(), margin=3.6, aspect=Math.max(stage.clientWidth,1)/Math.max(stage.clientHeight,1); let w=Math.max(b.width*margin,260),h=Math.max(b.height*margin,140); if(w/h<aspect)w=h*aspect; else h=w/aspect; setView({x:b.x+b.width/2-w/2,y:b.y+b.height/2-h/2,w,h}); };
const clearSearchStyles=()=>svg&&svg.querySelectorAll('g.node').forEach(n=>n.classList.remove('search-dim','search-match'));
const runSearch=()=>{ if(!svg)return; const query=q.value.trim().toLocaleLowerCase('ru'), nodes=[...svg.querySelectorAll('g.node')]; clearSearchStyles(); if(!query){matches=[];matchIndex=-1;count.textContent='289 ролей';return;} matches=nodes.filter(n=>n.textContent.toLocaleLowerCase('ru').includes(query)); const selected=new Set(matches); nodes.forEach(n=>n.classList.add(selected.has(n)?'search-match':'search-dim')); matchIndex=matches.length?0:-1; count.textContent=`${matches.length} найдено`; if(matches.length)centerNode(matches[0]); };
const nextMatch=()=>{ if(!matches.length)return; matchIndex=(matchIndex+1)%matches.length; centerNode(matches[matchIndex]); count.textContent=`${matchIndex+1}/${matches.length}`; };

async function boot(){
  try{
    const source=await fetchText('diagram.mmd',10000); sourcePre.textContent=source;
    mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'base',flowchart:{htmlLabels:true,useMaxWidth:false},themeVariables:{fontFamily:'Inter, system-ui, sans-serif',primaryColor:'#edf6ff',primaryTextColor:'#102a43',primaryBorderColor:'#6aa8d8',lineColor:'#8096aa',clusterBkg:'#f7fbff',clusterBorder:'#aac6dc'}});
    const result=await Promise.race([mermaid.render('synergy289',source),new Promise((_,reject)=>setTimeout(()=>reject(new Error('render timeout 45s')),45000))]);
    canvas.innerHTML=result.svg; svg=canvas.querySelector('svg'); if(!svg)throw new Error('SVG отсутствует');
    const vb=svg.viewBox?.baseVal; if(!vb||!vb.width||!vb.height)throw new Error('viewBox отсутствует');
    original={x:vb.x,y:vb.y,w:vb.width,h:vb.height}; svg.removeAttribute('width');svg.removeAttribute('height');svg.setAttribute('preserveAspectRatio','xMidYMid meet');fit();loading.hidden=true;q.addEventListener('input',runSearch);
  }catch(error){statusError(error?.name==='AbortError'?'MMD fetch timeout 10s':(error?.message||String(error)));}
}
$('#fit').addEventListener('click',fit); $('#zoomIn').addEventListener('click',()=>zoom(.78)); $('#zoomOut').addEventListener('click',()=>zoom(1.28)); $('#next').addEventListener('click',nextMatch);
q.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();nextMatch();}});
$('#sourceBtn').addEventListener('click',()=>sourceDialog.showModal()); $('#closeSource').addEventListener('click',()=>sourceDialog.close());
stage.addEventListener('wheel',e=>{if(!view)return;e.preventDefault();const r=stage.getBoundingClientRect();zoom(e.deltaY<0?.84:1.19,(e.clientX-r.left)/r.width,(e.clientY-r.top)/r.height);},{passive:false});
stage.addEventListener('pointerdown',e=>{if(!view||e.button!==0)return;drag={x:e.clientX,y:e.clientY,v:{...view}};stage.setPointerCapture(e.pointerId);stage.classList.add('dragging');});
stage.addEventListener('pointermove',e=>{if(!drag||!view)return;const r=stage.getBoundingClientRect(),dx=(e.clientX-drag.x)*drag.v.w/r.width,dy=(e.clientY-drag.y)*drag.v.h/r.height;setView({x:drag.v.x-dx,y:drag.v.y-dy,w:drag.v.w,h:drag.v.h});});
const endDrag=e=>{if(!drag)return;drag=null;stage.classList.remove('dragging');try{stage.releasePointerCapture(e.pointerId)}catch{}};
stage.addEventListener('pointerup',endDrag);stage.addEventListener('pointercancel',endDrag);window.addEventListener('resize',()=>{if(original&&!q.value)fit();});
boot();