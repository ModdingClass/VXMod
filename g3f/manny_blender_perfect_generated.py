"""GENERATED - do not hand edit.

Written by the "Generate BlenderPerfect table" operator in io_unreal_dump_importer.
To change any of it, edit io_unreal_dump_importer/manny_roll_convention.py and run
the operator again.

This is everything io_vxmod_workflow needs to take a BlenderPerfect rig to the
UE5 export orientation, so that addon has no runtime dependency on the dump
importer. Two steps, both bone-local:

    BP  -> BF    roll -= getBpToBfRollDelta(bone)
    BF  -> UE5   matrix *= Rz(-90 if isFlipped(bone) else +90)

then a 180 roll correction over every bone, applied by the exporter - see
apply_ue5_roll_correction there for why.

getBpToBfRollDelta returns None for a bone outside the convention (the Daz
extras: breasts, toes, eyes, ears, teeth, tongue). Both steps skip those, and
callers rely on that, so keep returning None rather than 0.
"""

DEFAULT_ROLL_DELTA = -90.0
FINGER_ROLL_DELTA  = 90.0


def normalizeBoneName(name):
    """thigh.L -> thigh_l. The tables are keyed on the UE-style names the dump
    uses; the VXMod rig names bones the Blender way."""
    if len(name) > 2 and name[-2] == '.':
        side = name[-1].lower()
        if side in ('l', 'r'):
            return name[:-2] + '_' + side
    return name


def getBpToBfRollDelta(name):
    """Degrees to subtract from a BlenderPerfect roll to reach BlenderFriendly,
    or None if this bone is not part of the Manny convention."""
    key = normalizeBoneName(name)
    if key not in _manny_set:
        return None
    return FINGER_ROLL_DELTA if key in _finger_set else DEFAULT_ROLL_DELTA


def isFlipped(name):
    """True if this bone takes -90 rather than +90 on the BF -> UE5 step."""
    return normalizeBoneName(name) in _flipped_set


# Every bone the convention covers. Anything not here is a Daz extra and
# is left alone by both conversion steps.
_manny_bones = [
    "ball_l",
    "ball_r",
    "calf_l",
    "calf_r",
    "calf_twist_01_l",
    "calf_twist_01_r",
    "calf_twist_02_l",
    "calf_twist_02_r",
    "center_of_mass",
    "clavicle_l",
    "clavicle_r",
    "foot_l",
    "foot_r",
    "hand_l",
    "hand_r",
    "head",
    "ik_foot_l",
    "ik_foot_r",
    "ik_foot_root",
    "ik_hand_gun",
    "ik_hand_l",
    "ik_hand_r",
    "ik_hand_root",
    "index_01_l",
    "index_01_r",
    "index_02_l",
    "index_02_r",
    "index_03_l",
    "index_03_r",
    "index_metacarpal_l",
    "index_metacarpal_r",
    "interaction",
    "lowerarm_l",
    "lowerarm_r",
    "lowerarm_twist_01_l",
    "lowerarm_twist_01_r",
    "lowerarm_twist_02_l",
    "lowerarm_twist_02_r",
    "middle_01_l",
    "middle_01_r",
    "middle_02_l",
    "middle_02_r",
    "middle_03_l",
    "middle_03_r",
    "middle_metacarpal_l",
    "middle_metacarpal_r",
    "neck_01",
    "neck_02",
    "pelvis",
    "pinky_01_l",
    "pinky_01_r",
    "pinky_02_l",
    "pinky_02_r",
    "pinky_03_l",
    "pinky_03_r",
    "pinky_metacarpal_l",
    "pinky_metacarpal_r",
    "ring_01_l",
    "ring_01_r",
    "ring_02_l",
    "ring_02_r",
    "ring_03_l",
    "ring_03_r",
    "ring_metacarpal_l",
    "ring_metacarpal_r",
    "root",
    "spine_01",
    "spine_02",
    "spine_03",
    "spine_04",
    "spine_05",
    "thigh_l",
    "thigh_r",
    "thigh_twist_01_l",
    "thigh_twist_01_r",
    "thigh_twist_02_l",
    "thigh_twist_02_r",
    "thumb_01_l",
    "thumb_01_r",
    "thumb_02_l",
    "thumb_02_r",
    "thumb_03_l",
    "thumb_03_r",
    "upperarm_l",
    "upperarm_r",
    "upperarm_twist_01_l",
    "upperarm_twist_01_r",
    "upperarm_twist_02_l",
    "upperarm_twist_02_r",
]

# Fingers take the other roll delta. As imported they are the one group
# that curls on -X while every other joint flexes on +X, and the extra
# 180 is what lines them up.
fingerBones = [
    "index_01_l",
    "index_01_r",
    "index_02_l",
    "index_02_r",
    "index_03_l",
    "index_03_r",
    "index_metacarpal_l",
    "index_metacarpal_r",
    "middle_01_l",
    "middle_01_r",
    "middle_02_l",
    "middle_02_r",
    "middle_03_l",
    "middle_03_r",
    "middle_metacarpal_l",
    "middle_metacarpal_r",
    "pinky_01_l",
    "pinky_01_r",
    "pinky_02_l",
    "pinky_02_r",
    "pinky_03_l",
    "pinky_03_r",
    "pinky_metacarpal_l",
    "pinky_metacarpal_r",
    "ring_01_l",
    "ring_01_r",
    "ring_02_l",
    "ring_02_r",
    "ring_03_l",
    "ring_03_r",
    "ring_metacarpal_l",
    "ring_metacarpal_r",
    "thumb_01_l",
    "thumb_01_r",
    "thumb_02_l",
    "thumb_02_r",
    "thumb_03_l",
    "thumb_03_r",
]

# Bones Epic runs 180 deg from the naive mirror: the spine column, the
# LEFT arm, the RIGHT leg, plus ball_l. These take -90 on the BF -> UE5
# step and everything else takes +90.
#
# Corroborated independently of the predicate that produced it: on the
# reference rig every right-side frame is the left one rotated 180 about
# the world left/right axis, 42 of 42 axes.
flippedBones = [
    "ball_l",
    "calf_r",
    "calf_twist_01_r",
    "calf_twist_02_r",
    "clavicle_l",
    "foot_r",
    "hand_l",
    "head",
    "index_01_l",
    "index_02_l",
    "index_03_l",
    "index_metacarpal_l",
    "lowerarm_l",
    "lowerarm_twist_01_l",
    "lowerarm_twist_02_l",
    "middle_01_l",
    "middle_02_l",
    "middle_03_l",
    "middle_metacarpal_l",
    "neck_01",
    "neck_02",
    "pelvis",
    "pinky_01_l",
    "pinky_02_l",
    "pinky_03_l",
    "pinky_metacarpal_l",
    "ring_01_l",
    "ring_02_l",
    "ring_03_l",
    "ring_metacarpal_l",
    "spine_01",
    "spine_02",
    "spine_03",
    "spine_04",
    "spine_05",
    "thigh_r",
    "thigh_twist_01_r",
    "thigh_twist_02_r",
    "thumb_01_l",
    "thumb_02_l",
    "thumb_03_l",
    "upperarm_l",
    "upperarm_twist_01_l",
    "upperarm_twist_02_l",
]

_manny_set = set(_manny_bones)
_finger_set = set(fingerBones)
_flipped_set = set(flippedBones)
