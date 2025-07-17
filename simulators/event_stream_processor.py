import os
from dotenv import load_dotenv
# Always load .env from project root before anything else
def _load_root_env():
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    load_dotenv(dotenv_path=os.path.join(root_dir, '.env'), override=True)
_load_root_env()

import json
import asyncio
import argparse
import signal
import sys
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

    # --- 4b. Ensure Composite Index for All Streams ---
    # Define composite index requirements for each stream type
    composite_index_map = {
        "scada": [
            {"path": "/MachineID", "order": "ascending"},
            {"path": "/_ts", "order": "descending"}
        ],
        "plc": [
            {"path": "/plcId", "order": "ascending"},
            {"path": "/_ts", "order": "descending"}
        ],
        "gps": [
            {"path": "/deviceId", "order": "ascending"},
            {"path": "/_ts", "order": "descending"}
        ]
    }
    if stream_type in composite_index_map:
        try:
            print(f"Ensuring composite index for {cosmos_container_name} container...")
            # Re-open management client for this operation (ensure context is valid)
            credential2 = DefaultAzureCredential()
            management_client2 = CosmosDBManagementClient(credential2, subscription_id)
            container = await management_client2.sql_resources.get_sql_container(
                resource_group_name=resource_group_name,
                account_name=cosmos_db_account_name,
                database_name=cosmos_database_name,
                container_name=cosmos_container_name
            )
            policy = container.resource.indexing_policy
            composite_needed = composite_index_map[stream_type]
            found = False
            for comp in getattr(policy, 'composite_indexes', []) or []:
                if (len(comp) == 2 and
                    comp[0].path == composite_needed[0]["path"] and comp[0].order == composite_needed[0]["order"] and
                    comp[1].path == composite_needed[1]["path"] and comp[1].order == composite_needed[1]["order"]):
                    found = True
                    break
            if not found:
                print(f"Adding composite index for {composite_needed[0]['path']} ASC, {composite_needed[1]['path']} DESC...")
                if not policy.composite_indexes:
                    policy.composite_indexes = []
                # Use the same type as existing composite index objects if present, else fallback to dict
                comp_type = type(comp[0]) if (getattr(policy, 'composite_indexes', []) and len(policy.composite_indexes) > 0 and len(policy.composite_indexes[0]) > 0) else dict
                policy.composite_indexes.append([
                    comp_type(path=composite_needed[0]["path"], order=composite_needed[0]["order"]),
                    comp_type(path=composite_needed[1]["path"], order=composite_needed[1]["order"])
                ])
                await management_client2.sql_resources.begin_create_update_sql_container(
                    resource_group_name=resource_group_name,
                    account_name=cosmos_db_account_name,
                    database_name=cosmos_database_name,
                    container_name=cosmos_container_name,
                    create_update_sql_container_parameters=SqlContainerCreateUpdateParameters(
                        resource=SqlContainerResource(
                            id=cosmos_container_name,
                            partition_key=ContainerPartitionKey(paths=[cosmos_partition_key_path], kind="Hash"),
                            indexing_policy=policy
                        )
                    )
                )
                print("Composite index added.")
            else:
                print("Composite index already present.")
            await management_client2.close()
            await credential2.close()
        except Exception as e:
            print(f"Error ensuring composite index for {cosmos_container_name}: {e}")

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
    
    running = True
    def handle_signal(signum, frame):
        nonlocal running
        print(f"\nReceived signal {signum}, shutting down event stream processor...")
        running = False
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

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

    # Replace the main event loop with a check for running
    while running:
        await asyncio.sleep(1)
    print("Event stream processor stopped.")
    sys.exit(0)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generic Event Stream Processor for Azure.")
    parser.add_argument(
        "--stream-type",
        type=str,
        required=True,
        choices=list(CONFIG_MAP.keys()) + ["all"],
        help="The type of event stream to process (e.g., scada, plc, gps, all)."
    )
    args = parser.parse_args()

    async def run_all_streams():
        tasks = [asyncio.create_task(main(stype)) for stype in CONFIG_MAP.keys()]
        await asyncio.gather(*tasks)

    if args.stream_type == "all":
        asyncio.run(run_all_streams())
    else:
        asyncio.run(main(args.stream_type))
