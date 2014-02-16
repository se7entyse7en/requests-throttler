import re
from setuptools import setup

TITLE_REGEX = r"^__title__\s=\s(?P<quote>['])(?P<title>\w*)(?P=quote)$"
VERSION_REGEX = r"^__version__\s=\s(?P<quote>['])(?P<version>[\d\.]*)(?P=quote)$"
LICENSE_REGEX = r"^__license__\s=\s(?P<quote>['])(?P<license>.*)(?P=quote)$"
PROJECT_URL_REGEX = r"^__project_url__\s=\s(?P<quote>['])(?P<project_url>.*)(?P=quote)$"
AUTHOR_REGEX = r"^__author__\s=\s(?P<quote>['])(?P<author>[\w\s]*)(?P=quote)$"
AUTHOR_EMAIL_REGEX = r"^__author_email__\s=\s(?P<quote>['])(?P<author_email>.*)(?P=quote)$"


packages = ['requests_throttler',
            'requests_throttler.tests']

requires = ['requests==2.1.0',
            'futures==2.1.5']

classifiers=[
    'Development Status :: 4 - Beta',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'Intended Audience :: System Administrators',
    'License :: OSI Approved :: Apache Software License',
    'Natural Language :: English',
    'Programming Language :: Python',
    'Topic :: Internet',
    'Topic :: Internet :: WWW/HTTP'
]

with open('README.rst') as f:
    readme = f.read()
with open('HISTORY.rst') as f:
    history = f.read()
with open('./requests_throttler/__init__.py') as f:
    datas = f.read()

title = re.search(TITLE_REGEX, datas, re.MULTILINE).group('title')
version = re.search(VERSION_REGEX, datas, re.MULTILINE).group('version')
license = re.search(LICENSE_REGEX, datas, re.MULTILINE).group('license')
project_url = re.search(PROJECT_URL_REGEX, datas, re.MULTILINE).group('project_url')
author = re.search(AUTHOR_REGEX, datas, re.MULTILINE).group('author')
author_email = re.search(AUTHOR_EMAIL_REGEX, datas, re.MULTILINE).group('author_email')

setup(name=title,
      version=version,
      license=license,
      url=project_url,
      description='Python HTTP requests throttler',
      long_description=readme + '\n\n' + history,
      author=author,
      author_email=author_email,
      packages=packages,
      package_dir={'requests_throttler': 'requests_throttler'},
      package_data={'': ['LICENSE']},
      include_package_data=True,
      install_requires=requires,
      classifiers=classifiers)
