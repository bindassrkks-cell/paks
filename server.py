import os
import json
import shutil
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from ue4_compiler import compile_pak, CONFIG_PATH, ORIGINAL_PAK_DIR, EDITOR_DIR, RESULT_DIR, init_folders

app = FastAPI(title="KNIGHT CORE CLOUD ENGINE", version="1.0.59")

init_folders()

@app.get("/", response_class=HTMLResponse)
def dashboard():
    with open(CONFIG_PATH, "r") as f:
        cfg = json.load(f)

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>KNIGHT CORE CUSTOM SERVER</title>
        <style>
            body {{ background: #0c0f12; color: #ffb703; font-family: sans-serif; padding: 12px; margin: 0; }}
            .container {{ border: 2px solid #ffb703; border-radius: 12px; padding: 16px; background: #13171c; max-width: 480px; margin: auto; }}
            .header {{ text-align: center; font-weight: bold; letter-spacing: 1.5px; font-size: 16px; margin-bottom: 16px; }}
            .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px; }}
            .btn {{ background: #161c24; border: 1.5px solid #ffb703; color: #00e5ff; padding: 12px; border-radius: 8px; font-weight: bold; cursor: pointer; text-align: center; }}
            .btn.active {{ background: #ffb703; color: #0c0f12; }}
            .box {{ background: #161c24; border: 1px solid #28313d; border-radius: 8px; padding: 12px; margin-bottom: 12px; }}
            .label-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }}
            .preset-badge {{ background: #263238; color: #80d8ff; font-size: 10px; padding: 3px 6px; border-radius: 4px; }}
            input[type=number] {{ background: #0c0f12; border: 1px solid #ffb703; color: #00e5ff; font-weight: bold; padding: 6px; border-radius: 6px; width: 80px; text-align: right; }}
            input[type=range] {{ width: 100%; accent-color: #00e5ff; margin-top: 6px; }}
            .guns {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 13px; color: #cfd8dc; }}
            .action-btn {{ background: #00e5ff; color: #0c0f12; width: 100%; padding: 14px; font-size: 15px; font-weight: 800; border: none; border-radius: 8px; cursor: pointer; margin-top: 10px; }}
            .download-btn {{ background: #00c853; color: white; display: block; text-decoration: none; text-align: center; padding: 12px; border-radius: 8px; font-weight: bold; margin-top: 8px; }}
            .log {{ background: #080a0c; color: #00e5ff; padding: 10px; font-family: monospace; font-size: 11px; border-radius: 6px; margin-top: 12px; max-height: 120px; overflow-y: auto; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">♦ KNIGHT CORE CUSTOM SERVER ♦</div>

            <div class="grid">
                <div class="btn {'active' if cfg.get('aimbot') else ''}" onclick="toggle('aimbot')">AIMBOT</div>
                <div class="btn {'active' if cfg.get('magic_bt', 0) > 0 else ''}" onclick="toggle('magic_bt')">MAGIC + BT</div>
            </div>

            <div class="box">
                <div class="label-row">
                    <span>Magic Bullet (BT Value)</span>
                    <span class="preset-badge">Low: 1-5 | Med: 9 | High: 15+</span>
                </div>
                <div style="display: flex; gap: 8px;">
                    <input type="range" min="0" max="50" step="0.5" value="{cfg.get('magic_bt', 9.0)}" oninput="syncVal('magic_bt', this.value)">
                    <input type="number" id="num_magic_bt" value="{cfg.get('magic_bt', 9.0)}" onchange="syncVal('magic_bt', this.value)">
                </div>
            </div>

            <div class="grid">
                <div class="btn {'active' if cfg.get('antena') else ''}" onclick="toggle('antena')">ANTENA</div>
                <div class="btn {'active' if cfg.get('headshot') else ''}" onclick="toggle('headshot')">HEADSHOT</div>
                <div class="btn {'active' if cfg.get('ipad_view') else ''}" onclick="toggle('ipad_view')">IPAD VIEW</div>
                <div class="btn {'active' if cfg.get('aura_esp') else ''}" onclick="toggle('aura_esp')">AURA ESP</div>
            </div>

            <div class="box">
                <div class="label-row">
                    <span>Bullet Spread</span>
                    <span class="preset-badge">Low: 2 | Med: 5 | High: 10+</span>
                </div>
                <div style="display: flex; gap: 8px;">
                    <input type="range" min="0" max="30" step="0.5" value="{cfg.get('bullet_spread', 5.0)}" oninput="syncVal('bullet_spread', this.value)">
                    <input type="number" id="num_bullet_spread" value="{cfg.get('bullet_spread', 5.0)}" onchange="syncVal('bullet_spread', this.value)">
                </div>
            </div>

            <div class="box">
                <div style="font-weight: bold; margin-bottom: 8px; color: #ffb703;">NO RECOIL WEAPONS</div>
                <div class="guns">
                    {"".join([f"<div><input type='checkbox' {'checked' if v else ''} onchange='setGun(\"{k}\", this.checked)'> {k}</div>" for k, v in cfg.get('no_recoil', {}).items()])}
                </div>
            </div>

            <button class="action-btn" onclick="compilePak()">COMPILE PAK ON CLOUD</button>
            <a href="/api/download" class="download-btn">DOWNLOAD COMPILED PAK</a>

            <div class="log" id="status_box">Ready. Configure values & hit compile.</div>
        </div>

        <script>
            async function syncVal(key, val) {{
                const num = parseFloat(val);
                document.getElementById('num_' + key).value = num;
                await fetch('/api/config', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{[key]: num}})
                }});
            }}
            async function toggle(key) {{
                await fetch('/api/config/toggle/' + key, {{ method: 'POST' }});
                location.reload();
            }}
            async function setGun(gun, status) {{
                await fetch('/api/config/gun/' + gun + '?enabled=' + status, {{ method: 'POST' }});
            }}
            async function compilePak() {{
                const box = document.getElementById('status_box');
                box.innerText = 'Compiling PAK on Render... Please wait.';
                const res = await fetch('/api/compile', {{ method: 'POST' }});
                const data = await res.json();
                box.innerText = JSON.stringify(data, null, 2);
            }}
        </script>
    </body>
    </html>
    """

@app.get("/api/config")
def get_config():
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

@app.post("/api/config")
def update_config(payload: dict):
    with open(CONFIG_PATH, "r") as f:
        cfg = json.load(f)
    cfg.update(payload)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    return {"status": "success", "config": cfg}

@app.post("/api/config/toggle/{key}")
def toggle_config(key: str):
    with open(CONFIG_PATH, "r") as f:
        cfg = json.load(f)
    cfg[key] = not cfg.get(key, False)
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    return {"status": "success", "key": key, "value": cfg[key]}

@app.post("/api/config/gun/{gun}")
def set_gun(gun: str, enabled: bool):
    with open(CONFIG_PATH, "r") as f:
        cfg = json.load(f)
    if "no_recoil" not in cfg:
        cfg["no_recoil"] = {}
    cfg["no_recoil"][gun] = enabled
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2)
    return {"status": "success"}

@app.post("/api/compile")
def trigger_compile():
    return compile_pak()

@app.get("/api/download")
def download_pak():
    files = [f for f in os.listdir(RESULT_DIR) if f.endswith((".pak", ".obb"))]
    if not files:
        return JSONResponse(status_code=404, content={"error": "No compiled PAK found."})
    target_path = os.path.join(RESULT_DIR, files[0])
    return FileResponse(target_path, filename=files[0], media_type="application/octet-stream")
