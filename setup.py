from glob import glob
from os.path import basename
from os.path import splitext

from setuptools import setup, find_packages


with open( "requirements.txt", "r") as fh:
    requirements = fh.read().splitlines()

setup(
    name="snipsclient",
    version="0.1.0",
    description="A utility package to simplify the development of Snips client applications",
    license="MIT",
    author="dnknth",
    url="https://github.com/dnknth/snipsclient.git",
    package_dir={'': '.'},
    py_modules=[ "mqtt", "snips"],
    install_requires=requirements,
    include_package_data=True,
    zip_safe=False,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Software Development :: Libraries'
    ],
)
