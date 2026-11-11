from setuptools import find_packages, setup

package_name = 'qirc_pill_dispenser'

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
    description='Pill dispensing: dispensing motors and arm positioning',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'pill_box_node = qirc_pill_dispenser.pill_box_node:main',
            'arm_node = qirc_pill_dispenser.arm_node:main',
        ],
    },
)
