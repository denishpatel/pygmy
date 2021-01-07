terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 2.70"
    }
  }
}

provider "aws" {
  profile = "default"
  region  = "us-east-1"
}

data "aws_ami" "ubuntu" {
  most_recent = true

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-focal-20.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  owners = ["099720109477"] # Canonical
}

resource "aws_key_pair" "denishpatel" {
  key_name   = "denishpatel-key"
  public_key = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQC0swQoM2DFQwXrti9jQkIWRdCpmWx3U0YfTBx9ieMH92iDjg1bPWhmOWVS3dtU2K78dg4060m5xBdxmh0HvEUC31dHZYyUn87JuMcCLMywF+NcSN5f+JQgIJBSyG4FcnlrKd29XaOSS0MLnlxhag9qNnuMQoHYq+/k2y6VwcB1QpBlViEvpMISJBDzGQtzWoCcNAJv1YYQLRhxK3BE1A+skmiHlzgP6jYxvj8wxUVL29D9e5LxNVVLyxb4EVgtgktNxfAgdXrJ7DEM2CXu8JpiB37aOqI/M7CbxEPB5NCOzB09e3O8JSH8xS3mFNIi2/leCNDhuaMUz9am7vdNFqRugi4zbaoz+voA15irazv9v9cHbMkXvJdweDGrckbq5dwysELjNltxi/P/P6GEb+L+AH7QRbdCuKNR9qoN44J3dxfxQSTblFFAyMyiGjwS0Q8WSFZnuzF51Ta+geveM1H2R21pxdUk02zwTTwuyPA8mClxkHcC5Te9/AayePQGuu16X+drk8FMSAbTAInbTqaY/x9NfThsTU80KDt5As2mrY2WsW3m0xNCdjq6N/UE7VVLUeI07Z4Xbg7NaEW7t3ATp1XZnGpQwL4gYV4WV6Df6LAvhvgy+mTiJ8tzd/16yRgWh4xwygQw9u11+z1m+v6LNGPxjrsXEO36sBu9qJfcxQ== /Users/denishpatel/.ssh/id_rsa"
}

resource "aws_instance" "pg-primary" {
  ami           = data.aws_ami.ubuntu.id 
  instance_type = "t2.micro"
  key_name = "denishpatel-key"
  tags = {
    Name = "pg-primary"
  }
}

resource "aws_instance" "pg-secondary-1" {
  ami           = data.aws_ami.ubuntu.id
  instance_type = "t2.micro"
  key_name = "denishpatel-key"
  tags = {
    Name = "pg-secondary"
  }
}
