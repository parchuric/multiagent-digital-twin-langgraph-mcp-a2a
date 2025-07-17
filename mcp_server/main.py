"""
Main entry point for the Model Context Protocol (MCP) Server.

This server acts as the central hub for a multi-agent system, facilitating
communication, context management, and orchestration between various intelligent agents.

It uses a hybrid architecture:
- Azure Event Hubs: As the scalable, underlying message bus for transport.
- Redis: For high-speed, in-memory state management (e.g., agent registration).
- FastAPI: As the web server framework.
"""

import asyncio
import json
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import redis.asyncio as redis
from azure.core.exceptions import ResourceNotFoundError
from azure.eventhub import EventData
from azure.eventhub.aio import EventHubConsumerClient, EventHubProducerClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

# --- Configuration ---
# Load .env from the project root to be robust
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(dotenv_path=os.path.join(project_root, '.env'))
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Pydantic Models for Message Validation ---
class MessageHeader(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    message_type: str
    source_agent_id: str
    destination_agent_id: str | None = None
    correlation_id: str | None = None
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class RegisterPayload(BaseModel):
    agent_id: str
    agent_type: str
    capabilities: list[str]

class MCPMessage(BaseModel):
    header: MessageHeader
    payload: dict

# --- Global State and Clients ---
producer_client = None
redis_client = None
consumer_client = None

# --- Key Vault Integration ---
KEY_VAULT_URI = os.getenv("KEY_VAULT_URI")
secret_client = None
if KEY_VAULT_URI:
    try:
        credential = DefaultAzureCredential()
        secret_client = SecretClient(vault_url=KEY_VAULT_URI, credential=credential)
        logging.info(f"Successfully connected to Key Vault: {KEY_VAULT_URI}")
    except Exception as e:
        logging.error(f"Failed to connect to Key Vault at {KEY_VAULT_URI}. Will rely solely on .env file. Error: {e}")
else:
    logging.warning("KEY_VAULT_URI not set. Will rely solely on .env file for secrets.")


def get_secret(secret_name_kv, secret_name_env=None, default_value=None, required=False):
    """
    Retrieves a secret, prioritizing Azure Key Vault then falling back to environment variables.
    
    Args:
        secret_name_kv (str): The exact (case-insensitive) name of the secret in Azure Key Vault.
        secret_name_env (str, optional): The environment variable name. If None, it's derived from secret_name_kv.
        default_value: The value to return if the secret is not found anywhere.
        required (bool): If True, raises an error if the secret is not found.
    """
    # If no specific env var name is given, create one from the KV name
    if secret_name_env is None:
        secret_name_env = secret_name_kv.upper().replace("-", "_")

    # 1. Try to get from Key Vault
    if secret_client:
        try:
            logging.info(f"Attempting to retrieve '{secret_name_kv}' from Key Vault...")
            retrieved_secret = secret_client.get_secret(secret_name_kv)
            value = retrieved_secret.value
            if value:
                logging.info(f"SUCCESS: Retrieved '{secret_name_kv}' from Key Vault.")
                return value
            logging.warning(f"WARN: Retrieved '{secret_name_kv}' from Key Vault, but its value is EMPTY.")
        except ResourceNotFoundError:
            logging.info(f"INFO: Secret '{secret_name_kv}' not found in Key Vault. Checking .env file for '{secret_name_env}'.")
        except Exception as e:
            logging.error(f"ERROR: Failed to access Key Vault for '{secret_name_kv}' ({e}). Checking .env file for '{secret_name_env}'.")

    # 2. Fallback to environment variables
    logging.info(f"Attempting to retrieve '{secret_name_env}' from .env file...")
    value = os.getenv(secret_name_env, default_value)

    if value and value != default_value:
        logging.info(f"SUCCESS: Found value for '{secret_name_env}' in .env file.")
        return value

    if required:
        error_msg = f"FATAL: Required configuration '{secret_name_kv}' (or '{secret_name_env}') not found in Key Vault or .env file."
        logging.error(error_msg)
        raise ValueError(error_msg)
    
    logging.warning(f"WARN: Optional secret '{secret_name_kv}' not found. Using default value.")
    return default_value

# --- Application Configuration ---
# Event Hubs
EVENT_HUB_CONNECTION_STR = get_secret("EventHub-A2A-ConnStr", required=True)
MCP_SERVER_REQUEST_TOPIC = get_secret("MCP-SERVER-REQUEST-TOPIC", default_value="mcp-requests", required=True)
MCP_SERVER_RESPONSE_TOPIC = get_secret("MCP-SERVER-RESPONSE-TOPIC", default_value="mcp-responses", required=True)

# Redis
REDIS_HOSTNAME = get_secret("REDIS-HOSTNAME", required=True)
REDIS_PORT = int(get_secret("REDIS-PORT", default_value="6380", required=True))
# Correctly use the 'REDIS-SSL' secret name and ensure robust boolean conversion
REDIS_SSL = str(get_secret("REDIS-SSL", default_value="true")).lower() == 'true'
REDIS_PASSWORD = get_secret("idtwin-dev-redis-access-key") # This can be None if not set

# Cosmos DB (if used in future)
COSMOS_DB_ENDPOINT = get_secret("Cosmos-DB-Endpoint")
COSMOS_DB_DATABASE = get_secret("Cosmos-DB-DatabaseName")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global producer_client, redis_client, consumer_client
    try:
        # Log config values for debugging
        logging.info(f"--- Service Initialization ---")
        logging.info(f"Event Hubs: Using connection string: {'YES' if EVENT_HUB_CONNECTION_STR else 'NO'}")
        logging.info(f"Event Hubs: Request Topic: {MCP_SERVER_REQUEST_TOPIC}, Response Topic: {MCP_SERVER_RESPONSE_TOPIC}")
        logging.info(f"Redis: Host={REDIS_HOSTNAME}, Port={REDIS_PORT}, SSL={REDIS_SSL}, Password Set={'YES' if REDIS_PASSWORD else 'NO'}")
        logging.info(f"-----------------------------")

        producer_client = EventHubProducerClient.from_connection_string(
            conn_str=EVENT_HUB_CONNECTION_STR,
            eventhub_name=MCP_SERVER_RESPONSE_TOPIC
        )
        logging.info("Event Hubs Producer client initialized.")

        redis_client = redis.Redis(
            host=REDIS_HOSTNAME,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            ssl=REDIS_SSL,
            decode_responses=True
        )
        await redis_client.ping()
        logging.info("Redis client initialized and connected.")

        consumer_client = EventHubConsumerClient.from_connection_string(
            conn_str=EVENT_HUB_CONNECTION_STR,
            consumer_group="$Default",
            eventhub_name=MCP_SERVER_REQUEST_TOPIC
        )
        logging.info("Event Hubs Consumer client initialized.")

        asyncio.create_task(consume_events())
        logging.info("Event Hubs consumer background task started.")

        yield  # The application is now running

    finally:
        # Shutdown logic
        logging.info("Shutting down services...")
        if producer_client:
            await producer_client.close()
            logging.info("Event Hubs Producer client closed.")
        if redis_client:
            # Use aclose() to avoid deprecation warning
            await redis_client.aclose()
            logging.info("Redis client closed.")
        if consumer_client:
            await consumer_client.close()
            logging.info("Event Hubs Consumer client closed.")

async def consume_events():
    async with consumer_client:
        logging.info(f"Starting to consume events from {MCP_SERVER_REQUEST_TOPIC}...")
        await consumer_client.receive(
            on_event=on_event_received,
            starting_position="-1",
        )

async def on_event_received(partition_context, event):
    logging.info(f"Received event from partition {partition_context.partition_id}: {event.body_as_str()}")
    try:
        message_data = json.loads(event.body_as_str())
        await handle_message(message_data)
    except json.JSONDecodeError:
        logging.error(f"Failed to decode JSON from event: {event.body_as_str()}")
    except Exception as e:
        logging.error(f"Error processing event: {e}")

async def handle_message(message_data: dict):
    try:
        message = MCPMessage(**message_data)
        if message.header.message_type == "agent.register":
            payload = RegisterPayload(**message.payload)
            await handle_agent_registration(payload)
        else:
            logging.warning(f"Received unhandled message type: {message.header.message_type}")
    except Exception as e:
        logging.error(f"Message validation or handling failed: {e}")

async def handle_agent_registration(payload: RegisterPayload):
    agent_key = f"agent:{payload.agent_id}"
    agent_details = {
        "agent_type": payload.agent_type,
        "capabilities": json.dumps(payload.capabilities),
        "last_seen_utc": datetime.now(timezone.utc).isoformat()
    }
    await redis_client.hset(agent_key, mapping=agent_details)
    logging.info(f"Registered/updated agent: {payload.agent_id}")

app = FastAPI(
    title="Model Context Protocol (MCP) Server",
    description="A central communication hub for a multi-agent system.",
    version="0.1.0",
    lifespan=lifespan
)

@app.get("/", summary="Server Health Check")
async def read_root():
    return {"status": "MCP Server is running"}

@app.get("/agents", summary="List Registered Agents")
async def list_registered_agents():
    agent_keys = await redis_client.keys("agent:*")
    agents = []
    for key in agent_keys:
        details = await redis_client.hgetall(key)
        details['agent_id'] = key.split(":")[1]
        if 'capabilities' in details and isinstance(details['capabilities'], str):
            details['capabilities'] = json.loads(details['capabilities'])
        agents.append(details)
    return {"agents": agents}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)