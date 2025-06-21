resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location
}

module "network" {
  source              = "../../modules/network"
  vnet_name           = "idtwin-dev-vnet"
  address_space       = ["10.10.0.0/16"]
  subnet_name         = "idtwin-dev-subnet"
  subnet_prefixes     = ["10.10.1.0/24"]
  nsg_name            = "idtwin-dev-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

module "identity" {
  source              = "../../modules/managed_identity"
  name                = "idtwin-dev-identity"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

module "event_hubs" {
  source              = "../../modules/event_hubs"
  namespace_name      = "idtwin-dev-ehns"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

module "aks" {
  source              = "../../modules/aks"
  name                = "idtwin-dev-aks"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = "idtwin-dev"
}

module "cosmosdb" {
  source              = "../../modules/cosmosdb"
  name                = "idtwin-dev-cosmos"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

module "postgresql" {
  source              = "../../modules/postgresql"
  name                = "idtwin-dev-pg-centralus"
  # Provision PostgreSQL Flexible Server in Central US with unique name
  location            = "Central US"
  resource_group_name = azurerm_resource_group.main.name
  admin_username      = "pgadmin"
  admin_password      = "ChangeMe123!" # Replace with a secure value or use secrets
}

module "redis" {
  source              = "../../modules/redis"
  name                = "idtwin-dev-redis"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

module "blob_storage" {
  source              = "../../modules/blob_storage"
  name                = "idtwindevstorage"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
}

module "keyvault" {
  source              = "../../modules/keyvault"
  name                = "idtwin-dev-kv"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku_name            = "standard"
}
