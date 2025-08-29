from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, RegisterEventHandler
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.substitutions import Command, FindExecutable, PathJoinSubstitution, LaunchConfiguration

from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    # Declare arguments
    declared_arguments = []
    declared_arguments.append(
        DeclareLaunchArgument(
            "remap_odometry_tf",
            default_value="false",
            description="Remap odometry TF from the steering controller to the TF tree.",
        )
    )

    # Initialize Arguments
    remap_odometry_tf = LaunchConfiguration("remap_odometry_tf")

    robot_description_content = Command(
        [
            PathJoinSubstitution([FindExecutable(name="xacro")]),
            " ",
            PathJoinSubstitution(
                [FindPackageShare("my_bot"), "description", "robot.urdf.xacro"]
            ),
        ]
    )
    robot_description = {"robot_description": robot_description_content}

    robot_controllers = PathJoinSubstitution(
        [
            FindPackageShare("my_bot"),
            "config",
            "my_controllers.yaml",
        ]
    )

    control_node = Node(
        package="controller_manager",
        executable="ros2_control_node",
        parameters=[robot_controllers],
        output="both",
    )
    robot_state_pub_ack_node = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="both",
        parameters=[robot_description],
    )

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["joint_state_broadcaster"],
    )

    # the steering controller libraries by default publish odometry on a separate topic than /tf
    robot_ack_controller_spawner_remapped = Node(
        package="controller_manager",
        executable="spawner",
        arguments=[
            "ack_cont",
            "--param-file",
            robot_controllers,
            "--controller-ros-args",
            "-r /ack_cont/tf_odometry:=/tf",
        ],
        condition=IfCondition(remap_odometry_tf),
    )

    robot_ack_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        arguments=["ack_cont", "--param-file", robot_controllers],
        condition=UnlessCondition(remap_odometry_tf),
    )

    # Delay start of joint_state_broadcaster after `robot_controller`
    # TODO(anyone): This is a workaround for flaky tests. Remove when fixed.
    delay_joint_state_broadcaster_after_robot_controller_spawner_remapped = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=robot_ack_controller_spawner_remapped,
            on_exit=[joint_state_broadcaster_spawner],
        )
    )
    delay_joint_state_broadcaster_after_robot_controller_spawner = RegisterEventHandler(
        event_handler=OnProcessExit(
            target_action=robot_ack_controller_spawner,
            on_exit=[joint_state_broadcaster_spawner],
        )
    )

    nodes = [
        control_node,
        robot_state_pub_ack_node,
        robot_ack_controller_spawner_remapped,
        robot_ack_controller_spawner,
        delay_joint_state_broadcaster_after_robot_controller_spawner_remapped,
        delay_joint_state_broadcaster_after_robot_controller_spawner,
    ]

    return LaunchDescription(nodes)
