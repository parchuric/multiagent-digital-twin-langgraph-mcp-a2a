import sys
import os

# Add the project root to the Python path to enable imports from the 'config' module
# This must be done before any other imports that rely on the config.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from config import settings

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import json
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from datetime import datetime, timezone
import asyncio
from azure.eventhub.aio import EventHubConsumerClient
import threading

# --- Globals for Agent Communication ---
# This is a simplified mechanism for the POC. In production, you'd use a more robust
# system like Redis, a database, or a dedicated notification service to store/retrieve analysis results.
latest_analysis_result = None
analysis_listener_thread = None # Global variable for the listener thread

# Configuration variables are now imported from config.settings
# No need to define ANALYSIS_HUB_CONNECTION_STR, etc. here

from agents.data_query_agent import create_agent_executor

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize Agent Executor
# The agent executor will use the settings loaded by the config module.
try:
    agent_executor = create_agent_executor()
    print("[INFO] Agent executor created successfully.")
except Exception as e:
    agent_executor = None
    print(f"[ERROR] Failed to create agent executor: {e}. The /api/ask endpoint will be disabled.")

# Cosmos DB configuration is now handled by the settings module
CONTAINER_MAP = {
    "scada": "scada_events",
    "plc": "plc_events",
    "gps": "gps_events"
}

# Initialize Cosmos Client using Azure AD credentials and settings
credential = DefaultAzureCredential()
client = CosmosClient(settings.COSMOS_DB_ENDPOINT, credential=credential)
database = client.get_database_client(settings.COSMOS_DB_DATABASE_NAME)

def run_async_listener():
    """Helper function to run the async event hub listener in a new event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(receive_analysis_results())

async def receive_analysis_results():
    """A background task to listen for analysis results from the AnalysisAgent."""
    global latest_analysis_result
    if not settings.EVENT_HUB_CONNECTION_STR:
        print("[WARN] EVENT_HUB_CONNECTION_STR is not set. Analysis result listener is disabled.")
        return

    consumer_client = EventHubConsumerClient.from_connection_string(
        conn_str=settings.EVENT_HUB_CONNECTION_STR,
        consumer_group=settings.EVENT_HUB_CONSUMER_GROUP,
        eventhub_name=settings.AGENT_ANALYSIS_RESULTS_TOPIC,
    )

    async def on_event(partition_context, event):
        global latest_analysis_result
        if event:
            result_str = event.body_as_str()
            print(f"[INFO] Received analysis result from Event Hub: {result_str}")
            latest_analysis_result = json.loads(result_str)
            # Checkpointing is important for production but can be simplified for this POC
            # await partition_context.update_checkpoint(event)

    print("[INFO] Starting background listener for agent analysis results...")
    try:
        async with consumer_client:
            # This will run indefinitely, listening for new events.
            await consumer_client.receive(on_event=on_event, starting_position="-1")
    except Exception as e:
        print(f"[ERROR] Analysis result listener failed: {e}")

# --- Start Background Thread for Listener ---
# This ensures the listener runs in the background without blocking the main Flask app.
if os.environ.get("WERKZEUG_RUN_MAIN") != "true": # Prevents the thread from starting twice in debug mode
    listener_thread = threading.Thread(target=run_async_listener, daemon=True)
    listener_thread.start()
    print("[INFO] Analysis listener thread started.")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/events/<stream_type>')
def get_events_by_type(stream_type):
    container_name = CONTAINER_MAP.get(stream_type, "scada_events")
    container = database.get_container_client(container_name)
    try:
        print(f"[DEBUG] /api/events/{stream_type} endpoint called")
        # Query the last 100 events, ordered by timestamp
        query = "SELECT * FROM c ORDER BY c._ts DESC OFFSET 0 LIMIT 100"
        items = list(container.query_items(query, enable_cross_partition_query=True))
        print(f"[DEBUG] Retrieved {len(items)} events from Cosmos DB container '{container_name}'")
        # Ensure each event has a valid ISO 8601 timestamp
        for item in items:
            # If 'timestamp' exists and is valid, leave as is
            ts = item.get('timestamp')
            if not ts or not _is_valid_iso8601(ts):
                # Use Cosmos DB _ts (epoch seconds) if available
                if '_ts' in item:
                    item['timestamp'] = datetime.fromtimestamp(item['_ts'], tz=timezone.utc).isoformat()
                else:
                    item['timestamp'] = datetime.now(timezone.utc).isoformat()
        return jsonify(items)
    except Exception as e:
        print(f"[ERROR] Exception in /api/events/{stream_type}: {e}")
        return jsonify({"error": str(e)}), 500

def _is_valid_iso8601(ts):
    try:
        datetime.fromisoformat(ts.replace('Z', '+00:00'))
        return True
    except Exception:
        return False

@app.route('/api/gps_map')
def get_gps_map():
    """Return the latest GPS coordinates and geofence info for each unique device for map visualization."""
    try:
        container = database.get_container_client(CONTAINER_MAP['gps'])
        # Get the latest event per deviceId (using 'latitude', 'longitude', and 'geofence_violations')
        query = """
        SELECT c.deviceId, c.latitude, c.longitude, c.timestamp, c.geofence_violations, c.delivery_status, c.altitude, c.speed, c.heading
        FROM c
        WHERE IS_DEFINED(c.latitude) AND IS_DEFINED(c.longitude)
        ORDER BY c.deviceId, c._ts DESC
        """
        items = list(container.query_items(query, enable_cross_partition_query=True))
        # Reduce to latest per deviceId
        latest = {}
        for item in items:
            if item['deviceId'] not in latest:
                latest[item['deviceId']] = item
        print(f"[DEBUG] /api/gps_map returned {len(latest)} device locations with geofence info")
        return jsonify(list(latest.values()))
    except Exception as e:
        print(f"[ERROR] Exception in /api/gps_map: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/events_status')
def get_events_status():
    """Summarize error/status fields across all event streams for dashboard indicators."""
    status_summary = {}
    try:
        for stream_type, container_name in CONTAINER_MAP.items():
            container = database.get_container_client(container_name)
            # Example: count events with 'error' or 'status' fields
            query = "SELECT VALUE COUNT(1) FROM c WHERE IS_DEFINED(c.error) OR IS_DEFINED(c.status)"
            count = list(container.query_items(query, enable_cross_partition_query=True))[0]
            status_summary[stream_type] = count
        print(f"[DEBUG] /api/events_status summary: {status_summary}")
        return jsonify(status_summary)
    except Exception as e:
        print(f"[ERROR] Exception in /api/events_status: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/ask', methods=['POST'])
async def ask_agent():
    """Receives a question from the user, passes it to the LangChain agent, and returns the answer."""
    if not agent_executor:
        return jsonify({"error": "Agent is not configured. Please check server logs for details (e.g., missing OPENAI_API_KEY)."}), 503

    if not request.json or 'question' not in request.json:
        return jsonify({"error": "Invalid request. 'question' field is required."}), 400

    question = request.json['question']
    stream_type = request.json.get('stream_type', 'scada') # Default to scada if not provided

    # Enhance the question with context from the selected stream type
    enhanced_question = f"Regarding the '{stream_type}' data stream, {question}"

    print(f"[DEBUG] /api/ask received question: {enhanced_question}")

    try:
        # Invoke the agent with the enhanced question
        response = agent_executor.invoke({"input": enhanced_question})
        answer = response.get('output', 'Sorry, I could not find an answer.')
        print(f"[DEBUG] Agent response: {answer}")

        # --- Multi-Agent Orchestration (POC) ---
        # After the DataQueryAgent has published its data, we give the AnalysisAgent
        # a moment to process it and return a result. This is a simple polling mechanism.
        # In a real-world scenario, this would be handled with WebSockets, SSE, or a proper callback.
        await asyncio.sleep(5) # Wait for the analysis to (hopefully) complete
        
        analysis_data = latest_analysis_result # Fetch the latest result received by our listener
        
        return jsonify({"answer": answer, "analysis": analysis_data})
    except Exception as e:
        print(f"[ERROR] Exception in /api/ask: {e}")
        return jsonify({"error": f"An error occurred while processing your question: {e}"}), 500

@app.route('/api/analysis_result')
def get_analysis_result():
    """An endpoint to fetch the latest analysis result from the AnalysisAgent."""
    if latest_analysis_result:
        return jsonify(latest_analysis_result)
    else:
        return jsonify({"status": "pending", "message": "No analysis result received yet."}), 202

if __name__ == '__main__':
    # To run the async listener, you would typically use an async-capable server.
    # For this example, we'll just note that the listener needs to be run in the background.
    print("[INFO] To enable the full multi-agent workflow, run the analysis result listener in a separate process or integrate with an async server.")
    # Running with use_reloader=False is important to prevent the server from
    # restarting when the OpenAI library modifies its own files.
    # The default port is 5000, but we use 5001 to avoid potential conflicts.
    app.run(debug=True, use_reloader=False, port=5001)
