# Camera UGV In Depot

Learn ROS 2 by taking a CAD-derived robot into Gazebo, driving it manually,
and viewing its onboard RGB camera in the Depot warehouse. This is a local,
standalone simulation. Robot meshes and warehouse assets are not included in
the repository and must be prepared locally in `assets/` before building.

There is no lidar, mapping, autonomous navigation, or real-motor connection.
The current target is Ubuntu 26.04, ROS 2 Lyrical, and Gazebo Jetty
(Gazebo Sim 10.5.0 was used during development).

## Assets

The `assets/` directory is excluded from Git. Obtain the source models from the
links in Credits And Asset Sources, subject to their respective terms, and
prepare the following local files before building:

- `assets/robot/chassis.stl` and `assets/robot/{front_left,front_right,rear_left,rear_right}_wheel.stl`.
- `assets/Depot/model.config`, `assets/Depot/model.sdf`, and the Depot meshes,
  materials and textures referenced by the model.

A fresh clone cannot run the full simulation until compatible assets have been prepared.

## Dependencies

With ROS 2 Lyrical installed, install the simulation tools if missing:

```bash
sudo apt update
sudo apt install python3-colcon-common-extensions python3-pytest \
  ros-lyrical-ros-gz ros-lyrical-xacro \
  ros-lyrical-robot-state-publisher ros-lyrical-teleop-twist-keyboard \
  ros-lyrical-rqt-image-view
```

Source ROS in every new terminal. 

## Build And Run

From the repository/workspace root:

```bash
source /opt/ros/lyrical/setup.bash
colcon build --symlink-install --packages-select ugv_sim
source install/local_setup.bash
ros2 launch ugv_sim simulation.launch.py
```

`--symlink-install` is recommended for development: supported installed files
point to their source files instead of duplicating them, reducing asset storage
and making edits available without rebuilding existing linked files. Restart
the affected node or relaunch Gazebo to load changes; this is not automatic hot
reload. Rebuild after adding/removing files or changing package metadata,
dependencies, or entry points. Omit `--symlink-install` for a copied installation.
If switching an existing build reports a symlink/file conflict, use fresh build
and install directories rather than deleting unrelated workspace files.


In a second terminal, from the same workspace root:

```bash
source /opt/ros/lyrical/setup.bash
source install/local_setup.bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard --ros-args \
  -p stamped:=true -p frame_id:=base_link \
  -p speed:=0.05 -p turn:=0.3
```

Keep the keyboard terminal focused. Hold movement keys for continued motion;
the adapter stops motion after 0.5 seconds without a new keyboard command.
The installed ROS 2 keyboard node publishes on keypresses; it does not implement
the ROS 1 `repeat_rate` or `key_timeout` parameters. Desktop key-repeat delay
can therefore cause a brief stop when first holding a key. Shift-modified keys
enable strafing.

| Key | Action |
| --- | --- |
| `i` / `,` | Forward / backward |
| `j` / `l` | Turn left / right |
| `J` / `L` (Shift) | Strafe left / right |
| `k` | Stop |
| `q` / `z` | Increase / decrease translation and rotation settings |
| `w` / `x` | Increase / decrease translation setting |
| `e` / `c` | Increase / decrease rotation setting |

Teleop speed increases are requests, not overrides. The adapter caps forward
and sideways speed at 0.35 m/s and turning at 1.2 rad/s, matching the existing
MecanumDrive velocity caps. After 0.5 seconds without a command it publishes
zero, using a steady clock even while Gazebo is paused. This is not an E-stop:
it cannot protect against failure of the adapter, bridge, or simulator itself.
Do not connect these commands to real motors.

Launch options:

```bash
ros2 launch ugv_sim simulation.launch.py viewer:=false
ros2 launch ugv_sim simulation.launch.py x:=-5.0 y:=0.0 z:=0.05 yaw:=0.0
ros2 run rqt_image_view rqt_image_view /camera/image_raw
```

Inspect a new spawn position before driving. Camera rendering requires working
GPU/display drivers; a functioning physics simulation alone is insufficient.

## ROS Wiring

```text
teleop_twist_keyboard
  -> /cmd_vel (TwistStamped)
  -> cmd_vel_adapter (limits + timeout)
  -> /cmd_vel_gz (Twist)
  -> ros_gz_bridge -> Gazebo /model/ugv/cmd_vel -> MecanumDrive

Gazebo camera -> ros_gz_bridge -> /camera/image_raw -> rqt_image_view
                             -> /camera/camera_info
Gazebo -> /clock, /odom, /joint_states, /tf
robot_state_publisher -> robot link transforms on /tf and /tf_static
```

Robot axes are +X forward, +Y left, +Z up. Camera optical axes are +Z forward,
+X right, +Y down. `odom -> base_footprint` comes from MecanumDrive;
robot_state_publisher connects the body, wheels, and camera frames.
Drive odometry is a wheel-kinematic estimate, not proof of actual chassis
motion when contacts slip.

Useful checks:

```bash
ros2 node list
ros2 topic list -t
ros2 topic hz /camera/image_raw
ros2 topic echo /camera/camera_info --once --field header
ros2 topic echo /clock --once
ros2 topic echo /cmd_vel_gz --once
```

## Manual Terminal Workflow

These are the separate operations that the launch automates. Do not run them
alongside the integrated launch. Begin in the workspace root after building
and sourcing it as above. Each long-running command needs its own terminal.

Generate the robot directly from Xacro; no Python XML-editing helper is used:

```bash
mkdir -p tmp
ros2 run xacro xacro src/ugv_sim/urdf/ugv.urdf.xacro \
  use_cad:=true mesh_dir:="$PWD/assets/robot" -o tmp/ugv.urdf
gz sdf -p tmp/ugv.urdf > tmp/ugv.sdf
export GZ_SIM_RESOURCE_PATH="$PWD/assets${GZ_SIM_RESOURCE_PATH:+:$GZ_SIM_RESOURCE_PATH}"
gz sim -r "$PWD/src/ugv_sim/worlds/depot.sdf"
```

Spawn the generated model in another terminal, from the workspace root:

```bash
ros2 run ros_gz_sim create -world depot -file "$PWD/tmp/ugv.sdf" \
  -name ugv -x -5 -y 0 -z 0.05
```

Start the bridge and adapter, each in its own sourced terminal:

```bash
ros2 run ros_gz_bridge parameter_bridge --ros-args \
  -p config_file:="$PWD/src/ugv_sim/config/bridge.yaml"
```

```bash
ros2 run ugv_sim cmd_vel_adapter
```

Then use the keyboard and image-viewer commands above. For full robot link TF,
prefer the integrated launch, which also supplies URDF to robot_state_publisher.
Files in `tmp/` are disposable and ignored by Git. Source edits require
regeneration/respawning in this manual workflow. With a symlink installation,
edits to existing linked Xacro, world, and configuration files require a relaunch;
a copied installation also requires rebuilding. A running Gazebo model does
not read subsequent edits.

## Models And Limitations

- Xacro: `src/ugv_sim/urdf/ugv.urdf.xacro`. Detailed CAD visuals are already in
  metres; do not apply another millimetre conversion.
- The CAD tires look conventional. Mecanum behavior is approximated using
  spherical wheel collisions and diagonal anisotropic friction, with `mu=1`
  and `mu2=0`. There are no individually simulated rollers.
- Wheel radius 0.03446133 m, wheelbase 0.134780014 m, and track 0.156907572 m
  are provisional CAD-derived dimensions. Mass/inertia are estimates.
- Camera: 640x480, 15 FPS, 60-degree horizontal field of view. Mount position
  is provisional; autofocus, distortion, and physical lens calibration are
  not modeled.
- Depot is a local modified asset with `depot_mesh_collision`. In the tested
  physics path the collision appears to load the whole mesh despite selecting
  a named submesh. Coverage and performance need further verification; do not
  duplicate the same whole-mesh collision for every visual.
- Depot retains legacy fan plugins and model-level system plugins. Warnings
  should be inspected, not hidden. The launch wrapper does not rewrite assets.
- The optional old flat-world experiment is not the supported launch world.

## Troubleshooting

- **No image:** ensure Gazebo is playing. Check `gz topic -l`, then
  `gz topic -t /camera/image_raw -z`, then the ROS image rate. Gazebo topics
  existing without messages do not prove the camera is rendering. Inspect the
  bridge log and viewer subscription QoS if Gazebo has images but ROS does not.
- **Camera missing after editing:** save Xacro, rebuild, and restart/spawn the
  new model. URDF-to-SDF may warn that `gz_frame_id` is an extension; verify the
  ROS header frame is `camera_optical_frame` rather than assuming it was kept.
- **Qt cannot connect to display:** use a fresh desktop terminal, preserving
  DISPLAY/Wayland and runtime variables. A locale warning alone is not the
  same as a fatal display connection error.
- **Speed increase has no effect:** inspect adapter/plugin caps. Also check
  Gazebo real-time factor: a heavy collision mesh may slow simulated time.
- **Old launch or lidar still appears:** use the new package build, not an old
  sourced install or another workspace. The current launch has no Nav2/SLAM.
- **Missing mesh:** prepare the root `assets/` folder alongside `src/` before
  building. Assets are installed into the ROS package; regenerate/rebuild
  rather than hardcoding another user's paths.

## Tests

```bash
colcon test --packages-select ugv_sim --python-testing pytest
colcon test-result --verbose
```

Unit/structural tests cannot establish realistic dynamics. Final integration
checks are driving forward after turning, strafing, stopping after keyboard
exit, receiving the camera image, and checking warehouse contacts visually.

## TODO

- Measure and improve mecanum traction, dynamics, mass, and inertia.
- Verify whole-mesh warehouse collision coverage and performance.
- Calibrate the camera mount and lens parameters against the real robot.
- Improve launch/control ergonomics after validating the simple workflow.
- Resolve third-party asset licenses and missing attribution before publishing.
- Treat real hardware control or autonomous navigation as separate future work.

## Credits And Asset Sources

- [Waveshare Robot-Chassis](https://www.waveshare.com/wiki/Robot-Chassis):
  original chassis CAD; Motor Driver HAT models also downloaded from Waveshare's
  official site. The assembled CAD was prepared in FreeCAD.
- [Open Robotics Depot](https://app.gazebosim.org/OpenRobotics/fuel/models/Depot):
  warehouse model. Its model.config credits Rafi Abdullah and Louise Poubel.
  The local copy has simulation modifications, including collision geometry.
- [Raspberry Pi 3 Model B reference design](https://grabcad.com/library/raspberry-pi-3-model-b-reference-design-solidworks-cad-raspberry-pi-raspberrypi-rpi-1):
  source of the Raspberry Pi visual model.
- [ROS 2](https://docs.ros.org/), [Gazebo](https://gazebosim.org/), ros_gz,
  robot_state_publisher, teleop_twist_keyboard, and rqt_image_view provide
  simulation integration, transforms, controls, and viewing tools.
- [Linorobot2](https://github.com/linorobot/linorobot2) was consulted as a
  reference for simplified mecanum contact configuration.

## License

Original project code and documentation are licensed under the [MIT License](LICENSE).
Third-party assets, including Depot, Waveshare-derived models, and the Raspberry
Pi mesh, are not included and are not covered by this MIT grant.
