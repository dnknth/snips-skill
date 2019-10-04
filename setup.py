from setuptools import setup, find_packages


with open( "requirements.txt", "r") as fh:
    requirements = fh.read().splitlines()

setup(
    name="snips-skill",
    version="0.1.0",
    description="Simplify the development of Snips skills",
    license="MIT",
    author="dnknth",
    url="https://github.com/dnknth/snips_skill.git",
    packages=find_packages('.'),
    package_dir={'snips_skill': 'snips_skill'},
    package_data = { 'snips_skill': ['locale/*/LC_MESSAGES/*.mo'] },
    py_modules=[ "snips_skill.mqtt", "snips_skill.snips",
        "snips_skill.intent", "snips_skill.multi_room"],
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
