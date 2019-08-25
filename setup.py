#!/usr/bin/python

# from distutils.core import setup
from setuptools import setup, find_packages

import zplconvert

setup(name='zplconvert',
      packages=find_packages(),
      package_data={
          '': ['zebra_logo.png']
      },
      description="ZPL Image converter",
      long_description=open('README.md').read(),
      author='Teemu Karimerto',
      author_email='teemu.karimerto@gmail.com',
      version=zplconvert.__version__,
      url='https://github.com/Karimerto/zplconvert',
      license='MIT License',
      entry_points={
          'console_scripts': [
              'zplconvert = zplconvert.main:main'
          ]
      },
      keywords='zebra zpl convert converter',
      classifiers=[
          'Development Status :: 3 - Alpha',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: MIT License',
          'Operating System :: OS Independent',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Topic :: Multimedia :: Graphics :: Graphics Conversion',
          'Topic :: Printing']
)
