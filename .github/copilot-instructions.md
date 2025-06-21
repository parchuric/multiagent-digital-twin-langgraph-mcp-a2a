<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->

- This project is a modular Terraform setup for Azure, focused on a cost-effective dev environment in East US 2.
- All infrastructure recommendations and code should default to minimal, dev-grade resources unless otherwise specified.
- Higher environment modules (staging, prod, dr) should be created but not deployed.
- Use best practices for Terraform module structure and Azure resource naming.
- Document all resource and module variables clearly for future scaling.
