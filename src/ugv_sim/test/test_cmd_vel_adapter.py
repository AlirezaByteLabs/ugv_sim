import math
from types import SimpleNamespace

import pytest

from ugv_sim.cmd_vel_adapter import CommandAdapter, limited_velocity


@pytest.mark.parametrize('velocity,expected', [
    ((0.1, 0.2, -0.2), (0.1, 0.2, -0.2)),
    ((3.0, 2.0, -5.0), (0.35, 0.25, -1.2)),
    ((-3.0, -2.0, 5.0), (-0.35, -0.25, 1.2)),
    ((math.nan, 0.0, 1.0), (0.0, 0.0, 0.0)),
    ((1.0, 0.0, math.inf), (0.0, 0.0, 0.0)),
])
def test_limited_velocity(velocity, expected):
    assert limited_velocity(velocity, (0.35, 0.25, 1.2)) == expected


def test_watchdog_stops_expired_commands(monkeypatch):
    published = []
    adapter = SimpleNamespace(
        last_received=10.0, timeout=0.5, velocity=(0.2, -0.1, 0.7),
        publisher=SimpleNamespace(publish=published.append),
    )
    monkeypatch.setattr('ugv_sim.cmd_vel_adapter.time.monotonic', lambda: 10.2)
    CommandAdapter.publish(adapter)
    assert published[-1].linear.x == 0.2
    assert published[-1].angular.z == 0.7
    assert published[-1].linear.y == -0.1
    monkeypatch.setattr('ugv_sim.cmd_vel_adapter.time.monotonic', lambda: 10.6)
    CommandAdapter.publish(adapter)
    assert published[-1].linear.x == 0.0
    assert published[-1].angular.z == 0.0
    assert published[-1].linear.y == 0.0


def test_receive_limits_all_axes():
    from geometry_msgs.msg import TwistStamped
    adapter = SimpleNamespace(limits=(0.35, 0.35, 1.2))
    message = TwistStamped()
    message.twist.linear.x = 2.0
    message.twist.linear.y = -2.0
    message.twist.angular.z = 3.0
    CommandAdapter.receive(adapter, message)
    assert adapter.velocity == (0.35, -0.35, 1.2)
    assert math.isfinite(adapter.last_received)


def test_startup_publishes_zero():
    published = []
    adapter = SimpleNamespace(last_received=-math.inf, timeout=0.5,
                              velocity=(1.0, 1.0, 1.0),
                              publisher=SimpleNamespace(publish=published.append))
    CommandAdapter.publish(adapter)
    assert published[-1].linear.x == 0.0
    assert published[-1].linear.y == 0.0
    assert published[-1].angular.z == 0.0


@pytest.mark.parametrize('value', [0.0, -1.0, math.nan, math.inf])
def test_invalid_timeout_rejected(value):
    import rclpy
    from rclpy.parameter import Parameter
    rclpy.init()
    try:
        original = CommandAdapter.declare_parameter

        def declare(self, name, default, *args, **kwargs):
            if name == 'timeout':
                return Parameter(name, value=value)
            return original(self, name, default, *args, **kwargs)

        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(CommandAdapter, 'declare_parameter', declare)
            with pytest.raises(ValueError, match='positive finite'):
                CommandAdapter()
    finally:
        rclpy.shutdown()
