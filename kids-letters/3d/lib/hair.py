"""Hair builders: curly clusters (Noam) and a smooth hair cap with bangs and pigtail puffs (Tamar)."""
import math
import random
import bpy
from mathutils import Vector, Euler

from .parts import lumpy, shell, torus
from .util import link_mesh


def fibonacci_dirs(n):
    out = []
    g = math.pi * (3 - math.sqrt(5))
    for i in range(n):
        z = 1 - 2 * (i + 0.5) / n
        r = math.sqrt(1 - z * z)
        out.append(Vector((math.cos(g * i) * r, math.sin(g * i) * r, z)))
    return out


def curly_cap(col, head_center, radii, mat, keep, n=180, rmin=0.032, rmax=0.047, lift=0.5, seed=1, extra=()):
    """Cover the scalp with curls. keep(unit_dir) decides where hair grows.
    extra: list of (unit_dir, radius) for hand-placed curls such as a forelock."""
    random.seed(seed)
    c = Vector(head_center)
    bases = [lumpy(f'curl_base_{i}', col, (0, 0, -50), 1.0, mat, seed=i * 2.3 + seed, amp=0.22, freq=2.6,
                   squash=(1, 1, 0.85)) for i in range(6)]
    curls = []
    spots = [(d, random.uniform(rmin, rmax)) for d in fibonacci_dirs(n) if keep(d)] + list(extra)
    for k, (d, r) in enumerate(spots):
        on = Vector((d.x * radii[0], d.y * radii[1], d.z * radii[2]))
        ob = link_mesh(f'curl_{k}', bases[k % len(bases)], col)
        ob.location = c + on + d.normalized() * r * lift
        ob.scale = (r, r, r)
        ob.rotation_euler = Euler((random.uniform(0, 6.28), random.uniform(0, 6.28), random.uniform(0, 6.28)))
        curls.append(ob)
    for b in bases:  # bases were parked far away; remove them
        bpy.data.objects.remove(b)
    return curls


def lock(name, col, center, radii, dirs, lifts, widths, mat):
    """A tapered hair lock that hugs the head: dirs are unit-sphere directions in head space,
    lifts the height above the skin and widths the lock radius at each point."""
    c, R = Vector(center), Vector(radii)
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = 1.0
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER')
    sp.bezier_points.add(len(dirs) - 1)
    for bp, d, lift, w in zip(sp.bezier_points, dirs, lifts, widths):
        dn = Vector(d).normalized()
        bp.co = c + Vector((dn.x * R.x, dn.y * R.y, dn.z * R.z)) + dn * lift
        bp.radius = w
        bp.handle_left_type = bp.handle_right_type = 'AUTO'
    ob = bpy.data.objects.new(name, cu)
    col.objects.link(ob)
    cu.materials.append(mat)
    return ob
