import os
import time
import json
import random
import uuid
import signal
import sys
from azure.eventhub import EventHubProducerClient, EventData
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from dotenv import load_dotenv

# Always load .env from project root
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(dotenv_path=os.path.join(root_dir, '.env'))

# Fetch secrets from Azure Key Vault
KEY_VAULT_URI = os.getenv("KEY_VAULT_URI", "https://idtwin-dev-kv.vault.azure.net/")
credential = DefaultAzureCredential()
client = SecretClient(vault_url=KEY_VAULT_URI, credential=credential)

EVENT_HUB_CONN_STR = client.get_secret("GPS-EventHub-ConnStr").value
EVENT_HUB_NAME = client.get_secret("GPS-EventHub-Name").value
EVENT_RATE = int(os.getenv('GPS_EVENT_RATE', '5'))  # events per second

producer = EventHubProducerClient.from_connection_string(
    conn_str=EVENT_HUB_CONN_STR,
    eventhub_name=EVENT_HUB_NAME
)

def generate_gps_event():
    # Always use current UTC time for timestamp in ISO 8601 format
    return {
        "id": str(uuid.uuid4()),
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        "deviceId": f"DEV_{random.randint(1000,9999)}",
        "facility_origin": random.choice([
            "FAC_KR_01", "FAC_IN_01", "FAC_JP_01", "FAC_ZA_01", "FAC_AE_01", "FAC_BR_01",
            "FAC_DE_07", "FAC_DE_08", "FAC_DE_12", "FAC_DE_03", "FAC_DE_01", "FAC_DE_06", "FAC_DE_05", "FAC_DE_10", "FAC_DE_09", "FAC_DE_11",
            "FAC_US_10", "FAC_US_03", "FAC_US_11", "FAC_US_09", "FAC_US_12", "FAC_US_01", "FAC_US_02", "FAC_US_07", "FAC_US_08", "FAC_US_04",
            "FAC_CN_11", "FAC_CN_07", "FAC_CN_06", "FAC_CN_05", "FAC_CN_03", "FAC_CN_12", "FAC_CN_01", "FAC_CN_02", "FAC_CN_08", "FAC_CN_04", "FAC_CN_10"
        ]),
        "facility_destination": random.choice([
            "FAC_KR_01", "FAC_IN_01", "FAC_JP_01", "FAC_ZA_01", "FAC_AE_01", "FAC_BR_01",
            "FAC_DE_07", "FAC_DE_08", "FAC_DE_12", "FAC_DE_03", "FAC_DE_01", "FAC_DE_06", "FAC_DE_05", "FAC_DE_10", "FAC_DE_09", "FAC_DE_11",
            "FAC_US_10", "FAC_US_03", "FAC_US_11", "FAC_US_09", "FAC_US_12", "FAC_US_01", "FAC_US_02", "FAC_US_07", "FAC_US_08", "FAC_US_04",
            "FAC_CN_11", "FAC_CN_07", "FAC_CN_06", "FAC_CN_05", "FAC_CN_03", "FAC_CN_12", "FAC_CN_01", "FAC_CN_02", "FAC_CN_08", "FAC_CN_04", "FAC_CN_10"
        ]),
        "latitude": round(random.uniform(-90, 90), 6),
        "longitude": round(random.uniform(-180, 180), 6),
        "altitude": round(random.uniform(0, 1000), 2),
        "speed": round(random.uniform(0, 120), 2),
        "heading": random.randint(0, 359),
        "route_efficiency": round(random.uniform(0.7, 1.0), 2),
        "delivery_status": random.choice(["IN_TRANSIT", "DELIVERED", "DELAYED"]),
        "cargo_type": random.choice(["PARTS", "RAW", "FINISHED"]),
        "cargo_value": random.randint(1000, 100000),
        "temperature_controlled": random.choice([True, False]),
        "customs_status": random.choice(["CLEARED", "PENDING", "HELD"]),
        "estimated_arrival": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(time.time() + random.randint(3600, 7200))),
        "geofence_violations": random.randint(0, 2),
        "driver_performance": round(random.uniform(0.7, 1.0), 2)
    }

def main():
    print(f"Sending GPS events to {EVENT_HUB_NAME} at {EVENT_RATE} events/sec...")
    running = True
    def handle_signal(signum, frame):
        nonlocal running
        print(f"\nReceived signal {signum}, shutting down...")
        running = False
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    try:
        with producer:
            while running:
                batch = []
                for _ in range(EVENT_RATE):
                    event = generate_gps_event()
                    batch.append(EventData(json.dumps(event)))
                producer.send_batch(batch)
                # Use shorter sleep for more responsive shutdown
                for _ in range(10):
                    if not running:
                        break
                    time.sleep(0.1)
    finally:
        print("Simulator stopped.")
        sys.exit(0)

if __name__ == "__main__":
    main()
