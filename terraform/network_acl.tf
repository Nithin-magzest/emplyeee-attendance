# ---------------------------------------------------------------------------
# Network ACL — stateless packet-filtering layer, subnet-level
#
# aws_security_group.app_firewall (main.tf) is stateful — it auto-allows
# return traffic for any connection it permitted, and never inspects a
# packet in isolation from the connection it belongs to. A Network ACL is
# the genuinely stateless layer: every packet, in both directions, is
# checked against these rules independently, with no memory of prior
# packets. This is what closes the "packet filtering firewall" gap noted
# in FIREWALL_ARCHITECTURE.md §1 — until now this project relied entirely
# on the VPC's default NACL (allow-all), so the Security Group was doing
# 100% of the filtering.
#
# Because NACLs are stateless, the ingress rules below must explicitly
# allow the EPHEMERAL PORT RANGE (1024-65535) inbound — that's where
# return traffic for the instance's own outbound connections (RDS, Redis,
# SMTP, AWS APIs, Let's Encrypt, apt/pip) lands. Skipping that rule would
# not break inbound web traffic, but would silently break every outbound
# connection the app itself makes, since the reply packets would be
# dropped on arrival.
#
# NOT auto-associated with the app server's subnet by default (subnet_ids
# defaults to [] below) — same pattern as aws_security_group.app_firewall's
# "provisioned but not attached" note. A NACL applies to every instance in
# the subnet, not just this one, and a misconfigured rule fails closed
# (silently drops traffic) rather than failing open, so this is deliberately
# opt-in: set var.app_subnet_ids and re-apply once the rules below have
# been reviewed against the actual subnet's other occupants (if any).
# ---------------------------------------------------------------------------

variable "app_subnet_ids" {
  description = "Subnet ID(s) to associate this NACL with — leave empty ([]) to provision the NACL without attaching it to any subnet yet (safe default; a NACL applies to every resource in the subnet, not just this app)."
  type        = list(string)
  default     = []
}

resource "aws_network_acl" "app" {
  vpc_id     = var.vpc_id
  subnet_ids = var.app_subnet_ids

  tags = {
    Name = "${var.project_name}-app-nacl"
  }
}

# ── Inbound ──────────────────────────────────────────────────────────────

resource "aws_network_acl_rule" "in_http" {
  network_acl_id = aws_network_acl.app.id
  rule_number    = 100
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 80
  to_port        = 80
}

resource "aws_network_acl_rule" "in_https" {
  network_acl_id = aws_network_acl.app.id
  rule_number    = 110
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 443
  to_port        = 443
}

# One rule per trusted admin CIDR (NACL rules take a single cidr_block
# each, unlike the security group's list-based cidr_blocks) — SSH only;
# RDP/MSSQL/direct-DB/alt-HTTP are deliberately NOT mirrored here since
# aws_security_group.app_firewall already filters them to the same CIDRs
# and stacking identical restrictions at both layers adds no protection,
# only more rules to keep in sync.
resource "aws_network_acl_rule" "in_ssh" {
  for_each       = toset(var.trusted_admin_cidrs)
  network_acl_id = aws_network_acl.app.id
  rule_number    = 120 + index(var.trusted_admin_cidrs, each.value)
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = each.value
  from_port      = 22
  to_port        = 22
}

# Return traffic for connections the instance itself initiates outbound
# (RDS, Redis if ever moved off-box, SMTP, AWS APIs, Let's Encrypt,
# package repos). Required because NACLs are stateless — see header note.
resource "aws_network_acl_rule" "in_ephemeral" {
  network_acl_id = aws_network_acl.app.id
  rule_number    = 200
  egress         = false
  protocol       = "tcp"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 1024
  to_port        = 65535
}

# ── Outbound ─────────────────────────────────────────────────────────────
# Deliberately permissive (matches aws_security_group.app_firewall's own
# egress: from_port=0, to_port=0, protocol=-1) — this NACL's job is
# inbound packet filtering, not egress control, matching the scope of the
# gap it's closing.

resource "aws_network_acl_rule" "out_all" {
  network_acl_id = aws_network_acl.app.id
  rule_number    = 100
  egress         = true
  protocol       = "-1"
  rule_action    = "allow"
  cidr_block     = "0.0.0.0/0"
  from_port      = 0
  to_port        = 0
}
