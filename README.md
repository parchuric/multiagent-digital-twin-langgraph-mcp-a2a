# Industrial Digital Twin Multi-Agent Platform - Terraform Infrastructure

This project uses a modular Terraform setup to provision a minimal, cost-effective dev environment in Azure (East US 2).

## Directory Structure

- `terraform/modules/` — Reusable modules for Azure resources (Event Hubs, AKS, Cosmos DB, PostgreSQL, Redis, Blob Storage, Networking)
- `terraform/environments/dev/` — Dev environment configuration (ready to deploy)
- `.github/copilot-instructions.md` — Copilot workspace instructions

## Quickstart (Dev Only)

1. Install [Terraform](https://www.terraform.io/downloads.html) and [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli).
2. Authenticate with Azure CLI:
   ```sh
   az login
   ```
3. Change directory to the dev environment:
   ```sh
   cd terraform/environments/dev
   ```
4. Initialize Terraform:
   ```sh
   terraform init
   ```
5. Review and apply the plan:
   ```sh
   terraform plan
   terraform apply
   ```

> **Note:** Only the dev environment is configured for deployment. Higher environments (staging, prod, dr) will have modules but are not to be deployed yet.

## Cost Optimization
- All resources are provisioned with minimal, dev-grade SKUs to keep costs low.
- For production, update variables and modules for scale, redundancy, and compliance.

## Next Steps
- Add/modify modules in `terraform/modules/` as needed.
- Expand environment configs for staging/prod/dr (do not deploy yet).
- See `PROJECT-VISION.md` for architecture and requirements.

## Industrial Digital Twin Multi-Agent Platform: Dev Environment

### Current State
- All core Azure resources for the dev environment are provisioned via Terraform modules:
  - Resource Group
  - Virtual Network, Subnet, NSG
  - Managed Identity
  - Event Hubs Namespace and Event Hubs (gps, plc, scada)
  - AKS (Kubernetes) Cluster
  - Cosmos DB Account
  - PostgreSQL Flexible Server (Central US, name: idtwin-dev-pg-centralus)
  - Redis Cache
  - Blob Storage Account

### PostgreSQL Region/Name Workaround
- Azure region restrictions and name conflicts required deploying PostgreSQL Flexible Server in `Central US` with a unique name (`idtwin-dev-pg-centralus`).
- If you encounter region or name errors, update the region or use a unique name in `main.tf`.

### AKS Cluster Troubleshooting
- If Terraform fails to update the AKS cluster with an error about the cluster not being in the 'Running' state, check the Azure Portal and start or troubleshoot the cluster as needed.

### How to Verify Resources
- Run `terraform state list` in `terraform/environments/dev` to see all resources managed by Terraform.
- Check the Azure Portal for the resource group and all resources.

## Simulators and Consumers (Event Hub Data Validation)

All simulators and consumers are located in the `simulators/` directory. They securely fetch Event Hub connection strings and names from Azure Key Vault.

### Prerequisites
- Python 3.8+
- Azure CLI authenticated (for local dev, to use DefaultAzureCredential)
- Key Vault secrets set for each Event Hub (see earlier instructions)

### Setup (First Time)
```powershell
cd simulators
python -m venv .venv
.venv\Scripts\Activate
pip install -r requirements.txt
```

### Set Key Vault URI (if not using default)
```powershell
$env:KEY_VAULT_URI="https://idtwin-dev-kv.vault.azure.net/"
```

### Run Simulators
```powershell
python scada_simulator.py
python plc_simulator.py
python gps_simulator.py
```

### Run Consumers
```powershell
python scada_eventhub_consumer.py
python plc_eventhub_consumer.py
python gps_eventhub_consumer.py
```

- You can run simulators and consumers in separate terminals for real-time validation.
- All secrets are fetched from Azure Key Vault; no secrets are stored in .env files.
- If you need to change the event rate, set the appropriate environment variable (e.g., `$env:SCADA_EVENT_RATE=10`).

---

For more details and project decisions, see PROJECT-DECISIONS.md.
