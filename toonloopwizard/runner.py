#!/usr/bin/env python
# -*- coding: utf-8; tab-width: 4; mode: python -*-
"""
Main entry point of the program.
"""
# from twisted.internet import gtk3reactor
# gtk3reactor.install()
# from twisted.internet import reactor

from toonloopwizard import gui
from toonloopwizard import config
from toonloopwizard import __version__
import optparse
import os
import sys
import subprocess


def run():
    """
    Main entry point of the program.
    """
    parser = optparse.OptionParser(usage="%prog", version=str(__version__))
    parser.add_option("-d", "--video-source", type="string", help="The default video source.")
    parser.add_option("-H", "--project-home", type="string", help="Toonloop project directory.")
    parser.add_option("-v", "--verbose", action="store_true", help="Makes the logging output verbose.")
    parser.add_option("-f", "--fullscreen", action="store_true", help="Makes the window full screen.")
    (options, args) = parser.parse_args()

    configuration = config.Configuration()

    # video source
    if options.video_source:
        configuration.video_source = options.video_source

    # project home
    if options.video_source:
        configuration.video_source = options.video_source

    # verbose
    if options.verbose:
        configuration.verbose = True

    # fullscreen
    if options.fullscreen:
        configuration.fullscreen = True

    configuration = gui.show_window_and_update_config(configuration)

    print(configuration)
    # Run Toonloop
    command = str(configuration)
    process = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
    process.wait()
    print(process.returncode)
