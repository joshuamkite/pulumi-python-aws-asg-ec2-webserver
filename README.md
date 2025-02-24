# Pulumi AWS ASG

This project uses Pulumi (Python) to deploy and manage AWS infrastructure, including an Auto Scaling Group (ASG) of EC2 instances, an Application Load Balancer (ALB), and (optionally) DNS configuration using Route 53. The stack is designed to operate within an existing AWS VPC and utilizes specific subnets and security groups to control traffic. The infrastructure is configured to automatically scale EC2 instances and distribute traffic using the ALB, with optional DNS records managed via Route 53.

I have also translated this stack:
- [TypeScript version](https://github.com/joshuamkite/pulumi-typescript-aws-asg-ec2-webserver)
- [C# version](https://github.com/joshuamkite/pulumi-csharp-aws-asg-ec2-webserver)

# Contents

- [Pulumi AWS ASG](#pulumi-aws-asg)
- [Contents](#contents)
  - [Stack Overview](#stack-overview)
    - [Features and Purpose](#features-and-purpose)
  - [Initial Setup](#initial-setup)
    - [Completed Initializations](#completed-initializations)
    - [Prerequisites](#prerequisites)
    - [Setup Instructions](#setup-instructions)
  - [Managing the Infrastructure](#managing-the-infrastructure)
    - [Previewing Changes](#previewing-changes)
    - [Deploying the Infrastructure](#deploying-the-infrastructure)
    - [Destroying the Infrastructure](#destroying-the-infrastructure)
  - [Additional Resources](#additional-resources)

## Stack Overview

### Features and Purpose

**Conditional resources**: HTTPS and Pre-defined DNS name associated resources are conditionally created if variable `create_dns_record=True`. If not then plain HTTP is used without those resources and with alternatives

- **VPC and Subnet Integration**: Utilizes an existing (default in my case!) VPC and associated subnets.
- **Security Groups**: Configures separate security groups for load balancer and for EC2 instances.
- **Instance Profile**: Assigns roles to EC2 instances to allow secure access to AWS services, specifically for using the Systems Manager (SSM).
- **VPC Endpoints**: Creates VPC endpoints for SSM and EC2 messages, enabling secure and private communication between AWS services and EC2 instances.
- **Auto Scaling Group (ASG)**: Automatically manages the number of EC2 instances. In our case these are running Apache with a simple 'Hello World' installed in user data
- **Load Balancer (ALB)**: Distributes incoming traffic across multiple EC2 instances and provides HTTPS termination with automatic redirection from HTTP if DNS Domain used, otherwise plain HTTP.
- **DNS Configuration**: Optionally uses Route 53 to manage DNS records for the deployed load balancer, allowing easy access to the deployed application.
- **TLS Certificate**:  If DNS Domain used, automatically requests and validates a TLS certificate using ACM for secure HTTPS communication.

**N.B.**

Instances are provisioned with a public IP to avoid use of a NAT gateway for installation of external packages. Not recommended for production use!

## Initial Setup

### Completed Initializations

1. **Project Initialization**:
   The project was initialized using Pulumi's `aws-python` template:
   ```bash
   pulumi new aws-python
   ```
   This set up the basic Pulumi project structure, including stack configuration and Pulumi's state management.

### Prerequisites

Before proceeding with any deployment or management actions, ensure the following tools are installed and configured:

- **Pulumi**
- **AWS CLI** 
- **Python**
  
### Setup Instructions

1. **Clone the Repository**

2. **Set Up Python Environment**:
   Create and activate a virtual environment, then install the required dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   pip install -r requirements.txt
   ```

3. **Configure Pulumi**:
   Login to Pulumi (either locally or via Pulumi's service):
   ```bash
   pulumi login --local  # Or use `pulumi login` for cloud service
   ```

4. **Stack Initialization**:

   Since the `Pulumi.dev.yaml` file is excluded from the repository due to containing sensitive information, you'll need to recreate it locally to configure your stack.

   If you haven't already set up the Pulumi stack, you'll need to initialize it:
   ```bash
   pulumi stack init dev
   ```
   Replace `dev` with your desired stack name if you're using a different environment.

5. **Configure Stack Settings**:
   You can set up the necessary configuration values for your stack using the `pulumi config set` command. These values will be stored in the `Pulumi.dev.yaml` file.

   For example, set the AWS region and any other required configuration variables:
   ```bash
   pulumi config set aws:region eu-west-2
   ```

6. **Verify the Configuration**:
   After setting up your configuration, you can verify it by checking the stack configuration:
   ```bash
   pulumi config
   ```
   This will list all the configurations you’ve set up for the current stack.

7. **Environment Variables**
   Although these aren't really secrets, rather than expose anything that might look like one several values are populated from environment variables:

   ```bash
   export VPC_ID=<Your existing VPC ID>
   export ROUTE53_ZONE_ID=<Your existing Route 53 Zone ID>
   export AWS_PROFILE=<Your AWS Profile>
   ```

## Managing the Infrastructure

### Previewing Changes

Before deploying, it's a good practice to preview the changes that will be made to your AWS environment:

1. **Preview**:
   ```bash
   pulumi preview
   ```
   This command shows a detailed plan of the proposed changes, including resources that will be created, updated, or destroyed.

### Deploying the Infrastructure

When you're ready to apply the changes and deploy the infrastructure:

1. **Deploy**:
   ```bash
   pulumi up
   ```
   Pulumi will show the proposed changes and ask for confirmation before proceeding. Type `yes` to confirm and deploy the resources.

2. **Accessing Deployed Resources**:
   After deployment, Pulumi will output key information, such as the DNS name of the Load Balancer. Use this or your preassigned DNS entry to access the deployed services.

### Destroying the Infrastructure

To remove all resources created by this Pulumi stack:

1. **Destroy**:
   ```bash
   pulumi destroy
   ```
   This command will tear down all infrastructure resources associated with the stack, ensuring a clean state.

2. **Optional Stack Removal**:
   If you no longer need the stack itself:
   ```bash
   pulumi stack rm <stack-name>
   ```

## Additional Resources

- **Pulumi Documentation**: For more detailed information, refer to the [Pulumi Documentation](https://www.pulumi.com/docs/).
- **AWS Provider Documentation**: Explore the [Pulumi AWS Provider Docs](https://www.pulumi.com/docs/intro/cloud-providers/aws/) for detailed configurations and examples.
