import os
from dotenv import load_dotenv
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential

# Determine the absolute path to the project root directory
# This allows the .env file to be found regardless of where a script is run
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Construct the path to the .env file and load it
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')
load_dotenv(dotenv_path=DOTENV_PATH)

print(f"[Config] Loading .env from: {DOTENV_PATH}")

# --- Azure Key Vault Setup ---
KEY_VAULT_URI = os.getenv("KEY_VAULT_URI")
credential = None
secret_client = None

if KEY_VAULT_URI:
    try:
        credential = DefaultAzureCredential()
        secret_client = SecretClient(vault_url=KEY_VAULT_URI, credential=credential)
        print(f"[Config] Successfully connected to Key Vault: {KEY_VAULT_URI}")
    except Exception as e:
        print(f"[Config] Warning: Failed to connect to Key Vault at {KEY_VAULT_URI}. Falling back to .env. Error: {e}")
        secret_client = None

def get_secret(secret_name, default_value=None):
    """
    Retrieves a secret from Azure Key Vault if available, otherwise falls back to environment variables.
    The secret name in Key Vault is expected to be the same as the environment variable name, but with hyphens instead of underscores.
    """
    if secret_client:
        try:
            kv_secret_name = secret_name.replace("_", "-")
            secret = secret_client.get_secret(kv_secret_name)
            print(f"[Config] Successfully retrieved '{secret_name}' from Key Vault (as '{kv_secret_name}').")
            return secret.value
        except Exception as e:
            pass # Fallback to .env
    value = os.getenv(secret_name, default_value)
    if value and value != default_value:
        print(f"[Config] Retrieved '{secret_name}' from .env file.")
    elif not value:
        print(f"[Config] Warning: '{secret_name}' not found in Key Vault or .env file.")
    return value

def get_event_hub_connection_str():
    """
    Retrieves the Event Hub connection string, trying multiple secret names for compatibility:
    1. Try 'EVENT_HUB_CONNECTION_STR' (env and Key Vault, as before)
    2. Try 'EventHub-A2A-ConnStr' (Key Vault only)
    3. Fallback to .env 'EventHub-A2A-ConnStr' if present
    """
    # 1. Try standard secret name (Key Vault and .env)
    value = get_secret("EVENT_HUB_CONNECTION_STR")
    if value:
        return value
    # 2. Try alternate Key Vault secret name
    if secret_client:
        try:
            secret = secret_client.get_secret("EventHub-A2A-ConnStr")
            print("[Config] Successfully retrieved 'EventHub-A2A-ConnStr' from Key Vault.")
            return secret.value
        except Exception:
            pass
    # 3. Fallback to .env with alternate name
    value = os.getenv("EventHub-A2A-ConnStr")
    if value:
        print("[Config] Retrieved 'EventHub-A2A-ConnStr' from .env file.")
        return value
    print("[Config] Warning: 'EVENT_HUB_CONNECTION_STR' and 'EventHub-A2A-ConnStr' not found in Key Vault or .env file.")
    return None

# --- Azure Event Hubs ---
EVENT_HUB_CONNECTION_STR = get_event_hub_connection_str()
EVENT_HUB_CONSUMER_GROUP = get_secret("EVENT_HUB_CONSUMER_GROUP", "$Default")

# --- Agent-specific Topics ---
AGENT_DATA_TOPIC = get_secret("AGENT_DATA_TOPIC", "agent-data")
AGENT_ANALYSIS_RESULTS_TOPIC = get_secret("AGENT_ANALYSIS_RESULTS_TOPIC", "agent-analysis-results")

# --- Azure OpenAI ---
AZURE_OPENAI_API_KEY = get_secret("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = get_secret("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_DEPLOYMENT_NAME = get_secret("AZURE_OPENAI_DEPLOYMENT_NAME")
AZURE_OPENAI_API_VERSION = get_secret("AZURE_OPENAI_API_VERSION")

# --- Azure Cosmos DB ---
COSMOS_DB_ENDPOINT = get_secret("COSMOS_DB_ENDPOINT")
COSMOS_DB_DATABASE_NAME = get_secret("COSMOS_DB_DATABASE_NAME", "industrial-digital-twin-db")

print("[Config] All settings loaded.")
