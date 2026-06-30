output "rds_endpoint" {
  description = "Paste this into .env as DB_HOST (strip the :3306 port suffix)"
  value       = aws_db_instance.this.address
}

output "rds_port" {
  value = aws_db_instance.this.port
}

output "ec2_iam_instance_profile_name" {
  description = "Attach this instance profile to the existing EC2 instance (EC2 console → Actions → Security → Modify IAM role)"
  value       = aws_iam_instance_profile.ec2_app_profile.name
}

output "sns_alert_topic_arn" {
  description = "Confirm the subscription email sent to alert_email before alarms will actually deliver"
  value       = aws_sns_topic.alerts.arn
}

output "backups_s3_bucket" {
  value = aws_s3_bucket.backups.bucket
}

output "dlm_required_instance_tag" {
  description = "Tag the EC2 instance with this key/value so the daily EBS snapshot policy applies to it"
  value       = "DlmBackup = ${var.project_name}-app-server"
}
