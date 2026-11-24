# -*- coding: utf-8 -*-
"""
app.py -- Simplified Flask Web Interface for Pure NSGA-II Timetabling.

Uses simple_moga.py (pure Python stdlib solver) + Flask + SSE streaming.
No NumPy, Pandas, or Matplotlib required.

Run with:
    python app.py
Open in browser:
    http://localhost:5000
"""

from __future__ import annotations

import json
import os
import queue
import sys
import threading

from flask import Flask, Response, jsonify, render_template_string, request, send_file

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import simple_moga as sm

app = Flask(__name__)
_progress_queue: queue.Queue = queue.Queue()
_stop_event = threading.Event()
_state_lock = threading.Lock()
_is_running = False

CSV_PATH = os.path.join(HERE, "emploi_du_temps_simple.csv")

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Simple MOGA Timetabling (Pure NSGA-II)</title>
<style>
  :root{--blue:#2563eb;--bg:#f8fafc;--card:#ffffff;--border:#e2e8f0;--text:#0f172a;--sub:#475569;--green:#16a34a;--red:#dc2626;}
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;background:var(--bg);color:var(--text);font-size:14px;line-height:1.4}
  header{background:#1e3a5f;color:#fff;padding:16px 28px;display:flex;justify-content:space-between;align-items:center}
  header h1{font-size:1.25rem}
  header span{font-size:.82rem;opacity:.85}
  main{max-width:1280px;margin:20px auto;padding:0 16px;display:grid;grid-template-columns:360px 1fr;gap:18px}
  @media(max-width:900px){main{grid-template-columns:1fr}}
  .card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:16px}
  .card h2{font-size:1rem;margin-bottom:12px;color:#1e3a5f}
  label{display:block;font-size:.8rem;color:var(--sub);margin:8px 0 3px}
  input,textarea{width:100%;padding:7px 9px;border:1px solid var(--border);border-radius:6px;font:inherit;font-size:.85rem}
  textarea{font-family:ui-monospace,Consolas,monospace;resize:vertical}
  .row2{display:grid;grid-template-columns:1fr 1fr;gap:8px}
  .btn-row{display:flex;gap:8px;margin-top:14px}
  button{cursor:pointer;border:0;border-radius:7px;padding:9px 14px;font-weight:600;font-size:.88rem}
  .btn-primary{background:var(--blue);color:#fff;flex:1}
  .btn-stop{background:#fee2e2;color:var(--red)}
  .btn-dl{background:#dcfce7;color:var(--green);text-decoration:none;display:inline-block;padding:8px 12px;border-radius:7px;font-weight:600;font-size:.85rem}
  .bar-wrap{background:#e2e8f0;border-radius:999px;height:12px;overflow:hidden;margin:8px 0}
  .bar{height:100%;background:var(--blue);width:0%;transition:width .15s}
  pre#log{background:#0f172a;color:#e2e8f0;padding:10px;border-radius:7px;height:130px;overflow:auto;font-size:.78rem}
  .metrics{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-bottom:14px}
  .metric{background:#f1f5f9;border-radius:8px;padding:10px;text-align:center}
  .metric .val{font-size:1.3rem;font-weight:700;color:var(--blue)}
  .metric .lbl{font-size:.75rem;color:var(--sub)}
  .tabs{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px}
  .tab{background:#e2e8f0;color:var(--text);padding:6px 12px;border-radius:6px;font-size:.82rem}
  .tab.active{background:var(--blue);color:#fff}
  table{width:100%;border-collapse:collapse;font-size:.78rem}
  th,td{border:1px solid var(--border);padding:6px 7px;text-align:center}
  th{background:#f1f5f9}
  td.busy{background:#eff6ff;color:#1d4ed8;font-weight:500}
  td.conflict{background:#fee2e2;color:var(--red);font-weight:700}
  td.off{background:#f8fafc;color:#94a3b8}
  svg{width:100%;height:180px;background:#f8fafc;border:1px solid var(--border);border-radius:8px}
</style>
</head>
<body>
<header>
  <div>
    <h1>Simple MOGA Timetabling</h1>
    <span>Pure NSGA-II (No MRV, No G-MOGA)</span>
  </div>
  <span id="status-badge">Ready</span>
</header>

<main>
  <section class="card">
    <h2>1. Problem & Algorithm Settings</h2>
    <div class="row2">
      <div><label>Population</label><input id="pop" type="number" value="100" min="10"></div>
      <div><label>Generations</label><input id="gens" type="number" value="400" min="1"></div>
    </div>
    <div class="row2">
      <div><label>Mutation Rate</label><input id="mut" type="number" step="0.01" value="0.08" min="0" max="1"></div>
      <div><label>Seed</label><input id="seed" type="number" value="42"></div>
    </div>

    <label>Groups (name:size per line)</label>
    <textarea id="groups" rows="3">{{ groups_txt }}</textarea>

    <label>Rooms (name:capacity per line)</label>
    <textarea id="rooms" rows="5">{{ rooms_txt }}</textarea>

    <label>Teachers & Available Days (name:0,1,2... per line; 0=Lundi..5=Samedi)</label>
    <textarea id="teachers" rows="5">{{ teachers_txt }}</textarea>

    <label>Courses (name, teacher, duration, ensemble|séparé per line)</label>
    <textarea id="courses" rows="9">{{ courses_txt }}</textarea>

    <div class="btn-row">
      <button class="btn-primary" onclick="startRun()">Run Pure NSGA-II</button>
      <button class="btn-stop" onclick="stopRun()">Stop</button>
    </div>
  </section>

  <section>
    <div class="card" id="progress-card" style="display:none">
      <h2>Live Evolution</h2>
      <div id="prog-text">Starting...</div>
      <div class="bar-wrap"><div class="bar" id="prog-bar"></div></div>
      <pre id="log"></pre>
    </div>

    <div class="card" id="results-card" style="display:none">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h2 style="margin:0">2. Ultimate Solution & Pareto Front</h2>
        <a class="btn-dl" href="/download/schedule">Download CSV</a>
      </div>

      <div class="metrics">
        <div class="metric"><div class="val" id="m-f1">-</div><div class="lbl">f1 Hard Conflicts</div></div>
        <div class="metric"><div class="val" id="m-f2">-</div><div class="lbl">f2 Student Comfort</div></div>
        <div class="metric"><div class="val" id="m-f3">-</div><div class="lbl">f3 Room Fit</div></div>
      </div>

      <h3 style="font-size:.9rem;margin:10px 0 6px">Convergence (Best f1, f2, f3 per Generation)</h3>
      <svg id="chart" viewBox="0 0 600 180"></svg>

      <h3 style="font-size:.9rem;margin:14px 0 6px">Weekly Timetable</h3>
      <div class="tabs" id="group-tabs"></div>
      <div id="group-grids"></div>

      <h3 style="font-size:.9rem;margin:14px 0 6px">Pareto Front 0</h3>
      <div id="front-table"></div>
    </div>
  </section>
</main>

<script>
let evtSource = null;
let totalGens = 400;

function startRun(){
  const payload = {
    pop: Number(document.getElementById('pop').value),
    gens: Number(document.getElementById('gens').value),
    mut: Number(document.getElementById('mut').value),
    seed: Number(document.getElementById('seed').value),
    groups: document.getElementById('groups').value,
    rooms: document.getElementById('rooms').value,
    teachers: document.getElementById('teachers').value,
    courses: document.getElementById('courses').value,
  };
  totalGens = payload.gens;
  document.getElementById('progress-card').style.display = 'block';
  document.getElementById('results-card').style.display = 'none';
  document.getElementById('log').textContent = '';
  document.getElementById('prog-bar').style.width = '0%';
  document.getElementById('status-badge').textContent = 'Running...';

  fetch('/run', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(payload)
  }).then(r => r.json()).then(res => {
    if (res.error) { alert(res.error); return; }
    if (evtSource) evtSource.close();
    evtSource = new EventSource('/progress');
    evtSource.onmessage = e => {
      const msg = JSON.parse(e.data);
      if (msg.type === 'progress') {
        const pct = Math.round((msg.gen / totalGens) * 100);
        document.getElementById('prog-bar').style.width = pct + '%';
        document.getElementById('prog-text').textContent =
          `Generation ${msg.gen} / ${totalGens} (${pct}%) — valid: ${msg.valid}/${payload.pop}`;
        if (msg.gen === 0 || msg.gen === 1 || msg.gen % 25 === 0 || msg.gen === totalGens) {
          const log = document.getElementById('log');
          log.textContent += `gen ${String(msg.gen).padStart(3)} | valid=${msg.valid}/${payload.pop} | f1=${msg.f1_min} f2=${msg.f2_min.toFixed(2)} f3=${msg.f3_min.toFixed(2)}\n`;
          log.scrollTop = log.scrollHeight;
        }
      } else if (msg.type === 'done') {
        evtSource.close();
        document.getElementById('status-badge').textContent = 'Done';
        renderResults(msg);
      } else if (msg.type === 'error') {
        evtSource.close();
        document.getElementById('status-badge').textContent = 'Stopped / Error';
        alert(msg.msg);
      }
    };
  });
}

function stopRun(){
  fetch('/stop', {method: 'POST'});
  if (evtSource) evtSource.close();
  document.getElementById('status-badge').textContent = 'Stopped';
}

function renderResults(d){
  document.getElementById('results-card').style.display = 'block';
  document.getElementById('m-f1').textContent = d.best.f1;
  document.getElementById('m-f2').textContent = d.best.f2.toFixed(2);
  document.getElementById('m-f3').textContent = d.best.f3.toFixed(2);
  drawChart(d.history);

  const tabs = document.getElementById('group-tabs');
  const grids = document.getElementById('group-grids');
  tabs.innerHTML = '';
  grids.innerHTML = '';
  d.timetables.forEach((tt, idx) => {
    const btn = document.createElement('button');
    btn.className = 'tab' + (idx === 0 ? ' active' : '');
    btn.textContent = `${tt.group} (${tt.size})`;
    btn.onclick = () => {
      tabs.querySelectorAll('.tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      grids.querySelectorAll('.gpanel').forEach((p, pi) => p.style.display = pi === idx ? 'block' : 'none');
    };
    tabs.appendChild(btn);

    const panel = document.createElement('div');
    panel.className = 'gpanel';
    panel.style.display = idx === 0 ? 'block' : 'none';
    let html = '<table><thead><tr><th>Slot</th>' + tt.days.map(day => `<th>${day}</th>`).join('') + '</tr></thead><tbody>';
    tt.slots.forEach(slot => {
      html += `<tr><td><strong>${slot}</strong></td>`;
      tt.days.forEach(day => {
        const val = tt.grid[slot][day];
        if (val === null) html += '<td class="off">---</td>';
        else if (val === '') html += '<td>.</td>';
        else if (val.includes(' / ')) html += `<td class="conflict">${val}</td>`;
        else html += `<td class="busy">${val}</td>`;
      });
      html += '</tr>';
    });
    html += '</tbody></table>';
    panel.innerHTML = html;
    grids.appendChild(panel);
  });

  let fhtml = '<table><thead><tr><th>#</th><th>f1</th><th>f2</th><th>f3</th><th>Valid</th><th>Ultimate</th></tr></thead><tbody>';
  d.pareto_solutions.forEach((s, i) => {
    fhtml += `<tr><td>${i+1}</td><td>${s.f1}</td><td>${s.f2.toFixed(3)}</td><td>${s.f3.toFixed(3)}</td><td>${s.valid ? 'Yes' : 'No'}</td><td>${s.best ? '★' : ''}</td></tr>`;
  });
  fhtml += '</tbody></table>';
  document.getElementById('front-table').innerHTML = fhtml;
}

function drawChart(history){
  const svg = document.getElementById('chart');
  if (!history || history.length < 2) { svg.innerHTML = ''; return; }
  const W = 600, H = 180, P = 24;
  const maxGen = history[history.length - 1].gen || 1;
  const series = [
    {key: 'f1_min', color: '#dc2626', label: 'f1'},
    {key: 'f2_min', color: '#2563eb', label: 'f2'},
    {key: 'f3_min', color: '#16a34a', label: 'f3'},
  ];
  const maxVal = Math.max(1, ...history.flatMap(r => [r.f1_min, r.f2_min, r.f3_min]));
  let out = '';
  series.forEach((s, si) => {
    const pts = history.map(r => {
      const x = P + (r.gen / maxGen) * (W - 2 * P);
      const y = H - P - (r[s.key] / maxVal) * (H - 2 * P);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
    out += `<polyline fill="none" stroke="${s.color}" stroke-width="2" points="${pts}"/>`;
    out += `<text x="${P + si * 55}" y="15" fill="${s.color}" font-size="11" font-weight="bold">${s.label}</text>`;
  });
  svg.innerHTML = out;
}
</script>
</body>
</html>
"""


def _default_form_texts() -> dict[str, str]:
    groups_txt = "\n".join(f"{k}:{v}" for k, v in sm.GROUPS.items())
    rooms_txt = "\n".join(f"{name}:{cap}" for name, cap in sm.ROOMS)
    teachers_txt = "\n".join(
        f"{t}:{','.join(str(d) for d in sorted(days))}"
        for t, days in sm.TEACHER_DAYS.items()
    )
    courses_txt = "\n".join(f"{n}, {t}, {d}, {m}" for n, t, d, m in sm.COURSES)
    return {
        "groups_txt": groups_txt,
        "rooms_txt": rooms_txt,
        "teachers_txt": teachers_txt,
        "courses_txt": courses_txt,
    }


def _parse_payload(data: dict) -> dict:
    groups = {}
    for line in data.get("groups", "").splitlines():
        if ":" in line:
            name, size = line.split(":", 1)
            groups[name.strip()] = int(size.strip())

    rooms = []
    for line in data.get("rooms", "").splitlines():
        if ":" in line:
            name, cap = line.split(":", 1)
            rooms.append((name.strip(), int(cap.strip())))

    teacher_days = {}
    for line in data.get("teachers", "").splitlines():
        if ":" in line:
            name, days_raw = line.split(":", 1)
            idx_set = {int(x.strip()) for x in days_raw.split(",") if x.strip().isdigit()}
            teacher_days[name.strip()] = idx_set or set(range(len(sm.DAYS)))

    courses = []
    for line in data.get("courses", "").splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 4:
            courses.append((parts[0], parts[1], int(parts[2]), parts[3]))

    return {
        "pop": int(data.get("pop", 100)),
        "gens": int(data.get("gens", 400)),
        "mut": float(data.get("mut", 0.08)),
        "seed": int(data.get("seed", 42)),
        "groups": groups or dict(sm.GROUPS),
        "rooms": rooms or list(sm.ROOMS),
        "teacher_days": teacher_days or {k: set(v) for k, v in sm.TEACHER_DAYS.items()},
        "courses": courses or list(sm.COURSES),
    }


def _build_timetables_json(
    timetable: sm.Timetable,
    sessions: list[sm.Session],
    groups: dict[str, int],
    rooms: list[tuple[str, int]],
) -> list[dict]:
    all_slots = sorted({lbl for d in sm.DAYS for lbl in sm.SLOTS_PER_DAY[d]})
    out = []
    for group_name, group_size in groups.items():
        grid = {
            slot: {day: ("" if slot in sm.SLOTS_PER_DAY[day] else None) for day in sm.DAYS}
            for slot in all_slots
        }
        for session, (day_idx, start_p, room_idx) in zip(sessions, timetable):
            if group_name not in session.groups:
                continue
            day_name = sm.DAYS[day_idx]
            room_name = rooms[room_idx][0]
            label = f"{session.name} ({session.teacher}, {room_name})"
            for dt in range(session.duration):
                slot_lbl = sm.SLOTS_PER_DAY[day_name][start_p + dt]
                prev = grid[slot_lbl][day_name]
                grid[slot_lbl][day_name] = label if not prev else f"{prev} / {label}"
        out.append({
            "group": group_name,
            "size": group_size,
            "days": sm.DAYS,
            "slots": all_slots,
            "grid": grid,
        })
    return out


@app.route("/")
def index():
    return render_template_string(HTML, **_default_form_texts())


@app.route("/run", methods=["POST"])
def run():
    global _is_running
    with _state_lock:
        if _is_running:
            return jsonify({"error": "An optimization is already running."}), 409
        _is_running = True
        _stop_event.clear()

    while not _progress_queue.empty():
        try:
            _progress_queue.get_nowait()
        except queue.Empty:
            break

    cfg = _parse_payload(request.get_json(force=True) or {})

    def worker() -> None:
        global _is_running
        try:
            def on_progress(gen: int, row: dict) -> None:
                _progress_queue.put({"type": "progress", **row})

            pareto_front, best_idx, history = sm.solve(
                pop_size=cfg["pop"],
                n_generations=cfg["gens"],
                seed=cfg["seed"],
                p_mut=cfg["mut"],
                verbose=False,
                groups=cfg["groups"],
                rooms=cfg["rooms"],
                teacher_days=cfg["teacher_days"],
                courses=cfg["courses"],
                progress_callback=on_progress,
                should_stop=_stop_event.is_set,
            )

            sessions = sm.build_sessions(courses=cfg["courses"], groups=cfg["groups"])
            best_tt, best_sc = pareto_front[best_idx]
            sm.export_schedule_csv(best_tt, sessions, CSV_PATH, rooms=cfg["rooms"])

            _progress_queue.put({
                "type": "done",
                "best": {"f1": best_sc[0], "f2": best_sc[1], "f3": best_sc[2]},
                "history": history,
                "timetables": _build_timetables_json(
                    best_tt, sessions, cfg["groups"], cfg["rooms"]
                ),
                "pareto_solutions": [
                    {
                        "f1": sc[0],
                        "f2": sc[1],
                        "f3": sc[2],
                        "valid": sc[0] == 0,
                        "best": idx == best_idx,
                    }
                    for idx, (_, sc) in enumerate(pareto_front)
                ],
            })
        except InterruptedError as ex:
            _progress_queue.put({"type": "error", "msg": str(ex)})
        except Exception as ex:
            _progress_queue.put({"type": "error", "msg": str(ex)})
        finally:
            with _state_lock:
                _is_running = False

    threading.Thread(target=worker, daemon=True).start()
    return jsonify({"ok": True})


@app.route("/progress")
def progress():
    def stream():
        while True:
            try:
                item = _progress_queue.get(timeout=30)
                yield f"data: {json.dumps(item)}\n\n"
                if item.get("type") in ("done", "error"):
                    break
            except queue.Empty:
                yield 'data: {"type":"ping"}\n\n'

    return Response(stream(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})


@app.route("/stop", methods=["POST"])
def stop():
    _stop_event.set()
    return jsonify({"ok": True})


@app.route("/download/schedule")
def download_schedule():
    if not os.path.exists(CSV_PATH):
        return "Run an optimization first.", 404
    return send_file(CSV_PATH, as_attachment=True)


if __name__ == "__main__":
    print("=" * 60)
    print("  Simple MOGA Timetabling -- Web Version")
    print("  Open: http://localhost:5000")
    print("=" * 60)
    app.run(debug=False, threaded=True, port=5000)
