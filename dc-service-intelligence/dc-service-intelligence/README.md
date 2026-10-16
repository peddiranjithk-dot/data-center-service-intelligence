# Data Center Service Intelligence

A simple base project that turns data center telemetry (CPU, temperature, power) and incident
history into per-service health scores, anomaly alerts and a live dashboard.

## Run

```bash
pip install -r requirements.txt
python db.py        # (re)seed sample data into dcsi.db
python app.py       # http://localhost:5000
```

## Structure

| File | Purpose |
|---|---|
| `db.py` | SQLite schema and synthetic data (6 services, ~25 servers, 48h metrics, 30d incidents) |
| `analytics.py` | Health score, z-score anomaly detection, MTTR, rack power |
| `app.py` | Flask app: dashboard + JSON API |
| `templates/index.html` | Dashboard (no JS libraries) |

## API

`/api/summary` · `/api/services` · `/api/anomalies` · `/api/incidents` · `/api/racks`

## Health score

`100 - incident penalty (P1=10, P2=5, P3=2, max 40) - CPU penalty (avg above 60%) - temperature penalty (avg above 40°C)`.
Healthy ≥ 80, degraded ≥ 60, otherwise critical.

## Next steps

Replace the seeder with real collectors (Prometheus, SNMP, DCIM, ServiceNow), add alert routing, forecasting and auth.
