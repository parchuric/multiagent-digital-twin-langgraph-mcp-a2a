import sys
import os

# Add the project root to the Python path to enable imports from the 'config' module
# This must be done before any other imports that rely on the config.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from config import settings

from langchain_openai import AzureChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import tool
import requests
import json
import asyncio
from azure.eventhub import EventData
from azure.eventhub.aio import EventHubProducerClient

# --- Event Hubs Producer ---
# Create a producer client to send messages to the event hub.
# This is created once and reused to be efficient.
async def publish_events_to_hub(events_data: str):
    if not settings.EVENT_HUB_CONNECTION_STR:
        print("[WARN] EVENT_HUB_CONNECTION_STR is not set. Skipping event hub publish.")
        return
    
    producer = EventHubProducerClient.from_connection_string(
        conn_str=settings.EVENT_HUB_CONNECTION_STR,
        eventhub_name=settings.AGENT_DATA_TOPIC
    )
    async with producer:
        event_data_batch = await producer.create_batch()
        event_data_batch.add(EventData(events_data))
        await producer.send_batch(event_data_batch)
        print(f"[INFO] Successfully published data to Event Hub topic: {settings.AGENT_DATA_TOPIC}")

# --- Agent Tools ---

@tool
def get_events_from_api(stream_type: str) -> str:
    """Queries the dashboard API to get events for a specific stream type (scada, plc, or gps)."""
    # Self-correction: The dashboard runs on port 5001, not 5000.
    api_url = f"http://localhost:5001/api/events/{stream_type}"
    try:
        print(f"[INFO] Agent tool querying API at: {api_url}") # Added for debugging
        response = requests.get(api_url)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # The raw JSON string from the response
        events_json_str = json.dumps(response.json(), indent=2)
        
        # Asynchronously publish the retrieved data to Event Hubs
        # This allows the agent to broadcast the data for other agents (like AnalysisAgent)
        # without blocking its own response to the user.
        print("[INFO] Publishing retrieved data to Event Hub for asynchronous analysis.")
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(publish_events_to_hub(events_json_str))
        except RuntimeError:
            # No running event loop (e.g., CLI/testing), fallback to asyncio.run
            asyncio.run(publish_events_to_hub(events_json_str))
        
        return events_json_str
    except requests.exceptions.RequestException as e:
        return f"Error querying API: {e}"
    except Exception as e:
        return f"An unexpected error occurred in get_events_from_api: {e}"

# --- Agent Creation ---

def create_agent_executor():
    """
    Creates and returns the LangChain agent executor.
    Initializes the LLM, tools, and prompt, then constructs the agent.
    """
    try:
        # Get Azure OpenAI credentials from the settings module
        if not all([settings.AZURE_OPENAI_API_KEY, settings.AZURE_OPENAI_ENDPOINT, settings.AZURE_OPENAI_DEPLOYMENT_NAME, settings.AZURE_OPENAI_API_VERSION]):
            raise ValueError("One or more Azure OpenAI environment variables are not set.")

        # --- Self-Correction & Debugging ---
        # Add detailed logging to help diagnose 404 errors.
        print("[INFO] Initializing AzureChatOpenAI with the following configuration:")
        print(f"  - Azure Endpoint: {settings.AZURE_OPENAI_ENDPOINT}")
        print(f"  - Azure Deployment Name: {settings.AZURE_OPENAI_DEPLOYMENT_NAME}")
        print(f"  - Azure API Version: {settings.AZURE_OPENAI_API_VERSION}")
        print("Note: If you see a 'Resource not found' (404) error, please double-check that the 'Azure Deployment Name' above matches the deployment name in your Azure AI Studio, not the model name.")
        # --- End Self-Correction ---

        # Initialize the Azure Chat LLM
        llm = AzureChatOpenAI(
            openai_api_version=settings.AZURE_OPENAI_API_VERSION,
            azure_deployment=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            temperature=0,
            max_tokens=1000,
        )

        print("[INFO] AzureChatOpenAI model initialized successfully.")
    except ValueError as ve:
        print(f"[ERROR] Configuration error: {ve}")
        print("[INFO] Please ensure all AZURE_OPENAI_* environment variables are set correctly in your .env file.")
        raise
    except Exception as e:
        print(f"[ERROR] Failed to initialize AzureChatOpenAI: {e}")
        print("[INFO] Please ensure AZURE_OPENAI_* environment variables are set correctly in your .env file.")
        raise

    # Define the tools the agent can use
    tools = [get_events_from_api]

    # Construct the prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are a helpful assistant for the Industrial Digital Twin platform. You can query real-time event streams from SCADA, PLC, and GPS sensors. Your goal is to answer user questions based on the data from these streams."),
        ("user", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])

    # Create the agent
    agent = create_tool_calling_agent(llm, tools, prompt)

    # Create the agent executor
    agent_executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,
        handle_parsing_errors=True # Handle cases where the agent output is not in the expected format
    )

    return agent_executor
