"""Build each character and save it as a .blend file (plus a .glb for other tools).
Usage: python3 save_models.py"""
import os
import sys
import importlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy
from lib.util import reset_scene
from lib import stage, poses

out_dir = os.path.join(HERE, 'models')
os.makedirs(out_dir, exist_ok=True)
for who in ('noam', 'tamar'):
    scene = reset_scene()
    ch = importlib.import_module(f'characters.{who}').build()
    poses.apply(ch, 'idle')
    ch.face.set_expression('happy')
    stage.world_sky(scene)
    stage.lights(scene)
    stage.render_settings(scene, 1080, 1920, samples=128)
    path = os.path.join(out_dir, f'{who}.blend')
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True)
    print('wrote', path, round(os.path.getsize(path) / 1e6, 1), 'MB')
    glb = os.path.join(out_dir, f'{who}.glb')
    try:
        bpy.ops.export_scene.gltf(filepath=glb, export_format='GLB', export_apply=True, export_animations=False)
        print('wrote', glb, round(os.path.getsize(glb) / 1e6, 1), 'MB')
    except Exception as e:  # the .blend is the master file; glb is a convenience copy
        print('glb export failed:', e)
