# Migration Path from Prototype to Real Radiation Sensors

## Phase 1 — Software Simulation

- Run Mosquitto, InfluxDB, Grafana, and ingestion service using Docker Compose.
- Run simulated radiation nodes publishing JSON over MQTT.
- Confirm data appears in Grafana.

## Phase 2 — ESP32 Stand-In Nodes

- Flash ESP32 + DHT22 sketch.
- ESP32 publishes to the same MQTT topic pattern.
- Backend continues working with no architectural changes.

## Phase 3 — ESP32 Bridge to Radiation Detector

If the detector has serial/UART/SPI/I2C output, ESP32 can act as bridge:

```text
Radiation Detector → ESP32 → WiFi/MQTT → Backend
```

Needed work:

- Parse detector output on ESP32.
- Map detector values to JSON `reading` fields.
- Preserve node_id, timestamp, status, sequence.

## Phase 4 — Native WiFi Radiation Detector

If the detector hardware can publish MQTT directly:

```text
Radiation Detector → WiFi/MQTT → Backend
```

Needed work:

- Implement same topic/payload contract in detector firmware.
- Confirm units and timestamps.
- Add authentication/security.

## Phase 5 — Production Hardening

- MQTT username/password, ACL, TLS certificates.
- Device registry and calibration metadata.
- Alert notification workflow.
- Offline buffering and retry strategy.
- Deployment on Raspberry Pi gateway, lab server, or cloud VM.
- Backups and retention policies for InfluxDB.
