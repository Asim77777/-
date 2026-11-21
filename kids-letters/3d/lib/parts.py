"""Procedural mesh parts: surfaces of revolution, capsules, tori, lumpy blobs and clothing shells."""
import math
import bpy
import bmesh
from mathutils import Vector, Matrix, noise

from .util import obj_from_bmesh, look_matrix


def lathe_bm(profile, segs=32, sx=1.0, sz=1.0):
    """Surface of revolution around local +Y.
    profile: list of (y, radius); a radius of 0 at either end becomes a pole vertex.
    sx/sz squash the cross-section (elliptical sections)."""
    bm = bmesh.new()
    rings = []
    for y, r in profile:
        if r <= 1e-9:
            rings.append([bm.verts.new((0.0, y, 0.0))])
        else:
            ring = []
            for i in range(segs):
                a = 2 * math.pi * i / segs
                ring.append(bm.verts.new((math.cos(a) * r * sx, y, math.sin(a) * r * sz)))
            rings.append(ring)
    for a, b in zip(rings[:-1], rings[1:]):
        if len(a) == 1 and len(b) > 1:
            for i in range(segs):
                bm.faces.new((a[0], b[(i + 1) % segs], b[i]))
        elif len(b) == 1 and len(a) > 1:
            for i in range(segs):
                bm.faces.new((a[i], a[(i + 1) % segs], b[0]))
        elif len(a) > 1 and len(b) > 1:
            for i in range(segs):
                bm.faces.new((a[i], a[(i + 1) % segs], b[(i + 1) % segs], b[i]))
    bm.normal_update()
    bm.faces.ensure_lookup_table()
    # make sure normals point outward
    c = sum((v.co for v in bm.verts), Vector()) / len(bm.verts)
    f = bm.faces[len(bm.faces) // 2]
    if f.normal.dot(f.calc_center_median() - c) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
    return bm


def capsule_profile(r0, r1, length, k=6, mid=4):
    prof = []
    for i in range(k + 1):  # bottom hemisphere, pole first
        a = -math.pi / 2 + (math.pi / 2) * i / k
        prof.append((r0 * math.sin(a), r0 * math.cos(a)))
    for i in range(1, mid):
        t = i / mid
        prof.append((length * t, r0 + (r1 - r0) * t))
    for i in range(k + 1):
        a = (math.pi / 2) * i / k
        prof.append((length + r1 * math.sin(a), r1 * math.cos(a)))
    return prof


def capsule(name, col, p0, p1, r0, r1, mat, segs=24, sx=1.0, sz=1.0, up=(0, -1, 0), subsurf=1):
    """Rounded limb from p0 to p1. Object origin sits at p0 so it rotates around the joint."""
    p0, p1 = Vector(p0), Vector(p1)
    L = (p1 - p0).length
    bm = lathe_bm(capsule_profile(r0, r1, L), segs, sx, sz)
    ob = obj_from_bmesh(name, bm, col, mat, subsurf=subsurf)
    ob.matrix_world = look_matrix(p0, p1 - p0, Vector(up))
    return ob


def ellipsoid(name, col, center, radii, mat, segs=40, rings=20, deform=None, subsurf=1):
    """Ellipsoid; `deform(unit_dir) -> Vector multiplier` lets callers sculpt it (cheeks, chin...)."""
    rx, ry, rz = radii
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs, v_segments=rings, radius=1.0)
    for v in bm.verts:
        d = v.co.normalized()
        m = deform(d) if deform else Vector((1, 1, 1))
        v.co = Vector((d.x * rx * m.x, d.y * ry * m.y, d.z * rz * m.z))
    bm.normal_update()
    ob = obj_from_bmesh(name, bm, col, mat, subsurf=subsurf)
    ob.location = Vector(center)
    return ob


def torus(name, col, center, R, r, mat, major=48, minor=16, scale=(1, 1, 1), rot=(0, 0, 0), subsurf=1):
    bm = bmesh.new()
    rings = []
    for i in range(major):
        a = 2 * math.pi * i / major
        ring = []
        for j in range(minor):
            b = 2 * math.pi * j / minor
            x = (R + r * math.cos(b)) * math.cos(a)
            y = (R + r * math.cos(b)) * math.sin(a)
            z = r * math.sin(b)
            ring.append(bm.verts.new((x, y, z)))
        rings.append(ring)
    for i in range(major):
        a, b = rings[i], rings[(i + 1) % major]
        for j in range(minor):
            bm.faces.new((a[j], b[j], b[(j + 1) % minor], a[(j + 1) % minor]))
    bm.normal_update()
    ob = obj_from_bmesh(name, bm, col, mat, subsurf=subsurf)
    ob.location = Vector(center)
    ob.rotation_euler = rot
    ob.scale = scale
    return ob


def lumpy(name, col, center, radius, mat, seed=0.0, amp=0.18, freq=2.2, squash=(1, 1, 1), subdiv=3, subsurf=1):
    """Soft irregular blob (curls, pigtail puffs, bushes)."""
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=1.0)
    off = Vector((seed * 7.13, seed * 3.71, seed * 5.29))
    for v in bm.verts:
        d = v.co.normalized()
        n = noise.noise(d * freq + off)
        n2 = noise.noise(d * freq * 2.7 + off * 1.7)
        k = 1.0 + amp * n + amp * 0.35 * n2
        v.co = Vector((d.x * squash[0], d.y * squash[1], d.z * squash[2])) * radius * k
    bm.normal_update()
    ob = obj_from_bmesh(name, bm, col, mat, subsurf=subsurf)
    ob.location = Vector(center)
    return ob


def rounded_box(name, col, center, size, mat, bevel=0.3, subsurf=2):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    ob = obj_from_bmesh(name, bm, col, mat, subsurf=0)
    b = ob.modifiers.new('Bevel', 'BEVEL')
    b.width = min(size) * bevel
    b.segments = 3
    s = ob.modifiers.new('Subsurf', 'SUBSURF')
    s.levels, s.render_levels = subsurf, subsurf
    ob.location = Vector(center)
    return ob


def shell(name, col, src, keep, mat, offset=0.006, thickness=0.008, subsurf=1, smooth_edge=0):
    """Clothing layer cut out of another object's surface.
    keep(world_point, world_normal) -> bool decides which faces survive."""
    deps = bpy.context.evaluated_depsgraph_get()
    bm = bmesh.new()
    bm.from_object(src, deps)
    bm.transform(src.matrix_world)
    bm.normal_update()
    dead = [f for f in bm.faces if not keep(f.calc_center_median(), f.normal)]
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * offset
    # relax the cut edge so it reads as a smooth line instead of a staircase
    edge_verts = [v for v in bm.verts if any(e.is_boundary for e in v.link_edges)]
    for _ in range(smooth_edge):
        new = {}
        for v in edge_verts:
            nb = [e.other_vert(v) for e in v.link_edges if e.is_boundary]
            if len(nb) == 2:
                new[v] = v.co * 0.4 + (nb[0].co + nb[1].co) * 0.3
        for v, co in new.items():
            v.co = co
    ob = obj_from_bmesh(name, bm, col, mat, subsurf=0)
    if thickness:
        so = ob.modifiers.new('Solidify', 'SOLIDIFY')
        so.thickness = thickness
        so.offset = 1.0
        so.use_even_offset = True
    if subsurf:
        s = ob.modifiers.new('Subsurf', 'SUBSURF')
        s.levels, s.render_levels = subsurf, subsurf
    return ob


def tube(name, col, points, radius, mat, segs=12, subsurf=1):
    """Thin tube along a polyline (drawstrings, eyebrows, straps)."""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = radius
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(len(points) - 1)
    for bp, p in zip(sp.bezier_points, points):
        bp.co = Vector(p)
        bp.handle_left_type = bp.handle_right_type = 'AUTO'
    ob = bpy.data.objects.new(name, cu)
    col.objects.link(ob)
    if mat is not None:
        cu.materials.append(mat)
    return ob
