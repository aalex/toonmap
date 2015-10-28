#!/usr/bin/env python
"""
Lists V4L2 cameras by looking at the Linux file system.
"""
import os

class Camera(object):
    """
    Represents a V4L2 device.
    """
    def __init__(self):
        self.name = ""
        self.device = ""
        self.index = 0

    def __str__(self):
        return "%s (%s)" % (self.name, self.device)


def list_v4l2_cameras():
    """
    Lists V4L2 cameras by looking at the Linux file system.
    """
    ret = []
    # V4L2 documentation says that there can be 64 allowed devices for each type.
    for index in range(64):
        device_path = "/dev/video%d" % (index)
        if os.path.exists(device_path):
            name = ""
            name_file_path = "/sys/class/video4linux/video%d/name" % (index)
            if os.path.exists(name_file_path):
                with open(name_file_path, "r") as name_file:
                    name = name_file.read().replace('\n', '')
            camera = Camera()
            camera.name = name
            camera.device = device_path
            camera.index = index
            ret.append(camera)
    return ret


if __name__ == "__main__":
    cameras = list_v4l2_cameras()
    for camera in cameras:
        print("%s" % (camera))

