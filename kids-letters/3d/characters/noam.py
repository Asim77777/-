"""Noam: curly brown hair, orange hoodie, blue pants, red sneakers, a missing front tooth.
Colors follow the 2D design (kids-letters/characters/src/option1.js)."""
import math
import random
from mathutils import Vector

from lib.body import Character, torso, limbs, hands, shoes
from lib.parts import ellipsoid, capsule, torus, shell, rounded_box, tube
from lib.face import Face
from lib.hair import curly_cap
from lib import materials as M
from lib.util import smoothstep

COLORS = dict(skin='#F2BF98', cheek='#FF8E7E', hair='#4A2412', hoodie='#FF7A1F', hoodie_d='#E2600E',
              pants='#3F6FD6', shoe='#E84B4B', iris='#7A4A2A', iris_d='#3A2214')

S = dict(hip_z=0.44, waist_z=0.52, neck_z=0.72, head_z=0.9, shoulder_z=0.69, shoulder_x=0.13,
         upper_arm=0.165, fore_arm=0.15, arm_r=0.047, arm_angle=17, hand_r=0.043,
         leg_x=0.07, knee_z=0.255, ankle_z=0.095, leg_r=0.057, torso_w=0.165, torso_depth=0.74)

K = 1.12  # head scale: big cartoon head
FACE = dict(eye_r=0.039, eye_dx=0.06, eye_z=0.008, eye_sink=0.6, eye_out=7,
            nose_z=-0.036, nose_r=0.017, mouth_z=-0.076, mouth_scale=1.15,
            brow_z=0.054, brow_w=0.0055, ear_z=-0.005, ear_r=0.036, ear_y=0.01)
FACE = {k: (v * K if k not in ('eye_sink', 'eye_out') else v) for k, v in FACE.items()}

HEAD_R = tuple(r * K for r in (0.168, 0.155, 0.158))


def _cheeks(d):
    f = smoothstep(0.0, 0.8, -d.z)            # lower half
    front = smoothstep(0.2, 0.9, -d.y)
    return Vector((1 + 0.05 * f, 1 + 0.035 * f * front, 1 - 0.03 * f))


def build(head_only=False, name='Noam'):
    ch = Character(name)
    C = COLORS
    mats = dict(
        skin_face=M.skin(name + '_face', C['skin'], C['cheek'], cheeks=[(-0.088 * K, -0.12 * K, -0.045 * K), (0.088 * K, -0.12 * K, -0.045 * K)], blush_r=0.042 * K),
        skin_plain=M.skin(name + '_skin', C['skin']),
        eye=M.eye(name + '_eye', C['iris'], C['iris_d']),
        mouth=M.mouth(name + '_mouth', gap=True),
        brow=M.hair(name + '_brow', '#3A1C0E', strand_scale=200, sheen=0.1),
        hair=M.hair(name + '_hair', C['hair'], strand_scale=7.0, light_mul=2.2, sheen=0.15, rough=0.55, coat=0.02),
        hoodie=M.fabric(name + '_hoodie', C['hoodie']),
        hoodie_d=M.fabric(name + '_hoodie_d', C['hoodie_d']),
        pants=M.fabric(name + '_pants', C['pants'], knit=1400),
        shoe=M.plain(name + '_shoe', C['shoe'], rough=0.45),
        white=M.plain(name + '_white', '#F6F3EE', rough=0.6),
        lash=M.plain(name + '_lash', '#2A140A', rough=0.6),
    )
    mats['lid'] = mats['skin_plain']

    if not head_only:
        ch.joints(S)
        ch.build_armature()
    hc = Vector((0, 0, S['head_z']))
    head = ellipsoid('head', ch.col, hc, HEAD_R, mats['skin_face'], segs=48, rings=24, deform=_cheeks)
    ch.head = head
    ch.face = Face(ch.col, head, mats, FACE)

    def keep(d):
        if abs(d.x) > 0.78 and -0.45 < d.z < 0.22 and d.y < 0.4:   # ears stay visible
            return False
        if d.y < -0.35:                                              # front: only above the hairline
            return d.z > 0.56 - 0.14 * abs(d.x)
        if d.y < 0.3:
            return d.z > 0.0
        return d.z > -0.42
    forelock = [(Vector((-0.14, -0.74, 0.64)), 0.03 * K), (Vector((0.12, -0.76, 0.63)), 0.027 * K), (Vector((-0.02, -0.72, 0.68)), 0.034 * K)]
    curls = curly_cap(ch.col, hc, HEAD_R, mats['hair'], keep, n=300, rmin=0.026 * K, rmax=0.04 * K, seed=3, extra=forelock)
    ch.hair = curls
    if head_only:
        return ch

    ch.add('head', head, *ch.face.objects, *curls)

    # ---- body
    t = torso(ch, S, mats['hoodie'])
    j = ch.j
    hem = torus('hem', ch.col, (0, 0, S['hip_z'] - 0.035), S['torso_w'] * 0.97, 0.026, mats['hoodie_d'],
                scale=(1.0, S['torso_depth'], 1.0))
    ch.add('hips', hem)
    # hood lying around the neck
    hood = torus('hood', ch.col, (0, 0.012, S['neck_z'] - 0.005), 0.088, 0.036, mats['hoodie_d'], scale=(1.0, 0.86, 0.8))
    ch.add('chest', hood)
    # drawstrings with white tips
    for sx in (-1, 1):
        pts = [(sx * 0.03, -0.108, S['neck_z'] - 0.035), (sx * 0.034, -0.124, S['neck_z'] - 0.085), (sx * 0.036, -0.127, S['neck_z'] - 0.135)]
        st = tube(f'string_{sx}', ch.col, pts, 0.0045, mats['white'])
        tip = capsule(f'string_tip_{sx}', ch.col, pts[-1], (pts[-1][0], pts[-1][1], pts[-1][2] - 0.02), 0.0065, 0.0065, mats['white'], segs=10)
        ch.add('chest', st, tip)
    # kangaroo pocket cut from the torso surface
    pz0, pz1 = S['hip_z'] - 0.005, S['hip_z'] + 0.1
    pocket = shell('pocket', ch.col, t, lambda p, n: n.y < -0.5 and abs(p.x) < 0.1 and pz0 < p.z < pz1, mats['hoodie_d'],
                   offset=0.002, thickness=0.009)
    ch.add('chest', pocket)
    limbs(ch, S, mats['hoodie'], mats['pants'], mats['skin_plain'])
    for side in ('L', 'R'):
        w = j['wrist.' + side]
        e = j['elbow.' + side]
        d = (w - e).normalized()
        cuff = torus('cuff.' + side, ch.col, w - d * 0.012, S['arm_r'] * 0.92, 0.012, mats['hoodie_d'])
        cuff.rotation_mode = 'QUATERNION'
        cuff.rotation_quaternion = Vector((0, 0, 1)).rotation_difference(d)
        ch.add('fore_arm.' + side, cuff)
    hands(ch, S, mats['skin_plain'])
    shoes(ch, S, mats['shoe'], mats['white'], mats['white'])
    ch.bind()
    return ch
