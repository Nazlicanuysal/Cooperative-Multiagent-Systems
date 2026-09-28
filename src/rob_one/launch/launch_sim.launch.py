import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_share = get_package_share_directory('rob_one')
    gazebo_share = get_package_share_directory('gazebo_ros')

    world = LaunchConfiguration('world')

    declare_world = DeclareLaunchArgument(
        'world',
        default_value=os.path.join(pkg_share, 'worlds', 'deneme.world'),
        description='Yuklenecek Gazebo dunya dosyasi')

    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_share, 'launch', 'rsp.launch.py')),
        launch_arguments={'use_sim_time': 'true'}.items())

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_share, 'launch', 'gazebo.launch.py')),
        launch_arguments={'world': world, 'verbose': 'true'}.items())

    spawn_entity = Node(
        package='gazebo_ros', executable='spawn_entity.py',
        arguments=['-topic', 'robot_description',
                   '-entity', 'amr_prototype',
                   '-x', '0.0', '-y', '0.0', '-z', '0.15'],
        output='screen')

    twist_mux_params = os.path.join(get_package_share_directory('rob_one'),'config','twist_mux.yaml')
    twist_mux_node = Node(
        package='twist_mux', 
        executable='twist_mux',
        output='screen',
        remappings=[('/cmd_vel_out', '/cmd_vel')],
        parameters=[twist_mux_params])

    return LaunchDescription([declare_world, rsp, gazebo, spawn_entity, twist_mux_node])