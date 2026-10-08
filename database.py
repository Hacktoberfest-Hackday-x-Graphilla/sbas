import sqlite3
from pathlib import Path
from datetime import datetime, timezone

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "realai.sqlite3"

SCHEMA = """
CREATE TABLE IF NOT EXISTS generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool TEXT NOT NULL,
    mode TEXT NOT NULL,
    input_text TEXT NOT NULL,
    output_text TEXT NOT NULL,
    provider TEXT NOT NULL,
    latency_ms INTEGER DEFAULT 0,
    favorite INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_generations_created_at ON generations(created_at);
CREATE INDEX IF NOT EXISTS idx_generations_tool ON generations(tool);

CREATE TABLE IF NOT EXISTS settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    display_name TEXT NOT NULL DEFAULT 'Demo User',
    theme TEXT NOT NULL DEFAULT 'dark',
    default_tool TEXT NOT NULL DEFAULT 'writer',
    updated_at TEXT NOT NULL
);
"""

def connect():
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = connect()
    conn.executescript(SCHEMA)
    # Safe migration for old databases.
    cols = {row[1] for row in conn.execute("PRAGMA table_info(generations)").fetchall()}
    for name, ddl in [("latency_ms", "ALTER TABLE generations ADD COLUMN latency_ms INTEGER DEFAULT 0"), ("favorite", "ALTER TABLE generations ADD COLUMN favorite INTEGER DEFAULT 0")]:
        if name not in cols:
            conn.execute(ddl)
    settings_cols = {row[1] for row in conn.execute("PRAGMA table_info(settings)").fetchall()}
    if "default_tool" not in settings_cols:
        conn.execute("ALTER TABLE settings ADD COLUMN default_tool TEXT NOT NULL DEFAULT 'writer'")
    now = datetime.now(timezone.utc).isoformat()
    conn.execute("INSERT OR IGNORE INTO settings (id, display_name, theme, default_tool, updated_at) VALUES (1, ?, ?, ?, ?)", ("Demo User", "dark", "writer", now))
    conn.commit(); conn.close()

def save_generation(tool, mode, input_text, output_text, provider, latency_ms=0):
    conn = connect()
    cur = conn.execute("INSERT INTO generations (tool, mode, input_text, output_text, provider, latency_ms, favorite, created_at) VALUES (?, ?, ?, ?, ?, ?, 0, ?)", (tool, mode, input_text, output_text, provider, int(latency_ms or 0), datetime.now(timezone.utc).isoformat()))
    conn.commit(); gid = cur.lastrowid; conn.close(); return gid

def recent_generations(limit=40, tool=None, favorites_only=False):
    conn = connect(); clauses=[]; params=[]
    if tool:
        clauses.append("tool = ?"); params.append(tool)
    if favorites_only:
        clauses.append("favorite = 1")
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(max(1, min(int(limit or 40), 100)))
    rows = conn.execute(f"SELECT id, tool, mode, input_text, output_text, provider, latency_ms, favorite, created_at FROM generations{where} ORDER BY id DESC LIMIT ?", params).fetchall()
    conn.close(); return [dict(row) for row in rows]

def get_generation(gid):
    conn=connect(); row=conn.execute("SELECT * FROM generations WHERE id=?",(gid,)).fetchone(); conn.close(); return dict(row) if row else None

def set_favorite(gid, favorite):
    conn=connect(); cur=conn.execute("UPDATE generations SET favorite=? WHERE id=?",(1 if favorite else 0,gid)); conn.commit(); ok=cur.rowcount>0; conn.close(); return ok

def delete_generation(gid):
    conn=connect(); cur=conn.execute("DELETE FROM generations WHERE id=?",(gid,)); conn.commit(); ok=cur.rowcount>0; conn.close(); return ok

def stats():
    conn=connect()
    total=conn.execute("SELECT COUNT(*) FROM generations").fetchone()[0]
    fav=conn.execute("SELECT COUNT(*) FROM generations WHERE favorite=1").fetchone()[0]
    avg=conn.execute("SELECT COALESCE(ROUND(AVG(latency_ms)),0) FROM generations WHERE latency_ms>0").fetchone()[0]
    top=conn.execute("SELECT tool, COUNT(*) AS uses FROM generations GROUP BY tool ORDER BY uses DESC LIMIT 5").fetchall()
    providers=conn.execute("SELECT provider, COUNT(*) AS uses FROM generations GROUP BY provider ORDER BY uses DESC").fetchall()
    conn.close()
    return {"total_generations":total,"favorites":fav,"avg_latency_ms":int(avg or 0),"top_tools":[dict(x) for x in top],"providers":[dict(x) for x in providers]}

def get_settings():
    conn=connect(); row=conn.execute("SELECT display_name, theme, default_tool, updated_at FROM settings WHERE id=1").fetchone(); conn.close()
    return dict(row) if row else {"display_name":"Demo User","theme":"dark","default_tool":"writer"}

def update_settings(display_name=None, theme=None, default_tool=None):
    current=get_settings(); name=(display_name or current["display_name"]).strip()[:80] or "Demo User"
    theme=theme if theme in {"dark","midnight"} else current["theme"]
    tool=(default_tool or current["default_tool"]).strip()[:40]
    conn=connect(); conn.execute("UPDATE settings SET display_name=?, theme=?, default_tool=?, updated_at=? WHERE id=1",(name,theme,tool,datetime.now(timezone.utc).isoformat())); conn.commit(); conn.close(); return get_settings()
