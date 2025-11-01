from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import os
import requests

# ----------------------------------------------------
# CONFIG
# ----------------------------------------------------

# Path to the shared SQLite DB with safety reports
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "db", "reports.db")
DB_PATH = os.path.abspath(DB_PATH)

# Open source LLM served locally by Ollama
# - run `ollama pull mistral`
# - run `ollama serve`
OLLAMA_MODEL = "mistral"   # can swap to "llama3.2", etc.
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"

app = Flask(__name__)
# Allow your frontend (served at :5000) to call this service (on :7000)
CORS(app, origins=["http://127.0.0.1:5000"])


def get_conn():
    """
    Open a fresh SQLite connection to the shared safety reports DB.
    check_same_thread=False lets Flask's debug server call SQLite safely.
    """
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def fetch_recent_reports(limit=20):
    """
    Pull the most recent hazard reports (lat,lng,type,description,timestamp)
    from the shared SQLite DB so we can feed them to the model.
    """
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        """
        SELECT lat, lng, type, description, timestamp
        FROM reports
        ORDER BY timestamp DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = c.fetchall()
    conn.close()

    structured = []
    for (lat, lng, typ, desc, ts) in rows:
        structured.append(
            {
                "lat": lat,
                "lng": lng,
                "type": typ,
                "description": desc,
                "timestamp": ts,
            }
        )
    return structured


def build_context_summary(reports):
    """
    Make a short plaintext summary for the LLM:
    - recent highlights
    - how often each hazard type is getting flagged
    """

    counts = {
        "Slippery": 0,
        "Low Lighting": 0,
        "Isolated": 0,
    }

    highlights = []

    for r in reports:
        typ = r["type"] or ""
        desc = r["description"] or ""
        ts = r["timestamp"] or ""
        lat = r["lat"]
        lng = r["lng"]

        if typ in counts:
            counts[typ] += 1

        # rounded coords = looks more human-readable
        try:
            lat_str = f"{float(lat):.5f}"
            lng_str = f"{float(lng):.5f}"
        except Exception:
            lat_str = str(lat)
            lng_str = str(lng)

        highlights.append(
            f"- {ts}: {typ} near ({lat_str}, {lng_str}) :: {desc}"
        )

    summary_lines = [
        "Recent safety reports (most recent first):",
        *highlights[:8],  # don't flood the model
        "",
        "Aggregate counts in last batch:",
        f"- Slippery: {counts['Slippery']}",
        f"- Low Lighting: {counts['Low Lighting']}",
        f"- Isolated: {counts['Isolated']}",
    ]

    return "\n".join(summary_lines), counts


def call_llm(system_prompt, user_prompt):
    """
    Call an open source LLM (via Ollama) with our safety context + user question.
    """
    full_prompt = f"{system_prompt}\n\nUser question:\n{user_prompt}"

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": full_prompt,
        "stream": False,  # single-shot response
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        answer = (data.get("response") or "").strip()
        if not answer:
            answer = (
                "I'm not sure yet, but stay in well-lit areas and avoid isolated paths."
            )
        return answer

    except Exception as e:
        print("LLM CALL ERROR:", e)
        return (
            "I couldn't reach the assistant model right now. "
            "For now: stick to main walkways and stay near other people."
        )


@app.route("/chat", methods=["POST"])
def chat():
    """
    The AI endpoint.

    Frontend sends:
        { "message": "is south oval safe?" }
    """
    data = request.get_json(force=True, silent=True) or {}
    user_msg = (data.get("message") or "").strip()
    print("CHAT REQUEST:", user_msg)

    # Get recent safety reports and build the context block
    reports = fetch_recent_reports(limit=20)
    context_text, counts = build_context_summary(reports)

    # System prompt = how the assistant thinks / speaks.
    system_prompt = f"""
You are WheelieMap Safety Assistant.

Your job is to help a student move more safely and confidently across campus,
especially at night, in bad weather, or in areas that feel empty or sketchy.

You have recent crowdsourced safety reports from students. Each report can include:
- "Slippery": icy / wet / uneven / wheelchair-hostile surface
- "Low Lighting": poor lighting, dim areas, burned-out lamps
- "Isolated": very empty, quiet, feels unsafe or hard to call for help

Use those real reports to answer questions.
You should:
- Be calm, direct, supportive.
- Suggest staying in well-lit / higher-traffic areas.
- Suggest alternate main paths instead of cutting through isolated shortcuts.
- If risk seems high, gently suggest walking with a friend or using a campus escort.
- If risk seems low, you can say it's mostly fine, but still encourage awareness.

NEVER invent crimes or emergencies that aren't in the data.
You MAY infer general risk patterns ("several low-light reports near that area tonight").

Keep answers to 3-5 sentences.
End with 1 actionable safety tip.

Recent campus context:
{context_text}
""".strip()

    reply_text = call_llm(system_prompt, user_msg)

    return jsonify({"reply": reply_text})


if __name__ == "__main__":
    print("Using DB at:", DB_PATH)
    app.run(host="127.0.0.1", port=7000, debug=True)
