from __future__ import annotations
import csv, io, os, random, sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from flask import Flask, jsonify, render_template, request, Response

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
DB = DATA / "energy.db"
DATA.mkdir(exist_ok=True)
app = Flask(__name__)

DEFAULTS = {
    "emission_factor": float(os.getenv("GRID_EMISSION_FACTOR", "0.70")),
    "loss_threshold_percent": float(os.getenv("LOSS_THRESHOLD_PERCENT", "12")),
    "power_limit_kw": float(os.getenv("POWER_LIMIT_KW", "5.0")),
}

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def setting(key):
    with db() as con:
        row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return float(row["value"]) if row else DEFAULTS[key]

def save_setting(key, value):
    with db() as con:
        con.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))

def sample(scenario="normal"):
    # All readings generated here are simulated, not physical sensor measurements.
    source = round(random.uniform(.65, 1.25), 3)
    loss = random.uniform(.02, .07)
    power = round(random.uniform(.8, 3.2), 2)
    if scenario == "high_load":
        source, loss, power = round(random.uniform(1.2, 1.8), 3), random.uniform(.03, .08), round(random.uniform(5.1, 6.5), 2)
    elif scenario == "imbalance":
        loss = random.uniform(.20, .32)
    load = round(source * (1 - loss), 3)
    voltage = round(random.uniform(218, 242), 1)
    return source, load, power, voltage, round(power * 1000 / voltage, 2), round(random.uniform(42, 58) if scenario == "high_load" else random.uniform(27, 44), 1)

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS readings(
          id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
          source_kwh REAL NOT NULL, load_kwh REAL NOT NULL, power_kw REAL NOT NULL,
          voltage_v REAL NOT NULL, current_a REAL NOT NULL, temperature_c REAL NOT NULL,
          scenario TEXT NOT NULL)""")
        con.execute("CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY, value REAL NOT NULL)")
        for k,v in DEFAULTS.items():
            con.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k,v))
        if con.execute("SELECT COUNT(*) FROM readings").fetchone()[0] == 0:
            now = datetime.now().replace(microsecond=0)
            for i in range(23,-1,-1):
                values = sample()
                stamp = (now - timedelta(hours=i)).isoformat(timespec="seconds")
                con.execute("""INSERT INTO readings(timestamp,source_kwh,load_kwh,power_kw,voltage_v,current_a,temperature_c,scenario)
                    VALUES(?,?,?,?,?,?,?,?)""", (stamp,*values,"normal"))

def dictrow(row):
    return {k: row[k] for k in row.keys()}

def summary(rows):
    if not rows:
        return {"total_source_kwh":0,"total_load_kwh":0,"loss_kwh":0,"loss_percent":0,"carbon_kg":0,"alerts":[],"latest":None}
    src = sum(r["source_kwh"] for r in rows)
    load = sum(r["load_kwh"] for r in rows)
    loss = max(src-load,0)
    pct = loss/src*100 if src else 0
    latest = rows[-1]
    alerts = []
    threshold, limit = setting("loss_threshold_percent"), setting("power_limit_kw")
    if pct >= threshold:
        alerts.append({"level":"warning","title":"Energy difference above configured threshold",
          "detail":f"Aggregate difference is {pct:.1f}% (threshold {threshold:.1f}%). Check meter accuracy, timing, wiring and assumptions."})
    if latest["power_kw"] >= limit:
        alerts.append({"level":"critical","title":"Simulated power limit exceeded",
          "detail":f"Latest simulated power is {latest['power_kw']:.2f} kW (limit {limit:.2f} kW)."})
    if latest["temperature_c"] >= 50:
        alerts.append({"level":"warning","title":"Elevated simulated temperature",
          "detail":f"Latest simulated temperature is {latest['temperature_c']:.1f} °C. This is a demo alert, not a real safety reading."})
    factor = setting("emission_factor")
    return {"total_source_kwh":round(src,3),"total_load_kwh":round(load,3),"loss_kwh":round(loss,3),
      "loss_percent":round(pct,2),"carbon_kg":round(src*factor,3),"emission_factor":factor,
      "loss_threshold_percent":threshold,"power_limit_kw":limit,"alerts":alerts,"latest":latest}

@app.get("/")
def index():
    return render_template("index.html")

@app.get("/api/health")
def health():
    return jsonify({"status":"ok","application":"Smart Energy Digital Twin","database":"connected","mode":"simulation"})

@app.get("/api/dashboard")
def dashboard():
    limit = max(1,min(request.args.get("limit",48,type=int),500))
    with db() as con:
        rows = con.execute("SELECT * FROM readings ORDER BY id DESC LIMIT ?",(limit,)).fetchall()
    records = [dictrow(r) for r in reversed(rows)]
    return jsonify({"readings":records,"summary":summary(records),"demo_mode":True})

@app.post("/api/simulate")
def simulate():
    body = request.get_json(silent=True) or {}
    scenario = body.get("scenario","normal")
    if scenario not in ("normal","high_load","imbalance"):
        return jsonify({"error":"Scenario must be normal, high_load, or imbalance."}),400
    values = sample(scenario)
    with db() as con:
        cur = con.execute("""INSERT INTO readings(timestamp,source_kwh,load_kwh,power_kw,voltage_v,current_a,temperature_c,scenario)
          VALUES(?,?,?,?,?,?,?,?)""",(datetime.now().isoformat(timespec="seconds"),*values,scenario))
        row = con.execute("SELECT * FROM readings WHERE id=?",(cur.lastrowid,)).fetchone()
    return jsonify({"reading":dictrow(row),"message":f"Added a {scenario.replace('_',' ')} demo reading."})

@app.post("/api/reset")
def reset():
    with db() as con:
        con.execute("DELETE FROM readings")
        now = datetime.now().replace(microsecond=0)
        for i in range(23,-1,-1):
            vals = sample("normal")
            con.execute("""INSERT INTO readings(timestamp,source_kwh,load_kwh,power_kw,voltage_v,current_a,temperature_c,scenario)
              VALUES(?,?,?,?,?,?,?,?)""",((now-timedelta(hours=i)).isoformat(timespec="seconds"),*vals,"normal"))
    return jsonify({"message":"Demo readings reset to 24 normal sample points."})

@app.get("/api/settings")
def get_settings():
    return jsonify({k:setting(k) for k in DEFAULTS})

@app.post("/api/settings")
def update_settings():
    body = request.get_json(silent=True) or {}
    try:
        vals = {k:float(body[k]) for k in DEFAULTS}
    except (KeyError,TypeError,ValueError):
        return jsonify({"error":"Provide numeric values for all settings."}),400
    if not (0 <= vals["emission_factor"] <= 5 and .1 <= vals["loss_threshold_percent"] <= 100 and .1 <= vals["power_limit_kw"] <= 10000):
        return jsonify({"error":"One or more settings are outside allowed ranges."}),400
    for k,v in vals.items(): save_setting(k,v)
    return jsonify({"message":"Settings saved.","settings":vals})

@app.get("/api/export.csv")
def export_csv():
    with db() as con:
        rows = con.execute("SELECT * FROM readings ORDER BY id").fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id","timestamp","source_kwh","load_kwh","power_kw","voltage_v","current_a","temperature_c","scenario"])
    for r in rows: writer.writerow([r[k] for k in r.keys()])
    return Response(output.getvalue(),mimetype="text/csv",headers={"Content-Disposition":"attachment; filename=energy_readings.csv"})

init_db()
if __name__ == "__main__":
    # Local development server only; do not expose it directly to the public internet.
    app.run(host="127.0.0.1",port=5000,debug=False)
