#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Scenic
# Copyright (C) 2008 Société des arts technologiques (SAT)
# http://www.sat.qc.ca
# All rights reserved.
#
# This file is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Scenic is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Scenic. If not, see <http://www.gnu.org/licenses/>.
"""
Tools to lists available cameras.

Uses milhouse --list-v4l2
"""
import os
import pprint
import re
from twisted.internet import utils
from twisted.internet import defer
from twisted.python import procutils
from twisted.internet import reactor
#  oups... we should not have to use it... see _parse_milhouse_sdi_cameras())
import subprocess

from scenic import logger
log = logger.start(name="cameras")

ugly_to_beautiful_camera_names = {
    "BT878 video (Osprey 210/220/230": "Osprey 210/220/230",
    "BT878 video (Osprey 100/150 (87": "Osprey 100/150",
    "BT878 video (Hauppauge (bt878))": "Hauppauge WinTV",
    }

def _beautify_camera_name(name):
    """
    Renames a camera with a better name if it's in our list of know camera names.

    @rtype: str
    @type name: str
    """
    global ugly_to_beautiful_camera_names
    if name in ugly_to_beautiful_camera_names.keys():
        return ugly_to_beautiful_camera_names[name]
    elif name.startswith("UVC Camera"):
        return "USB %s" % (name[4:]) # we replace UVC by USB
    else:
        return name

# TODO: Simplify to eliminate redundancy in code (parsing v4l and dc cameras) and clean up
def _parse_milhouse_v4l2_cameras(text):
    """
    Parses the output of `milhouse --list-v4l2`
    Returns a dict of dict with keys "name", "size", "standard", "is_interlaced", "input", "inputs", "supported_sizes"
    For now, considers only V4L2 cameras.
    @rtype: list
    """
    v4l2_devices = {}
    currently_parsed_is_v4l2 = False
    current_v4l2_device = None
    for line in text.splitlines():
        line = line.strip()
        #print(line)
        if line.startswith('Video4Linux Camera'):
            name = line.split()[2].split(":")[0]
            current_v4l2_device = name
            #print "  name", name
            v4l2_devices[name] = {
                "name": name, # /dev/video0
                "size": None,
                "standard": None,
                "is_interlaced": False,
                "input": None, # int
                "card": "", # Osprey 110
                "inputs": [], # list of inputs
                "supported_sizes": []
                }
            currently_parsed_is_v4l2 = True
        elif line.startswith("DCI1394") or line.startswith("DeckLink") or line.startswith("DV1394"):
            currently_parsed_is_v4l2 = False
#            dc_cameras = _parse_milhouse_dc_cameras(text)
        # TODO: know if currently parsed is a V4L 1
        elif currently_parsed_is_v4l2:
            try:
                value = line.split(":")[1].strip()
            except IndexError:
                value = None
            if line.startswith("Standard"):
                try:
                    standard = line.split(":")[1].strip()
                except IndexError:
                    standard = None
                else:
                    if standard == '':
                        standard = None
                    v4l2_devices[current_v4l2_device]["standard"] = standard
                    #print "  standard:", standard
            elif line.startswith("Width/Height"):
                size = value
                v4l2_devices[current_v4l2_device]["size"] = size
                # sometimes the size listed in Width/Height is not listed in Format
                v4l2_devices[current_v4l2_device]["supported_sizes"].append(size)
                #print "  size:", size
            elif line.startswith("Format"):
                size = line.split(" ")[1]
                v4l2_devices[current_v4l2_device]["supported_sizes"].append(size)
                #print "  adding supported_size:", size
            elif line.startswith("Field"):
                is_interlaced = value == "Interlaced"
                v4l2_devices[current_v4l2_device]["is_interlaced"] = is_interlaced
                #print "  interlaced:", is_interlaced
            elif line.startswith("Card type"):
                card = _beautify_camera_name(value)
                v4l2_devices[current_v4l2_device]["card"] = card
                #print "  card:", card
            elif line.startswith("Video input"):
                try:
                    _input = value.split(" ")[0]
                except IndexError:
                    _input = None
                else:
                    # now, let's try to get an int out of it:
                    try:
                        log.debug(_input)
                        _input = int(_input)
                    except ValueError, e:
                        log.error(e)
                        _input = None
                    except TypeError, e:
                        log.error(e)
                        _input = None
                    else:
                        #print "  input", input
                        v4l2_devices[current_v4l2_device]["input"] = _input
            elif line.startswith("All inputs"):
                for each in value.split(","):
                    tokens = each.strip().split(" ")
                    try:
                        #num = tokens[0]
                        name = tokens[1].replace("(", "").replace(")", "")
                    except IndexError:
                        pass
                    else:
                        # actually, we assume their number is sequential, starting at 0
                        v4l2_devices[current_v4l2_device]["inputs"].append(name)
    # append Other size for manual input size configuration
    #v4l2_devices[current_v4l2_device]["supported_sizes"].append("Custom...")
    #print v4l2_devices
    return v4l2_devices

# TODO: generalize to include DV cameras(?)
# TODO: prepare lists of frame sizes (if such can actually be useful)
def _parse_milhouse_dc_cameras(text):
    dc_devices = {}
    sizes = []
    pmodes = []
    frame_rates = []
    guid = None
    current_dc_device = None
    currently_parsed_is_dc = False
    for line in text.splitlines():
        line = line.strip()
        #print(line)
        if line.startswith("DC1394 Camera"):
            card = " ".join(line.split()[3:])
            name = " ".join(line.split()[1:3])
            current_dc_device = name
            dc_devices[name] = {
                "name" : name,
                "card" : card,
                "sizes" : [],
                "pmodes" : [],
                "GUID" : guid,
                "supported_sizes" : [],
                "frame_rates" : [],
            }
            currently_parsed_is_dc = True
        elif  line.startswith("Video4Linux") or line.startswith("DeckLink") or line.startswith("DV1394"):
            currently_parsed_is_dc = False
        elif line.startswith("GUID"):
            log.debug("found GUID line")
            dc_devices[name]["GUID"] = _parse_guid(line)
            log.debug("GUID is: %s" % (dc_devices[name]["GUID"]))
        elif currently_parsed_is_dc:
            mode = _parse_dc_vmodes(line)
            log.debug("Mode parsed: %s" % (mode))
            if mode:
                sizes.append(mode[0])
                pmodes.append(mode[1])
            rates = _parse_dc_framerates(line)
            if rates:
                frame_rates.append(rates)
            dc_devices[current_dc_device]["sizes"] = sizes
            dc_devices[current_dc_device]["pmodes"] = pmodes
            dc_devices[current_dc_device]["frame_rates"] = frame_rates
    # append Other size for manual input size configuration
    #dc_devices[current_dc_device]["supported_sizes"].append("Custom...")
    return dc_devices

def _parse_milhouse_dv_cameras(text):
    """
    Provides basic support for DC cameras. Currently milhouse can handle only the first DV camera so we ignore all info that could identify a camera
    """
    dv_devices = {}
    card = None
    sizes = ["640x480", "768x480", "320x240"]
    currently_parsed_is_dv = False
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("DV1394"):
            card = line.split()[0]
            currently_parsed_is_dv = True
        if currently_parsed_is_dv:
            if "GUID" in line:
                # we assume that this is a DV camera (milhouse tends to format them this way)
                name = line.split(":")[0]
                dv_devices[name] = {
                    "name" : name,
                    "card" : card,
                    "size" : "768x480",
                    "supported_sizes" : sizes,
                }
        elif line.startswith("Video4Linux") or line.startswith("DeckLink") or line.startswith("DC1394"):
            currently_parsed_is_dv = False
    return dv_devices

def _parse_milhouse_sdi_cameras():
    """
    Parse info on DeckLink interface. Currently info comes from milhouse-listdecklink executable and has
    been tested on SDI interface.
    """
    # FIXME: rather than launching this process, integrate the behaviour into list_cameras() using Deferreds etc.
    out = None
    text = None
    try:
        out = subprocess.Popen("milhouse-listdecklink", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        text = out.stdout.read()
        err = out.stderr.read()
    except OSError:
        pass
    # do not even run this function if outout form the above command is empty or error occures.
    # Error is sure to happen if DeckLink drivers/libraries are not present, which will be the case if user
    # has no such interface.
    if text == None or err == None:
        return None
    if len(text) < 1 or "cannot open" in err:
        return None
    else:
        sdi_devices = {}
        inputs = None
        modes = []
        current_sdi_device = None
        currently_parsed_is_sdi = False
        for line in text.splitlines():
            line = line.strip()
            #print(line)
            if line.startswith("DeckLink"):
                card = " ".join(line.split()[3:])
                name = "".join(line.split()[2:])
                current_sdi_device = name
                sdi_devices[name] = {
                    "name" : name,
                    "input": None,
                    "inputs": [],
                    "card" : card,
                    "modes" : [],
                    "supported_sizes" : [],
                    "frame_rates" : [],
                }
                currently_parsed_is_sdi = True
            elif line.startswith("Video4Linux") or line.startswith("DC1394") or line.startswith("DV1394"):
                currently_parsed_is_sdi = False
            elif currently_parsed_is_sdi:
                mode = _parse_sdi_modes(line)
                connection = _parse_sdi_connections(line)
                if mode:
                    modes.append(mode)
                if connection:
                    inputs = connection
                # parse the sizes and remove index numbers
                #_sizes = [x.split(":")[1] for x in modes]
                sdi_devices[current_sdi_device]["modes"] = modes
                sdi_devices[current_sdi_device]["modes"] = _sdi_mode_append_res(sdi_devices[current_sdi_device])
                sdi_devices[current_sdi_device]["supported_sizes"] = _sdi_supported_sizes(sdi_devices[current_sdi_device])
                sdi_devices[current_sdi_device]["inputs"] = inputs
        # let's assign a default input
        log.debug(" ==== SDI inputs:")
        log.debug(sdi_devices[current_sdi_device]["inputs"])
        if len(sdi_devices[current_sdi_device]["inputs"]) > 0:
            _input = 0
            sdi_devices[current_sdi_device]["input"] = _input
        # append Other size for manual input size configuration
        #sdi_devices[current_sdi_device]["supported_sizes"].append("Custom...")
        return sdi_devices

def _sdi_mode_append_res(device):
    modes = []
    for mode in device["modes"]:
        if "(ntsc-p)" in mode:
            modes.append(mode + " (1920x1080)")
        elif "(pal-p)" in mode:
            modes.append(mode + " (1920x1080)")
        elif "HD1080" in mode:
            modes.append(mode + " (1920x1080)")
        elif "HD1080" in mode:
            modes.append(mode + " (1920x1080)")
        elif "HD720" in mode:
            modes.append(mode + " (1280x720)")
        else:
            modes.append(mode + " (720x486)")
    return modes

def _parse_sdi_modes(line):
    """
    Parses lines from milhouse output and returns those which contain
    certain keywords
    """
    if "HD" in line:
        if "HDMI" in line:
            return False
        else:
            return line
    elif "PAL" in line:
        return line
    if "NTSC" in line:
        return line
    else:
        return False
        
def _sdi_supported_sizes(device):
    """
    Map HD formats to sizes in pixels
    """
    _sizes = []
    for mode in device["modes"]:
        if "(ntsc-p)" in mode:
            _sizes.append("1920x1080")
        elif "(pal-p)" in mode:
            _sizes.append("1920x1080")
        elif "HD1080" in mode:
            _sizes.append("1920x1080")
        elif "HD1080" in mode:
            _sizes.append("1920x1080")
        elif "HD720" in mode:
            _sizes.append("1280x720")
        else:
            _sizes.append("720x486")
    return _sizes
    
def _parse_sdi_connections(line):
    """
    Parses lines from milhouse output and returns those which contain
    certain keywords
    """
    inputs = None
    # COnnections line looks like this: "Detected video input(s): SDI"
    if line.startswith("Detected video"):
        # Parse the stuff after ":"
        s = line.split(":")[1:]
        # split it at commas
        l = s[0].split(",")
        # finally, split each item in list by removing the prefixed space
        inputs = [x.split(" ")[1] for x in l]
        return inputs
    else:
        return False
    
def _parse_guid(line):
    """
    Parse the GUID of the firewire camera
    """
    guid = line.split("=")[-1].split()
    return guid

def _parse_dc_vmodes(line):
    """
    Parse video modes
    i.e. 640x480_MONO8 (vmode 69)
    """
    # TODO: do we need to know the vmode number actually?
    # anyways, let's extract the resolution and pixel format
    # regex: 4 spaces (3 digits)x(3 digits)_(2-4 letters)(1-3 digits)
    vformat = re.compile(r"^\s{4}([0-9]{3}x[0-9]{3})_([A-Z]{2,4}[0-9]{1,3})")
    result = vformat.match(line)
    log.debug("Parsed mode line : %s" % (line))
    # we get tuples of resolution, pixel format
    if result:
        return result.groups()
    else:
        return None

def _parse_dc_framerates(line):
    """
    parse framerates
    i.e. Framerates: 3.75,7.5,15.30
    """
    _framerates = re.compile("Framerates")
    result = _framerates.search(line)
    if result:
        frates_as_string = line.split()[1]
        frates = frates_as_string.split(",")
        return frates
    else:
        return None

def list_cameras():
    """
    Calls the Deferred with the dict of devices as argument.

    @rtype: Deferred
    """
    def _cb(text, deferred):
        #print text
        v4l_cameras = _parse_milhouse_v4l2_cameras(text)
        #log.debug("*** v4l cameras: %s" % (v4l_cameras))
        dc_cameras = _parse_milhouse_dc_cameras(text)
        #log.debug("*** dc cameras: %s" % (dc_cameras))
        sdi_cameras = _parse_milhouse_sdi_cameras()
        #log.debug("*** sdi cameras: %s" % (sdi_cameras))
        dv_cameras = _parse_milhouse_dv_cameras(text)
        if sdi_cameras is not None:
            all_cameras = dict(v4l_cameras.items() + dc_cameras.items() + sdi_cameras.items() + dv_cameras.items())
        else:
            all_cameras = dict(v4l_cameras.items() + dc_cameras.items() + dv_cameras.items())
        #log.debug("*** all cameras: %s" % (all_cameras))
        deferred.callback(all_cameras)

    def _eb(reason, deferred):
        deferred.errback(reason)
        print("Error listing cameras: %s" % (reason))

    command_name = "milhouse"
    args = ['--list-cameras']
    try:
        executable = procutils.which(command_name)[0] # gets the executable
    except IndexError:
        return defer.fail(RuntimeError("Could not find command %s" % (command_name)))
    deferred = defer.Deferred()
    d = utils.getProcessOutput(executable, args=args, env=os.environ, errortoo=True) # errortoo puts stderr in output
    d.addCallback(_cb, deferred)
    d.addErrback(_eb, deferred)
    return deferred

#if __name__ == "__main__":
#    def _go():
#        def _cb(result):
#            reactor.stop()
#        def _eb(reason):
#            print(reason)
#            return None
#        d = list_cameras()
#        d.addCallback(_cb)
#
#    reactor.callLater(0, _go)
#    reactor.run()

TESTDATA = """Ver:0.3.6
INFO:Built on Feb 10 2010 at 10:17:35

DC1394 Camera 0: Unibrain Fire-i 1.2
GUID = 814436102630ee6
Supported modes :
    640x480_MONO8 (vmode 69)
    Framerates: 3.75,7.5,15,30
    640x480_RGB8 (vmode 68)
    Framerates: 3.75,7.5,15
    640x480_YUV422 (vmode 67)
    Framerates: 3.75,7.5,15
    640x480_YUV411 (vmode 66)
    Framerates: 3.75,7.5,15,30
    320x240_YUV422 (vmode 65)
    Framerates: 3.75,7.5,15,30
    160x120_YUV444 (vmode 64)
    Framerates: 7.5,15,30

Video4Linux Camera /dev/video1:
    Driver name   :
    Card type     :
    Bus info      :
    Driver version: 0
    Video input   :
    Standard      :
    Width/Height  : 0x0
    Pixel Format  :
    Capture Type  : 1
    Field         : Any
    Bytes per Line: 0
    Size Image    : 0
    Colorspace    : Unknown (00000000)
    Format 924x576 not supported
    Format 768x480 not supported
    Format 720x480 not supported
    Format 704x480 not supported
    Format 704x240 not supported
    Format 640x480 not supported
    Format 352x240 not supported
    Format 320x240 not supported
    Format 176x120 not supported
WARNING:Format 0x-1222839056not reverted correctly

Video4Linux Camera /dev/video0:
    Driver name   : bttv
    Card type     : BT878 video (Osprey 210/220/230
    Bus info      : PCI:0000:05:00.0
    Driver version: 2321
    Video input   : 0 (Composite0)
    Standard      : PAL
    Width/Height  : 640x480
    Pixel Format  : BGR3
    Capture Type  : 1
    Field         : Interlaced
    Bytes per Line: 1920
    Size Image    : 921600
    Colorspace    : Unknown (00000000)
    Format 924x576 supported
    Format 768x480 supported
    Format 720x480 supported
    Format 704x480 supported
    Format 704x240 supported
    Format 640x480 supported
    Format 352x240 supported
    Format 320x240 supported
    Format 176x120 supported

DV1394 devices:
    Canon ZR960 ZR960 ZR960: GUID 0x3404830684809

DeckLink card DeckLink SDI
    Number of sub-devices: 1
    Sub-device index: 0
    Detected video input(s): SDI
    Milhouse supported modes: 
    0: NTSC SD 60i (ntsc)
    1: NTSC SD 60i (24 fps) (ntsc2398)
    2: PAL SD 50i (pal)
    3: NTSC SD 60p (ntsc-p)
    4: PAL SD 50p (pal-p)
    5: HD1080 23.98p (1080p2398)
    6: HD1080 24p (1080p24)
    7: HD1080 25p (1080p25)
    8: HD1080 29.97p (1080p2997)
    9: HD1080 30p (1080p30)
    10: HD1080 50i (1080i50)
    11: HD1080 59.94i (1080i5994)
    12: HD1080 60i (1080i60)
    13: HD1080 50p (1080p50)
    14: HD1080 59.94p (1080p5994)
    15: HD1080 60p (1080p60)
    16: HD720 50p (720p50)
    17: HD720 59.94p (720p5994)
    18: HD720 60p (720p60)
    Milhouse supported inputs: 
    0: SDI (sdi)
    1: HDMI (hdmi)
    2: Optical SDI (optical-sdi)
    3: Component (component)
    4: Composite (composite)
    5: S-Video (svideo)

Exitting Milhouse
"""

def set_v4l2_input_number(device_name="/dev/video0", input_number=0):
    """
    Sets input number for a V4L2 device.
    @rtype: Deferred
    """
    command_name = "milhouse"
    args = ['--v4l2-input', str(input_number), '--videodevice', device_name]
    try:
        executable = procutils.which(command_name)[0]
    except IndexError:
        return defer.fail(RuntimeError("Could not find command %s" % (command_name)))
    deferred = utils.getProcessOutput(executable, args=args, env=os.environ)
    return deferred

def set_v4l2_video_standard(device_name="/dev/video0", standard="ntsc"):
    """
    Sets norm for a V4L2 device.
    @rtype: Deferred
    """
    command_name = "milhouse"
    args = ['--v4l2-standard', standard, '--videodevice', device_name]
    try:
        executable = procutils.which(command_name)[0]
    except IndexError:
        return defer.fail(RuntimeError("Could not find command %s" % (command_name)))
    deferred = utils.getProcessOutput(executable, args=args, env=os.environ)
    return deferred

if __name__ == "__main__":
    pprint.pprint(_parse_milhouse_v4l2_cameras(TESTDATA))
    pprint.pprint(_parse_milhouse_dc_cameras(TESTDATA))
    pprint.pprint(_parse_milhouse_sdi_cameras(TESTDATA))
    pprint.pprint(_parse_milhouse_dv_cameras(TESTDATA))
