from setuptools import setup

setup(
    name = 'pyfmt',
    version = '0.1',
    description = 'A python formatter',
    url = None,
    author = "Eli Ribble",
    extras_require = {
        "develop" : [
            "nose2"
        ]
    },
    install_requires = [],
    scripts = ['bin/pyfmt'],
    packages = ['pyfmt'],
    package_data = {
        'pyfmt' : ['pyfmt/*'],
    },
)
