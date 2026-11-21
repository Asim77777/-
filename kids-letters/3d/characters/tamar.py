"""Tamar: two puffy pigtails with yellow ties, side-swept bangs, pink striped shirt,
yellow overalls with a heart, purple sneakers. Colors follow the 2D design (option1.js)."""
import math
import bmesh
import bpy
from mathutils import Vector

from lib.body import Character, torso, limbs, hands, shoes
from lib.parts import ellipsoid, capsule, torus, shell, lumpy
from lib.hair import lock
from lib.face import Face
from lib import materials as M
from lib.util import smoothstep, obj_from_bmesh, ray_to_surface

COLORS = dict(skin='#C68A60', cheek='#E8746A', hair='#2B1B14', tie='#FFC93C', shirt='#FF6F91', stripe='#FFE3EA',
              overall='#FFC22E', overall_d='#E3A20C', shoe='#8E5BD9', iris='#6A3D22', iris_d='#2E180C')

S = dict(hip_z=0.44, waist_z=0.52, neck_z=0.72, head_z=0.9, shoulder_z=0.69, shoulder_x=0.125,
         upper_arm=0.16, fore_arm=0.145, arm_r=0.043, arm_angle=15, hand_r=0.041,
         leg_x=0.068, knee_z=0.255, ankle_z=0.095, leg_r=0.054, torso_w=0.155, torso_depth=0.74)

K = 1.1
FACE = dict(eye_r=0.04, eye_dx=0.058, eye_z=0.006, eye_sink=0.6, eye_out=7, lashes=True,
            nose_z=-0.038, nose_r=0.0145, mouth_z=-0.077, mouth_scale=1.05,
            brow_z=0.056, brow_w=0.0045, ear_z=-0.005, ear_r=0.033, ear_y=0.01)
FACE = {k: (v * K if isinstance(v, float) and k not in ('eye_sink', 'eye_out') else v) for k, v in FACE.items()}
HEAD_R = tuple(r * K for r in (0.162, 0.152, 0.156))


def _cheeks(d):
    f = smoothstep(0.0, 0.8, -d.z)
    front = smoothstep(0.2, 0.9, -d.y)
    return Vector((1 + 0.04 * f, 1 + 0.03 * f * front, 1 - 0.04 * f))


def _heart(name, col, mat, size):
    bm = bmesh.new()
    pts = []
    for i in range(48):
        t = 2 * math.pi * i / 48
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append(bm.verts.new((x / 34 * size, 0, (y + 2) / 34 * size)))
    bm.faces.new(pts)
    ob = obj_from_bmesh(name, bm, col, mat, smooth=False, subsurf=0)
    so = ob.modifiers.new('Solidify', 'SOLIDIFY')
    so.thickness = 0.007
    bv = ob.modifiers.new('Bevel', 'BEVEL')
    bv.width = 0.002
    bv.segments = 2
    return ob


def build(head_only=False, name='Tamar'):
    ch = Character(name)
    C = COLORS
    mats = dict(
        skin_face=M.skin(name + '_face', C['skin'], C['cheek'], cheeks=[(-0.085 * K, -0.118 * K, -0.045 * K), (0.085 * K, -0.118 * K, -0.045 * K)],
                         blush_r=0.04 * K, blush_amt=0.45),
        skin_plain=M.skin(name + '_skin', C['skin']),
        eye=M.eye(name + '_eye', C['iris'], C['iris_d']),
        mouth=M.mouth(name + '_mouth'),
        brow=M.hair(name + '_brow', '#1E120D', strand_scale=200, sheen=0.1),
        lash=M.plain(name + '_lash', '#1A100C', rough=0.6),
        hair=M.hair(name + '_hair', C['hair'], strand_scale=140.0, light_mul=3.0, sheen=0.2, rough=0.55, bands=True, coat=0.0),
        puff=M.hair(name + '_puff', C['hair'], strand_scale=7.0, light_mul=3.0, sheen=0.15, rough=0.5, coat=0.05),
        tie=M.plain(name + '_tie', C['tie'], rough=0.35, coat=0.3),
        shirt=M.fabric(name + '_shirt', C['shirt'], stripes=(C['stripe'], 20.0, 'Y')),
        overall=M.fabric(name + '_overall', C['overall'], knit=1300),
        overall_d=M.fabric(name + '_overall_d', C['overall_d'], knit=1300),
        shoe=M.plain(name + '_shoe', C['shoe'], rough=0.45),
        white=M.plain(name + '_white', '#F6F3EE', rough=0.6),
        heart=M.fabric(name + '_heart', '#FF5A84'),
    )
    mats['lid'] = mats['skin_plain']

    if not head_only:
        ch.joints(S)
        ch.build_armature()
    hc = Vector((0, 0, S['head_z']))
    head = ellipsoid('head', ch.col, hc, HEAD_R, mats['skin_face'], segs=48, rings=24, deform=_cheeks)
    ch.head = head
    ch.face = Face(ch.col, head, mats, FACE)

    # ---- hair: one shell with a side-swept fringe edge, leaving the ears and face free
    R = Vector(HEAD_R)

    def grows(p, n):
        d = Vector(((p.x - hc.x) / R.x, (p.y - hc.y) / R.y, (p.z - hc.z) / R.z))
        if abs(d.x) > 0.74 and -0.5 < d.z < 0.2 and d.y < 0.45:
            return False
        if d.y < -0.15:
            return d.z > 0.5 + 0.12 * (d.x + 1) / 2
        if d.y < 0.3:
            return d.z > 0.05
        return d.z > -0.5
    cap = shell('hair_cap', ch.col, head, grows, mats['hair'], offset=0.011, thickness=0.026, subsurf=2, smooth_edge=6)
    hair = [cap]
    # side-swept bangs: tapered locks from the part (upper right) across the forehead to the left temple
    for k in range(7):
        t = k / 6
        start = Vector((0.22 + 0.32 * t, -0.42 - 0.2 * t, 0.88 - 0.25 * t))
        end = Vector((-0.12 - 0.62 * t, -0.94 + 0.3 * t, 0.42 - 0.12 * t))
        mid = (start + end) / 2 + Vector((0, -0.25, 0.08))
        hair.append(lock(f'bang_{k}', ch.col, hc, R, [start, mid, end], [0.03, 0.022, 0.011],
                         [0.027, 0.022 - 0.002 * t, 0.006], mats['hair']))
    for sx in (-1, 1):  # short locks in front of the ears
        hair.append(lock(f'side_{sx}', ch.col, hc, R, [Vector((sx * 0.75, -0.3, 0.55)), Vector((sx * 0.86, -0.42, 0.25))],
                         [0.035, 0.012], [0.024, 0.007], mats['hair']))
    for sx in (-1, 1):
        d = Vector((sx * 0.8, 0.12, 0.6)).normalized()
        base = hc + Vector((d.x * R.x, d.y * R.y, d.z * R.z))
        pc = base + d * 0.112
        puff = lumpy(f'puff_{sx}', ch.col, pc, 0.08, mats['puff'], seed=4 + sx, amp=0.12, freq=2.0, squash=(1, 0.95, 1.05))
        puff2 = lumpy(f'puff2_{sx}', ch.col, pc + Vector((sx * 0.03, 0.012, -0.04)), 0.055, mats['puff'], seed=9 + sx, amp=0.14)
        stem = capsule(f'stem_{sx}', ch.col, base - d * 0.01, base + d * 0.05, 0.026, 0.026, mats['puff'], segs=16)
        tie = torus(f'tie_{sx}', ch.col, base + d * 0.03, 0.029, 0.012, mats['tie'])
        tie.rotation_mode = 'QUATERNION'
        tie.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
        hair += [puff, puff2, stem, tie]
    ch.hair = hair
    if head_only:
        return ch
    ch.add('head', head, *ch.face.objects, *hair)

    # ---- body: striped shirt with yellow overalls
    t = torso(ch, S, mats['shirt'])
    j = ch.j
    wz = S['waist_z']
    lower = shell('overall_lower', ch.col, t, lambda p, n: p.z < wz + 0.015, mats['overall'], offset=0.004, thickness=0.006)
    bib = shell('overall_bib', ch.col, t, lambda p, n: n.y < -0.25 and abs(p.x) < 0.082 and wz - 0.01 < p.z < S['shoulder_z'] - 0.07,
                mats['overall'], offset=0.004, thickness=0.006)
    straps = shell('overall_straps', ch.col, t, lambda p, n: abs(abs(p.x) - 0.07) < 0.016 and p.z > wz + 0.06,
                   mats['overall'], offset=0.004, thickness=0.005)
    ch.add('chest', bib, straps)
    ch.add('hips', lower)
    bpy.context.view_layer.update()
    for sx in (-1, 1):
        ok, hit, nor = ray_to_surface(bib, (sx * 0.07, -1, S['shoulder_z'] - 0.085), (0, 1, 0))
        if ok:
            ch.add('chest', ellipsoid(f'button_{sx}', ch.col, hit, (0.011, 0.006, 0.011), mats['overall_d']))
    ok, hit, nor = ray_to_surface(bib, (0, -1, wz + 0.06), (0, 1, 0))
    if ok:
        h = _heart('heart', ch.col, mats['heart'], 0.06)
        h.location = hit + Vector((0, -0.002, -0.02))
        h.rotation_euler = (0, 0, 0)
        ch.add('chest', h)
    limbs(ch, S, mats['shirt'], mats['overall'], mats['skin_plain'])
    for side in ('L', 'R'):
        a = j['ankle.' + side]
        cuff = torus('cuff.' + side, ch.col, a + Vector((0, 0, 0.035)), S['leg_r'] * 1.02, 0.014, mats['overall_d'])
        ch.add('shin.' + side, cuff)
    hands(ch, S, mats['skin_plain'])
    shoes(ch, S, mats['shoe'], mats['white'], mats['white'])
    ch.bind()
    return ch
