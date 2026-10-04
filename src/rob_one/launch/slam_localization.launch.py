import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='false')
    
    # Paket dizinini ve config dosyasını tanımlıyoruz
    pkg_dir = get_package_share_directory('rob_one')
    config_file = os.path.join(pkg_dir, 'config', 'localization_params.yaml')

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='false',
            description='Gazebo kullaniliyorsa true yapilmali'),

        # SLAM Toolbox'ı lokalizasyon modunda başlatıyoruz
        Node(
            package='slam_toolbox',
            executable='localization_slam_toolbox_node',
            name='slam_toolbox',
            output='screen',
            parameters=[
                config_file,
                {'use_sim_time': use_sim_time}
            ]
        )
    ])