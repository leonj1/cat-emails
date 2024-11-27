from setuptools import setup, find_packages

setup(
    name="cat-emails",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'requests>=2.26.0',
        'requests-mock>=1.11.0',
        'pydantic>=2.9.2',
        'beautifulsoup4>=4.9.3',
        'tabulate>=0.8.9'
    ],
)
