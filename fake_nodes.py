import json
import os
import random
import signal
import sys
import time
from datetime import datetime, timezone

import paho.mqtt.client as mqtt

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
SITE_ID = os.getenv("SITE_ID", "utd-test-lab")
NODE_COUNT = int(os.getenv("NODE_COUNT", "5"))
PUBLISH_INTERVAL_SECONDS = float(os.getenv("PUBLISH_INTERVAL_SECONDS", "2"))
TOPIC_PREFIX = os.getenv("TOPIC_PREFIX", "radiation")

running = True
sequences = {f"detector-{i:03d}": 0 for i in range(1, NODE_COUNT + 1)}


def stop_handler(signum, frame):
    global running
    running = False


def make_payload(node_id: str) -> dict:
    sequences[node_id] += 1

    # Mostly normal background values, with occasional small spikes to test alerts.
    background = random.uniform(0.05, 0.18)
    spike = random.choice([0.0] * 18 + [random.uniform(0.15, 0.45)] + [random.uniform(0.85, 1.4)])
    dose_rate = round(background + spike, 4)
    counts_per_second = max(0, int(random.gauss(38 + dose_rate * 120, 5)))

    status = "ok"
    if dose_rate > 0.3:
        status = "warning"

    return {
        "node_id": node_id,
        "site_id": SITE_ID,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sensor_type": "simulated-radiation",
        "reading": {
            "dose_rate_usv_h": dose_rate,
            "counts_per_second": counts_per_second,
            "gamma_current": dose_rate,
            "gamma_average": round(max(0.0, dose_rate - random.uniform(0.01, 0.04)), 4),
            "gamma_max": round(dose_rate + random.uniform(0.01, 0.08), 4),
            "neutron_detected": False,
        },
        "location": {
            "lat": round(32.9857 + random.uniform(-0.001, 0.001), 6),
            "lon": round(-96.7502 + random.uniform(-0.001, 0.001), 6),
            "accuracy_m": round(random.uniform(3.0, 8.0), 2),
        },
        "battery_pct": round(random.uniform(72, 99), 1),
        "rssi": round(random.uniform(-74, -45), 1),
        "firmware_version": "sim-0.1.0",
        "status": status,
        "sequence": sequences[node_id],
    }


def main() -> int:
    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    client = mqtt.Client(client_id="radiation-simulator", clean_session=True)

    while running:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            client.loop_start()
            print(f"Simulator connected to mqtt://{MQTT_HOST}:{MQTT_PORT}", flush=True)
            break
        except Exception as exc:
            print(f"Waiting for MQTT broker: {exc}", flush=True)
            time.sleep(2)

    node_ids = list(sequences.keys())
    while running:
        for node_id in node_ids:
            payload = make_payload(node_id)
            topic = f"{TOPIC_PREFIX}/{SITE_ID}/{node_id}/telemetry"
            result = client.publish(topic, json.dumps(payload), qos=1)
            result.wait_for_publish(timeout=5)
            print(f"published {topic} dose={payload['reading']['dose_rate_usv_h']} status={payload['status']}", flush=True)
        time.sleep(PUBLISH_INTERVAL_SECONDS)

    client.loop_stop()
    client.disconnect()
    print("Simulator stopped", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
