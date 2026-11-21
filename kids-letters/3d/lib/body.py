"""Shared body, skeleton and rigid-part rig for the kid characters.

Limbs are capsules whose rounded ends sit on the joints, so a part can rotate around its joint
without opening a gap. Every part is parented to one bone (no skin weights to break)."""
import math
import bpy
from mathutils import Vector, Matrix

from .util import collection, look_matrix
from .parts import capsule, ellipsoid, lathe_bm, rounded_box
from .util import obj_from_bmesh


class Character:
    def __init__(self, name):
        self.name = name
        self.col = collection(name)
        self.parts = {}      # bone name -> [objects]
        self.arm = None
        self.head = None
        self.face = None
        self.j = {}          # joint positions (rest pose, world)

    def add(self, bone, *obs):
        self.parts.setdefault(bone, []).extend(obs)
        return obs[0] if len(obs) == 1 else obs

    # ------------------------------------------------------------------ skeleton
    def joints(self, s):
        """s: proportions dict. Fills self.j with rest joint positions (character at origin, facing -Y)."""
        j = self.j
        j['hip'] = Vector((0, 0, s['hip_z']))
        j['waist'] = Vector((0, 0, s['waist_z']))
        j['neck'] = Vector((0, 0, s['neck_z']))
        j['head_base'] = Vector((0, 0, s['neck_z'] + 0.06))
        j['head_c'] = Vector((0, 0, s['head_z']))
        for side, sx in (('L', 1), ('R', -1)):
            sh = Vector((sx * s['shoulder_x'], 0, s['shoulder_z']))
            a = math.radians(s.get('arm_angle', 18))
            down = Vector((sx * math.sin(a), -0.01, -math.cos(a)))
            j['shoulder.' + side] = sh
            j['elbow.' + side] = sh + down * s['upper_arm']
            j['wrist.' + side] = j['elbow.' + side] + (down + Vector((0, -0.12, 0))).normalized() * s['fore_arm']
            j['hand_tip.' + side] = j['wrist.' + side] + down * 0.09
            hipj = Vector((sx * s['leg_x'], 0, s['hip_z']))
            j['hipj.' + side] = hipj
            j['knee.' + side] = Vector((sx * s['leg_x'], -0.005, s['knee_z']))
            j['ankle.' + side] = Vector((sx * s['leg_x'], 0, s['ankle_z']))
            j['toe.' + side] = Vector((sx * s['leg_x'], -0.11, s['ankle_z'] - 0.03))

    def build_armature(self):
        j = self.j
        bones = [('root', Vector((0, 0, 0)), Vector((0, 0, 0.12)), None),
                 ('hips', j['hip'], j['waist'], 'root'),
                 ('chest', j['waist'], j['neck'], 'hips'),
                 ('neck', j['neck'], j['head_base'], 'chest'),
                 ('head', j['head_base'], j['head_base'] + Vector((0, 0, 0.22)), 'neck')]
        for side in ('L', 'R'):
            bones += [('upper_arm.' + side, j['shoulder.' + side], j['elbow.' + side], 'chest'),
                      ('fore_arm.' + side, j['elbow.' + side], j['wrist.' + side], 'upper_arm.' + side),
                      ('hand.' + side, j['wrist.' + side], j['hand_tip.' + side], 'fore_arm.' + side),
                      ('thigh.' + side, j['hipj.' + side], j['knee.' + side], 'hips'),
                      ('shin.' + side, j['knee.' + side], j['ankle.' + side], 'thigh.' + side),
                      ('foot.' + side, j['ankle.' + side], j['toe.' + side], 'shin.' + side)]
        ad = bpy.data.armatures.new(self.name + '_rig')
        arm = bpy.data.objects.new(self.name + '_rig', ad)
        self.col.objects.link(arm)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.object.mode_set(mode='EDIT')
        eb = ad.edit_bones
        for name, h, t, parent in bones:
            b = eb.new(name)
            b.head, b.tail = h, t
            if parent:
                b.parent = eb[parent]
            b.align_roll(Vector((0, 0, 1)) if name.startswith('foot') else Vector((0, -1, 0)))
        bpy.ops.object.mode_set(mode='OBJECT')
        for pb in arm.pose.bones:
            pb.rotation_mode = 'XYZ'
        ad.display_type = 'STICK'
        arm.hide_render = True
        self.arm = arm
        return arm

    def bind(self):
        """Parent every part to its bone, keeping its current world transform."""
        arm = self.arm
        bpy.context.view_layer.update()
        for bname, obs in self.parts.items():
            bone = arm.data.bones[bname]
            pm = arm.matrix_world @ bone.matrix_local @ Matrix.Translation((0, bone.length, 0))
            for ob in obs:
                mw = ob.matrix_basis.copy()  # unparented: basis is the world transform (always current)
                ob.parent = arm
                ob.parent_type = 'BONE'
                ob.parent_bone = bname
                ob.matrix_parent_inverse = pm.inverted()
                ob.matrix_basis = mw

    def bone_matrix(self, bname):
        """Rest matrix of a bone in world space (Y along the bone, Z forward)."""
        b = self.arm.data.bones[bname]
        return self.arm.matrix_world @ b.matrix_local

    # ------------------------------------------------------------------ posing
    def pose(self, bname, x=0.0, y=0.0, z=0.0, frame=None):
        pb = self.arm.pose.bones[bname]
        pb.rotation_euler = (math.radians(x), math.radians(y), math.radians(z))
        if frame is not None:
            pb.keyframe_insert('rotation_euler', frame=frame)

    def rest(self, frame=None):
        for pb in self.arm.pose.bones:
            pb.rotation_euler = (0, 0, 0)
            pb.location = (0, 0, 0)
            if frame is not None:
                pb.keyframe_insert('rotation_euler', frame=frame)

    def place(self, x=0.0, y=0.0, rot_z=0.0):
        self.arm.location = (x, y, 0)
        self.arm.rotation_euler = (0, 0, math.radians(rot_z))


# ---------------------------------------------------------------------- body parts
def torso(ch, s, mat, top_extra=0.0):
    """Rounded pill torso standing on the waistline."""
    j = ch.j
    h = (s['shoulder_z'] + 0.05 + top_extra) - (s['hip_z'] - 0.06)
    w = s['torso_w']
    prof = [(0, 0), (0.004, w * 0.78), (0.03, w * 0.96), h * 0.35, h * 0.7, (h * 0.86, w * 0.82), (h * 0.95, w * 0.5), (h, 0)]
    prof = [p if isinstance(p, tuple) else (p, w) for p in prof]
    bm = lathe_bm(prof, 40, 1.0, s.get('torso_depth', 0.74))
    ob = obj_from_bmesh('torso', bm, ch.col, mat, subsurf=2)
    ob.matrix_world = look_matrix((0, 0, s['hip_z'] - 0.06), (0, 0, 1), (0, -1, 0))
    return ch.add('chest', ob)


def limbs(ch, s, sleeve_mat, pants_mat, skin_mat):
    j = ch.j
    for side in ('L', 'R'):
        ch.add('upper_arm.' + side, capsule('upper_arm.' + side, ch.col, j['shoulder.' + side], j['elbow.' + side],
                                            s['arm_r'] * 1.08, s['arm_r'], sleeve_mat))
        ch.add('fore_arm.' + side, capsule('fore_arm.' + side, ch.col, j['elbow.' + side], j['wrist.' + side],
                                           s['arm_r'], s['arm_r'] * 0.92, sleeve_mat))
        ch.add('thigh.' + side, capsule('thigh.' + side, ch.col, j['hipj.' + side], j['knee.' + side],
                                        s['leg_r'] * 1.08, s['leg_r'], pants_mat))
        ch.add('shin.' + side, capsule('shin.' + side, ch.col, j['knee.' + side], j['ankle.' + side] + Vector((0, 0, 0.02)),
                                       s['leg_r'], s['leg_r'] * 0.95, pants_mat))
    neck = capsule('neck', ch.col, j['neck'] - Vector((0, 0, 0.03)), j['head_base'] + Vector((0, 0, 0.02)), 0.042, 0.042, skin_mat)
    ch.add('neck', neck)


def hands(ch, s, skin_mat):
    """Four-finger cartoon hands built in bone space, palms facing the body."""
    for side, inward in (('L', 1), ('R', -1)):
        bm = ch.bone_matrix('hand.' + side)
        r = s['hand_r']
        obs = [ellipsoid('palm.' + side, ch.col, (0, r * 0.75, 0), (r * 0.5, r * 0.95, r * 0.9), skin_mat)]
        for k, z in enumerate((-0.48, -0.16, 0.16, 0.48)):
            ln = r * (0.8 if k in (1, 2) else 0.66)
            base = Vector((inward * r * 0.05, r * 1.4, z * r))
            tip = base + Vector((inward * r * 0.25, ln, z * r * 0.12))
            obs.append(capsule(f'finger{k}.' + side, ch.col, base, tip, r * 0.29, r * 0.27, skin_mat, segs=12))
        tb = Vector((inward * r * 0.15, r * 0.65, r * 0.75))
        obs.append(capsule('thumb.' + side, ch.col, tb, tb + Vector((inward * r * 0.35, r * 0.45, r * 0.45)), r * 0.3, r * 0.27, skin_mat, segs=12))
        for ob in obs:
            ob.matrix_basis = bm @ ob.matrix_basis
        ch.add('hand.' + side, *obs)


def shoes(ch, s, upper_mat, sole_mat, lace_mat=None):
    for side in ('L', 'R'):
        a = ch.j['ankle.' + side]
        sx = 1 if side == 'L' else -1
        up = ellipsoid('shoe.' + side, ch.col, (a.x + sx * 0.006, a.y - 0.045, 0.06), (0.068, 0.112, 0.058), upper_mat,
                       deform=lambda d: Vector((1, 1, 0.85 if d.z > 0 else 1)))
        sole = ellipsoid('sole.' + side, ch.col, (a.x + sx * 0.006, a.y - 0.045, 0.024), (0.073, 0.12, 0.024), sole_mat,
                         deform=lambda d: Vector((1, 1, 0.45 if d.z < 0 else 1)))
        obs = [up, sole]
        if lace_mat:
            for k in range(2):
                obs.append(capsule(f'lace{k}.' + side, ch.col, (a.x - 0.026, a.y - 0.085 - k * 0.03, 0.106 - k * 0.012),
                                   (a.x + 0.026, a.y - 0.085 - k * 0.03, 0.106 - k * 0.012), 0.007, 0.007, lace_mat, segs=8))
        ch.add('foot.' + side, *obs)
