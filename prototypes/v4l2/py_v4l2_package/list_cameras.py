#!/usr/bin/env python
import v4l2 
import fcntl 
import os


def list_v4l2_cameras():
    for index in range(64):
        device_path = "/dev/video%d" % (index)
        if os.path.exists(device_path):
            vd = open(device_path, 'rw') 
            cp = v4l2.v4l2_capability() 
            fcntl.ioctl(vd, v4l2.VIDIOC_QUERYCAP, cp) 
            print("%s %s %s %s" % (cp.card, device_path, cp.driver, cp.bus_info))
            vd.close()


if __name__ == "__main__":
    list_v4l2_cameras()

