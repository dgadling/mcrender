# MCRender by David Gadling is licensed under a
#   Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
# More details available at http://creativecommons.org/licenses/by-nc-sa/3.0/

import sys
import os
import math

import bpy
from mathutils import *

scene = bpy.context.scene

print("\nConfiguring lighting")
scene.objects.unlink(scene.objects["Lamp"])
lights = scene.world.light_settings
lights.use_ambient_occlusion = True         # def = False
#lights.samples = 10                         # def = 5

print("\nPulling Weighted Companion Cube")
scene.objects.unlink(scene.objects["Cube"])

# On Windows paths are separated with \'s
# but the rest of blender doesn't like that so much
work_dir = os.getcwd()
input_file = sys.argv[-1]

if not input_file.endswith(".obj"):
    sys.exit(1)

output_file = input_file.replace(".obj", ".png")
    
if os.path.exists(os.path.join(work_dir, output_file)):
    print("%s already done, skipping" % input_file)
    sys.exit(2)

in_f = os.path.join(work_dir, input_file)
out_f = os.path.join(work_dir, output_file)
print("\nLoading and centering %s" % input_file)

bpy.ops.import_scene.obj('EXEC_DEFAULT', filepath=in_f)
our_mesh = [k for k in scene.objects.keys() if k.startswith("Mesh")][0]
bpy.ops.object.origin_set(type='ORIGIN_GEOMETRY', center='MEDIAN')
scene.objects[our_mesh].location = Vector((0, 0, 0))

# The size of the mesh we imported is the basic dimension of many of our
# calculations later on. Store it for easier use later
base_dimension = scene.objects[our_mesh].dimensions.x

# NOTE: Most of the values below were determined experimentally. If you want
# to change them it'll probably take some trial and error.
print("\nConfiguring camera")
camera = scene.objects["Camera"]
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 2 * base_dimension
camera.location = Vector((20, -20, 29))
# NOTE: The blender GUI shows degrees by default, but this method takes radians!
camera.rotation_euler = Euler((math.pi * 45.0 / 180,
                               math.pi *  0.0 / 180,
                               math.pi * 45.0 / 180), 'XYZ')

print("\nConfiguring renderer")
# These next two settings make it such that:
# 1) A minecraft lock is always the same size, pixel wise
# 2) The output file is "wide-screen"
scene.render.resolution_x = 1.42 * 93 * base_dimension
scene.render.resolution_y = 93 * base_dimension
scene.render.resolution_percentage = 100    # 50 is default
scene.render.color_mode = 'RGBA'
scene.render.file_quality = 100             # 90 is defaultscene.render.
scene.render.parts_x = 128                  # 8 is default
scene.render.parts_y = 128                  # 8 is default

print("\nRendering...")
bpy.ops.render.render()

print("\nSaving image...")
bpy.data.images['Render Result'].save_render(filepath=out_f)

# Just process one file, due to memory leaks
sys.exit(0)
