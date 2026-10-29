from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

import pytest
import xacro
import yaml


PACKAGE = Path(__file__).resolve().parents[1]


def test_world_and_bridges():
    world = ET.parse(PACKAGE / 'worlds/depot.sdf').find('world')
    assert world.get('name') == 'depot'
    assert world.findtext('include/uri') == 'model://Depot'
    bridge = yaml.safe_load((PACKAGE / 'config/bridge.yaml').read_text())
    topics = {entry['ros_topic_name'] for entry in bridge}
    assert '/scan' not in topics
    assert {'/camera/image_raw', '/camera/camera_info', '/cmd_vel_gz'} <= topics


@pytest.mark.skipif(shutil.which('gz') is None, reason='Gazebo CLI unavailable')
def test_standard_conversion_preserves_contacts_and_camera(tmp_path):
    urdf = xacro.process_file(str(PACKAGE / 'urdf/ugv.urdf.xacro')).toxml()
    source = tmp_path / 'ugv.urdf'
    source.write_text(urdf)
    result = subprocess.run(['gz', 'sdf', '-p', str(source)],
                            capture_output=True, text=True, check=True)
    # gz sdf can preserve gz: attributes without emitting their namespace declaration.
    sdf = result.stdout
    if 'xmlns:gz=' not in sdf:
        sdf = sdf.replace('<sdf ', '<sdf xmlns:gz="http://gazebosim.org/schema" ', 1)
    root = ET.fromstring(sdf)
    assert len(root.findall('.//joint')) == 4
    sensors = root.findall('.//sensor')
    assert len(sensors) == 1
    assert sensors[0].get('type') == 'camera'
    assert sensors[0].findtext('gz_frame_id') == 'camera_optical_frame'
    directions = root.findall('.//fdir1')
    assert len(directions) == 4
    assert all(d.get('{http://gazebosim.org/schema}expressed_in') == 'base_footprint'
               for d in directions)
