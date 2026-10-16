"""Database layer: schema + synthetic data seeding (SQLite)."""
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(__file__).parent / "dcsi.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS services (
    id INTEGER PRIMARY KEY, name TEXT UNIQUE, tier INTEGER, owner TEXT);
CREATE TABLE IF NOT EXISTS servers (
    id INTEGER PRIMARY KEY, hostname TEXT UNIQUE, rack TEXT, service_id INTEGER,
    FOREIGN KEY(service_id) REFERENCES services(id));
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY, server_id INTEGER, ts TEXT,
    cpu REAL, temp_c REAL, power_w REAL,
    FOREIGN KEY(server_id) REFERENCES servers(id));
CREATE TABLE IF NOT EXISTS incidents (
    id INTEGER PRIMARY KEY, service_id INTEGER, severity TEXT,
    opened TEXT, resolved TEXT, summary TEXT,
    FOREIGN KEY(service_id) REFERENCES services(id));
"""

SERVICES = [
    ("Payments API", 1, "fintech-team"), ("Auth Service", 1, "platform-team"),
    ("Order Processing", 2, "commerce-team"), ("Search Index", 2, "search-team"),
    ("Reporting DB", 3, "data-team"), ("Batch ETL", 3, "data-team"),
]
SUMMARIES = ["High latency", "Disk failure", "Cooling alarm", "Network flap",
             "Memory leak", "Power fluctuation", "Failed deployment"]


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(reset=False, seed=42):
    if reset and DB_PATH.exists():
        DB_PATH.unlink()
    conn = connect()
    conn.executescript(SCHEMA)
    if conn.execute("SELECT COUNT(*) FROM services").fetchone()[0] == 0:
        _seed(conn, random.Random(seed))
    conn.commit()
    conn.close()


def _seed(conn, rng):
    now = datetime.now().replace(minute=0, second=0, microsecond=0)
    conn.executemany("INSERT INTO services(name,tier,owner) VALUES(?,?,?)", SERVICES)
    sid = 0
    for svc_id in range(1, len(SERVICES) + 1):
        for _ in range(rng.randint(3, 5)):
            sid += 1
            conn.execute("INSERT INTO servers(hostname,rack,service_id) VALUES(?,?,?)",
                         (f"srv-{sid:03d}", f"R{rng.randint(1, 6)}", svc_id))
    # 48 hourly metric samples per server; a few servers run "hot"
    hot = set(rng.sample(range(1, sid + 1), 3))
    for server_id in range(1, sid + 1):
        base_cpu = rng.uniform(30, 60) + (30 if server_id in hot else 0)
        for h in range(48):
            ts = (now - timedelta(hours=47 - h)).isoformat()
            cpu = min(100, max(1, rng.gauss(base_cpu, 7)))
            temp = 22 + cpu * 0.35 + rng.gauss(0, 1.5)
            power = 150 + cpu * 3.2 + rng.gauss(0, 10)
            conn.execute("INSERT INTO metrics(server_id,ts,cpu,temp_c,power_w) VALUES(?,?,?,?,?)",
                         (server_id, ts, round(cpu, 1), round(temp, 1), round(power, 1)))
    # incidents over the last 30 days
    for _ in range(40):
        opened = now - timedelta(hours=rng.randint(1, 720))
        resolved = opened + timedelta(minutes=rng.randint(10, 400))
        conn.execute("INSERT INTO incidents(service_id,severity,opened,resolved,summary) VALUES(?,?,?,?,?)",
                     (rng.randint(1, len(SERVICES)), rng.choices(["P1", "P2", "P3"], [1, 3, 6])[0],
                      opened.isoformat(), resolved.isoformat(), rng.choice(SUMMARIES)))


if __name__ == "__main__":
    init_db(reset=True)
    print(f"Seeded database at {DB_PATH}")
