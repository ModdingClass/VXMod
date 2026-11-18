"""
Finding the Diffeomorphic-imported Genesis 3 Female by what she IS, not by her name (2026-11-18).

Diffeomorphic names the Blender objects after the figure's Daz label: "Genesis 3 Female" (armature) and
"Genesis 3 Female Mesh". VXModExport 1.8+ loads a base character with her own label ("Bela"), so the objects arrive
as "Bela" / "Bela Mesh" and every lookup by name failed ("Genesis 3 Female Armature is not the active object").

Diffeomorphic also stamps every figure object with properties that do not depend on the label
(import_daz: daz.py registers them, node.py / figure.py fill them):
    DazUrl   "/data/DAZ 3D/Genesis 3/Female/Genesis3Female.dsf#Genesis3Female"   (the figure node)
    DazId    the same, percent-encoded and lower-case path
    DazMesh  "Genesis3-female"   (finger.py: fingerprint of the vertex / edge / face counts, on rig AND mesh)
    DazRig   "genesis3"          (rig type; also Genesis 3 Male, so not used alone)

An object WITH Daz properties is judged by them only; an object without any (an older import, a hand-made scene)
falls back to the old name test. The geograft ("Genesis 3 Female Genitalia") has its own URL and fingerprint, so it
never passes as the body. The body mesh clone made by the conversion keeps the properties but has no parent; the
lookups below want the mesh parented to a G3F armature, so the clone is never taken for the original.
"""
import bpy

try:
    from urllib.parse import unquote
except ImportError:  # pragma: no cover - Blender 2.79 ships Python 3.5, which has it
    unquote = lambda s: s

G3F_MESH_FINGERPRINT = "Genesis3-female"
G3F_URL_SUFFIX = "genesis3female.dsf#genesis3female"   # lower-case, spaces removed
G3F_ARMATURE_NAME = "Genesis 3 Female"                  # the name fallback (and Diffeomorphic's default)
G3F_BODY_MESH_NAME = "Genesis 3 Female Mesh"


def _dazProp(ob, name):
    """A Diffeomorphic property as a string ('' when missing): registered bpy prop first, then an ID prop."""
    value = None
    try:
        value = getattr(ob, name, None)
    except Exception:
        value = None
    if not value:
        try:
            value = ob.get(name)
        except Exception:
            value = None
    return str(value) if value else ""


def _hasDazProps(ob):
    return bool(_dazProp(ob, "DazUrl") or _dazProp(ob, "DazId") or _dazProp(ob, "DazMesh"))


def _isG3FByProps(ob):
    if _dazProp(ob, "DazMesh") == G3F_MESH_FINGERPRINT:
        return True
    for name in ("DazUrl", "DazId"):
        url = unquote(_dazProp(ob, name)).lower().replace(" ", "")
        if url.endswith(G3F_URL_SUFFIX):
            return True
    return False


def isG3FArmature(ob):
    """The Diffeomorphic Genesis 3 Female armature, whatever its label in Daz was."""
    if ob is None or ob.type != 'ARMATURE':
        return False
    if _hasDazProps(ob):
        return _isG3FByProps(ob)
    return G3F_ARMATURE_NAME in ob.name


def isG3FBodyMesh(ob):
    """The Diffeomorphic Genesis 3 Female body mesh (not a geograft), whatever its label in Daz was."""
    if ob is None or ob.type != 'MESH':
        return False
    if _hasDazProps(ob):
        return _isG3FByProps(ob)
    return G3F_BODY_MESH_NAME in ob.name


def findG3FBodyMesh(armature=None):
    """
    The original G3F body mesh, or None:
    1. a child of `armature` (or of the active object when that is a G3F armature),
    2. the object named "Genesis 3 Female Mesh" (what the addon always used),
    3. a G3F body mesh parented to a G3F armature (names without a ".001" suffix first).
    """
    if armature is None:
        active = bpy.context.scene.objects.active
        if isG3FArmature(active):
            armature = active
    if armature is not None:
        for child in armature.children:
            if isG3FBodyMesh(child):
                return child
    if G3F_BODY_MESH_NAME in bpy.data.objects:
        return bpy.data.objects[G3F_BODY_MESH_NAME]
    found = [ob for ob in bpy.data.objects if isG3FBodyMesh(ob) and isG3FArmature(ob.parent)]
    found.sort(key=lambda ob: ("." in ob.name[-4:], ob.name))
    return found[0] if found else None


def g3fBodyMeshName():
    """The G3F body mesh's object name, for code that looks it up in bpy.data.objects by name."""
    ob = findG3FBodyMesh()
    return ob.name if ob is not None else G3F_BODY_MESH_NAME
