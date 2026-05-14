import json
import os
import queue
import re
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

from flask import Flask, Response, jsonify, render_template, request, stream_with_context

from crew import crew
from task import set_task_progress_callback_for_thread

MAX_TOPIC_LEN = 300
KICKOFF_TIMEOUT_SECONDS = int(os.environ.get("KICKOFF_TIMEOUT_SECONDS", "180"))
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "600"))
CACHE_MAX_ENTRIES = 64

app = Flask(__name__)

_cache: dict[str, tuple[float, dict]] = {}
_cache_lock = threading.Lock()
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="crew")


def _parse_listings_markdown(md_text: str):
    """Parse the Property_Fetcher markdown table into a list of listing dicts."""
    listings = []
    source_url = ""

    if not md_text:
        return listings, source_url

    for line in md_text.splitlines():
        line = line.strip()
        if line.lower().startswith("source:"):
            source_url = line.split(":", 1)[1].strip()
            continue

        if not line.startswith("|"):
            continue

        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 8:
            continue
        if cells[0].lower() in {"#", ""} or set(cells[0]) <= {"-", " "}:
            continue
        if not re.match(r"^\d+$", cells[0]):
            continue

        url_cell = cells[7]
        md_link = re.search(r"\[[^\]]*\]\((https?://[^\s)]+)\)", url_cell)
        if md_link:
            clean_url = md_link.group(1)
        else:
            url_match = re.search(r"https?://\S+", url_cell)
            clean_url = url_match.group(0).rstrip(")") if url_match else url_cell

        listings.append({
            "rank": cells[0],
            "title": cells[1],
            "price": cells[2],
            "location": cells[3],
            "beds": cells[4],
            "baths": cells[5],
            "area": cells[6],
            "url": clean_url,
        })

    return listings, source_url


def _normalize_topic(topic: str) -> str:
    return re.sub(r"\s+", " ", topic.strip().lower())


def _cache_get(key: str):
    with _cache_lock:
        entry = _cache.get(key)
        if not entry:
            return None
        ts, payload = entry
        if time.time() - ts > CACHE_TTL_SECONDS:
            _cache.pop(key, None)
            return None
        return payload


def _cache_set(key: str, payload: dict) -> None:
    with _cache_lock:
        if len(_cache) >= CACHE_MAX_ENTRIES:
            oldest_key = min(_cache, key=lambda k: _cache[k][0])
            _cache.pop(oldest_key, None)
        _cache[key] = (time.time(), payload)


def _validate_topic(payload: dict):
    topic = (payload.get("topic") or "").strip()
    if not topic:
        return None, ("Please enter a search query.", 400)
    if len(topic) > MAX_TOPIC_LEN:
        return None, (f"Query is too long (max {MAX_TOPIC_LEN} characters).", 400)
    return topic, None


def _run_crew_to_payload(topic: str, on_progress=None) -> dict:
    """Run the crew with a per-task progress hook and return the response payload."""
    def _kickoff_with_callback():
        tid = threading.get_ident()
        if on_progress is not None:
            set_task_progress_callback_for_thread(tid, on_progress)
        try:
            return crew.kickoff(inputs={"topic": topic})
        finally:
            if on_progress is not None:
                set_task_progress_callback_for_thread(tid, None)

    future = _executor.submit(_kickoff_with_callback)
    try:
        result = future.result(timeout=KICKOFF_TIMEOUT_SECONDS)
    except FuturesTimeout:
        future.cancel()
        raise TimeoutError(f"Agent run exceeded {KICKOFF_TIMEOUT_SECONDS}s")

    task_outputs = list(getattr(result, "tasks_output", []) or [])
    listings_md = task_outputs[0].raw if len(task_outputs) > 0 else ""
    research_md = task_outputs[1].raw if len(task_outputs) > 1 else ""
    listings, source_url = _parse_listings_markdown(listings_md)

    return {
        "topic": topic,
        "listings": listings,
        "source_url": source_url,
        "listings_markdown": listings_md,
        "research_markdown": research_md,
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/healthz")
def healthz():
    return jsonify({
        "ok": True,
        "groq_key_present": bool(os.environ.get("GROQ_API_KEY")),
        "serper_key_present": bool(os.environ.get("SERPER_API_KEY")),
        "cache_size": len(_cache),
    })


@app.route("/search", methods=["POST"])
def search():
    payload = request.get_json(silent=True) or {}
    topic, err = _validate_topic(payload)
    if err:
        msg, code = err
        return jsonify({"error": msg}), code

    key = _normalize_topic(topic)
    cached = _cache_get(key)
    if cached:
        return jsonify({**cached, "cached": True})

    try:
        result_payload = _run_crew_to_payload(topic)
    except TimeoutError as e:
        return jsonify({"error": "Agent run timed out.", "detail": str(e)}), 504
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Agent run failed.", "detail": str(e)}), 500

    _cache_set(key, result_payload)
    return jsonify({**result_payload, "cached": False})


@app.route("/search/stream", methods=["GET"])
def search_stream():
    topic, err = _validate_topic({"topic": request.args.get("topic", "")})
    if err:
        msg, code = err
        return Response(
            f"event: error\ndata: {json.dumps({'error': msg})}\n\n",
            status=code,
            mimetype="text/event-stream",
        )

    key = _normalize_topic(topic)
    cached = _cache_get(key)

    events: "queue.Queue[tuple[str, dict]]" = queue.Queue()

    def emit(event: str, data: dict) -> None:
        events.put((event, data))

    def worker():
        try:
            if cached:
                emit("task_done", {"task": "fetch"})
                emit("task_done", {"task": "research"})
                emit("result", {**cached, "cached": True})
                emit("done", {})
                return

            emit("started", {"topic": topic})

            def on_progress(task_index: int, _output) -> None:
                label = "fetch" if task_index == 0 else "research"
                emit("task_done", {"task": label})

            result_payload = _run_crew_to_payload(topic, on_progress=on_progress)
            _cache_set(key, result_payload)
            emit("result", {**result_payload, "cached": False})
            emit("done", {})
        except TimeoutError as e:
            emit("error", {"error": "Agent run timed out.", "detail": str(e)})
        except Exception as e:
            traceback.print_exc()
            emit("error", {"error": "Agent run failed.", "detail": str(e)})
        finally:
            events.put((None, None))

    threading.Thread(target=worker, daemon=True).start()

    @stream_with_context
    def generate():
        # Initial comment to flush headers immediately on some proxies.
        yield ": stream-open\n\n"
        while True:
            try:
                event, data = events.get(timeout=KICKOFF_TIMEOUT_SECONDS + 10)
            except queue.Empty:
                yield f"event: error\ndata: {json.dumps({'error': 'Stream stalled.'})}\n\n"
                return
            if event is None:
                return
            yield f"event: {event}\ndata: {json.dumps(data)}\n\n"

    return Response(generate(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host="0.0.0.0", port=port, debug=debug, threaded=True)
