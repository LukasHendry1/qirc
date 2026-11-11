from glob import glob

from setuptools import find_packages, setup

package_name = 'qirc_localization'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', glob('config/*.yaml')),
        ('share/' + package_name + '/launch', glob('launch/*.launch.py')),
        ('share/' + package_name + '/udev', glob('udev/*.rules')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Lukas Hendry',
    maintainer_email='lukas.hendry15@gmail.com',
    description='Localization stack: LiDAR mapping of the house and localization within it',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'mapping_node = qirc_localization.mapping_node:main',
            'localization_node = qirc_localization.localization_node:main',
        ],
    },
)
