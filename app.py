#!/usr/bin/env python3
"""Flask web frontend for the Honimunn scraper."""
from __future__ import annotations

import asyncio
import csv
import io
import json
import os
import re
import threading
import uuid
import zipfile
from queue import Queue, Empty

from flask import Flask, render_template, request, jsonify, Response, send_from_directory

from config import DEFAULT_CONCURRENCY
from main import run_with_progress
from scraper.url_parser import extract_itinerary_id

app = Flask(__name__)

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

_jobs: dict[str, dict] = {}

URL_PATTERN = re.compile(r"https?://destino\.honimunn\.com/Itinerary/\w+/[\w-]+")


def _validate_urls(raw: list[str]) -> tuple[list[str], list[str]]:
    valid, invalid = [], []
    for url in raw:
        url = url.strip()
        if not url:
            continue
        try:
            extract_itinerary_id(url)
            valid.append(url)
        except ValueError:
            invalid.append(url)
    return valid, invalid


def _run_scrape_thread(job_id: str, urls: list[str]):
    job = _jobs[job_id]
    queue: Queue = job["queue"]
    pause_event: threading.Event = job["pause_event"]

    def on_progress(msg: str, current: int, total: int):
        queue.put({"type": "progress", "message": msg, "current": current, "total": total})

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results, consolidated = loop.run_until_complete(
            run_with_progress(urls, OUTPUT_DIR, DEFAULT_CONCURRENCY, on_progress, pause_event)
        )
        job["results"] = results
        queue.put({
            "type": "done",
            "results": results,
            "consolidated": consolidated,
        })
    except Exception as e:
        queue.put({"type": "error", "message": str(e)})
    finally:
        loop.close()
        job["running"] = False


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/scrape", methods=["POST"])
def scrape():
    urls: list[str] = []

    # JSON body with URLs
    if request.is_json:
        data = request.get_json()
        urls = data.get("urls", [])
    else:
        # Check for textarea URLs
        text_urls = request.form.get("urls", "")
        if text_urls:
            urls = [u.strip() for u in text_urls.splitlines() if u.strip()]

        # Check for uploaded CSV
        csv_file = request.files.get("csv_file")
        if csv_file and csv_file.filename:
            content = csv_file.read().decode("utf-8")
            reader = csv.DictReader(io.StringIO(content))
            for row in reader:
                url = row.get("url", "").strip()
                if url:
                    urls.append(url)

    if not urls:
        return jsonify({"error": "No se proporcionaron URLs"}), 400

    valid, invalid = _validate_urls(urls)
    if not valid:
        return jsonify({"error": "Ninguna URL es valida", "invalid": invalid}), 400

    job_id = str(uuid.uuid4())[:8]
    pause_event = threading.Event()
    pause_event.set()  # starts unpaused
    _jobs[job_id] = {
        "queue": Queue(),
        "running": True,
        "urls": valid,
        "pause_event": pause_event,
        "results": [],
    }

    thread = threading.Thread(target=_run_scrape_thread, args=(job_id, valid), daemon=True)
    thread.start()

    return jsonify({
        "job_id": job_id,
        "url_count": len(valid),
        "invalid": invalid,
    })


@app.route("/progress/<job_id>")
def progress(job_id: str):
    if job_id not in _jobs:
        return jsonify({"error": "Job not found"}), 404

    def generate():
        queue: Queue = _jobs[job_id]["queue"]
        while True:
            try:
                event = queue.get(timeout=30)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") in ("done", "error"):
                    break
            except Empty:
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"
                if not _jobs[job_id]["running"]:
                    break

    return Response(generate(), mimetype="text/event-stream")


@app.route("/pause/<job_id>", methods=["POST"])
def pause(job_id: str):
    if job_id not in _jobs:
        return jsonify({"error": "Job not found"}), 404
    _jobs[job_id]["pause_event"].clear()
    return jsonify({"status": "paused"})


@app.route("/resume/<job_id>", methods=["POST"])
def resume(job_id: str):
    if job_id not in _jobs:
        return jsonify({"error": "Job not found"}), 404
    _jobs[job_id]["pause_event"].set()
    return jsonify({"status": "resumed"})


@app.route("/download/<filename>")
def download(filename: str):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True)


@app.route("/download-all", methods=["POST"])
def download_all():
    data = request.get_json(silent=True) or {}
    filenames = data.get("filenames", [])
    if not filenames:
        return jsonify({"error": "No files specified"}), 400

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in filenames:
            fpath = os.path.join(OUTPUT_DIR, fname)
            if os.path.isfile(fpath):
                zf.write(fpath, fname)
    buf.seek(0)

    return Response(
        buf.getvalue(),
        mimetype="application/zip",
        headers={"Content-Disposition": "attachment; filename=itinerarios.zip"},
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5657))
    print(f"Scraper Web UI: http://localhost:{port}")
    app.run(debug=False, port=port, host="0.0.0.0")
