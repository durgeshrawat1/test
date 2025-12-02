| Phase | Task | Description | Estimated Effort |
|------|------|-------------|------------------|
| Pre-requisites | Access & Permissions | Confirm AWS, EKS, Route53, Artifactory, Entra ID access | 1–2 days |
| Pre-requisites | Network Validation | VPC routing, subnets, firewall rules, egress to Artifactory & Entra | 1 day |
| EKS Setup | VPC Creation | Subnets, NAT, routing tables | 0.5 day |
| EKS Setup | EKS Cluster Creation | Control plane + worker node groups | 1 day |
| EKS Setup | IAM Roles & OIDC | IRSA setup, roles for ALB, ExternalDNS, Secrets manager | 0.5 day |
| EKS Setup | Cluster Add-ons | ALB Ingress, ExternalDNS, Metrics server, FSx/EBS drivers | 1 day |
| Entra ID Integration | App Registration | Create app, redirect URI, logout endpoints | 0.5 day |
| Entra ID Integration | Permission Scopes | API permissions, admin consent | 0.5 day |
| Entra ID Integration | Group Mapping & Claims | Configure roles/groups | 1 day |
| Entra ID Integration | OIDC/OAuth Integration | Connect K8s app to Entra ID | 1 day |
| Artifactory Integration | Service Account | Robot/technical user creation | 0.5 day |
| Artifactory Integration | Pull Secret Setup | Docker registry secret & test pull | 0.5 day |
| Artifactory Integration | Image Access Validation | Validate all Nimbus Uno images | 1 day |
| Route53 & Ingress | Hosted Zone Setup | Create or reuse hosted zone | 0.5 day |
| Route53 & Ingress | DNS Records | A/AAAA/CNAME records | 0.5 day |
| Route53 & Ingress | Ingress Setup | ALB rules + target groups | 1 day |
| Route53 & Ingress | SSL Certificate | ACM issuance & validation | 1 day |
| Application Deployment | Namespace Creation | Isolate Solytics workloads | 0.25 day |
| Application Deployment | Helm/Manifest Config | Values overrides, secrets | 1 day |
| Application Deployment | Deployment & Rollout | Deploy services, pods | 1 day |
| Validation | Functional Testing | Login, workflows, dashboards | 1 day |
| Validation | Performance Testing | Resource usage, autoscaling tests | 1 day |
| Validation | Failover Testing | Pod restart, node failure tests | 0.5–1 day |
| Handover | Runbook | Access, backup, scaling docs | 1 day |
| Handover | Knowledge Transfer | Ops team walkthrough | 0.5 day |
