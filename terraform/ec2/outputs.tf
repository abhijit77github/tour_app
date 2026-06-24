output "instance_id" {
  value       = aws_instance.tour_app.id
  description = "EC2 instance ID"
}

output "instance_public_ip" {
  value       = var.allocate_eip ? aws_eip.tour_app[0].public_ip : aws_instance.tour_app.public_ip
  description = "Public IP address for the EC2 test deployment"
}

output "instance_public_dns" {
  value       = aws_instance.tour_app.public_dns
  description = "Public DNS name for the EC2 instance"
}

output "app_url" {
  value       = var.domain_name == "_" ? "http://${var.allocate_eip ? aws_eip.tour_app[0].public_ip : aws_instance.tour_app.public_ip}" : "${var.enable_tls ? "https" : "http"}://${var.domain_name}"
  description = "Base URL for the frontend behind Nginx"
}

output "ssh_command" {
  value       = var.key_name == null ? "No key_name configured" : "ssh ubuntu@${var.allocate_eip ? aws_eip.tour_app[0].public_ip : aws_instance.tour_app.public_ip}"
  description = "Convenience SSH command"
}