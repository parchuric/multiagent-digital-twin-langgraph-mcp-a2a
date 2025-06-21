resource "azurerm_user_assigned_identity" "main" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name
}

output "client_id" {
  value = azurerm_user_assigned_identity.main.client_id
}

output "id" {
  value = azurerm_user_assigned_identity.main.id
}
