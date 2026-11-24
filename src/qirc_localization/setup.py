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
        ('share/' + package_name + '/rviz', glob('rviz/*.rviz')),
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
            'imu_bias = qirc_localization.imu_bias:main',
            'laser_odometry = qirc_localization.laser_odometry:main',
            'odometry_test = qirc_localization.odometry_test:main',
            'save_map = qirc_localization.save_map:main',
        ],
    },
)
