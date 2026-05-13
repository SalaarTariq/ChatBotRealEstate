import os
import re
import traceback

from flask import Flask, jsonify, render_template, request

from crew import crew

MAX_TOPIC_LEN = 300

app = Flask(__name__)


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


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    payload = request.get_json(silent=True) or {}
    topic = (payload.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "Please enter a search query."}), 400
    if len(topic) > MAX_TOPIC_LEN:
        return jsonify({
            "error": f"Query is too long (max {MAX_TOPIC_LEN} characters).",
        }), 400

    try:
        result = crew.kickoff(inputs={"topic": topic})
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": "Agent run failed.",
            "detail": str(e),
        }), 500

    task_outputs = list(getattr(result, "tasks_output", []) or [])
    listings_md = task_outputs[0].raw if len(task_outputs) > 0 else ""
    research_md = task_outputs[1].raw if len(task_outputs) > 1 else ""
    listings, source_url = _parse_listings_markdown(listings_md)

    return jsonify({
        "topic": topic,
        "listings": listings,
        "source_url": source_url,
        "listings_markdown": listings_md,
        "research_markdown": research_md,
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("FLASK_DEBUG", "").lower() in {"1", "true", "yes"}
    app.run(host="0.0.0.0", port=port, debug=debug)
