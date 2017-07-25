#!/usr/bin/env python

from distutils.core import setup

setup(name='restit',
      version='0.1',
      description='Generic REST client for Python',
      author='Ricardo Dias',
      author_email='rdias@suse.com',
      url='https://github.com/rjfd/restit',
      packages=['restit'],
      package_dir={'restit': 'restit'})
