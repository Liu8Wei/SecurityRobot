# =============================================================================
# shared_state.py - Shared memory between main.py and dashboard.py
# =============================================================================

state = {
    "nav_status":     "Idle",
    "mission_active": False,
    "mode":           "Autonomous",
    "distance":       999.0,
    "ir_array":       "[1, 1, 1, 1, 1]",
    "bus_voltage":    11.8,
    "current_mA":     0,
    "arm_status":     "Stowed",
    "command":        None,
}
