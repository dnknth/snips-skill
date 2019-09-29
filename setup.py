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
    packages=find_packages('.'),
    package_dir={'snipsclient': 'snipsclient'},
    py_modules=[ "snipsclient.mqtt", "snipsclient.snips"],
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
