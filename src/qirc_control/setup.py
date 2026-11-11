from setuptools import find_packages, setup

package_name = 'qirc_control'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Lukas Hendry',
    maintainer_email='lukas.hendry15@gmail.com',
    description='Controls stack: trajectory tracking (MPC) for the drive motors',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'control_node = qirc_control.control_node:main',
        ],
    },
)
