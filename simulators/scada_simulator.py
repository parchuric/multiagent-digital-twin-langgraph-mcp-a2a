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

EVENT_HUB_CONN_STR = client.get_secret("SCADA-EventHub-ConnStr").value
EVENT_HUB_NAME = client.get_secret("SCADA-EventHub-Name").value
EVENT_RATE = int(os.getenv('SCADA_EVENT_RATE', '5'))  # events per second

producer = EventHubProducerClient.from_connection_string(
    conn_str=EVENT_HUB_CONN_STR,
    eventhub_name=EVENT_HUB_NAME
)

def generate_scada_event():
    return {
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        "facility_id": f"FAC_{random.choice(['DE','US','CN'])}_{random.randint(1,12):02}",
        "production_line_id": f"PL{random.randint(1,10)}",
        "equipment_tag": f"EQ{random.randint(100,999)}",
        "temperature": round(random.uniform(20, 100), 2),
        "pressure": round(random.uniform(1, 10), 2),
        "flow_rate": round(random.uniform(10, 100), 2),
        "vibration_amplitude": round(random.uniform(0, 5), 2),
        "power_consumption": round(random.uniform(100, 1000), 2),
        "product_quality_score": random.randint(80, 100),
        "throughput_rate": random.randint(50, 200),
        "alarm_status": random.choice(["OK", "WARN", "ALARM"]),
        "operational_mode": random.choice(["AUTO", "MANUAL"]),
        "efficiency_percentage": round(random.uniform(70, 100), 2),
        "maintenance_alerts": random.choice(["NONE", "DUE", "URGENT"])
    }

def main():
    print(f"Sending SCADA events to {EVENT_HUB_NAME} at {EVENT_RATE} events/sec...")
    while True:
        batch = []
        for _ in range(EVENT_RATE):
            event = generate_scada_event()
            batch.append(EventData(json.dumps(event)))
        with producer:
            producer.send_batch(batch)
        time.sleep(1)

if __name__ == "__main__":
    main()
