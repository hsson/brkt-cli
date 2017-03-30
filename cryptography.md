Some of the advanced **brkt-cli** commands that perform encryption require
the Python [cryptography](https://cryptography.io/) library:

* `make-key`: create a private key PEM that conforms to Bracket
Computing's security requirements
* `get-public-key`: print the public key that is associated with a
private key
* `make-token`: create a launch token for Metavisor.  Cryptography is
only required when generating a launch token based on a private key
in the local filesystem.

The default behavior of **brkt-cli** is to manage keys and launch
tokens behind the scenes.  Users who need to manage their own keys
and tokens will need to install the cryptography library manually.

#### Windows and OS X

Windows and OS X users need to use [pip 8](https://pip.pypa.io/) or
later.  pip 8 supports Python Wheels, which include the binary portion
of the [cryptography](https://cryptography.io/) library.  To
[upgrade pip](https://pip.pypa.io/en/stable/installing/#upgrading-pip)
to the latest version, run

```
$ pip install --upgrade pip
```

#### Linux

Linux users need to install several packages, which allow you to compile
the cryptography library.  Ubuntu users need to run

```
$ sudo apt-get install build-essential libssl-dev libffi-dev python-dev
```

before installing **brkt-cli**.  RHEL and CentOS users need to run

```
$ sudo yum install gcc libffi-devel python-devel openssl-devel
```

For more details, see the
[installation section](https://cryptography.io/en/latest/installation/) of
the cryptography library documentation.
