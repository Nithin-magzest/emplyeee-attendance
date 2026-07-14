output "rds_endpoint" {
  description = "Paste this into .env as DB_HOST (strip the :5432 port suffix)"
  value       = aws_db_instance.this.address
}

output "rds_port" {
  value = aws_db_instance.this.port
}

output "app_firewall_sg_id" {
  description = "Attach this security group to the existing EC2 instance (EC2 console -> Actions -> Security -> Change security groups) — it isn't attached automatically since the instance was originally provisioned outside Terraform"
  value       = aws_security_group.app_firewall.id
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

output "app_secrets_arn" {
  description = "Set AWS_SECRET_ID to this on the EC2 instance, then populate it: aws secretsmanager put-secret-value --secret-id <this-arn> --secret-string file://secrets-payload.json"
  value       = aws_secretsmanager_secret.app_secrets.arn
}

output "ebs_cmk_alias" {
  description = "New EBS volumes in this account/region now default to this key. The EXISTING app-server volume must be migrated manually (snapshot -> encrypted copy -> new volume -> swap) — this does not happen automatically."
  value       = aws_kms_alias.ebs_cmk.name
}

output "waf_web_acl_arn" {
  description = "Only takes effect once attached to a CloudFront distribution or ALB — set app_origin_domain to deploy the CloudFront distribution below, or attach manually to an ALB if you provision one instead."
  value       = aws_wafv2_web_acl.app.arn
}

output "cloudfront_domain_name" {
  description = "Point your DNS (CNAME/ALIAS) here once ready to cut over — only created when app_origin_domain is set. Until then this stays empty and no CloudFront distribution exists."
  value       = length(aws_cloudfront_distribution.app) > 0 ? aws_cloudfront_distribution.app[0].domain_name : null
}

output "cloudfront_distribution_id" {
  description = "For verification: aws cloudfront get-distribution --id <this> --query \"Distribution.DistributionConfig.WebACLId\" — should equal waf_web_acl_arn above if the WAF is actually bound."
  value       = length(aws_cloudfront_distribution.app) > 0 ? aws_cloudfront_distribution.app[0].id : null
}

output "ecr_repository_url" {
  description = "podman login/push target if you adopt ECR as the image registry — see the comment in security_hardening.tf for why this needs a CI/CD workflow change to actually take effect"
  value       = aws_ecr_repository.app.repository_url
}

output "app_nacl_id" {
  description = "Provisioned but not attached to any subnet until var.app_subnet_ids is set (see network_acl.tf) — find the EC2 instance's subnet ID (EC2 console -> instance -> Networking tab) and set it there before applying, so this stateless filtering layer actually takes effect."
  value       = aws_network_acl.app.id
}

output "network_firewall_arn" {
  description = "Empty/null until var.firewall_subnet_ids is set (see network_firewall.tf) — and even then, only INSPECTS traffic once your VPC's route tables are updated to send app-subnet traffic through the firewall endpoint. Provisioning this resource alone does not put it in the traffic path."
  value       = length(aws_networkfirewall_firewall.app) > 0 ? aws_networkfirewall_firewall.app[0].arn : null
}
