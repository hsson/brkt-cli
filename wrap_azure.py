# Copyright 2017 Bracket Computing, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License").
# You may not use this file except in compliance with the License.
# A copy of the License is located at
#
# https://github.com/brkt/brkt-cli/blob/master/LICENSE
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and
# limitations under the License.

"""
Create an Bracket wrapped based on an existing unencrypted AMI.

Overview of the process:
    * Obtain the Bracket (metavisor) image to be used
    * Obtain the root volume snapshot of the guest image
    * When lacking "create volume" permissions on the guest image
        create a local snapshot of the guest image
    * Configure the Bracket image to be launched with the guest
        root volume attached at /dev/sdf
    * Pass appropriate user-data to the Bracket image to indicate
        that the guest volume is unencrypted
    * Launch the Bracket image

Before running brkt encrypt-ami, set the AWS_ACCESS_KEY_ID and
AWS_SECRET_ACCESS_KEY environment variables, like you would when
running the AWS command line utility.
"""

# code taken from https://azure-sdk-for-python.readthedocs.io/en/v2.0.0rc6/resourcemanagementcomputenetwork.html
from brkt_cli.instance_config_args import (
    instance_config_from_values,
    setup_instance_config_args
)
from azure.common.credentials import ServicePrincipalCredentials
from brkt_cli import instance_config_args
import azure.mgmt.compute
import azure.mgmt.compute.models
import azure.mgmt.network
import azure.mgmt.network.models
import azure.mgmt.resource
import azure.mgmt.storage
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
from azure.mgmt.resource.resources import ResourceManagementClient
from azure.mgmt.storage import StorageManagementClient
import time
from brkt_cli.instance_config import InstanceConfig
from brkt_cli.user_data import gzip_user_data
import base64
import subprocess
import argparse
import brkt_cli
import os

config = None

#from azure.common.credentials import UserPassCredentials

# TODO: Replace this with your subscription id
subscription_id = 'aee38975-fbc5-47b8-8935-7f5dfcbb411a'
# TODO: See above how to get a Credentials instance
#credentials = ...
# credentials = UserPassCredentials(
#     '',  # Your new user
#     '',  # Your password
# )

ap = argparse.ArgumentParser(description="Azure MV Launcher")
ap.add_argument('--name', metavar='name', type=str, nargs='+',
                help='Name of the VM')
ap.add_argument('--service_domain', metavar='service_domain', type=str, nargs='+',
                help='Name of the service_domain')
ap.add_argument('--brkt_env', metavar='brkt_env', type=str, nargs='+',
                help='Name of the brkt_env')
ap.add_argument('--token', metavar='token', type=str, nargs='+',
                help='Name of the token')
ap.add_argument('--ntp_servers', metavar='ntp_servers', type=str, nargs='+',
                help='Name of the ntp_servers')
ap.add_argument('--proxy_config_file', metavar='proxy_config_file', type=str, nargs='+',
                help='Name of the proxy_config_file')
ap.add_argument('--proxies', metavar='proxies', type=str, nargs='+',
                help='Name of the proxies')


values = ap.parse_args()

c_id = os.environ['CLIENT_ID']
if c_id == None:
    raise Exception('CLIENT_ID must be set as an env variable:'
    'https://docs.microsoft.com/en-us/azure/azure-resource-manager/resource-group-create-service-principal-portal')

secret = os.environ['SECRET']
if c_id == None:
    raise Exception('SECRET must be set as an env variable:'
    'https://docs.microsoft.com/en-us/azure/azure-resource-manager/resource-group-create-service-principal-portal')

tenant = os.environ['TENANT']
if c_id == None:
    raise Exception('TENANT must be set as an env variable:'
    'https://docs.microsoft.com/en-us/azure/azure-resource-manager/resource-group-create-service-principal-portal')

credentials = ServicePrincipalCredentials(
    client_id = c_id,
    secret = secret,
    tenant = tenant
)

compute_client = ComputeManagementClient(
    credentials,
    subscription_id
)

network_client = NetworkManagementClient(
    credentials,
    subscription_id
)

#1

resource_client = ResourceManagementClient(
    credentials,
    subscription_id
)
resource_client.providers.register('Microsoft.Compute')
resource_client.providers.register('Microsoft.Network')

storage_client = StorageManagementClient(
    credentials,
    subscription_id
)

#2

# resource_client = azure.mgmt.resource.ResourceManagementClient(res_config)
# storage_client = azure.mgmt.storage.StorageManagementClient(storage_config)
# compute_client = azure.mgmt.compute.ComputeManagementClient(compute_config)
# network_client = azure.mgmt.network.NetworkManagementClient(network_config)
try:
    BASE_NAME = values.name[0]
except Exception:
    raise Exception('--name must be provided')

lt = values.token
if lt is None:
    lt = os.environ['BRKT_API_TOKEN']

GROUP_NAME = 'mark'
STORAGE_NAME = 'bracket2'
VIRTUAL_NETWORK_NAME = BASE_NAME
SUBNET_NAME = BASE_NAME
NETWORK_INTERFACE_NAME = BASE_NAME
VM_NAME = BASE_NAME
OS_DISK_NAME = BASE_NAME
PUBLIC_IP_NAME = BASE_NAME
COMPUTER_NAME = BASE_NAME
ADMIN_USERNAME='username'
ADMIN_PASSWORD='Password#26'
REGION = 'westus2'
# IMAGE_PUBLISHER = 'Canonical'
# IMAGE_OFFER = 'UbuntuServer'
# IMAGE_SKU = '16.04.0-LTS'
# IMAGE_VERSION = 'latest'


def create_network_interface(network_client, region, group_name, interface_name,
                             network_name, subnet_name, ip_name):

    result = network_client.virtual_networks.create_or_update(
        group_name,
        network_name,
        azure.mgmt.network.models.VirtualNetwork(
            location=region,
            address_space=azure.mgmt.network.models.AddressSpace(
                address_prefixes=[
                    '10.1.0.0/16',
                ],
            ),
            subnets=[
                azure.mgmt.network.models.Subnet(
                    name=subnet_name,
                    address_prefix='10.1.0.0/24',
                ),
            ],
        ),
    )

    subnet = network_client.subnets.get(group_name, network_name, subnet_name)

    result = network_client.public_ip_addresses.create_or_update(
        group_name,
        ip_name,
        azure.mgmt.network.models.PublicIPAddress(
            location=region,
            public_ip_allocation_method=azure.mgmt.network.models.IPAllocationMethod.dynamic,
            idle_timeout_in_minutes=4,
        ),
    )

    public_ip_address = network_client.public_ip_addresses.get(group_name, ip_name)
    public_ip_id = public_ip_address.id

    result = network_client.network_interfaces.create_or_update(
        group_name,
        interface_name,
        azure.mgmt.network.models.NetworkInterface(
            location=region,
            ip_configurations=[
                azure.mgmt.network.models.NetworkInterfaceIPConfiguration(
                    name='default',
                    private_ip_allocation_method=azure.mgmt.network.models.IPAllocationMethod.dynamic,
                    subnet=subnet,
                    public_ip_address=azure.mgmt.network.models.PublicIPAddress(
                        id=public_ip_id,
                    ),
                ),
            ],
        ),
    )

    network_interface = network_client.network_interfaces.get(
        group_name,
        interface_name,
    )

    return network_interface.id

#1. Create a resource group?
try:
    GROUP_NAME = values.group_name[0]
    resource_group(GROUP_NAME)
except Exception:
    pass

def resource_group():
    result = resource_client.resource_groups.create_or_update(
        GROUP_NAME,
        azure.mgmt.resource.models.ResourceGroup(
            location=REGION,
        ),
    )

#2. Create a storage account?
def storage_account():
    result = storage_client.storage_accounts.create(
        GROUP_NAME,
        STORAGE_NAME,
        azure.mgmt.storage.models.StorageAccountCreateParameters(
            location=REGION,
            account_type=azure.mgmt.storage.models.AccountType.standard_lrs,
        ),
    )
    result.wait() # async operation

# 3. Create the network interface using a helper function (defined below)
nic_id = create_network_interface(
    network_client,
    REGION,
    GROUP_NAME,
    NETWORK_INTERFACE_NAME,
    VIRTUAL_NETWORK_NAME,
    SUBNET_NAME,
    PUBLIC_IP_NAME,
)

INSTANCE_METAVISOR_MODE = 'metavisor'

values.service_domain = values.service_domain[0]
brkt_env = brkt_cli.brkt_env_from_values(values, config)

instance_config = instance_config_from_values(
   values,
   mode=INSTANCE_METAVISOR_MODE,
   brkt_env=brkt_env,
   launch_token=lt)

instance_config.brkt_config['allow_unencrypted_guest'] = True
userdata = instance_config.make_userdata()

# userdata = \
# '''From nobody Tue Dec  3 19:00:57 2013
# Content-Type: multipart/mixed; boundary="--===============HI-20131203==--"
# MIME-Version: 1.0

# ----===============HI-20131203==--
# Content-Type: text/brkt-config; charset="utf-8"
# MIME-Version: 1.0
# Content-Transfer-Encoding: 7bit

# {"brkt": {"allow_unencrypted_guest": true, "api_host": "yetiapi.stage.mgmt.brkt.com:443", "hsmproxy_host": "hsmproxy.stage.mgmt.brkt.com:443", "identity_token": "eyJhbGciOiJFUzM4NCIsImtpZCI6IjZiNGMyMzlmODk0YzE3NDdhNDA0NTRjODFiYjg2NjViZDllNWJjMTE0ODNiNDI2ZmRkM2QzYTA0Y2QwOGE5Y2MiLCJ0eXAiOiJKV1QifQ.eyJleHAiOjE1MDAxNjUxNzQsImlhdCI6MTQ5OTMwMTE3NCwiaXNzIjoic3RhZ2UubWdtdC5icmt0LmNvbSIsImp0aSI6IjE2ODgxNDQ3ODI2OTYwOTE3MDg2IiwiYXBwX21ldGFkYXRhIjp7ImN1c3RvbWVyIjoiMjZmNDVkN2QtMzE0Zi00YjE4LTg0Y2MtZjk3ZTdkYzE0NWMxIn0sImF6cCI6IjZiNGMyMzlmODk0YzE3NDdhNDA0NTRjODFiYjg2NjViZDllNWJjMTE0ODNiNDI2ZmRkM2QzYTA0Y2QwOGE5Y2MiLCJicmt0LnRva2VuX3R5cGUiOiJBUEkiLCJlbWFpbCI6Im12b2xsQGJya3QuY29tIiwiZW1haWxfdmVyaWZpZWQiOnRydWUsInVzZXJfaWQiOiJhdXRoMHw1OGJmNDJjMzc3MDc4ZjNlMWM1MTdhNmEifQ.9sspkXIOVAtEbZ1Bq0F1VojRnRttx0OLUiQEiuOEiY2KgKEJhP4NK8TRMEGESubd-ZHH0xEHmr9fgGvph-Kci-M8FMlhRMXdHbeYUYkbBuRkKJ9Ynyw0pgaoQQCQVWKa", "network_host": "network.stage.mgmt.brkt.com:443", "solo_mode": "metavisor"}}
# ----===============HI-20131203==----'''
encoded_userdata = base64.b64encode(userdata)
#KEY_DATA = "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC7RVXXe6D0gO6gXe/SiWARxy7G5A9kItgioIgiS9mNvGTcG9tei1qNzBy6apERIADCXXqKTaAcb7k7W1N7mS5k4d+78laaXXOTp8xBoqHhNHDcP8cJ8vWW5OwH60EasQbu1Jof/p1+MAdE6NF2x1bHTfdXQq6tsZpdqOoT4p1VtApLJJUkxHid/Z1LSFx43YFiUlpT1BY0BlvFSZTKFnn8n3OyvIvyNk/zCfMiUb5xgWrmpDoLUeZibRBwrf81gMAlpLcwxg/mfK/pgtsHTpn5ZAAtZdsCGMjmT/ufg9opKY6+pkUHdny3A5MZmzVtfq6ZtJRWrvXY5S9KjdDQMTnl mark@marks-mbp.int.brkt.com"
# 4. Create the virtual machine
def launch(BASE_NAME, GROUP_NAME, STORAGE_NAME, VIRTUAL_NETWORK_NAME, SUBNET_NAME, NETWORK_INTERFACE_NAME,
           VM_NAME, OS_DISK_NAME, PUBLIC_IP_NAME, COMPUTER_NAME, ADMIN_USERNAME,
           ADMIN_PASSWORD, REGION, nic_id):
    compute_client.virtual_machines.create_or_update(
        GROUP_NAME,
        VM_NAME,
        azure.mgmt.compute.models.VirtualMachine(
            location=REGION,
            os_profile=azure.mgmt.compute.models.OSProfile(
                admin_username=ADMIN_USERNAME,
                admin_password=ADMIN_PASSWORD,
                computer_name=COMPUTER_NAME,
                custom_data=encoded_userdata,
                # linux_configuration=azure.mgmt.compute.models.LinuxConfiguration(
                #     disable_password_authentication='True',
                #     ssh=azure.mgmt.compute.models.SshConfiguration(
                #         public_keys=[
                #             azure.mgmt.compute.models.SshPublicKey(
                #                 path="/home/mark/.ssh/authorized_keys",
                #                 key_data=KEY_DATA)
                #             ],
                #     ),
                # ),
            ),
            hardware_profile=azure.mgmt.compute.models.HardwareProfile(
                vm_size="Standard_DS1_v2",
            ),
            network_profile=azure.mgmt.compute.models.NetworkProfile(
                network_interfaces=[
                    azure.mgmt.compute.models.NetworkInterfaceReference(
                        id=nic_id,
                    ),
                ],
            ),
            storage_profile=azure.mgmt.compute.models.StorageProfile(
                os_disk=azure.mgmt.compute.models.OSDisk(
                    caching='None',
                    create_option='fromImage',
                    name='root',
                    os_type="Linux",
                    vhd=azure.mgmt.compute.models.VirtualHardDisk(
                        uri='https://bracket2.blob.core.windows.net/container/{0}root.vhd'.format(BASE_NAME)
                    ),
                    image=azure.mgmt.compute.models.VirtualHardDisk(
                        uri='https://bracket2.blob.core.windows.net/container/disk.vhd'
                    ),
                ),
                data_disks=[
                    azure.mgmt.compute.models.DataDisk(
                        name='mvsource',
                        lun=0,
                        vhd=azure.mgmt.compute.models.VirtualHardDisk(
                            uri='https://bracket2.blob.core.windows.net/container/trusty.vhd'
                        ),
                        create_option='Attach'
                    ),
                    azure.mgmt.compute.models.DataDisk(
                        name='mvtarget',
                        disk_size_gb=61,
                        lun=1,
                        vhd=azure.mgmt.compute.models.VirtualHardDisk(
                            uri='https://{0}.blob.core.windows.net/container/{1}target.vhd'.format(
                                'bracket2',
                                BASE_NAME,
                            ),
                        ),
                        create_option='Empty'

                    )
                ]
            ),
            diagnostics_profile=azure.mgmt.compute.models.DiagnosticsProfile(
                boot_diagnostics=azure.mgmt.compute.models.BootDiagnostics( 
                    enabled=True,
                    storage_uri='https://markdiag302.blob.core.windows.net/',
                ),
            ),
        ),
    )
    #time.sleep(10)
    # Display the public ip address
    # You can now connect to the machine using SSH
    public_ip_address = network_client.public_ip_addresses.get(GROUP_NAME, PUBLIC_IP_NAME)
    print('VM available at {}'.format(public_ip_address.ip_address))

launch(BASE_NAME, GROUP_NAME, STORAGE_NAME, VIRTUAL_NETWORK_NAME, SUBNET_NAME, NETWORK_INTERFACE_NAME,
       VM_NAME, OS_DISK_NAME, PUBLIC_IP_NAME, COMPUTER_NAME, ADMIN_USERNAME,
       ADMIN_PASSWORD, REGION, nic_id)
