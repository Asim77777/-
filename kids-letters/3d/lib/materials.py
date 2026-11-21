"""Cycles materials: skin with subsurface and blush, soft fabric, hair, glossy cartoon eyes, mouth."""
import bpy
from .util import hex2lin


def _new(name):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    return mat, nt, nt.nodes['Principled BSDF']


def _math(nt, op, a=None, b=None, clamp=False):
    n = nt.nodes.new('ShaderNodeMath')
    n.operation = op
    n.use_clamp = clamp
    for i, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[i].default_value = v
        else:
            nt.links.new(v, n.inputs[i])
    return n.outputs[0]


def _mix(nt, fac, a, b):
    """Mix two colors (sockets or RGBA tuples) by fac (socket or float)."""
    n = nt.nodes.new('ShaderNodeMix')
    n.data_type = 'RGBA'
    by_id = {s.identifier: s for s in n.inputs}
    f_sock = by_id.get('Factor_Float', n.inputs[0])
    if isinstance(fac, (int, float)):
        f_sock.default_value = fac
    else:
        nt.links.new(fac, f_sock)
    for sock, v in ((by_id['A_Color'], a), (by_id['B_Color'], b)):
        if isinstance(v, tuple):
            sock.default_value = v
        else:
            nt.links.new(v, sock)
    return {s.identifier: s for s in n.outputs}['Result_Color']


def _bump(nt, bsdf, height, strength=0.2, distance=0.002):
    bp = nt.nodes.new('ShaderNodeBump')
    bp.inputs['Strength'].default_value = strength
    bp.inputs['Distance'].default_value = distance
    nt.links.new(height, bp.inputs['Height'])
    nt.links.new(bp.outputs['Normal'], bsdf.inputs['Normal'])


def plain(name, hexc, rough=0.5, coat=0.0, metallic=0.0):
    mat, nt, b = _new(name)
    b.inputs['Base Color'].default_value = hex2lin(hexc)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Metallic'].default_value = metallic
    return mat


def emission(name, hexc, strength=8.0):
    mat, nt, b = _new(name)
    b.inputs['Base Color'].default_value = hex2lin(hexc)
    b.inputs['Emission Color'].default_value = hex2lin(hexc)
    b.inputs['Emission Strength'].default_value = strength
    return mat


def skin(name, hexc, blush_hex=None, cheeks=(), blush_r=0.05, blush_amt=0.5):
    """Skin. With `cheeks` (object-space points) adds soft round blush, like the 2D design."""
    mat, nt, b = _new(name)
    base = hex2lin(hexc)
    color = base
    if blush_hex and cheeks:
        tc = nt.nodes.new('ShaderNodeTexCoord')
        mask = None
        for c in cheeks:
            vm = nt.nodes.new('ShaderNodeVectorMath')
            vm.operation = 'DISTANCE'
            nt.links.new(tc.outputs['Object'], vm.inputs[0])
            vm.inputs[1].default_value = c
            mr = nt.nodes.new('ShaderNodeMapRange')
            mr.interpolation_type = 'SMOOTHSTEP'
            mr.inputs['From Min'].default_value = blush_r
            mr.inputs['From Max'].default_value = blush_r * 0.15
            nt.links.new(vm.outputs['Value'], mr.inputs['Value'])
            m = mr.outputs['Result']
            mask = m if mask is None else _math(nt, 'MAXIMUM', mask, m)
        fac = _math(nt, 'MULTIPLY', mask, blush_amt)
        color = _mix(nt, fac, base, hex2lin(blush_hex))
    if isinstance(color, tuple):
        b.inputs['Base Color'].default_value = color
    else:
        nt.links.new(color, b.inputs['Base Color'])
    b.inputs['Subsurface Weight'].default_value = 0.25
    b.inputs['Subsurface Radius'].default_value = (1.0, 0.4, 0.25)
    b.inputs['Subsurface Scale'].default_value = 0.012
    b.inputs['Roughness'].default_value = 0.48
    b.inputs['Specular IOR Level'].default_value = 0.35
    return mat


def fabric(name, hexc, rough=0.8, sheen=0.0, knit=900.0, stripes=None):
    """Soft cotton. stripes=(hex2, count_per_meter, axis) paints stripes along an object axis."""
    mat, nt, b = _new(name)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = knit
    nz.inputs['Detail'].default_value = 2.0
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    color = hex2lin(hexc)
    if stripes:
        hex2, per_m, axis = stripes
        sep = nt.nodes.new('ShaderNodeSeparateXYZ')
        nt.links.new(tc.outputs['Object'], sep.inputs[0])
        s = _math(nt, 'MULTIPLY', sep.outputs[axis], per_m)
        s = _math(nt, 'FRACT', s)
        s = _math(nt, 'GREATER_THAN', s, 0.62)
        color = _mix(nt, s, color, hex2lin(hex2))
    if isinstance(color, tuple):
        b.inputs['Base Color'].default_value = color
    else:
        nt.links.new(color, b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough
    b.inputs['Sheen Weight'].default_value = sheen
    b.inputs['Sheen Roughness'].default_value = 0.4
    b.inputs['Specular IOR Level'].default_value = 0.3
    _bump(nt, b, nz.outputs['Fac'], strength=0.12, distance=0.001)
    return mat


def hair(name, hexc, strand_scale=60.0, rough=0.42, light_mul=1.6, sheen=0.35, bands=False, coat=0.15):
    mat, nt, b = _new(name)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    wv = nt.nodes.new('ShaderNodeTexWave')
    wv.wave_type = 'BANDS' if bands else 'RINGS'
    if bands:
        wv.bands_direction = 'X'
    wv.inputs['Scale'].default_value = strand_scale
    wv.inputs['Distortion'].default_value = 6.0
    wv.inputs['Detail'].default_value = 3.0
    nt.links.new(tc.outputs['Object'], wv.inputs['Vector'])
    base = hex2lin(hexc)
    light = tuple(min(1.0, c * light_mul) for c in base[:3]) + (1.0,)
    col = _mix(nt, _math(nt, 'MULTIPLY', wv.outputs['Fac'], 0.35), base, light)
    nt.links.new(col, b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough
    b.inputs['Sheen Weight'].default_value = sheen
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Coat Roughness'].default_value = 0.3
    _bump(nt, b, wv.outputs['Fac'], strength=0.35, distance=0.002)
    return mat


def eye(name, iris_hex, iris_dark_hex):
    """Eyeball modelled with radius 1 in object space, looking down local -Y.
    Iris, pupil, limbal ring and two catchlights are painted from object coordinates."""
    mat, nt, b = _new(name)
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], sep.inputs[0])
    x, z = sep.outputs['X'], sep.outputs['Z']
    r = _math(nt, 'SQRT', _math(nt, 'ADD', _math(nt, 'MULTIPLY', x, x), _math(nt, 'MULTIPLY', z, z)))
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    nt.links.new(r, ramp.inputs['Fac'])
    cr = ramp.color_ramp
    cr.elements[0].position, cr.elements[0].color = 0.0, (0.004, 0.003, 0.003, 1)
    cr.elements[1].position, cr.elements[1].color = 0.66, (0.92, 0.92, 0.94, 1)
    for pos, c in ((0.25, (0.004, 0.003, 0.003, 1)), (0.29, hex2lin(iris_hex)),
                   (0.52, hex2lin(iris_dark_hex)), (0.585, (0.01, 0.008, 0.008, 1)), (0.63, (0.92, 0.92, 0.94, 1))):
        e = cr.elements.new(pos)
        e.color = c
    nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
    # catchlights (fixed in eye space so they read as sparkle)
    spots = None
    for cx, cz, rad in ((0.2, 0.26, 0.11), (-0.17, -0.2, 0.05)):
        dx = _math(nt, 'SUBTRACT', x, cx)
        dz = _math(nt, 'SUBTRACT', z, cz)
        d = _math(nt, 'SQRT', _math(nt, 'ADD', _math(nt, 'MULTIPLY', dx, dx), _math(nt, 'MULTIPLY', dz, dz)))
        s = _math(nt, 'LESS_THAN', d, rad)
        spots = s if spots is None else _math(nt, 'MAXIMUM', spots, s)
    front = _math(nt, 'LESS_THAN', sep.outputs['Y'], 0.0)
    spots = _math(nt, 'MULTIPLY', spots, front)
    b.inputs['Emission Color'].default_value = (1, 1, 1, 1)
    nt.links.new(_math(nt, 'MULTIPLY', spots, 3.0), b.inputs['Emission Strength'])
    b.inputs['Roughness'].default_value = 0.25
    b.inputs['Coat Weight'].default_value = 1.0
    b.inputs['Coat Roughness'].default_value = 0.02
    return mat


def mouth(name, gap=False):
    """Mouth decal painted from its UVs: u across (0..1), v from top lip (0) to bottom lip (1).
    The 'Teeth' value node (0..1) hides the teeth for closed shapes."""
    mat, nt, b = _new(name)
    uv = nt.nodes.new('ShaderNodeUVMap')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(uv.outputs['UV'], sep.inputs[0])
    u, v = sep.outputs['X'], sep.outputs['Y']
    teeth_val = nt.nodes.new('ShaderNodeValue')
    teeth_val.name = teeth_val.label = 'Teeth'
    teeth_val.outputs[0].default_value = 1.0
    t = _math(nt, 'LESS_THAN', v, 0.26)
    t = _math(nt, 'MULTIPLY', t, _math(nt, 'GREATER_THAN', u, 0.1))
    t = _math(nt, 'MULTIPLY', t, _math(nt, 'LESS_THAN', u, 0.9))
    if gap:
        in_gap = _math(nt, 'MULTIPLY', _math(nt, 'GREATER_THAN', u, 0.43), _math(nt, 'LESS_THAN', u, 0.5))
        t = _math(nt, 'MULTIPLY', t, _math(nt, 'SUBTRACT', 1.0, in_gap))
    t = _math(nt, 'MULTIPLY', t, teeth_val.outputs[0])
    du = _math(nt, 'DIVIDE', _math(nt, 'SUBTRACT', u, 0.5), 0.3)
    dv = _math(nt, 'DIVIDE', _math(nt, 'SUBTRACT', v, 1.05), 0.5)
    tongue = _math(nt, 'LESS_THAN', _math(nt, 'ADD', _math(nt, 'MULTIPLY', du, du), _math(nt, 'MULTIPLY', dv, dv)), 1.0)
    inside = _mix(nt, _math(nt, 'MULTIPLY', v, 0.6), (0.09, 0.012, 0.018, 1), (0.25, 0.03, 0.045, 1))
    c = _mix(nt, tongue, inside, hex2lin('#E86A7A'))
    c = _mix(nt, t, c, hex2lin('#FBF7F2'))
    nt.links.new(c, b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.35
    b.inputs['Specular IOR Level'].default_value = 0.4
    return mat
