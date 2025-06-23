import os
import json
import asyncio
import argparse
from dotenv import load_dotenv
from azure.eventhub.aio import EventHubConsumerClient
from azure.cosmos.aio import CosmosClient
from azure.cosmos import PartitionKey
from azure.identity.aio import DefaultAzureCredential
from azure.keyvault.secrets.aio import SecretClient
# Import the management client and models
from azure.mgmt.cosmosdb.aio import CosmosDBManagementClient
from azure.mgmt.cosmosdb.models import (
    SqlDatabaseCreateUpdateParameters,
    SqlContainerCreateUpdateParameters,
    SqlContainerResource,
    ContainerPartitionKey,
    SqlDatabaseResource,
)


# Configuration mapping for different stream types
CONFIG_MAP = {
    "scada": {
        "eh_conn_str_secret": "SCADA-EventHub-ConnStr",
        "eh_name_secret": "SCADA-EventHub-Name",
        "cosmos_container": "scada_events",
        "partition_key": "/MachineID"
    },
    "plc": {
        "eh_conn_str_secret": "PLC-EventHub-ConnStr",
        "eh_name_secret": "PLC-EventHub-Name",
        "cosmos_container": "plc_events",
        "partition_key": "/plcId" # NOTE: Ensure your PLC events have a 'plcId' field.
    },
    "gps": {
        "eh_conn_str_secret": "GPS-EventHub-ConnStr",
        "eh_name_secret": "GPS-EventHub-Name",
        "cosmos_container": "gps_events",
        "partition_key": "/deviceId" # NOTE: Ensure your GPS events have a 'deviceId' field.
    }
}

async def get_secret(secret_client, secret_name):
    """Asynchronously retrieves a secret from Azure Key Vault."""
    try:
        secret = await secret_client.get_secret(secret_name)
        return secret.value
    except Exception as e:
        print(f"Error retrieving secret '{secret_name}': {e}")
        return None

async def on_event(partition_context, event, cosmos_container_client):
    """Callback function to process a single event."""
    event_data_str = None
    try:
        event_data_str = event.body_as_str()
        event_data = json.loads(event_data_str)
        # Log the received event on a single line for better parsing by the runner script
        print(f"[PROCESSOR] Received event: {json.dumps(event_data)}")

        # Insert the event data into Cosmos DB
        await cosmos_container_client.upsert_item(body=event_data)
        print(f"[PROCESSOR] Successfully inserted event with id '{event_data.get('id')}' into Cosmos DB container.")

        # Update the partition checkpoint
        await partition_context.update_checkpoint(event)
    except json.JSONDecodeError:
        print(f"Warning: Received non-JSON message on partition {partition_context.partition_id}. Skipping.")
    except Exception as e:
        print(f"Error processing event from partition {partition_context.partition_id}: {e}")
        # --- DIAGNOSTIC --- 
        # If an error occurs, print the data that caused it.
        print("--- FAILING EVENT DATA ---")
        print(event_data_str)
        print("--------------------------")

async def main(stream_type):
    """Main function to set up and run the event stream processor."""
    # --- 1. Load Environment Variables ---
    dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
    load_dotenv(dotenv_path=dotenv_path)

    key_vault_uri = os.getenv("KEY_VAULT_URI")
    subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
    resource_group_name = os.getenv("AZURE_RESOURCE_GROUP_NAME")
    cosmos_db_account_name = os.getenv("COSMOS_DB_ACCOUNT_NAME")

    if not all([key_vault_uri, subscription_id, resource_group_name, cosmos_db_account_name]):
        raise ValueError("One or more required environment variables are missing: KEY_VAULT_URI, AZURE_SUBSCRIPTION_ID, AZURE_RESOURCE_GROUP_NAME, COSMOS_DB_ACCOUNT_NAME")

    # --- 2. Configuration ---
    config = CONFIG_MAP.get(stream_type)
    if not config:
        raise ValueError(f"Invalid stream type: {stream_type}. Valid types are: {list(CONFIG_MAP.keys())}")

    cosmos_container_name = config["cosmos_container"]
    cosmos_partition_key_path = config["partition_key"]

    # --- 3. Initialize Azure Clients ---
    try:
        credential = DefaultAzureCredential()
        secret_client = SecretClient(vault_url=key_vault_uri, credential=credential)
        # Initialize the management client for Cosmos DB (Control Plane)
        management_client = CosmosDBManagementClient(credential, subscription_id)

        # Fetch secrets from Key Vault
        event_hub_conn_str = await get_secret(secret_client, config["eh_conn_str_secret"])
        event_hub_name = await get_secret(secret_client, config["eh_name_secret"])
        cosmos_db_endpoint = await get_secret(secret_client, "Cosmos-DB-Endpoint")
        cosmos_database_name = await get_secret(secret_client, "Cosmos-DB-DatabaseName")

        if not all([event_hub_conn_str, event_hub_name, cosmos_db_endpoint, cosmos_database_name]):
            print("Could not retrieve all necessary secrets from Key Vault. Exiting.")
            await credential.close()
            return

        # Initialize the data plane client for Cosmos DB
        cosmos_client = CosmosClient(url=cosmos_db_endpoint, credential=credential)
        
    except Exception as e:
        print(f"Failed to initialize Azure clients: {e}")
        await credential.close()
        return

    # --- 4. Ensure Cosmos DB Database and Container Exist (Control Plane) ---
    try:
        print(f"Ensuring database '{cosmos_database_name}' exists in account '{cosmos_db_account_name}'...")
        db_poller = await management_client.sql_resources.begin_create_update_sql_database(
            resource_group_name=resource_group_name,
            account_name=cosmos_db_account_name,
            database_name=cosmos_database_name,
            create_update_sql_database_parameters=SqlDatabaseCreateUpdateParameters(
                resource=SqlDatabaseResource(id=cosmos_database_name)
            )
        )
        await db_poller.result()
        print(f"Database '{cosmos_database_name}' ensured.")

        print(f"Ensuring container '{cosmos_container_name}' exists...")
        container_poller = await management_client.sql_resources.begin_create_update_sql_container(
            resource_group_name=resource_group_name,
            account_name=cosmos_db_account_name,
            database_name=cosmos_database_name,
            container_name=cosmos_container_name,
            create_update_sql_container_parameters=SqlContainerCreateUpdateParameters(
                resource=SqlContainerResource(
                    id=cosmos_container_name,
                    partition_key=ContainerPartitionKey(paths=[cosmos_partition_key_path], kind="Hash")
                )
            )
        )
        await container_poller.result()
        print(f"Container '{cosmos_container_name}' ensured with partition key '{cosmos_partition_key_path}'.")

    except Exception as e:
        print(f"Error ensuring Cosmos DB resources exist (control plane): {e}")
        print("Please ensure the identity running this script has the 'Cosmos DB Operator' role on the Cosmos DB account.")
        await credential.close()
        return
    finally:
        # It's important to close the management client after use.
        await management_client.close()

    # --- 5. Get Data Plane Client for the Container ---
    try:
        database_client = cosmos_client.get_database_client(cosmos_database_name)
        container_client = database_client.get_container_client(cosmos_container_name)
        # A quick read to verify data plane access. This is a lightweight operation.
        await container_client.read()
        print("Successfully connected to container and verified data plane access.")
    except Exception as e:
        print(f"Error connecting to container (data plane): {e}")
        print("Please ensure the identity running this script has the 'Cosmos DB Built-in Data Contributor' role on the Cosmos DB account.")
        await credential.close()
        await cosmos_client.close()
        return

    # --- 6. Start Event Hub Consumer ---
    consumer_client = EventHubConsumerClient.from_connection_string(
        conn_str=event_hub_conn_str,
        consumer_group="$Default",
        eventhub_name=event_hub_name,
    )

    print(f"Starting processor for '{stream_type}' stream. Listening for events on Event Hub: '{event_hub_name}'...")
    print("PROCESSOR_READY", flush=True)
    
    try:
        async with consumer_client:
            await consumer_client.receive(
                on_event=lambda pc, e: on_event(pc, e, container_client),
                starting_position="@latest",  # Start from the end of the stream, processing only new events
            )
    except KeyboardInterrupt:
        print("Stopping the processor.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        print("Closing clients.")
        await secret_client.close()
        await cosmos_client.close()
        await credential.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generic Event Stream Processor for Azure.")
    parser.add_argument(
        "--stream-type",
        type=str,
        required=True,
        choices=list(CONFIG_MAP.keys()),
        help="The type of event stream to process (e.g., scada, plc, gps)."
    )
    args = parser.parse_args()
    
    asyncio.run(main(args.stream_type))
