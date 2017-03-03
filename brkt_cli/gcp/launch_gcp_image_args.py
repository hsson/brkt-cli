import argparse


# VERY EXPERIMENTAL FEATURE
# It will not work for you
def setup_launch_gcp_image_args(parser, parsed_config):
    parser.add_argument(
        'image',
        metavar='ID',
        help='The image that will be launched',
    )
    parser.add_argument(
        '--instance-name',
        metavar='NAME',
        dest='instance_name',
        help='Name of the instance'
    )
    parser.add_argument(
        '--instance-type',
        help='Instance type',
        dest='instance_type',
        default='n1-standard-1'
    )
    zone_kwargs = {
        'help': 'GCP zone to operate in',
        'dest': 'zone',
        'default': parsed_config.get_option('gcp.zone'),
        'required': False,
    }
    if zone_kwargs['default'] is None:
        zone_kwargs['required'] = True
    parser.add_argument(
        '--zone',
        **zone_kwargs
    )
    parser.add_argument(
        '--no-delete-boot',
        help='Do not delete boot disk when instance is deleted',
        dest='delete_boot',
        default=True,
        action='store_false'
    )
    proj_kwargs = {
        'help': 'GCP project name',
        'dest': 'project',
        'default': parsed_config.get_option('gcp.project'),
        'required': False,
    }
    if proj_kwargs['default'] is None:
        proj_kwargs['required'] = True
    parser.add_argument(
        '--project',
        **proj_kwargs
    )
    parser.add_argument(
        '--network',
        dest='network',
        default=parsed_config.get_option('gcp.network', 'default'),
        required=False
    )
    parser.add_argument(
        '--gcp-tag',
        dest='gcp_tags',
        action='append',
        metavar='VALUE',
        help=(
              'Set a GCP tag on the encrypted instance being launched. May be '
              'specified multiple times.'
        )
    )

    # Optional startup script. Hidden because it is only used for development
    # and testing. It should be passed as a string containing a multi-line
    # script (bash, python etc.)
    parser.add_argument(
        '--startup-script',
        help=argparse.SUPPRESS,
        dest='startup_script',
        metavar='SCRIPT'
    )
    parser.add_argument(
        '--subnetwork',
        metavar='NAME',
        help='Launch instance in this subnetwork',
        dest='subnetwork',
        default=parsed_config.get_option('gcp.subnetwork', None),
        required=False
    )
    parser.add_argument(
        '--guest-fqdn',
        metavar='FQDN',
        dest='guest_fqdn',
        help=argparse.SUPPRESS
    )
    # Optional (number of) SSD scratch disks because these can only be attached
    # at instance launch time, compared to the other (persistent) disks
    parser.add_argument(
        '--ssd-scratch-disks',
        metavar='N',
        type=int,
        default=0,
        dest='ssd_scratch_disks',
        help='Number of SSD scratch disks to be attached (max. 8)'
    )
