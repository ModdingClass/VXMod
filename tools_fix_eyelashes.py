import bpy
import importlib
from mathutils import Vector

# Follower vertices that sculpting leaves behind, put back at their leader + a base G3F offset
# (WORLD space, written by the capture scripts in Tools/Blender of the VXMod project):
# - eyelashes: twin cards, each primary vertex has a secondary copy a tiny step behind it
#   (EYELASH_PAIRS in g3f/g3f_eyelashes_offsets.py, g3f_eyelash_capture.py).
# - eye moisture on the eyeballs: a film over the sclera/cornea, each vertex follows the nearest
#   sclera/cornea vertex (EYEBALL_MOISTURE_PAIRS in g3f/g3f_eyeball_moisture_offsets.py,
#   g3f_eyeball_moisture_capture.py).


def loadEyelashPairs():
    """EYELASH_PAIRS, re-read from disk (a fresh capture needs no addon reload); None if missing."""
    try:
        from .g3f import g3f_eyelashes_offsets
    except ImportError:
        return None
    return importlib.reload(g3f_eyelashes_offsets).EYELASH_PAIRS


def loadEyeballMoisturePairs():
    """EYEBALL_MOISTURE_PAIRS, re-read from disk; None if missing."""
    try:
        from .g3f import g3f_eyeball_moisture_offsets
    except ImportError:
        return None
    return importlib.reload(g3f_eyeball_moisture_offsets).EYEBALL_MOISTURE_PAIRS


def fixVertexPairs(ob, pairs):
    """
    pairs = {follower: (leader, (dx, dy, dz))}. Puts every follower back at its leader + the base G3F
    offset (world space, converted to this object's local space), in the mesh and in every shape key.

    Call it in OBJECT mode. Returns a list of (target name, vertices that moved).
    """
    # Directions only: rotation + scale. 2.79: Matrix * Vector (no @).
    to_local = ob.matrix_world.to_3x3().inverted()
    offsets = [(s, p, to_local * Vector(d)) for s, (p, d) in pairs.items()]
    targets = [('Mesh', ob.data.vertices)]
    if ob.data.shape_keys:
        targets += [(k.name, k.data) for k in ob.data.shape_keys.key_blocks]
    result = []
    for name, data in targets:
        moved = 0
        for s, p, d in offsets:
            co = data[p].co + d
            if (data[s].co - co).length > 1e-6:
                moved += 1
            data[s].co = co
        result.append((name, moved))
    ob.data.update()
    return result
