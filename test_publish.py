"""One-shot MQTT test publisher for local debugging.

Run from project root after `docker compose up -d`:
    python scripts/test_publish.py
"""
import json
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

payload = {
    "node_id": "detector-test-001",
    "site_id": "utd-test-lab",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "sensor_type": "manual-test",
    "reading": {
        "dose_rate_usv_h": 0.42,
        "counts_per_second": 55,
        "gamma_current": 0.42,
        "gamma_average": 0.31,
        "gamma_max": 0.47
    },
    "battery_pct": 88,
    "rssi": -58,
    "status": "warning",
    "sequence": 1
}

client = mqtt.Client(client_id="manual-test-publisher")
client.connect("localhost", 1883, keepalive=60)
client.loop_start()
client.publish("radiation/utd-test-lab/detector-test-001/telemetry", json.dumps(payload), qos=1).wait_for_publish()
client.loop_stop()
client.disconnect()
print("Published one test message")
