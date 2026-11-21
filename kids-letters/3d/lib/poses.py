"""Named poses (bone -> XYZ degrees). Bones use .L/.R for the character's left/right;
the character's right arm is on the viewer's left. Raising an arm sideways: .L +Z, .R -Z."""

POSES = {
    'idle':      {'upper_arm.L': (0, 0, -4), 'upper_arm.R': (0, 0, 4)},
    'wave_a':    {'upper_arm.R': (0, 0, -105), 'fore_arm.R': (0, 0, -48), 'hand.R': (0, 0, -10), 'head': (0, 0, -5),
                  'upper_arm.L': (0, 0, -4)},
    'wave_b':    {'upper_arm.R': (0, 0, -100), 'fore_arm.R': (0, 0, -14), 'hand.R': (0, 0, 12), 'head': (0, 0, -5),
                  'upper_arm.L': (0, 0, -4)},
    'point_up':  {'upper_arm.R': (0, 0, -126), 'fore_arm.R': (0, 0, -6), 'upper_arm.L': (0, 0, 42),
                  'fore_arm.L': (0, 0, -100), 'hand.L': (0, 0, -20), 'head': (0, 0, 4)},
    'cheer':     {'upper_arm.R': (0, 0, -150), 'fore_arm.R': (0, 0, -20), 'upper_arm.L': (0, 0, 150), 'fore_arm.L': (0, 0, 20)},
}


def apply(ch, name, frame=None):
    ch.rest(frame=None)
    for bone, (x, y, z) in POSES[name].items():
        ch.pose(bone, x, y, z)
    if frame is not None:
        for pb in ch.arm.pose.bones:
            pb.keyframe_insert('rotation_euler', frame=frame)
