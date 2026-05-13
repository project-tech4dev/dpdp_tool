/* ─────────────────────────────────────────
   DPDP Navigator — Assessment Page JS
   Tech4Dev · dpdp.projecttech4dev.org
   File: public/js/dpdp-assess.js
   Requires: jsPDF (CDN), frappe-web.min.js
─────────────────────────────────────────── */
'use strict';

// ══ DATA — from DPDP_Readiness_Questionnaire_short.xlsx ════════════

const SECTIONS = [
  {id:'consent',   label:'Data Collection & Consent'},
  {id:'storage',   label:'Data Storage & Security'},
  {id:'usage',     label:'Data Usage & Sharing'},
  {id:'rights',    label:'Rights of Individuals'},
  {id:'governance',label:'Governance & Processes'},
];

// Questions: {s=section index, t=text, w=why(short), o=options array}
// Options: [label, points]  Yes=2, Partially=1, No/Not Sure=0
const Q = [
  // SECTION 1: Data Collection & Consent (Q1-5)
  {s:0,t:"Before collecting personal data, do you give individuals a clear notice covering: (a) what data is collected, (b) why it is needed, (c) their rights, and (d) who to contact?",
   w:"A valid Notice must cover all four elements. Consent given without a proper notice is not valid under the DPDP Act.",
   o:[["Yes — notice covers all four elements",2],["Partially — notice is incomplete or unclear",1],["No / Not Sure",0]]},
  {s:0,t:"Do you have a separate and more stringent consent process for collecting data about children under 18 years of age?",
   w:"Children's data requires verifiable guardian consent, identification of minors, and stronger safeguards than adult data. If your programme does not work with under-18s, answer Yes.",
   o:[["Yes — or we do not work with under-18s",2],["Partially — some safeguards exist but not fully in place",1],["No / Not Sure",0]]},
  {s:0,t:"Is consent obtained in a manner that is clear, specific, informed, and recorded — so you can demonstrate it was given?",
   w:"Verbal or implied consent is very difficult to defend. You must be able to produce a record if a beneficiary disputes consent.",
   o:[["Yes — written or digital record for all consents",2],["Partially — some records exist but coverage is incomplete",1],["No / Not Sure",0]]},
  {s:0,t:"Do you collect only the personal data you actually need for your programme, avoiding extra details collected 'just in case'?",
   w:"Data Minimisation: only collect what is necessary for the stated purpose. Aadhaar, income, or caste should only be collected if directly required.",
   o:[["Yes — we collect only what is necessary",2],["Partially — we sometimes collect more than needed",1],["No / Not Sure",0]]},
  {s:0,t:"Do you have a clear process for individuals to withdraw consent, and do you stop using their data promptly after withdrawal?",
   w:"Withdrawal must be as easy as giving consent. After withdrawal you must stop processing and delete the data unless another legal basis applies.",
   o:[["Yes — a clear process exists and is followed",2],["Partially — withdrawal is possible but the process is unclear",1],["No / Not Sure",0]]},

  // SECTION 2: Data Storage & Security (Q6-10)
  {s:1,t:"Do you know what personal data you hold, where it is stored, who can access it, and why you keep it?",
   w:"A data inventory — even a simple spreadsheet — is the foundation of all compliance. You cannot protect data you do not know exists.",
   o:[["Yes — a maintained data inventory exists",2],["Partially — we have an informal sense but nothing documented",1],["No / Not Sure",0]]},
  {s:1,t:"Is personal data protected with reasonable security measures such as passwords, access controls, or encryption?",
   w:"Open WhatsApp groups or unprotected spreadsheets shared via 'anyone with the link' are a direct breach risk under the DPDP Act.",
   o:[["Yes — data is password-protected and access-controlled",2],["Partially — some systems are protected, others are not",1],["No / Not Sure",0]]},
  {s:1,t:"Do only the staff members who actually need the data have access to it?",
   w:"Access control is a core security safeguard. Not every staff member needs access to every beneficiary's personal data.",
   o:[["Yes — role-based access is in place",2],["Partially — access is somewhat restricted but not formally managed",1],["No / Not Sure",0]]},
  {s:1,t:"Do you have a defined retention schedule stating how long each type of data is kept and when it is deleted?",
   w:"Data must be deleted once the purpose is complete. Keeping data indefinitely 'just in case' is not permitted under the Act.",
   o:[["Yes — a retention schedule exists and deletions are carried out",2],["Partially — some retention rules exist but are not consistently followed",1],["No / Not Sure",0]]},
  {s:1,t:"Do you have a process — such as regular backups — ensuring personal data is not lost due to theft, damage, or system failure?",
   w:"Lost data cannot be recovered and may need to be reported as a breach. Security safeguards include ensuring data availability and integrity.",
   o:[["Yes — regular backups and a recovery process are in place",2],["Partially — backups occur but are not tested or regular",1],["No / Not Sure",0]]},

  // SECTION 3: Data Usage & Sharing (Q11-15)
  {s:2,t:"Do you use personal data only for the purpose you told the person about, unless another lawful basis applies?",
   w:"Purpose Limitation: data collected for one purpose cannot be used for another without fresh consent. Patient phone numbers must not be used for fundraising calls.",
   o:[["Yes — data is used only for its stated purpose",2],["Partially — we sometimes use data beyond its original purpose",1],["No / Not Sure",0]]},
  {s:2,t:"If you share personal data with another organisation, do you clearly define why it is shared and how it will be protected?",
   w:"As the Data Fiduciary, you remain responsible for beneficiary data even when a partner or processor handles it. Written agreements are essential.",
   o:[["Yes — written data-sharing agreements exist with all partners",2],["Partially — some agreements exist but coverage is incomplete",1],["No / Not Sure",0]]},
  {s:2,t:"Do your staff avoid sharing beneficiary data via personal WhatsApp, personal email accounts, or other unsecured channels?",
   w:"Unsecured sharing is an avoidable breach risk. Reasonable security safeguards include controlling how data is transmitted.",
   o:[["Yes — staff use only official, secure channels for data",2],["Partially — unofficial channels are sometimes used",1],["No / Not Sure",0]]},
  {s:2,t:"Do you know whether any vendor or online service (e.g. Google Forms, KoBoToolbox) stores data outside India, and have you assessed whether that arrangement is permitted?",
   w:"The government may impose conditions on cross-border transfers. NGOs should at minimum know where their data is hosted.",
   o:[["Yes — we know where all our data is hosted and have assessed the risk",2],["Partially — we know about some platforms but not all",1],["No / Not Sure",0]]},
  {s:2,t:"Before using any new vendor, tool, or app that handles personal data, do you check whether it has adequate privacy and security practices?",
   w:"You are accountable for vendors who handle data on your behalf. Basic due diligence — checking for a privacy policy and encryption — is required.",
   o:[["Yes — vendor checks are done before adoption",2],["Partially — some checks happen but not consistently",1],["No / Not Sure",0]]},

  // SECTION 4: Rights of Individuals (Q16-20)
  {s:3,t:"Do you have a defined process for responding to requests to access personal data and information about how it is being used?",
   w:"Rights of access, correction, and erasure are legally enforceable. There must be a defined workflow — not a vague 'someone will handle it' approach.",
   o:[["Yes — a named person, log, and response timeline exist",2],["Partially — requests are handled informally without a formal process",1],["No / Not Sure",0]]},
  {s:3,t:"Can individuals ask you to correct, complete, or update inaccurate personal data — and do you update it everywhere it appears?",
   w:"Right to Correction: inaccurate data can harm beneficiaries. The correction must flow to all records and partner systems where the data appears.",
   o:[["Yes — a correction process exists and is followed",2],["Partially — corrections happen but not systematically",1],["No / Not Sure",0]]},
  {s:3,t:"Can individuals ask you to erase their personal data, and do you comply (subject to legal retention requirements)?",
   w:"Right to Erasure: when someone asks for deletion and there is no legal reason to retain the data, you must comply and confirm.",
   o:[["Yes — an erasure process exists and is documented",2],["Partially — erasure happens on request but without a formal process",1],["No / Not Sure",0]]},
  {s:3,t:"Do you have a visible, accessible grievance mechanism for individuals to raise complaints or questions about their data?",
   w:"Grievance Redressal is a mandatory requirement under the DPDP Act. There must be a named contact and a response process.",
   o:[["Yes — a named contact and process are communicated to beneficiaries",2],["Partially — a contact exists but is not clearly communicated",1],["No / Not Sure",0]]},
  {s:3,t:"Do you respond to all data-related requests (access, correction, deletion, complaints) within your published timeline?",
   w:"Unresolved requests can be escalated to the Data Protection Board. Timely response — within 90 days — is required under DPDP Rules.",
   o:[["Yes — requests are tracked and resolved within timeline",2],["Partially — most requests are resolved but tracking is informal",1],["No / Not Sure",0]]},

  // SECTION 5: Governance & Processes (Q21-25)
  {s:4,t:"Has your organisation assigned at least one person to be responsible for data protection — even if not a full-time role?",
   w:"Without ownership, no compliance work can proceed consistently. Someone must be accountable.",
   o:[["Yes — a named person with a defined mandate",2],["Partially — someone is informally responsible but without a defined role",1],["No / Not Sure",0]]},
  {s:4,t:"Do you have a written privacy or data protection policy that explains what data you collect, why, and how you protect it?",
   w:"A written policy helps you stay consistent, builds trust with beneficiaries, and demonstrates accountability to regulators and funders.",
   o:[["Yes — a written policy exists and is shared with staff",2],["Partially — a draft or partial policy exists",1],["No / Not Sure",0]]},
  {s:4,t:"Have your staff and volunteers received any training on what personal data is, why protecting it matters, and how to handle it carefully?",
   w:"The organisation is responsible for how staff handle data. Training reduces the risk of accidental breaches.",
   o:[["Yes — structured training has been conducted and documented",2],["Partially — informal briefings have happened but no structured training",1],["No / Not Sure",0]]},
  {s:4,t:"If a personal data breach occurs, can you identify it, assess the impact, and notify affected individuals and the Data Protection Board when required?",
   w:"Breach notification to the Board is mandatory. Penalties are highest in breach situations. Detection and response speed matter.",
   o:[["Yes — a documented breach response plan exists and has been communicated",2],["Partially — some informal guidance exists but no documented plan",1],["No / Not Sure",0]]},
  {s:4,t:"Do you periodically review and update your privacy practices to reflect changes in programmes, tools, and regulations?",
   w:"Compliance is ongoing. Programmes evolve, tools change, and the law gets updated — annual review keeps you on track.",
   o:[["Yes — an annual or periodic review process is in place",2],["Partially — reviews happen occasionally but not systematically",1],["No / Not Sure",0]]},
];

function getCsrfToken() {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : 'fetch';
}

const SEC_COUNTS = [5,5,5,5,5];

// ══ STATE ══════════════════════════════════════════════════════════
let org={};
let answers = new Array(Q.length).fill(null);
let currentQ = 0;
let reco = '';
const FRAPPE_URL = '';

// ══ NAV ════════════════════════════════════════════════════════════
function showScreen(id){
  document.querySelectorAll('.screen').forEach(s=>s.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  currentScreen=id;window.scrollTo(0,0);
}
let currentScreen='s-intro';
window.addEventListener('beforeunload',e=>{if(currentScreen==='s-assess'){e.preventDefault();e.returnValue='';}});

function startAssessment(){
  const o=document.getElementById('i-org').value.trim();
  const n=document.getElementById('i-name').value.trim();
  const e=document.getElementById('i-email').value.trim();
  const sc = Array.from(document.querySelectorAll('#sector-checkboxes input:checked')).map(cb => cb.value);
  const sz=document.getElementById('i-size').value;
  if(!o||!n||!e||sc.length===0||!sz){alert('Please fill in all required fields and select at least one sector.');return;}
  org={org:o,name:n,email:e,sector:sc,size:sz,bene:document.getElementById('i-bene').value.trim()};
  showScreen('s-assess');currentQ=0;renderQ(0);
}

// ══ RENDER QUESTION ════════════════════════════════════════════════
function renderQ(idx){
  const q=Q[idx];const tot=Q.length;const pct=Math.round(((idx+1)/tot)*100);
  const secIdx=q.s;const sec=SECTIONS[secIdx];
  const priorQ=SEC_COUNTS.slice(0,secIdx).reduce((a,b)=>a+b,0);
  const qInSec=idx-priorQ+1;const totInSec=SEC_COUNTS[secIdx];

  document.getElementById('prog-fill').style.width=pct+'%';
  document.getElementById('prog-cnt').textContent=`Question ${idx+1} of ${tot}`;
  document.getElementById('prog-sec').textContent=`${sec.label} · ${qInSec} of ${totInSec}`;

  const sel=answers[idx];
  document.getElementById('q-area').innerHTML=`
    <div class="sec-badge">Section ${secIdx+1} — ${sec.label}</div>
    <div class="q-card">
      <div class="q-num">Q${idx+1}</div>
      <div class="q-text">${q.t}</div>
      ${q.w?`<div class="q-why">${q.w}</div>`:''}
      <div class="opts">${q.o.map((opt,oi)=>`
        <div class="opt${sel===oi?' sel':''}" onclick="selectOpt(${idx},${oi})">
          <div class="opt-radio"></div>
          <div class="opt-label">${opt[0]}</div>
          <div class="opt-pts">${opt[1]} pt${opt[1]!==1?'s':''}</div>
        </div>`).join('')}
      </div>
    </div>`;

  document.getElementById('btn-prev').style.visibility=idx===0?'hidden':'visible';
  document.getElementById('btn-next').textContent=idx===tot-1?'Submit →':'Next →';
  document.getElementById('btn-next').disabled=(sel===null);
  updateStrip(idx);
}

function selectOpt(qIdx,oi){answers[qIdx]=oi;renderQ(qIdx);}

function nextQ(){if(answers[currentQ]===null)return;if(currentQ===Q.length-1){submitAssessment();}else{currentQ++;renderQ(currentQ);}}
function prevQ(){if(currentQ>0){currentQ--;renderQ(currentQ);}}

function updateStrip(cur){
  const strip=document.getElementById('ss-strip');
  const firstDone=answers.slice(0,5).every(a=>a!==null);
  if(!firstDone){strip.classList.remove('vis');return;}
  strip.classList.add('vis');
  const {secScores}=calcScores();
  document.getElementById('ss-bars').innerHTML=SECTIONS.map((sec,i)=>{
    const sc=secScores[i];if(sc===null)return'';
    const maxSec=SEC_COUNTS[i]*2;const pct=Math.round((sc/maxSec)*100);
    const col=pct>=70?'var(--blue)':pct>=40?'var(--amber)':'var(--red)';
    return`<div class="ss-row"><div class="ss-label">${sec.label}</div><div class="ss-track"><div class="ss-fill" style="width:${pct}%;background:${col}"></div></div><div class="ss-pct">${pct}%</div></div>`;
  }).join('');
}

// ══ SCORING ════════════════════════════════════════════════════════
function calcScores(){
  const secScores=SECTIONS.map((sec,si)=>{
    const qs=Q.filter(q=>q.s===si);
    const scored=qs.filter((_,qi)=>answers[Q.indexOf(qs[qi])]!==null);
    if(!scored.length)return null;
    return qs.reduce((sum,q)=>{const gi=Q.indexOf(q);const a=answers[gi];if(a===null)return sum;return sum+Q[gi].o[a][1];},0);
  });
  const validSec=secScores.filter(s=>s!==null);
  const total=validSec.reduce((a,b)=>a+b,0);
  const maxTotal=Q.reduce((s,q)=>s+q.o.reduce((m,o)=>Math.max(m,o[1]),0),0);
  return{secScores,total,maxTotal};
}

// ══ SUBMIT ═════════════════════════════════════════════════════════
async function submitAssessment(){
  const{secScores,total}=calcScores();
  showScreen('s-result');

  document.getElementById('rh-org').textContent=`${org.org} · ${org.sector} · ${org.size}`;
  animateScore('rh-score',total);

  const band=document.getElementById('rh-band');
  if(total>=46){band.textContent='🟢 Strong Readiness';band.style.background='rgba(22,101,52,.15)';band.style.color='#166534';}
  else if(total>=36){band.textContent='🟠 Moderate Readiness';band.style.background='rgba(234,88,12,.12)';band.style.color='#9a3412';}
  else if(total>=21){band.textContent='🟡 Basic Readiness — Needs Work';band.style.background='rgba(146,64,14,.12)';band.style.color='#78350f';}
  else{band.textContent='🔴 High Risk — Not Ready';band.style.background='rgba(185,28,28,.12)';band.style.color='#991b1b';}

  renderSGrid(secScores);
  renderQBreakdown();
  fetchReco(secScores,total).then(()=>storeInFrappe(secScores,total));
}

function animateScore(id,target){
  const el=document.getElementById(id);let cur=0;
  const step=Math.ceil(target/40);
  const t=setInterval(()=>{cur=Math.min(cur+step,target);el.textContent=cur;if(cur>=target)clearInterval(t);},30);
}

function renderSGrid(secScores){
  const g=document.getElementById('sgrid');
  g.innerHTML=SECTIONS.map((sec,i)=>{
    const raw=secScores[i]!==null?secScores[i]:0;
    const maxSec=SEC_COUNTS[i]*2;
    const pct=Math.round((raw/maxSec)*100);
    const band=pct>=70?'high':pct>=40?'mid':'low';
    const lbl=pct>=70?'Strong':pct>=40?'Developing':'Priority gap';
    return`<div class="scard ${band}" style="animation-delay:${i*.07}s">
      <div class="sc-name">Section ${i+1} · ${sec.label}</div>
      <div class="sc-pct ${band}">${raw}/${maxSec}</div>
      <div class="sc-bar"><div class="sc-bar-fill fill-${band}" style="width:${pct}%"></div></div>
      <div class="sc-lbl">${lbl} · ${pct}%</div>
    </div>`;
  }).join('');
}

function renderQBreakdown(){
  document.getElementById('qb-secs').innerHTML=SECTIONS.map((sec,si)=>{
    const qs=Q.filter(q=>q.s===si);
    return`<div>
      <div class="qb-sec-title">Section ${si+1} — ${sec.label}</div>
      <div class="qb-rows">${qs.map(q=>{
        const gi=Q.indexOf(q);const a=answers[gi];if(a===null)return'';
        const pts=Q[gi].o[a][1];
        const pip=pts===2?'var(--blue)':pts===1?'var(--amber)':'var(--red)';
        const cls=pts===2?'ans-yes':pts===1?'ans-part':'ans-no';
        const lbl=pts===2?'Yes':pts===1?'Partially':'No';
        return`<div class="qb-row">
          <div class="qb-pip" style="background:${pip}"></div>
          <div class="qb-q">${q.t.substring(0,85)}${q.t.length>85?'…':''}</div>
          <div class="qb-ans ${cls}">${lbl}</div>
        </div>`;
      }).join('')}</div>
    </div>`;
  }).join('');
}

// ══ FRAPPE + CLAUDE ════════════════════════════════════════════════
async function fetchReco(secScores,total){
  const steps=['Analysing your responses…','Mapping gaps to DPDP Act sections…','Generating your 30-day priority actions…','Building your 90-day roadmap…','Preparing your 1-year plan…'];
  let si=0;const stepEl=document.getElementById('reco-step');
  const t=setInterval(()=>{si=(si+1)%steps.length;if(stepEl)stepEl.textContent=steps[si];},2800);

  return new Promise(async(resolve)=>{
    try{
      const payload={
        org_name:org.org,sector:org.sector,org_size:org.size,beneficiaries:org.bene,
        total_score:total,max_score:Q.reduce((s,q)=>s+q.o.reduce((m,o)=>Math.max(m,o[1]),0),0),
        section_scores:{consent:secScores[0],storage:secScores[1],usage:secScores[2],rights:secScores[3],governance:secScores[4]},
        answers:buildAnswerSummary()
      };
      const p=new URLSearchParams();
      p.append('sector',JSON.stringify(Array.isArray(payload.sector)?payload.sector:[payload.sector]));
      p.append('org_size',payload.org_size);
      p.append('beneficiaries',payload.beneficiaries||'');
      p.append('total_score',payload.total_score);
      p.append('max_score',payload.max_score);
      p.append('section_scores',JSON.stringify(payload.section_scores));
      p.append('answers',payload.answers);
      const res=await fetch(`${FRAPPE_URL}/api/method/dpdp_tool.api.get_recommendations?${p}`);
      const j=await res.json();
      clearInterval(t);
      reco=j.message?.recommendations||'';
      if(!reco)throw new Error('empty');
      renderReco(reco);
    }catch(e){
      clearInterval(t);
      console.error('[fetchReco] failed:', e.message, e);
//      reco = fallbackReco(secScores, total); renderReco(reco);
    }
    document.getElementById('btn-pdf').disabled=false;
    resolve();
  });
}

function buildAnswerSummary(){
  return Q.map((q,i)=>{
    const a=answers[i];const lbl=a===null?'Not answered':Q[i].o[a][0];
    return`Q${i+1} [${SECTIONS[q.s].label}]: ${lbl}`;
  }).join('\n');
}

function renderReco(text){
  const el=document.getElementById('reco-content');
  const html=text
    .replace(/^## (.+)$/gm,'<h2>$1</h2>')
    .replace(/^### (.+)$/gm,'<h3>$1</h3>')
    .replace(/\*\*(.+?)\*\*/g,'<strong>$1</strong>')
    .replace(/^- (.+)$/gm,'<li>$1</li>')
    .replace(/(<li>[\s\S]*?<\/li>)+/g,m=>`<ul>${m}</ul>`)
    .replace(/\n\n/g,'</p><p>')
    .replace(/^(?!<[hul])(.+)$/gm,'<p>$1</p>');
  el.innerHTML=html||text;
}

function fallbackReco(secScores,total){
  const maxSec=SEC_COUNTS.map(c=>c*2);
  const gaps=SECTIONS.map((s,i)=>({label:s.label,pct:secScores[i]!==null?Math.round((secScores[i]/maxSec[i])*100):0})).sort((a,b)=>a.pct-b.pct).slice(0,3);
  return`## Executive Summary\n\nYour organisation scored **${total} out of 50** on the DPDP Act 2023 readiness assessment. Your three priority gaps are in **${gaps.map(g=>g.label).join(', ')}**. Focused effort across the next 90 days can make meaningful progress.\n\n## 30-Day Priority Actions\n\n**1. ${gaps[0]?.label}** — Start by documenting your current practices. Assign a named person to own data protection and draft a one-page interim policy.\n\n**2. Review consent documentation** — Check all data collection forms against the DPDP notice requirements: purpose, retention period, rights, and contact details.\n\n**3. Map your data landscape** — Create a simple spreadsheet listing every category of personal data, where it is stored, and who has access.\n\n## 90-Day Compliance Foundation\n\n- Approve a written data protection policy\n- Train all programme staff on DPDP basics (2-hour session)\n- Sign Data Processing Agreements with key technology vendors\n- Establish a grievance mechanism and communicate it to beneficiaries\n- Conduct a basic security review of your key systems\n\n## 1-Year Programme\n\n- Annual DPDP compliance review at board meeting\n- Refresh consent forms when programmes change\n- Test your breach response plan annually\n- Review vendor DPAs at contract renewal\n\n*Contact Tech4Dev for a personalised implementation plan.*`;
}

async function storeInFrappe(secScores, total) {
  try {
    const params = new URLSearchParams({
      org_name:      org.org,
      org_email:     org.email,
      contact_name:  org.name,
      sector:        JSON.stringify(Array.isArray(org.sector) ? org.sector : [org.sector]),
      org_size:      org.size,
      beneficiaries: org.bene || '',
      total_score:   total,
      score_consent:    secScores[0] || 0,
      score_storage:    secScores[1] || 0,
      score_usage:      secScores[2] || 0,
      score_rights:     secScores[3] || 0,
      score_governance: secScores[4] || 0,
      answers_json:  JSON.stringify(answers),
      recommendations: reco || ''
    });
    const res = await fetch(`/api/method/dpdp_tool.api.store_assessment?${params}`);
    const j = await res.json();
    console.log('Stored:', j.message?.docname);
  } catch(e) { console.error('storeInFrappe:', e); }
}

// ══ PDF ════════════════════════════════════════════════════════════
function generatePDF(){
  const{jsPDF}=window.jspdf;
  const doc=new jsPDF({unit:'mm',format:'a4'});
  const{secScores,total}=calcScores();
  const W=210,M=18,CW=W-M*2;let y=0;
  const chk=(n=15)=>{if(y+n>270){doc.addPage();y=20;}};

  // Cover
  doc.setFillColor(26,43,74);doc.rect(0,0,W,297,'F');
  doc.setFillColor(29,111,184);doc.rect(0,0,5,297,'F');
  doc.setTextColor(126,184,240);doc.setFontSize(8);doc.setFont('helvetica','normal');
  doc.text('TECH4DEV · DPDP READINESS NAVIGATOR',M,40);
  doc.setTextColor(255,255,255);doc.setFontSize(26);doc.setFont('helvetica','light');
  doc.text('DPDP Compliance',M,78);doc.text('Readiness Report',M,91);
  doc.setTextColor(126,184,240);doc.setFontSize(48);
  doc.text(`${total}/50`,M,140);
  doc.setTextColor(160,185,210);doc.setFontSize(10);doc.text('Overall readiness score',M,150);
  doc.setTextColor(255,255,255);doc.setFontSize(14);doc.text(org.org,M,180);
  doc.setFontSize(10);doc.setTextColor(140,165,200);
  doc.text(`${org.sector} · ${org.size}`,M,188);
  doc.text('Assessed: '+new Date().toLocaleDateString('en-IN',{day:'numeric',month:'long',year:'numeric'}),M,196);

  // Readiness band
  const bandTxt=total>=46?'Strong Readiness':total>=36?'Moderate Readiness':total>=21?'Basic Readiness — Needs Work':'High Risk — Not Ready';
  doc.setTextColor(126,184,240);doc.setFontSize(9);doc.text(bandTxt,M,210);

  // Page 2: Section scores
  doc.addPage();y=25;
  doc.setFillColor(26,43,74);doc.rect(0,0,W,10,'F');
  doc.setTextColor(255,255,255);doc.setFontSize(7);
  doc.text('DPDP READINESS REPORT · '+org.org.toUpperCase(),M,7);
  y=28;doc.setTextColor(26,43,74);doc.setFontSize(15);doc.setFont('helvetica','bold');
  doc.text('Section Score Summary',M,y);y+=12;

  SECTIONS.forEach((sec,i)=>{
    chk(22);const raw=secScores[i]||0;const max=SEC_COUNTS[i]*2;const pct=Math.round((raw/max)*100);
    const col=pct>=70?[29,111,184]:pct>=40?[146,64,14]:[185,28,28];
    doc.setFontSize(9);doc.setFont('helvetica','bold');doc.setTextColor(26,43,74);
    doc.text(`Section ${i+1}: ${sec.label}`,M,y);
    doc.setFontSize(8);doc.setFont('helvetica','normal');doc.setTextColor(74,85,104);
    doc.text(`${raw} of ${max} points`,M+CW-28,y);y+=5;
    doc.setFillColor(220,226,232);doc.roundedRect(M,y,CW-35,5,1,1,'F');
    doc.setFillColor(...col);doc.roundedRect(M,y,((CW-35)*pct/100),5,1,1,'F');
    y+=14;
  });

  // Page 3: Q breakdown
  doc.addPage();y=25;
  doc.setFillColor(26,43,74);doc.rect(0,0,W,10,'F');
  doc.setTextColor(255,255,255);doc.setFontSize(7);doc.text('DPDP READINESS REPORT · '+org.org.toUpperCase(),M,7);
  y=28;doc.setTextColor(26,43,74);doc.setFontSize(15);doc.setFont('helvetica','bold');
  doc.text('Question-by-Question Breakdown',M,y);y+=12;

  SECTIONS.forEach((sec,si)=>{
    chk(20);doc.setFontSize(9);doc.setFont('helvetica','bold');doc.setTextColor(29,111,184);
    doc.text(`SECTION ${si+1} — ${sec.label.toUpperCase()}`,M,y);y+=6;
    Q.filter(q=>q.s===si).forEach(q=>{
      chk(12);const gi=Q.indexOf(q);const a=answers[gi];const pts=Q[gi].o[a]?.[1]||0;
      const lbl=pts===2?'Yes':pts===1?'Partially':'No';
      const col=pts===2?[29,111,184]:pts===1?[146,64,14]:[185,28,28];
      doc.setFillColor(...col);doc.circle(M+2,y-1.5,1.5,'F');
      doc.setFontSize(8);doc.setFont('helvetica','normal');doc.setTextColor(26,43,74);
      const lines=doc.splitTextToSize(q.t,CW-30);
      doc.text(lines[0]+(lines.length>1?'…':''),M+6,y);
      doc.setFont('helvetica','bold');doc.setTextColor(...col);
      doc.text(lbl,M+CW-20,y);y+=8;
    });y+=4;
  });

  // Page 4+: Recommendations
  if(reco){
    doc.addPage();y=25;
    doc.setFillColor(26,43,74);doc.rect(0,0,W,10,'F');
    doc.setTextColor(255,255,255);doc.setFontSize(7);doc.text('DPDP READINESS REPORT · '+org.org.toUpperCase(),M,7);
    y=28;doc.setTextColor(26,43,74);doc.setFontSize(15);doc.setFont('helvetica','bold');
    doc.text('AI-Generated Compliance Roadmap',M,y);y+=12;
    const clean=reco.replace(/#{1,3} /g,'').replace(/\*\*(.+?)\*\*/g,'$1').replace(/^- /gm,'• ');
    clean.split('\n').filter(l=>l.trim()).forEach(line=>{
      chk(10);
      if(line.length<60&&!line.startsWith('•')&&line===line.trim()){
        y+=3;doc.setFontSize(10);doc.setFont('helvetica','bold');doc.setTextColor(29,111,184);
        doc.text(line,M,y);y+=6;
      }else{
        doc.setFontSize(8.5);doc.setFont('helvetica','normal');doc.setTextColor(26,43,74);
        doc.splitTextToSize(line,CW).forEach(wl=>{chk(6);doc.text(wl,M,y);y+=5.5;});y+=1;
      }
    });
  }

  // Footer on all pages
  const tot=doc.getNumberOfPages();
  for(let p=1;p<=tot;p++){
    doc.setPage(p);if(p>1){
      doc.setFillColor(232,236,245);doc.rect(0,285,W,12,'F');
      doc.setFontSize(7);doc.setFont('helvetica','normal');doc.setTextColor(74,85,104);
      doc.text('Tech4Dev · DPDP Readiness Navigator · dpdp.projecttech4dev.org',M,292);
      doc.text(`Page ${p} of ${tot}`,W-M-15,292);
    }
  }
  doc.save(`DPDP_${org.org.replace(/\s+/g,'_')}_${new Date().toISOString().slice(0,10)}.pdf`);
}

function restartAssessment(){
  answers=new Array(Q.length).fill(null);currentQ=0;reco='';
  document.getElementById('btn-pdf').disabled=true;
  showScreen('s-intro');
}
