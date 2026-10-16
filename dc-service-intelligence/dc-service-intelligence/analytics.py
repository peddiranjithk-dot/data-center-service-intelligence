"""Service intelligence: health scoring, anomaly detection, incident stats."""
from datetime import datetime
from statistics import mean, pstdev

from db import connect

SEVERITY_WEIGHT = {"P1": 10, "P2": 5, "P3": 2}


def _mttr_minutes(rows):
    durations = [(datetime.fromisoformat(r["resolved"]) - datetime.fromisoformat(r["opened"])).total_seconds() / 60
                 for r in rows if r["resolved"]]
    return round(mean(durations), 1) if durations else 0.0


def service_health():
    """Score 0-100 per service from avg CPU, temperature and weighted incident load."""
    conn = connect()
    result = []
    for svc in conn.execute("SELECT * FROM services ORDER BY tier, name"):
        m = conn.execute("""SELECT AVG(cpu) cpu, AVG(temp_c) temp, AVG(power_w) power, COUNT(DISTINCT s.id) servers
                            FROM metrics m JOIN servers s ON s.id = m.server_id
                            WHERE s.service_id = ?""", (svc["id"],)).fetchone()
        inc = conn.execute("SELECT * FROM incidents WHERE service_id = ?", (svc["id"],)).fetchall()
        inc_penalty = min(40, sum(SEVERITY_WEIGHT[i["severity"]] for i in inc))
        cpu_penalty = max(0, m["cpu"] - 60) * 0.8
        temp_penalty = max(0, m["temp"] - 40) * 2
        score = max(0, round(100 - inc_penalty - cpu_penalty - temp_penalty, 1))
        result.append({
            "service": svc["name"], "tier": svc["tier"], "owner": svc["owner"],
            "servers": m["servers"], "avg_cpu": round(m["cpu"], 1), "avg_temp_c": round(m["temp"], 1),
            "avg_power_w": round(m["power"], 1), "incidents_30d": len(inc),
            "mttr_min": _mttr_minutes(inc), "health_score": score,
            "status": "healthy" if score >= 80 else "degraded" if score >= 60 else "critical",
        })
    conn.close()
    return result


def detect_anomalies(z_threshold=2.5):
    """Flag latest metric readings that deviate strongly from each server's own history."""
    conn = connect()
    anomalies = []
    for srv in conn.execute("""SELECT s.id, s.hostname, s.rack, v.name service
                               FROM servers s JOIN services v ON v.id = s.service_id"""):
        rows = conn.execute("SELECT * FROM metrics WHERE server_id = ? ORDER BY ts", (srv["id"],)).fetchall()
        for field in ("cpu", "temp_c", "power_w"):
            vals = [r[field] for r in rows]
            sd = pstdev(vals[:-1])
            if sd == 0:
                continue
            z = (vals[-1] - mean(vals[:-1])) / sd
            if abs(z) >= z_threshold:
                anomalies.append({"hostname": srv["hostname"], "rack": srv["rack"], "service": srv["service"],
                                  "metric": field, "value": vals[-1], "z_score": round(z, 2)})
        # absolute thresholds
        last = rows[-1]
        if last["temp_c"] > 55:
            anomalies.append({"hostname": srv["hostname"], "rack": srv["rack"], "service": srv["service"],
                              "metric": "temp_c (over limit)", "value": last["temp_c"], "z_score": None})
    conn.close()
    return sorted(anomalies, key=lambda a: abs(a["z_score"] or 99), reverse=True)


def recent_incidents(limit=15):
    conn = connect()
    rows = conn.execute("""SELECT i.id, v.name service, i.severity, i.summary, i.opened, i.resolved
                           FROM incidents i JOIN services v ON v.id = i.service_id
                           ORDER BY i.opened DESC LIMIT ?""", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def rack_power():
    conn = connect()
    rows = conn.execute("""SELECT s.rack, ROUND(AVG(m.power_w),1) avg_power_w, COUNT(DISTINCT s.id) servers
                           FROM metrics m JOIN servers s ON s.id = m.server_id
                           GROUP BY s.rack ORDER BY s.rack""").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def summary():
    health = service_health()
    return {
        "services": len(health),
        "avg_health": round(mean(h["health_score"] for h in health), 1),
        "critical": sum(h["status"] == "critical" for h in health),
        "open_anomalies": len(detect_anomalies()),
        "total_incidents_30d": sum(h["incidents_30d"] for h in health),
    }
