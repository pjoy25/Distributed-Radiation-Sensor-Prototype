# Distributed Radiation Sensing Network Prototype

This repository is a professional starting scaffold for a distributed radiation sensing network software pipeline.

It proves the complete software flow before final radiation detector hardware is available:

```text
Simulated node / ESP32 node
  → MQTT broker
  → Python ingestion service
  → InfluxDB time-series database
  → Grafana dashboard
```

The design is hardware-independent. Once the real radiation sensors are ready, they only need to publish the agreed MQTT topic and JSON payload.

## Included Components

- **Mosquitto MQTT broker** for IoT message routing.
- **Python ingestion service** for MQTT subscription, JSON validation, alert-level calculation, and InfluxDB writes.
- **InfluxDB 2.x** for time-series storage.
- **Grafana** for dashboard visualization.
- **Python simulator** that publishes fake radiation telemetry from multiple nodes.
- **ESP32 + DHT22 Arduino sketch** as a physical stand-in sensor node.
- **JSON schema** for the telemetry contract.
- **Architecture and migration docs** for moving from simulated data to real detector streams.

## Quick Start

### 1. Open the folder in VS Code

```bash
cd radiation_network_prototype
code .
```

### 2. Start the core services

```bash
docker compose up -d --build
```

This starts:

- MQTT broker: `localhost:1883`
- InfluxDB: `http://localhost:8086`
- Grafana: `http://localhost:3000`
- Ingestion service

Default Grafana login:

```text
username: admin
password: admin
```

Default InfluxDB values are defined in `docker-compose.yml`. For serious deployment, copy `.env.example` to `.env` and replace the secrets.

### 3. Start simulated radiation nodes

```bash
docker compose --profile simulator up --build simulator
```

This publishes fake readings for 5 detector nodes.

### 4. Open Grafana

Go to:

```text
http://localhost:3000
```

Open the provisioned dashboard:

```text
Radiation Network / Radiation Network Prototype Overview
```

You should see live readings within a few seconds after the simulator starts.

## Useful Commands

View logs:

```bash
docker compose logs -f ingestion-service
```

Stop everything:

```bash
docker compose down
```

Stop and delete volumes/database data:

```bash
docker compose down -v
```

Publish one manual test message from your laptop:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install paho-mqtt==1.6.1
python scripts/test_publish.py
```

## MQTT Topic Pattern

```text
radiation/{site_id}/{node_id}/telemetry
```

Example:

```text
radiation/utd-test-lab/detector-001/telemetry
```

## Example Payload

```json
{
  "node_id": "detector-001",
  "site_id": "utd-test-lab",
  "timestamp": "2026-06-06T16:20:00Z",
  "sensor_type": "simulated-radiation",
  "reading": {
    "dose_rate_usv_h": 0.14,
    "counts_per_second": 38,
    "gamma_current": 0.14,
    "gamma_average": 0.12,
    "gamma_max": 0.21,
    "neutron_detected": false
  },
  "battery_pct": 91,
  "rssi": -62,
  "status": "ok",
  "sequence": 42
}
```

## How Real Sensors Plug In Later

A real detector can integrate in either way:

```text
Detector → ESP32/Raspberry Pi bridge → MQTT
```

or:

```text
Detector with WiFi firmware → MQTT
```

As long as it publishes to the same topic pattern and payload schema, the broker, ingestion service, database, and dashboard do not need to be redesigned.

## Suggested Next Steps

1. Run the Docker prototype locally.
2. Confirm simulated readings reach Grafana.
3. Review and adjust `schema/telemetry.schema.json` with the team.
4. Ask the hardware team what fields the real detector will output.
5. Flash the ESP32 DHT22 sketch and publish real stand-in sensor readings.
6. Replace DHT22 fields with detector fields when hardware is ready.

## Important Security Note

The prototype uses anonymous MQTT and default local credentials to keep the first lab setup simple. Before any real deployment, add:

- MQTT username/password
- MQTT ACLs per device
- TLS encryption
- rotated InfluxDB tokens
- proper network firewall rules
