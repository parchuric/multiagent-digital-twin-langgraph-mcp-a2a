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

EVENT_HUB_CONN_STR = client.get_secret("PLC-EventHub-ConnStr").value
EVENT_HUB_NAME = client.get_secret("PLC-EventHub-Name").value
EVENT_RATE = int(os.getenv('PLC_EVENT_RATE', '5'))  # events per second

producer = EventHubProducerClient.from_connection_string(
    conn_str=EVENT_HUB_CONN_STR,
    eventhub_name=EVENT_HUB_NAME
)

def generate_plc_event():
    return {
        "id": str(uuid.uuid4()),
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        "facility_id": f"FAC_{random.choice(['DE','US','CN'])}_{random.randint(1,12):02}",
        "plcId": f"PLC_{random.randint(1,20)}",
        "equipment_type": random.choice(["ROBOT", "CONVEYOR", "PRESS", "PAINT"]),
        "input_registers": [random.randint(0, 1) for _ in range(8)],
        "output_registers": [random.randint(0, 1) for _ in range(8)],
        "program_state": random.choice(["RUN", "STOP", "ERROR"]),
        "cycle_time": round(random.uniform(0.5, 2.0), 2),
        "error_codes": random.choices([0, 101, 202, 303], k=2),
        "memory_usage": round(random.uniform(30, 90), 2),
        "io_status": random.choice(["OK", "FAULT"]),
        "communication_health": random.choice(["GOOD", "DEGRADED", "LOST"]),
        "performance_degradation_score": round(random.uniform(0, 1), 2),
        "safety_interlocks": random.choice(["ENGAGED", "DISENGAGED"]),
        "diagnostic_codes": random.choices([0, 10, 20, 30], k=2)
    }

def main():
    print(f"Sending PLC events to {EVENT_HUB_NAME} at {EVENT_RATE} events/sec...")
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
            event = generate_plc_event()
            batch.append(EventData(json.dumps(event)))
        with producer:
            producer.send_batch(batch)
        time.sleep(1)
    print("Simulator stopped.")
    sys.exit(0)

if __name__ == "__main__":
    main()
