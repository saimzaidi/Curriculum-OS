"""Offline course pack export functionality."""
from __future__ import annotations

import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from typing import Any

from ..db import connect
from ..errors import DomainError
from . import common
from .common import dump, load, new_id, now, require_course, row, rows
from .scheduling import get_schedule


def create_offline_export(course_id: str, version_id: str | None = None) -> dict[str, Any]:
    course = require_course(course_id)
    schedule = get_schedule(course_id, version_id)
    with connect() as conn:
        lessons = rows(conn.execute("SELECT * FROM lessons WHERE course_id=?", (course_id,)).fetchall())
        assessments = rows(conn.execute("SELECT * FROM assessments WHERE course_id=?", (course_id,)).fetchall())
    lesson_data = [{"id": item["id"], "schedule_entry_id": item["schedule_entry_id"], "content": load(item["content_json"])} for item in lessons]
    assessment_data = [{"id": item["id"], "content": load(item["content_json"]), "approved": bool(item["approved"])} for item in assessments]
    export_id = new_id()
    export_dir = common.EXPORT_DIR / export_id
    if export_dir.exists():
        shutil.rmtree(export_dir)
    (export_dir / "data").mkdir(parents=True)
    (export_dir / "app").mkdir()
    payloads = {"data/course.json": course, "data/schedule.json": schedule, "data/lessons.json": lesson_data, "data/assessments.json": assessment_data}
    for relative, payload in payloads.items():
        (export_dir / relative).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    pack_data = {"course": course, "schedule": schedule, "lessons": lesson_data, "assessments": assessment_data}
    (export_dir / "app/styles.css").write_text("body{font-family:Arial,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;color:#111}header{display:flex;justify-content:space-between;align-items:center;border-bottom:2px solid #111}input,button{padding:.45rem}.entry{border-bottom:1px solid #999;padding:.65rem 0}.meta{color:#444;font-size:.9rem}@media print{button,input{display:none}header{border:0}}", encoding="utf-8")
    (export_dir / "app/app.js").write_text("const pack=window.__PACK__,esc=value=>String(value??'').replace(/[&<>\\\"]/g,char=>({'&':'&amp;','<':'&lt;','>':'&gt;','\\\"':'&quot;'}[char]));document.title=pack.course.name;title.textContent=pack.course.name;const render=q=>{const needle=q.toLowerCase(),matches=value=>String(value??'').toLowerCase().includes(needle),entries=pack.schedule.entries;schedule.innerHTML=entries.filter(e=>matches(`${e.session_date} ${e.concept_title||e.kind}`)).map(e=>`<div class=entry><b>${esc(e.session_date)}</b> ${esc(e.concept_title||e.kind)}<div class=meta>${esc(e.kind)}${e.locked?' · locked':''}</div></div>`).join('')||'<p>No matching schedule items.</p>';lessons.innerHTML=pack.lessons.filter(l=>matches(`${l.content.title} ${l.content.objectives.join(' ')}`)).map(l=>`<article class=entry><h3>${esc(l.content.title)}</h3><p>${l.content.objectives.map(esc).join('; ')}</p><p class=meta>Sources: ${l.content.source_block_ids.map(esc).join(', ')}</p></article>`).join('')||'<p>No matching lessons.</p>';assessments.innerHTML=pack.assessments.filter(a=>matches(`${a.content.title} ${a.content.items.map(item=>item.question).join(' ')}`)).map(a=>`<article class=entry><h3>${esc(a.content.title)}</h3><p>${a.content.items.length} source-grounded item(s)</p></article>`).join('')||'<p>No matching assessments.</p>';};search.oninput=e=>render(e.target.value);render('');", encoding="utf-8")
    (export_dir / "app/service-worker.js").write_text("self.addEventListener('install',event=>event.waitUntil(self.skipWaiting()));self.addEventListener('activate',event=>event.waitUntil(self.clients.claim()));", encoding="utf-8")
    serialized_pack = json.dumps(pack_data, separators=(",", ":")).replace("<", "\\u003c")
    (export_dir / "index.html").write_text(f"<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><link rel='stylesheet' href='app/styles.css'><title>CurriculumOS Pack</title></head><body><header><div><p class='meta'>OFFLINE COURSE PACK</p><h1 id='title'>Course pack</h1></div><button onclick='print()'>Print</button></header><p><input id='search' placeholder='Search schedule or concepts'></p><h2>Schedule</h2><div id='schedule'></div><h2>Lessons</h2><div id='lessons'></div><h2>Assessments</h2><div id='assessments'></div><script>window.__PACK__={serialized_pack};if('serviceWorker' in navigator&&location.protocol!=='file:')navigator.serviceWorker.register('app/service-worker.js');</script><script src='app/app.js'></script></body></html>", encoding="utf-8")
    manifest = {str(path.relative_to(export_dir)).replace("\\", "/"): hashlib.sha256(path.read_bytes()).hexdigest() for path in export_dir.rglob("*") if path.is_file()}
    (export_dir / "MANIFEST.json").write_text(json.dumps({"export_version": 1, "created_at": now(), "checksums": manifest}, indent=2), encoding="utf-8")
    zip_path = common.EXPORT_DIR / f"{export_id}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in export_dir.rglob("*"):
            if file.is_file():
                archive.write(file, file.relative_to(export_dir))
    with connect() as conn:
        conn.execute("INSERT INTO exports VALUES(?,?,?,?,?,?)", (export_id, course_id, schedule["version"]["id"], str(zip_path), dump(manifest), now()))
    return {"id": export_id, "file_path": str(zip_path), "manifest": manifest}


def export_path(export_id: str) -> Path:
    with connect() as conn:
        record = row(conn.execute("SELECT * FROM exports WHERE id=?", (export_id,)).fetchone())
    if not record or not Path(record["file_path"]).is_file():
        raise DomainError("EXPORT_NOT_FOUND", "Export was not found.", status_code=404)
    return Path(record["file_path"])


def export_course_id(export_id: str) -> str:
    with connect() as conn:
        record = row(conn.execute("SELECT course_id FROM exports WHERE id=?", (export_id,)).fetchone())
    if not record:
        raise DomainError("EXPORT_NOT_FOUND", "Export was not found.", status_code=404)
    return record["course_id"]
