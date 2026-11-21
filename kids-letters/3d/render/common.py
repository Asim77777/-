"""Scene setup shared by the render scripts."""
import os
import sys
import math
import importlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import bpy
from mathutils import Vector
from lib.util import reset_scene
from lib import stage

OUT = os.path.join(ROOT, 'renders')


def build(who=('noam', 'tamar'), layout=None):
    """Fresh scene with the requested characters. layout: {who: (x, y, rot_z)}."""
    scene = reset_scene()
    layout = layout or {}
    chars = {}
    for w in who:
        ch = importlib.import_module(f'characters.{w}').build()
        x, y, r = layout.get(w, (0.0, 0.0, 0.0))
        ch.place(x, y, r)
        chars[w] = ch
    stage.world_sky(scene)
    stage.courtyard(scene)
    stage.lights(scene, target=Vector((0, 0, 0.6)))
    bpy.context.view_layer.update()
    return scene, chars


def camera_orbit(scene, angle_deg, dist, height, target, lens, fstop=2.0, focus=None):
    a = math.radians(angle_deg)
    t = Vector(target)
    loc = t + Vector((math.sin(a) * dist, -math.cos(a) * dist, 0))
    loc.z = height
    return stage.camera(scene, loc, t, lens=lens, focus=focus or t, fstop=fstop)


def render_still(scene, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print('wrote', path)
