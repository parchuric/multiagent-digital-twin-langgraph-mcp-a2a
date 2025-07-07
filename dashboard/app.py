from flask import Flask, jsonify, render_template, request
from flask_cors import CORS
import os
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from datetime import datetime, timezone

# Always load .env from project root
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(dotenv_path=os.path.join(root_dir, '.env'))

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Cosmos DB configuration
COSMOS_DB_ENDPOINT = os.environ["COSMOS_DB_ENDPOINT"]
COSMOS_DB_DATABASE_NAME = os.environ["COSMOS_DB_DATABASE_NAME"]
CONTAINER_MAP = {
    "scada": "scada_events",
    "plc": "plc_events",
    "gps": "gps_events"
}

# Initialize Cosmos Client using Azure AD credentials
credential = DefaultAzureCredential()
client = CosmosClient(COSMOS_DB_ENDPOINT, credential=credential)
database = client.get_database_client(COSMOS_DB_DATABASE_NAME)

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

# Backward compatible default route for scada
@app.route('/api/events')
def get_events():
    return get_events_by_type("scada")

if __name__ == '__main__':
    app.run(debug=True, port=5001)
