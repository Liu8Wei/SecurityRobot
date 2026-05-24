# =============================================================================
# test_motors.py — Standalone Motor Test Script
#
# PURPOSE:
#   Run this BEFORE plugging in main.py to confirm your L298N wiring is correct.
#   It tests each motor direction one at a time so you can verify:
#     - Both motors spin when they should
#     - Forward is actually forward (not backward)
#     - Left and right motors are not swapped
#
# HOW TO RUN (on the Pi via SSH):
#   1. sudo pigpiod          ← start the background service first
#   2. python3 test_motors.py
#
# WHAT TO WATCH:
#   The script will print what it's doing before it does it.
#   If a motor spins the wrong direction, swap the two wires going
#   into that motor (OUT1/OUT2 for left, OUT3/OUT4 for right).
# =============================================================================

import time
import sys

# sys.path.insert adds the parent folder to Python's search path.
# This lets us import config and drivers from the project root even though
# this test script might be run from a different folder.
sys.path.insert(0, '/home/pi/your_project_folder')  # ← change this to your actual path

import config
from drivers import motors


def pause(seconds, label):
    """Counts down a pause so you can see what's happening on the robot."""
    print(f"    Waiting {seconds}s... ({label})")
    time.sleep(seconds)


def run_tests():
    print("=" * 50)
    print("  MOTOR TEST SEQUENCE")
    print("  Make sure the robot is on a surface or lifted.")
    print("=" * 50)

    # --- STEP 1: Initialize ---
    # This connects to pigpio and sets up all pins.
    # If it fails here, check that you ran: sudo pigpiod
    print("\n[1] Initializing motor driver...")
    motors.init()
    print("    OK — pigpio connected, pins configured.")
    pause(1, "ready")

    # --- STEP 2: Low-speed forward ---
    # We start slow (speed=100, which is 100/255 ≈ 39%) to be safe.
    # If something is wired wrong, low speed causes less damage.
    print("\n[2] LOW SPEED FORWARD (39%)...")
    print("    Both wheels should spin FORWARD slowly.")
    motors.forward(speed=100)
    pause(2, "observe direction")
    motors.stop()
    pause(1, "stopped")

    # --- STEP 3: Full speed forward ---
    print("\n[3] FULL SPEED FORWARD (100%)...")
    print("    Both wheels forward at full speed.")
    motors.forward(speed=255)
    pause(2, "observe speed")
    motors.stop()
    pause(1, "stopped")

    # --- STEP 4: Reverse ---
    print("\n[4] REVERSE (78%)...")
    print("    Both wheels should spin BACKWARD.")
    motors.reverse(speed=200)
    pause(2, "observe direction")
    motors.stop()
    pause(1, "stopped")

    # --- STEP 5: Left turn ---
    # Left motor reverses, right motor goes forward.
    # Robot should rotate CLOCKWISE when viewed from above.
    print("\n[5] TURN LEFT (tank turn)...")
    print("    Left wheel BACKWARD, right wheel FORWARD.")
    print("    Robot should spin clockwise (nose turns left).")
    motors.turn_left(speed=180)
    pause(2, "observe turn")
    motors.stop()
    pause(1, "stopped")

    # --- STEP 6: Right turn ---
    print("\n[6] TURN RIGHT (tank turn)...")
    print("    Left wheel FORWARD, right wheel BACKWARD.")
    print("    Robot should spin counter-clockwise (nose turns right).")
    motors.turn_right(speed=180)
    pause(2, "observe turn")
    motors.stop()
    pause(1, "stopped")

    # --- STEP 7: set_speeds() directly ---
    # This tests the core function that main.py uses for joystick control.
    # Left motor at 60%, right motor at 30% → gentle curve to the right.
    print("\n[7] DIFFERENTIAL SPEED TEST...")
    print("    Left=150, Right=80 → robot should curve to the RIGHT.")
    motors.set_speeds(150, 80)
    pause(2, "observe curve")
    motors.stop()
    pause(1, "stopped")

    # --- DONE ---
    print("\n" + "=" * 50)
    print("  TEST COMPLETE")
    print()
    print("  If any step was wrong, check these:")
    print("  - Wrong direction on ONE motor → swap that motor's 2 wires")
    print("  - Both motors wrong direction  → swap L_MOTOR_FWD/REV in config.py")
    print("  - Motors didn't move at all    → check ENA/ENB jumpers are REMOVED")
    print("  - Only one motor works         → check IN3/IN4 or ENB wiring")
    print("=" * 50)


# =============================================================================
# This block only runs when you execute this file directly.
# It will NOT run if another file imports this file.
# That's the purpose of:  if __name__ == "__main__"
# =============================================================================
if __name__ == "__main__":
    try:
        run_tests()
    except KeyboardInterrupt:
        # If you press Ctrl+C during the test, this catches it cleanly
        # instead of crashing with an ugly error message.
        print("\n\n[!] Test interrupted by user (Ctrl+C).")
    finally:
        # finally: runs NO MATTER WHAT — even if there was an error or Ctrl+C.
        # This guarantees the motors always stop and GPIO is released.
        # Without this, motors could keep spinning after the script exits.
        print("[!] Running cleanup...")
        motors.cleanup()
        print("[!] Done. Motors stopped, GPIO released.")