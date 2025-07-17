import os
import time
import json
import random
import uuid
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

EVENT_HUB_CONN_STR = client.get_secret("SCADA-EventHub-ConnStr").value
EVENT_HUB_NAME = client.get_secret("SCADA-EventHub-Name").value
EVENT_RATE = int(os.getenv('SCADA_EVENT_RATE', '5'))  # events per second

producer = EventHubProducerClient.from_connection_string(
    conn_str=EVENT_HUB_CONN_STR,
    eventhub_name=EVENT_HUB_NAME
)

def generate_scada_event():
    return {
        "id": str(uuid.uuid4()),
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        "MachineID": f"SCADA_{random.randint(1, 100)}",
        "facility_id": random.choice([
            "FAC_KR_01", "FAC_IN_01", "FAC_JP_01", "FAC_ZA_01", "FAC_AE_01", "FAC_BR_01",
            "FAC_DE_07", "FAC_DE_08", "FAC_DE_12", "FAC_DE_03", "FAC_DE_01", "FAC_DE_06", "FAC_DE_05", "FAC_DE_10", "FAC_DE_09", "FAC_DE_11",
            "FAC_US_10", "FAC_US_03", "FAC_US_11", "FAC_US_09", "FAC_US_12", "FAC_US_01", "FAC_US_02", "FAC_US_07", "FAC_US_08", "FAC_US_04",
            "FAC_CN_11", "FAC_CN_07", "FAC_CN_06", "FAC_CN_05", "FAC_CN_03", "FAC_CN_12", "FAC_CN_01", "FAC_CN_02", "FAC_CN_08", "FAC_CN_04", "FAC_CN_10"
        ]),
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
    running = True
    def handle_signal(signum, frame):
        nonlocal running
        print(f"\nReceived signal {signum}, shutting down...")
        running = False
    import signal
    import sys
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    while running:
        batch = []
        for _ in range(EVENT_RATE):
            event = generate_scada_event()
            batch.append(EventData(json.dumps(event)))
        with producer:
            producer.send_batch(batch)
        time.sleep(1)
    print("Simulator stopped.")
    sys.exit(0)

if __name__ == "__main__":
    main()
