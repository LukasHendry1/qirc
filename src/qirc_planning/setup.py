from setuptools import find_packages, setup

package_name = 'qirc_planning'

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
    description='Planning stack: vehicle manager, global planner and local planner',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'vehicle_manager_node = qirc_planning.vehicle_manager_node:main',
            'global_planner_node = qirc_planning.global_planner_node:main',
            'local_planner_node = qirc_planning.local_planner_node:main',
        ],
    },
)
