# Firewall Architecture

This project doesn't use one monolithic "firewall" — it layers several
AWS-managed and application-level controls that together cover the five
classic firewall categories. This document maps each category to what is
**actually deployed today**, with exact file references, and is explicit
about what's genuinely missing rather than implying coverage that isn't
there.

| # | Type | Status | Primary location |
|---|------|--------|-------------------|
| 1 | Packet filtering | Provisioned, not yet attached to a subnet | `terraform/network_acl.tf` |
| 2 | Stateful inspection | Implemented | `terraform/main.tf` |
| 3 | Proxy firewall | Implemented (reverse proxy only) | `nginx/nginx.conf.template` |
| 4 | Next-generation firewall (NGFW) | Resource-complete, not yet in the traffic path (no subnet association or route-table wiring) | `terraform/network_firewall.tf` |
| 5 | Web Application Firewall | Provisioned, not yet in the traffic path | `terraform/security_hardening.tf` |

---

## 1. Packet Filtering Firewall

Filters purely on IP / port / protocol, no awareness of connection state.

- **What exists**: AWS Security Groups (`aws_security_group.app_firewall`,
  `aws_security_group.rds` — `terraform/main.tf:36-170`) filter every
  inbound connection by port and source CIDR: `80`/`443` open to
  `0.0.0.0/0`; `22`/`3389`/`5432`/`1433`/`8080`/`8443` restricted to
  `var.trusted_admin_cidrs`; `21`/`23`/`25` have no rule at all (default
  deny).
- **The catch**: Security Groups are *stateful* (see §2), not pure packet
  filters. The textbook stateless packet-filtering layer in AWS is the
  **Network ACL**, applied per-subnet.
- **Now provisioned**: `aws_network_acl.app` (`terraform/network_acl.tf`)
  mirrors the Security Group's inbound policy (80/443 public, 22 filtered
  to `trusted_admin_cidrs`) as a genuinely stateless layer — including the
  ephemeral-port-range rule (1024-65535) that stateless filtering requires
  for return traffic, which the stateful Security Group never needed.
- **Not attached yet**: `var.app_subnet_ids` defaults to `[]`, so this
  NACL exists in AWS but applies to nothing — same "provisioned, not
  attached" pattern as `aws_security_group.app_firewall`. A NACL applies
  to every resource in a subnet, not just this app, so attaching it is
  left deliberate rather than automatic: set `app_subnet_ids` to the EC2
  instance's actual subnet and re-apply once reviewed.

## 2. Stateful Inspection Firewall

Tracks connection state so return traffic for an already-permitted
connection is allowed automatically, without a separate matching rule.

- **What exists**: AWS Security Groups are inherently stateful — this
  *is* the project's stateful firewall, for both tiers:
  - `aws_security_group.app_firewall` — the EC2 instance
    (`terraform/main.tf:88-170`)
  - `aws_security_group.rds` — the database, scoped to accept `5432`
    only from the app's own security group, not a CIDR
    (`terraform/main.tf:36-59`)
- Fully implemented. No gap here.

## 3. Proxy Firewall

Sits between client and server, terminates the connection itself, and
inspects/re-originates traffic rather than passing packets through.

- **What exists**: nginx (`nginx/nginx.conf.template`) is a full reverse
  proxy in front of gunicorn — no client ever reaches the app directly.
  It terminates TLS, and enforces traffic shaping before a request ever
  reaches Flask:
  - `limit_req_zone` — 5 requests/min on login endpoints, 20 requests/sec
    general (`nginx.conf.template:16-17`)
  - `limit_conn_zone` — 20 concurrent connections per IP
    (`nginx.conf.template:18,63`)
  - Strips/sets headers, serves `/static/` directly with its own security
    headers (`nginx.conf.template:77-96`)
- **Nuance**: this is a *reverse* proxy — it protects the app from
  inbound clients. There is no *forward* proxy (outbound/egress
  filtering), because this app has no outbound-to-arbitrary-internet
  requirement that would call for one.

## 4. Next-Generation Firewall (NGFW)

Combines deep packet inspection, intrusion prevention, and
application-awareness into one appliance — AWS's actual product for this
is **AWS Network Firewall** (Suricata-compatible IDS/IPS rules).

- **What exists**: `aws_networkfirewall_firewall`, its rule group, and its
  policy (`terraform/network_firewall.tf`) — a starter Suricata ruleset
  (blocks FTP/Telnet, alerts on suspiciously long URIs) evaluated in
  `STRICT_ORDER` with an `aws:alert_strict` default (monitor, not block,
  until the ruleset has been watched in CloudWatch and proven not to flag
  legitimate traffic). Complements, rather than replaces, three
  application-layer tools already covering their own slice:
  - `aws_wafv2_web_acl.app`'s managed rule groups — HTTP-layer signatures (§5)
  - ClamAV (`compose.yaml` `clamav` service) — content inspection on uploads
  - Flask-Limiter (`extensions.py`) — per-route rate/anomaly control
- **Gap**: the firewall/policy/rule-group resources only actually exist in
  AWS once `var.firewall_subnet_ids` is set to real, dedicated subnet
  IDs (`count = length(var.firewall_subnet_ids) > 0 ? 1 : 0` — currently
  `[]`, so nothing is provisioned). Even once set, **no traffic passes
  through it** until the VPC's route tables are edited to send app-subnet
  traffic via the firewall subnet and back — Network Firewall only
  inspects what a route table explicitly routes to its endpoint, and this
  Terraform config has never managed route tables (this project's
  VPC/subnets are pre-existing, externally-managed infrastructure). Real
  ongoing cost starts the moment the firewall itself is created:
  ~$0.395/hr (~$285/month) + $0.065/GB processed, independent of the
  route-table wiring being finished — flagging this as a cost decision to
  make deliberately, not a mechanical `terraform apply`.

## 5. Web Application Firewall (WAF)

Layer 7 filtering purpose-built for HTTP: SQLi, XSS, bad-input
signatures, rate limiting per client.

- **What exists**: `aws_wafv2_web_acl.app`
  (`terraform/security_hardening.tf:157-255`) with:
  - `AWSManagedRulesCommonRuleSet` (OWASP Top 10 generic protections)
  - `AWSManagedRulesSQLiRuleSet`
  - `AWSManagedRulesKnownBadInputsRuleSet`
  - `RateLimitPerIP` — blocks a single IP past 2000 requests/5 minutes
- **Important caveat**: WAFv2 can only attach to CloudFront, an ALB, or
  API Gateway — never directly to an EC2 instance. This Web ACL is
  provisioned in AWS but **is not in the traffic path today**. It only
  starts protecting real requests once `aws_cloudfront_distribution.app`
  is created (gated behind `var.app_origin_domain`,
  `terraform/security_hardening.tf:263-315`) and DNS is cut over from the
  EC2 instance's IP to the CloudFront domain. Until that cutover happens,
  this WAF exists as infrastructure but sees zero live traffic — treat
  "WAF deployed" and "WAF protecting the site" as two different
  milestones.
- **Complementary, already active regardless of the WAF/CloudFront
  status**: Flask's own `after_request` hook in `app.py` (CSP nonces,
  XSS-safe escaping via `_html.escape()`, CSRF tokens, security headers)
  functions as an application-level WAF and protects every request today,
  independent of the AWS-layer WAF above it.

---

## Summary of genuine gaps

1. **Network ACL provisioned but not attached** — set `var.app_subnet_ids`
   and re-apply to actually put it in the traffic path; until then the
   Security Group is still doing 100% of the real filtering.
2. **NGFW resource-complete but not provisioned or wired into the traffic
   path** — set `var.firewall_subnet_ids` to provision it (real ongoing
   cost starts immediately), then separately edit the VPC's route tables
   to actually send traffic through it; neither step happens automatically.
3. **WAF is provisioned but inactive** — requires the CloudFront +
   DNS cutover described in `terraform/security_hardening.tf` and
   `AWS_DEPLOYMENT.md` before it protects live traffic.

None of these are silently claimed as "done" elsewhere in the project's
docs — this file exists so the five-category checklist has one place with
an honest, file-referenced answer for each.
