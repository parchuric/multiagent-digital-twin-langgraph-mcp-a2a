from langchain_openai import AzureChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain.tools import tool
import requests
import json
import os

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
        return json.dumps(response.json(), indent=2)
    except requests.exceptions.RequestException as e:
        return f"Error querying API: {e}"

# --- Agent Creation ---

def create_agent_executor():
    """
    Creates and returns the LangChain agent executor.
    Initializes the LLM, tools, and prompt, then constructs the agent.
    """
    try:
        # Get Azure OpenAI credentials from environment variables
        azure_api_key = os.environ["AZURE_OPENAI_API_KEY"]
        azure_endpoint = os.environ["AZURE_OPENAI_ENDPOINT"]
        azure_deployment = os.environ["AZURE_OPENAI_DEPLOYMENT_NAME"]
        azure_api_version = os.environ["AZURE_OPENAI_API_VERSION"]

        # --- Self-Correction & Debugging ---
        # Add detailed logging to help diagnose 404 errors.
        print("[INFO] Initializing AzureChatOpenAI with the following configuration:")
        print(f"  - Azure Endpoint: {azure_endpoint}")
        print(f"  - Azure Deployment Name: {azure_deployment}")
        print(f"  - Azure API Version: {azure_api_version}")
        print("Note: If you see a 'Resource not found' (404) error, please double-check that the 'Azure Deployment Name' above matches the deployment name in your Azure AI Studio, not the model name.")
        # --- End Self-Correction ---

        # Initialize the Azure Chat LLM
        llm = AzureChatOpenAI(
            openai_api_version=azure_api_version,
            azure_deployment=azure_deployment,
            azure_endpoint=azure_endpoint,
            api_key=azure_api_key,
            temperature=0,
            max_tokens=1000,
        )

        print("[INFO] AzureChatOpenAI model initialized successfully.")
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
