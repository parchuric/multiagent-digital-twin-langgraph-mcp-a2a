# Industrial Digital Twin Multi-Agent Platform

This repository contains the infrastructure and application code for an Industrial Digital Twin platform. It leverages Azure services to ingest, process, and store real-time data from various industrial simulators (SCADA, PLC, GPS). The platform is designed to be a foundation for building advanced analytics, real-time dashboards, and multi-agent autonomous systems.

The project is architected with a modular Terraform setup for infrastructure-as-code, and a robust Python application layer for simulation and stream processing.

## Architecture Overview

The platform consists of several key components:

- **Data Simulators (`/simulators`):** Python scripts that mimic real-world industrial equipment (SCADA, PLC, GPS) by generating and sending event data.
- **Event Ingestion (Azure Event Hubs):** A highly scalable event streaming service that decouples data producers from consumers.
- **Stream Processing (`event_stream_processor.py`):** A unified Python application that consumes events from Event Hubs, processes them, and archives them in a database.
- **Data Storage (Azure Cosmos DB):** A multi-model NoSQL database used to store the processed event data.
- **Web UI (`/dashboard`):** (In Development) A real-time dashboard for visualizing data and system status.
- **Intelligent Agents (`/agents`):** (In Development) The framework for building multi-agent systems that can analyze data and perform autonomous actions.

For a visual representation, see the [architecture diagram](industrial_architecture_diagram.html).

## Getting Started

Follow these steps to set up the infrastructure and run the simulation environment.

### 1. Prerequisites

- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- [Terraform](https://www.terraform.io/downloads.html)
- [Python 3.8+](https://www.python.org/downloads/)

### 2. Infrastructure Deployment (Terraform)

First, deploy the necessary Azure resources using the provided Terraform scripts.

1.  **Authenticate with Azure:**
    ```sh
    az login
    ```
2.  **Navigate to the dev environment directory:**
    ```sh
    cd terraform/environments/dev
    ```
3.  **Initialize and apply the Terraform plan:**
    ```sh
    terraform init
    terraform plan
    terraform apply
    ```
    This will provision all the necessary resources, including Event Hubs, Cosmos DB, and a Key Vault.

### 3. Application Setup

Next, configure your local environment to run the Python simulators and processor.

1.  **Navigate to the simulators directory:**
    ```sh
    cd ../../../simulators 
    ```
    *(Note: If you are in `terraform/environments/dev`, navigate back to the root and then into `simulators`)*

2.  **Create and activate a Python virtual environment:**
    ```powershell
    # For Windows
    python -m venv .venv
    .venv\Scripts\Activate
    ```
    ```sh
    # For macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

### 4. Security & Configuration

The application uses `DefaultAzureCredential` for secure, passwordless access to Azure resources.

1.  **Configure Environment File:**
    Create a `.env` file by copying the sample and adding your Key Vault URI.
    ```powershell
    # In the 'simulators' directory
    copy .env.sample .env
    ```
    Now, open `.env` and set the `KEY_VAULT_URI` variable:
    ```
    KEY_VAULT_URI="https://<your-key-vault-name>.vault.azure.net/"
    ```

2.  **Assign RBAC Permissions:**
    Your user account needs data-plane permissions on the Azure resources. Run the following Azure CLI commands, replacing `<your-principal-object-id>` with your user's Object ID (`az ad signed-in-user show --query id -o tsv`).

    ```sh
    # Set your identity's object ID
    PRINCIPAL_ID="<your-principal-object-id>"

    # Set your resource names (these are the defaults from Terraform)
    KEY_VAULT_NAME="idtwin-dev-kv"
    COSMOS_ACCOUNT_NAME="idtwin-dev-cosmos"
    RESOURCE_GROUP_NAME="idtwin-dev-rg"
    EVENT_HUB_NAMESPACE="idtwin-dev-eh-ns"
    SUBSCRIPTION_ID=$(az account show --query id -o tsv)
    
    # 1. Grant access to Key Vault secrets
    az keyvault set-policy --name $KEY_VAULT_NAME --object-id $PRINCIPAL_ID --secret-permissions get list

    # 2. Grant access to Cosmos DB (Data and Control Plane)
    az cosmosdb sql role assignment create --account-name $COSMOS_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --role-definition-name "Cosmos DB Built-in Data Contributor" --principal-id $PRINCIPAL_ID --scope "/"
    az cosmosdb sql role assignment create --account-name $COSMOS_ACCOUNT_NAME --resource-group $RESOURCE_GROUP_NAME --role-definition-name "Cosmos DB Operator" --principal-id $PRINCIPAL_ID --scope "/"

    # 3. Grant access to Event Hubs
    az role assignment create --assignee $PRINCIPAL_ID --role "Azure Event Hubs Data Owner" --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$RESOURCE_GROUP_NAME/providers/Microsoft.EventHub/namespaces/$EVENT_HUB_NAMESPACE"
    ```

3.  **Configure Firewalls:**
    For local development, add your public IP address to the firewall rules for Key Vault and Cosmos DB in the Azure Portal.

## Running a Full Simulation

The easiest way to run the platform is using the `run_simulation.py` script, which starts and manages a simulator and its corresponding stream processor in one command.

1.  **Ensure your virtual environment is active** and you are in the `simulators` directory.
2.  **Run the simulation:**
    Choose a stream type (`scada`, `plc`, or `gps`) and run the script.

    ```powershell
    # Example: Run the SCADA simulation and processor
    python run_simulation.py scada
    ```
    You will see interleaved output from both the simulator and the processor, showing events being sent and received in real-time.

    ```
    [PROCESSOR - SCADA]: Initializing processor for stream type: scada...
    [PROCESSOR - SCADA]: PROCESSOR_READY: Now listening for events.
    
    Processor is ready. Starting the simulator.
    
    [SIMULATOR - SCADA]: Sending event: {"id": "...", "value": 101.5}
    [PROCESSOR - SCADA]: Received event: {"id": "...", "value": 101.5}
    [PROCESSOR - SCADA]: Successfully inserted event ... into Cosmos DB.
    ...
    ```
3.  **To stop the simulation**, press `Ctrl+C`.

### 5. Running the Simulation

To see the full pipeline in action, you need to run a simulator and the event stream processor concurrently. The provided `run_simulation.py` script handles this for you.

1.  **Ensure you are in the `simulators` directory with your virtual environment active.**

2.  **Run the script:**
    Choose a simulator to run (`scada`, `plc`, or `gps`).

    ```sh
    # Example: Run the SCADA simulator and its corresponding processor
    python run_simulation.py --simulator scada
    ```

    You will see interleaved output from both the simulator sending events and the processor receiving them and writing them to Cosmos DB.

### 6. Running the Dashboard (New!)

The project includes a simple Flask-based web dashboard to visualize the data being ingested into Cosmos DB in real-time.

1.  **Open a new terminal.**

2.  **Navigate to the `dashboard` directory:**
    ```sh
    cd ../dashboard 
    ```
    *(Note: If you are in the `simulators` directory, navigate back to the root and then into `dashboard`)*

3.  **Create and activate a Python virtual environment (can be separate from the simulators'):**
    ```powershell
    # For Windows
    python -m venv .venv
    .venv\Scripts\Activate
    ```
    ```sh
    # For macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

4.  **Install dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

5.  **Run the Flask application:**
    ```sh
    python app.py
    ```

6.  **View the dashboard:**
    Open your web browser and navigate to `http://127.0.0.1:5001`.

    The dashboard will automatically fetch and display the latest events from the SCADA container in Cosmos DB every 5 seconds. For the dashboard to display data, the `scada` simulator and processor must have been run at least once.

## Project Decisions

Major architectural decisions, troubleshooting steps, and operational workflows are documented in `PROJECT-DECISIONS.md`. This file is essential reading for understanding the "why" behind the technical implementation.

## Next Steps

With the foundational data pipeline and initial dashboard in place, the next phases of the project will focus on:

1.  **Data Query API:** Develop a more sophisticated API to allow for querying and filtering data from Cosmos DB.
2.  **Agent Framework:** Begin development of the multi-agent system in the `/agents` directory.
3.  **Advanced Visualization:** Enhance the dashboard with more complex visualizations, such as time-series charts and geographical maps for GPS data.

---

## Platform Limitations: Process Management on Windows

> **Note:** On Windows, Python's signal and process management is limited. Even with robust signal handling and aggressive use of `taskkill`, simulator and processor subprocesses may persist after pressing Ctrl+C. If this occurs:
>
> - Open Task Manager and manually end any remaining `python.exe` processes related to your simulation.
> - For a more reliable developer experience, consider running the platform in WSL (Windows Subsystem for Linux) or a Linux VM/container.
> - This is a known limitation of Python and the Windows platform, not a project bug.

---

## Flink Integration: Java/Scala vs PyFlink

- **Flink jobs will be developed in Java/Scala for maximum performance, feature parity, and community support.**
- PyFlink is suitable for prototyping and simple pipelines, but not for advanced or production workloads.
- Java/Scala Flink development requires a local JDK (and Scala for Scala jobs). PyFlink only requires Python, but with noted limitations.
- Flink integration will be developed in a new branch for clean iteration and review.

