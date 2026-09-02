import bpy
import re

from ..g3f.difeomorphic_workflow_convert_body import *
from ..g3f.difeomorphic_workflow_init_custom_face_indices import *
from ..g3f.difeomorphic_workflow_init_geografts import *
from ..tools_message_box import *
from ..utils_bpy import *


def checkIfMaterialExistElseCreateIt(ob, material_name):
    mat = bpy.data.materials.get(material_name)
    #if it doesnt exist, create it.
    if mat is None:
        # create material
        mat = bpy.data.materials.new(name=material_name)
        #assign material
    if mat.name not in ob.material_slots.keys():
        ob.data.materials.append(mat) 
    index = bpy.context.object.material_slots.find(mat.name)    
    return mat,index

def _materialSlotsAreDataLinked(ob):
    """The fast paths below rewrite ob.data.materials, which only mirrors the object's
    slots while every slot is DATA-linked. Diffeomorphic imports always are, but check
    rather than assume - the callers fall back to the operator path if not."""
    for slot in ob.material_slots:
        if slot.link != 'DATA':
            return False
    return True


def _remapPolygonMaterialIndices(mesh, remap, fallback=0):
    """Bulk-rewrite every polygon's material_index through `remap`.

    foreach_get/foreach_set move the whole array in C, so this is one pass over the mesh
    rather than a Python loop, and it triggers no scene update.
    """
    count = len(mesh.polygons)
    if not count:
        return
    indices = [0] * count
    mesh.polygons.foreach_get("material_index", indices)
    mesh.polygons.foreach_set("material_index",
                              [remap.get(i, fallback) for i in indices])


def rebuildMaterialSlots(ob, keep_indices):
    """Reorder and/or prune material slots without a single bpy.ops call.

    `keep_indices` is the list of CURRENT slot indices to keep, in the order wanted.
    Polygons on a dropped slot fall back to slot 0.

    This replaces material_slot_remove / material_slot_move loops. Each of those is an
    operator, and bpy/ops.py runs a full scene.update() after every operator - measured
    at 53 ms in this scene, which is where ~98% of the conversion's runtime was going.
    """
    mesh = ob.data
    old_materials = [m for m in mesh.materials]
    remap = {}
    for new_index, old_index in enumerate(keep_indices):
        remap[old_index] = new_index

    while len(mesh.materials):
        mesh.materials.pop(index=len(mesh.materials) - 1, update_data=False)
    for old_index in keep_indices:
        mesh.materials.append(old_materials[old_index])

    _remapPolygonMaterialIndices(mesh, remap, fallback=0)
    ob.active_material_index = 0


_MATERIAL_BLENDER_DUPLICATE_SUFFIX = re.compile(r"\.\d{3}$")
_MATERIAL_DIFFEOMORPHIC_SUFFIX = re.compile(r"-\d+$")


def normalizeMaterialName(name):
    """Strip the suffixes bolted onto a material name, leaving the Daz surface name.

    Two different suffixes stack up on these imports:

      - Diffeomorphic appends "-N" to every surface it brings in, so the body arrives
        as Eyelashes-1, Fingernails-1, Toenails-1 and so on. There is no mode in which
        the plain name shows up, so any comparison against a bare Daz surface name has
        to account for it.
      - Blender appends ".NNN" whenever a datablock name collides, which the material
        copy step at the top of the conversion triggers - Eyelashes-1 -> Eyelashes-1.001.

    ".NNN" is stripped first because it lands on the outside.
    """
    base = _MATERIAL_BLENDER_DUPLICATE_SUFFIX.sub("", name)
    return _MATERIAL_DIFFEOMORPHIC_SUFFIX.sub("", base)


def _slotIndicesMatchingPrefixes(ob, prefixes):
    """Slot indices whose name startswith any prefix - the match the original
    removeMaterialListFromObject and selectByMaterials both used.

    Now tested against the NORMALIZED name as well as the raw one, so the "-N" suffix
    Diffeomorphic adds cannot defeat a comparison. Raw startswith already absorbed a
    trailing suffix on the SLOT side by luck (Eyelashes-1 startswith Eyelashes); the
    normalized pass is what handles a suffix on the PREFIX side, and it makes the
    tolerance deliberate rather than incidental.

    Strictly additive - every prefix that matched before still matches.
    """
    normalized_prefixes = [normalizeMaterialName(p) for p in prefixes]
    matched = []
    for index, slot in enumerate(ob.material_slots):
        raw_name = slot.name
        base_name = normalizeMaterialName(raw_name)
        for prefix, normalized_prefix in zip(prefixes, normalized_prefixes):
            if raw_name.startswith(prefix) or base_name.startswith(normalized_prefix):
                matched.append(index)
                break
    return matched


def removeMaterialListFromObject(ob, deletion_list):
    """Drop every material slot whose name starts with an entry in deletion_list.

    Same signature and semantics as before; the operator loop is gone. This was the
    single most expensive helper in the conversion - 10 calls, 5.96 s.
    """
    if not _materialSlotsAreDataLinked(ob):
        _removeMaterialListFromObjectSlow(ob, deletion_list)
        return

    doomed = set(_slotIndicesMatchingPrefixes(ob, deletion_list))
    if not doomed:
        return
    keep = [i for i in range(len(ob.material_slots)) if i not in doomed]
    rebuildMaterialSlots(ob, keep)


def _removeMaterialListFromObjectSlow(ob, deletion_list):
    """Original operator-based implementation, kept as a fallback for the
    OBJECT-linked-slot case the fast path cannot handle."""
    saved_context_mode = ob.mode
    #
    bpy.ops.object.mode_set(mode='OBJECT')
    #
    materials_list = bpy.context.object.material_slots.keys()
    del_slots = []
    for mat in materials_list:
        for del_mat in deletion_list:
            if mat.startswith(del_mat):
                del_index = bpy.context.object.material_slots.find(mat)
                del_slots.append(del_index)
    #
    for i in reversed(range(len(ob.material_slots))):
        if i in del_slots:
            ob.active_material_index = i
            bpy.ops.object.material_slot_remove()

    bpy.ops.object.mode_set(mode=saved_context_mode)
    #

def reassignMaterialsAndRemoveSlots(ob, source_prefixes, target_material_name):
    """Move every polygon on a source slot onto `target_material_name`, then drop the
    now-unused source slots.

    Operator-free equivalent of the block that was repeated nine times:

        selectByMaterials(ob, working_mats)          # EDIT mode + material_slot_select
        mat, i = checkIfMaterialExistElseCreateIt(ob, target)
        bpy.context.object.active_material_index = i
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.material_slot_assign()
        bpy.ops.mesh.select_all(action='DESELECT')
        removeMaterialListFromObject(ob, working_mats)

    Nine of those cost roughly 80 operator calls and, at ~53 ms of scene update each,
    the bulk of the conversion's runtime.
    """
    if not _materialSlotsAreDataLinked(ob):
        selectByMaterials(ob, source_prefixes)
        mat, mat_index = checkIfMaterialExistElseCreateIt(ob, target_material_name)
        bpy.context.object.active_material_index = mat_index
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.material_slot_assign()
        bpy.ops.mesh.select_all(action='DESELECT')
        removeMaterialListFromObject(ob, source_prefixes)
        return

    source_indices = _slotIndicesMatchingPrefixes(ob, source_prefixes)
    reassignMaterialSlotIndices(ob, source_indices, target_material_name)


def reassignMaterialSlotIndices(ob, source_indices, target_material_name):
    """Index-based twin of reassignMaterialsAndRemoveSlots.

    For callers that already know which slots they want. Skipping the name round-trip
    matters because material names here carry two layers of suffix (see
    normalizeMaterialName) - a caller that has indices should never have to convert them
    to names and match them back.
    """
    source_indices = set(source_indices)
    if not _materialSlotsAreDataLinked(ob):
        # The operator fallback can only address slots by name.
        names = [ob.material_slots[i].name for i in sorted(source_indices)]
        if names:
            reassignMaterialsAndRemoveSlots(ob, names, target_material_name)
        return

    # Appends at the end if the target is new, so indices captured by the caller stay
    # valid - but the target is then never one of its own sources.
    mat, target_index = checkIfMaterialExistElseCreateIt(ob, target_material_name)
    source_indices.discard(target_index)

    if source_indices:
        remap = dict((i, target_index) for i in source_indices)
        mesh = ob.data
        count = len(mesh.polygons)
        indices = [0] * count
        mesh.polygons.foreach_get("material_index", indices)
        mesh.polygons.foreach_set("material_index",
                                  [remap.get(i, i) for i in indices])

    keep = [i for i in range(len(ob.material_slots)) if i not in source_indices]
    if len(keep) != len(ob.material_slots):
        rebuildMaterialSlots(ob, keep)


def selectByMaterials(ob, selection_list):
    #reload the materials list
    materials_list = bpy.context.object.material_slots.keys()
    saved_context_mode = ob.mode
    bpy.ops.object.mode_set(mode='EDIT')  # we need to be in EDIT mode so we can select vertices from materials
    #
    #g3f body has too many vertices that we don't need, so we are going to select them based on materials and remove them
    mat_slots = []
    for mat in materials_list:
        for sel_mat in selection_list:
            if mat.startswith(sel_mat):
                mat_index = bpy.context.object.material_slots.find(mat)
                bpy.context.object.active_material_index = mat_index
                bpy.ops.object.material_slot_select()
    bpy.ops.object.mode_set(mode=saved_context_mode)



# ---------------------------------------------------------------------------
# Material conversion modes
#
# Three ways to turn the Daz surface list into game materials, picked in the panel
# under the "G3F -> VX body" button and passed in as `material_mode`:
#
#   DAZ       leave the stock Daz surfaces exactly as imported
#   LEGACY    the original vxmod collapse into the 21 body_* game materials
#   FULLBODY  one material for the whole body, minus two exceptions
#
# Whatever the mode, the mesh always ends up with the placeholder materials and with the
# censor region on its own slot - see ensurePlaceholderMaterials and assignCensorFaces.
# ---------------------------------------------------------------------------

# Daz surfaces that make up the eye interior. LEGACY folds these into body_head01 and
# relies on them ending up hidden inside the skull; FULLBODY gives them their own
# DONT_RENDER material instead, so Unreal can drop them outright.
# Matched against the bare Daz names - Diffeomorphic imports them suffixed.
EYE_INTERIOR_MATERIALS = ["Cornea", "Pupils", "Sclera", "Irises", "EyeMoisture"]

# Kept out of every merge: this one needs a translucent material in Unreal, so it
# cannot share a slot with opaque skin.
EYELASH_MATERIALS = ["Eyelashes"]

# --- Material names, per mode -----------------------------------------------
#
# TWO schemes, not three.
#
# LEGACY keeps the body_* names it has always had. They are the keys the legacy engine
# tables look up - dictionary_materials.stock_materials (duplicated in
# helper_material_lists_lookup) and importer_g3f - so they are frozen. Renaming them
# would mean editing four places in lockstep for no gain on the Unreal side.
#
# DAZ and FULLBODY share a "modern" scheme:
#   - a mat_ prefix marking the material as VX-authored, the same idea as the _joint0N
#     suffix on VX-authored bones
#   - no numeric suffix; body_eyelash01's "01" never had an 02
#   - no vestigial words. "main" in body_main_censor came from the body_main_upper /
#     body_main_lower family, which does not exist here, so it is dropped.
#
# DONT_RENDER is deliberately NOT prefixed and deliberately shouty. It is a delete-me
# marker; it should look nothing like the materials that are kept.
LEGACY_MATERIAL_NAMES = {
    'fullbody': None,        # LEGACY has no single body material
    'dont_render': None,     # LEGACY hides the eye interior inside the head instead
    'eyelashes': "body_eyelash01",
    'censor': "body_main_censor",
    'genital': "body_genital01",
}

MODERN_MATERIAL_NAMES = {
    'fullbody': "mat_fullbody",
    'dont_render': "DONT_RENDER",
    'eyelashes': "mat_eyelashes",
    'censor': "mat_censor",
    'genital': "mat_genital",
}


def materialNamesForMode(material_mode):
    """The name table for a mode. LEGACY has its own; DAZ and FULLBODY share modern."""
    if material_mode == 'LEGACY':
        return LEGACY_MATERIAL_NAMES
    return MODERN_MATERIAL_NAMES


def ensurePlaceholderMaterials(ob, material_mode):
    """Guarantee the runtime-swap placeholder slots exist. Assigns no faces itself.

    Mode-aware, because the two schemes must not both appear on one mesh - creating the
    modern names unconditionally would leave LEGACY carrying mat_censor AND
    body_main_censor, two slots for one region.

    The censor material is given faces immediately afterwards by assignCensorFaces. The
    genital material stays empty on the body mesh in DAZ and FULLBODY; in LEGACY it
    already carries faces from that mode's Genitalia remap.
    """
    names = materialNamesForMode(material_mode)
    for key in ('censor', 'genital'):
        material_name = names[key]
        if material_name:
            checkIfMaterialExistElseCreateIt(ob, material_name)


def assignFacesToMaterial(ob, face_indices, material_name):
    """Move the listed POLYGONS onto `material_name`, creating the slot if needed.

    Face indices, not vertex indices - see difeomorphic_workflow_init_custom_face_indices.

    Out-of-range indices are counted and reported rather than raised. A figure whose
    topology does not match should produce a loud console line, not abort a conversion
    that is otherwise fine.

    Returns the number of faces actually assigned.
    """
    if not face_indices:
        return 0

    mat, _created_index = checkIfMaterialExistElseCreateIt(ob, material_name)

    # Resolve the slot index from `ob` ITSELF. checkIfMaterialExistElseCreateIt reads
    # bpy.context.object, which is not guaranteed to be `ob` - if the context has drifted
    # it returns -1, and writing -1 into material_index would silently point every listed
    # polygon at the wrong slot instead of failing.
    target_index = ob.material_slots.find(mat.name)
    if target_index < 0:
        print("assignFacesToMaterial: \"{0}\" is not a slot on {1} - nothing assigned"
              .format(mat.name, ob.name))
        return 0

    mesh = ob.data
    polygon_count = len(mesh.polygons)
    indices = [0] * polygon_count
    mesh.polygons.foreach_get("material_index", indices)

    assigned = 0
    out_of_range = 0
    for face_index in face_indices:
        if 0 <= face_index < polygon_count:
            indices[face_index] = target_index
            assigned += 1
        else:
            out_of_range += 1
    mesh.polygons.foreach_set("material_index", indices)

    if out_of_range:
        print("assignFacesToMaterial: {0} of {1} indices are outside the mesh "
              "({2} polygons) - wrong topology for \"{3}\"?".format(
                  out_of_range, len(face_indices), polygon_count, material_name))
    print("assignFacesToMaterial: {0} faces -> {1} (slot {2})".format(
        assigned, material_name, target_index))
    return assigned


def assignCensorFaces(ob, material_mode, geograft_names):
    """Put the censor region on its own slot, in every material mode.

    The faces come off whatever material otherwise owned them - body_main_upper in
    LEGACY, mat_fullbody in FULLBODY, the stock Daz surface in DAZ - which is the point:
    the region has to be its own slot for Unreal to swap what renders there without
    touching the rest of the body.

    WHICH faces depends on the GEOGRAFT, not on the material mode. The region has to
    cover the graft's footprint and the body around it, so the indices are only
    meaningful paired with one specific geograft - see
    difeomorphic_workflow_init_custom_face_indices.censor_faces_by_geograft.

    With no geograft, or one with no entry in that table, nothing is assigned. The
    material slot still exists (ensurePlaceholderMaterials made it), just empty, so the
    Unreal side keeps its guarantee that the slot is there. Borrowing a face set from a
    different geograft would put the censor in the wrong place, which is worse than an
    empty slot.
    """
    material_name = materialNamesForMode(material_mode)['censor']

    if not geograft_names:
        print("assignCensorFaces: no geograft on this body - {0} left empty".format(
            material_name))
        return 0

    # A body can carry several geografts at once, so the region is the UNION of what
    # each contributes. Sorted so the assignment is order-independent.
    face_indices = set()
    contributors = []
    for geograft_name in geograft_names:
        faces = censorFacesForGeograft(geograft_name)
        if faces is None:
            print("assignCensorFaces: no censor face table for geograft \"{0}\" - it "
                  "contributes nothing. Add one to censor_faces_by_geograft.".format(
                      geograft_name))
            continue
        face_indices.update(faces)
        contributors.append(geograft_name)

    if not face_indices:
        print("assignCensorFaces: no geograft on this body has a censor face table - "
              "{0} left empty".format(material_name))
        return 0

    print("assignCensorFaces: from {0}".format(contributors))
    return assignFacesToMaterial(ob, sorted(face_indices), material_name)


# ---------------------------------------------------------------------------
# Geografts
#
# Discovery mirrors import_daz's own getAnatomies(): a mesh is a geograft iff its data
# carries a non-empty DazGraftGroup, and it belongs to THIS body iff its DazVertexCount
# equals the body's vertex count. That is the authoritative test - it finds genitalia,
# tails, wings, vampire teeth and anything else, with no name list to maintain.
# ---------------------------------------------------------------------------

_GEOGRAFT_PREFIX_RE = re.compile(r"^geograft_\d+_")
_GEOGRAFT_UNSAFE_CHARS_RE = re.compile(r"[^0-9A-Za-z]+")
_OBJECT_DUPLICATE_SUFFIX_RE = re.compile(r"(\.\d{3})+$")


def normalizeObjectName(name):
    """Strip Blender's ".NNN" duplicate suffix from an OBJECT name.

    For geografts this is the NORMAL case, not an edge case. A geograft is imported as a
    figure in its own right: an ARMATURE named "Genesis 3 Female Genitalia" plus its child
    MESH. The armature claims the bare name first, so the mesh - the object we actually
    care about - is left with "Genesis 3 Female Genitalia.001". One geograft, two objects,
    and the interesting one always carries the suffix.

    Which number lands on the mesh depends on Blender's collision resolution and on how
    many objects already hold the name, so it cannot be assumed to be .001. The suffix can
    also stack (.001.001) when objects are appended between files, hence the repeat in the
    pattern. Normalizing gets back to the figure name, which is what the profile and
    censor tables are keyed by.

    (This is also why the old substring lookup worked: "Genesis 3 Female Genitalia" IS a
    substring of "...Genitalia.001". Moving to exact-key tables is what broke it.)

    Object names do NOT carry Diffeomorphic's "-N" material suffix, so only ".NNN" comes
    off here. normalizeMaterialName strips both and must not be reused for objects: a
    geograft legitimately named "Tail-2" would lose its "-2".
    """
    return _OBJECT_DUPLICATE_SUFFIX_RE.sub("", name)


def geograftTableKey(table, object_name):
    """The key in `table` matching `object_name`, by PREFIX. Longest key wins.

    Prefix rather than exact, because the object name a geograft's mesh ends up with is
    not something we control. It is the figure name plus whatever Blender and Daz bolt
    on - ".001" because the geograft's own armature took the bare name first, and
    sometimes a descriptive tail as well. A prefix match absorbs all of that from one
    table entry.

    Longest key wins so a more specific entry can be added later without the shorter one
    shadowing it: with both "Genesis 3 Female Genitalia" and "Genesis 3 Female Genitalia
    2" listed, the second no longer silently resolves to the first.

    Tried against the normalized name and the raw one, so a key that itself carries a
    suffix still matches.
    """
    normalized = normalizeObjectName(object_name)
    best_key = None
    for key in table:
        if normalized.startswith(key) or object_name.startswith(key):
            if best_key is None or len(key) > len(best_key):
                best_key = key
    return best_key


def geograftProfile(object_name):
    """Profile for a geograft, matched by name prefix."""
    key = geograftTableKey(geograft_profiles, object_name)
    return geograft_profiles[key] if key else None


def censorFacesForGeograft(object_name):
    """Censor face indices for a geograft, matched by name prefix."""
    key = geograftTableKey(censor_faces_by_geograft, object_name)
    return censor_faces_by_geograft[key] if key else None


def isGeograft(ob, body_vertex_count):
    """True if `ob` is a geograft fitting a body with `body_vertex_count` vertices."""
    if ob is None or ob.type != 'MESH':
        return False
    if not hasattr(ob.data, "DazGraftGroup"):
        # Diffeomorphic not enabled - no geograft data to read at all.
        return False
    if len(ob.data.DazGraftGroup) == 0:
        return False
    return ob.data.DazVertexCount == body_vertex_count


def geograftShortName(original_name):
    """The fragment after the geograft_<N>_ prefix.

    From the profile table when the geograft is known; otherwise the object name with
    everything non-alphanumeric collapsed to underscores. Any existing geograft_<N>_
    prefix is stripped first, so re-running never produces geograft_0_geograft_0_genz.
    """
    profile = geograftProfile(original_name)
    if profile and profile.get("short_name"):
        return profile["short_name"]

    # .NNN comes off first, or an unlisted "Dragon Tail.001" becomes Dragon_Tail_001.
    stripped = _GEOGRAFT_PREFIX_RE.sub("", normalizeObjectName(original_name))
    safe = _GEOGRAFT_UNSAFE_CHARS_RE.sub("_", stripped).strip("_")
    return safe if safe else "geograft"


def sortGeografts(geograft_objects):
    """Deterministic order: profile `order` first, then object name as tie-break.

    Determinism is the whole point - see the ORDER note in
    difeomorphic_workflow_init_geografts. Unlisted geografts sort after every listed one
    and alphabetically among themselves, so adding one never renumbers the others.
    """
    def sort_key(ob):
        profile = geograftProfile(ob.name)
        order = profile.get("order", GEOGRAFT_UNKNOWN_ORDER) if profile \
            else GEOGRAFT_UNKNOWN_ORDER
        # Normalized name as the tie-break so "X" and "X.001" sort adjacently, with the
        # raw name last to keep the ordering total.
        return (order, normalizeObjectName(ob.name), ob.name)
    return sorted(geograft_objects, key=sort_key)


def findGeografts(root_object, body_mesh_object):
    """Every geograft under `root_object` that fits `body_mesh_object`, in sorted order."""
    children = []
    getChildrenRecursive(root_object, children, 0, levels=10)
    body_vertex_count = len(body_mesh_object.data.vertices)
    found = [c for c in children
             if c is not body_mesh_object and isGeograft(c, body_vertex_count)]
    return sortGeografts(found)


def assignGeograftNames(geograft_clones):
    """Rename every clone, numbering sequentially and keeping short names UNIQUE.

    `geograft_clones` is a list of (original_name, clone) already in sorted order.

    Uniqueness matters because the short names are joined into the exported merged mesh
    name. A scene holding both "Genesis 3 Female Genitalia" and a leftover
    "...Genitalia.001" normalizes both to the same profile, so without this they would
    both become "genz" and the export would read Belle_genz_genz - two identical
    fragments with no way to tell afterwards which file belonged to which graft.
    """
    used = {}
    names = []
    for index, (original_name, clone) in enumerate(geograft_clones):
        short_name = geograftShortName(original_name)
        seen = used.get(short_name, 0)
        used[short_name] = seen + 1
        if seen:
            print("assignGeograftNames: short name \"{0}\" already taken by an earlier "
                  "geograft - duplicate in the scene?".format(short_name))
            short_name = "{0}_{1}".format(short_name, seen + 1)
        names.append(renameGeograft(clone, short_name, index))
    return names


def renameGeograft(ob, short_name, index):
    """Rename to geograft_<index>_<short_name>, the convention the exporter reads.

    exporter_unreal.get_geograft_children matches `^geograft_(\\d+)_` among the body
    mesh's children and sorts by that number; get_refined_geograft_names strips the
    prefix and joins what is left into the merged mesh name. Doing the rename here means
    the export convention no longer depends on remembering to rename by hand - and it
    removes the trap where a hand-renamed geograft became invisible to this conversion.
    """
    new_name = "geograft_{0}_{1}".format(index, short_name)
    ob.name = new_name
    ob.data.name = "M_" + new_name
    return new_name


def applyGeograftMaterial(ob, original_name, material_mode):
    """Replace the geograft's material slots with the one its profile names.

    Only for geografts whose profile has a `material_role`. Anything else keeps its own
    materials - correct default for a tail or wings, which have textures worth keeping,
    and which have no reason to land on the body's genital slot.
    """
    profile = geograftProfile(original_name)
    if not profile or not profile.get("material_role"):
        print("applyGeograftMaterial: {0} keeps its own materials".format(ob.name))
        return None

    material_name = materialNamesForMode(material_mode)[profile["material_role"]]
    if not material_name:
        return None

    setActiveObject(ob)
    activateObject(ob)
    for i in reversed(range(len(ob.material_slots))):
        ob.active_material_index = i
        bpy.ops.object.material_slot_remove()

    mat = bpy.data.materials.get(material_name)
    if mat is None:
        mat = bpy.data.materials.new(name=material_name)
    ob.data.materials.append(mat)
    print("applyGeograftMaterial: {0} -> {1}".format(ob.name, material_name))
    return material_name


def tagMaterialEngineIds(material_name, localname, objectname):
    """Stamp the legacy engine ids onto a material, if that material exists.

    Guarded on purpose. body_teeth01 only exists in LEGACY - FULLBODY merges the mouth
    into the body material and DAZ never renames anything - so the original unguarded
    bpy.data.materials["body_teeth01"] would raise KeyError in both new modes.
    """
    mat = bpy.data.materials.get(material_name)
    if mat is None:
        return
    mat["localname"] = localname
    mat["objectname"] = objectname


def applyLegacyMaterialConversion(ob):
    """The original collapse: Daz surfaces onto the 21 body_* game material names."""
    #g3f body has too many vertices that we don't need, so we are going to select them based on materials and remove them
    #the eye interior is folded into the head material rather than deleted; it ends up
    #hidden inside the head and is fixed later with an aa (auto apply) shapekey
    working_mats = EYE_INTERIOR_MATERIALS
    reassignMaterialsAndRemoveSlots(ob, working_mats, "body_head01")

    #
    removeMaterialListFromObject(ob, EYE_INTERIOR_MATERIALS)
    #

    #
    working_mats = ["EyeSocket", "Ears", "Lips","Face"]
    reassignMaterialsAndRemoveSlots(ob, working_mats, "body_head01")

    working_mats = ["Mouth", "Teeth"]
    reassignMaterialsAndRemoveSlots(ob, working_mats, "body_teeth01")

    #
    working_mats = ["Arms"]
    reassignMaterialsAndRemoveSlots(ob, working_mats, "body_hand01_L")

    working_mats = ["Torso"]
    reassignMaterialsAndRemoveSlots(ob, working_mats, "body_main_upper")

    working_mats = ["Toenails", "Legs" ]
    reassignMaterialsAndRemoveSlots(ob, working_mats, "body_foot_L")

    working_mats = ["Genitalia"]
    reassignMaterialsAndRemoveSlots(ob, working_mats, "body_genital01")

    working_mats = EYELASH_MATERIALS
    reassignMaterialsAndRemoveSlots(ob, working_mats, "body_eyelash01")


    working_mats = ["Fingernails"]
    reassignMaterialsAndRemoveSlots(ob, working_mats, "body_fingernails_L.001")


def applyFullBodyMaterialConversion(ob):
    """Collapse the whole body onto one material, with two exceptions.

    Exception 1 - eyelashes keep their own material, because Unreal needs translucency
                  on them and that cannot be shared with the skin.
    Exception 2 - the eye interior goes to DONT_RENDER, so Unreal can skip it entirely
                  rather than hiding it inside the head the way LEGACY does.

    The merge is decided by EXCLUSION, not by listing Daz surface names: anything that
    is not protected is swept into the body material. A custom or non-stock surface is
    then folded in too, instead of being silently left as its own slot.
    """
    # FULLBODY is always the modern scheme - mat_fullbody / mat_eyelashes / DONT_RENDER.
    names = MODERN_MATERIAL_NAMES

    # The two exceptions first, by name. This is the ONLY name matching in the whole
    # pass, and it is against bare Daz surface names ("Eyelashes", "Cornea"), which
    # Diffeomorphic imports suffixed ("Eyelashes-1") - _slotIndicesMatchingPrefixes
    # normalizes for that.
    reassignMaterialsAndRemoveSlots(ob, EYE_INTERIOR_MATERIALS, names['dont_render'])
    reassignMaterialsAndRemoveSlots(ob, EYELASH_MATERIALS, names['eyelashes'])

    # Everything still standing goes to the body material. Computed AFTER the two calls
    # above, because each of them drops slots and shifts every index behind them - and
    # by index, so the bulk merge never compares a name at all.
    #
    # Only the three target names are protected here. They are ours, not Daz's, so the
    # suffix problem does not arise; the prefix form still covers a ".001" duplicate.
    protected_indices = set(_slotIndicesMatchingPrefixes(
        ob, [names['eyelashes'], names['dont_render'], names['fullbody']]))
    merge_indices = [index for index in range(len(ob.material_slots))
                     if index not in protected_indices]
    if merge_indices:
        reassignMaterialSlotIndices(ob, merge_indices, names['fullbody'])


def ensureLegacyGameMaterials(ob):
    """Make sure all 21 legacy body_* materials exist as slots, creating empties.

    LEGACY only. The other modes do not have a fixed material table to fill in, and
    get just the two placeholders from ensurePlaceholderMaterials instead.
    """
    game_material_names = [
    'body_teeth01',
    'body_leg_lower_R',
    'body_leg_lower_L',
    'body_main_lower',
    'body_arm_lower_R',
    'body_arm_lower_L',
    'body_fingernails_R',
    'body_arm_upper_R',
    'body_arm_upper_L',
    'body_leg_upper_R',
    'body_leg_upper_L',
    'body_foot_L',
    'body_hand01_L',
    'body_genital01',
    'body_head01',
    'body_main_upper',
    'body_main_censor',
    'body_hand01_R',
    'body_foot_R',
    'body_fingernails_L',
    'body_eyelash01']

    #refresh the materials_list array
    current_materials_list = bpy.context.object.material_slots.keys()
    print ("size of current_materials_list:{0}".format(len(current_materials_list)))
    #
    for i,game_mat_name in enumerate(game_material_names):
        print ("current index {0} and size of current_materials_list:{1}".format(i,len(current_materials_list)))
        mat = None
        for existing_mat in current_materials_list:
            if (game_mat_name in existing_mat):
                # Get material
                print("Found material: {0} in current_materials_list as {1}".format(game_mat_name,existing_mat))
                mat = bpy.data.materials.get(existing_mat)
        #if mat not found in body, lets look in the entire project
        if mat is None:
            print("Material: {0} not found, lets look for it in the entire project".format(game_mat_name))
            mat = bpy.data.materials.get(game_mat_name)
            if mat is not None:
                #assign material
                ob.data.materials.append(mat)
        #if mat still doesnt exist, create it.
        if mat is None:
            # create material
            print("Material: {0} not found, lets create it".format(game_mat_name))
            mat = bpy.data.materials.new(name=game_mat_name)
            print("\t Material added as : {0}".format(mat.name))
            #assign material
            ob.data.materials.append(mat)
        #
        #
        if (mat.name != game_mat_name):
            print("\t Material should be renamed as : {0}".format(game_mat_name))
            mat.name = game_mat_name
            print("\t Material new name is : {0}".format(mat.name))


def sortLegacyMaterialSlots(ob):
    """Sort slots by the last underscore token, then rotate slot 0 down to index 15.

    LEGACY only - the resulting order is what the legacy engine's material index table
    expects. It means nothing for DAZ or FULLBODY, so neither of those calls it.

    This used to be a bubble sort with bpy.ops.object.material_slot_move inside the
    inner loop, followed by 15 more move calls. With 21 slots that is 420 iterations
    and ~150 operator invocations - and bpy/ops.py runs a full scene.update() after
    every operator, measured at 53 ms here. It was the single largest cost in the
    conversion. The permutation is now computed in Python and applied in one pass.

    Semantics are preserved exactly: Python's sorted() is stable and the original
    bubble sort used a strict <, so equal keys keep their relative order either way.
    """
    if _materialSlotsAreDataLinked(ob):
        slot_names = [slot.name for slot in ob.material_slots]
        order = sorted(range(len(slot_names)),
                       key=lambda i: slot_names[i].split("_")[-1])
        if order:
            # 15 x move DOWN on slot 0 puts it at index 15 (clamped to the last slot).
            insert_at = min(15, len(order) - 1)
            order = order[1:insert_at + 1] + [order[0]] + order[insert_at + 1:]
        rebuildMaterialSlots(ob, order)
        print("material slot order: {}".format([slot.name for slot in ob.material_slots]))
    else:
        for j in range (len(ob.material_slots)):
            for i in range (len(ob.material_slots)-1):
                ob.active_material_index = i
                tempStr = ob.active_material.name
                ob.active_material_index = i+1
                if ob.active_material.name.split("_")[-1] < tempStr.split("_")[-1]:
                    bpy.ops.object.material_slot_move(direction='UP')
        ob.active_material_index = 0
        for _ in range(15):
            bpy.ops.object.material_slot_move(direction='DOWN')


def convertG3FDifeomorphicToVXModFBody(material_mode='FULLBODY') :
    isMyArmature = checkIfActiveObjectIs("ARMATURE","Genesis 3 Female")
    if (isMyArmature):
        pass
    else:
        ShowMessageBox("Genesis 3 Female Armature is not the active object","Error",icon="ERROR")
        return
    #
    activeObject = bpy.context.scene.objects.active
    bodyMesh = checkIfActiveObjectHasChild("MESH","Genesis 3 Female Mesh")
    if (bodyMesh != None):
        pass
    else:
        ShowMessageBox("Genesis 3 Female Mesh is not a child of the active object","Error",icon="ERROR")
        return
    #
   
    if (bodyMesh != None):
        setActiveObject(bodyMesh)
        activateObject(bodyMesh)
        active_object = bpy.context.scene.objects.active
        bpy.ops.object.duplicate(linked=False)
        bodyMeshCloned = bpy.context.scene.objects.active
        bodyMeshCloned.parent = None
    #
    # Every geograft, not just genitalia - found by Diffeomorphic's own test
    # (non-empty DazGraftGroup + matching DazVertexCount), so tails, wings and vampire
    # teeth come along too with no name list to maintain.
    #
    # Clone each one, parent it to the body clone, then rename it to the
    # geograft_<N>_<short> convention exporter_unreal reads. Originals are left alone -
    # they get hidden at the end of Manny FULL.
    geograftMeshes = findGeografts(activeObject, bodyMesh)
    print("found {0} geograft(s): {1}".format(
        len(geograftMeshes), [g.name for g in geograftMeshes]))

    # (original Daz name, clone). The ORIGINAL name is what the profile and censor
    # tables are keyed by, and it is gone from the clone the moment it is renamed, so
    # it has to be captured here.
    geograftClones = []
    for geograftMesh in geograftMeshes:
        original_name = geograftMesh.name
        setActiveObject(geograftMesh)
        activateObject(geograftMesh)
        bpy.ops.object.duplicate(linked=False)
        clone = bpy.context.scene.objects.active
        clone.parent = None
        #actually reassign it
        clone.parent = bodyMeshCloned
        geograftClones.append((original_name, clone))

    for original_name, new_name in zip([n for n, _c in geograftClones],
                                       assignGeograftNames(geograftClones)):
        print("geograft {0} -> {1}".format(original_name, new_name))
    #
    #gensMeshCloned.parent
    
    # no, we are not going to merge yet... we need to do that later
    #activateObject(gensMeshCloned) # activate this to maybe deselect all in scene first?
    #gensMeshCloned.select = True
    #bodyMeshCloned.select = True
    #setActiveObject(bodyMeshCloned)
    #if (True == False):
    #    return  
    #bpy.ops.daz.merge_geografts()
    activateObject(bodyMeshCloned)
    setActiveObject(bodyMeshCloned)
    """     #
    #setActiveObject(gensMesh)
    setActiveObject(bodyMesh)
    activateObject(bodyMesh)
    active_object = bpy.context.scene.objects.active
    bpy.ops.object.duplicate(linked=False)
    cloned_object = bpy.context.scene.objects.active
    setActiveObject(cloned_object)
    activateObject(cloned_object) 
    cloned_object.parent = None """
    #
    #activateObject(gensMesh)
    #if (1==1):
    #    return
    scene = bpy.context.scene
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    #
    # we need to make clones of the materials, otherwise we will overwrite on the stock materials assigned to difeomorphic body
    materials_list = bpy.context.object.material_slots.keys()
    for mat_name in materials_list:
        mat_index = bpy.context.object.material_slots.find(mat_name)
        bpy.context.object.active_material_index = mat_index
        active_material = bodyMeshCloned.active_material
        bodyMeshCloned.active_material = active_material.copy()
    #
    #reload the materials list
    materials_list = bpy.context.object.material_slots.keys()
    #
    # Which surfaces survive, and under what name, is the only thing the three modes
    # disagree about. Everything after this point - the unused-slot sweep, the
    # placeholders, the cage rename, the eyelash normal flip - is shared.
    # Normalized ONCE, up front, and reused for the rest of the function. An unknown
    # mode string has to be rewritten here rather than handled in the else branch below:
    # everything downstream (placeholders, censor target, geograft material) asks
    # materialNamesForMode, which hands anything that is not LEGACY the modern names. A
    # fallback that ran the LEGACY conversion while still reporting an unknown mode
    # would get body_* materials from the conversion and mat_* placeholders on top -
    # two schemes on one mesh, which is exactly what per-mode naming exists to prevent.
    if material_mode not in ('DAZ', 'LEGACY', 'FULLBODY'):
        print("unknown material conversion mode {0}, falling back to LEGACY".format(
            material_mode))
        material_mode = 'LEGACY'

    print("material conversion mode: {0}".format(material_mode))
    if material_mode == 'LEGACY':
        applyLegacyMaterialConversion(bodyMeshCloned)
    elif material_mode == 'FULLBODY':
        applyFullBodyMaterialConversion(bodyMeshCloned)
    else:
        # DAZ: nothing to do. The stock Daz surfaces stay exactly as imported - they
        # were already copied above, so the originals on the Difeomorphic body are safe.
        pass

    bpy.ops.object.mode_set(mode='OBJECT')

    #delete unused materials
    ob = bpy.context.active_object
    used_indices = set()
    polygon_count = len(ob.data.polygons)
    if polygon_count:
        indices = [0] * polygon_count
        ob.data.polygons.foreach_get("material_index", indices)
        used_indices = set(indices)

    if _materialSlotsAreDataLinked(ob):
        keep = [i for i in range(len(ob.material_slots)) if i in used_indices]
        if keep and len(keep) != len(ob.material_slots):
            rebuildMaterialSlots(ob, keep)
    else:
        for i in reversed(range(len(ob.material_slots))):
            if i not in used_indices:
                bpy.context.scene.objects.active = ob
                ob.active_material_index = i
                bpy.ops.object.material_slot_remove()



    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.object.mode_set(mode='OBJECT')

    # LEGACY needs the full 21-name table present and in engine slot order. The other
    # two modes have no such table - FULLBODY deliberately ends up with three or four
    # slots, DAZ keeps whatever Daz shipped - so neither is sorted or padded.
    ob = bpy.context.active_object
    if material_mode == 'LEGACY':
        ensureLegacyGameMaterials(ob)
        sortLegacyMaterialSlots(ob)

    # Runs LAST, and in every mode, so the slots are guaranteed to exist no matter what
    # the mode above did or did not create. In LEGACY this is a no-op because
    # ensureLegacyGameMaterials already made both.
    #
    # After the unused-slot sweep on purpose - created earlier, body_main_censor would
    # be empty at sweep time and get pruned before it could be filled. And after
    # sortLegacyMaterialSlots, which is why assignCensorFaces looks the slot up by name
    # rather than trusting an index from before the sort.
    ensurePlaceholderMaterials(ob, material_mode)
    # The ORIGINAL geograft names, not the clones' - the clones have been renamed to
    # geograft_<N>_<short> by now and would never match a table key.
    assignCensorFaces(ob, material_mode,
                      [original_name for original_name, _clone in geograftClones])

    # Legacy engine identities, and deliberately still spelled with the LEGACY material
    # names. Those materials do not exist in DAZ or FULLBODY, so tagMaterialEngineIds
    # no-ops there on its own - the ids are meaningless in a pipeline targeting Unreal,
    # and the _SG / _RS strings belong to the engine's namespace, not Blender's, so they
    # do not follow the mat_ rename.
    tagMaterialEngineIds("body_teeth01", "local_custommouth_RS", "body_teeth01_SG")
    tagMaterialEngineIds("body_main_censor", "local_customcensor_RS", "body_main_censor_SG")

    # DISABLED - LEGACY. The 14 fake "bbb_*" shape keys plus a Basis were inherited from
    # the pre-Difeomorphic importer (importer_g3f.py:309 still sets the same property).
    # They carry no deltas; they only reserved names that dictionary_shapekeys.py maps to
    # body_blends_* ids. The real shape keys are imported later from a custom file with
    # the Game Mod Tiny Tools (GMTT) addon, which creates whatever it needs.
    #
    # Leaving them out means the converted mesh has NO shape keys at all, i.e.
    # ob.data.shape_keys is None. Checked against every consumer in the addon:
    #   safe   exporter_unreal.py:193-194  adds a Basis when one is missing
    #   safe   exporter_unreal.py:1293     checks for None before reading key_blocks
    #   fixed  legacy_tools_import_export_shape_keys_json.py  (dead module, now guarded)
    #   fixed  tools_duplicate_object_remove_mats_shapekeys.py:18  (now guarded)
    #
    #verts = ob.data.vertices
    #
    #sk_basis = ob.shape_key_add('Basis')
    #ob.data.shape_keys.use_relative = True
    #
    #shape_keys = [
    #'bbb_asian02_morph',
    #'bbb_vagfix_morph',
    #'bbb_eye_L_morph',
    #'bbb_asian01_morph',
    #'bbb_atomic01',
    #'bbb_hentai01_morph',
    #'bbb_eye_R_morph',
    #'bbb_african01_morph',
    #'bbb_vag_morph',
    #'bbb_jenna01_morph',
    #'bbb_capelli01_morph',
    #'bbb_ear01',
    #'bbb_pregnant',
    #'bbb_ear02'
    #]
    #
    ## Create 10 sequential deformations
    #for shape_key in shape_keys:
    #    # Create new shape key
    #    sk = ob.shape_key_add(shape_key)
    #    sk.slider_min = -1



    body_subdiv_cage_object = bpy.context.scene.objects.get("body_subdiv_cage")

    if body_subdiv_cage_object:
        print ("\"body_subdiv_cage\" object found in scene, using original name")
    else:
        ob.name= "body_subdiv_cage"
        ob.data.name = "M_body_subdiv_cage"

    
    #lets flip eyelashes normals
    eyelashes_faces_that_needs_to_have_flipped_normals = [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197]
    
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_mode(type="FACE")
    bpy.ops.object.mode_set(mode='OBJECT')
    for i in eyelashes_faces_that_needs_to_have_flipped_normals:
        ob.data.polygons[i].select = True
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.flip_normals() 
    bpy.ops.object.mode_set(mode='OBJECT')

    ob.data.uv_layers[0].name = "UVMap"
    #lets add this property
    ob.data["json_sk_exporter"] = "bbb_eye_L_morph,bbb_eye_R_morph,bbb_vagfix_morph"

    # Per geograft, driven by its profile's material_role. Genitalia gets the mode's
    # genital material (body_genital01 in LEGACY, mat_genital otherwise); anything
    # without a role - a tail, wings - keeps its own materials, which is what you want
    # for something that ships with its own textures.
    for original_name, clone in geograftClones:
        applyGeograftMaterial(clone, original_name, material_mode)

    #lets end
    activateObject(bodyMeshCloned)
    setActiveObject(bodyMeshCloned)
