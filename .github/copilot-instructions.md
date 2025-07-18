<!-- Copilot Custom Instructions for Industrial Digital Twin Multi-Agent Platform -->

# Project Overview
- This is a modular Azure-based digital twin platform for industrial data, using Python, Java (Flink), and Terraform IaC.
- The architecture is event-driven: **Simulators → Event Hubs → Stream Processors (Python/Flink) → Cosmos DB → Agents → Dashboard**.
- All code and infra should default to minimal, dev-grade resources unless otherwise specified.

# Major Components
- **/simulators/**: Python scripts for SCADA, PLC, GPS event generation. Use `.env` for config. Run all with `python run_simulation.py`.
- **/dashboard/**: Streamlit app for real-time visualization. Start with `streamlit run dashboard.py`.
- **/agents/**: Multi-agent system (DataQueryAgent, AnalysisAgent) supporting both legacy and MCP (Model Context Protocol) communication via Azure Event Hubs. Agents are decoupled and communicate via topics, not direct calls.
- **/mcp_server/**: Implements MCP protocol server and agent communication logic.
- **/flink-java/**: Java Maven project for advanced stream processing (cross-stream joins, windowed analytics). Build with `mvn clean package`.
- **/terraform/**: Modular infrastructure-as-code. Use `terraform/environments/dev` for dev deployments. Higher envs (staging, prod, dr) are defined but not deployed by default.

# Agent Communication Patterns
- Agents support three modes: `legacy`, `mcp`, `auto` (set via `AGENT_COMM_MODE` in `.env`).
  - **Legacy**: Topics `agent-data`, `agent-analysis-results`.
  - **MCP**: Topics `mcp-requests`, `mcp-responses` and protocol server.
  - **Auto**: Tries MCP, falls back to legacy.
- Topic names and connection strings are set via `.env` and/or Azure Key Vault. Always keep topic names in sync across config, code, and Azure.
- Never mix raw ingestion topics (e.g., `scada-production-hub`) with agent-to-agent topics.

# Developer Workflow
- **Provision infra**: `cd terraform/environments/dev; terraform init; terraform apply` (requires Azure CLI login).
- **Configure local env**: Copy `.env.sample` to `.env`, set Key Vault URI, Event Hub connection string, and agent mode.
- **Install Python deps**: `python -m venv .venv; .venv\Scripts\activate; pip install -r requirements.txt` (per component).
- **Run all simulators**: `python run_simulation.py` (in `/simulators`).
- **Run agents**: `python data_query_agent.py` and `python analysis_agent.py` (in `/agents`).
- **Run dashboard**: `streamlit run dashboard.py` (in `/dashboard`).
- **Build Flink job**: `cd flink-java; mvn clean package`.

# Project-Specific Conventions
- Use clear, environment-prefixed Azure resource names (e.g., `idtwin-dev-ehns`).
- Document all resource/module variables for future scaling.
- All major architectural decisions are logged in `PROJECT-DECISIONS.md`.
- For Windows: If Python subprocesses persist after Ctrl+C, kill them in Task Manager or use WSL for better process handling.
- All new code should follow the modular, decoupled pattern: no direct cross-component imports except for shared config/utilities.

# References
- See `README.md` for full architecture, workflows, and troubleshooting.
- See `PROJECT-DECISIONS.md` for rationale behind key design choices.
- See `/docs/industrial_architecture_diagram.png` for a visual overview.

# Terraform/IaC Guidance (preserved)
- Use best practices for Terraform module structure and Azure resource naming.
- Document all resource and module variables clearly for future scaling.
- Higher environment modules (staging, prod, dr) should be created but not deployed.
- All infrastructure recommendations and code should default to minimal, dev-grade resources unless otherwise specified.
