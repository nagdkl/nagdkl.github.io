const $=(s)=>document.querySelector(s);
const $$=(s)=>[...document.querySelectorAll(s)];
let data=null;

function setAll(open){$$('.floor').forEach(d=>d.open=open);}
$('#openAll').addEventListener('click',()=>setAll(true));
$('#closeAll').addEventListener('click',()=>setAll(false));

function floorText(d){return d.textContent.toLocaleLowerCase('ru');}
$('#floorSearch').addEventListener('input',e=>{
  const q=e.target.value.trim().toLocaleLowerCase('ru');
  let visible=0;
  $$('.floor').forEach(d=>{
    const hit=!q||floorText(d).includes(q);
    d.hidden=!hit;
    if(hit){visible++; if(q)d.open=true;}
  });
  $('#floorStatus').textContent=`Этажей/модулей показано: ${visible} из 7`;
});

function indoorFor(p){
  const gs=p.floor_id?.startsWith('gs-');
  const base=gs?'Главный штаб Эрмитаж':'Государственный Эрмитаж';
  const target=p.room&&p.room!=='—'?`зал ${p.room}`:p.name;
  return `https://2gis.ru/spb/search/${encodeURIComponent(base+' '+target)}`;
}
function floorLabel(id){
  const f=data.floor_modules.find(x=>x.id===id);
  return f?`${f.building}, этаж ${f.floor}`:'Проверить текущий план';
}
function placeCard(p){
  const hot=p.group==='popular';
  return `<article class="place">
    <div class="place-head"><div class="score ${hot?'hot':'cool'}">${p.score}</div>
      <div><h3>${escapeHtml(p.name)}</h3><div class="meta">${escapeHtml(floorLabel(p.floor_id))}${p.room&&p.room!=='—'?` · зал ${escapeHtml(String(p.room))}`:''}</div></div>
    </div>
    <div class="tags"><span class="tag">${hot?'Популярные 50':'Спокойные 50'}</span><span class="tag">${escapeHtml(p.country)}</span><span class="tag">${escapeHtml(p.kind)}</span><span class="tag">${escapeHtml(p.block_hint)}</span></div>
    <div class="meta">Размещение: ${escapeHtml(p.placement_confidence)}. ${escapeHtml(p.desc)}</div>
    <div class="place-actions"><a href="#${escapeHtml(p.floor_id)}" data-open-floor="${escapeHtml(p.floor_id)}">Открыть этаж</a><a href="${indoorFor(p)}" target="_blank" rel="noopener noreferrer">2GIS ↗</a></div>
  </article>`;
}
function escapeHtml(v){return String(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}

function renderPlaces(){
  if(!data)return;
  const q=$('#placeSearch').value.trim().toLocaleLowerCase('ru');
  const group=$('#groupFilter').value;
  const floor=$('#placeFloor').value;
  const crowd=$('#crowdFilter').value;
  let a=data.places.filter(p=>{
    const blob=[p.name,p.country,p.period,p.style,p.kind,p.room,p.desc,p.block_hint].join(' ').toLocaleLowerCase('ru');
    if(q&&!blob.includes(q))return false;
    if(group&&p.group!==group)return false;
    if(floor&&p.floor_id!==floor)return false;
    if(crowd==='high'&&p.score<8)return false;
    if(crowd==='low'&&p.score>3)return false;
    return true;
  });
  a.sort((x,y)=>y.score-x.score||x.name.localeCompare(y.name,'ru'));
  $('#placeCards').innerHTML=a.map(placeCard).join('')||'<p>Ничего не найдено — ослабьте фильтры.</p>';
}
for(const id of ['placeSearch','groupFilter','placeFloor','crowdFilter']){
  $('#'+id).addEventListener(id==='placeSearch'?'input':'change',renderPlaces);
}
document.addEventListener('click',e=>{
  const a=e.target.closest('[data-open-floor]');
  if(!a)return;
  const d=document.getElementById(a.dataset.openFloor);
  if(d)d.open=true;
});

async function boot(){
  try{
    const r=await fetch('data/floors.v1.json',{cache:'no-store'});
    if(!r.ok)throw new Error(`HTTP ${r.status}`);
    data=await r.json();
    const sel=$('#placeFloor');
    data.floor_modules.forEach(f=>{
      const o=document.createElement('option');
      o.value=f.id;o.textContent=`${f.building} · этаж ${f.floor}`;sel.append(o);
    });
    renderPlaces();
  }catch(err){
    $('#placeCards').innerHTML='<p>Каталог 100 мест не загрузился. Поэтажные модули выше остаются полностью доступными.</p>';
  }
}
boot();
