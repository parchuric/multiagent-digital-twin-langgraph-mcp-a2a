import os
import json
import uuid
from datetime import datetime, timezone
import time
import requests
from azure.eventhub import EventHubProducerClient, EventData
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from dotenv import load_dotenv

# Load .env to get KEY_VAULT_URI
load_dotenv()

# Configuration
EVENT_HUB_NAME = "mcp-requests"
SERVER_URL = "http://localhost:8000"

# Retrieve Event Hub connection string from Azure Key Vault
def get_event_hub_connection_str_from_keyvault():
    key_vault_uri = os.getenv("KEY_VAULT_URI")
    secret_name = "EventHub-A2A-ConnStr"  # Use the same secret name as your server
    if not key_vault_uri:
        raise RuntimeError("KEY_VAULT_URI environment variable not set (check your .env file)")
    credential = DefaultAzureCredential()
    secret_client = SecretClient(vault_url=key_vault_uri, credential=credential)
    return secret_client.get_secret(secret_name).value

EVENT_HUB_CONNECTION_STR = get_event_hub_connection_str_from_keyvault()

def send_registration_event(agent_id, agent_type, capabilities):
    message = {
        "header": {
            "message_id": str(uuid.uuid4()),
            "message_type": "agent.register",
            "source_agent_id": agent_id,
            "timestamp_utc": datetime.now(timezone.utc).isoformat()
        },
        "payload": {
            "agent_id": agent_id,
            "agent_type": agent_type,
            "capabilities": capabilities
        }
    }
    producer = EventHubProducerClient.from_connection_string(
        conn_str=EVENT_HUB_CONNECTION_STR,
        eventhub_name=EVENT_HUB_NAME
    )
    event_data_batch = producer.create_batch()
    event_data_batch.add(EventData(json.dumps(message)))
    producer.send_batch(event_data_batch)
    producer.close()

def test_agent_registration():
    agent_id = "test-agent-001"
    agent_type = "test-type"
    capabilities = ["foo", "bar"]

    send_registration_event(agent_id, agent_type, capabilities)

    # Wait a bit for the server to process the event
    time.sleep(3)

    # Check if the agent is registered via the HTTP API
    response = requests.get(f"{SERVER_URL}/agents")
    assert response.status_code == 200
    agents = response.json().get("agents", [])
    found = any(a.get("agent_id") == agent_id for a in agents)
    assert found, f"Agent {agent_id} not found in registered agents"

if __name__ == "__main__":
    test_agent_registration()
    print("Agent registration test passed.")