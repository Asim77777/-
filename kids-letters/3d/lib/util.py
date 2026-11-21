"""Small helpers shared by the 3D character scripts (Blender / bpy)."""
import math
import bpy
import bmesh
from mathutils import Vector, Matrix


def hex2lin(h, alpha=1.0):
    """'#RRGGBB' (sRGB) -> linear RGBA tuple, which is what Blender colors expect."""
    h = h.lstrip('#')
    out = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return (*out, alpha)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    return bpy.context.scene


def collection(name, parent=None):
    col = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    parent = parent or bpy.context.scene.collection
    if col.name not in [c.name for c in parent.children]:
        parent.children.link(col)
    return col


def obj_from_bmesh(name, bm, col, mat=None, smooth=True, subsurf=1, render_subsurf=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    col.objects.link(ob)
    if smooth:
        me.shade_smooth()
    if mat is not None:
        me.materials.append(mat)
    if subsurf:
        m = ob.modifiers.new('Subsurf', 'SUBSURF')
        m.levels = subsurf
        m.render_levels = render_subsurf if render_subsurf is not None else subsurf + 1
    return ob


def link_mesh(name, src, col):
    """Linked duplicate: shares the mesh data (cheap for repeated curls)."""
    ob = bpy.data.objects.new(name, src.data)
    col.objects.link(ob)
    for m in src.modifiers:
        n = ob.modifiers.new(m.name, m.type)
        if m.type == 'SUBSURF':
            n.levels, n.render_levels = m.levels, m.render_levels
    return ob


def look_matrix(origin, direction, up_hint=Vector((0, -1, 0))):
    """Matrix whose local +Y points along `direction`, local +Z as close to up_hint as possible."""
    y = Vector(direction).normalized()
    up = Vector(up_hint)
    if abs(y.dot(up.normalized())) > 0.98:
        up = Vector((0, 0, 1)) if abs(y.z) < 0.9 else Vector((1, 0, 0))
    x = y.cross(up).normalized()
    z = x.cross(y).normalized()
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = Vector(origin)
    return m


def smoothstep(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def ray_to_surface(ob, origin, direction):
    """Ray cast against an object's evaluated mesh, in world space. Returns (hit, location, normal)."""
    deps = bpy.context.evaluated_depsgraph_get()
    mw = ob.matrix_world
    inv = mw.inverted()
    o = inv @ Vector(origin)
    d = (inv.to_3x3() @ Vector(direction)).normalized()
    ok, loc, nor, _ = ob.evaluated_get(deps).ray_cast(o, d)
    if not ok:
        return False, None, None
    return True, mw @ loc, (mw.to_3x3() @ nor).normalized()
