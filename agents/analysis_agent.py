import sys
import os

# Add the project root to the Python path
# This allows us to import from the 'config' module from anywhere in the project
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

import asyncio
from config.settings import (
    EVENT_HUB_CONNECTION_STR,
    EVENT_HUB_CONSUMER_GROUP,
    AGENT_DATA_TOPIC,
    AGENT_ANALYSIS_RESULTS_TOPIC,
)
from azure.eventhub.aio import EventHubConsumerClient, EventHubProducerClient
from azure.eventhub import EventData
import json

class AnalysisAgent:
    """
    An agent that listens for data on an Event Hubs topic, performs analysis,
    and publishes results to another topic.
    """

    def __init__(self):
        if not EVENT_HUB_CONNECTION_STR:
            raise ValueError("EVENT_HUB_CONNECTION_STR is not set. Please check your .env file.")
        
        self.consumer_client = EventHubConsumerClient.from_connection_string(
            conn_str=EVENT_HUB_CONNECTION_STR,
            consumer_group=EVENT_HUB_CONSUMER_GROUP,
            eventhub_name=AGENT_DATA_TOPIC,
        )
        self.producer_client = EventHubProducerClient.from_connection_string(
            conn_str=EVENT_HUB_CONNECTION_STR,
            eventhub_name=AGENT_ANALYSIS_RESULTS_TOPIC,
        )

    async def on_event(self, partition_context, event):
        """
        Callback function for processing a received event.
        """
        try:
            if event:
                raw_data_str = event.body_as_str()
                print(f"Received event: {raw_data_str}")

                # In a real scenario, you would perform complex analysis here.
                # For this placeholder, we'll just log the data.
                analysis_result = {
                    "status": "processed",
                    "original_data": json.loads(raw_data_str),
                    "analysis": "Placeholder analysis: data received.",
                }

                print(f"Analysis complete: {analysis_result}")

                # Publish the analysis result to the agent-analysis-results topic
                async with self.producer_client:
                    event_data_batch = await self.producer_client.create_batch()
                    event_data_batch.add(EventData(json.dumps(analysis_result)))
                    await self.producer_client.send_batch(event_data_batch)

                print("Analysis result published.")

                await partition_context.update_checkpoint(event)
        except Exception as e:
            print(f"An error occurred: {e}")

    async def start(self):
        """
        Starts the agent's event listening loop.
        """
        print("Analysis Agent starting...")
        async with self.consumer_client:
            await self.consumer_client.receive(
                on_event=self.on_event,
                starting_position="-1",  # "-1" is from the beginning of the partition.
            )


if __name__ == "__main__":
    try:
        agent = AnalysisAgent()
        asyncio.run(agent.start())
    except ValueError as e:
        print(f"[ERROR] {e}")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")
