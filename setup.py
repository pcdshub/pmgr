import versioneer
from setuptools import setup, find_packages

setup(name='pmgr',
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      license='BSD',
      author='SLAC National Accelerator Laboratories',
      packages=find_packages(),
      include_package_data=True,
      description=('Parameter Manager for LCLS Device Configurations'),
      scripts=['pmgr/pmgr', 'pmgr/pmgr.py', 'pmgr/pmgrUtils.sh']
      )
