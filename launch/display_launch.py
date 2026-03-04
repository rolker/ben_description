from ament_index_python.packages import get_package_share_path
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import Command
from launch.substitutions import LaunchConfiguration
from launch.substitutions import TextSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    namespace = LaunchConfiguration('namespace')

    namespace_arg = DeclareLaunchArgument(
        'namespace', default_value=TextSubstitution(text='ben')
    )

    pkg_share = get_package_share_path('ben_description')
    path_to_urdf = pkg_share / 'urdf' / 'ben_mesh.xacro'
    path_to_rviz = pkg_share / 'rviz' / 'urdf.rviz'

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        namespace=namespace,
        parameters=[{
            'robot_description': ParameterValue(
                Command(['xacro ', str(path_to_urdf),
                         ' namespace:=', namespace]), value_type=str
            )
        }],
        emulate_tty=True,
    )

    joint_state_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        namespace=namespace,
        emulate_tty=True,
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        arguments=['-d', str(path_to_rviz)],
    )

    return LaunchDescription([
        namespace_arg,
        robot_state_publisher_node,
        joint_state_publisher_node,
        rviz_node,
    ])
