from flask import Flask, render_template_string, jsonify, request
import time

app = Flask(__name__)

# ── AGV TELEMETRY STATE ──
state = {
    "mode": "Autonomous",         
    "nav_status": "Cruising (80%)",
    "ir_array": "[0, 0, 1, 0, 0]", 
    "distance": 45,               
    "bus_voltage": 16.2,          
    "current_mA": 450,            
    "arm_status": "Stowed"
}

# ── 🛠️ FIX 1: FORCE FLASK TO KILL BROWSER CACHING ──
@app.after_request
def kill_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>Blynk AGV Interface</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <style>
    /* Blynk App Aesthetic: Deep Flat Charcoal and Vibrantly Colored LEDs */
    body { background: #111424; color: #e2e8f0; font-family: -apple-system, system-ui, sans-serif; padding: 15px; margin: 0; user-select: none; }
    
    .blynk-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e2538; padding-bottom: 10px; margin-bottom: 15px; }
    .blynk-title { font-size: 1.2em; font-weight: bold; color: #209cee; letter-spacing: 0.5px; }
    .connection-led { width: 10px; height: 10px; background: #23d160; border-radius: 5px; box-shadow: 0 0 8px #23d160; }

    /* Blynk Grid Widget Blocks */
    .blynk-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 15px; }
    .widget { background: #1a1f35; border-radius: 8px; padding: 12px; border-left: 4px solid #209cee; position: relative; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
    .widget.green { border-left-color: #23d160; }
    .widget.orange { border-left-color: #ffdd57; }
    .widget.red { border-left-color: #ff3860; }
    
    .widget-label { font-size: 0.75em; color: #6b7c96; text-transform: uppercase; font-weight: bold; letter-spacing: 0.5px; margin-bottom: 6px; }
    .widget-value { font-size: 1.5em; font-weight: bold; color: #ffffff; font-family: monospace; }
    
    /* Blynk Status Pin (Internal LED indicator style) */
    .pin-status { display: inline-block; width: 8px; height: 8px; border-radius: 4px; margin-right: 6px; background: #6b7c96; }
    .pin-on { background: #23d160; box-shadow: 0 0 6px #23d160; }

    .main-layout { display: grid; grid-template-columns: 1.3fr 1fr; gap: 15px; }
    .camera-card { background: #1a1f35; border-radius: 8px; padding: 10px; text-align: center; }
    img { width: 100%; border-radius: 6px; background: #090b11; max-height: 260px; object-fit: contain; }

    /* Blynk Large Button Layouts */
    .btn-panel { background: #1a1f35; border-radius: 8px; padding: 15px; display: flex; flex-direction: column; justify-content: space-between; }
    .mode-row { display: flex; gap: 8px; margin-bottom: 15px; }
    .blynk-btn { flex: 1; background: #242b4d; border: none; color: #fff; padding: 12px; border-radius: 6px; font-weight: bold; cursor: pointer; transition: background 0.2s; font-size: 0.9em; }
    .blynk-btn:active { background: #209cee; }
    .blynk-btn.active-mode { background: #00d1b2; color: #111424; }
    
    /* Segmented D-Pad Control layout */
    .dpad-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; max-width: 220px; margin: 0 auto; }
    .dpad-btn { background: #242b4d; border: none; color: #fff; padding: 15px; border-radius: 6px; font-size: 1.1em; cursor: pointer; font-weight: bold; }
    .dpad-btn:active { background: #209cee; }
    .dpad-btn.halt { background: #ff3860; }
    .dpad-btn.halt:active { background: #bd1f40; }

    /* Responsive scaling for mobile phone frames */
    @media (max-width: 650px) {
      .blynk-grid { grid-template-columns: 1fr 1fr; gap: 8px; }
      .widget-value { font-size: 1.2em; }
      .main-layout { grid-template-columns: 1fr; gap: 12px; }
      .dpad-btn { padding: 18px; }
    }
  </style>
</head>
<body>

  <div class="blynk-header">
    <div class="blynk-title">VIRTUAL BLYNK INTERFACE</div>
    <div class="connection-led" title="System Synchronized"></div>
  </div>

  <div class="blynk-grid">
    <div class="widget" id="edge-mode">
      <div class="widget-label">📌 V0: Operating Mode</div>
      <div id="mode" class="widget-value">{{ state.mode }}</div>
    </div>
    <div class="widget orange">
      <div class="widget-label">📌 V1: Navigation Track</div>
      <div id="nav_status" class="widget-value">{{ state.nav_status }}</div>
    </div>
    <div class="widget">
      <div class="widget-label">📌 V2: 5-Way IR Array</div>
      <div id="ir_array" class="widget-value" style="color: #00d1b2;">{{ state.ir_array }}</div>
    </div>
    <div class="widget red" id="edge-dist">
      <div class="widget-label">📌 V3: Sonar Proximity</div>
      <div id="distance" class="widget-value">{{ state.distance }} cm</div>
    </div>
    <div class="widget green">
      <div class="widget-label">📌 V4: INA219 Telemetry</div>
      <div id="power_metrics" class="widget-value" style="color: #23d160;">{{ state.bus_voltage }}V / {{ state.current_mA }}mA</div>
    </div>
    <div class="widget">
      <div class="widget-label">📌 V5: Arm Sequencer</div>
      <div id="arm_status" class="widget-value">{{ state.arm_status }}</div>
    </div>
  </div>

  <div class="main-layout">
    <div class="camera-card">
      <div class="widget-label" style="text-align: left;">🎥 V6: Real-time OpenCV Target Stream</div>
      <img src="http://{{ request.host.split(':')[0] }}:8080" onerror="this.alt='Awaiting OpenCV Video Thread Pipeline...'" alt="Stream Loading...">
    </div>

    <div class="btn-panel">
      <div>
        <div class="widget-label">System State Hooks</div>
        <div class="mode-row">
          <button id="btn-auto" class="blynk-btn" onclick="cmd('mode/auto')">AUTO</button>
          <button id="btn-manual" class="blynk-btn" onclick="cmd('mode/manual')">MANUAL</button>
        </div>
        <button class="blynk-btn" style="background: #23d160; color:#111424; width:100%; margin-bottom: 20px;" onclick="cmd('arm/trigger')">⚡ RUN PICK ROUTINE</button>
      </div>

      <div>
        <div class="widget-label" style="text-align: center;">Virtual Pad Overrides</div>
        <div class="dpad-grid">
          <div></div><button class="dpad-btn" onclick="cmd('move/forward')">▲</button><div></div>
          <button class="dpad-btn" onclick="cmd('move/left')">◀</button>
          <button class="dpad-btn halt" onclick="cmd('move/stop')">■</button>
          <button class="dpad-btn" onclick="cmd('move/right')">▶</button>
          <div></div><button class="dpad-btn" onclick="cmd('move/reverse')">▼</button><div></div>
        </div>
      </div>
    </div>
  </div>

  <script>
    function cmd(action) {
      fetch('/command/' + action + '?nocache=' + Date.now()).then(r => r.json());
    }

    setInterval(function() {
      // Appending the time forced the phone/laptop browsers to always pull freshly generated data
      fetch('/state?t=' + Date.now())
        .then(response => response.json())
        .then(data => {
          document.getElementById('mode').innerText = data.mode;
          document.getElementById('nav_status').innerText = data.nav_status;
          document.getElementById('ir_array').innerText = data.ir_array;
          document.getElementById('distance').innerText = data.distance + " cm";
          document.getElementById('power_metrics').innerText = data.bus_voltage + "V / " + data.current_mA + "mA";
          document.getElementById('arm_status').innerText = data.arm_status;
          
          // Sync high-level button states stylistically 
          if(data.mode === "Autonomous") {
            document.getElementById('btn-auto').className = "blynk-btn active-mode";
            document.getElementById('btn-manual').className = "blynk-btn";
            document.getElementById('edge-mode').style.borderLeftColor = "#00d1b2";
          } else {
            document.getElementById('btn-auto').className = "blynk-btn";
            document.getElementById('btn-manual').className = "blynk-btn active-mode";
            document.getElementById('edge-mode').style.borderLeftColor = "#ffdd57";
          }

          // Dynamic warning colors based on sonar threshold limits
          let distWidget = document.getElementById('edge-dist');
          if (data.distance < 15) { distWidget.style.borderLeftColor = "#ff3860"; }
          else if (data.distance < 30) { distWidget.style.borderLeftColor = "#ffdd57"; }
          else { distWidget.style.borderLeftColor = "#23d160"; }
        }).catch(err => console.log(err));
    }, 400); // Ticks every 400ms for clean real-time syncing
  </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML, state=state, request=request)

@app.route('/command/<path:action>')
def command(action):
    if action == "mode/auto": state["mode"] = "Autonomous"
    elif action == "mode/manual": state["mode"] = "Manual Override"
    elif "move/" in action:
        move_dir = action.split("/")[1].upper()
        if state["mode"] == "Manual Override": state["nav_status"] = f"Moving {move_dir}"
    elif action == "arm/trigger": state["arm_status"] = "Executing..."
    return jsonify({"status": "synchronized"})

@app.route('/state')
def get_state():
    return jsonify(state)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=False)
