"""Face features placed onto a head mesh: eyes with lids, brows, nose, ears and a shape-keyed mouth.

The mouth is a grid that is shrink-wrapped onto the face. All mouth shapes share one topology,
so they are shape keys and can blend smoothly when the characters talk."""
import math
import bpy
import bmesh
from mathutils import Vector

from .util import obj_from_bmesh, ray_to_surface
from .parts import ellipsoid, tube

# Mouth shapes: (width, corner_z, top_center_z, bottom_center_z), in units of the head's mouth scale.
MOUTHS = {
    'rest':      (0.050, 0.006, 0.000, -0.0028),
    'happy':     (0.060, 0.010, 0.001, -0.028),
    'laugh':     (0.074, 0.014, 0.003, -0.046),
    'A':         (0.050, 0.002, 0.008, -0.034),
    'E':         (0.064, 0.004, 0.003, -0.016),
    'O':         (0.030, -0.012, 0.008, -0.030),
    'M':         (0.044, 0.001, 0.0005, -0.0008),
    'surprised': (0.028, -0.011, 0.007, -0.027),
}
TEETH = {'rest': 0, 'M': 0, 'O': 0.0, 'surprised': 0.0}

# Expression presets: mouth shape, upper/lower lid angle (deg), brow lift (m)
EXPRESSIONS = {
    'neutral':   dict(mouth='rest', upper=-64, lower=86, brow=0.0),
    'happy':     dict(mouth='happy', upper=-60, lower=24, brow=0.002),
    'surprised': dict(mouth='surprised', upper=-88, lower=88, brow=0.014),
    'laugh':     dict(mouth='laugh', upper=-40, lower=-47, brow=0.007),
    'blink':     dict(mouth='rest', upper=84, lower=72, brow=0.0),
}


def _mouth_coords(shape, scale, U, V):
    w, c, t, b = (s * scale for s in MOUTHS[shape])
    out = []
    for j in range(V + 1):
        v = j / V
        for i in range(U + 1):
            u = i / U
            s = abs(2 * u - 1)
            zt = t + (c - t) * s ** 2.0
            zb = b + (c - b) * s ** 2.2
            out.append(Vector(((u - 0.5) * w, -0.03, zt + (zb - zt) * v)))
    return out


class Face:
    def __init__(self, col, head, mats, p):
        """p: dict of face proportions (see characters/*.py). mats: dict with skin, eye, mouth, brow, lash."""
        self.col, self.head, self.p = col, head, p
        self.objects = []
        c = head.matrix_world.translation
        self.center = c
        self.eyes, self.upper, self.lower, self.brows, self.brow_rest = [], [], [], [], []
        bpy.context.view_layer.update()

        # ---- eyes and lids
        er = p['eye_r']
        for side in (-1, 1):
            ok, hit, nor = ray_to_surface(head, (c.x + side * p['eye_dx'], c.y - 1, c.z + p['eye_z']), (0, 1, 0))
            ec = hit + Vector((0, er * p.get('eye_sink', 0.5), 0))
            eb = ellipsoid(f'eye_{side}', col, ec, (1, 1, 1), mats['eye'], segs=32, rings=16)
            eb.scale = (er, er, er)
            eb.rotation_euler = (0, 0, math.radians(-side * p.get('eye_out', 6)))
            self.eyes.append(eb)
            for kind in ('upper', 'lower'):
                bm = bmesh.new()
                bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1.07)
                keep_top = kind == 'upper'
                dead = [v for v in bm.verts if (v.co.z < -1e-4 if keep_top else v.co.z > 1e-4)]
                bmesh.ops.delete(bm, geom=dead, context='VERTS')
                lid = obj_from_bmesh(f'lid_{kind}_{side}', bm, col, mats['lid'], subsurf=0)
                so = lid.modifiers.new('Solidify', 'SOLIDIFY')
                so.thickness = 0.09
                ss = lid.modifiers.new('Subsurf', 'SUBSURF')
                ss.levels, ss.render_levels = 1, 2
                lid.location = ec
                lid.scale = (er, er, er)
                lid.rotation_mode = 'XYZ'
                # dark line along the front rim: eyeliner when open, a curved line when the lid closes
                arc = [(math.cos(a) * 1.075, -math.sin(a) * 1.075, 0.0) for a in
                       [math.pi * (0.1 + 0.8 * i / 8) for i in range(9)]]
                rim = tube(f'rim_{kind}_{side}', col, arc, 0.045 if keep_top else 0.035, mats['lash'])
                rim.parent = lid
                (self.upper if keep_top else self.lower).append(lid)
            if p.get('lashes'):
                lid = self.upper[-1]
                for k, (a, l) in enumerate(((0.55, 0.42), (0.85, 0.36))):
                    ang = math.pi / 2 + side * (math.pi / 2) * a  # point on the rim toward the outer corner
                    x0, y0 = math.cos(ang) * 1.07, -abs(math.sin(ang)) * 1.07
                    pts = [(x0, y0, 0.0), (x0 + side * l * 0.55, y0 - l * 0.5, 0.04), (x0 + side * l, y0 - l * 0.65, -0.02)]
                    ls = tube(f'lash_{side}_{k}', col, pts, 0.05, mats['lash'])
                    ls.parent = lid
        self.objects += self.eyes + self.upper + self.lower

        # ---- nose
        ok, hit, nor = ray_to_surface(head, (c.x, c.y - 1, c.z + p['nose_z']), (0, 1, 0))
        nr = p['nose_r']
        self.nose = ellipsoid('nose', col, hit + Vector((0, nr * 0.15, 0)), (nr * 1.15, nr, nr * 0.85), mats['skin_plain'])
        self.objects.append(self.nose)

        # ---- ears
        self.ears = []
        for side in (-1, 1):
            ok, hit, nor = ray_to_surface(head, (c.x + side, c.y + p.get('ear_y', 0.0), c.z + p['ear_z']), (-side, 0, 0))
            e = ellipsoid(f'ear_{side}', col, hit + Vector((side * p['ear_r'] * 0.25, 0, 0)),
                          (p['ear_r'] * 0.55, p['ear_r'] * 0.8, p['ear_r']), mats['skin_plain'])
            self.ears.append(e)
        self.objects += self.ears

        # ---- brows (curved tubes hugging the forehead)
        for side in (-1, 1):
            pts = []
            bx = c.x + side * p['eye_dx']
            for k, dx in enumerate((-0.026, 0.0, 0.026)):
                lift = 0.006 if k == 1 else 0.0
                ok, hit, nor = ray_to_surface(head, (bx + dx * side, c.y - 1, c.z + p['brow_z'] + lift), (0, 1, 0))
                pts.append(hit + nor * 0.003)
            mid = pts[1].copy()
            br = tube(f'brow_{side}', col, [q - mid for q in pts], p.get('brow_w', 0.0045), mats['brow'])
            br.location = mid
            self.brows.append(br)
            self.brow_rest.append(mid.copy())
        self.objects += self.brows

        # ---- mouth
        ok, hit, nor = ray_to_surface(head, (c.x, c.y - 1, c.z + p['mouth_z']), (0, 1, 0))
        U, V = 28, 8
        scale = p.get('mouth_scale', 1.0)
        bm = bmesh.new()
        verts = [bm.verts.new(co) for co in _mouth_coords('rest', scale, U, V)]
        uv_layer = bm.loops.layers.uv.new('UVMap')
        for j in range(V):
            for i in range(U):
                a = j * (U + 1) + i
                quad = (verts[a], verts[a + 1], verts[a + U + 2], verts[a + U + 1])
                f = bm.faces.new(quad)
                for loop, (ii, jj) in zip(f.loops, ((i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1))):
                    loop[uv_layer].uv = (ii / U, jj / V)
        bm.normal_update()
        self.mouth = obj_from_bmesh('mouth', bm, col, mats['mouth'], subsurf=0)
        self.mouth.location = hit
        sk = self.mouth.shape_key_add(name='Basis')
        for name in MOUTHS:
            if name == 'rest':
                continue
            k = self.mouth.shape_key_add(name=name, from_mix=False)
            for pt, co in zip(k.data, _mouth_coords(name, scale, U, V)):
                pt.co = co
        sw = self.mouth.modifiers.new('Wrap', 'SHRINKWRAP')
        sw.target = head
        sw.wrap_method = 'PROJECT'
        sw.use_project_y = True
        sw.use_negative_direction = True
        sw.use_positive_direction = True
        sw.offset = 0.0012
        sub = self.mouth.modifiers.new('Subsurf', 'SUBSURF')
        sub.levels, sub.render_levels = 1, 2
        self.objects.append(self.mouth)
        self.teeth_node = mats['mouth'].node_tree.nodes['Teeth']
        self.set_expression('happy')

    # ---------------------------------------------------------------- controls
    def set_mouth(self, shape, amount=1.0, frame=None):
        for kb in self.mouth.data.shape_keys.key_blocks[1:]:
            kb.value = amount if kb.name == shape else 0.0
            if frame is not None:
                kb.keyframe_insert('value', frame=frame)
        self.teeth_node.outputs[0].default_value = TEETH.get(shape, 1.0)
        if frame is not None:
            self.teeth_node.outputs[0].keyframe_insert('default_value', frame=frame)

    def set_lids(self, upper, lower, frame=None):
        for lid in self.upper:
            lid.rotation_euler.x = math.radians(upper)
            if frame is not None:
                lid.keyframe_insert('rotation_euler', index=0, frame=frame)
        for lid in self.lower:
            lid.rotation_euler.x = math.radians(lower)
            if frame is not None:
                lid.keyframe_insert('rotation_euler', index=0, frame=frame)

    def set_brows(self, lift, frame=None):
        for br, rest in zip(self.brows, self.brow_rest):
            br.location = rest + Vector((0, 0, lift))
            if frame is not None:
                br.keyframe_insert('location', frame=frame)

    def set_expression(self, name, frame=None):
        e = EXPRESSIONS[name]
        self.set_mouth(e['mouth'], 1.0, frame)
        self.set_lids(e['upper'], e['lower'], frame)
        self.set_brows(e['brow'], frame)

    def look(self, dx_deg=0.0, dz_deg=0.0, frame=None):
        for i, eb in enumerate(self.eyes):
            side = -1 if i == 0 else 1
            eb.rotation_euler = (math.radians(dz_deg), 0, math.radians(-side * self.p.get('eye_out', 6) + dx_deg))
            if frame is not None:
                eb.keyframe_insert('rotation_euler', frame=frame)
