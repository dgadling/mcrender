# MCRender by David Gadling is licensed under a
#   Creative Commons Attribution-NonCommercial-ShareAlike 3.0 Unported License.
# More details available at http://creativecommons.org/licenses/by-nc-sa/3.0/

import sys
import os
import bpy
from mathutils import *

scene = bpy.context.scene

print("\nConfiguring renderer")
scene.render.resolution_x = 1920
scene.render.resolution_y = 1350
scene.render.resolution_percentage = 100    # 50 is default
scene.render.color_mode = 'RGBA'
scene.render.file_quality = 100             # 90 is defaultscene.render.
scene.render.parts_x = 128                  # 8 is default
scene.render.parts_y = 128                  # 8 is default

print("\nConfiguring camera")
########################################
# Notes for other views
########################################
#camera.location = Vector((27, -27, 30))
#camera.location = Vector((29, -27, 15))

########################################
# ORTHOGRAPHIC VIEW
########################################
camera = scene.objects["Camera"]
camera.data.type = 'ORTHO'
camera.data.ortho_scale = 35.0
camera.location = Vector((13, -13.5, 13))
camera.rotation_euler = Euler((0.9773848056793213,
                               0.0,
                               0.7853984832763672), 'XYZ')

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

print("\nRendering...")
bpy.ops.render.render()

print("\nSaving image...")
bpy.data.images['Render Result'].save_render(filepath=out_f)

print("\nCleaning up")
scene.objects.unlink(scene.objects[our_mesh])

# Just process one file, due to memory leaks
sys.exit(0)
