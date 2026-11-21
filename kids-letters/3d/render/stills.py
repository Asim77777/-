"""Hero stills and expression close-ups.
Usage: python3 render/stills.py [hero|pair|expressions|all] [samples]"""
import sys
import os
import time
from common import build, camera_orbit, render_still, OUT  # imports bpy first
from mathutils import Vector
from lib import stage, poses

what = sys.argv[1] if len(sys.argv) > 1 else 'all'
samples = int(sys.argv[2]) if len(sys.argv) > 2 else 128
t0 = time.time()

if what in ('hero', 'all'):
    for who, ang, pose, expr in (('noam', 22, 'wave_a', 'happy'), ('tamar', -22, 'point_up', 'happy')):
        scene, chars = build((who,))
        ch = chars[who]
        poses.apply(ch, pose)
        ch.face.set_expression(expr)
        stage.render_settings(scene, 1080, 1920, samples=samples)
        camera_orbit(scene, ang, 4.6, 0.78, (0, 0, 0.62), lens=72, fstop=1.4, focus=Vector((0, 0, 0.8)))
        render_still(scene, os.path.join(OUT, f'{who}_hero.png'))
        # plain front view, arms down, for the model sheet
        poses.apply(ch, 'idle')
        ch.face.set_expression('happy')
        camera_orbit(scene, 0, 4.6, 0.7, (0, 0, 0.6), lens=72, fstop=1.4, focus=Vector((0, 0, 0.8)))
        render_still(scene, os.path.join(OUT, f'{who}_front.png'))

if what in ('pair', 'all'):
    scene, chars = build(layout={'noam': (-0.29, 0.0, -10), 'tamar': (0.3, 0.05, 10)})
    poses.apply(chars['noam'], 'wave_a')
    chars['noam'].face.set_expression('laugh')
    poses.apply(chars['tamar'], 'point_up')
    chars['tamar'].face.set_expression('happy')
    stage.render_settings(scene, 1080, 1920, samples=samples)
    camera_orbit(scene, 0, 4.5, 0.8, (0, 0, 0.72), lens=64, fstop=1.4, focus=Vector((0, 0, 0.8)))
    render_still(scene, os.path.join(OUT, 'pair.png'))

if what in ('expressions', 'all'):
    for who in ('noam', 'tamar'):
        scene, chars = build((who,))
        ch = chars[who]
        poses.apply(ch, 'idle')
        stage.render_settings(scene, 800, 800, samples=max(32, samples // 2))
        hc = ch.head.matrix_world.translation
        for expr in ('happy', 'surprised', 'laugh'):
            ch.face.set_expression(expr)
            stage.camera(scene, hc + Vector((0.3, -1.6, 0.06)), hc + Vector((0, 0, 0.0)), lens=85, fstop=2.8)
            render_still(scene, os.path.join(OUT, f'{who}_{expr}.png'))

print('done in', round(time.time() - t0), 's')
