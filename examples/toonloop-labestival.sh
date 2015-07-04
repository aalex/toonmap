#!/bin/bash
FOLDER=/media/toonloop/ELBY_2_FAT/toonloop/project
WIDTH=1280
HEIGHT=720
CAMERA=/dev/video1

toonloop -d ${CAMERA} --width ${WIDTH} --height ${HEIGHT} --project-home=$FOLDER --fullscreen

