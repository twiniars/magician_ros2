from rqt_gui_py.plugin import Plugin
from .dobot_control_panel_widget import DobotControlPanel
import rclpy
from rclpy.node import Node
import threading
    
    
class Ros2DobotControlPanel(Plugin):

    def __init__(self, context):
        super(Ros2DobotControlPanel, self).__init__(context)

        self.worker_node = Node('dobot_control_panel_worker')
        worker_thread = threading.Thread(target=rclpy.spin, args=(self.worker_node,))
        worker_thread.start()

        self._logger = context.node.get_logger().get_child('dobot_control_panel.ros2_dobot_control_panel.Ros2DobotControlPanel')
        
        self.setObjectName('Ros2DobotControlPanel')

        self._widget = DobotControlPanel(self.worker_node, self)

        self._widget.start()
        if context.serial_number() > 1:
            self._widget.setWindowTitle(
                self._widget.windowTitle() + (' (%d)' % context.serial_number()))
        context.add_widget(self._widget)
