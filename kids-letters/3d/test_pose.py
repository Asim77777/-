"""Pose test (development aid): python3 test_pose.py <who> <out.png> bone:x,y,z [bone:x,y,z ...]"""
import sys, os, time, importlib, math
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from mathutils import Vector
from lib.util import reset_scene
from lib import stage
who, out = sys.argv[1], sys.argv[2]
scene = reset_scene()
ch = importlib.import_module(f'characters.{who}').build()
from lib import poses
for spec in sys.argv[3:]:
    if ':' not in spec:
        if spec in poses.POSES:
            poses.apply(ch, spec)
        else:
            ch.face.set_expression(spec)
        continue
    b, v = spec.split(':')
    x, y, z = (float(t) for t in v.split(','))
    ch.pose(b, x, y, z)
stage.render_settings(scene, 432, 640, samples=16)
stage.world_sky(scene)
stage.lights(scene, target=Vector((0, 0, 0.6)))
stage.camera(scene, Vector((0, -3.2, 0.65)), Vector((0, 0, 0.62)), lens=60, fstop=16)
scene.render.filepath = out
bpy.ops.render.render(write_still=True)
