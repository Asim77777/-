"""Quick look at a character head (development aid). Usage: python3 test_head.py <noam|tamar> <out.png>"""
import sys, os, time, importlib
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from mathutils import Vector
from lib.util import reset_scene
from lib import stage

who, out = sys.argv[1], sys.argv[2]
expr = sys.argv[3] if len(sys.argv) > 3 else 'happy'
scene = reset_scene()
mod = importlib.import_module(f'characters.{who}')
ch = mod.build(head_only=True)
ch.face.set_expression(expr)
stage.render_settings(scene, 640, 800, samples=48)
stage.world_sky(scene)
c = ch.head.matrix_world.translation
stage.lights(scene, target=c)
stage.camera(scene, c + Vector((0.25, -1.35, 0.05)), c + Vector((0, 0, 0.01)), lens=85, fstop=4)
scene.render.filepath = out
t = time.time()
bpy.ops.render.render(write_still=True)
print('render', round(time.time() - t, 1), 's')
