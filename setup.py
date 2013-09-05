import ez_setup
ez_setup.use_setuptools()
from setuptools import setup, find_packages
setup(
    name="Smoq",
    version="0.1",
    packages=find_packages(),
    entry_point={
        'console_scripts': [
             'smoqi = smoq.query:main'
        ]
    },
    # Project uses reStructuredText, so ensure that the docutils get
    # installed or upgraded on the target machine
    install_requires =['docutils>=0.3'],
    package_data={
        # If any package contains *.txt or *.rst files, include them:
        '': ['*.txt', '*.rst'],
    },

    # metadata for upload to PyPI
    author="Dan Gunter",
    author_email="dkgunter@lbl.gov",
    description="Simple MongoDB Query (SMoQ)",
    license="LGPL",
    keywords="MongoDB",
    url="http://example.com/HelloWorld/",   # project home page, if any
    # could also include long_description, download_url, classifiers, etc.
)
