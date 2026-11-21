"""Full-body check render (development aid). Usage: python3 test_full.py <noam|tamar> <out.png> [angle_deg] [expr]"""
import sys, os, time, importlib, math
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from mathutils import Vector
from lib.util import reset_scene
from lib import stage

who, out = sys.argv[1], sys.argv[2]
ang = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
expr = sys.argv[4] if len(sys.argv) > 4 else 'happy'
scene = reset_scene()
ch = importlib.import_module(f'characters.{who}').build()
ch.face.set_expression(expr)
stage.render_settings(scene, 540, 960, samples=40)
stage.world_sky(scene)
stage.courtyard(scene)
stage.lights(scene, target=Vector((0, 0, 0.6)))
a = math.radians(ang)
dist = 5.2
cam = Vector((math.sin(a) * dist, -math.cos(a) * dist, 0.75))
stage.camera(scene, cam, Vector((0, 0, 0.55)), lens=85, focus=Vector((0, 0, 0.75)), fstop=1.8)
scene.render.filepath = out
t = time.time()
bpy.ops.render.render(write_still=True)
print('render', round(time.time() - t, 1), 's')
