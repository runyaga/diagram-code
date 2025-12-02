# AWS Production VPC Architecture

Multi-AZ production infrastructure with public/private subnet tiers, auto scaling web servers, and Aurora databases.

## Description

A highly available AWS architecture spanning two availability zones with three-tier subnet design (public, application, database), auto-scaling EC2 instances, NAT gateways, and Amazon Aurora for data persistence. Includes security controls via WAF, Network ACLs, and IAM.

## Components

### Network Entry
- **alb**: Application Load Balancer | alb | Main entry point distributing traffic across AZs

### Availability Zone 1 - Public Subnet
- **nat_gw_1**: NAT gateway | vpc | NAT gateway for AZ1 private subnet internet access
- **ec2_web_pub_1**: EC2 instances (Web) | ec2 | Web tier instances in public subnet AZ1
- **nacl_pub_1**: Network ACL | waf | Network ACL for public subnet AZ1

### Availability Zone 1 - Private Subnet (Application)
- **ec2_web_priv_1**: EC2 instances (Web) | ec2 | Application tier instances in private subnet AZ1
- **nacl_app_1**: Network ACL | waf | Network ACL for application subnet AZ1

### Availability Zone 1 - Private Subnet (DB)
- **aurora_1**: Amazon Aurora | aurora | Aurora database instance AZ1
- **nacl_db_1**: Network ACL | waf | Network ACL for database subnet AZ1

### Availability Zone 2 - Public Subnet
- **nat_gw_2**: NAT gateway | vpc | NAT gateway for AZ2 private subnet internet access
- **ec2_web_pub_2**: EC2 instances (Web) | ec2 | Web tier instances in public subnet AZ2
- **nacl_pub_2**: Network ACL | waf | Network ACL for public subnet AZ2

### Availability Zone 2 - Private Subnet (Application)
- **ec2_web_priv_2**: EC2 instances (Web) | ec2 | Application tier instances in private subnet AZ2
- **nacl_app_2**: Network ACL | waf | Network ACL for application subnet AZ2

### Availability Zone 2 - Private Subnet (DB)
- **aurora_2**: Amazon Aurora | aurora | Aurora database instance AZ2
- **nacl_db_2**: Network ACL | waf | Network ACL for database subnet AZ2

### External Services (Right Side)
- **waf**: AWS WAF | waf | Web Application Firewall for security
- **s3_bucket**: Amazon S3 Bucket | s3 | Object storage
- **elasticsearch**: Amazon ES | elasticache | Elasticsearch service for search/analytics
- **iam**: AWS Identity and Access Management | generic_compute | IAM service
- **iam_roles**: IAM roles and permissions | generic_compute | IAM roles configuration

### External Services (Left Side)
- **peering**: Peering | vpc | VPC Peering connection
- **route_tables**: Route tables | generic_compute | Route tables (172.16.0.0, 172.16.1.0, 172.16.2.0)

## Connections

### Load Balancer to Web Tier
- alb -> ec2_web_pub_1 | HTTPS/443 | Traffic to AZ1 web instances
- alb -> ec2_web_pub_2 | HTTPS/443 | Traffic to AZ2 web instances

### Auto Scaling Group Connections (Public Tier)
- ec2_web_pub_1 -> ec2_web_pub_2 | Auto Scaling | Cross-AZ auto scaling group

### Web to Application Tier
- ec2_web_pub_1 -> ec2_web_priv_1 | Internal | AZ1 web to app tier
- ec2_web_pub_2 -> ec2_web_priv_2 | Internal | AZ2 web to app tier

### Auto Scaling Group Connections (Application Tier)
- ec2_web_priv_1 -> ec2_web_priv_2 | Auto Scaling | Cross-AZ auto scaling group

### Application to Database Tier
- ec2_web_priv_1 -> aurora_1 | TCP/3306 | AZ1 app to database
- ec2_web_priv_2 -> aurora_2 | TCP/3306 | AZ2 app to database

### NAT Gateway Connections
- ec2_web_priv_1 -> nat_gw_1 | Internet | Outbound internet via NAT AZ1
- ec2_web_priv_2 -> nat_gw_2 | Internet | Outbound internet via NAT AZ2

### Security Services
- waf -> alb | Security | WAF protection for ALB
- peering -> alb | VPC Peering | Peering connection to VPC

### Route Table Connections
- route_tables -> peering | Routing | Route table to peering

## Clusters

### Production VPC
- **production_vpc**: Production VPC | alb, nat_gw_1, ec2_web_pub_1, nacl_pub_1, ec2_web_priv_1, nacl_app_1, aurora_1, nacl_db_1, nat_gw_2, ec2_web_pub_2, nacl_pub_2, ec2_web_priv_2, nacl_app_2, aurora_2, nacl_db_2

### Availability Zone 1
- **az1**: Availability Zone 1 | nat_gw_1, ec2_web_pub_1, nacl_pub_1, ec2_web_priv_1, nacl_app_1, aurora_1, nacl_db_1
- parent: production_vpc

### Availability Zone 2
- **az2**: Availability Zone 2 | nat_gw_2, ec2_web_pub_2, nacl_pub_2, ec2_web_priv_2, nacl_app_2, aurora_2, nacl_db_2
- parent: production_vpc

### Public Subnet AZ1
- **public_subnet_1**: Public subnet | nat_gw_1, ec2_web_pub_1, nacl_pub_1
- parent: az1

### Private Subnet Application AZ1
- **private_subnet_app_1**: Private subnet (Application) | ec2_web_priv_1, nacl_app_1
- parent: az1

### Private Subnet DB AZ1
- **private_subnet_db_1**: Private subnet (DB) | aurora_1, nacl_db_1
- parent: az1

### Public Subnet AZ2
- **public_subnet_2**: Public subnet | nat_gw_2, ec2_web_pub_2, nacl_pub_2
- parent: az2

### Private Subnet Application AZ2
- **private_subnet_app_2**: Private subnet (Application) | ec2_web_priv_2, nacl_app_2
- parent: az2

### Private Subnet DB AZ2
- **private_subnet_db_2**: Private subnet (DB) | aurora_2, nacl_db_2
- parent: az2

### Auto Scaling Group - Web Tier
- **asg_web**: Auto Scaling Group | ec2_web_pub_1, ec2_web_pub_2
- parent: production_vpc

### Auto Scaling Group - App Tier
- **asg_app**: Auto Scaling Group | ec2_web_priv_1, ec2_web_priv_2
- parent: production_vpc

### External AWS Services
- **external_aws**: AWS Services | waf, s3_bucket, elasticsearch, iam, iam_roles

### Network Services
- **network_services**: Network Services | peering, route_tables

## Expected Results

### Node Count
- Total: 22 nodes
- Network Entry: 1 (alb)
- AZ1 Components: 7 (nat_gw_1, ec2_web_pub_1, nacl_pub_1, ec2_web_priv_1, nacl_app_1, aurora_1, nacl_db_1)
- AZ2 Components: 7 (nat_gw_2, ec2_web_pub_2, nacl_pub_2, ec2_web_priv_2, nacl_app_2, aurora_2, nacl_db_2)
- External Services: 7 (waf, s3_bucket, elasticsearch, iam, iam_roles, peering, route_tables)

### Edge Count
- Total: 13 connections

### Cluster Count
- Total: 13 clusters (with nested hierarchy)
