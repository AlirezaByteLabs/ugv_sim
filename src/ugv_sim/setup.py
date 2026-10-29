from glob import glob
import os
from pathlib import Path

from setuptools import find_packages, setup


assets = Path(__file__).resolve().parents[2] / 'assets'
asset_files: list[tuple[str, list[str]]] = []
for folder in ('Depot', 'robot'):
    for path in sorted((assets / folder).rglob('*')):
        if path.is_file() and path.suffix.lower() in {'.sdf', '.config', '.dae', '.stl', '.png', '.jpg', '.jpeg', '.material'}:
            asset_files.append((str(Path('share/ugv_sim/assets') / path.parent.relative_to(assets)),
                                [os.path.relpath(path, Path(__file__).resolve().parent)]))

setup(
    name='ugv_sim',
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/ugv_sim']),
        ('share/ugv_sim', ['package.xml']),
        ('share/ugv_sim/launch', glob('launch/*.launch.py')),
        ('share/ugv_sim/config', glob('config/*.yaml') + glob('config/*.rviz')),
        ('share/ugv_sim/urdf', glob('urdf/*.xacro')),
        ('share/ugv_sim/worlds', glob('worlds/*.sdf')),
    ] + asset_files,
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Alireza',
    description='Camera-equipped mecanum UGV simulation in Gazebo',
    license='MIT',
    entry_points={'console_scripts': ['cmd_vel_adapter = ugv_sim.cmd_vel_adapter:main']},
)
