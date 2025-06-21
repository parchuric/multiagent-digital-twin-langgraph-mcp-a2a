# Data Simulators for Azure Event Hubs (SCADA, PLC, GPS)

This directory contains three minimal Python simulators for sending test events to your Azure Event Hubs:

- `scada_simulator.py` → scada-production-hub
- `plc_simulator.py`   → plc-control-hub
- `gps_simulator.py`   → gps-logistics-hub

## Prerequisites
- Python 3.8+
- Install dependencies:
  ```sh
  pip install -r requirements.txt
  ```
- Set up Azure Event Hubs and obtain connection strings for each hub.

## Usage
Set the required environment variables and run the desired simulator:

### SCADA Simulator
```sh
set SCADA_EVENT_HUB_CONN_STR=...  # Your Event Hub connection string
set SCADA_EVENT_HUB_NAME=scada-production-hub
python scada_simulator.py
```

### PLC Simulator
```sh
set PLC_EVENT_HUB_CONN_STR=...  # Your Event Hub connection string
set PLC_EVENT_HUB_NAME=plc-control-hub
python plc_simulator.py
```

### GPS Simulator
```sh
set GPS_EVENT_HUB_CONN_STR=...  # Your Event Hub connection string
set GPS_EVENT_HUB_NAME=gps-logistics-hub
python gps_simulator.py
```

You can also set the event rate (events per second) with `SCADA_EVENT_RATE`, `PLC_EVENT_RATE`, or `GPS_EVENT_RATE`.

## Notes
- Each script sends a batch of events every second.
- Edit the scripts to customize event payloads or rates as needed.
- These simulators are for dev/test use only.
