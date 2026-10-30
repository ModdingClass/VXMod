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


def eyeMoistureTubeVertices():
    """
    The G3F eye moisture TUBES: 26 rings of 4 along the lower lids, 104 vertices (Daz index 17314-17417),
    from the same table Fix eye moisture uses. DAZSPLIT folds EyeMoisture into mat_cornea, but these sit on
    the LIDS, which move in the eyeLook shapes (up to 3.3 mm on Belle): put back to rest with the eyeball
    they part from the lid. The rest of EyeMoisture is the wet film over the eyeball and goes with it.
    Empty when the table is missing.
    """
    from .tools_fix_eye_moisture import loadEyeMoistureRings
    rings = loadEyeMoistureRings() or []
    return set(v for lid, anchor, _, others in rings for v in [anchor] + [o for o, _ in others])


def fixEyeMorphs(ob, key_names=EYE_LOOK_SHAPEKEYS, material_names=EYE_MATERIALS, keep=None):
    """
    Puts the eyeball vertices (every vertex of the given material slots) back to rest in the given
    shape keys, i.e. back where each key's "Relative To" key (normally Basis) has them. The rest of
    each shape (lids, skin) is untouched, and so are the vertices in keep (default: the eye moisture
    tubes, which follow the lids).

    Call it in OBJECT mode. Returns (eyeball vertex count, names of the keys fixed, names not found).
    """
    wanted = set(material_names)
    slots = set(i for i, s in enumerate(ob.material_slots) if s.material and s.material.name in wanted)
    verts = set(v for p in ob.data.polygons if p.material_index in slots for v in p.vertices)
    verts -= eyeMoistureTubeVertices() if keep is None else set(keep)
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
