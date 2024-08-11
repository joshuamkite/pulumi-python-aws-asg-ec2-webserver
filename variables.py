# AWS configuration
aws_region = "eu-west-2"

# EC2 Configuration
instance_type = "t2.micro"

ec2_config = {
    "min_size": 1,
    "max_size": 3,
    "desired_capacity": 1
}

default_tags = {
    "project": "pulumi-aws-ec2-asg",
    "owner": "Joshua",
    "Name": "pulumi-aws-ec2-asg"
}

create_dns_record=True
dns_name = "ec2-asg.pulumi.joshuakite.co.uk" # Has to exist and be valid but won't really be used unless `create_dns_record`` is set to True

