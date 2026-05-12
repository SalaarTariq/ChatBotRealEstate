import os
import re
import traceback
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from crew import crew

BASE_DIR = Path(__file__).parent
LISTINGS_FILE = BASE_DIR / "property_listings.md"
RESEARCH_FILE = BASE_DIR / "property_research_report.md"

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

        url = cells[7]
        url_match = re.search(r"https?://\S+", url)
        clean_url = url_match.group(0).rstrip(")") if url_match else url

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


def _read_file(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/search", methods=["POST"])
def search():
    payload = request.get_json(silent=True) or {}
    topic = (payload.get("topic") or "").strip()
    if not topic:
        return jsonify({"error": "Please enter a search query."}), 400

    # Wipe stale output files so we know we got fresh results.
    for f in (LISTINGS_FILE, RESEARCH_FILE):
        try:
            f.unlink()
        except FileNotFoundError:
            pass

    try:
        crew.kickoff(inputs={"topic": topic})
    except Exception as e:
        traceback.print_exc()
        return jsonify({
            "error": "Agent run failed.",
            "detail": str(e),
        }), 500

    listings_md = _read_file(LISTINGS_FILE)
    research_md = _read_file(RESEARCH_FILE)
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
    app.run(host="0.0.0.0", port=port, debug=True)
