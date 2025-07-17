output "redis_host_name" {
  description = "The hostname of the Redis Cache."
  value       = module.redis.redis_host_name
}

output "redis_primary_key" {
  description = "The primary access key for the Redis Cache."
  value       = module.redis.redis_primary_key
  sensitive   = true
}