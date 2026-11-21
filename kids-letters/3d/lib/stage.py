"""A warm late-afternoon courtyard stage, lights, camera with depth of field and Cycles settings."""
import math
import random
import bpy
from mathutils import Vector

from .util import hex2lin, collection, look_matrix
from .parts import lumpy, rounded_box
from . import materials as M


def render_settings(scene, w=1080, h=1920, samples=128, fps=24):
    scene.render.engine = 'CYCLES'
    cy = scene.cycles
    cy.device = 'CPU'
    cy.samples = samples
    cy.use_adaptive_sampling = True
    cy.adaptive_threshold = 0.02
    cy.use_denoising = True
    cy.max_bounces = 6
    cy.diffuse_bounces = 3
    cy.glossy_bounces = 3
    cy.transparent_max_bounces = 4
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.resolution_percentage = 100
    scene.render.fps = fps
    scene.render.film_transparent = False
    scene.render.use_persistent_data = True
    scene.render.image_settings.file_format = 'PNG'
    vs = scene.view_settings
    # PBR Neutral keeps the design palette saturated (AgX washes bright cartoon colors out)
    vs.view_transform = 'Khronos PBR Neutral'
    vs.look = 'None'
    vs.exposure = -0.2


def world_sky(scene, horizon='#F7C99B', zenith='#7FA8D8', strength=0.55):
    w = bpy.data.worlds.new('Sky')
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes['Background']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    ramp.color_ramp.elements[0].position = 0.45
    ramp.color_ramp.elements[0].color = hex2lin(horizon)
    ramp.color_ramp.elements[1].position = 0.75
    ramp.color_ramp.elements[1].color = hex2lin(zenith)
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = strength


def lights(scene, target=Vector((0, 0, 0.8)), key_power=130.0):
    col = collection('Lights')

    def area(name, loc, power, size, hexc):
        ld = bpy.data.lights.new(name, 'AREA')
        ld.energy = power
        ld.size = size
        ld.color = hex2lin(hexc)[:3]
        ob = bpy.data.objects.new(name, ld)
        col.objects.link(ob)
        ob.location = loc
        d = Vector(target) - Vector(loc)
        ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
        return ob

    # warm low sun from behind-left: golden rim light like late afternoon
    sun = bpy.data.lights.new('Sun', 'SUN')
    sun.energy = 2.4
    sun.angle = math.radians(3)
    sun.color = hex2lin('#FFC58A')[:3]
    so = bpy.data.objects.new('Sun', sun)
    col.objects.link(so)
    so.rotation_euler = (math.radians(68), 0, math.radians(-145))
    area('Key', (1.6, -2.4, 2.0), key_power, 1.6, '#FFE2C4')
    area('Fill', (-2.2, -2.0, 1.3), key_power * 0.35, 2.0, '#CFE0FF')
    area('Rim', (-1.2, 1.8, 2.2), key_power * 0.6, 1.0, '#FFD3A0')


def camera(scene, loc, target, lens=50, focus=None, fstop=2.2):
    cd = bpy.data.cameras.new('Camera')
    cd.lens = lens
    cd.sensor_width = 36
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = fstop
    ob = bpy.data.objects.new('Camera', cd)
    scene.collection.objects.link(ob)
    ob.location = loc
    d = Vector(target) - Vector(loc)
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    cd.dof.focus_distance = (Vector(focus or target) - Vector(loc)).length
    scene.camera = ob
    return ob


def courtyard(scene, seed=4):
    """Stone floor, a sandstone wall with bougainvillea, a lemon bush and a string of warm lights.
    Everything sits far enough back to melt into soft bokeh."""
    random.seed(seed)
    col = collection('Set')
    floor_mat = bpy.data.materials.new('Floor')
    floor_mat.use_nodes = True
    nt = floor_mat.node_tree
    b = nt.nodes['Principled BSDF']
    br = nt.nodes.new('ShaderNodeTexBrick')
    br.inputs['Color1'].default_value = hex2lin('#D9B994')
    br.inputs['Color2'].default_value = hex2lin('#C9A27B')
    br.inputs['Mortar'].default_value = hex2lin('#A98962')
    br.inputs['Scale'].default_value = 1.6
    br.inputs['Mortar Size'].default_value = 0.012
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nt.links.new(tc.outputs['Object'], br.inputs['Vector'])
    nt.links.new(br.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.75
    me = bpy.data.meshes.new('Floor')
    me.from_pydata([(-12, -12, 0), (12, -12, 0), (12, 12, 0), (-12, 12, 0)], [], [(0, 1, 2, 3)])
    fl = bpy.data.objects.new('Floor', me)
    col.objects.link(fl)
    me.materials.append(floor_mat)

    # Jerusalem-stone wall with large blocks
    wall = bpy.data.materials.new('Wall')
    wall.use_nodes = True
    wn = wall.node_tree
    wb = wn.nodes['Principled BSDF']
    wbr = wn.nodes.new('ShaderNodeTexBrick')
    wbr.inputs['Color1'].default_value = hex2lin('#EAD5B2')
    wbr.inputs['Color2'].default_value = hex2lin('#DDC398')
    wbr.inputs['Mortar'].default_value = hex2lin('#C7AC84')
    wbr.inputs['Scale'].default_value = 1.2
    wbr.inputs['Mortar Size'].default_value = 0.01
    wbr.inputs['Row Height'].default_value = 0.35
    wbr.inputs['Brick Width'].default_value = 0.7
    wtc = wn.nodes.new('ShaderNodeTexCoord')
    wmap = wn.nodes.new('ShaderNodeMapping')
    wmap.inputs['Rotation'].default_value = (1.5708, 0, 0)
    wn.links.new(wtc.outputs['Object'], wmap.inputs['Vector'])
    wn.links.new(wmap.outputs['Vector'], wbr.inputs['Vector'])
    wn.links.new(wbr.outputs['Color'], wb.inputs['Base Color'])
    wb.inputs['Roughness'].default_value = 0.9
    rounded_box('Wall', col, (0, 6.2, 1.6), (14, 0.4, 3.2), wall, bevel=0.02, subsurf=1)

    # blue arched door, a little right of center
    door = M.plain('Door', '#2F6DB5', rough=0.55)
    frame = M.plain('DoorFrame', '#D2B88E', rough=0.85)
    rounded_box('DoorFrame', col, (0.55, 5.98, 1.05), (1.2, 0.1, 2.1), frame, bevel=0.05, subsurf=1)
    rounded_box('Door', col, (0.55, 5.94, 1.0), (0.98, 0.08, 1.95), door, bevel=0.05, subsurf=1)
    knob = M.plain('Knob', '#D9A93C', rough=0.3, metallic=1.0)
    lumpy('Knob', col, (0.9, 5.88, 1.0), 0.035, knob, amp=0.0, subdiv=2)

    purple = M.plain('Bougainvillea', '#B23A9E', rough=0.7)
    pink = M.plain('Bougainvillea2', '#E0539C', rough=0.7)
    leaf = M.plain('Leaf', '#4E8A3A', rough=0.6)
    leaf2 = M.plain('Leaf2', '#6FA845', rough=0.6)
    lemon = M.plain('Lemon', '#F2D23C', rough=0.4)
    # bougainvillea spilling over the top-left of the wall
    for i in range(70):
        x = -2.6 + random.random() * 2.7
        z = 3.2 - random.random() ** 1.6 * 1.8 + (0.0 if x < -0.6 else -0.0)
        z = min(z, 3.35)
        m = (purple, pink, leaf)[i % 5 % 3] if i % 5 else leaf
        lumpy(f'flower_{i}', col, (x, 5.85 - random.random() * 0.25, z), 0.1 + random.random() * 0.1, m, seed=i * 1.3, amp=0.3)
    # lemon tree on the right
    bark = M.plain('Bark', '#7A5A3A', rough=0.9)
    from .parts import capsule
    capsule('Trunk', col, (1.9, 5.2, 0.0), (1.85, 5.2, 1.3), 0.08, 0.06, bark)
    for i in range(30):
        lumpy(f'tree_{i}', col, (1.4 + random.random() * 1.2, 5.0 + random.random() * 0.5, 1.2 + random.random() * 1.3),
              0.18 + random.random() * 0.14, leaf if i % 3 else leaf2, seed=i * 2.1, amp=0.3)
    for i in range(14):
        lumpy(f'lemon_{i}', col, (1.35 + random.random() * 1.2, 4.75 + random.random() * 0.3, 1.25 + random.random() * 1.2),
              0.055, lemon, seed=i, amp=0.05, squash=(1, 1, 1.25), subdiv=2)
    # string of warm lights
    bulb = M.emission('Bulb', '#FFD9A0', strength=25)
    for i in range(30):
        t = i / 29
        x = -3.0 + 6.0 * t
        z = 2.75 - 0.4 * math.sin(math.pi * t)
        lumpy(f'bulb_{i}', col, (x, 5.4, z), 0.035, bulb, amp=0.0, subdiv=2, subsurf=0)
    # terracotta pots along the wall
    planter = M.plain('Planter', '#B86B45', rough=0.8)
    for k, (px, py) in enumerate(((-1.25, 5.2), (-0.35, 5.35))):
        rounded_box(f'Planter_{k}', col, (px, py, 0.22), (0.45, 0.45, 0.44), planter, bevel=0.2)
        for i in range(5):
            lumpy(f'plant_{k}_{i}', col, (px + (random.random() - 0.5) * 0.4, py + (random.random() - 0.5) * 0.2, 0.55 + random.random() * 0.3),
                  0.14 + random.random() * 0.07, leaf if i % 2 else leaf2, seed=i * 3.7 + k, amp=0.3)
    return col
