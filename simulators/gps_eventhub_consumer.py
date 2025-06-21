import os
from azure.eventhub import EventHubConsumerClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient

# Fetch secrets from Azure Key Vault
KEY_VAULT_URI = os.getenv("KEY_VAULT_URI", "https://idtwin-dev-kv.vault.azure.net/")
credential = DefaultAzureCredential()
client = SecretClient(vault_url=KEY_VAULT_URI, credential=credential)

EVENT_HUB_CONN_STR = client.get_secret("GPS-EventHub-ConnStr").value
EVENT_HUB_NAME = client.get_secret("GPS-EventHub-Name").value
CONSUMER_GROUP = os.getenv('GPS_EVENT_HUB_CONSUMER_GROUP', '$Default')

def on_event(partition_context, event):
    print(f"[GPS] Partition: {partition_context.partition_id}")
    print(event.body_as_str())
    partition_context.update_checkpoint(event)

client = EventHubConsumerClient.from_connection_string(
    EVENT_HUB_CONN_STR,
    consumer_group=CONSUMER_GROUP,
    eventhub_name=EVENT_HUB_NAME
)

with client:
    print(f"Listening for GPS events on {EVENT_HUB_NAME}...")
    client.receive(
        on_event=on_event,
        starting_position="-1",
    )
