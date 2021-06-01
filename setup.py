import versioneer
from setuptools import setup, find_packages

setup(name='pmgr',
      version=versioneer.get_version(),
      cmdclass=versioneer.get_cmdclass(),
      license='BSD',
      author='SLAC National Accelerator Laboratory',
      packages=find_packages(),
      include_package_data=True,
      description=('Parameter Manager for LCLS Device Configurations'),
      entry_points={'console_scripts': ['pmgrLauncher.sh = pmgr.pmgr:main',
                                        'pmgrUtils.sh = pmgr.pmgrUtils:main']}
      )
