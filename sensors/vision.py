import subprocess
import os

class PatrolCam:
    def __init__(self, output_path="captures/"):
        self.output_path = output_path
        if not os.path.exists(self.output_path):
            os.makedirs(self.output_path)

    def take_snapshot(self, filename="intruder.jpg"):
        """Captures a high-res image for evidence."""
        full_path = os.path.join(self.output_path, filename)
        try:
            # Using rpicam-jpeg for the most stable capture in Trixie
            subprocess.run([
                "rpicam-jpeg", 
                "-o", full_path, 
                "-t", "1000",   # 1 second warmup
                "--width", "1280", 
                "--height", "720",
                "--immediate"   # Skip preview to save CPU
            ], check=True)
            return full_path
        except subprocess.CalledProcessError:
            print("Camera Capture Failed!")
            return None

    def check_presence(self):
        """Placeholder for future ML/Motion logic."""
        # This is where we will later add pixel-diff or ML scans
        pass