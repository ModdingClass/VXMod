import bpy
import importlib
from mathutils import Vector

# G3F eye moisture: small 4-vertex-ring tubes along the lower lids. Sculpting the lids leaves them
# behind. Each ring's second vertex (the anchor) follows its lower-lid vertex, the other 3 follow the
# anchor, all by the offsets measured on the base G3F (g3f/g3f_eyemoisture_offsets.py, written by
# Tools/Blender/g3f_eye_moisture_capture.py in the VXMod project).


def loadEyeMoistureRings():
    """EYE_MOISTURE_RINGS, re-read from disk (a fresh capture needs no addon reload); None if missing."""
    try:
        from .g3f import g3f_eyemoisture_offsets
    except ImportError:
        return None
    return importlib.reload(g3f_eyemoisture_offsets).EYE_MOISTURE_RINGS


def fixEyeMoisture(ob, rings):
    """
    Puts every ring back on its lid: anchor = lid + offset, the other 3 = anchor + offset (offsets in
    world space, converted to this object's local space), in the mesh and in every shape key.

    Call it in OBJECT mode. Returns a list of (target name, vertices that moved).
    """
    # The offsets are WORLD space (the base G3F may carry an unapplied import rotation); turn them into
    # this object's local space. Directions only: rotation + scale. 2.79: Matrix * Vector (no @).
    to_local = ob.matrix_world.to_3x3().inverted()
    rings = [(lid, a, to_local * Vector(da), [(v, to_local * Vector(dv)) for v, dv in others])
             for lid, a, da, others in rings]
    targets = [('Mesh', ob.data.vertices)]
    if ob.data.shape_keys:
        targets += [(k.name, k.data) for k in ob.data.shape_keys.key_blocks]
    result = []
    for name, data in targets:
        moved = 0
        for lid, a, da, others in rings:
            anchor = data[lid].co + da
            for v, co in [(a, anchor)] + [(v, anchor + dv) for v, dv in others]:
                if (data[v].co - co).length > 1e-6:
                    moved += 1
                data[v].co = co
        result.append((name, moved))
    ob.data.update()
    return result
