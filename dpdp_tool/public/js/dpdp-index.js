/* ─────────────────────────────────────────
   DPDP Navigator — Index Page JS
   Tech4Dev · dpdp.projecttech4dev.org
   File: public/js/dpdp-index.js
   Requires: Chart.js (CDN), frappe-web.min.js
─────────────────────────────────────────── */
'use strict';
const FU = '';
const DL=['Data Collection & Consent','Data Storage & Security','Data Usage & Sharing','Rights of Individuals','Governance & Processes'];
const DS=['Consent','Storage','Usage','Rights','Governance'];
const DK=['avg_consent','avg_storage','avg_usage','avg_rights','avg_governance'];
let CI={};

function getCsrfToken() {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : 'fetch';
}

let _chart=null;
let _sectionBands=null;

// ── SECTION BAND HELPER ───────────────────────────────────────────────
// Reads section_bands from cached config (same sessionStorage key as assess page).
// Falls back to hardcoded values only if config is unavailable.
function getSectionBand(pct){
  if(!_sectionBands){
    try{
      const cfg=JSON.parse(sessionStorage.getItem('dpdp_cfg_v1')||'{}');
      _sectionBands=cfg?.scoring?.section_bands||null;
    }catch(e){_sectionBands=null;}
  }
  const bands=_sectionBands||[
    {min_pct:70,label:'Strong',      color:'green'},
    {min_pct:40,label:'Developing',  color:'amber'},
    {min_pct:0, label:'Priority gap',color:'red'}
  ];
  return bands.find(b=>pct>=b.min_pct)||bands[bands.length-1];
}

// Read score colours from CSS variables so chart stays in sync with the stylesheet.
// getComputedStyle only works in a browser context; the fallbacks are never
// reached in production but guard against any server-side rendering edge cases.
const _cssVar = (name) =>
  (typeof getComputedStyle !== 'undefined'
    ? getComputedStyle(document.documentElement).getPropertyValue(name).trim()
    : '') || null;

function bandColor(pct){
  const c=getSectionBand(pct).color;
  if(c==='green')  return _cssVar('--score-high') || '#16A34A';
  if(c==='amber')  return _cssVar('--score-mid')  || '#D97706';
  return               _cssVar('--score-low')  || '#B91C1C';
}

function pipClass(pct){
  const c=getSectionBand(pct).color;
  return c==='green'?'pg':c==='amber'?'pa':'pr';
}

// ── LOAD DASHBOARD ────────────────────────────────────────────────────
async function loadDB(){
  try{
    const r=await fetch(`${FU}/api/method/dpdp_tool.api.get_sector_insights`,{headers:{'Accept':'application/json'}});
    const j=await r.json();const d=j.message||[];
    document.getElementById('db-loading').remove();
    if(!d.length){showEmpty();return;}

    // Separate aggregate (All Sectors) from real sectors
    const agg=d.find(s=>s.sector==='All Sectors')||d[0];
    const sectors=d.filter(s=>s.sector!=='All Sectors');

    mkStatCards(agg,sectors.length);
    mkDomainCards(agg);
    mkTabs(sectors);
    if(sectors.length) mkChart(sectors[0]);
  }
  catch(e){
    document.getElementById('db-loading').remove();
    document.getElementById('dpanels').innerHTML='<div class="db-empty">Sector insights could not be loaded. Please try refreshing the page.</div>';
  }
}

function showEmpty(){
  document.getElementById('stat-cards').innerHTML='';
  document.getElementById('domain-cards').innerHTML='';
  document.getElementById('dpanels').innerHTML='<div class="db-empty"><b style="display:block;margin-bottom:.5rem;color:var(--ink)">Sector insights building</b>Aggregated data appears once organisations complete the assessment. <a href="/assess" style="color:var(--teal)">Be among the first →</a></div>';
}

// ── ROW 1: stat cards ─────────────────────────────────────────────────
function mkStatCards(agg,sectorCount){
  const tot=agg?.total_submissions||0;
  const avg=Math.round(agg?.avg_overall||0);
  const el=document.getElementById('stat-cards');
  if(!el)return;
  el.innerHTML=`
    <div class="stat-card">
      <div class="stat-card-label">Org assessments</div>
      <div class="stat-card-val">${tot}</div>
      <div class="stat-card-sub">Organisations completed</div>
    </div>
    <div class="stat-card">
      <div class="stat-card-label">Sectors spanned</div>
      <div class="stat-card-val">${sectorCount}</div>
      <div class="stat-card-sub">Active sector groups</div>
    </div>
    <div class="stat-card">
      <div class="stat-card-label">Avg. readiness score</div>
      <div class="stat-card-val">${avg}<span class="stat-card-denom">/50</span></div>
      <div class="stat-card-sub">Across all sectors</div>
    </div>`;
}

// ── ROW 2: domain cards (fixed, always all-sectors aggregate) ─────────
function mkDomainCards(agg){
  const el=document.getElementById('domain-cards');
  if(!el)return;
  el.innerHTML=DK.map((k,i)=>{
    const rawVal=agg?.[k]||0;
    const raw=Math.round(rawVal);
    const pct=Math.round((rawVal/10)*100);
    const sb=getSectionBand(pct);
    const fillCls=sb.color==='green'?'bg-high':sb.color==='amber'?'bg-mid':'bg-low';
    const scoreCls=sb.color==='green'?'score-high':sb.color==='amber'?'score-mid':'score-low';
    return `<div class="domain-card">
      <div class="domain-card-label">${DL[i]}</div>
      <div class="domain-card-score ${scoreCls}">${raw}<span class="domain-card-denom">/10</span></div>
      <div class="domain-card-bar"><div class="domain-card-fill ${fillCls}" style="width:${pct}%"></div></div>
      <div class="pip-row"><div class="pip ${fillCls}"></div><div class="pip-label">${sb.label}</div></div>
    </div>`;
  }).join('');
}

// ── ROW 3: sector tabs + chart ────────────────────────────────────────
function mkTabs(sectors){
  const el=document.getElementById('stabs');if(!el)return;
  el.innerHTML='';
  sectors.forEach((s,i)=>{
    const t=document.createElement('button');
    t.className='stab'+(i===0?' on':'');
    t.textContent=s.sector;
    t.onclick=()=>{
      document.querySelectorAll('.stab').forEach((b,j)=>b.classList.toggle('on',j===i));
      mkChart(s);
    };
    el.appendChild(t);
  });
}

function mkChart(s){
  const rawVals=DK.map(k=>s[k]||0);
  const sc=rawVals.map(v=>Math.round(v));
  const colors=rawVals.map(v=>bandColor(Math.round((v/10)*100)));
  const titleEl=document.getElementById('chart-title');
  if(titleEl)titleEl.textContent='Domain scores — '+s.sector;
  const ctx=document.getElementById('ch-main');if(!ctx)return;
  if(_chart){
    _chart.data.datasets[0].data=sc;
    _chart.data.datasets[0].backgroundColor=colors;
    _chart.update('active');
    return;
  }
  _chart=new Chart(ctx,{
    type:'bar',
    data:{labels:DS,datasets:[{data:sc,backgroundColor:colors,borderRadius:4,borderSkipped:false,barPercentage:.55}]},
    options:{
      responsive:true,maintainAspectRatio:false,
      animation:{duration:300},
      plugins:{legend:{display:false},tooltip:{callbacks:{label:v=>` ${v.raw}/10`}}},
      scales:{
        y:{min:0,max:10,ticks:{stepSize:2,callback:v=>v+'/10',font:{size:11}},grid:{color:'rgba(0,0,0,.05)'},border:{display:false}},
        x:{ticks:{font:{size:11}},grid:{display:false},border:{display:false}}
      }
    }
  });
}

async function submitConsult(){
  const org=document.getElementById('cf-org').value.trim();
  const name=document.getElementById('cf-name').value.trim();
  const email=document.getElementById('cf-email').value.trim();
  if(!org||!name||!email){alert('Please fill in organisation name, your name, and email.');return;}
  const btn=document.querySelector('.fsub');btn.textContent='Submitting…';btn.disabled=true;
  try{
    const sectors=Array.from(document.querySelectorAll('#cf-sectors input:checked')).map(cb=>cb.value);
    const cp=new URLSearchParams({org_name:org,contact_name:name,email,sector:JSON.stringify(sectors),org_size:document.getElementById('cf-size').value,service_interest:document.getElementById('cf-svc').value,message:document.getElementById('cf-msg').value});
    const cr=await fetch(`${FU}/api/method/dpdp_tool.api.submit_consult_request?${cp}`);
    const cj=await cr.json();console.log('Consult result:',cj.message);
  }catch(e){console.error('submitConsult failed:',e);}
  document.getElementById('cf-inner').style.display='none';
  document.getElementById('cf-success').style.display='block';
}

async function loadConsultSectors(){
  try{
    let cfg;
    const cached=sessionStorage.getItem('dpdp_cfg_v1');
    if(cached){cfg=JSON.parse(cached);}
    else{
      const r=await fetch('/assets/dpdp_tool/dpdp-config.json');
      cfg=await r.json();
      sessionStorage.setItem('dpdp_cfg_v1',JSON.stringify(cfg));
    }
    const el=document.getElementById('cf-sectors');
    if(el&&cfg.sectors){el.innerHTML=cfg.sectors.map(s=>`<label class="sector-cb"><input type="checkbox" value="${s}"> ${s}</label>`).join('');}
  }catch(e){console.error('[loadConsultSectors] failed:',e);}
}

loadDB();
loadConsultSectors();

// ── Mobile nav ────────────────────────────────────────────────────
function toggleMenu(){
  const h=document.getElementById('hamburger');
  const d=document.getElementById('nav-drawer');
  h.classList.toggle('open');
  d.classList.toggle('open');
  document.body.style.overflow=d.classList.contains('open')?'hidden':'';
}
function closeMenu(){
  document.getElementById('hamburger').classList.remove('open');
  document.getElementById('nav-drawer').classList.remove('open');
  document.body.style.overflow='';
}
// Close drawer on outside click
document.addEventListener('click',function(e){
  const h=document.getElementById('hamburger');
  const d=document.getElementById('nav-drawer');
  if(d.classList.contains('open')&&!d.contains(e.target)&&!h.contains(e.target)){closeMenu();}
});
