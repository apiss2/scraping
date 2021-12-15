from setuptools import setup
from scraping import __version__ as VERSION

install_requires = [
    'requests',
    'BeautifulSoup4',
    'tqdm',
    'pandas',
    'selenium',
]

packages = [
    'scraping',
]

setup(
    name='scraping',
    version=VERSION,
    packages=packages,
    install_requires=install_requires,
)
