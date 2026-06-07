# Interface Questions for Hardware / Research Team

These questions are not blockers for the prototype, but they will help make the first software stack compatible with the real detector stream.

## Detector Output

1. What exact fields will the radiation detector output?
   - dose rate?
   - counts per second?
   - current / average / maximum gamma reading?
   - spectrum bins or isotope ID?
   - neutron detection flag?
   - battery level?
   - GPS/location?
   - device health/status?

2. What units should the backend assume?
   - µSv/h for dose rate?
   - CPS for counts per second?
   - keV/channel for spectrum?

3. What sampling/publishing frequency is expected?
   - 1 Hz?
   - every 5 seconds?
   - event-based only?

## Connectivity

4. Will each detector publish directly over WiFi, or will an ESP32/Raspberry Pi act as a bridge?

5. Should the prototype broker run locally in the lab, on a Raspberry Pi gateway, or in the cloud?

6. Is temporary local-only operation acceptable if the internet drops?

## Dashboard / Operations

7. Is Grafana acceptable for the first dashboard prototype?

8. Are alert thresholds already defined, or should the software use configurable placeholders?

9. Should the first dashboard include GPS/map view, or only node table + time-series charts?

## Security / Deployment

10. Are there university/project constraints for cloud services, data storage, or network ports?

11. Should MQTT require authentication from the first prototype, or can the initial lab prototype run without auth and add security after functionality is validated?
