import socket
import cv2
import time
from flask import Flask, render_template_string, jsonify, request, Response
import numpy as np
# ── MEMORY CORE (Replaces shared_state.py) ───────────────────────────────────
state = {
    "mode": "Manual Override",
    "nav_status": "Idle",
    "vision_status": "Awaiting Video...",
    "ir_array": "[0, 0, 0, 0, 0]",
    "distance": 0,
    "bus_voltage": 0.0,
    "current_mA": 0,
    "arm_status": "Stowed",
    "command": None,
    "mission_active": False
}

_latest_frame = None

def set_frame(frame):
    global _latest_frame
    _latest_frame = frame

def get_frame():
    return _latest_frame

# ── VIDEO STREAM GENERATOR ───────────────────────────────────────────────────
def gen_frames():
    while True:
        frame = get_frame()
        if frame is not None:
            _, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            time.sleep(0.05)
        else:
            # Generate a black "NO SIGNAL" placeholder image
            dummy = np.zeros((240, 320, 3), dtype=np.uint8)
            cv2.putText(dummy, "NO SIGNAL", (80, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)
            cv2.putText(dummy, "Start main.py", (90, 160), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 1)
            _, jpeg = cv2.imencode('.jpg', dummy)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            time.sleep(1.0) # Only check once a second if camera is dead
# ── AUTO-DETECT IP ───────────────────────────────────────────────────────────
def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except:
        return '127.0.0.1'
    finally:
        s.close()

PI_IP = get_ip()
app = Flask(__name__)

# ── PASSWORD PROTECTION ──────────────────────────────────────────────────────
USERNAME = 'idp'
PASSWORD = 'group5'

def check_auth(u, p):
    return u == USERNAME and p == PASSWORD

def require_auth():
    return Response('Login Required', 401, {'WWW-Authenticate': 'Basic realm="PatrolBot IDP Group 5"'})

@app.before_request
def authenticate():
    auth = request.authorization
    if not auth or not check_auth(auth.username, auth.password):
        return require_auth()

@app.after_request
def kill_cache(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response

# ── HTML DASHBOARD ───────────────────────────────────────────────────────────
HTML = """
<!DOCTYPE html>
<html>
<head>
  <title>AGV Manipulator Console</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <style>
    body { background: #111424; color: #e2e8f0; font-family: -apple-system, system-ui, sans-serif; padding: 15px; margin: 0; user-select: none; }
    .blynk-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #1e2538; padding-bottom: 10px; margin-bottom: 15px; }
    .blynk-title { font-size: 1.2em; font-weight: bold; color: #209cee; }
    .connection-led { width: 10px; height: 10px; background: #23d160; border-radius: 5px; box-shadow: 0 0 8px #23d160; }
    .blynk-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 15px; }
    .widget { background: #1a1f35; border-radius: 8px; padding: 12px; border-left: 4px solid #209cee; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }
    .widget.green { border-left-color: #23d160; }
    .widget.orange { border-left-color: #ffdd57; }
    .widget.red { border-left-color: #ff3860; }
    .widget-label { font-size: 0.75em; color: #6b7c96; text-transform: uppercase; font-weight: bold; letter-spacing: 0.5px; margin-bottom: 6px; }
    .widget-value { font-size: 1.5em; font-weight: bold; color: #ffffff; font-family: monospace; }
    .main-layout { display: grid; grid-template-columns: 1.3fr 1fr; gap: 15px; }
    .camera-card { background: #1a1f35; border-radius: 8px; padding: 10px; text-align: center; }
    img { width: 100%; border-radius: 6px; background: #090b11; max-height: 260px; object-fit: contain; }
    .btn-panel { background: #1a1f35; border-radius: 8px; padding: 15px; display: flex; flex-direction: column; justify-content: space-between; }
    .mode-row { display: flex; gap: 8px; margin-bottom: 15px; }
    .blynk-btn { flex: 1; background: #242b4d; border: none; color: #fff; padding: 12px; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 0.9em; }
    .blynk-btn.active-mode { background: #00d1b2; color: #111424; }
    .dpad-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; max-width: 220px; margin: 0 auto; }
    .dpad-btn { background: #242b4d; border: none; color: #fff; padding: 15px; border-radius: 6px; font-size: 1.1em; cursor: pointer; font-weight: bold; }
    .dpad-btn.halt { background: #ff3860; }
    @media (max-width: 650px) {
      .blynk-grid { grid-template-columns: 1fr 1fr; }
      .main-layout { grid-template-columns: 1fr; }
    }
  </style>
</head>
<body>
  <div class="blynk-header">
    <div class="blynk-title">AGV Manipulator Console</div>
    <div style="font-size:0.75em;color:#6b7c96;">IDP - Group 5</div>
    <div class="connection-led"></div>
  </div>
  <div class="blynk-grid">
    <div class="widget" id="edge-mode">
      <div class="widget-label">SYSTEM MODE</div>
      <div id="mode" class="widget-value">{{ state.mode }}</div>
    </div>
    <div class="widget orange">
      <div class="widget-label">NAV STATE</div>
      <div id="nav_status" class="widget-value">{{ state.nav_status }}</div>
    </div>
    <div class="widget">
      <div class="widget-label">IR ARRAY</div>
      <div id="ir_array" class="widget-value" style="color:#00d1b2;">{{ state.ir_array }}</div>
    </div>
    <div class="widget red" id="edge-dist">
      <div class="widget-label">ULTRASONIC</div>
      <div id="distance" class="widget-value">{{ state.distance }} cm</div>
    </div>
    <div class="widget green">
      <div class="widget-label">INA219 POWER</div>
      <div id="power_metrics" class="widget-value" style="color:#23d160;">{{ state.bus_voltage }}V / {{ state.current_mA }}mA</div>
    </div>
    <div class="widget">
      <div class="widget-label">ARM SEQUENCE</div>
      <div id="arm_status" class="widget-value">{{ state.arm_status }}</div>
    </div>
  </div>
  <div class="main-layout">
    <div class="camera-card">
      <div style="display:flex; justify-content:space-between; margin-bottom:6px;">
        <div class="widget-label">OPENCV LIVE FEED</div>
        <div id="vision_status" class="widget-label" style="color:#ffdd57; font-size: 1em;">Awaiting Video...</div>
      </div>
      <img src="/video_feed" onerror="this.alt='Camera Offline'" alt="Stream Loading...">
    </div>
    <div class="btn-panel">
      <div>
        <div class="widget-label">SYSTEM OVERRIDES</div>
        <div class="mode-row">
          <button id="btn-auto" class="blynk-btn" onclick="cmd('mode/auto')">AUTO</button>
          <button id="btn-manual" class="blynk-btn" onclick="cmd('mode/manual')">MANUAL</button>
        </div>
        <button class="blynk-btn" style="background:#23d160;color:#111424;width:100%;margin-bottom:20px;" onclick="cmd('arm/trigger')">Force Pick Routine</button>
      </div>
      <div>
        <div class="widget-label" style="text-align:center;">Virtual Pad Overrides</div>
        <div class="dpad-grid">
          <div></div><button class="dpad-btn" onclick="cmd('move/forward')">Up</button><div></div>
          <button class="dpad-btn" onclick="cmd('move/left')">Left</button>
          <button class="dpad-btn halt" onclick="cmd('move/stop')">HALT</button>
          <button class="dpad-btn" onclick="cmd('move/right')">Right</button>
          <div></div><button class="dpad-btn" onclick="cmd('move/reverse')">Down</button><div></div>
        </div>
      </div>
    </div>
  </div>
  <script>
    function cmd(action){fetch('/command/'+action+'?t='+Date.now()).then(r=>r.json());}
    setInterval(function(){
      fetch('/state?t='+Date.now()).then(r=>r.json()).then(data=>{
        document.getElementById('mode').innerText=data.mode;
        document.getElementById('nav_status').innerText=data.nav_status;
        document.getElementById('vision_status').innerText=data.vision_status;
        document.getElementById('ir_array').innerText=data.ir_array;
        document.getElementById('distance').innerText=data.distance+" cm";
        document.getElementById('power_metrics').innerText=data.bus_voltage+"V / "+data.current_mA+"mA";
        document.getElementById('arm_status').innerText=data.arm_status;
        if(data.mode==="Autonomous"){
          document.getElementById('btn-auto').className="blynk-btn active-mode";
          document.getElementById('btn-manual').className="blynk-btn";
          document.getElementById('edge-mode').style.borderLeftColor="#00d1b2";
        }else{
          document.getElementById('btn-auto').className="blynk-btn";
          document.getElementById('btn-manual').className="blynk-btn active-mode";
          document.getElementById('edge-mode').style.borderLeftColor="#ffdd57";
        }
        let d=document.getElementById('edge-dist');
        if(data.distance<15)d.style.borderLeftColor="#ff3860";
        else if(data.distance<30)d.style.borderLeftColor="#ffdd57";
        else d.style.borderLeftColor="#23d160";
      }).catch(err=>console.log(err));
    },400);
  </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML, state=state)

@app.route('/video_feed')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/command/<path:action>')
def command(action):
    if action == "mode/auto": state["mode"] = "Autonomous"; state["command"] = "mode_auto"
    elif action == "mode/manual": state["mode"] = "Manual Override"; state["command"] = "mode_manual"
    elif "move/" in action:
        move_dir = action.split("/")[1].upper()
        state["nav_status"] = f"Moving {move_dir}"
        state["command"] = action.split("/")[1].lower()
    elif action == "arm/trigger":
        state["arm_status"] = "Executing..."; state["command"] = "pick"
    return jsonify({"status": "synchronized"})

@app.route('/state')
def get_state():
    return jsonify(state)

# NO app.run() here. This file is strictly imported by main.py.

if __name__ == "__main__":
    print(f"========================================")
    print(f"  STANDALONE DASHBOARD TEST MODE")
    print(f"  http://{PI_IP}:5000")
    print(f"  Login: idp / group5")
    print(f"========================================")
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)