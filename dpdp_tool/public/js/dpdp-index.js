/* ─────────────────────────────────────────
   DPDP Navigator — Index Page JS
   Tech4Dev · dpdp.projecttech4dev.org
   File: public/js/dpdp-index.js
   Requires: Chart.js (CDN), frappe-web.min.js
─────────────────────────────────────────── */
'use strict';
const FU = '';
const DL=['Data Collection & Consent','Data Storage & Security','Data Usage & Sharing','Rights of Individuals','Governance & Processes'];
const DK=['avg_consent','avg_storage','avg_usage','avg_rights','avg_governance'];
let CI={};

function getCsrfToken() {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : 'fetch';
}
async function loadDB(){
  try{
    const r=await fetch(`${FU}/api/method/dpdp_tool.api.get_sector_insights`,{headers:{'Accept':'application/json'}});
    const j=await r.json();const msg=j.message||{};const d=msg.sectors||[];
    document.getElementById('db-loading').remove();
    if(!d.length){showEmpty();return;}
    const tot=msg.total_submissions||0;
    document.getElementById('db-meta').innerHTML=`<strong>${tot}</strong> submissions across <strong>${d.length}</strong> sectors`;
    mkTabs(d);mkPanels(d);document.querySelector('.stab')?.click();
  }
  catch(e){
    document.getElementById('db-loading').remove();
    document.getElementById('dpanels').innerHTML = '<div class="db-empty">Sector insights could not be loaded. Please try refreshing the page.</div>';
    document.getElementById('db-meta').textContent = '';
  }
}

function showEmpty(){
  document.getElementById('dpanels').innerHTML='<div class="db-empty"><b style="display:block;margin-bottom:.5rem;color:var(--ink)">Sector insights building</b>Aggregated data appears once organisations complete the assessment. <a href="/assess" style="color:var(--teal)">Be among the first →</a></div>';
  document.getElementById('db-meta').textContent='0 submissions so far';
}

function mkTabs(data){
  const el=document.getElementById('stabs');el.innerHTML='';
  data.forEach((s,i)=>{const t=document.createElement('button');t.className='stab'+(i===0?' on':'');t.textContent=s.sector;t.onclick=()=>swTab(i,data);el.appendChild(t);});
}

function swTab(i,data){
  document.querySelectorAll('.stab').forEach((t,j)=>t.classList.toggle('on',i===j));
  document.querySelectorAll('.dpanel').forEach((p,j)=>p.classList.toggle('on',i===j));
  mkChart(i,data[i]);
}

function mkPanels(data){
  const c=document.getElementById('dpanels');c.innerHTML='';
  data.forEach((s,i)=>{
    const sc=DK.map(k=>Math.round(s[k]||0));
    const avg=Math.round(s.avg_overall||0); /* overall out of 50 */
    const p=document.createElement('div');
    p.className='dpanel'+(i===0?' on':'');
    p.innerHTML=`<div class="cbox"><div class="cbox-t">Domain scores — ${s.sector}</div><canvas id="ch-${i}" height="220"></canvas></div>
      <div class="scol">
        <div class="sbox"><div class="sbox-lbl">Overall avg. readiness</div><div class="sbox-val">${avg}/50</div><div class="sbox-sub">${s.submission_count} submission${s.submission_count!==1?'s':''}</div></div>
        <div class="sbox"><div class="sbox-lbl">Section breakdown</div><div class="glist">${DL.map((l,j)=>`<div class="grow"><div class="gpip ${sc[j]>=7?'pg':sc[j]>=4?'pa':'pr'}"></div><div class="gname">${l}</div><div class="gpct">${sc[j]}/10</div></div>`).join('')}</div></div>
      </div>`;
    c.appendChild(p);
  });
}

function mkChart(i,s){
  if(CI[i])return;
  const sc=DK.map(k=>Math.round(s[k]||0));
  const ctx=document.getElementById(`ch-${i}`);if(!ctx)return;
  CI[i]=new Chart(ctx,{type:'bar',data:{labels:DL.map(l=>l.split(' ').slice(0,2).join(' ')),datasets:[{data:sc,backgroundColor:sc.map(v=>v>=7?'rgba(22,163,74,.85)':v>=4?'rgba(217,119,6,.85)':'rgba(185,28,28,.85)'),borderRadius:3,borderSkipped:false}]},options:{responsive:true,plugins:{legend:{display:false}},scales:{y:{min:0,max:10,ticks:{stepSize:2,callback:v=>v+'/10',font:{size:11}},grid:{color:'rgba(0,0,0,.05)'}},x:{ticks:{font:{size:10}},grid:{display:false}}}}});
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

loadDB();

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
