import bpy

# The ARKit gaze shapes. Their eyeball part fights the eye BONE in Unreal (the gaze node rotates the bone,
# the shape rotates the eyeball again: double travel, the iris went under the lid). The lids and skin
# part of each shape is what should stay.
EYE_LOOK_SHAPEKEYS = [
    'eyeLookUpLeft', 'eyeLookDownLeft', 'eyeLookInLeft', 'eyeLookOutLeft',
    'eyeLookUpRight', 'eyeLookDownRight', 'eyeLookInRight', 'eyeLookOutRight',
]

# Material slots whose vertices are the eyeball (sclera + iris + pupil, and the cornea over it).
EYE_MATERIALS = ['mat_eyes', 'mat_cornea']


def fixEyeMorphs(ob, key_names=EYE_LOOK_SHAPEKEYS, material_names=EYE_MATERIALS):
    """
    Puts the eyeball vertices (every vertex of the given material slots) back to rest in the given
    shape keys, i.e. back where each key's "Relative To" key (normally Basis) has them. The rest of
    each shape (lids, skin) is untouched.

    Call it in OBJECT mode. Returns (eyeball vertex count, names of the keys fixed, names not found).
    """
    wanted = set(material_names)
    slots = set(i for i, s in enumerate(ob.material_slots) if s.material and s.material.name in wanted)
    verts = set(v for p in ob.data.polygons if p.material_index in slots for v in p.vertices)
    fixed = []
    missing = []
    key_blocks = ob.data.shape_keys.key_blocks if ob.data.shape_keys else None
    for name in key_names:
        key = key_blocks.get(name) if key_blocks else None
        if key is None:
            missing.append(name)
            continue
        ref = key.relative_key
        for v in verts:
            key.data[v].co = ref.data[v].co
        fixed.append(name)
    return len(verts), fixed, missing
