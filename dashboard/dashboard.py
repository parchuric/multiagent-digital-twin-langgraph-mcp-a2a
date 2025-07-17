import streamlit as st
import pandas as pd
import json
import os
from azure.cosmos import CosmosClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from streamlit_autorefresh import st_autorefresh

# Load environment variables from .env
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Cosmos DB config from environment variables
COSMOS_DB_ENDPOINT = os.getenv('COSMOS_DB_ENDPOINT')
COSMOS_DB_DATABASE_NAME = os.getenv('COSMOS_DB_DATABASE_NAME')

if not COSMOS_DB_ENDPOINT or not COSMOS_DB_DATABASE_NAME:
    st.error("COSMOS_DB_ENDPOINT and COSMOS_DB_DATABASE_NAME must be set in your .env file.")
    st.stop()

credential = DefaultAzureCredential()
client = CosmosClient(COSMOS_DB_ENDPOINT, credential=credential)
database = client.get_database_client(COSMOS_DB_DATABASE_NAME)

# Load site locations from JSON file
SITE_LOC_FILE = os.path.join(os.path.dirname(__file__), '..', 'site_locations.json')
with open(SITE_LOC_FILE, 'r') as f:
    site_locations = {site['facility_id']: site for site in json.load(f)}

# Valid containers
CONTAINER_MAP = {
    'scada': 'scada_events',
    'plc': 'plc_events',
    'gps': 'gps_events'
}

st.set_page_config(page_title="Global Manufacturing Dashboard", layout="wide")
st.title("Global Manufacturing Sites Performance Dashboard")

# Add event type selection at the top of the page
st.subheader("Select Event Type")
event_type = st.selectbox("Select Event Type", ["SCADA", "PLC", "GPS"])

# Query latest SCADA events for each site
container = database.get_container_client(CONTAINER_MAP['scada'])
query = "SELECT * FROM c ORDER BY c._ts DESC OFFSET 0 LIMIT 200"
items = list(container.query_items(query, enable_cross_partition_query=True))

# Aggregate status per site_id
site_status = {}
for item in items:
    facility_id = item.get('facility_id')
    if facility_id in site_locations:
        status = 'optimal'
        if 'error' in item:
            status = 'error'
        elif 'warning' in item:
            status = 'warning'
        site_status[facility_id] = {
            'facility': site_locations[facility_id]['facility'],
            'latitude': site_locations[facility_id]['latitude'],
            'longitude': site_locations[facility_id]['longitude'],
            'status': status,
            'last_event': item.get('timestamp', ''),
            'details': item
        }

# Query GPS events
gps_container = database.get_container_client(CONTAINER_MAP['gps'])
gps_query = "SELECT * FROM c ORDER BY c._ts DESC OFFSET 0 LIMIT 200"
gps_items = list(gps_container.query_items(gps_query, enable_cross_partition_query=True))

gps_map_data = pd.DataFrame([
    {
        'deviceId': item.get('deviceId'),
        'latitude': item.get('latitude'),
        'longitude': item.get('longitude'),
        'status': 'active' if not item.get('error') else 'error'
    }
    for item in gps_items if item.get('latitude') and item.get('longitude')
])

# Query PLC events (assuming facility_id exists)
plc_container = database.get_container_client(CONTAINER_MAP['plc'])
plc_query = "SELECT * FROM c ORDER BY c._ts DESC OFFSET 0 LIMIT 200"
plc_items = list(plc_container.query_items(plc_query, enable_cross_partition_query=True))

plc_status = {}
for item in plc_items:
    facility_id = item.get('facility_id')
    if facility_id in site_locations:
        status = 'optimal'
        if 'error' in item:
            status = 'error'
        elif 'warning' in item:
            status = 'warning'
        plc_status[facility_id] = {
            'facility': site_locations[facility_id]['facility'],
            'latitude': site_locations[facility_id]['latitude'],
            'longitude': site_locations[facility_id]['longitude'],
            'status': status,
            'last_event': item.get('timestamp', ''),
            'details': item
        }

# Prepare map data based on selected event type
if event_type == "SCADA":
    map_data = pd.DataFrame([
        {
            'facility_id': fid,
            'facility': data['facility'],
            'latitude': data['latitude'],
            'longitude': data['longitude'],
            'status': data['status']
        }
        for fid, data in site_status.items()
    ])
elif event_type == "PLC":
    map_data = pd.DataFrame([
        {
            'facility_id': fid,
            'facility': data['facility'],
            'latitude': data['latitude'],
            'longitude': data['longitude'],
            'status': data['status']
        }
        for fid, data in plc_status.items()
    ])
elif event_type == "GPS":
    map_data = gps_map_data

status_color = {'optimal': 'green', 'warning': 'orange', 'error': 'red', 'active': 'green'}

# Render map based on selected event type
st.subheader("Site Status Map")
if not map_data.empty:
    import plotly.express as px
    fig = px.scatter_mapbox(
        map_data,
        lat="latitude",
        lon="longitude",
        hover_name="facility" if event_type != "GPS" else "deviceId",
        hover_data=["facility_id", "status"] if event_type != "GPS" else ["deviceId", "status"],
        color="status",
        color_discrete_map=status_color,
        zoom=1,
        height=400
    )
    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info(f"No {event_type} events found for mapped sites.")

# Display site details for SCADA events
if event_type == "SCADA":
    st.subheader("SCADA Site Details")
    for fid, data in site_status.items():
        st.markdown(f"### {data['facility']} ({fid})")
        st.write(f"Status: {data['status']}")
        st.write(f"Last Event: {data['last_event']}")
        st.json(data['details'])
elif event_type == "PLC":
    st.subheader("PLC Site Details")
    for fid, data in plc_status.items():
        st.markdown(f"### {data['facility']} ({fid})")
        st.write(f"Status: {data['status']}")
        st.write(f"Last Event: {data['last_event']}")
        st.json(data['details'])
elif event_type == "GPS":
    st.subheader("GPS Device Details")
    for i, row in gps_map_data.iterrows():
        st.markdown(f"### Device {row['deviceId']}")
        st.write(f"Status: {row['status']}")
        st.write(f"Location: {row['latitude']}, {row['longitude']}")