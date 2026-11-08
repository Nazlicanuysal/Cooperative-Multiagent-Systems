import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, GroupAction, OpaqueFunction,
                            SetEnvironmentVariable)
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node, PushRosNamespace
from launch_ros.descriptions import ParameterFile
from nav2_common.launch import RewrittenYaml


def _check_namespace(context, *args, **kwargs):
    # rqt_graph'taki kök isim uzayındaki (/planner_server, /controller_server ...)
    # "hayalet" Nav2 yığını, bu dosyanın namespace'siz çağrılmasından kaynaklanıyordu.
    # Boş namespace ile başlatılmasını engelle.
    ns = LaunchConfiguration('namespace').perform(context).strip('/')
    if not ns:
        raise RuntimeError(
            "[nav2_bringup_multi] 'namespace' boş olamaz (ör. namespace:=amr_1). "
            "Namespace'siz Nav2 yığını /odom gibi var olmayan topic'lere bağlanır.")
    return []


def generate_launch_description():
    pkg_share = get_package_share_directory('rob_one')
    default_params_file = os.path.join(pkg_share, 'config', 'nav2_params.yaml')

    namespace = LaunchConfiguration('namespace')
    use_sim_time = LaunchConfiguration('use_sim_time')
    autostart = LaunchConfiguration('autostart')
    params_file = LaunchConfiguration('params_file')
    use_respawn = LaunchConfiguration('use_respawn')
    log_level = LaunchConfiguration('log_level')

    # Lokalizasyon ve navigasyon AYRI yöneticilerde: AMCL düşerse
    # tüm navigasyon yığını onunla birlikte "bond" hatasıyla kapanmaz.
    localization_nodes = ['amcl']
    navigation_nodes = ['controller_server', 'smoother_server', 'planner_server',
                        'behavior_server', 'bt_navigator', 'waypoint_follower',
                        'velocity_smoother']

    # YAML'daki 'controller_server:' gibi anahtarlar yalnızca /controller_server ile
    # eşleşir; /amr_1/controller_server parametreleri ALMAZ. RewrittenYaml tüm
    # dosyayı '<namespace>:' altına taşıyarak eşleşmeyi sağlar.
    configured_params = ParameterFile(
        RewrittenYaml(
            source_file=params_file,
            root_key=namespace,
            # Çerçeve adları ve costmap scan topic'leri launch_sim.launch.py içinde
            # tam yol ile robot başına yazılır; burada yalnızca isim uzayı sarmalanır.
            param_rewrites={'use_sim_time': use_sim_time},
            convert_types=True),
        allow_substs=True)

    # Tüm robotlar ORTAK /tf ağacını kullanır (çerçeveler amr_X/ önekli).
    # tf2 dinleyicileri zaten mutlak '/tf' ve '/tf_static' kullanır.
    # Harita sunucusu tek ve global: göreli 'map' -> '/amr_X/map' olmasın.
    remappings = [('map', '/map'), ('map_updates', '/map_updates')]

    # Hız zinciri:
    # controller/behavior -> cmd_vel_nav -> velocity_smoother -> cmd_vel_nav_smoothed
    # -> twist_mux (cmd_vel_out -> cmd_vel olarak remap edilmeli) -> diff_drive
    nav_cmd_remap = [('cmd_vel', 'cmd_vel_nav')]

    common = dict(output='screen', respawn=use_respawn, respawn_delay=2.0,
                  parameters=[configured_params],
                  arguments=['--ros-args', '--log-level', log_level])

    lifecycle_common = dict(output='screen',
                            arguments=['--ros-args', '--log-level', log_level])

    load_nodes = GroupAction(actions=[
        # İsim uzayı YALNIZCA burada push edilir. Bu dosyayı çağıran launch
        # dosyası ayrıca PushRosNamespace YAPMAMALIDIR.
        PushRosNamespace(namespace),

        # ---------------- LOCALIZATION ----------------
        Node(package='nav2_amcl', executable='amcl', name='amcl',
             remappings=remappings, **common), # type: ignore
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
             name='lifecycle_manager_localization',
             parameters=[{'use_sim_time': use_sim_time,
                          'autostart': autostart,
                          'node_names': localization_nodes,
                          'bond_timeout': 10.0}],
             **lifecycle_common), # type: ignore

        # ---------------- NAVIGATION ----------------
        Node(package='nav2_controller', executable='controller_server',
             name='controller_server',
             remappings=remappings + nav_cmd_remap, **common), # type: ignore
        Node(package='nav2_smoother', executable='smoother_server',
             name='smoother_server', remappings=remappings, **common), # type: ignore
        Node(package='nav2_planner', executable='planner_server',
             name='planner_server', remappings=remappings, **common), # type: ignore
        Node(package='nav2_behaviors', executable='behavior_server',
             name='behavior_server', 
             remappings=remappings + nav_cmd_remap, **common), # type: ignore
        Node(package='nav2_bt_navigator', executable='bt_navigator',
             name='bt_navigator', remappings=remappings, **common), # type: ignore
        Node(package='nav2_waypoint_follower', executable='waypoint_follower',
             name='waypoint_follower', remappings=remappings, **common), # type: ignore
        Node(package='nav2_velocity_smoother', executable='velocity_smoother',
             name='velocity_smoother',
             remappings=remappings + [('cmd_vel', 'cmd_vel_nav'),
                                      ('cmd_vel_smoothed', 'cmd_vel_nav_smoothed')],
             **common), # type: ignore
        Node(package='nav2_lifecycle_manager', executable='lifecycle_manager',
             name='lifecycle_manager_navigation',
             parameters=[{'use_sim_time': use_sim_time,
                          'autostart': autostart,
                          'node_names': navigation_nodes,
                          'bond_timeout': 10.0}],
             **lifecycle_common), # type: ignore
    ])

    ld = LaunchDescription()
    ld.add_action(SetEnvironmentVariable('RCUTILS_LOGGING_BUFFERED_STREAM', '1'))
    # Varsayılan değer YOK -> namespace zorunlu argüman.
    ld.add_action(DeclareLaunchArgument(
        'namespace', description='Robot isim uzayı, ör. amr_1 (zorunlu)'))
    ld.add_action(DeclareLaunchArgument('use_sim_time', default_value='true'))
    ld.add_action(DeclareLaunchArgument('params_file', default_value=default_params_file))
    ld.add_action(DeclareLaunchArgument('autostart', default_value='true'))
    ld.add_action(DeclareLaunchArgument('use_respawn', default_value='False'))
    ld.add_action(DeclareLaunchArgument('log_level', default_value='info'))
    ld.add_action(OpaqueFunction(function=_check_namespace))
    ld.add_action(load_nodes)
    return ld