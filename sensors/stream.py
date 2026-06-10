# stream.py — run this separately on the Pi
import io
import picamera2
from http.server import BaseHTTPRequestHandler, HTTPServer

class StreamHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type',
                         'multipart/x-mixed-replace; boundary=frame')
        self.end_headers()
        camera = picamera2.Picamera2()
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
        except:
            camera.stop()

HTTPServer(('0.0.0.0', 8080), StreamHandler).serve_forever()