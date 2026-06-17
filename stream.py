# stream.py
import cv2
import time
from picamera2 import Picamera2
from http.server import BaseHTTPRequestHandler, HTTPServer

print("[CAMERA] Initializing...")
camera = Picamera2()
config = camera.create_preview_configuration(main={"size": (320, 240)})
camera.configure(config)
camera.start()
time.sleep(2)  # let camera warm up
print("[CAMERA] Ready at 320x240")

class StreamHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress request logs

    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type',
                         'multipart/x-mixed-replace; boundary=frame')
        self.end_headers()
        try:
            while True: 
                buf = camera.capture_array()
                buf = cv2.cvtColor(buf, cv2.COLOR_RGB2BGR)
                _, jpeg = cv2.imencode('.jpg', buf, 
                                       [cv2.IMWRITE_JPEG_QUALITY, 70])
                frame = jpeg.tobytes()
                self.wfile.write(b'--frame\r\n')
                self.wfile.write(b'Content-Type: image/jpeg\r\n\r\n')
                self.wfile.write(frame)
                self.wfile.write(b'\r\n')
                time.sleep(0.1)  # 10fps
        except:
            pass

if __name__ == "__main__":
    print("Stream on http://0.0.0.0:8080")
    HTTPServer(('0.0.0.0', 8080), StreamHandler).serve_forever()