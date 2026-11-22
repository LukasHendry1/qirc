"""
Save the map slam_toolbox is building, so later runs can localize in it.

    ros2 run qirc_localization save_map                  # ~/qirc_maps/house
    ros2 run qirc_localization save_map ~/qirc_maps/lab

Run it while mapping.launch.py is running. It writes four files, all
starting with the given path:

    <map>.posegraph, <map>.data   slam_toolbox's pose graph, which
                                  localization.launch.py loads
    <map>.pgm, <map>.yaml         the occupancy grid as an image, for
                                  Nav2's map_server (#59)
"""

import argparse
from pathlib import Path
import sys

import rclpy
from rclpy.node import Node
from slam_toolbox.srv import SaveMap, SerializePoseGraph
from std_msgs.msg import String

# Also the default map in launch/localization.launch.py.
DEFAULT_MAP = '~/qirc_maps/house'

SERVICE_TIMEOUT = 10.0      # s to wait for slam_toolbox to be running
CALL_TIMEOUT = 60.0         # s; serializing a large map takes a while


def map_path(name):
    """
    Return the map's absolute path without an extension.

    slam_toolbox runs in another directory, so a relative path would be
    saved relative to it.
    """
    path = Path(name).expanduser().resolve()
    if path.suffix in ('.posegraph', '.data', '.pgm', '.yaml'):
        path = path.with_suffix('')
    return path


def _call(node, service_type, name, request):
    client = node.create_client(service_type, name)
    if not client.wait_for_service(timeout_sec=SERVICE_TIMEOUT):
        raise RuntimeError(f'{name} is not available: is mapping.launch.py running?')
    future = client.call_async(request)
    rclpy.spin_until_future_complete(node, future, timeout_sec=CALL_TIMEOUT)
    if future.result() is None:
        raise RuntimeError(f'{name} did not answer within {CALL_TIMEOUT:.0f} s')
    return future.result().result


def save(node, path):
    """Save the pose graph and the occupancy grid; raise if either fails."""
    path.parent.mkdir(parents=True, exist_ok=True)

    result = _call(node, SerializePoseGraph, '/slam_toolbox/serialize_map',
                   SerializePoseGraph.Request(filename=str(path)))
    if result != SerializePoseGraph.Response.RESULT_SUCCESS:
        raise RuntimeError(f'slam_toolbox could not write {path}.posegraph')

    result = _call(node, SaveMap, '/slam_toolbox/save_map',
                   SaveMap.Request(name=String(data=str(path))))
    if result != SaveMap.Response.RESULT_SUCCESS:
        raise RuntimeError(f'slam_toolbox could not save {path}.pgm (result {result})')

    missing = [p.name for p in (path.with_suffix(s) for s in
               ('.posegraph', '.data', '.pgm', '.yaml')) if not p.exists()]
    if missing:
        raise RuntimeError(f'missing after saving: {", ".join(missing)}')


def main(args=None):
    rclpy.init(args=args)
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0].strip())
    parser.add_argument('map', nargs='?', default=DEFAULT_MAP,
                        help=f'path without extension (default {DEFAULT_MAP})')
    options = parser.parse_args(rclpy.utilities.remove_ros_args(sys.argv)[1:])

    node = Node('save_map')
    path = map_path(options.map)
    try:
        save(node, path)
        node.get_logger().info(f'saved {path}.{{posegraph,data,pgm,yaml}}')
    except RuntimeError as error:
        node.get_logger().error(str(error))
        sys.exit(1)
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
