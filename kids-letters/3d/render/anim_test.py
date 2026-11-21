"""5-second rig test in the courtyard: Noam waves and laughs, Tamar blinks, says "Shalom"
(mouth shapes only, no sound yet) and points up.
Usage: python3 render/anim_test.py [samples=16] [width=540]"""
import os
import sys
import subprocess
from common import build, OUT  # imports bpy first
import bpy
from mathutils import Vector
from lib import stage, poses
from lib.face import EXPRESSIONS

samples = int(sys.argv[1]) if len(sys.argv) > 1 else 16
width = int(sys.argv[2]) if len(sys.argv) > 2 else 540
FPS, END = 24, 120

scene, chars = build(layout={'noam': (-0.29, 0.0, -10), 'tamar': (0.3, 0.05, 10)})
N, T = chars['noam'], chars['tamar']
stage.render_settings(scene, width, width * 16 // 9, samples=samples, fps=FPS)
scene.frame_start, scene.frame_end = 1, END


def blink(face, f, base):
    e = EXPRESSIONS[base]
    face.set_lids(e['upper'], e['lower'], frame=f - 2)
    face.set_lids(84, 72, frame=f)
    face.set_lids(e['upper'], e['lower'], frame=f + 3)


# ---- Noam: wave, laugh, blink
poses.apply(N, 'idle', frame=1)
f = 10
for k in range(10):
    poses.apply(N, 'wave_a' if k % 2 == 0 else 'wave_b', frame=f)
    f += 7
poses.apply(N, 'idle', frame=f + 14)
N.face.set_expression('happy', frame=1)
N.face.set_expression('happy', frame=26)
N.face.set_expression('laugh', frame=32)
N.face.set_expression('laugh', frame=56)
N.face.set_expression('happy', frame=62)
blink(N.face, 96, 'happy')

# ---- Tamar: blink, "Sha-lom", point up
poses.apply(T, 'idle', frame=1)
T.pose('head', 0, 0, 0, frame=30)
T.pose('head', 0, 6, 8, frame=44)
T.face.set_expression('happy', frame=1)
blink(T.face, 20, 'happy')
for fr, shape in ((36, 'rest'), (41, 'E'), (46, 'A'), (51, 'E'), (55, 'O'), (61, 'M'), (66, 'happy')):
    T.face.set_mouth(shape, 1.0, frame=fr)
poses.apply(T, 'idle', frame=66)
poses.apply(T, 'point_up', frame=80)
T.face.set_expression('happy', frame=80)
T.face.set_expression('surprised', frame=88)
T.face.set_expression('happy', frame=110)
blink(T.face, 104, 'happy')

# ---- camera: slow push-in
cam = stage.camera(scene, Vector((0, -4.9, 0.82)), Vector((0, 0, 0.72)), lens=64, fstop=1.6, focus=Vector((0, 0, 0.8)))
cam.keyframe_insert('location', frame=1)
cam.location = Vector((0, -4.3, 0.8))
cam.keyframe_insert('location', frame=END)

fdir = os.path.join(OUT, 'frames_anim')
os.makedirs(fdir, exist_ok=True)
scene.render.filepath = os.path.join(fdir, 'f_')
bpy.ops.render.render(animation=True)
mp4 = os.path.join(OUT, 'anim_test.mp4')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-framerate', str(FPS), '-i', os.path.join(fdir, 'f_%04d.png'),
                '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-movflags', '+faststart', mp4], check=True)
print('wrote', mp4)
