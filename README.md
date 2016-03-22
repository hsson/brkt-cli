**brkt-cli** is a command-line interface to the [Bracket Computing](http://www.brkt.com)
service.  It produces an encrypted version of an Amazon Machine Image, which can then be
launched in EC2. It can also update an already encrypted version of an Amazon Machine Image,
which can then be launched in EC2.

## Requirements

In order to use the Bracket service, you must be a
registered Bracket customer.  Email support@brkt.com for
more information.

**brkt-cli** has the following dependencies:
* Python 2.7
* [boto](https://github.com/boto/boto) 2.38.0+ (Python interface to AWS)
* [requests](http://www.python-requests.org/en/latest/) 2.7.0+ (Python HTTP library)

## Process

The `encrypt-ami` subcommand performs the following steps to create an
encrypted image:

1. Launch an instance based on the specified unencrypted AMI.  We call this
the guest instance.
1. Snapshot the root volume of the guest instance.
1. Launch a Bracket Encryptor instance.
1. Attach the unencrypted guest root volume to the Bracket encryptor instance.
1. Copy the unencrypted root volume to a new, encrypted volume.
1. Create a new AMI based on the encrypted root volume and other volumes
required by the metavisor at runtime.

The `update-encrypted-ami` subcommand updates an encrypted AMI with the latest
version of the metavisor code.

## Networking requirements

The following network connections are established during image encryption:

* **brkt-cli** talks to the Encryptor instance on port 8000.
* The Encryptor talks to the Bracket service at `yetiapi.mgmt.brkt.com`.  In
order to do this, port 443 must be accessible on the following hosts:
  * 52.32.38.106
  * 52.35.101.76
  * 52.88.55.6
* Both **brkt-cli** and the Encryptor also need to access Amazon S3.

When launching the Encryptor instance, **brkt-cli** creates a temporary
security group that allows inbound access on port 8000.  Alternately, you can
use the `--security-group` option to specify one or more existing security
groups.

## Installation

The latest release of **brkt-cli** is 0.9.12.  Use pip to install **brkt-cli** and its dependencies:

```
$ pip install brkt-cli
```

To install the most recent **brkt-cli** code from the tip of the master branch, run

```
$ pip install git+https://github.com/brkt/brkt-cli.git
```

The master branch has the latest features and bug fixes, but is not as thoroughly tested as the official release.

## Usage
```
$ brkt encrypt-ami --help
usage: brkt encrypt-ami [-h] [--encrypted-ami-name NAME] [--no-validate]
                        --region NAME [--security-group ID] [--subnet ID]
                        ID

Create an encrypted AMI from an existing AMI.

positional arguments:
  ID                    The AMI that will be encrypted

optional arguments:
  -h, --help            show this help message and exit
  --encrypted-ami-name NAME
                        Specify the name of the generated encrypted AMI
  --hvm                 Use the HVM encryptor (beta)
  --no-validate         Don't validate AMIs, subnet, and security groups
  --proxy HOST:PORT     Use this HTTPS proxy during encryption. May be
                        specified multiple times.
  --region NAME         AWS region (e.g. us-west-2)
  --security-group ID   Use this security group when running the encryptor
                        instance. May be specified multiple times.
  --subnet ID           Launch instances in this subnet
  --tag KEY=VALUE       Custom tag for resources created during encryption.
                        May be specified multiple times.
```
```
$ brkt update-encrypted-ami --help
usage: brkt update-encrypted-ami [-h] [--encrypted-ami-name NAME]
                                 [--no-validate] --region REGION
                                 [--security-group ID] [--subnet ID]
                                 ID

Update an encrypted AMI with the latest Metavisor release.

positional arguments:
  ID                    The AMI that will be encrypted

optional arguments:
  -h, --help            show this help message and exit
  --encrypted-ami-name NAME
                        Specify the name of the generated encrypted AMI
  --hvm                 Use the HVM encryptor (beta)
  --no-validate         Don't validate AMIs, subnet, and security groups
  --region REGION       AWS region (e.g. us-west-2)
  --security-group ID   Use this security group when running the encryptor
                        instance. May be specified multiple times.
  --subnet ID           Launch instances in this subnet
  --tag KEY=VALUE       Custom tag for resources created during encryption.
                        May be specified multiple times.
```

## Configuration

Before running the **brkt** command, make sure that you've set the AWS
environment variables:

```
$ export AWS_ACCESS_KEY_ID=<access key>
$ export AWS_SECRET_ACCESS_KEY=<secret key>
```

You'll also need to make sure that your AWS account has the required
permissions, such as running an instance, describing an image, and
creating snapshots.  See [brkt-cli-iam-permissions.json](https://github.com/brkt/brkt-cli/blob/master/reference_templates/brkt-cli-iam-permissions.json)
for the complete list of required permissions.

## Encrypting an AMI

Run **brkt encrypt-ami** to create a new encrypted AMI based on an existing
image:

```
$ brkt encrypt-ami --region us-east-1 ami-76e27e1e
15:28:37 Starting encryptor session caabe51a
15:28:38 Launching instance i-703f4c99 to snapshot root disk for ami-76e27e1e
...
15:57:11 Created encrypted AMI ami-07c2a262 based on ami-76e27e1e
15:57:11 Terminating encryptor instance i-753e4d9c
15:57:12 Deleting snapshot copy of original root volume snap-847da3e1
15:57:12 Done.
ami-07c2a262
```

When the process completes, the new AMI id is written to stdout.  All log
messages are written to stderr.

## Updating an encrypted AMI

Run **brkt update-encrypted-ami** to update an encrypted AMI based on an existing
encrypted image:

```
$ brkt update-encrypted-ami --region us-east-1 --updater-ami ami-32430158 ami-72094e18
13:38:14 Using zone us-east-1a
13:38:15 Updating ami-72094e18
13:38:15 Creating guest volume snapshot
...
13:39:25 Encrypted root drive created.
...
13:39:28 waiting for snapshot ready
13:39:48 metavisor updater snapshots ready
...
13:39:54 Created encrypted AMI ami-63733e09 based on ami-72094e18
13:39:54 Done.
ami-63733e09
```

When the process completes, the new AMI id is written to stdout.  All log
messages are written to stderr.
