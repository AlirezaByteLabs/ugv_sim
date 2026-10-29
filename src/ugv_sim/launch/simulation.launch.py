"""Start the local Depot, CAD robot, ROS bridges, and camera viewer."""

import os
from pathlib import Path

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, EmitEvent, ExecuteProcess
from launch.actions import OpaqueFunction, RegisterEventHandler, SetEnvironmentVariable
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.events import Shutdown
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro


def launch_setup(context):
    share = Path(get_package_share_directory('ugv_sim'))
    meshes = share / 'assets' / 'robot'
    for name in ('chassis', 'front_left_wheel', 'front_right_wheel',
                 'rear_left_wheel', 'rear_right_wheel'):
        if not (meshes / f'{name}.stl').is_file():
            raise FileNotFoundError(meshes / f'{name}.stl')
    robot = xacro.process_file(str(share / 'urdf' / 'ugv.urdf.xacro'),
                               mappings={'use_cad': 'true', 'mesh_dir': str(meshes)}).toxml()
    gazebo = ExecuteProcess(cmd=['gz', 'sim', '-r', str(share / 'worlds' / 'depot.sdf')],
                            output='screen')
    spawn = Node(package='ros_gz_sim', executable='create', output='screen',
                 parameters=[{'world': 'depot', 'name': 'ugv', 'string': robot,
                              **{name: float(LaunchConfiguration(name).perform(context))
                                 for name in ('x', 'y', 'z')},
                              'Y': float(LaunchConfiguration('yaw').perform(context))}])

    def check_spawn(event, context):
        if event.returncode != 0:
            return [EmitEvent(event=Shutdown(reason='Robot spawn failed; see create output'))]
        return []

    resources = os.pathsep.join(filter(None, (str(share / 'assets'),
                                             os.environ.get('GZ_SIM_RESOURCE_PATH', ''))))
    return [
        SetEnvironmentVariable('GZ_SIM_RESOURCE_PATH', resources),
        RegisterEventHandler(OnProcessExit(target_action=gazebo, on_exit=[
            EmitEvent(event=Shutdown(reason='Gazebo exited'))])),
        RegisterEventHandler(OnProcessExit(target_action=spawn, on_exit=check_spawn)),
        gazebo,
        Node(package='robot_state_publisher', executable='robot_state_publisher',
             parameters=[{'robot_description': robot, 'use_sim_time': True}]),
        spawn,
        Node(package='ros_gz_bridge', executable='parameter_bridge', output='screen',
             parameters=[{'config_file': str(share / 'config' / 'bridge.yaml'),
                          'use_sim_time': True}]),
        Node(package='ugv_sim', executable='cmd_vel_adapter', output='screen'),
        Node(package='rqt_image_view', executable='rqt_image_view',
             arguments=['/camera/image_raw'], condition=IfCondition(LaunchConfiguration('viewer'))),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('viewer', default_value='true'),
        DeclareLaunchArgument('x', default_value='-5.0'),
        DeclareLaunchArgument('y', default_value='0.0'),
        DeclareLaunchArgument('z', default_value='0.05'),
        DeclareLaunchArgument('yaw', default_value='0.0'),
        OpaqueFunction(function=launch_setup),
    ])
