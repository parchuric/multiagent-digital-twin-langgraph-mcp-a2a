import os
import time
import json
import random
from azure.eventhub import EventHubProducerClient, EventData
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

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
    return {
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        "vehicle_id": f"VEH{random.randint(1000,9999)}",
        "facility_origin": f"FAC_{random.choice(['DE','US','CN'])}_{random.randint(1,12):02}",
        "facility_destination": f"FAC_{random.choice(['DE','US','CN'])}_{random.randint(1,12):02}",
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
    while True:
        batch = []
        for _ in range(EVENT_RATE):
            event = generate_gps_event()
            batch.append(EventData(json.dumps(event)))
        with producer:
            producer.send_batch(batch)
        time.sleep(1)

if __name__ == "__main__":
    main()
