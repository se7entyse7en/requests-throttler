from setuptools import setup

import requests_throttler


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

setup(name=requests_throttler.__title__,
      version=requests_throttler.__version__,
      license=requests_throttler.__license__,
      url=requests_throttler.__project_url__,
      description='Python HTTP requests throttler',
      long_description=readme + '\n\n' + history,
      author=requests_throttler.__author__,
      author_email=requests_throttler.__author_email__,
      packages=packages,
      package_dir={'requests_throttler': 'requests_throttler'},
      package_data={'': ['LICENSE']},
      include_package_data=True,
      install_requires=requires,
      classifiers=classifiers)
