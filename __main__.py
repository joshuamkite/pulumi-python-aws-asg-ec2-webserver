import pulumi
import pulumi_aws as aws
import pulumi_aws_native as aws_native
import variables 
import os
import base64

# Configure the AWS provider to use the specified profile
provider = aws.Provider("aws", region=variables.aws_region)

# Define standard tags
standard_tags = variables.default_tags

# Use the existing VPC
vpc = aws.ec2.get_vpc(id=os.environ.get('VPC_ID'))

# Retrieve subnet IDs for the given VPC
subnets = aws.ec2.get_subnets(filters=[{
    'name': 'vpc-id',
    'values': [vpc.id]
}]).ids

# Retrieve the latest Amazon Linux 2023 AMI 
ami = aws.ec2.get_ami(most_recent=True,
    owners=["amazon"],
    filters=[{
            "name": "name", 
            "values": ["al2023-ami-*-kernel*x86_64*"]
            }]
            ) 

# Security Group in the existing VPC
security_group = aws.ec2.SecurityGroup("security-group",
    vpc_id=vpc.id,
    description="Allow HTTP; HTTPS",
    opts=pulumi.ResourceOptions(provider=provider),
    tags=standard_tags
    )

# Add HTTPS ingress rule to the security group
if variables.create_dns_record:
    aws.ec2.SecurityGroupRule("https-ingress",
        security_group_id=security_group.id,
        protocol="tcp",
        from_port=443,
        to_port=443,
        cidr_blocks=["0.0.0.0/0"],
        opts=pulumi.ResourceOptions(provider=provider),
        type="ingress"
        )

# Add HTTP ingress rule to the security group
if not variables.create_dns_record:
    aws.ec2.SecurityGroupRule("http-ingress",
        security_group_id=security_group.id,
        protocol="tcp",
        from_port=80,
        to_port=80,
        cidr_blocks=["0.0.0.0/0"],
        opts=pulumi.ResourceOptions(provider=provider),
        type="ingress"
        )

# Add egress rule to the security group
aws.ec2.SecurityGroupRule("egress",
    security_group_id=security_group.id,
    protocol="-1",
    from_port=0,
    to_port=0,
    cidr_blocks=["0.0.0.0/0"],
    opts=pulumi.ResourceOptions(provider=provider),
    type="egress"
    )


# Instance Security Group 
security_group_instance = aws.ec2.SecurityGroup("security-group_instance",
    vpc_id=vpc.id,
    description="Allow HTTP; HTTPS",
    opts=pulumi.ResourceOptions(provider=provider),
    tags=standard_tags
    )


# Add HTTP ingress rule to the security group
aws.ec2.SecurityGroupRule("http-ingress_instance",
    security_group_id=security_group_instance.id,
    protocol="tcp",
    from_port=80,
    to_port=80,
    source_security_group_id=security_group.id,
    opts=pulumi.ResourceOptions(provider=provider),
    type="ingress"
    )

# Add egress rule to the security group
aws.ec2.SecurityGroupRule("egress_instance",
    security_group_id=security_group_instance.id,
    protocol="-1",
    from_port=0,
    to_port=0,
    cidr_blocks=["0.0.0.0/0"],
    opts=pulumi.ResourceOptions(provider=provider),
    type="egress"
    )


# IAM Role for EC2 Instance
ec2_role = aws.iam.Role("ec2-role",
    assume_role_policy="""{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "ec2.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }""",
    opts=pulumi.ResourceOptions(provider=provider),
    tags=standard_tags
)


# Attach the AmazonSSMManagedInstanceCore managed policy to the role
aws.iam.RolePolicyAttachment("ssm-core-policy-attachment",
    role=ec2_role.name,
    policy_arn="arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore",
    opts=pulumi.ResourceOptions(provider=provider),
)


# VPC Endpoint for SSM
ssm_endpoint = aws.ec2.VpcEndpoint("ssm-endpoint",
    vpc_id=vpc.id,
    service_name=f"com.amazonaws.{variables.aws_region}.ssm",
    vpc_endpoint_type="Interface",
    security_group_ids=[security_group_instance.id],
    subnet_ids=subnets,
    # private_dns_enabled=True,
    opts=pulumi.ResourceOptions(provider=provider),
)


# VPC Endpoint for EC2 Messages
ec2_messages_endpoint = aws.ec2.VpcEndpoint("ec2-messages-endpoint",
    vpc_id=vpc.id,
    service_name=f"com.amazonaws.{variables.aws_region}.ec2messages",
    vpc_endpoint_type="Interface",
    security_group_ids=[security_group_instance.id],
    subnet_ids=subnets,
    # private_dns_enabled=True,
    opts=pulumi.ResourceOptions(provider=provider),
)


# VPC Endpoint for SSM Session Manager
ssm_messages_endpoint = aws.ec2.VpcEndpoint("ssm-messages-endpoint",
    vpc_id=vpc.id,
    service_name=f"com.amazonaws.{variables.aws_region}.ssmmessages",
    vpc_endpoint_type="Interface",
    subnet_ids=subnets,
    security_group_ids=[security_group_instance.id],
    # private_dns_enabled=True,
    opts=pulumi.ResourceOptions(provider=provider),
)


# Instance Profile for EC2 Instance
instance_profile = aws.iam.InstanceProfile("instance-profile",
    role=ec2_role.name,
    opts=pulumi.ResourceOptions(provider=provider),
    tags=standard_tags
)


# Launch Configuration
user_data_script = """#!/bin/bash
dnf update -y
dnf install -y httpd
systemctl start httpd
systemctl enable httpd
echo "<h1>Hello World from $(hostname -f)</h1>" > /var/www/html/index.html
"""

encoded_user_data = base64.b64encode(user_data_script.encode('utf-8')).decode('utf-8')

launch_template = aws.ec2.LaunchTemplate("launch-template",
    image_id=ami.id,
    instance_type=variables.instance_type,
    user_data=encoded_user_data,
    opts=pulumi.ResourceOptions(provider=provider),
    iam_instance_profile={
        "name": instance_profile.name
    },
    network_interfaces=[{
        "deviceIndex": 0,
        "associatePublicIpAddress": True,
        "subnetId": subnets[0],
        "securityGroups": [security_group_instance.id]
    }],
)

# Convert standard_tags dictionary to a list of dictionaries with propagate_at_launch key
asg_tags = [{"key": k, "value": v, "propagate_at_launch": "True"} for k, v in standard_tags.items()]

# Auto Scaling Group
asg = aws.autoscaling.Group("asg",
    vpc_zone_identifiers=subnets,
    launch_template={
        "id": launch_template.id,
        "version": "$Latest"  
    },
    min_size=variables.ec2_config['min_size'],
    max_size=variables.ec2_config['max_size'],
    desired_capacity=variables.ec2_config['desired_capacity'],
    health_check_type="EC2",
    tags=asg_tags,
    opts=pulumi.ResourceOptions(provider=provider)
)


# Convert standard_tags dictionary to the required array format for load balancer tags
def convert_tags_dict_to_array(tags_dict):
    return [{"key": k, "value": v} for k, v in tags_dict.items()]

lb_tags = convert_tags_dict_to_array(standard_tags)


# Load Balancer
load_balancer = aws_native.elasticloadbalancingv2.LoadBalancer(
"load-balancer",
    subnets=subnets,
    security_groups=[security_group.id],
    opts=pulumi.ResourceOptions(provider=provider),
    type="application",
    tags=lb_tags
    )


# Target Group for EC2 instances
target_group = aws_native.elasticloadbalancingv2.TargetGroup("target-group",
    port=80,
    protocol="HTTP",
    vpc_id=vpc.id,
    opts=pulumi.ResourceOptions(provider=provider),
    tags=lb_tags
    )


# TLS Certificate
if variables.create_dns_record:
    certificate = aws.acm.Certificate("certificate",
        domain_name=variables.dns_name,
        validation_method="DNS",
        opts=pulumi.ResourceOptions(provider=provider),
        tags=standard_tags
        )


# Certificate Validation
if variables.create_dns_record:
    certificate_validation = aws.route53.Record("certificate-validation",
        name=certificate.domain_validation_options[0].resource_record_name,
        type=certificate.domain_validation_options[0].resource_record_type,
        zone_id=os.environ.get('ROUTE53_ZONE_ID'),
        records=[certificate.domain_validation_options[0].resource_record_value],
        ttl=60,
        opts=pulumi.ResourceOptions(provider=provider)
        )


# Certificate Validation DNS Record
if variables.create_dns_record:
    certificate_validation_dns_record = aws.acm.CertificateValidation("certificate-validation-dns-record",
        certificate_arn=certificate.arn,
        validation_record_fqdns=[
            certificate_validation.fqdn
        ],
        opts=pulumi.ResourceOptions(provider=provider)
        )


# HTTPS Listener with certificate
if variables.create_dns_record:
    listener = aws_native.elasticloadbalancingv2.Listener("https-listener",
        load_balancer_arn=load_balancer.load_balancer_arn,
        port=443,
        protocol="HTTPS",
        default_actions=[{
            "type": "forward",
            "target_group_arn": target_group.target_group_arn,
        }],
        certificates=[{
            "certificateArn": certificate.arn
        }],
        opts=pulumi.ResourceOptions(provider=provider),
    )

# HTTP Listener 
if not variables.create_dns_record:
    listener = aws_native.elasticloadbalancingv2.Listener("http-listener",
        load_balancer_arn=load_balancer.load_balancer_arn,
        port=80,
        protocol="HTTP",
        default_actions=[{
            "type": "forward",
            "target_group_arn": target_group.target_group_arn,
        }],
        opts=pulumi.ResourceOptions(provider=provider),
    )


# HTTP Listener with Redirection to HTTPS
if variables.create_dns_record:
    http_listener = aws_native.elasticloadbalancingv2.Listener("http-listener",
        load_balancer_arn=load_balancer.load_balancer_arn,
        port=80,
        protocol="HTTP",
        default_actions=[{
            "type": "redirect",
            "redirect_config": {
                "protocol": "HTTPS",
                "port": "443",
                "status_code": "HTTP_301",
            },
        }],
        opts=pulumi.ResourceOptions(provider=provider),
    )


# Attach the ASG to the Load Balancer
asg_attachment = aws.autoscaling.Attachment("asg-attachment",
    autoscaling_group_name=asg.name,
    lb_target_group_arn=target_group.target_group_arn,
    opts=pulumi.ResourceOptions(provider=provider),
)


# Export the Load Balancer DNS name
pulumi.export("loadBalancerDns", load_balancer.dns_name)

# DNS Record
if variables.create_dns_record:
    dns_record = aws.route53.Record("dns-record",
        name=variables.dns_name,
        type="A",
        zone_id=os.environ.get('ROUTE53_ZONE_ID'),
        aliases=[{
            "name": load_balancer.dns_name,
            "zoneId": load_balancer.canonical_hosted_zone_id,
            "evaluateTargetHealth": True,
        }],
        opts=pulumi.ResourceOptions(provider=provider),
    )

# Export the DNS Record
if variables.create_dns_record:
    pulumi.export("dnsRecord", dns_record.fqdn)