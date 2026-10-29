"""Limit keyboard commands and stop forwarding stale requests."""

import math
import time

from geometry_msgs.msg import Twist, TwistStamped
import rclpy
from rclpy.clock import Clock, ClockType
from rclpy.node import Node


def limited_velocity(velocity, limits):
    if not all(math.isfinite(value) for value in velocity):
        return 0.0, 0.0, 0.0
    return tuple(max(-limit, min(limit, value)) for value, limit in zip(velocity, limits))


class CommandAdapter(Node):
    def __init__(self):
        super().__init__('cmd_vel_adapter')
        self.timeout = self.declare_parameter('timeout', 0.5).value
        self.limits = tuple(self.declare_parameter(name, default).value for name, default in (
            ('max_linear', 0.35), ('max_lateral', 0.35), ('max_angular', 1.2)))
        if not all(math.isfinite(value) and value > 0 for value in (self.timeout, *self.limits)):
            raise ValueError('Timeout and velocity limits must be positive finite numbers')
        self.last_received = -math.inf
        self.velocity = (0.0, 0.0, 0.0)
        self.publisher = self.create_publisher(Twist, '/cmd_vel_gz', 1)
        self.create_subscription(TwistStamped, '/cmd_vel', self.receive, 1)
        # The watchdog must keep publishing zeros while simulation time is paused.
        self.create_timer(0.05, self.publish, clock=Clock(clock_type=ClockType.STEADY_TIME))

    def receive(self, message):
        self.velocity = limited_velocity(
            (message.twist.linear.x, message.twist.linear.y, message.twist.angular.z),
            self.limits)
        self.last_received = time.monotonic()

    def publish(self):
        message = Twist()
        if time.monotonic() - self.last_received <= self.timeout:
            message.linear.x, message.linear.y, message.angular.z = self.velocity
        self.publisher.publish(message)


def main(args=None):
    rclpy.init(args=args)
    node = CommandAdapter()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            node.publisher.publish(Twist())
        node.destroy_node()
        rclpy.try_shutdown()
