import os, sys, subprocess
import serial.tools.list_ports
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import LogInfo, RegisterEventHandler, TimerAction, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessStart, OnShutdown
from launch.substitutions import LocalSubstitution, PythonExpression, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():

    # -----------------------------------------------------------------------------------------------------------------
    # Check if the robot is physically connected
    os.environ['MAGICIAN_USB_DEVICE_PATH'] = 'none'
    ports = serial.tools.list_ports.comports()

    for port in ports:
        if port.manufacturer == 'Silicon Labs':
            os.environ['MAGICIAN_USB_DEVICE_PATH'] = port.usb_device_path

    if os.environ['MAGICIAN_USB_DEVICE_PATH'] == 'none':
        sys.exit("Dobot is disconnected! Check if the USB cable and power adapter are plugged in.")
    # ----------------------------------------------------------------script-------------------------------------------------


    # -----------------------------------------------------------------------------------------------------------------
    # Check if another instance of dobot_bringup is already running
    script_name = os.path.basename(__file__)
    cmd = f"ps aux | grep '{script_name}' | grep -v grep | grep -v {os.getpid()}"

    result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.stdout.strip():  # If output is not empty, another instance is running
        print("Another instance of dobot_bringup is already running. Do NOT use ctrl+Z inside the terminal with dobot_bringup launched.")
        print("If you want to kill the previous process, follow the steps below:")
        print("1. Run the following command to find the process ID of the running script: ps aux | grep dobot_bringup | grep -v grep")
        print("   The second column is the Process ID (PID).")
        print("2. Once you have the PID, use the kill command to terminate it: kill -9 <PID_of_dobot_bringup>")
        print("   Now, another instance of dobot_bringup can be launched again.")
        print("Exiting...")
        sys.exit(1)
    # -----------------------------------------------------------------------------------------------------------------


    # -----------------------------------------------------------------------------------------------------------------
    # Check if MAGICIAN_TOOL env var has the right value
    tool_env_var = str(os.environ.get('MAGICIAN_TOOL'))

    if tool_env_var == "None":
         sys.exit("MAGICIAN_TOOL env var is not set!")

    if tool_env_var not in ['none', 'pen', 'suction_cup', 'gripper', 'extended_gripper']:
         sys.exit("MAGICIAN_TOOL env var has an incorrect value!")

    valid_tool=["'", tool_env_var, "' == 'none'", 'or', \
                "'", tool_env_var, "' == 'pen'", 'or', \
                "'", tool_env_var, "' == 'suction_cup'", 'or', \
                "'", tool_env_var, "' == 'gripper'", 'or', \
                "'", tool_env_var, "' == 'extended_gripper'"
    ]
    # -----------------------------------------------------------------------------------------------------------------


    # -----------------------------------------------------------------------------------------------------------------
    # Nodes & launch files

    tool_null = Node(
        package='dobot_bringup',
        executable='set_tool_null',
        output='screen',
        condition = IfCondition(PythonExpression(valid_tool))
    )

    alarms = IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare('dobot_diagnostics'),
                    'launch',
                    'alarms_analyzer.launch.py'
                ])
            ]),
            condition = IfCondition(PythonExpression(valid_tool))
        )

    gripper = Node(
        package='dobot_end_effector',
        executable='gripper_server',
        output='screen',
        condition = IfCondition(PythonExpression(valid_tool))
    )

    suction_cup = Node(
        package='dobot_end_effector',
        executable='suction_cup_server',
        output='screen',
        condition = IfCondition(PythonExpression(valid_tool))
    )

    homing = IncludeLaunchDescription(
            PythonLaunchDescriptionSource([
                PathJoinSubstitution([
                    FindPackageShare('dobot_homing'),
                    'launch',
                    'dobot_homing.launch.py'
                ])
            ]),
            condition = IfCondition(PythonExpression(valid_tool))
        )

    trajectory_validator = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('dobot_kinematics'),
                'launch',
                'dobot_validate_trajectory.launch.py'
            ])
        ]),
        condition = IfCondition(PythonExpression(valid_tool))
    )
    
    PTP_action = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('dobot_motion'),
                'launch',
                'dobot_PTP.launch.py'
            ])
        ]),
        condition = IfCondition(PythonExpression(valid_tool))
    )

    robot_state = Node(
        package='dobot_state_updater',
        executable='state_publisher',
        output='screen',
        condition = IfCondition(PythonExpression(valid_tool))
    )

    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    # OnProcessStart events for information purposes

    tool_null_event = RegisterEventHandler(
        OnProcessStart(
            target_action=tool_null,
            on_start=[
                LogInfo(msg='Loading tool parameters.')
            ]
        )
    )

    gripper_event = RegisterEventHandler(
        OnProcessStart(
            target_action=gripper,
            on_start=[
                LogInfo(msg='Gripper control service started.')
            ]
        )
    )

    suction_cup_event = RegisterEventHandler(
        OnProcessStart(
            target_action=suction_cup,
            on_start=[
                LogInfo(msg='Suction Cup control service started.')
            ]
        )
    )

    robot_state_event = RegisterEventHandler(
        OnProcessStart(
            target_action=robot_state,
            on_start=[
                LogInfo(msg='Dobot state updater node started.'),
                LogInfo(msg='Dobot Magician control stack has been launched correctly')
            ]
        )
    )
    # -----------------------------------------------------------------------------------------------------------------



    # -----------------------------------------------------------------------------------------------------------------
    # Shutdown event handler
    on_shutdown = RegisterEventHandler(
        OnShutdown(
            on_shutdown=[LogInfo(
                msg=['Dobot Magician control system launch was asked to shutdown: ',
                    LocalSubstitution('event.reason')]
            )]
        )
    )
    # -----------------------------------------------------------------------------------------------------------------

    # -----------------------------------------------------------------------------------------------------------------
    # Launch scheduler


    tool_null_sched = TimerAction(
        period=1.0,
        actions=[tool_null]
        )

    alarms_sched = TimerAction(
        period=2.0,
        actions=[alarms]
        )

    gripper_sched = TimerAction(
        period=2.0,
        actions=[gripper]
        )

    suction_cup_sched = TimerAction(
        period=2.0,
        actions=[suction_cup]
        )

    homing_sched = TimerAction(
        period=3.0,
        actions=[homing]
        )

    trajectory_validator_sched = TimerAction(
        period=5.0,
        actions=[trajectory_validator]
        )

    PTP_action_sched = TimerAction(
        period=7.0,
        actions=[PTP_action]
        )

    robot_state_sched = TimerAction(
        period=18.0,
        actions=[robot_state]
        )

    # -----------------------------------------------------------------------------------------------------------------


    return LaunchDescription([
        tool_null_event,
        gripper_event,
        suction_cup_event,
        robot_state_event,
        tool_null_sched,
        alarms_sched,
        gripper_sched,
        suction_cup_sched,
        homing_sched,
        trajectory_validator_sched,
        PTP_action_sched,
        robot_state_sched,
        on_shutdown
    ])
