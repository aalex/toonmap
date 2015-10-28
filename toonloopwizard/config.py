#!/usr/bin/env python
# -*- coding: utf-8; tab-width: 4; mode: python -*-
"""
Configuration options.
"""

class Configuration(object):
    """
    Configuration options for Toonloop.
    """
    def __init__(self):
        self.project_home = "~/Documents/toonloop/default"
        self.video_source = "/dev/video0"
        self.osc_send_port = 17777
        self.width = 640
        self.height = 480
        self.verbose = False
        self.fullscreen = False

        # TODO:
        # self.fullscreen = False
        # self.enable_intervalometer = False
        # self.intervalometer_rate = 10
        # self.enable_shaders = False
        # self.enable_info_window = False
        # self.image_on_top = None
        # self.auto_save_project = False
        # self.continue_when_choose = False
        # self.enable_mouse_controls = False
        # self.osc_receive_port = 19999
        # self.osc_send_addr = "localhost"

    def __str__(self):
        """
        Returns a command to launch toonloop.
        """
        ret = "toonloop --project-home %s --video-source %s --osc-send-port %d --width %d --height %d" % (self.project_home, self.video_source, self.osc_send_port, self.width, self.height)
        if self.verbose:
            ret += " --verbose"
        if self.fullscreen:
            ret += " --fullscreen"
        return ret

