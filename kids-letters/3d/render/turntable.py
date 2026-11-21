"""360-degree turntable of one character on a clean studio floor.
Usage: python3 render/turntable.py <noam|tamar> [frames=48] [samples=24]"""
import os
import sys
import math
import subprocess
import importlib
from common import ROOT, OUT  # imports bpy first
import bpy
from mathutils import Vector
from lib.util import reset_scene, hex2lin
from lib import stage, poses, materials as M

who = sys.argv[1]
frames = int(sys.argv[2]) if len(sys.argv) > 2 else 48
samples = int(sys.argv[3]) if len(sys.argv) > 3 else 24

scene = reset_scene()
ch = importlib.import_module(f'characters.{who}').build()
poses.apply(ch, 'idle')
ch.face.set_expression('happy')
stage.world_sky(scene, horizon='#F4D7B8', zenith='#BFD3EA', strength=0.7)
floor = bpy.data.meshes.new('Floor')
floor.from_pydata([(-6, -6, 0), (6, -6, 0), (6, 6, 0), (-6, 6, 0)], [], [(0, 1, 2, 3)])
fo = bpy.data.objects.new('Floor', floor)
scene.collection.objects.link(fo)
floor.materials.append(M.plain('StudioFloor', '#EAD9C4', rough=0.8))
stage.lights(scene, target=Vector((0, 0, 0.6)))
stage.render_settings(scene, 540, 960, samples=samples, fps=12)
stage.camera(scene, Vector((0, -4.4, 0.72)), Vector((0, 0, 0.6)), lens=70, fstop=4.0, focus=Vector((0, 0, 0.75)))

bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
scene.frame_start, scene.frame_end = 1, frames
ch.arm.rotation_euler = (0, 0, 0)
ch.arm.keyframe_insert('rotation_euler', index=2, frame=1)
ch.arm.rotation_euler = (0, 0, math.radians(360 * frames / (frames - 0)))
ch.arm.keyframe_insert('rotation_euler', index=2, frame=frames + 1)

fdir = os.path.join(OUT, f'frames_turn_{who}')
os.makedirs(fdir, exist_ok=True)
scene.render.filepath = os.path.join(fdir, 'f_')
bpy.ops.render.render(animation=True)
mp4 = os.path.join(OUT, f'{who}_turntable.mp4')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', '12', '-i', os.path.join(fdir, 'f_%04d.png'),
                '-vf', 'fps=24', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-movflags', '+faststart', mp4], check=True)
print('wrote', mp4)
