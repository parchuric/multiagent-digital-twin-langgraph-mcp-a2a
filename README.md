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

The following diagram illustrates the high-level architecture of the platform:

![Architecture Diagram](docs/industrial_architecture_diagram.png)

---

## Multi-Agent System Implementation Strategy

The platform is being evolved to include a multi-agent system for intelligent data analysis and interaction. The implementation follows a phased approach:

### Phase 1: The Foundational `DataQueryAgent`

A single agent integrated into the dashboard that can answer natural language questions about the event data.

#### Agent Data Flow

To ensure clarity, here is a step-by-step breakdown of how the agent retrieves and uses data:

1. **Cosmos DB as the Source of Truth:** The raw event data from the SCADA, PLC, and GPS simulators is permanently stored in Azure Cosmos DB.
2. **Backend Caching:** The backend Flask application (`dashboard/app.py`) reads the latest events from Cosmos DB and maintains a recent history of these events in memory. This caching strategy ensures the dashboard is fast and responsive, as it avoids querying the database for every user interaction.
3. **User Interaction:** When a user asks a question in the agent chat window, the browser sends the question and the currently selected stream type (e.g., 'scada') to the `/api/ask` endpoint in the Flask application.
4. **Agent Invocation:** The `/api/ask` endpoint invokes the `DataQueryAgent`. It provides the agent with the user's question and the relevant cached data stream from its memory.
5. **LLM-Powered Analysis:** The agent then sends the question and the data to the configured Azure OpenAI Large Language Model (LLM). The LLM analyzes the data in the context of the question and generates a natural language response.
6. **Displaying the Response:** The agent's response is sent back to the user's browser and displayed in the chat window.

In summary, the agent uses data that originates from Cosmos DB but accesses it via the backend's in-memory cache for performance. It does **not** directly query the database or call a separate API endpoint to get its data.

### Phase 2: Event-Driven A2A Communication with `AnalysisAgent`

Goal: Introduce a second agent, the `AnalysisAgent`, and enable scalable, event-driven communication between agents using Azure Event Hubs. This transitions the platform from a single-agent system to a true multi-agent architecture.

#### Core Technologies

- **Azure Event Hubs:** For asynchronous, decoupled agent-to-agent (A2A) communication.
- **LangChain:** For agent implementation and orchestration.

#### Implementation Strategy

1. **New `AnalysisAgent`:** A new Python agent will be created (`agents/analysis_agent.py`). Its primary role is to perform deeper analysis on data, such as calculating moving averages, detecting anomalies, or summarizing trends. It will not directly interface with the user.
2. **Event Hubs for A2A:** Instead of direct function calls, agents will communicate via dedicated Event Hubs topics. This creates a pub/sub model:
    - The `DataQueryAgent`, upon request from the UI, will fetch data and publish it to an `agent-data` topic in Event Hubs.
    - The `AnalysisAgent` will subscribe to this topic, process the data it receives, and publish its findings (e.g., an alert or a summary) to an `agent-analysis-results` topic.
3. **Orchestration:** The backend application (`dashboard/app.py`) will be updated to manage this flow. It will orchestrate the initial data query and listen for results from the `AnalysisAgent` to display to the user.

This event-driven pattern provides a robust foundation for adding more specialized agents in the future without creating tight coupling between them.

**Note on Event Hubs Topics:** It is a core architectural principle that the Event Hubs topics used for raw data ingestion from simulators (e.g., `scada-production-hub`) are kept separate from the topics used for agent-to-agent communication (`agent-data`, `agent-analysis-results`). This separation of concerns ensures the platform is scalable, maintainable, and easy to debug.

---

## Phase 3: Multi-Agent Platform, Communication Modes, and Dashboard

### Key Accomplishments

- Refactored agents to support both legacy and **Model Context Protocol (MCP)** communication modes.
- Implemented **dynamic topic selection** for agent-to-agent messaging via **Azure Event Hubs**.
- Ensured agents can register, communicate, and exchange analysis results in both modes.
- Developed a **Streamlit dashboard** for interactive, real-time visualization of **SCADA, PLC, and GPS events**.
- Added event type toggling, global facility mapping, and detailed site/device status views.
- Integrated facility metadata and color-coded status markers for comprehensive monitoring.
- Updated simulators and mapping to include new global manufacturing sites.
- Validated event flow and dashboard coverage for all facility IDs.
- Demonstrated full pipeline:  `Simulators → Event Hubs → Stream Processor (Python & Flink) → Cosmos DB → Agents → Dashboard`.
- Updated `README.md` and diagrams to reflect new components, data workflows, and best practices.
- Provided clear instructions for infrastructure provisioning, agent configuration, and dashboard usage.
- Delivered a robust, scalable, and extensible multi-agent platform with real-time global visibility, flexible communication modes, and comprehensive documentation.

### Communication Modes

In this phase the platform supports two agent-to-agent (A2A) communication modes:

- **Legacy Mode:** Agents communicate using default topic names (`agent-data`, `agent-analysis-results`).
- **MCP Mode:** Agents communicate using Model Context Protocol (MCP) topics (`mcp-requests`, `mcp-responses`) and a formalized protocol server.

#### How to Configure Communication Mode

The communication mode is controlled by the `AGENT_COMM_MODE` environment variable in your `.env` file:

- `legacy` — Use legacy topic names and direct communication.
- `mcp` — Use MCP topic names and protocol-based communication.
- `auto` — Try MCP first, fallback to legacy if not available.

**Example in `.env`:**

```env
AGENT_COMM_MODE=legacy  # or mcp or auto
```

#### Event Hub Topic Mapping

| Mode     | Data Query Agent Topic | Analysis Agent Topic     |
|----------|------------------------|--------------------------|
| legacy   | agent-data             | agent-analysis-results   |
| mcp      | mcp-requests           | mcp-responses            |

The actual topic used is determined at runtime by the agent code, which checks for the MCP environment variables first:
- `MCP_SERVER_REQUEST_TOPIC` (default: `mcp-requests`)
- `MCP_SERVER_RESPONSE_TOPIC` (default: `mcp-responses`)

#### How to Run Agents in Each Mode

**Legacy Mode:**
1. Set `AGENT_COMM_MODE=legacy` in your `.env` file.
2. Ensure `AGENT_DATA_TOPIC` and `AGENT_ANALYSIS_RESULTS_TOPIC` are set (or use defaults).
3. Start the agents as usual:
   ```bash
   python data_query_agent.py
   python analysis_agent.py
   ```
4. Agents will use `agent-data` and `agent-analysis-results` topics for communication.

**MCP Mode:**
1. Set `AGENT_COMM_MODE=mcp` in your `.env` file.
2. Ensure `MCP_SERVER_REQUEST_TOPIC` and `MCP_SERVER_RESPONSE_TOPIC` are set (defaults: `mcp-requests`, `mcp-responses`).
3. Start the agents as usual:
   ```bash
   python data_query_agent.py
   python analysis_agent.py
   ```
4. Agents will use `mcp-requests` and `mcp-responses` topics for communication.

**Auto Mode:**
1. Set `AGENT_COMM_MODE=auto` in your `.env` file.
2. The agent will attempt to use MCP mode first, and fallback to legacy if MCP is not available.

**Example .env Configuration for MCP Mode:**

```env
AGENT_COMM_MODE=mcp
MCP_SERVER_REQUEST_TOPIC=mcp-requests
MCP_SERVER_RESPONSE_TOPIC=mcp-responses
EVENTHUB_CONNECTION_STRING=your-connection-string
KEYVAULT_URL=https://your-keyvault.vault.azure.net/
```

#### Best Practices

- Always use Key Vault for secrets in production; `.env` is for local/dev only.
- Use namespace-level Event Hub connection strings for multi-topic access.
- Keep topic names in sync between `.env`, Key Vault, and Azure resources.
- Document any manual resource creation (e.g., Event Hubs) in your project notes.

#### Troubleshooting

- If agents do not communicate, check the topic names and connection string in your `.env`.
- Use debug prints in the agent code to verify which topics are being used at runtime.
- Ensure your Azure identity has the correct permissions for Event Hubs and Key Vault.

#### Activity Log: Phase 3 (MCP Integration)

- Refactored agents to support dual-mode (legacy and MCP) communication.
- Updated agent code to dynamically select Event Hub topics based on environment variables.
- Ensured secrets are loaded from Key Vault with fallback to `.env`.
- Verified agent registration and event flow in both modes.
- Documented configuration and troubleshooting steps in this README.

For more details, see the code comments in `data_query_agent.py` and `analysis_agent.py`.

#### End-to-End Validation Steps (Phase 3)

To validate the full multi-agent workflow, follow these step-by-step instructions. All commands are provided for Windows PowerShell unless otherwise noted.

1. **Provision and Verify Core Azure Resources**
   - Event Hubs Namespace and required topics
   - Cosmos DB account and database
   - Key Vault for secrets

   If not already provisioned, use Terraform:

   ```powershell
   cd terraform/environments/dev
   terraform init
   terraform plan
   terraform apply
   ```

2. **Start the MCP Server (if using MCP mode)**

   ```bash
   python mcp_server/main.py
   ```

3. **Start All Simulators**

   ```powershell
   cd simulators
   python run_simulation.py
   ```
   Or start individual simulators in separate terminals:

   ```powershell
   python scada_simulator.py
   python plc_simulator.py
   python gps_simulator.py
   ```

4. **Start the Event Stream Processor**

   Create or update your `.env` file in the project root with the following variables:

   ```env
   AGENT_COMM_MODE=mcp  # or legacy
   EVENT_HUB_CONNECTION_STR=your-event-hub-connection-string
   KEY_VAULT_URI=https://your-key-vault.vault.azure.net/
   ```

---

### Phase 4: Advanced Orchestration and Scaling

A sophisticated orchestration layer is built to manage complex workflows across a growing number of specialized agents.

#### Phase 4 Preview: Orchestrated Multi-Agent System

In Phase 4, the goal is to build an advanced orchestration layer for the platform. Here’s what you will achieve:

- **Sophisticated Workflow Orchestration:** Manage complex workflows across multiple specialized agents, enabling coordinated, multi-step analysis and decision-making.
- **Scalable Multi-Agent Coordination:** Support dynamic scaling and flexible agent collaboration, so new agents and analytical tasks can be added and managed efficiently.
- **Automated Task Routing:** Automatically route tasks, events, and analysis requests to the appropriate agents based on context, workload, and business logic.
- **Resilience and Monitoring:** Monitor agent health, track workflow status, and handle errors and exceptions for robust, reliable operation at scale.
- **Foundation for Future Expansion:** Lay the groundwork for integrating advanced AI, optimization algorithms, and autonomous control features in future development phases.

---

## Getting Started

Follow these steps to set up the infrastructure and run the simulation environment.

### 1. Prerequisites

- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- [Terraform](https://www.terraform.io/downloads.html)
- [Python 3.8+](https://www.python.org/downloads/)

### 2. Infrastructure Deployment (Terraform)

First, deploy the necessary Azure resources using the provided Terraform scripts.

1. **Authenticate with Azure:**

    ```sh
    az login
    ```

2. **Navigate to the dev environment directory:**

    ```sh
    cd terraform/environments/dev
    ```

3. **Initialize and apply the Terraform plan:**

    ```sh
    terraform init
    terraform plan
    terraform apply
    ```

    This will provision all the necessary resources, including Event Hubs, Cosmos DB, and a Key Vault.

### 3. Application Setup

Next, configure your local environment to run the Python simulators and processor.

1. **Navigate to the simulators directory:**

    ```sh
    cd ../../../simulators 
    ```

    *(Note: If you are in `terraform/environments/dev`, navigate back to the root and then into `simulators`)*

2. **Create and activate a Python virtual environment:**

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

3. **Install dependencies:**

    ```sh
    pip install -r requirements.txt
    ```

### 4. Security & Configuration

The application uses `DefaultAzureCredential` for secure, passwordless access to Azure resources.

1. **Configure Environment File:**
    Create a `.env` file by copying the sample and adding your Key Vault URI.

    ```powershell
    # In the 'simulators' directory
    copy .env.sample .env
    ```

    Now, open `.env` and set the `KEY_VAULT_URI` variable:

    ```env
    KEY_VAULT_URI="https://<your-key-vault-name>.vault.azure.net/"
    ```

2. **Configure Event Hubs Connection for Agents:**
    For the agents to communicate via Event Hubs, they need a connection string with access to the namespace.

    First, retrieve the connection string using the Azure CLI. The following command gets the primary connection string for the default access policy on your Event Hubs namespace:

    ```powershell
    # PowerShell
    $eventHubConnectionString = az eventhubs namespace authorization-rule keys list --resource-group idtwin-dev-rg --namespace-name idtwin-dev-ehns --name RootManageSharedAccessKey --query primaryConnectionString --output tsv
    echo "EVENT_HUB_CONNECTION_STR=\"$eventHubConnectionString\"" | Out-File -Append -Encoding utf8 .env
    ```

    ```sh
    # Bash
    eventHubConnectionString=$(az eventhubs namespace authorization-rule keys list --resource-group idtwin-dev-rg --namespace-name idtwin-dev-ehns --name RootManageSharedAccessKey --query primaryConnectionString --output tsv)
    echo "EVENT_HUB_CONNECTION_STR=\"$eventHubConnectionString\"" >> .env
    ```

    This will automatically append the `EVENT_HUB_CONNECTION_STR` to the `.env` file in your current directory. Make sure you run this from the project root where your `.env` file is located.

    Alternatively, you can run the `az` command and manually copy the output into your `.env` file like this:

    ```env
    EVENT_HUB_CONNECTION_STR="Endpoint=sb://...;SharedAccessKeyName=...;SharedAccessKey=...;EntityPath=..."
    ```

3. **Assign RBAC Permissions:**
    Your user account needs data-plane permissions on the Azure resources. Run the following Azure CLI commands, replacing `<your-principal-object-id>` with your user's Object ID (`az ad signed-in-user show --query id -o tsv`).

    ```sh
    # Set your identity's object ID
    PRINCIPAL_ID="<your-principal-object-id>"

    # Set your resource names (these are the defaults from Terraform)
    KEY_VAULT_NAME="idtwin-dev-kv"
    EVENT_HUBS_NAMESPACE="idtwin-dev-ehns"
    COSMOS_DB_ACCOUNT="idtwin-dev-cosmos"

    # Grant Key Vault access
    az keyvault secret set-permission --name $KEY_VAULT_NAME --object-id $PRINCIPAL_ID --permissions get list

    # Grant Event Hubs data access
    az role assignment create --role "Azure Event Hubs Data Owner" --assignee $PRINCIPAL_ID --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/idtwin-dev-rg/providers/Microsoft.EventHub/namespaces/$EVENT_HUBS_NAMESPACE"

    # Grant Cosmos DB data access (Contributor is needed for programmatic resource creation)
    az role assignment create --role "Contributor" --assignee $PRINCIPAL_ID --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/idtwin-dev-rg/providers/Microsoft.DocumentDB/databaseAccounts/$COSMOS_DB_ACCOUNT"
    ```

4. **Add Event Hubs Connection String to `.env`**:
    The agent-to-agent communication requires a connection string for the Event Hubs Namespace. Retrieve it using the Azure CLI and add it to your root `.env` file.

    ```powershell
    # Get the connection string
    $eventHubConnectionString = az eventhubs namespace authorization-rule keys list --resource-group idtwin-dev-rg --namespace-name idtwin-dev-ehns --name RootManageSharedAccessKey --query primaryConnectionString --output tsv

    # Append it to your .env file
    Add-Content -Path ".\.env" -Value "EVENT_HUB_CONNECTION_STR=\"$eventHubConnectionString\""
    
    echo "EVENT_HUB_CONNECTION_STR added to .env file."
    ```

5. **Configure Firewalls:**
    For local development, add your public IP address to the firewall rules for Key Vault and Cosmos DB in the Azure Portal.

---

## Running a Full Simulation

The easiest way to run the platform is using the `run_simulation.py` script, which starts and manages a simulator and its corresponding stream processor in one command.

1. **Ensure your virtual environment is active** and you are in the `simulators` directory.
2. **Run the simulation:**
    You can run all simulators in parallel, or specify a stream type (`scada`, `plc`, or `gps`) to run only that simulator. For example:

    ```powershell
    # Run all simulators in parallel
    python run_simulation.py

    # Run only the SCADA simulator
    python run_simulation.py scada

    # Run only the PLC simulator
    python run_simulation.py plc

    # Run only the GPS simulator
    python run_simulation.py gps
    ```

    You will see interleaved output from all running simulators, showing events being sent in real-time.

    To stop the simulation, press `Ctrl+C`.

### Running Components Manually (Alternative)

While `run_simulation.py` is the recommended way to run the platform for development, you can also run the stream processor and simulators manually in separate terminals. This can be useful for debugging individual components or for running only a subset of streams.

#### 1. Run All Simulators in Parallel

To launch all data simulators (SCADA, PLC, GPS) in parallel, use:

```sh
python run_simulation.py
```

This will start all three simulators as separate processes. Press `Ctrl+C` to stop all simulators at once. The script will handle graceful shutdown and process cleanup.

#### 2. Run a Single Simulator and Processor Pair

You can also run a single simulator and its corresponding processor for focused testing. For example, to run only the SCADA stream:

```sh
python run_simulation.py scada
```

Valid arguments are:

- `scada` — runs only the SCADA simulator
- `plc` — runs only the PLC simulator
- `gps` — runs only the GPS simulator
- No argument — runs all simulators in parallel

#### 3. Run the Event Stream Processor (Python)

The unified event stream processor can be run directly and requires the `--stream-type` argument to specify which stream to process. For example:

```sh
python event_stream_processor.py --stream-type scada
```

Valid arguments for `--stream-type` are:

- `scada` — process SCADA events
- `plc` — process PLC events
- `gps` — process GPS events
- (If supported) `all` — process all streams

**Example: Run the SCADA processor and simulator in separate terminals:**

Terminal 1:

```sh
python event_stream_processor.py --stream-type scada
```

Terminal 2:

```sh
python scada_simulator.py
```

**Example: Run all simulators and processors in parallel:**

Terminal 1:

```sh
python run_simulation.py
```

Terminal 2 (optional, for a specific processor):

```sh
python event_stream_processor.py --stream_type scada
```

**Notes:**

- The simulators and processor rely on the `.env` file for configuration (Key Vault URI, etc.) and use Azure AD to authenticate. Ensure you have logged in with `az login` and have the required permissions.
- You can control the event rate for each simulator by setting the `SCADA_EVENT_RATE`, `PLC_EVENT_RATE`, or `GPS_EVENT_RATE` environment variables.
- These simulators are for development and testing purposes only.

---

## Advanced Stream Processing (Apache Flink)

For more complex, stateful stream processing scenarios, this project includes a Maven-based Java application using Apache Flink. It processes the same event streams from Event Hubs (using its Kafka endpoint) and writes the results to Azure Cosmos DB, authenticating via Azure AD.

### Flink Prerequisites

Before you can build and run the Flink job, you will need the following installed on your system:

1. **Java Development Kit (JDK) 11:**
    - The project is standardized on the **Microsoft Build of OpenJDK 11**.
    - You can install it on Windows via `winget install Microsoft.OpenJDK.11` or download it from the official Microsoft site for other operating systems.
    - **Crucially**, you must set the `JAVA_HOME` environment variable to point to the JDK's installation directory.

2. **Apache Maven:**
    - A build automation tool used for Java projects.
    - You can download it from the [official Maven website](https://maven.apache.org/downloads.html).
    - Ensure the `mvn` command is available in your system's PATH.

### Flink Configuration

The Flink job is configured using environment variables defined in the `.env` file in the **project root directory**. Ensure the following variables are set correctly:

```env
# Flink Job Configuration
# Replace <YourEventHubsNamespace> with your actual Event Hubs Namespace
KAFKA_BOOTSTRAP_SERVERS=<YourEventHubsNamespace>.servicebus.windows.net:9093
FLINK_KAFKA_TOPICS=scada-production-hub,plc-control-hub,gps-logistics-hub

# Cosmos DB Configuration (used by the Flink Job)
COSMOS_DB_ENDPOINT=https://<YourCosmosDbAccount>.documents.azure.com:443/
COSMOS_DB_DATABASE=industrial-digital-twin-db
```

**Authentication:** The job uses `DefaultAzureCredential` for authenticating to Cosmos DB, so no keys are needed in the `.env` file. Ensure you are logged in via the Azure CLI (`az login`) or have the appropriate service principal environment variables set for authentication to work.

### Building the Flink Job

To compile the Java source code and package it into a runnable JAR file, navigate to the `flink-java` directory and run the following Maven command:

```sh
# From the project root
cd flink-java
mvn clean package
cd ..
```

This will create a JAR file in the `flink-java/target/` directory (e.g., `flink-java-1.0-SNAPSHOT.jar`).

### Running the Flink Job

Once the JAR file is built, you can submit it to a running Flink cluster. For local development, you can use a standalone Flink distribution.

1. **Download Apache Flink:** Download a stable Flink distribution (e.g., Flink 1.17 or later) from the [official Flink website](https://flink.apache.org/downloads/).

2. **Start a Local Flink Cluster:**

    ```sh
    # Navigate to your Flink distribution directory
    # cd /path/to/flink-1.17.x

    # Start the cluster
    ./bin/start-cluster.sh
    ```

3. **Submit the Job:**
    From the Flink distribution directory, use the `flink run` command to submit your JAR. You will need to provide the absolute path to the JAR file created in the previous step.

    ```sh
    # Example from within the Flink distribution directory
    ./bin/flink run c:\Projects\GithubLocal\industrial-digital-twin-multiagent-platform\flink-java\target\flink-java-1.0-SNAPSHOT.jar
    ```

You can monitor the job's progress through the Flink Web UI, which is typically available at `http://localhost:8081`.

---

## Project Structure

```
industrial-digital-twin-multiagent-platform/
├── .github/                  # CI/CD workflows and GitHub Actions
├── agents/                   # Python code for intelligent agents (in development)
├── dashboard/                # Web-based UI for data visualization (Streamlit, in development)
│   ├── dashboard.py          # Streamlit dashboard for real-time event visualization
│   ├── requirements.txt      # Python dependencies for dashboard
│   └── ...
├── docs/                     # Project documentation and architecture diagrams
│   ├── industrial_architecture_diagram.png   # Architecture diagram (image)
│   └── ...
├── flink-java/               # Maven project for the Flink Java stream processor
│   ├── src/main/java/com/industrialdigitaltwin/flink/
│   │   ├── StreamingJob.java         # Main Flink job (reference implementation)
│   │   ├── ScadaEvent.java           # SCADA event POJO
│   │   ├── GpsEvent.java             # GPS event POJO
│   │   ├── PlcEvent.java             # PLC event POJO
│   │   ├── EnrichedEvent.java        # Output of cross-stream join
│   │   ├── MovingAverageAggregate.java # Windowed aggregation logic
│   │   └── ...                       # Additional Flink utilities and classes
│   ├── pom.xml                       # Maven build configuration
│   └── ...
├── simulators/                # Python scripts for data generation
│   ├── scada_simulator.py     # SCADA event generator
│   ├── plc_simulator.py       # PLC event generator
│   ├── gps_simulator.py       # GPS event generator
│   ├── run_simulation.py      # Orchestrates processor and simulator for dev
│   ├── event_stream_processor.py # Unified Python stream processor
│   ├── site_locations.json    # Facility ID to location mapping
│   ├── requirements.txt       # Python dependencies
│   └── ...
├── terraform/                 # Terraform modules for infrastructure-as-code
│   ├── modules/               # Reusable infrastructure components
│   └── environments/          # Environment-specific configs (dev, staging, prod)
├── industrial_architecture_diagram.html # Interactive architecture diagram
├── PROJECT-DECISIONS.md       # Log of key architectural and technical decisions
├── README.md                  # This file
└── ...                        # Other root-level files (e.g., .env.sample, .gitignore)
```

- **Each major component is modularized for clarity and scalability.**
- **Terraform** manages all Azure infrastructure, with clear separation between reusable modules and environment-specific settings.
- **Simulators** and **stream processors** are decoupled, supporting both Python and Java (Flink) implementations.
- **Dashboard** is implemented in Streamlit for real-time, interactive visualization of global events.
- **Documentation** is comprehensive, with all major decisions and troubleshooting steps logged for future reference.

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

---

## Project Evolution: From Python Ingestion to Advanced Flink Stream Processing

### Phase 1: Python-Based Stream Processor (Foundational Ingestion)

- The project began with a unified Python stream processor (`event_stream_processor.py`) that consumes events from Azure Event Hubs and writes them to Cosmos DB.
- This approach prioritized rapid prototyping, secure authentication (using Azure AD and Key Vault), and robust infrastructure-as-code (Terraform) for all Azure resources.
- The Python processor uses `DefaultAzureCredential` for passwordless authentication and programmatically ensures Cosmos DB containers and indexes exist, making onboarding and local development seamless.
- All simulators (SCADA, PLC, GPS) generate cryptographically unique event IDs at the source, ensuring data integrity and traceability throughout the pipeline.
- The Python ingestion pipeline is still the recommended starting point for new developers and is ideal for simple, stateless processing and rapid iteration.

### Phase 2: Advanced Stream Processing with Apache Flink (Java)

- As requirements for real-time analytics, cross-stream joins, and stateful processing emerged, the project evolved to include a Java-based Flink job (`flink-java`).
- Flink connects to Azure Event Hubs using the Kafka protocol endpoint, enabling high-throughput, low-latency stream processing with full support for event-time semantics and advanced windowing.
- The Flink job demonstrates:
  - **Cross-Stream Join:** Joins SCADA and GPS streams by device/unit ID within a configurable time window using Flink's `intervalJoin` API. This enables event correlation and enrichment (e.g., associating sensor readings with location data).
  - **Stateful Processing:** Implements windowed aggregations (such as moving averages) using Flink's keyed state and window APIs. This is the foundation for anomaly detection, trend analysis, and other advanced analytics.
  - **Output Enrichment:** The joined and aggregated results can be written to Cosmos DB or other sinks, making them available for downstream applications and dashboards.
- The Flink reference implementation is modular and extensible, serving as a template for future analytical features and production workloads.

### Phase 3: Multi-Agent Communication, MCP Server, and End-to-End Testing

- Introduced the **MCP server** (`/mcp_server`) to support Model Context Protocol (MCP) for agent-to-agent (A2A) communication, enabling robust, protocol-driven interactions between agents.
- Agents now support both **Legacy** and **MCP** communication modes:
  - **Legacy Mode:** Agents communicate using default Event Hub topics (`agent-data`, `agent-analysis-results`).
  - **MCP Mode:** Agents communicate using protocol-based topics (`mcp-requests`, `mcp-responses`) and register with the MCP server for structured message exchange.
  - **Auto Mode:** Agents attempt MCP first, falling back to legacy if MCP is not available.
- The communication mode is controlled by the `AGENT_COMM_MODE` environment variable in `.env`.
- Topic names and connection strings are managed via `.env` and/or Azure Key Vault, and must be kept in sync across code, config, and Azure resources.
- **End-to-end testing** now validates the full data pipeline in both MCP and Legacy modes:
  - Simulators → Event Hubs → Stream Processor (Python/Flink) → Cosmos DB → Agents (MCP/Legacy) → Dashboard
  - Step-by-step instructions are provided for provisioning, configuration, running all components, and verifying data flow and agent communication.
- The platform now supports flexible, decoupled agent orchestration and is validated for both legacy and modern (MCP) workflows, ensuring future scalability and maintainability.

### Phase 4: Orchestrator, Scalability, and Observability

In this phase, the focus is on building an orchestrator for managing complex agent workflows and enhancing the platform's scalability and observability.

#### Key Objectives

- **Orchestrator Development:** Create a centralized orchestrator component that manages and coordinates workflows across multiple agents, enabling complex, multi-step processing and decision-making.
- **Scalability Enhancements:** Optimize the platform to support a growing number of agents and higher event throughput, ensuring reliable performance at scale.
- **Observability Features:** Implement comprehensive monitoring and logging for all components, providing insights into system behavior, performance, and potential issues.

#### Orchestrator Design

The orchestrator is designed as a separate microservice that interacts with the existing components:

- **Workflow Management:** Define and manage workflows that specify the sequence of actions and data transformations across agents.
- **Dynamic Scaling:** Automatically scale the number of agent instances based on workload, event volume, and processing requirements.
- **Error Handling and Retries:** Implement robust error handling, automatic retries, and fallback mechanisms to ensure reliable processing and fault tolerance.

#### Implementation Plan

1. **Develop Orchestrator Service:**
    - Create a new microservice for the orchestrator, with a REST API for workflow submission and status monitoring.
    - Implement workflow management, dynamic scaling, and error handling features.

2. **Integrate with Existing Components:**
    - Update agent implementations to support orchestration commands and status reporting.
    - Ensure seamless communication and data exchange between the orchestrator and agents.

3. **Enhance Monitoring and Logging:**
    - Integrate with Azure Monitor, Application Insights, or similar services for comprehensive observability.
    - Implement structured logging, distributed tracing, and custom metrics for all components.

4. **Testing and Validation:**
    - Thoroughly test the orchestrator with simulated workloads and failure scenarios.
    - Validate end-to-end workflows, performance, scalability, and fault tolerance.

5. **Documentation and Training:**
    - Update documentation to include orchestrator usage, configuration, and troubleshooting.
    - Provide training and examples for users to define and manage their own workflows.

---

## Getting Started

Follow these steps to set up the infrastructure and run the simulation environment.

### 1. Prerequisites

- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- [Terraform](https://www.terraform.io/downloads.html)
- [Python 3.8+](https://www.python.org/downloads/)

### 2. Infrastructure Deployment (Terraform)

First, deploy the necessary Azure resources using the provided Terraform scripts.

1. **Authenticate with Azure:**

    ```sh
    az login
    ```

2. **Navigate to the dev environment directory:**

    ```sh
    cd terraform/environments/dev
    ```

3. **Initialize and apply the Terraform plan:**

    ```sh
    terraform init
    terraform plan
    terraform apply
    ```

    This will provision all the necessary resources, including Event Hubs, Cosmos DB, and a Key Vault.

### 3. Application Setup

Next, configure your local environment to run the Python simulators and processor.

1. **Navigate to the simulators directory:**

    ```sh
    cd ../../../simulators 
    ```

    *(Note: If you are in `terraform/environments/dev`, navigate back to the root and then into `simulators`)*

2. **Create and activate a Python virtual environment:**

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

3. **Install dependencies:**

    ```sh
    pip install -r requirements.txt
    ```

### 4. Security & Configuration

The application uses `DefaultAzureCredential` for secure, passwordless access to Azure resources.

1. **Configure Environment File:**
    Create a `.env` file by copying the sample and adding your Key Vault URI.

    ```powershell
    # In the 'simulators' directory
    copy .env.sample .env
    ```

    Now, open `.env` and set the `KEY_VAULT_URI` variable:

    ```env
    KEY_VAULT_URI="https://<your-key-vault-name>.vault.azure.net/"
    ```

2. **Configure Event Hubs Connection for Agents:**
    For the agents to communicate via Event Hubs, they need a connection string with access to the namespace.

    First, retrieve the connection string using the Azure CLI. The following command gets the primary connection string for the default access policy on your Event Hubs namespace:

    ```powershell
    # PowerShell
    $eventHubConnectionString = az eventhubs namespace authorization-rule keys list --resource-group idtwin-dev-rg --namespace-name idtwin-dev-ehns --name RootManageSharedAccessKey --query primaryConnectionString --output tsv
    echo "EVENT_HUB_CONNECTION_STR=\"$eventHubConnectionString\"" | Out-File -Append -Encoding utf8 .env
    ```

    ```sh
    # Bash
    eventHubConnectionString=$(az eventhubs namespace authorization-rule keys list --resource-group idtwin-dev-rg --namespace-name idtwin-dev-ehns --name RootManageSharedAccessKey --query primaryConnectionString --output tsv)
    echo "EVENT_HUB_CONNECTION_STR=\"$eventHubConnectionString\"" >> .env
    ```

    This will automatically append the `EVENT_HUB_CONNECTION_STR` to the `.env` file in your current directory. Make sure you run this from the project root where your `.env` file is located.

    Alternatively, you can run the `az` command and manually copy the output into your `.env` file like this:

    ```env
    EVENT_HUB_CONNECTION_STR="Endpoint=sb://...;SharedAccessKeyName=...;SharedAccessKey=...;EntityPath=..."
    ```

3. **Assign RBAC Permissions:**
    Your user account needs data-plane permissions on the Azure resources. Run the following Azure CLI commands, replacing `<your-principal-object-id>` with your user's Object ID (`az ad signed-in-user show --query id -o tsv`).

    ```sh
    # Set your identity's object ID
    PRINCIPAL_ID="<your-principal-object-id>"

    # Set your resource names (these are the defaults from Terraform)
    KEY_VAULT_NAME="idtwin-dev-kv"
    EVENT_HUBS_NAMESPACE="idtwin-dev-ehns"
    COSMOS_DB_ACCOUNT="idtwin-dev-cosmos"

    # Grant Key Vault access
    az keyvault secret set-permission --name $KEY_VAULT_NAME --object-id $PRINCIPAL_ID --permissions get list

    # Grant Event Hubs data access
    az role assignment create --role "Azure Event Hubs Data Owner" --assignee $PRINCIPAL_ID --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/idtwin-dev-rg/providers/Microsoft.EventHub/namespaces/$EVENT_HUBS_NAMESPACE"

    # Grant Cosmos DB data access (Contributor is needed for programmatic resource creation)
    az role assignment create --role "Contributor" --assignee $PRINCIPAL_ID --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/idtwin-dev-rg/providers/Microsoft.DocumentDB/databaseAccounts/$COSMOS_DB_ACCOUNT"
    ```

4. **Add Event Hubs Connection String to `.env`**:
    The agent-to-agent communication requires a connection string for the Event Hubs Namespace. Retrieve it using the Azure CLI and add it to your root `.env` file.

    ```powershell
    # Get the connection string
    $eventHubConnectionString = az eventhubs namespace authorization-rule keys list --resource-group idtwin-dev-rg --namespace-name idtwin-dev-ehns --name RootManageSharedAccessKey --query primaryConnectionString --output tsv

    # Append it to your .env file
    Add-Content -Path ".\.env" -Value "EVENT_HUB_CONNECTION_STR=\"$eventHubConnectionString\""
    
    echo "EVENT_HUB_CONNECTION_STR added to .env file."
    ```

5. **Configure Firewalls:**
    For local development, add your public IP address to the firewall rules for Key Vault and Cosmos DB in the Azure Portal.

---

## Running a Full Simulation

The easiest way to run the platform is using the `run_simulation.py` script, which starts and manages a simulator and its corresponding stream processor in one command.

1. **Ensure your virtual environment is active** and you are in the `simulators` directory.
2. **Run the simulation:**
    You can run all simulators in parallel, or specify a stream type (`scada`, `plc`, or `gps`) to run only that simulator. For example:

    ```powershell
    # Run all simulators in parallel
    python run_simulation.py

    # Run only the SCADA simulator
    python run_simulation.py scada

    # Run only the PLC simulator
    python run_simulation.py plc

    # Run only the GPS simulator
    python run_simulation.py gps
    ```

    You will see interleaved output from all running simulators, showing events being sent in real-time.

    To stop the simulation, press `Ctrl+C`.

### Running Components Manually (Alternative)

While `run_simulation.py` is the recommended way to run the platform for development, you can also run the stream processor and simulators manually in separate terminals. This can be useful for debugging individual components or for running only a subset of streams.

#### 1. Run All Simulators in Parallel

To launch all data simulators (SCADA, PLC, GPS) in parallel, use:

```sh
python run_simulation.py
```

This will start all three simulators as separate processes. Press `Ctrl+C` to stop all simulators at once. The script will handle graceful shutdown and process cleanup.

#### 2. Run a Single Simulator and Processor Pair

You can also run a single simulator and its corresponding processor for focused testing. For example, to run only the SCADA stream:

```sh
python run_simulation.py scada
```

Valid arguments are:

- `scada` — runs only the SCADA simulator
- `plc` — runs only the PLC simulator
- `gps` — runs only the GPS simulator
- No argument — runs all simulators in parallel

#### 3. Run the Event Stream Processor (Python)

The unified event stream processor can be run directly and requires the `--stream-type` argument to specify which stream to process. For example:

```sh
python event_stream_processor.py --stream-type scada
```

Valid arguments for `--stream-type` are:

- `scada` — process SCADA events
- `plc` — process PLC events
- `gps` — process GPS events
- (If supported) `all` — process all streams

**Example: Run the SCADA processor and simulator in separate terminals:**

Terminal 1:

```sh
python event_stream_processor.py --stream-type scada
```

Terminal 2:

```sh
python scada_simulator.py
```

**Example: Run all simulators and processors in parallel:**

Terminal 1:

```sh
python run_simulation.py
```

Terminal 2 (optional, for a specific processor):

```sh
python event_stream_processor.py --stream_type scada
```

**Notes:**

- The simulators and processor rely on the `.env` file for configuration (Key Vault URI, etc.) and use Azure AD to authenticate. Ensure you have logged in with `az login` and have the required permissions.
- You can control the event rate for each simulator by setting the `SCADA_EVENT_RATE`, `PLC_EVENT_RATE`, or `GPS_EVENT_RATE` environment variables.
- These simulators are for development and testing purposes only.

---

## Advanced Stream Processing (Apache Flink)

For more complex, stateful stream processing scenarios, this project includes a Maven-based Java application using Apache Flink. It processes the same event streams from Event Hubs (using its Kafka endpoint) and writes the results to Azure Cosmos DB, authenticating via Azure AD.

### Flink Prerequisites

Before you can build and run the Flink job, you will need the following installed on your system:

1. **Java Development Kit (JDK) 11:**
    - The project is standardized on the **Microsoft Build of OpenJDK 11**.
    - You can install it on Windows via `winget install Microsoft.OpenJDK.11` or download it from the official Microsoft site for other operating systems.
    - **Crucially**, you must set the `JAVA_HOME` environment variable to point to the JDK's installation directory.

2. **Apache Maven:**
    - A build automation tool used for Java projects.
    - You can download it from the [official Maven website](https://maven.apache.org/downloads.html).
    - Ensure the `mvn` command is available in your system's PATH.

### Flink Configuration

The Flink job is configured using environment variables defined in the `.env` file in the **project root directory**. Ensure the following variables are set correctly:

```env
# Flink Job Configuration
# Replace <YourEventHubsNamespace> with your actual Event Hubs Namespace
KAFKA_BOOTSTRAP_SERVERS=<YourEventHubsNamespace>.servicebus.windows.net:9093
FLINK_KAFKA_TOPICS=scada-production-hub,plc-control-hub,gps-logistics-hub

# Cosmos DB Configuration (used by the Flink Job)
COSMOS_DB_ENDPOINT=https://<YourCosmosDbAccount>.documents.azure.com:443/
COSMOS_DB_DATABASE=industrial-digital-twin-db
```

**Authentication:** The job uses `DefaultAzureCredential` for authenticating to Cosmos DB, so no keys are needed in the `.env` file. Ensure you are logged in via the Azure CLI (`az login`) or have the appropriate service principal environment variables set for authentication to work.

### Building the Flink Job

To compile the Java source code and package it into a runnable JAR file, navigate to the `flink-java` directory and run the following Maven command:

```sh
# From the project root
cd flink-java
mvn clean package
cd ..
```

This will create a JAR file in the `flink-java/target/` directory (e.g., `flink-java-1.0-SNAPSHOT.jar`).

### Running the Flink Job

Once the JAR file is built, you can submit it to a running Flink cluster. For local development, you can use a standalone Flink distribution.

1. **Download Apache Flink:** Download a stable Flink distribution (e.g., Flink 1.17 or later) from the [official Flink website](https://flink.apache.org/downloads/).

2. **Start a Local Flink Cluster:**

    ```sh
    # Navigate to your Flink distribution directory
    # cd /path/to/flink-1.17.x

    # Start the cluster
    ./bin/start-cluster.sh
    ```

3. **Submit the Job:**
    From the Flink distribution directory, use the `flink run` command to submit your JAR. You will need to provide the absolute path to the JAR file created in the previous step.

    ```sh
    # Example from within the Flink distribution directory
    ./bin/flink run c:\Projects\GithubLocal\industrial-digital-twin-multiagent-platform\flink-java\target\flink-java-1.0-SNAPSHOT.jar
    ```

You can monitor the job's progress through the Flink Web UI, which is typically available at `http://localhost:8081`.

---

## Project Structure

```
industrial-digital-twin-multiagent-platform/
├── .github/                  # CI/CD workflows and GitHub Actions
├── agents/                   # Python code for intelligent agents (in development)
├── dashboard/                # Web-based UI for data visualization (Streamlit, in development)
│   ├── dashboard.py          # Streamlit dashboard for real-time event visualization
│   ├── requirements.txt      # Python dependencies for dashboard
│   └── ...
├── docs/                     # Project documentation and architecture diagrams
│   ├── industrial_architecture_diagram.png   # Architecture diagram (image)
│   └── ...
├── flink-java/               # Maven project for the Flink Java stream processor
│   ├── src/main/java/com/industrialdigitaltwin/flink/
│   │   ├── StreamingJob.java         # Main Flink job (reference implementation)
│   │   ├── ScadaEvent.java           # SCADA event POJO
│   │   ├── GpsEvent.java             # GPS event POJO
│   │   ├── PlcEvent.java             # PLC event POJO
│   │   ├── EnrichedEvent.java        # Output of cross-stream join
│   │   ├── MovingAverageAggregate.java # Windowed aggregation logic
│   │   └── ...                       # Additional Flink utilities and classes
│   ├── pom.xml                       # Maven build configuration
│   └── ...
├── simulators/                # Python scripts for data generation
│   ├── scada_simulator.py     # SCADA event generator
│   ├── plc_simulator.py       # PLC event generator
│   ├── gps_simulator.py       # GPS event generator
│   ├── run_simulation.py      # Orchestrates processor and simulator for dev
│   ├── event_stream_processor.py # Unified Python stream processor
│   ├── site_locations.json    # Facility ID to location mapping
│   ├── requirements.txt       # Python dependencies
│   └── ...
├── terraform/                 # Terraform modules for infrastructure-as-code
│   ├── modules/               # Reusable infrastructure components
│   └── environments/          # Environment-specific configs (dev, staging, prod)
├── industrial_architecture_diagram.html # Interactive architecture diagram
├── PROJECT-DECISIONS.md       # Log of key architectural and technical decisions
├── README.md                  # This file
└── ...                        # Other root-level files (e.g., .env.sample, .gitignore)
```

- **Each major component is modularized for clarity and scalability.**
- **Terraform** manages all Azure infrastructure, with clear separation between reusable modules and environment-specific settings.
- **Simulators** and **stream processors** are decoupled, supporting both Python and Java (Flink) implementations.
- **Dashboard** is implemented in Streamlit for real-time, interactive visualization of global events.
- **Documentation** is comprehensive, with all major decisions and troubleshooting steps logged for future reference.

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

---

## Project Evolution: From Python Ingestion to Advanced Flink Stream Processing

### Phase 1: Python-Based Stream Processor (Foundational Ingestion)

- The project began with a unified Python stream processor (`event_stream_processor.py`) that consumes events from Azure Event Hubs and writes them to Cosmos DB.
- This approach prioritized rapid prototyping, secure authentication (using Azure AD and Key Vault), and robust infrastructure-as-code (Terraform) for all Azure resources.
- The Python processor uses `DefaultAzureCredential` for passwordless authentication and programmatically ensures Cosmos DB containers and indexes exist, making onboarding and local development seamless.
- All simulators (SCADA, PLC, GPS) generate cryptographically unique event IDs at the source, ensuring data integrity and traceability throughout the pipeline.
- The Python ingestion pipeline is still the recommended starting point for new developers and is ideal for simple, stateless processing and rapid iteration.

### Phase 2: Advanced Stream Processing with Apache Flink (Java)

- As requirements for real-time analytics, cross-stream joins, and stateful processing emerged, the project evolved to include a Java-based Flink job (`flink-java`).
- Flink connects to Azure Event Hubs using the Kafka protocol endpoint, enabling high-throughput, low-latency stream processing with full support for event-time semantics and advanced windowing.
- The Flink job demonstrates:
  - **Cross-Stream Join:** Joins SCADA and GPS streams by device/unit ID within a configurable time window using Flink's `intervalJoin` API. This enables event correlation and enrichment (e.g., associating sensor readings with location data).
  - **Stateful Processing:** Implements windowed aggregations (such as moving averages) using Flink's keyed state and window APIs. This is the foundation for anomaly detection, trend analysis, and other advanced analytics.
  - **Output Enrichment:** The joined and aggregated results can be written to Cosmos DB or other sinks, making them available for downstream applications and dashboards.
- The Flink reference implementation is modular and extensible, serving as a template for future analytical features and production workloads.

### Phase 3: Multi-Agent Communication, MCP Server, and End-to-End Testing

- Introduced the **MCP server** (`/mcp_server`) to support Model Context Protocol (MCP) for agent-to-agent (A2A) communication, enabling robust, protocol-driven interactions between agents.
- Agents now support both **Legacy** and **MCP** communication modes:
  - **Legacy Mode:** Agents communicate using default Event Hub topics (`agent-data`, `agent-analysis-results`).
  - **MCP Mode:** Agents communicate using protocol-based topics (`mcp-requests`, `mcp-responses`) and register with the MCP server for structured message exchange.
  - **Auto Mode:** Agents attempt MCP first, falling back to legacy if MCP is not available.
- The communication mode is controlled by the `AGENT_COMM_MODE` environment variable in `.env`.
- Topic names and connection strings are managed via `.env` and/or Azure Key Vault, and must be kept in sync across code, config, and Azure resources.
- **End-to-end testing** now validates the full data pipeline in both MCP and Legacy modes:
  - Simulators → Event Hubs → Stream Processor (Python/Flink) → Cosmos DB → Agents (MCP/Legacy) → Dashboard
  - Step-by-step instructions are provided for provisioning, configuration, running all components, and verifying data flow and agent communication.
- The platform now supports flexible, decoupled agent orchestration and is validated for both legacy and modern (MCP) workflows, ensuring future scalability and maintainability.

### Phase 4: Orchestrator, Scalability, and Observability

In this phase, the focus is on building an orchestrator for managing complex agent workflows and enhancing the platform's scalability and observability.

#### Key Objectives

- **Orchestrator Development:** Create a centralized orchestrator component that manages and coordinates workflows across multiple agents, enabling complex, multi-step processing and decision-making.
- **Scalability Enhancements:** Optimize the platform to support a growing number of agents and higher event throughput, ensuring reliable performance at scale.
- **Observability Features:** Implement comprehensive monitoring and logging for all components, providing insights into system behavior, performance, and potential issues.

#### Orchestrator Design

The orchestrator is designed as a separate microservice that interacts with the existing components:

- **Workflow Management:** Define and manage workflows that specify the sequence of actions and data transformations across agents.
- **Dynamic Scaling:** Automatically scale the number of agent instances based on workload, event volume, and processing requirements.
- **Error Handling and Retries:** Implement robust error handling, automatic retries, and fallback mechanisms to ensure reliable processing and fault tolerance.

#### Implementation Plan

1. **Develop Orchestrator Service:**
    - Create a new microservice for the orchestrator, with a REST API for workflow submission and status monitoring.
    - Implement workflow management, dynamic scaling, and error handling features.

2. **Integrate with Existing Components:**
    - Update agent implementations to support orchestration commands and status reporting.
    - Ensure seamless communication and data exchange between the orchestrator and agents.

3. **Enhance Monitoring and Logging:**
    - Integrate with Azure Monitor, Application Insights, or similar services for comprehensive observability.
    - Implement structured logging, distributed tracing, and custom metrics for all components.

4. **Testing and Validation:**
    - Thoroughly test the orchestrator with simulated workloads and failure scenarios.
    - Validate end-to-end workflows, performance, scalability, and fault tolerance.

5. **Documentation and Training:**
    - Update documentation to include orchestrator usage, configuration, and troubleshooting.
    - Provide training and examples for users to define and manage their own workflows.

---

## Getting Started

Follow these steps to set up the infrastructure and run the simulation environment.

### 1. Prerequisites

- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
- [Terraform](https://www.terraform.io/downloads.html)
- [Python 3.8+](https://www.python.org/downloads/)

### 2. Infrastructure Deployment (Terraform)

First, deploy the necessary Azure resources using the provided Terraform scripts.

1. **Authenticate with Azure:**

    ```sh
    az login
    ```

2. **Navigate to the dev environment directory:**

    ```sh
    cd terraform/environments/dev
    ```

3. **Initialize and apply the Terraform plan:**

    ```sh
    terraform init
    terraform plan
    terraform apply
    ```

    This will provision all the necessary resources, including Event Hubs, Cosmos DB, and a Key Vault.

### 3. Application Setup

Next, configure your local environment to run the Python simulators and processor.

1. **Navigate to the simulators directory:**

    ```sh
    cd ../../../simulators 
    ```

    *(Note: If you are in `terraform/environments/dev`, navigate back to the root and then into `simulators`)*

2. **Create and activate a Python virtual environment:**

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

3. **Install dependencies:**

    ```sh
    pip install -r requirements.txt
    ```

### 4. Security & Configuration

The application uses `DefaultAzureCredential` for secure, passwordless access to Azure resources.

1. **Configure Environment File:**
    Create a `.env` file by copying the sample and adding your Key Vault URI.

    ```powershell
    # In the 'simulators' directory
    copy .env.sample .env
    ```

    Now, open `.env` and set the `KEY_VAULT_URI` variable:

    ```env
    KEY_VAULT_URI="https://<your-key-vault-name>.vault.azure.net/"
    ```

2. **Configure Event Hubs Connection for Agents:**
    For the agents to communicate via Event Hubs, they need a connection string with access to the namespace.

    First, retrieve the connection string using the Azure CLI. The following command gets the primary connection string for the default access policy on your Event Hubs namespace:

    ```powershell
    # PowerShell
    $eventHubConnectionString = az eventhubs namespace authorization-rule keys list --resource-group idtwin-dev-rg --namespace-name idtwin-dev-ehns --name RootManageSharedAccessKey --query primaryConnectionString --output tsv
    echo "EVENT_HUB_CONNECTION_STR=\"$eventHubConnectionString\"" | Out-File -Append -Encoding utf8 .env
    ```

    ```sh
    # Bash
    eventHubConnectionString=$(az eventhubs namespace authorization-rule keys list --resource-group idtwin-dev-rg --namespace-name idtwin-dev-ehns --name RootManageSharedAccessKey --query primaryConnectionString --output tsv)
    echo "EVENT_HUB_CONNECTION_STR=\"$eventHubConnectionString\"" >> .env
    ```

    This will automatically append the `EVENT_HUB_CONNECTION_STR` to the `.env` file in your current directory. Make sure you run this from the project root where your `.env` file is located.

    Alternatively, you can run the `az` command and manually copy the output into your `.env` file like this:

    ```env
    EVENT_HUB_CONNECTION_STR="Endpoint=sb://...;SharedAccessKeyName=...;SharedAccessKey=...;EntityPath=..."
    ```

3. **Assign RBAC Permissions:**
    Your user account needs data-plane permissions on the Azure resources. Run the following Azure CLI commands, replacing `<your-principal-object-id>` with your user's Object ID (`az ad signed-in-user show --query id -o tsv`).

    ```sh
    # Set your identity's object ID
    PRINCIPAL_ID="<your-principal-object-id>"

    # Set your resource names (these are the defaults from Terraform)
    KEY_VAULT_NAME="idtwin-dev-kv"
    EVENT_HUBS_NAMESPACE="idtwin-dev-ehns"
    COSMOS_DB_ACCOUNT="idtwin-dev-cosmos"

    # Grant Key Vault access
    az keyvault secret set-permission --name $KEY_VAULT_NAME --object-id $PRINCIPAL_ID --permissions get list

    # Grant Event Hubs data access
    az role assignment create --role "Azure Event Hubs Data Owner" --assignee $PRINCIPAL_ID --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/idtwin-dev-rg/providers/Microsoft.EventHub/namespaces/$EVENT_HUBS_NAMESPACE"

    # Grant Cosmos DB data access (Contributor is needed for programmatic resource creation)
    az role assignment create --role "Contributor" --assignee $PRINCIPAL_ID --scope "/subscriptions/$(az account show --query id -o tsv)/resourceGroups/idtwin-dev-rg/providers/Microsoft.DocumentDB/databaseAccounts/$COSMOS_DB_ACCOUNT"
    ```

4. **Add Event Hubs Connection String to `.env`**:
    The agent-to-agent communication requires a connection string for the Event Hubs Namespace. Retrieve it using the Azure CLI and add it to your root `.env` file.

    ```powershell
    # Get the connection string
    $eventHubConnectionString = az eventhubs namespace authorization-rule keys list --resource-group idtwin-dev-rg --namespace-name idtwin-dev-ehns --name RootManageSharedAccessKey --query primaryConnectionString --output tsv

    # Append it to your .env file
    Add-Content -Path ".\.env" -Value "EVENT_HUB_CONNECTION_STR=\"$eventHubConnectionString\""
    
    echo "EVENT_HUB_CONNECTION_STR added to .env file."
    ```

5. **Configure Firewalls:**
    For local development, add your public IP address to the firewall rules for Key Vault and Cosmos DB in the Azure Portal.

---

## Running a Full Simulation

The easiest way to run the platform is using the `run_simulation.py` script, which starts and manages a simulator and its corresponding stream processor in one command.

1. **Ensure your virtual environment is active** and you are in the `simulators` directory.
2. **Run the simulation:**
    You can run all simulators in parallel, or specify a stream type (`scada`, `plc`, or `gps`) to run only that simulator. For example:

    ```powershell
    # Run all simulators in parallel
    python run_simulation.py

    # Run only the SCADA simulator
    python run_simulation.py scada

    # Run only the PLC simulator
    python run_simulation.py plc

    # Run only the GPS simulator
    python run_simulation.py gps
    ```

    You will see interleaved output from all running simulators, showing events being sent in real-time.

    To stop the simulation, press `Ctrl+C`.

### Running Components Manually (Alternative)

While `run_simulation.py` is the recommended way to run the platform for development, you can also run the stream processor and simulators manually in separate terminals. This can be useful for debugging individual components or for running only a subset of streams.

#### 1. Run All Simulators in Parallel

To launch all data simulators (SCADA, PLC, GPS) in parallel, use:

```sh
python run_simulation.py
```

This will start all three simulators as separate processes. Press `Ctrl+C` to stop all simulators at once. The script will handle graceful shutdown and process cleanup.

#### 2. Run a Single Simulator and Processor Pair

You can also run a single simulator and its corresponding processor for focused testing. For example, to run only the SCADA stream:

```sh
python run_simulation.py scada
```

Valid arguments are:

- `scada` — runs only the SCADA simulator
- `plc` — runs only the PLC simulator
- `gps` — runs only the GPS simulator
- No argument — runs all simulators in parallel

#### 3. Run the Event Stream Processor (Python)

The unified event stream processor can be run directly and requires the `--stream-type` argument to specify which stream to process. For example:

```sh
python event_stream_processor.py --stream-type scada
```

Valid arguments for `--stream-type` are:

- `scada` — process SCADA events
- `plc` — process PLC events
- `gps` — process GPS events
- (If supported) `all` — process all streams

**Example: Run the SCADA processor and simulator in separate terminals:**

Terminal 1:

```sh
python event_stream_processor.py --stream-type scada
```

Terminal 2:

```sh
python scada_simulator.py
```

**Example: Run all simulators and processors in parallel:**

Terminal 1:

```sh
python run_simulation.py
```

Terminal 2 (optional, for a specific processor):

```sh
python event_stream_processor.py --stream_type scada
```

**Notes:**

- The simulators and processor rely on the `.env` file for configuration (Key Vault URI, etc.) and use Azure AD to authenticate. Ensure you have logged in with `az login` and have the required permissions.
- You can control the event rate for each simulator by setting the `SCADA_EVENT_RATE`, `PLC_EVENT_RATE`, or `GPS_EVENT_RATE` environment variables.
- These simulators are for development and testing purposes only.

---

## Advanced Stream Processing (Apache Flink)

For more complex, stateful stream processing scenarios, this project includes a Maven-based Java application using Apache Flink. It processes the same event streams from Event Hubs (using its Kafka endpoint) and writes the results to Azure Cosmos DB, authenticating via Azure AD.

### Flink Prerequisites

Before you can build and run the Flink job, you will need the following installed on your system:

1. **Java Development Kit (JDK) 11:**
    - The project is standardized on the **Microsoft Build of OpenJDK 11**.
    - You can install it on Windows via `winget install Microsoft.OpenJDK.11` or download it from the official Microsoft site for other operating systems.
    - **Crucially**, you must set the `JAVA_HOME` environment variable to point to the JDK's installation directory.

2. **Apache Maven:**
    - A build automation tool used for Java projects.
    - You can download it from the [official Maven website](https://maven.apache.org/downloads.html).
    - Ensure the `mvn` command is available in your system's PATH.

### Flink Configuration

The Flink job is configured using environment variables defined in the `.env` file in the **project root directory**. Ensure the following variables are set correctly:

```env
# Flink Job Configuration
# Replace <YourEventHubsNamespace> with your actual Event Hubs Namespace
KAFKA_BOOTSTRAP_SERVERS=<YourEventHubsNamespace>.servicebus.windows.net:9093
FLINK_KAFKA_TOPICS=scada-production-hub,plc-control-hub,gps-logistics-hub

# Cosmos DB Configuration (used by the Flink Job)
COSMOS_DB_ENDPOINT=https://<YourCosmosDbAccount>.documents.azure.com:443/
COSMOS_DB_DATABASE=industrial-digital-twin-db
```

**Authentication:** The job uses `DefaultAzureCredential` for authenticating to Cosmos DB, so no keys are needed in the `.env` file. Ensure you are logged in via the Azure CLI (`az login`) or have the appropriate service principal environment variables set for authentication to work.

### Building the Flink Job

To compile the Java source code and package it into a runnable JAR file, navigate to the `flink-java` directory and run the following Maven command:

```sh
# From the project root
cd flink-java
mvn clean package
cd ..
```

This will create a JAR file in the `flink-java/target/` directory (e.g., `flink-java-1.0-SNAPSHOT.jar`).

### Running the Flink Job

Once the JAR file is built, you can submit it to a running Flink cluster. For local development, you can use a standalone Flink distribution.

1. **Download Apache Flink:** Download a stable Flink distribution (e.g., Flink 1.17 or later) from the [official Flink website](https://flink.apache.org/downloads/).

2. **Start a Local Flink Cluster:**

    ```sh
    # Navigate to your Flink distribution directory
    # cd /path/to/flink-1.17.x

    # Start the cluster
    ./bin/start-cluster.sh
    ```

3. **Submit the Job:**
    From the Flink distribution directory, use the `flink run` command to submit your JAR. You will need to provide the absolute path to the JAR file created in the previous step.

    ```sh
    # Example from within the Flink distribution directory
    ./bin/flink run c:\Projects\GithubLocal\industrial-digital-twin-multiagent-platform\flink-java\target\flink-java-1.0-SNAPSHOT.jar
    ```

You can monitor the job's progress through the Flink Web UI, which is typically available at `http://localhost:8081`.

---

## Project Structure

```
industrial-digital-twin-multiagent-platform/
├── .github/                  # CI/CD workflows and GitHub Actions
├── agents/                   # Python code for intelligent agents (in development)
├── dashboard/                # Web-based UI for data visualization (Streamlit, in development)
│   ├── dashboard.py          # Streamlit dashboard for real-time event visualization
│   ├── requirements.txt      # Python dependencies for dashboard
│   └── ...
├── docs/                     # Project documentation and architecture diagrams
│   ├── industrial_architecture_diagram.png   # Architecture diagram (image)
│   └── ...
├── flink-java/               # Maven project for the Flink Java stream processor
│   ├── src/main/java/com/industrialdigitaltwin/flink/
│   │   ├── StreamingJob.java         # Main Flink job (reference implementation)
│   │   ├── ScadaEvent.java           # SCADA event POJO
│   │   ├── GpsEvent.java             # GPS event POJO
│   │   ├── PlcEvent.java             # PLC event POJO
│   │   ├── EnrichedEvent.java        # Output of cross-stream join
│   │   ├── MovingAverageAggregate.java # Windowed aggregation logic
│   │   └── ...                       # Additional Flink utilities and classes
│   ├── pom.xml                       # Maven build configuration
│   └── ...
├── simulators/                # Python scripts for data generation
│   ├── scada_simulator.py     # SCADA event generator
│   ├── plc_simulator.py       # PLC event generator
│   ├── gps_simulator.py       # GPS event generator
│   ├── run_simulation.py      # Orchestrates processor and simulator for dev
│   ├── event_stream_processor.py # Unified Python stream processor
│   ├── site_locations.json    # Facility ID to location mapping
│   ├── requirements.txt       # Python dependencies
│   └── ...
├── terraform/                 # Terraform modules for infrastructure-as-code
│   ├── modules/               # Reusable infrastructure components
│   └── environments/          # Environment-specific configs (dev, staging, prod)
├── industrial_architecture_diagram.html # Interactive architecture diagram
├── PROJECT-DECISIONS.md       # Log of key architectural and technical decisions
├── README.md                  # This file
└── ...                        # Other root-level files (e.g., .env.sample, .gitignore)
```

- **Each major component is modularized for clarity and scalability.**
- **Terraform** manages all Azure infrastructure, with clear separation between reusable modules and environment-specific settings.
- **Simulators** and **stream processors** are decoupled, supporting both Python and Java (Flink) implementations.
- **Dashboard** is implemented in Streamlit for real-time, interactive visualization of global events.
- **Documentation** is comprehensive, with all major decisions and troubleshooting steps logged for future reference.

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

---
