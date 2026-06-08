# =============================================================================
# config.py - Master Configuration (Updated for A4950 + Correct Ultrasonic)
# Robot: 4-DOF Pick-and-Grab Towing Robot
# Controller: Raspberry Pi Zero 2W
# =============================================================================

# --- 1. Blynk Auth ---
BLYNK_AUTH = '53dbEEqyWdF93tPnCbu7h25sVxiQYmQ0'

# --- 2. A4950 Motor Driver ---
# Two A4950 chips, one per motor
# No ENA/ENB pins - speed controlled via PWM on IN1/IN2 directly
# Left motor:  IN1=GPIO17, IN2=GPIO24
# Right motor: IN1=GPIO25, IN2=GPIO23
L_MOTOR_FWD = 17    # GPIO17, Physical Pin 11 - Left IN1 (forward)
L_MOTOR_REV = 24    # GPIO24, Physical Pin 18 - Left IN2 (reverse)
R_MOTOR_FWD = 25    # GPIO25, Physical Pin 22 - Right IN1 (forward)
R_MOTOR_REV = 23    # GPIO23, Physical Pin 16 - Right IN2 (reverse)

# --- 3. HC-SR04 Ultrasonic Sensor ---
# TRIG=GPIO22, ECHO=GPIO27
# IMPORTANT: ECHO outputs 5V
# Use 1k + 2k voltage divider to drop to 3.3V before connecting to Pi
TRIG_PIN = 22       # GPIO22, Physical Pin 15 - HC-SR04 TRIG
ECHO_PIN = 27       # GPIO27, Physical Pin 13 - HC-SR04 ECHO (via voltage divider!)

# --- 4. PIR Motion Sensor ---
# REMOVED - not used in this project

# --- 5. 5-Way IR Line Tracking Sensor (TCRT5000L) ---
IR_SENSOR_1 = 5     # GPIO5,  Physical Pin 29 (Far Left)
IR_SENSOR_2 = 6     # GPIO6,  Physical Pin 31 (Centre-Left)
IR_SENSOR_3 = 12    # GPIO12, Physical Pin 32 (Centre)
IR_SENSOR_4 = 16    # GPIO16, Physical Pin 36 (Centre-Right)
IR_SENSOR_5 = 20    # GPIO20, Physical Pin 38 (Far Right)

# Legacy aliases
SENSOR_LEFT  = IR_SENSOR_1
SENSOR_RIGHT = IR_SENSOR_5

# --- 6. 4x SG90 Servo Motors (pigpio hardware PWM) ---
SERVO_BASE     = 19  # GPIO19, Physical Pin 35 - Waist/Base rotation
SERVO_SHOULDER = 21  # GPIO21, Physical Pin 40 - Shoulder joint
SERVO_ELBOW    = 26  # GPIO26, Physical Pin 37 - Elbow joint
SERVO_GRIPPER  = 14  # GPIO14, Physical Pin 8  - Gripper open/close
# NOTE: GPIO14 is UART TX pin. Disable serial console first:
#   sudo raspi-config -> Interface Options -> Serial Port -> disable login shell

# --- 7. INA219 Power Monitor (Hardware I2C) ---
INA219_SDA     = 2      # GPIO2, Physical Pin 3 (I2C SDA)
INA219_SCL     = 3      # GPIO3, Physical Pin 5 (I2C SCL)
INA219_ADDRESS = 0x40   # Default I2C address

# --- 8. Safety & Operational Thresholds ---
STOP_DISTANCE_CM    = 20.0   # Robot stops if obstacle closer than this
WARNING_DISTANCE_CM = 50.0   # Robot slows if obstacle within this range
BATTERY_MIN_V       = 9.0    # 4S Li-ion fully discharged (2.25V/cell)
BATTERY_MAX_V       = 12.6   # 4S Li-ion fully charged (4.2V/cell)
BATTERY_LOW_PCT     = 20     # Trigger low battery alert below this %

# --- 9. Servo PWM Pulse Widths (microseconds) for SG90 ---
SERVO_MIN_US  = 500    # 0 degrees
SERVO_MID_US  = 1500   # 90 degrees (neutral/home)
SERVO_MAX_US  = 2500   # 180 degrees

# --- 10. Blynk Virtual Pin Map ---
V_JOYSTICK_X    = 1    # Joystick horizontal (manual drive)
V_OP_MODE       = 2    # Auto(1)/Manual(0) toggle
V_ULTRASONIC_CM = 3    # Ultrasonic distance display (cm)
V_BATTERY_PCT   = 4    # Battery percentage gauge
V_JOYSTICK_Y    = 5    # Joystick vertical (manual drive)
V_LOG           = 6    # Terminal log stream
V_IR_STATUS     = 7    # IR sensor array status
V_MISSION       = 8    # Start(1)/Pause(0) mission
V_THROTTLE      = 9    # Master speed slider (0-255)