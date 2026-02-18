"""
Minimal Tracking Server for Railway
"""

from flask import Flask, redirect, request, jsonify
import sqlite3
import os
from datetime import datetime
from urllib.parse import unquote

app = Flask(__name__)

DB_PATH = os.environ.get("DB_PATH", "/tmp/clicks.db")

# ── Database ────────────────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS clicks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_num INTEGER,
            post_num INTEGER,
            tg_id INTEGER,
            tg_username TEXT,
            x_username TEXT,
            x_link TEXT,
            clicked_at TEXT
        )
    """)
    con.commit()
    con.close()

init_db()

def save_click(session_num, post_num, tg_id, tg_username, x_username, x_link):
    con = sqlite3.connect(DB_PATH)
    row = con.execute(
        "SELECT id FROM clicks WHERE session_num=? AND post_num=? AND tg_id=?",
        (session_num, post_num, tg_id)
    ).fetchone()
    if not row:
        con.execute(
            "INSERT INTO clicks (session_num,post_num,tg_id,tg_username,x_username,x_link,clicked_at) VALUES (?,?,?,?,?,?,?)",
            (session_num, post_num, tg_id, tg_username, x_username, x_link,
             datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
        con.commit()
    con.close()

# ── Routes ──────────────────────────────────────────────────────
@app.route("/")
def index():
    return jsonify({"status": "ok", "service": "engagement-tracker"})

@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/track")
def track_visit():
    """Track click and redirect to X."""
    try:
        uid = int(request.args.get("uid", 0))
        post = int(request.args.get("post", 0))
        sess = int(request.args.get("sess", 1))
        x_user = request.args.get("x", "Unknown")
        link = unquote(request.args.get("link", ""))
    except:
        return redirect("https://x.com")

    if not link or not uid:
        return redirect("https://x.com")

    save_click(sess, post, uid, f"User{uid}", x_user, link)
    return redirect(link)

@app.route("/api/clicks/<int:session_num>")
def get_clicks(session_num):
    """Return clicks for session."""
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT post_num, tg_id, tg_username, x_username, x_link, clicked_at "
        "FROM clicks WHERE session_num=?",
        (session_num,)
    ).fetchall()
    con.close()
    
    return jsonify({
        "clicks": [
            {
                "post_num": r[0],
                "tg_id": r[1],
                "tg_username": r[2],
                "x_username": r[3],
                "x_link": r[4],
                "clicked_at": r[5]
            }
            for r in rows
        ]
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Server starting on port {port}")
    app.run(host="0.0.0.0", port=port)
