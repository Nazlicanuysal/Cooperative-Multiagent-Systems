import os
import tempfile

import yaml
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, GroupAction, IncludeLaunchDescription,
                            RegisterEventHandler, TimerAction)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace

# Robot başına Nav2 yığınını başlatan dosya. İçinde PushRosNamespace +
# RewrittenYaml(root_key=namespace) VARDIR -> burada namespace sarmalaması YAPILMAZ.
NAV2_LAUNCH = 'nav2_bringup_multi.launch.py'

# ---------------------------------------------------------------------------
# Filo tanımı: isim + Gazebo spawn pozu. AMCL initial_pose BURADAN türetilir,
# böylece spawn pozu ile AMCL başlangıç pozu asla birbirinden kopamaz.
# ---------------------------------------------------------------------------
ROBOTS = [
    {'name': 'amr_1', 'x': 0.0, 'y': 1.0, 'z': 0.15, 'yaw': 0.0},
    {'name': 'amr_2', 'x': 0.0, 'y': -1.0, 'z': 0.15, 'yaw': 0.0},
]


def set_path(d, path, value):
    """'a.b.c' yolundaki anahtarı ayarla; yol (son anahtar dahil) yoksa hata ver.

    Son anahtar da kontrol edilir: yazım hatası olan bir yol sessizce YENİ bir
    parametre oluşturup asıl değeri değiştirmeden bırakmasın.
    """
    keys = path.split('.')
    for k in keys[:-1]:
        if not isinstance(d, dict) or k not in d:
            raise KeyError(f'nav2_params.yaml icinde yol bulunamadi: {path}')
        d = d[k]
    if keys[-1] not in d:
        raise KeyError(f'nav2_params.yaml icinde anahtar bulunamadi: {path}')
    d[keys[-1]] = value


def make_robot_params(src_yaml, robot):
    """Ortak nav2_params.yaml'dan robota özel bir YAML üretir.

    Her çerçeve adı ve topic AÇIKÇA (tam yol ile) yazılır. Böylece 'global_frame'
    gibi farklı düğümlerde farklı değer alması gereken anahtarlar çakışmaz.

    DİKKAT: Çıktı isim uzayı altına SARILMAZ. Bunu nav2 launch dosyasındaki
    RewrittenYaml(root_key=namespace) yapar. Burada da sarılırsa parametreler
    'amr_1: amr_1: ...' olur ve hiçbir düğüm parametresini bulamaz.
    """
    ns = robot['name']
    p = ns + '/'
    with open(src_yaml, 'r') as f:
        params = yaml.safe_load(f)

    # map_server global; robot dosyasında kalmasın
    params.pop('map_server', None)

    rewrites = {
        # --- AMCL ---
        'amcl.ros__parameters.base_frame_id': p + 'base_footprint',
        'amcl.ros__parameters.odom_frame_id': p + 'odom',
        'amcl.ros__parameters.global_frame_id': 'map',
        'amcl.ros__parameters.initial_pose.x': float(robot['x']),
        'amcl.ros__parameters.initial_pose.y': float(robot['y']),
        'amcl.ros__parameters.initial_pose.yaw': float(robot['yaw']),
        # --- BT Navigator ---
        'bt_navigator.ros__parameters.global_frame': 'map',
        'bt_navigator.ros__parameters.robot_base_frame': p + 'base_footprint',
        # --- Local costmap (odom çerçevesinde) ---
        'local_costmap.local_costmap.ros__parameters.global_frame': p + 'odom',
        'local_costmap.local_costmap.ros__parameters.robot_base_frame': p + 'base_footprint',
        # Costmap düğümü /amr_X/local_costmap altında çalışır; göreli 'scan' bazı
        # sürümlerde /amr_X/local_costmap/scan'e çözülür -> mutlak yol ver.
        'local_costmap.local_costmap.ros__parameters.voxel_layer.scan.topic': f'/{ns}/scan',
        # --- Global costmap (map çerçevesinde) ---
        'global_costmap.global_costmap.ros__parameters.global_frame': 'map',
        'global_costmap.global_costmap.ros__parameters.robot_base_frame': p + 'base_footprint',
        'global_costmap.global_costmap.ros__parameters.obstacle_layer.scan.topic': f'/{ns}/scan',
        # --- Smoother server ---
        'smoother_server.ros__parameters.robot_base_frame': p + 'base_footprint',
        # --- Behavior server (odom çerçevesinde) ---
        'behavior_server.ros__parameters.global_frame': p + 'odom',
        'behavior_server.ros__parameters.robot_base_frame': p + 'base_footprint',
    }
    for path, value in rewrites.items():
        set_path(params, path, value)

    out = os.path.join(tempfile.gettempdir(), f'nav2_params_{ns}.yaml')
    with open(out, 'w') as f:
        yaml.safe_dump(params, f, sort_keys=False)
    return out


def generate_launch_description():
    pkg_share = get_package_share_directory('rob_one')
    gazebo_share = get_package_share_directory('gazebo_ros')

    nav2_params_file = os.path.join(pkg_share, 'config', 'nav2_params.yaml')
    twist_mux_params = os.path.join(pkg_share, 'config', 'twist_mux.yaml')
    map_file = os.path.join(pkg_share, 'maps', 'map_saved.yaml')

    world = LaunchConfiguration('world')
    declare_world = DeclareLaunchArgument(
        'world', default_value=os.path.join(pkg_share, 'worlds', 'deneme.world'))

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(gazebo_share, 'launch', 'gazebo.launch.py')),
        launch_arguments={'world': world, 'verbose': 'true', 'gui': 'false'}.items())

    # ---------------- GLOBAL: tek harita sunucusu ----------------
    # Bilerek isim uzaysız: /map ve /map_server. Kök isim uzayında OLMASI GEREKEN
    # tek Nav2 bileşenleri bu ikisidir.
    global_map_server = Node(
        package='nav2_map_server', executable='map_server', name='map_server',
        output='screen',
        parameters=[{'yaml_filename': map_file, 'use_sim_time': True,
                     'topic_name': 'map', 'frame_id': 'map'}])

    global_lifecycle_manager = Node(
        package='nav2_lifecycle_manager', executable='lifecycle_manager',
        name='lifecycle_manager_map', output='screen',
        parameters=[{'use_sim_time': True, 'autostart': True,
                     'node_names': ['map_server']}])

    actions = [declare_world, gazebo, global_map_server, global_lifecycle_manager]

    previous_spawn = None
    for robot in ROBOTS:
        ns = robot['name']
        robot_params = make_robot_params(nav2_params_file, robot)

        # 1) RSP + twist_mux: hemen başlayabilir (isim uzayı TEK KEZ push edilir)
        base_group = GroupAction([
            PushRosNamespace(ns),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(os.path.join(pkg_share, 'launch', 'rsp.launch.py')),
                launch_arguments={'use_sim_time': 'true', 'prefix': ns + '/'}.items()),
            Node(
                package='twist_mux', executable='twist_mux', name='twist_mux',
                output='screen',
                parameters=[twist_mux_params, {'use_sim_time': True}],
                # twist_mux 'cmd_vel_out' (göreli) yayınlar -> /amr_X/cmd_vel
                remappings=[('cmd_vel_out', 'cmd_vel')]),
        ])
        actions.append(base_group)

        # 2) Spawn: robotlar SIRAYLA spawn edilir (Gazebo factory yarışını önler)
        spawn = Node(
            package='gazebo_ros', executable='spawn_entity.py',
            name=f'spawn_{ns}', output='screen',
            arguments=['-topic', f'/{ns}/robot_description',
                       '-entity', ns,
                       '-robot_namespace', ns,
                       '-x', str(robot['x']), '-y', str(robot['y']),
                       '-z', str(robot['z']), '-Y', str(robot['yaw']),
                       '-timeout', '60'])

        if previous_spawn is None:
            actions.append(TimerAction(period=3.0, actions=[spawn]))
        else:
            actions.append(RegisterEventHandler(OnProcessExit(
                target_action=previous_spawn, on_exit=[spawn])))

        # 3) Nav2: ancak bu robot Gazebo'da var olduktan SONRA başlar.
        #    NAV2_LAUNCH kendi içinde PushRosNamespace + root_key yapar ->
        #    burada DIŞARIDA bir namespace grubu YOK (çift isim uzayı olmaz).
        nav2 = IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(pkg_share, 'launch', NAV2_LAUNCH)),
            launch_arguments={'namespace': ns,
                              'use_sim_time': 'true',
                              'params_file': robot_params}.items())
        actions.append(RegisterEventHandler(OnProcessExit(
            target_action=spawn,
            on_exit=[TimerAction(period=3.0, actions=[nav2])])))

        previous_spawn = spawn

    return LaunchDescription(actions)