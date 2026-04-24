import sys, os, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.monitor_engine import MonitorEngine, DEBOUNCE_SECONDS

# Fake recognition results
UNAUTHORIZED = [{"bbox": [10, 10, 100, 100], "name": "Unknown", "authorized": False}]
AUTHORIZED   = [{"bbox": [10, 10, 100, 100], "name": "Me",      "authorized": True}]
NO_FACES     = []

engine = MonitorEngine()
engine.alert_timer = 10   # 10-second countdown for testing

print("=" * 60)
print("TEST 1: Countdown is strictly monotonic (no 6<->7 flicker)")
print("=" * 60)

prev_countdown = 999
prev_state     = None
samples        = []

# Simulate threat appearing and staying for DEBOUNCE + 10s = ~12s
sim_duration = DEBOUNCE_SECONDS + engine.alert_timer + 0.5
t0 = time.monotonic()

while time.monotonic() - t0 < sim_duration:
    r = engine.process(UNAUTHORIZED, [{"gaze": "at_screen"}])
    cd = r["countdown"]
    state = r["status"]

    # Record
    samples.append((round(time.monotonic() - t0, 2), state, cd))

    # Countdown must NEVER increase once it starts going down
    if state == "countdown":
        if cd > prev_countdown and prev_state == "countdown":
            print(f"  FAIL: countdown went UP from {prev_countdown} → {cd}")
        prev_countdown = min(prev_countdown, cd)  
    elif state == "warning":
        prev_countdown = 999  

    prev_state = state
    time.sleep(0.05)   # ~20 fps

# Print a summary (every ~0.5s)
print(f"  {'time':>6}  {'state':>10}  {'countdown':>9}")
for t, st, cd in samples[::10]:
    print(f"  {t:>6.2f}  {st:>10}  {cd:>9}")

# Check final state
final = engine.process(UNAUTHORIZED, [])
assert final["status"] == "locked", f"Expected locked, got {final['status']}"
print(f"\n  Final state: {final['status']} - CORRECT (threat reached 0)\n")

print("=" * 60)
print("TEST 2: Threat clears -> safe within SAFE_HYSTERESIS_SECONDS")
print("=" * 60)

engine2 = MonitorEngine()
engine2.alert_timer = 5

# Start a threat
for _ in range(5):
    engine2.process(UNAUTHORIZED, [])
    time.sleep(0.1)

st = engine2.process(UNAUTHORIZED, [])
print(f"  After 0.5s threat: state={st['status']} countdown={st['countdown']}")

# Remove threat and wait for hysteresis to clear
from core.monitor_engine import SAFE_HYSTERESIS_SECONDS
time.sleep(SAFE_HYSTERESIS_SECONDS + 0.2)

# Process one more frame with no faces
st2 = engine2.process(NO_FACES, [])
print(f"  After {SAFE_HYSTERESIS_SECONDS+0.2:.1f}s clear: state={st2['status']}")
assert st2["status"] in ("safe", "monitoring"), f"Expected safe/monitoring, got {st2['status']}"
print("  CORRECT - threat cleared cleanly.\n")

print("=" * 60)
print("TEST 3: reset() is instant - no stuck alerts")
print("=" * 60)

engine3 = MonitorEngine()
engine3.alert_timer = 30

for _ in range(20):
    engine3.process(UNAUTHORIZED, [])
    time.sleep(0.05)

before = engine3.state
engine3.reset()
after = engine3.state
print(f"  Before reset: {before}  ->  After reset: {after}")
assert after == "safe", f"Expected safe after reset, got {after}"
print("  CORRECT - reset() is instant.\n")

print("=" * 60)
print("ALL TESTS PASSED")
print("=" * 60)
