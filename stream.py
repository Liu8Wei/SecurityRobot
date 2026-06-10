import io
import time
import picamera2
from http.server import BaseHTTPRequestHandler, HTTPServer

class StreamHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type',
                         'multipart/x-mixed-replace; boundary=frame')
        self.end_headers()
        camera = picamera2.Picamera2()
        # LOW RES — much less data per frame
        config = camera.create_still_configuration(
            main={"size": (320, 240)}
        )
        camera.configure(config)
        camera.start()
        try:
            while True:
                buf = io.BytesIO()
                camera.capture_file(buf, format='jpeg')
                frame = buf.getvalue()
                self.wfile.write(b'--frame\r\n')
                self.wfile.write(b'Content-Type: image/jpeg\r\n\r\n')
                self.wfile.write(frame)
                self.wfile.write(b'\r\n')
                time.sleep(0.2)  # cap at ~5fps — saves bandwidth
        except:
            camera.stop()

print("Stream starting on port 8080 at 320x240, 5fps...")
HTTPServer(('0.0.0.0', 8080), StreamHandler).serve_forever()