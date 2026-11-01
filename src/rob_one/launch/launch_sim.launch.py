import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument, GroupAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace
from nav2_common.launch import RewrittenYaml

def generate_launch_description():
    pkg_share = get_package_share_directory('rob_one')
    gazebo_share = get_package_share_directory('gazebo_ros')

    world = LaunchConfiguration('world')

    declare_world = DeclareLaunchArgument(
        'world',
        default_value=os.path.join(pkg_share, 'worlds', 'deneme.world'),
        description='Yuklenecek Gazebo dunya dosyasi')

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(gazebo_share, 'launch', 'gazebo.launch.py')),
        launch_arguments={'world': world, 'verbose': 'true', 'gui': 'false'}.items())

    # Çoğaltılacak araçların listesi (İsimleri ve Gazebo başlangıç konumları)
    robots = [
        {'name': 'amr_1', 'x': '0.0', 'y': '1.0', 'z': '0.15'},
        {'name': 'amr_2', 'x': '0.0', 'y': '-1.0', 'z': '0.15'}
    ]

    spawn_robots_cmds = []
    
    twist_mux_params = os.path.join(pkg_share, 'config', 'twist_mux.yaml')
    nav2_params_file = os.path.join(pkg_share, 'config', 'nav2_params.yaml')
    map_file = os.path.join(pkg_share, 'maps', 'map_saved.yaml')

    # Global harita sunucusu ve yaşam döngüsü yöneticisi (Girintiler düzeltildi)
    global_map_server = Node(
        package='nav2_map_server',
        executable='map_server',
        name='map_server',
        output='screen',
        parameters=[{'yaml_filename': map_file}, {'use_sim_time': True}]
    )

    global_lifecycle_manager = Node(
        package='nav2_lifecycle_manager',
        executable='lifecycle_manager',
        name='lifecycle_manager_map',
        output='screen',
        parameters=[{'use_sim_time': True},
                    {'autostart': True},
                    {'node_names': ['map_server']}]
    )
    
    for robot in robots:
        
        # 1. Ana dosyada değişecek olan çerçeve/kanal isimleri
        param_substitutions = {
            'use_sim_time': 'true',
            # 'robot_description': LaunchConfiguration('robot_description'),          
        }

        # 2. Dinamik YAML dosyasının oluşturulması
        configured_params = RewrittenYaml(
            source_file=nav2_params_file,
            root_key=robot['name'],
            param_rewrites=param_substitutions,
            convert_types=True
        )

        # 3. Her robot için özel İsim Uzayı (Namespace) grubu
        robot_group = GroupAction([
            PushRosNamespace(robot['name']),

            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(pkg_share, 'launch', 'rsp.launch.py')),
                launch_arguments={
                    'use_sim_time': 'true',
                    'prefix': robot['name'] + '/'
                }.items()
            ),

            Node(
                package='gazebo_ros', executable='spawn_entity.py',
                arguments=[
                    '-topic', 'robot_description', 
                    '-entity', robot['name'],
                    '-robot_namespace', robot['name'],
                    '-x', robot['x'], '-y', robot['y'], '-z', robot['z']
                ],
                output='screen'
            ),

            Node(
                package='twist_mux',
                executable='twist_mux',
                output='screen',
                remappings=[('/cmd_vel_out', 'cmd_vel')],
                parameters=[twist_mux_params, {'use_sim_time': True}]
            ),
            
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(
                    os.path.join(pkg_share, 'launch', 'nav2_bringup_multi.launch.py') 
                ),
                launch_arguments={
                    'namespace': robot['name'],
                    'use_sim_time': 'true',
                    'params_file': configured_params
                }.items()
            )
        ])
        
        # 4. Grubu listeye ekle (Döngünün içinde!)
        spawn_robots_cmds.append(robot_group)

    # Döngü dışına çıkıp tüm komutları başlat (Global sunucular listeye eklendi!)
    return LaunchDescription([declare_world, gazebo, global_map_server, global_lifecycle_manager] + spawn_robots_cmds)