# -*- coding: utf-8 -*-
"""
app.py – Interface Web Interactive pour MOGA Timetabling.

Lancer avec :  python app.py
Ouvrir dans le navigateur : http://localhost:5000

Fonctionnalités :
  - Formulaire de saisie complet (groupes, salles, enseignants, matières, paramètres NSGA-II)
  - Streaming de la progression en temps réel (SSE) pendant l'optimisation
  - Visualisation des résultats : graphiques Pareto + convergence, grilles d'emplois du temps
  - Téléchargement des CSV et images générés
"""

import os
import sys
import json
import threading
import time
import base64
import io
import queue

# ── Flask ────────────────────────────────────────────────────────────────────
try:
    from flask import Flask, render_template_string, request, jsonify, Response, send_file
except ImportError:
    print("Flask non installé. Lancez :  pip install flask")
    sys.exit(1)

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ── Projet ───────────────────────────────────────────────────────────────────
DOSSIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DOSSIER)

import config as C

app   = Flask(__name__)
_lock = threading.Lock()          # empêche deux optimisations simultanées

# File d'événements SSE par session (simpliste : une seule session à la fois)
_progress_queue: queue.Queue = queue.Queue()
_run_state = {"running": False, "result": None, "error": None}

# ═══════════════════════════════════════════════════════════════════════════════
# HTML TEMPLATE (tout en un seul fichier pour la portabilité)
# ═══════════════════════════════════════════════════════════════════════════════
HTML = r"""
<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>MOGA Timetabling – NSGA-II</title>
<style>
:root{
  --blue:#2563eb;--blue-dark:#1d4ed8;--green:#16a34a;
  --red:#dc2626;--gray:#6b7280;--bg:#f1f5f9;--card:#fff;
  --border:#e2e8f0;--text:#1e293b;--sub:#475569;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',system-ui,sans-serif;background:var(--bg);color:var(--text);font-size:14px}
header{background:linear-gradient(135deg,#1e3a5f,#2563eb);color:#fff;padding:18px 32px;display:flex;align-items:center;gap:16px}
header h1{font-size:1.4rem;font-weight:700}
header p{font-size:.85rem;opacity:.8;margin-top:2px}
.badge{background:rgba(255,255,255,.18);border-radius:999px;padding:3px 10px;font-size:.75rem}
main{max-width:1300px;margin:0 auto;padding:24px 16px;display:grid;grid-template-columns:380px 1fr;gap:20px}
@media(max-width:900px){main{grid-template-columns:1fr}}
/* CARD */
.card{background:var(--card);border-radius:12px;border:1px solid var(--border);padding:20px;margin-bottom:16px}
.card h2{font-size:1rem;font-weight:700;margin-bottom:14px;display:flex;align-items:center;gap:8px}
.card h2 .ico{font-size:1.1rem}
/* FORM */
fieldset{border:1px solid var(--border);border-radius:8px;padding:12px 14px;margin-bottom:12px}
legend{font-weight:600;font-size:.85rem;padding:0 6px;color:var(--blue)}
label{display:block;font-size:.8rem;color:var(--sub);margin-bottom:2px;margin-top:8px}
label:first-child{margin-top:0}
input,select,textarea{width:100%;padding:7px 10px;border:1px solid var(--border);border-radius:6px;font-size:.85rem;color:var(--text);background:#fff}
input:focus,select:focus,textarea:focus{outline:2px solid var(--blue);border-color:var(--blue)}
textarea{resize:vertical;min-height:80px;font-family:monospace;font-size:.78rem}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.btn{display:inline-flex;align-items:center;gap:6px;padding:9px 18px;border:none;border-radius:7px;font-size:.88rem;font-weight:600;cursor:pointer;transition:.15s}
.btn-primary{background:var(--blue);color:#fff}.btn-primary:hover{background:var(--blue-dark)}
.btn-danger{background:var(--red);color:#fff}
.btn-sm{padding:5px 12px;font-size:.8rem}
.btn-green{background:var(--green);color:#fff}
/* PROGRESS */
#progress-wrap{display:none}
.prog-bar-bg{background:var(--border);border-radius:999px;height:10px;margin:10px 0}
.prog-bar{background:var(--blue);height:10px;border-radius:999px;width:0%;transition:width .3s}
#log{background:#0f172a;color:#94a3b8;border-radius:8px;padding:12px;font-family:monospace;font-size:.75rem;height:160px;overflow-y:auto;margin-top:8px}
/* TABS */
.tabs{display:flex;gap:4px;margin-bottom:14px;flex-wrap:wrap}
.tab{padding:6px 14px;border-radius:6px;border:1px solid var(--border);background:#fff;cursor:pointer;font-size:.82rem;font-weight:600;color:var(--sub)}
.tab.active{background:var(--blue);color:#fff;border-color:var(--blue)}
.tab-panel{display:none}.tab-panel.active{display:block}
/* RESULTS */
.metric-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px}
.metric{text-align:center;background:var(--bg);border-radius:8px;padding:10px 6px}
.metric .val{font-size:1.5rem;font-weight:800;color:var(--blue)}
.metric .lbl{font-size:.72rem;color:var(--sub);margin-top:2px}
.metric.good .val{color:var(--green)}
/* TIMETABLE */
.tt-wrap{overflow-x:auto;margin-top:10px}
table{border-collapse:collapse;width:100%;font-size:.75rem}
th,td{border:1px solid var(--border);padding:5px 7px;text-align:center}
th{background:var(--blue);color:#fff;font-weight:600}
td:first-child{background:#f8fafc;font-weight:600;white-space:nowrap}
td.conflict{background:#fee2e2;color:var(--red)}
td.empty{color:#cbd5e1}
td.occupied{background:#eff6ff}
/* CHART */
.chart-row{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:14px}
@media(max-width:700px){.chart-row{grid-template-columns:1fr}}
.chart-row img{width:100%;border-radius:8px;border:1px solid var(--border)}
/* Dynamic rows */
.dyn-row{display:flex;gap:6px;align-items:center;margin-bottom:6px}
.dyn-row input,.dyn-row select{flex:1}
.dyn-row .rm{background:var(--red);color:#fff;border:none;border-radius:5px;width:24px;height:24px;cursor:pointer;font-size:1rem;line-height:1}
.add-btn{font-size:.8rem;color:var(--blue);cursor:pointer;background:none;border:none;padding:2px 0;text-decoration:underline}
</style>
</head>
<body>
<header>
  <div>
    <h1>🎓 MOGA Timetabling</h1>
    <p>Optimisation NSGA-II des emplois du temps universitaires</p>
  </div>
  <span class="badge">NSGA-II • 3 objectifs</span>
</header>

<main>
<!-- ═══ PANNEAU GAUCHE : FORMULAIRE ═══ -->
<aside>
  <div class="card">
    <h2><span class="ico">⚙️</span> Configuration du problème</h2>
    <form id="form">

      <!-- JOURS actifs -->
      <fieldset>
        <legend>Jours de la semaine actifs</legend>
        <div id="days-check" style="display:grid;grid-template-columns:1fr 1fr;gap:4px 12px;margin-top:4px">
          {% for jour in all_jours %}
          <label style="display:flex;align-items:center;gap:5px;margin:0;font-size:.82rem">
            <input type="checkbox" name="jours" value="{{ jour }}"
              {% if jour in default_jours %}checked{% endif %}> {{ jour }}
          </label>
          {% endfor %}
        </div>
      </fieldset>

      <!-- GROUPES -->
      <fieldset>
        <legend>Groupes d'étudiants</legend>
        <div id="grp-list">
          {% for nom, eff in default_groupes %}
          <div class="dyn-row">
            <input type="text" placeholder="Nom (ex: G1)" value="{{ nom }}" data-role="grp-nom">
            <input type="number" placeholder="Effectif" value="{{ eff }}" min="1" max="500" data-role="grp-eff">
            <button type="button" class="rm" onclick="rmRow(this)">×</button>
          </div>
          {% endfor %}
        </div>
        <button type="button" class="add-btn" onclick="addRow('grp-list','grp-nom|grp-eff','Nom|Effectif')">+ Ajouter un groupe</button>
      </fieldset>

      <!-- SALLES -->
      <fieldset>
        <legend>Salles</legend>
        <div id="sal-list">
          {% for nom, cap in default_salles %}
          <div class="dyn-row">
            <input type="text" placeholder="Nom" value="{{ nom }}" data-role="sal-nom">
            <input type="number" placeholder="Capacité" value="{{ cap }}" min="1" data-role="sal-cap">
            <button type="button" class="rm" onclick="rmRow(this)">×</button>
          </div>
          {% endfor %}
        </div>
        <button type="button" class="add-btn" onclick="addRow('sal-list','sal-nom|sal-cap','Salle|Capacité')">+ Ajouter une salle</button>
      </fieldset>

      <!-- ENSEIGNANTS -->
      <fieldset>
        <legend>Enseignants & disponibilités</legend>
        <div id="ens-list">
          {% for nom, jours in default_ens %}
          <div class="dyn-row" style="flex-wrap:wrap">
            <input type="text" placeholder="Nom" value="{{ nom }}" data-role="ens-nom" style="flex:0 0 70px">
            <input type="text" placeholder="Jours dispo (ex: Lun,Mar)" value="{{ jours }}" data-role="ens-jours" title="Noms de jours séparés par virgule">
            <button type="button" class="rm" onclick="rmRow(this)">×</button>
          </div>
          {% endfor %}
        </div>
        <button type="button" class="add-btn" onclick="addRow('ens-list','ens-nom|ens-jours','Nom|Jours dispo')">+ Ajouter un enseignant</button>
      </fieldset>

      <!-- MATIÈRES -->
      <fieldset>
        <legend>Matières</legend>
        <div id="mat-list">
          {% for nom, ens, duree, mode in default_matieres %}
          <div class="dyn-row" style="flex-wrap:wrap;gap:4px">
            <input type="text"   placeholder="Matière" value="{{ nom }}"   data-role="mat-nom"   style="flex:2 1 100px">
            <input type="text"   placeholder="Enseignant" value="{{ ens }}" data-role="mat-ens"  style="flex:1 1 60px">
            <input type="number" placeholder="Durée(créneaux)" value="{{ duree }}" min="1" max="4" data-role="mat-duree" style="flex:0 0 55px">
            <select data-role="mat-mode" style="flex:1 1 80px">
              <option value="ensemble" {% if mode=='ensemble' %}selected{% endif %}>CM</option>
              <option value="séparé"   {% if mode=='séparé'   %}selected{% endif %}>TD/TP</option>
            </select>
            <button type="button" class="rm" onclick="rmRow(this)">×</button>
          </div>
          {% endfor %}
        </div>
        <button type="button" class="add-btn" onclick="addMatRow()">+ Ajouter une matière</button>
      </fieldset>

      <!-- ALGORITHME -->
      <fieldset>
        <legend>Paramètres NSGA-II</legend>
        <div class="row2">
          <div><label>Population</label><input type="number" id="pop" value="100" min="10" max="500"></div>
          <div><label>Générations</label><input type="number" id="gen" value="400" min="10" max="2000"></div>
          <div><label>Pc (croisement)</label><input type="number" id="pc" value="0.9" min="0" max="1" step="0.05"></div>
          <div><label>Pm (mutation gène)</label><input type="number" id="pm" value="0.05" min="0" max="1" step="0.01"></div>
        </div>
        <label>Graine aléatoire (seed)</label>
        <input type="number" id="seed" value="42">
        <label style="display:flex;align-items:center;gap:6px;margin-top:8px">
          <input type="checkbox" id="dominance" checked> Dominance contrainte (recommandé)
        </label>
      </fieldset>

      <button type="button" class="btn btn-primary" style="width:100%" onclick="lancerOptimisation()">
        🚀 Lancer l'optimisation
      </button>
    </form>
  </div>
</aside>

<!-- ═══ PANNEAU DROIT : RÉSULTATS ═══ -->
<section>
  <!-- PROGRESS -->
  <div class="card" id="progress-wrap">
    <h2><span class="ico">⏳</span> Progression NSGA-II</h2>
    <div id="prog-label" style="font-size:.82rem;color:var(--sub)">Génération 0 / ?</div>
    <div class="prog-bar-bg"><div class="prog-bar" id="prog-bar"></div></div>
    <div id="log"></div>
    <button class="btn btn-danger btn-sm" style="margin-top:8px" onclick="arreter()">⏹ Arrêter</button>
  </div>

  <!-- RESULTS -->
  <div class="card" id="results-wrap" style="display:none">
    <h2><span class="ico">✅</span> Résultats</h2>

    <div class="metric-grid">
      <div class="metric good"><div class="val" id="m-f1">–</div><div class="lbl">f₁ Conflits</div></div>
      <div class="metric"><div class="val" id="m-f2">–</div><div class="lbl">f₂ Heures creuses</div></div>
      <div class="metric"><div class="val" id="m-f3">–</div><div class="lbl">f₃ Utilisation salles</div></div>
    </div>

    <div class="tabs">
      <button class="tab active" onclick="showTab('tab-charts',this)">📈 Graphiques</button>
      <button class="tab" onclick="showTab('tab-tt',this)">📅 Emplois du temps</button>
      <button class="tab" onclick="showTab('tab-front',this)">🏆 Front de Pareto</button>
      <button class="tab" onclick="showTab('tab-dl',this)">⬇️ Téléchargements</button>
    </div>

    <!-- Charts -->
    <div class="tab-panel active" id="tab-charts">
      <div class="chart-row">
        <img id="img-pareto" src="" alt="Front de Pareto">
        <img id="img-evol"   src="" alt="Évolution objectifs">
      </div>
    </div>

    <!-- Timetables -->
    <div class="tab-panel" id="tab-tt">
      <div id="tt-selector" style="display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap"></div>
      <div id="tt-content"></div>
    </div>

    <!-- Pareto front table -->
    <div class="tab-panel" id="tab-front">
      <div class="tt-wrap"><div id="front-table"></div></div>
    </div>

    <!-- Downloads -->
    <div class="tab-panel" id="tab-dl">
      <p style="margin-bottom:12px;color:var(--sub)">Fichiers générés dans le dossier du projet :</p>
      <div style="display:flex;flex-wrap:wrap;gap:8px">
        <a class="btn btn-green btn-sm" href="/download/front_pareto.png">🖼️ front_pareto.png</a>
        <a class="btn btn-green btn-sm" href="/download/evolution_objectifs.png">🖼️ evolution_objectifs.png</a>
        <a class="btn btn-green btn-sm" href="/download/emploi_du_temps_final.csv">📄 emploi_du_temps_final.csv</a>
        <a class="btn btn-green btn-sm" href="/download/solutions_pareto.csv">📄 solutions_pareto.csv</a>
        <a class="btn btn-green btn-sm" href="/download/historique_generations.csv">📄 historique_generations.csv</a>
      </div>
    </div>
  </div>
</section>
</main>

<script>
// ── helpers ────────────────────────────────────────────────────────────────
function rmRow(btn){btn.closest('.dyn-row').remove()}

function addRow(listId, roles, placeholders){
  const ph = placeholders.split('|');
  const rl = roles.split('|');
  const div = document.createElement('div');
  div.className='dyn-row';
  rl.forEach((r,i)=>{
    const inp=document.createElement('input');
    inp.type='text'; inp.placeholder=ph[i]; inp.dataset.role=r;
    div.appendChild(inp);
  });
  const rm=document.createElement('button');
  rm.type='button'; rm.className='rm'; rm.textContent='×';
  rm.onclick=function(){rmRow(this)};
  div.appendChild(rm);
  document.getElementById(listId).appendChild(div);
}

function addMatRow(){
  const div=document.createElement('div');
  div.className='dyn-row'; div.style.cssText='flex-wrap:wrap;gap:4px';
  div.innerHTML=`
    <input type="text"   placeholder="Matière"      data-role="mat-nom"   style="flex:2 1 100px">
    <input type="text"   placeholder="Enseignant"   data-role="mat-ens"   style="flex:1 1 60px">
    <input type="number" placeholder="Durée"        data-role="mat-duree" value="1" min="1" max="4" style="flex:0 0 55px">
    <select data-role="mat-mode" style="flex:1 1 80px">
      <option value="ensemble">CM</option>
      <option value="séparé" selected>TD/TP</option>
    </select>
    <button type="button" class="rm" onclick="rmRow(this)">×</button>`;
  document.getElementById('mat-list').appendChild(div);
}

function collectRows(listId, roles){
  const result=[];
  document.getElementById(listId).querySelectorAll('.dyn-row').forEach(row=>{
    const vals=roles.map(r=>{
      const el=row.querySelector(`[data-role="${r}"]`);
      return el ? el.value.trim() : '';
    });
    if(vals[0]) result.push(vals);
  });
  return result;
}

function showTab(id, btn){
  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
}

// ── form collection ─────────────────────────────────────────────────────────
function collectForm(){
  const jours = [...document.querySelectorAll('[name="jours"]:checked')].map(c=>c.value);
  const groupes = collectRows('grp-list',['grp-nom','grp-eff']);
  const salles  = collectRows('sal-list',['sal-nom','sal-cap']);
  const ens     = collectRows('ens-list',['ens-nom','ens-jours']);
  const matieres= collectRows('mat-list',['mat-nom','mat-ens','mat-duree','mat-mode']);
  return {
    jours, groupes, salles, ens, matieres,
    pop: parseInt(document.getElementById('pop').value)||100,
    gen: parseInt(document.getElementById('gen').value)||400,
    pc:  parseFloat(document.getElementById('pc').value)||0.9,
    pm:  parseFloat(document.getElementById('pm').value)||0.05,
    seed: parseInt(document.getElementById('seed').value)||42,
    dominance: document.getElementById('dominance').checked,
  };
}

// ── SSE / streaming ─────────────────────────────────────────────────────────
let evtSource = null;
let totalGen  = 400;

function lancerOptimisation(){
  const data = collectForm();
  if(!data.jours.length)   return alert('Sélectionnez au moins un jour.');
  if(!data.groupes.length) return alert('Ajoutez au moins un groupe.');
  if(!data.salles.length)  return alert('Ajoutez au moins une salle.');
  if(!data.ens.length)     return alert('Ajoutez au moins un enseignant.');
  if(!data.matieres.length)return alert('Ajoutez au moins une matière.');

  totalGen = data.gen;
  document.getElementById('progress-wrap').style.display='block';
  document.getElementById('results-wrap').style.display='none';
  document.getElementById('prog-bar').style.width='0%';
  document.getElementById('log').textContent='Démarrage…\n';
  document.getElementById('prog-label').textContent='Génération 0 / '+totalGen;

  // Start run
  fetch('/run',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)})
    .then(r=>r.json()).then(r=>{
      if(r.error){ alert(r.error); return; }
      // Start SSE
      if(evtSource) evtSource.close();
      evtSource = new EventSource('/progress');
      evtSource.onmessage = handleSSE;
      evtSource.onerror   = ()=>evtSource.close();
    });
}

function handleSSE(e){
  const d = JSON.parse(e.data);
  if(d.type==='done'){
    evtSource.close();
    showResults(d);
    return;
  }
  if(d.type==='error'){
    evtSource.close();
    alert('Erreur : '+d.msg);
    return;
  }
  // progress row
  const gen = d.gen;
  const pct = Math.round(gen/totalGen*100);
  document.getElementById('prog-bar').style.width=pct+'%';
  document.getElementById('prog-label').textContent=`Génération ${gen} / ${totalGen}`;
  const log = document.getElementById('log');
  log.textContent += `gén ${String(gen).padStart(3)} | f1=${d.f1_min.toFixed(0)} f2=${d.f2_min.toFixed(2)} f3=${d.f3_min.toFixed(2)} | sans conflit: ${d.valid}/${d.pop_size}\n`;
  log.scrollTop = log.scrollHeight;
}

function showResults(d){
  document.getElementById('progress-wrap').style.display='none';
  document.getElementById('results-wrap').style.display='block';

  document.getElementById('m-f1').textContent = d.f1.toFixed(0);
  document.getElementById('m-f2').textContent = d.f2.toFixed(2);
  document.getElementById('m-f3').textContent = d.f3.toFixed(2);
  document.getElementById('img-pareto').src = 'data:image/png;base64,'+d.img_pareto;
  document.getElementById('img-evol').src   = 'data:image/png;base64,'+d.img_evol;

  // Timetable tabs per group
  const sel = document.getElementById('tt-selector');
  sel.innerHTML='';
  const content = document.getElementById('tt-content');
  content.innerHTML='';
  d.timetables.forEach((tt,i)=>{
    const btn=document.createElement('button');
    btn.className='tab'+(i===0?' active':'');
    btn.textContent=tt.groupe;
    btn.onclick=function(){
      sel.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      content.querySelectorAll('.tt-panel').forEach(p=>p.style.display='none');
      content.querySelector('#tt-'+i).style.display='block';
    };
    sel.appendChild(btn);
    const panel=document.createElement('div');
    panel.className='tt-panel';
    panel.id='tt-'+i;
    panel.style.display=i===0?'block':'none';
    panel.innerHTML='<div class="tt-wrap">'+buildTable(tt)+'</div>';
    content.appendChild(panel);
  });

  // Pareto front
  document.getElementById('front-table').innerHTML = buildFrontTable(d.pareto_solutions);
}

function buildTable(tt){
  let html='<table><thead><tr><th>Créneau</th>';
  tt.jours.forEach(j=>html+=`<th>${j}</th>`);
  html+='</tr></thead><tbody>';
  tt.slots.forEach(slot=>{
    html+=`<tr><td>${slot}</td>`;
    tt.jours.forEach(j=>{
      const cell=(tt.grid[slot]||{})[j]||'';
      const cls=cell===''?'empty':cell.includes('/')?' conflict':'occupied';
      html+=`<td class="${cls}">${cell||'–'}</td>`;
    });
    html+='</tr>';
  });
  html+='</tbody></table>';
  return html;
}

function buildFrontTable(solutions){
  if(!solutions||!solutions.length) return '<p>Aucune solution.</p>';
  let html='<table><thead><tr><th>#</th><th>f1 Conflits</th><th>f2 Heures creuses</th><th>f3 Salles</th><th>Valide</th><th>Meilleur</th></tr></thead><tbody>';
  solutions.forEach((s,i)=>{
    html+=`<tr><td>${i+1}</td><td>${s.f1.toFixed(2)}</td><td>${s.f2.toFixed(2)}</td><td>${s.f3.toFixed(2)}</td>
      <td>${s.valid?'✅':'❌'}</td><td>${s.best?'⭐':'–'}</td></tr>`;
  });
  html+='</tbody></table>';
  return html;
}

function arreter(){
  fetch('/stop',{method:'POST'});
  if(evtSource) evtSource.close();
  document.getElementById('progress-wrap').style.display='none';
}
</script>
</body>
</html>
"""

# ═══════════════════════════════════════════════════════════════════════════════
# ROUTES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    # Données par défaut pour le formulaire
    default_groupes  = list(C.GROUPES.items())
    default_salles   = list(C.SALLES.items())
    default_ens      = [(e, ", ".join(C.JOURS[j][:3] for j in C.JOURS_DISPO.get(e,[])))
                        for e in C.ENSEIGNANTS]
    default_matieres = C.MATIERES
    all_jours        = list(C.CRENEAUX_PAR_JOUR.keys())
    default_jours    = [j for j in all_jours if j in C.JOURS]

    return render_template_string(
        HTML,
        all_jours=all_jours,
        default_jours=default_jours,
        default_groupes=default_groupes,
        default_salles=default_salles,
        default_ens=default_ens,
        default_matieres=default_matieres,
    )


@app.route("/run", methods=["POST"])
def run():
    global _run_state
    if _run_state["running"]:
        return jsonify({"error": "Une optimisation est déjà en cours. Attendez ou arrêtez-la."})

    data = request.get_json()
    # flush queue
    while not _progress_queue.empty():
        try: _progress_queue.get_nowait()
        except: pass

    _run_state = {"running": True, "result": None, "error": None}

    def worker():
        global _run_state
        try:
            _apply_config(data)
            from population import population_initiale
            from evaluation import evaluer_population
            from nsga2 import nsga2
            from resultats import (extraire_front, meilleur_compromis,
                                   construire_tableau_front, exporter_resultats)
            from visualisation import tracer_front, tracer_evolution
            from affichage import tableau_groupe, liste_seances

            pop_size = C.TAILLE_POPULATION
            n_gen    = C.N_GENERATIONS

            pop0 = population_initiale(pop_size)
            F0   = evaluer_population(pop0)

            def cb(gen, row):
                if not _run_state["running"]:
                    raise InterruptedError("Arrêté par l'utilisateur")
                _progress_queue.put({
                    "type":    "progress",
                    "gen":     gen,
                    "f1_min":  row["f1 min"],
                    "f2_min":  row["f2 min"],
                    "f3_min":  row["f3 min"],
                    "valid":   row["solutions sans conflit"],
                    "pop_size": pop_size,
                })

            pop, F, hist = nsga2(pop_init=[p.copy() for p in pop0],
                                 verbose=False, progress_callback=cb)

            solutions = extraire_front(pop, F)
            k_best    = meilleur_compromis(solutions)
            front_df  = construire_tableau_front(solutions, k_best)
            meilleur, f_meilleur = solutions[k_best]

            # Save CSV + PNG to project folder
            exporter_resultats(hist, front_df, meilleur, dossier=DOSSIER)
            tracer_front(F0, solutions, k_best,
                         fichier=os.path.join(DOSSIER, "front_pareto.png"))
            tracer_evolution(hist,
                             fichier=os.path.join(DOSSIER, "evolution_objectifs.png"))

            # Encode charts to base64
            img_pareto = _img_to_b64(os.path.join(DOSSIER, "front_pareto.png"))
            img_evol   = _img_to_b64(os.path.join(DOSSIER, "evolution_objectifs.png"))

            # Build timetable grids per group
            timetables = []
            for g in range(C.N_GRP):
                grille = tableau_groupe(meilleur, g)
                # Collect all slot labels (rows)
                all_slots = []
                for j, jour in enumerate(C.JOURS):
                    for lbl in C.CRENEAUX_PAR_JOUR.get(jour, []):
                        if lbl not in all_slots:
                            all_slots.append(lbl)
                grid_dict = {}
                for slot in all_slots:
                    grid_dict[slot] = {}
                    if slot in grille.index:
                        for jour in C.JOURS:
                            if jour in grille.columns:
                                grid_dict[slot][jour] = str(grille.loc[slot, jour])
                timetables.append({
                    "groupe": C.GRP_NOMS[g],
                    "jours":  C.JOURS,
                    "slots":  all_slots,
                    "grid":   grid_dict,
                })

            # Pareto solutions list
            pareto_solutions = [
                {
                    "f1": float(f[0]), "f2": float(f[1]), "f3": float(f[2]),
                    "valid": bool(f[0] == 0),
                    "best":  k == k_best,
                }
                for k, (_, f) in enumerate(solutions)
            ]

            result = {
                "type":      "done",
                "f1":        float(f_meilleur[0]),
                "f2":        float(f_meilleur[1]),
                "f3":        float(f_meilleur[2]),
                "img_pareto": img_pareto,
                "img_evol":   img_evol,
                "timetables": timetables,
                "pareto_solutions": pareto_solutions,
            }
            _run_state["result"] = result
            _progress_queue.put(result)

        except InterruptedError:
            _progress_queue.put({"type": "error", "msg": "Optimisation arrêtée."})
        except Exception as ex:
            import traceback
            msg = traceback.format_exc()
            _progress_queue.put({"type": "error", "msg": str(ex), "trace": msg})
            print(msg)
        finally:
            _run_state["running"] = False

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/progress")
def progress():
    """Server-Sent Events endpoint."""
    def stream():
        while True:
            try:
                item = _progress_queue.get(timeout=30)
                yield f"data: {json.dumps(item)}\n\n"
                if item.get("type") in ("done", "error"):
                    break
            except queue.Empty:
                yield "data: {\"type\":\"ping\"}\n\n"
    return Response(stream(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache",
                             "X-Accel-Buffering": "no"})


@app.route("/stop", methods=["POST"])
def stop():
    _run_state["running"] = False
    return jsonify({"ok": True})


@app.route("/download/<filename>")
def download(filename):
    path = os.path.join(DOSSIER, filename)
    if not os.path.exists(path):
        return "Fichier non trouvé – lancez d'abord l'optimisation.", 404
    return send_file(path, as_attachment=True)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def _apply_config(data):
    """Traduit le JSON du formulaire en appel configure()."""
    # Jours
    jours = data.get("jours", list(C.CRENEAUX_PAR_JOUR.keys()))

    # Groupes
    groupes = {}
    for nom, eff in data.get("groupes", []):
        try: groupes[nom] = int(eff)
        except: pass

    # Salles
    salles = {}
    for nom, cap in data.get("salles", []):
        try: salles[nom] = int(cap)
        except: pass

    # Enseignants + disponibilités
    enseignants  = []
    jours_dispo  = {}
    all_jours    = list(C.CRENEAUX_PAR_JOUR.keys())
    for nom, dispo_str in data.get("ens", []):
        nom = nom.strip()
        if not nom:
            continue
        enseignants.append(nom)
        # Parse dispo: "Lun,Mar" → match to full JOURS names
        abbrevs = [s.strip() for s in dispo_str.replace(";", ",").split(",") if s.strip()]
        idx_list = []
        for ab in abbrevs:
            for ji, j in enumerate(jours):
                if j.lower().startswith(ab.lower()[:3]):
                    idx_list.append(ji)
                    break
        jours_dispo[nom] = idx_list if idx_list else list(range(len(jours)))

    # Matières
    matieres = []
    for row in data.get("matieres", []):
        nom, ens, duree, mode = row
        try: duree = int(duree)
        except: duree = 1
        matieres.append((nom, ens, duree, mode))

    # Algorithme
    taille_pop  = int(data.get("pop", 100))
    n_gen       = int(data.get("gen", 400))
    seed        = int(data.get("seed", 42))
    dominance   = bool(data.get("dominance", True))

    C.configure(
        groupes=groupes,
        salles=salles,
        enseignants=enseignants,
        jours_dispo=jours_dispo,
        matieres=matieres,
        jours=jours,
        taille_pop=taille_pop,
        n_gen=n_gen,
        seed=seed,
        dominance_contrainte=dominance,
    )


def _img_to_b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 60)
    print("  MOGA Timetabling – Interface Web")
    print("  Ouvrez : http://localhost:5000")
    print("=" * 60)
    app.run(debug=False, threaded=True, port=5000)
