"""Detects objects and the user from the front and back camera images."""

import rclpy
from rclpy.node import Node


class ObjectDetectionNode(Node):
    """
    Detects objects and the user from the front and back camera images.

    Inputs:
        - Front camera image
        - Back camera image

    Outputs:
        - Detections (objects / user / stairwell) -> planning stack
    """

    def __init__(self):
        super().__init__('object_detection')
        self.get_logger().info('object_detection started')


def main(args=None):
    rclpy.init(args=args)
    node = ObjectDetectionNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
