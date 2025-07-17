import abc
from azure.eventhub import EventHubProducerClient, EventData
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from dotenv import load_dotenv
import os, json, uuid
from datetime import datetime, timezone

load_dotenv()
EVENT_HUB_NAME = "mcp-requests"

def get_event_hub_connection_str_from_keyvault():
    key_vault_uri = os.getenv("KEY_VAULT_URI")
    secret_name = "EventHub-A2A-ConnStr"
    credential = DefaultAzureCredential()
    secret_client = SecretClient(vault_url=key_vault_uri, credential=credential)
    return secret_client.get_secret(secret_name).value

class AgentCommunicator(abc.ABC):
    @abc.abstractmethod
    def register(self, agent_id, agent_type, capabilities):
        pass

    @abc.abstractmethod
    def send_message(self, message_type, payload):
        pass

    @abc.abstractmethod
    def receive_messages(self, callback):
        pass

class LegacyCommunicator(AgentCommunicator):
    def register(self, agent_id, agent_type, capabilities):
        # Existing direct registration logic
        print(f"Legacy register: {agent_id}")

    def send_message(self, message_type, payload):
        # Existing direct send logic
        print(f"Legacy send: {message_type}")

    def receive_messages(self, callback):
        # Existing direct receive logic
        print("Legacy receive")

class MCPCommunicator(AgentCommunicator):
    def __init__(self):
        self.conn_str = get_event_hub_connection_str_from_keyvault()

    def register(self, agent_id, agent_type, capabilities):
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
            conn_str=self.conn_str,
            eventhub_name=EVENT_HUB_NAME
        )
        event_data_batch = producer.create_batch()
        event_data_batch.add(EventData(json.dumps(message)))
        producer.send_batch(event_data_batch)
        producer.close()

    def send_message(self, message_type, payload):
        # Similar to register, but with different message_type/payload
        pass

    def receive_messages(self, callback):
        # Implement Event Hubs consumer logic here
        pass