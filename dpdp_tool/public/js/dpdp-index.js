/* ─────────────────────────────────────────
   DPDP Navigator — Index Page JS
   Tech4Dev · dpdp.projecttech4dev.org
   File: public/js/dpdp-index.js
   Requires: Chart.js (CDN), frappe-web.min.js
─────────────────────────────────────────── */
'use strict';

const DL=['Data Collection & Consent','Data Storage & Security','Data Usage & Sharing','Rights of Individuals','Governance & Processes'];
const DK=['avg_consent','avg_storage','avg_usage','avg_rights','avg_governance'];
let CI={};

async function loadDB(){
  try{
    const r=await fetch(`${FU}/api/method/dpdp_tool.api.get_sector_insights`,{headers:{'Accept':'application/json'}});
    const j=await r.json();const d=j.message||[];
    document.getElementById('db-loading').remove();
    if(!d.length){showEmpty();return;}
    const tot=d.reduce((s,x)=>s+(x.submission_count||0),0);
    document.getElementById('db-meta').innerHTML=`<strong>${tot}</strong> submissions across <strong>${d.length}</strong> sectors`;
    mkTabs(d);mkPanels(d);document.querySelector('.stab')?.click();
  }catch(e){document.getElementById('db-loading').remove();loadDemo();}
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
        <div class="sbox"><div class="sbox-lbl">Overall avg. readiness</div><div class="sbox-val">${avg}/50</div><div class="sbox-sub">${s.submission_count} organisation${s.submission_count!==1?'s':''} assessed</div></div>
        <div class="sbox"><div class="sbox-lbl">Section breakdown</div><div class="glist">${DL.map((l,j)=>`<div class="grow"><div class="gpip ${sc[j]>=7?'pg':sc[j]>=4?'pa':'pr'}"></div><div class="gname">${l}</div><div class="gpct">${sc[j]}/10</div></div>`).join('')}</div></div>
      </div>`;
    c.appendChild(p);
  });
}

function mkChart(i,s){
  if(CI[i])return;
  const sc=DK.map(k=>Math.round(s[k]||0));
  const ctx=document.getElementById(`ch-${i}`);if(!ctx)return;
  CI[i]=new Chart(ctx,{type:'bar',data:{labels:DL.map(l=>l.split(' ').slice(0,2).join(' ')),datasets:[{data:sc,backgroundColor:sc.map(v=>v>=7?'rgba(29,111,184,.75)':v>=4?'rgba(146,64,14,.75)':'rgba(185,28,28,.75)'),borderRadius:3,borderSkipped:false}]},options:{responsive:true,plugins:{legend:{display:false}},scales:{y:{min:0,max:10,ticks:{stepSize:2,callback:v=>v+'/10',font:{size:11}},grid:{color:'rgba(0,0,0,.05)'}},x:{ticks:{font:{size:10}},grid:{display:false}}}}});
}

function loadDemo(){
  const d=[
    {sector:'Health & Nutrition',submission_count:12,avg_overall:44,avg_consent:4,avg_storage:3,avg_usage:4,avg_rights:3,avg_governance:6},
    {sector:'Education',submission_count:9,avg_overall:51,avg_consent:5,avg_storage:5,avg_usage:5,avg_rights:5,avg_governance:6},
    {sector:'Livelihoods',submission_count:6,avg_overall:38,avg_consent:3,avg_storage:4,avg_usage:4,avg_rights:3,avg_governance:4},
    {sector:'Gender & SRHR',submission_count:5,avg_overall:33,avg_consent:3,avg_storage:3,avg_usage:3,avg_rights:3,avg_governance:4},
    {sector:'Humanitarian',submission_count:4,avg_overall:29,avg_consent:3,avg_storage:3,avg_usage:3,avg_rights:2,avg_governance:3},
  ];
  const tot=d.reduce((s,x)=>s+x.submission_count,0);
  document.getElementById('db-meta').innerHTML=`<strong>${tot}</strong> submissions &nbsp;·&nbsp; <em style="color:var(--amber);font-size:.65rem">DEMO DATA</em>`;
  mkTabs(d);mkPanels(d);document.querySelector('.stab')?.click();
}

async function submitConsult(){
  const org=document.getElementById('cf-org').value.trim();
  const name=document.getElementById('cf-name').value.trim();
  const email=document.getElementById('cf-email').value.trim();
  if(!org||!name||!email){alert('Please fill in organisation name, your name, and email.');return;}
  const btn=document.querySelector('.fsub');btn.textContent='Submitting…';btn.disabled=true;
  try{
    await fetch(`${FU}/api/method/dpdp_tool.api.submit_consult_request`,{method:'POST',headers:{'Content-Type':'application/json','X-Frappe-CSRF-Token':frappe.csrf_token},body:JSON.stringify({org_name:org,contact_name:name,email,sector:document.getElementById('cf-sector').value,org_size:document.getElementById('cf-size').value,service_interest:document.getElementById('cf-svc').value,message:document.getElementById('cf-msg').value})});
  }catch(e){}
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
