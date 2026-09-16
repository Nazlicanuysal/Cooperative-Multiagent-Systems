import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node

def generate_launch_description():
    package_name = 'rob_one'

    # 1. Kendi yazdığımız rsp.launch.py'yi simülasyon saatiyle (use_sim_time) çağır
    rsp = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory(package_name),'launch','rsp.launch.py'
                )]), launch_arguments={'use_sim_time': 'true'}.items()
    )

    # 2. Arka planda boş bir Gazebo dünyası başlat
    gazebo = IncludeLaunchDescription(
                PythonLaunchDescriptionSource([os.path.join(
                    get_package_share_directory('gazebo_ros'), 'launch', 'gazebo.launch.py')]),
             )

    # 3. TF ağacındaki modeli alıp fiziksel olarak Gazebo'ya yerleştir (Spawning)
    spawn_entity = Node(package='gazebo_ros', executable='spawn_entity.py',
                        arguments=['-topic', 'robot_description',
                                   '-entity', 'amr_prototype'],
                        output='screen')

    return LaunchDescription([
        rsp,
        gazebo,
        spawn_entity
    ])
