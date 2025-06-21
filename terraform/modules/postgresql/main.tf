resource "azurerm_postgresql_flexible_server" "main" {
  name                   = var.name
  location               = var.location
  resource_group_name    = var.resource_group_name
  administrator_login    = var.admin_username
  administrator_password = var.admin_password
  sku_name               = "B_Standard_B1ms"
  storage_mb             = 32768
  version                = "14"
  zone                   = "1"
  backup_retention_days  = 7
  geo_redundant_backup_enabled = false
  public_network_access_enabled = true
}
