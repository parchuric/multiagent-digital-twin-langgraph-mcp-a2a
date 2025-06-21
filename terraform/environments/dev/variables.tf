variable "location" { default = "East US 2" }
variable "resource_group_name" { default = "idtwin-dev-rg" }
variable "postgresql_location" {
  description = "Azure region for PostgreSQL Flexible Server (use a region with available capacity)"
  type        = string
  default     = "Central US"
}

# Add more variables as needed for each module
