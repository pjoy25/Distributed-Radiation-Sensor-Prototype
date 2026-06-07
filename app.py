import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

import paho.mqtt.client as mqtt
from dateutil import parser as dt_parser
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from jsonschema import Draft202012Validator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("radiation-ingestion")

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "radiation/+/+/telemetry")

INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "dev-super-secret-token-change-me")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "utd-radiation-lab")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "sensor_readings")
JSON_SCHEMA_PATH = os.getenv("JSON_SCHEMA_PATH", "/app/schema/telemetry.schema.json")

LEVEL1 = float(os.getenv("ALERT_THRESHOLD_LEVEL1_USV_H", "0.3"))
LEVEL2 = float(os.getenv("ALERT_THRESHOLD_LEVEL2_USV_H", "1.0"))
LEVEL3 = float(os.getenv("ALERT_THRESHOLD_LEVEL3_USV_H", "100.0"))

running = True


def load_schema(path: str) -> Draft202012Validator:
    with open(path, "r", encoding="utf-8") as f:
        schema = json.load(f)
    return Draft202012Validator(schema)


validator = load_schema(JSON_SCHEMA_PATH)

influx_client = InfluxDBClient(
    url=INFLUXDB_URL,
    token=INFLUXDB_TOKEN,
    org=INFLUXDB_ORG,
)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)


def parse_timestamp(value: str) -> datetime:
    try:
        dt = dt_parser.isoparse(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        logger.warning("Invalid timestamp %r; using server receive time", value)
        return datetime.now(timezone.utc)


def get_alert_level(dose_rate: float | None) -> Tuple[int, str]:
    if dose_rate is None:
        return 0, "no_radiation_field"
    if dose_rate > LEVEL3:
        return 3, "extreme"
    if dose_rate > LEVEL2:
        return 2, "very_dangerous"
    if dose_rate > LEVEL1:
        return 1, "warning"
    return 0, "normal"


def build_points(payload: Dict[str, Any], raw_topic: str) -> list[Point]:
    node_id = payload["node_id"]
    site_id = payload["site_id"]
    sensor_type = payload["sensor_type"]
    status = payload["status"]
    timestamp = parse_timestamp(payload["timestamp"])
    reading = payload.get("reading", {})

    base_tags = {
        "node_id": node_id,
        "site_id": site_id,
        "sensor_type": sensor_type,
        "status": status,
        "mqtt_topic": raw_topic,
    }

    point = Point("sensor_telemetry")
    for key, value in base_tags.items():
        point = point.tag(key, str(value))

    # Flexible reading fields. Numeric and boolean values become queryable Influx fields.
    for key, value in reading.items():
        if isinstance(value, (int, float, bool)) and value is not None:
            point = point.field(key, value)
        elif isinstance(value, str):
            point = point.field(key, value)

    for optional_field in ("battery_pct", "rssi", "sequence"):
        value = payload.get(optional_field)
        if isinstance(value, (int, float)) and value is not None:
            point = point.field(optional_field, value)

    location = payload.get("location") or {}
    if isinstance(location, dict):
        for field_name in ("lat", "lon", "accuracy_m"):
            value = location.get(field_name)
            if isinstance(value, (int, float)):
                point = point.field(f"location_{field_name}", value)

    point = point.time(timestamp, WritePrecision.NS)

    dose_rate = reading.get("dose_rate_usv_h") or reading.get("gamma_current")
    if not isinstance(dose_rate, (int, float)):
        dose_rate = None
    alert_level, alert_label = get_alert_level(float(dose_rate) if dose_rate is not None else None)

    alert_point = (
        Point("sensor_alerts")
        .tag("node_id", node_id)
        .tag("site_id", site_id)
        .tag("alert_label", alert_label)
        .field("alert_level", alert_level)
        .time(timestamp, WritePrecision.NS)
    )
    if dose_rate is not None:
        alert_point = alert_point.field("dose_rate_usv_h", float(dose_rate))

    return [point, alert_point]


def handle_payload(raw_topic: str, raw_payload: bytes) -> None:
    try:
        payload = json.loads(raw_payload.decode("utf-8"))
    except json.JSONDecodeError as exc:
        logger.error("Invalid JSON on topic=%s error=%s", raw_topic, exc)
        return

    errors = sorted(validator.iter_errors(payload), key=lambda e: e.path)
    if errors:
        for error in errors[:3]:
            logger.error("Schema validation failed topic=%s path=%s error=%s", raw_topic, list(error.path), error.message)
        return

    points = build_points(payload, raw_topic)
    try:
        write_api.write(bucket=INFLUXDB_BUCKET, org=INFLUXDB_ORG, record=points)
        logger.info("stored node=%s site=%s topic=%s", payload["node_id"], payload["site_id"], raw_topic)
    except Exception as exc:
        logger.exception("Failed writing to InfluxDB: %s", exc)


def on_connect(client: mqtt.Client, userdata: Any, flags: Dict[str, Any], rc: int) -> None:
    if rc == 0:
        logger.info("Connected to MQTT broker %s:%s", MQTT_HOST, MQTT_PORT)
        client.subscribe(MQTT_TOPIC, qos=1)
        logger.info("Subscribed to topic filter: %s", MQTT_TOPIC)
    else:
        logger.error("MQTT connection failed rc=%s", rc)


def on_message(client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
    handle_payload(msg.topic, msg.payload)


def stop_handler(signum: int, frame: Any) -> None:
    global running
    running = False


def wait_for_influx(max_attempts: int = 30) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            if influx_client.ping():
                logger.info("InfluxDB is reachable")
                return
        except Exception:
            pass
        logger.info("Waiting for InfluxDB... attempt %s/%s", attempt, max_attempts)
        time.sleep(2)
    raise RuntimeError("InfluxDB was not reachable after waiting")


def main() -> None:
    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)

    wait_for_influx()

    client = mqtt.Client(client_id="radiation-ingestion-service", clean_session=True)
    client.on_connect = on_connect
    client.on_message = on_message

    while running:
        try:
            client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
            client.loop_start()
            while running:
                time.sleep(1)
            client.loop_stop()
            client.disconnect()
        except Exception as exc:
            logger.error("MQTT loop error: %s. Reconnecting in 3 seconds...", exc)
            time.sleep(3)

    write_api.close()
    influx_client.close()
    logger.info("Ingestion service stopped")


if __name__ == "__main__":
    main()
