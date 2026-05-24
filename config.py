# =============================================================================
# config.py — Master Configuration (Corrected)
# Robot: 4-DOF Pick-and-Grab Towing Robot
# Controller: Raspberry Pi Zero 2W
# =============================================================================

# --- 1. Blynk Auth ---
BLYNK_AUTH = '53dbEEqyWdF93tPnCbu7h25sVxiQYmQ0'

# --- 2. L298N Motor Driver ---
# (Matches PDF Page 5 wiring table — chosen as the canonical wiring)
# IMPORTANT: Remove ENA and ENB jumpers from L298N board, otherwise
# PWM speed control will not work and motors run at full speed only.
L_MOTOR_FWD = 17    # GPIO17, Physical Pin 11 → IN1 (Left motor forward)
L_MOTOR_REV = 27    # GPIO27, Physical Pin 13 → IN2 (Left motor reverse)
L_MOTOR_ENA = 18    # GPIO18, Physical Pin 12 → ENA (Left PWM speed) ← WAS MISSING
R_MOTOR_FWD = 22    # GPIO22, Physical Pin 15 → IN3 (Right motor forward)
R_MOTOR_REV = 23    # GPIO23, Physical Pin 16 → IN4 (Right motor reverse)
R_MOTOR_ENB = 13    # GPIO13, Physical Pin 33 → ENB (Right PWM speed) ← WAS MISSING

# --- 3. HC-SR04 Ultrasonic Sensor ---
# FIX: PDF Page 15 incorrectly used GPIO27/GPIO22 (already taken by motors).
# Reassigned to safe, free pins.
# IMPORTANT: ECHO pin outputs 5V — use 1kΩ + 2kΩ voltage divider to drop to 3.3V.
TRIG_PIN = 24       # GPIO24, Physical Pin 18 → HC-SR04 TRIG  ← WAS MISSING
ECHO_PIN = 25       # GPIO25, Physical Pin 22 → HC-SR04 ECHO (via voltage divider!) ← WAS MISSING

# --- 4. PIR Motion Sensor ---
PIR_PIN = 4         # GPIO4,  Physical Pin 7  → HC-SR501 OUT  ← WAS MISSING

# --- 5. 5-Way IR Line Tracking Sensor (TCRT5000L) ---
# FIX: Original config only had 2 sensors. All 5 are now defined.
# (Matches PDF Page 18 table)
IR_SENSOR_1 = 5     # GPIO5,  Physical Pin 29 (Far Left)
IR_SENSOR_2 = 6     # GPIO6,  Physical Pin 31 (Centre-Left)
IR_SENSOR_3 = 12    # GPIO12, Physical Pin 32 (Centre)        ← WAS MISSING
IR_SENSOR_4 = 16    # GPIO16, Physical Pin 36 (Centre-Right)  ← WAS MISSING
IR_SENSOR_5 = 20    # GPIO20, Physical Pin 38 (Far Right)     ← WAS MISSING

# Legacy aliases for backwards compatibility with any code using old names
SENSOR_LEFT  = IR_SENSOR_1
SENSOR_RIGHT = IR_SENSOR_5

# --- 6. 4x SG90 Servo Motors (pigpio hardware PWM) ---
# All 4 servos use pigpio for smooth, jitter-free control.  ← ALL MISSING
SERVO_BASE     = 19  # GPIO19, Physical Pin 35 — Waist/Base rotation
SERVO_SHOULDER = 21  # GPIO21, Physical Pin 40 — Shoulder joint
SERVO_ELBOW    = 26  # GPIO26, Physical Pin 37 — Elbow joint
SERVO_GRIPPER  = 14  # GPIO14, Physical Pin 8  — Gripper open/close
# NOTE: GPIO14 is the UART TX pin. Disable the serial console first:
#   sudo raspi-config → Interface Options → Serial Port → disable login shell

# --- 7. INA219 Power Monitor (I2C — fixed hardware pins) ---
INA219_SDA     = 2      # GPIO2, Physical Pin 3 (I2C SDA — fixed)
INA219_SCL     = 3      # GPIO3, Physical Pin 5 (I2C SCL — fixed)
INA219_ADDRESS = 0x40   # Default I2C address for INA219  ← WAS MISSING

# --- 8. Safety & Operational Thresholds ---
STOP_DISTANCE_CM    = 20.0   # Robot stops if obstacle closer than this
WARNING_DISTANCE_CM = 50.0   # Robot slows/warns if obstacle within this range
BATTERY_MIN_V       = 9.0    # 4S Li-ion fully discharged (2.25V/cell)
BATTERY_MAX_V       = 12.6   # 4S Li-ion fully charged (4.2V/cell)
BATTERY_LOW_PCT     = 20     # Trigger low-battery Blynk alert below this %

# --- 9. Servo PWM Pulse Widths (microseconds) for SG90 ---
SERVO_MIN_US  = 500    # ~0 degrees
SERVO_MID_US  = 1500   # ~90 degrees (neutral/home)
SERVO_MAX_US  = 2500   # ~180 degrees

# --- 10. Blynk Virtual Pin Map ---
V_JOYSTICK_X    = 1    # Joystick horizontal axis (manual drive)
V_OP_MODE       = 2    # Auto(0)/Manual(1) toggle button
V_ULTRASONIC_CM = 3    # Ultrasonic distance display (cm)
V_BATTERY_PCT   = 4    # Battery percentage gauge
V_JOYSTICK_Y    = 5    # Joystick vertical axis (manual drive)
V_LOG           = 6    # Terminal/log stream
V_IR_STATUS     = 7    # IR sensor array live status
V_MISSION       = 8    # Start(1)/Pause(0) mission button
V_THROTTLE      = 9    # Master speed slider (0–255)