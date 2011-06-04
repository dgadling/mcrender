About
=====

This app is meant to do one thing pretty decently: turn Minecraft
backups/snapshots into nicely rendered PNGs. My personal plan is to use these
frames to make a timelapse video of construction over time.

It does this using mcobj (https://github.com/quag/mcobj) and Blender (http://www.blender.org/)

Requirements
------------
1. blender in your PATH
2. mcobj in your PATH
3.  Python 2.[567] (http://python.org); might work in Python3, not tested.

Installation / Running
----------------------
This runs perfectly well under Windows and should have no issues in Linux/OS X!

You'll need to copy example.ini to config.ini, and then change it as appropriate.
If you don't the app will yell at you.

You also need to have mcobj and blender in your PATH.

obj2png.py is supplied as an example Blender script. Obviously you should tweak
this to your taste, or replace it entirely if you know what you're doing.

Bugs / Limitations / Known Issues
---------------------------------
* Runs "mcobj.exe" this needs to be smarter or I need a new version of mcobj
* For some reason the renders don't come out centered; figure it out and fix it
* Add support for Gallery3
* Expand obj2png.py to take a size parameter and move the camera around appropriately
