"""
server.py — Tracking Server with SQLite

Setup:
    pip install flask

Run:
    Terminal 1: python server.py
    Terminal 2: ngrok http 5000  →  copy URL → SERVER_URL in bot.py
"""

from flask import Flask, redirect, request, jsonify
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)

DB_PATH = "clicks.db"

# ── Shared refs injected by bot.py ──────────────────────────────
session_links_ref = {}   # post_num → link info dict
user_cache_ref    = {}   # tg_id    → user object

# ── DB Setup ────────────────────────────────────────────────────
def init_db():
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS clicks (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            session_num   INTEGER,
            post_num      INTEGER,
            tg_id         INTEGER,
            tg_username   TEXT,
            x_username    TEXT,
            x_link        TEXT,
            clicked_at    TEXT
        )
    """)
    con.commit()
    con.close()

init_db()

def save_click(session_num, post_num, tg_id, tg_username, x_username, x_link):
    """Save one click to SQLite (ignore duplicates for same user+post)."""
    con = sqlite3.connect(DB_PATH)
    # Check duplicate
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

def get_clicks_for_session(session_num):
    """Return all click rows for a given session."""
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT post_num,tg_id,tg_username,x_username,x_link,clicked_at "
        "FROM clicks WHERE session_num=? ORDER BY clicked_at",
        (session_num,)
    ).fetchall()
    con.close()
    return rows  # list of tuples

def clear_session_clicks(session_num):
    con = sqlite3.connect(DB_PATH)
    con.execute("DELETE FROM clicks WHERE session_num=?", (session_num,))
    con.commit()
    con.close()

# ── Tracking Route ───────────────────────────────────────────────
# URL: /visit?uid=<tg_id>&post=<post_num>&sess=<session_num>
@app.route("/visit")
def visit():
    try:
        uid      = int(request.args.get("uid",  0))
        post_num = int(request.args.get("post", 0))
        sess_num = int(request.args.get("sess", 0))
    except (ValueError, TypeError):
        return "Bad request", 400

    link_info = session_links_ref.get(post_num)
    if not link_info:
        return redirect("https://x.com")   # fallback

    original_url = link_info["url"]

    # Don't log if user clicks own link — still redirect
    if uid == link_info["poster_id"]:
        return redirect(original_url)

    # Resolve tg_username
    cached = user_cache_ref.get(uid)
    if cached and cached.username:
        tg_username = f"@{cached.username}"
    elif cached:
        tg_username = cached.full_name
    else:
        tg_username = f"User {uid}"

    x_username = f"@{link_info['x_username']}"

    save_click(sess_num, post_num, uid, tg_username, x_username, original_url)
    return redirect(original_url)

# ── Health ───────────────────────────────────────────────────────
@app.route("/health")
def health():
    return jsonify({"status": "ok"})

@app.route("/api/clicks/<int:session_num>")
def get_session_clicks(session_num):
    """API endpoint for bot to fetch clicks for a session."""
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT post_num, tg_id, tg_username, x_username, x_link, clicked_at "
        "FROM clicks WHERE session_num=? ORDER BY clicked_at",
        (session_num,)
    ).fetchall()
    con.close()
    
    clicks = []
    for row in rows:
        clicks.append({
            "post_num": row[0],
            "tg_id": row[1],
            "tg_username": row[2],
            "x_username": row[3],
            "x_link": row[4],
            "clicked_at": row[5]
        })
    
    return jsonify({"clicks": clicks})

import os

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
