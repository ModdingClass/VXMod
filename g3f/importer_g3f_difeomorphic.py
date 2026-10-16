import bpy
import math
import re

from ..g3f.difeomorphic_workflow_convert_body import *
from ..g3f.difeomorphic_workflow_init_custom_face_indices import *
from ..g3f.difeomorphic_workflow_init_geografts import *
from ..tools_message_box import *
from ..utils_bpy import *

# Object custom property marking the converted body mesh. Read by
# findConvertedBodyMesh (difeomorphic_workflow.py) and stripped from the export
# copies by exporter_unreal.py - keep the three spellings in step.
BODY_MARKER_PROP = "vx_body"


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
# Four ways to turn the Daz surface list into game materials, picked in the panel
# under the "G3F -> VX body" button and passed in as `material_mode`:
#
#   DAZ        leave the stock Daz surfaces exactly as imported
#   LEGACY     the original vxmod collapse into the 21 body_* game materials
#   FULLBODY   one material for the whole body, minus two exceptions
#   SPLITBODY  one material per body REGION, plus own slots for graft and censor
#
# Every mode marks the censor region in VERTEX COLOUR - see paintCensorVertexColors.
# SPLITBODY additionally gives it a material slot of its own, because a slot swap in
# Unreal is cheaper and simpler than a vertex-colour classifier in the shader. There is
# no placeholder material pass: nothing needs an empty slot reserved for it any more.
# ---------------------------------------------------------------------------

# Daz surfaces that make up the eye interior. LEGACY folds these into body_head01 and
# relies on them ending up hidden inside the skull; FULLBODY gives them their own
# DONT_RENDER material instead, so Unreal can drop them outright.
# Matched against the bare Daz names - Diffeomorphic imports them suffixed.
EYE_INTERIOR_MATERIALS = ["Cornea", "Pupils", "Sclera", "Irises", "EyeMoisture"]

# Kept out of every merge: this one needs a translucent material in Unreal, so it
# cannot share a slot with opaque skin.
EYELASH_MATERIALS = ["Eyelashes"]

# SPLITBODY only. One Daz surface list per body region, keyed by the role name the
# SPLIT_MATERIAL_NAMES table uses.
#
# The groupings follow the G3F UDIM tile map exactly - see "G3F UDIM tile map" in
# CLAUDE.md - because that is what the Unreal side keys its per-region textures off:
#   tile 0 face   tile 1 torso   tile 2 legs   tile 3 arms   tile 4 mouth
#
# Matched against bare Daz names through _slotIndicesMatchingPrefixes, so Diffeomorphic's
# "-N" suffixes normalize away ("Torso-1" matches "Torso").
#
# NOTE this is INCLUSION matching, unlike FullBody's exclusion sweep. SplitBody has to
# know WHICH region a surface belongs to, so it cannot merge by "everything unprotected".
# applySplitBodyMaterialConversion compensates by routing unmatched surfaces to a named
# fallback and printing them, so a custom surface is loud rather than silently skinned.
SPLIT_BODY_REGION_MATERIALS = [
    ('face',  ["EyeSocket", "Ears", "Lips", "Face"]),
    ('torso', ["Torso"]),
    ('legs',  ["Legs", "Toenails"]),
    ('arms',  ["Arms", "Fingernails"]),
    ('mouth', ["Mouth", "Teeth"]),
    # A genital surface sitting on the BODY (rather than arriving as a geograft) belongs
    # with the graft. applyGeograftMaterial handles the geograft object itself.
    ('genital', ["Genitalia"]),
]

# Where a surface goes when it matches no region list. Torso is the largest skin region
# and the least wrong place for an unknown patch of skin - but every fallback is printed,
# so it is a warning, not a silent default.
SPLIT_BODY_FALLBACK_ROLE = 'torso'

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

    # A role names the GEOGRAFT CATEGORY, not a material, so the same role can resolve to
    # different materials per scheme. In the modern scheme a genital geograft goes on the
    # BODY material - there is no mat_genital.
    #
    # That is what the Unreal graph expects: body and geograft live in one merged mesh
    # under ONE material, and the shader tells them apart by UV TILE (the graft's island
    # sits at U in [-1,0), the body at [0,1)) rather than by material slot. Two slots
    # would be a second section and a second draw call buying nothing.
    #
    # After the merge Blender folds both objects onto the same slot automatically, since
    # a join merges slots by material datablock and they now share one.
    'genital': "mat_fullbody",

    # Unused by default - the censor region is vertex colour now, not a material. Kept so
    # the assignCensorFaces revert path still resolves a name. SPLITBODY is the one mode
    # that DOES put the censor on its own slot; see SPLIT_MATERIAL_NAMES.
    'censor': "mat_censor",
}


# THREE schemes, not two. SPLITBODY needs its own table because two roles resolve
# differently from the modern scheme:
#
#   genital -> mat_gens, not mat_fullbody. The whole point of the mode is that the graft
#             is its own SECTION, so Unreal can hide it by swapping that slot to
#             DONT_RENDER instead of working out body-vs-graft from the UV tile in the
#             shader. That deletes Floor(U+1), Is_Graft, GeograftRegionIndex, the tile
#             switch and the OpacityMask dependency - and sidesteps a UE 5.8 bug where
#             OpacityMask 0 is not clipped on skeletal LOD0.
#
#   censor  -> mat_censor, and actually used. Same reasoning: a slot swap instead of a
#             vertex-colour classifier in the shader.
#
# fullbody is None: there is no single body material in this scheme, the same way LEGACY
# has none. Anything asking for it is asking the wrong question in this mode.
SPLIT_MATERIAL_NAMES = {
    'fullbody': None,
    'dont_render': "DONT_RENDER",
    'eyelashes': "mat_eyelashes",
    'genital': "mat_gens",
    'censor': "mat_censor",

    # Region materials - SPLITBODY only. The other schemes have no equivalent.
    'face': "mat_face",
    'torso': "mat_torso",
    'legs': "mat_legs",
    'arms': "mat_arms",
    'mouth': "mat_mouth",
}


# DAZSPLIT: every Daz surface keeps its own slot, renamed mat_<lowercased daz name> -
# see applyDazSplitMaterialConversion. Only the roles the rest of the pipeline asks for
# by name live here; the per-surface names are derived, not tabulated.
#
# The graft and censor behave exactly as in SPLITBODY (own slots, hidden in Unreal by a
# slot swap). dont_render is None: nothing goes to DONT_RENDER in this mode for now, the
# eye interior keeps mat_cornea, mat_sclera, ... like every other surface.
DAZSPLIT_MATERIAL_NAMES = {
    'fullbody': None,
    'dont_render': None,
    'eyelashes': "mat_eyelashes",
    'genital': "mat_gens",
    'censor': "mat_censor",
}


def materialNamesForMode(material_mode):
    """The name table for a mode.

    FOUR schemes: LEGACY, SPLITBODY and DAZSPLIT each have their own, and DAZ + FULLBODY
    share the modern one. Anything unrecognised gets modern, which is safe because
    convertG3FDifeomorphicToVXModFBody normalizes an unknown mode to LEGACY before any
    of this runs - see the comment at that guard for why the normalization has to happen
    there rather than here.
    """
    if material_mode == 'LEGACY':
        return LEGACY_MATERIAL_NAMES
    if material_mode == 'SPLITBODY':
        return SPLIT_MATERIAL_NAMES
    if material_mode == 'DAZSPLIT':
        return DAZSPLIT_MATERIAL_NAMES
    return MODERN_MATERIAL_NAMES


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


def assignCensorFaces(ob, material_mode, geograft_objects):
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
    material slot is created by assignFacesToMaterial itself when there is something to
    put in it. Borrowing a face set from a different geograft would put the censor in the
    wrong place, which is worse than no censor at all.
    """
    material_name = materialNamesForMode(material_mode)['censor']

    if not geograft_objects:
        print("assignCensorFaces: no geograft on this body - {0} left empty".format(
            material_name))
        return 0

    # A body can carry several geografts at once, so the region is the UNION of what
    # each contributes. Sorted so the assignment is order-independent.
    face_indices = set()
    contributors = []
    for geograft_object in geograft_objects:
        faces = censorFacesForGeograft(geograft_object)
        if not faces:
            print("assignCensorFaces: geograft \"{0}\" has an empty DazMaskGroup and no "
                  "override - it contributes nothing".format(geograft_object.name))
            continue
        face_indices.update(faces)
        contributors.append(geograft_object.name)

    if not face_indices:
        print("assignCensorFaces: no geograft on this body yields censor faces - "
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


def censorFacesForGeograft(geograft_object):
    """The base-mesh faces this geograft hides - the region to censor.

    Read from the geograft's OWN DazMaskGroup: Daz's list of base-mesh faces to hide when
    the graft is applied. That IS the censor region, and it ships with the geograft, so
    nothing has to be collected by hand.

    Verified 2026-09-03 on the G3F genitalia - DazMaskGroup returned exactly the 82
    indices that had been hand-collected for it, empty diff both ways. So any geograft now
    masks its own footprint with no table entry: a tail, wings, whatever comes next.

    censor_faces_by_geograft survives as an OVERRIDE and WINS when it has a matching
    entry, for a graft whose mask is not the region you actually want censored. Empty by
    default.

    Takes the OBJECT, not a name - the mask lives on the mesh data. Pass the ORIGINAL
    geograft, not the clone: the clone is renamed, and the original is the one certain to
    carry Diffeomorphic's data.
    """
    override_key = geograftTableKey(censor_faces_by_geograft, geograft_object.name)
    if override_key:
        print("censorFacesForGeograft: using the override entry for \"{0}\"".format(
            override_key))
        return censor_faces_by_geograft[override_key]

    mask_group = getattr(geograft_object.data, "DazMaskGroup", None)
    if not mask_group:
        return None
    return sorted(item.a for item in mask_group)


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

    `geograft_clones` is a list of (original_object, clone) already in sorted order.

    Uniqueness matters because the short names are joined into the exported merged mesh
    name. A scene holding both "Genesis 3 Female Genitalia" and a leftover
    "...Genitalia.001" normalizes both to the same profile, so without this they would
    both become "genz" and the export would read Belle_genz_genz - two identical
    fragments with no way to tell afterwards which file belonged to which graft.
    """
    used = {}
    names = []
    for index, (original_object, clone) in enumerate(geograft_clones):
        short_name = geograftShortName(original_object.name)
        seen = used.get(short_name, 0)
        used[short_name] = seen + 1
        if seen:
            print("assignGeograftNames: short name \"{0}\" already taken by an earlier "
                  "geograft - duplicate in the scene?".format(short_name))
            short_name = "{0}_{1}".format(short_name, seen + 1)
        names.append(renameGeograft(clone, short_name, index))
    return names


_GEOGRAFT_INDEX_RE = re.compile(r"^geograft_(\d+)_")


def findGeograftChildren(body_mesh_object):
    """The geograft clones parented to the converted body, in geograft_<N>_ order.

    Identified by the same `^geograft_(\\d+)_` prefix exporter_unreal.get_geograft_children
    uses, so the conversion, Manny FULL and the exporter all agree on what a geograft is.

    Used by Manny FULL, which otherwise only ever touches body_subdiv_cage - see
    bindGeograftToArmature for why that mattered.
    """
    matched = []
    for child in body_mesh_object.children:
        if child.type != 'MESH':
            continue
        match = _GEOGRAFT_INDEX_RE.match(child.name)
        if match:
            matched.append((int(match.group(1)), child))
    matched.sort(key=lambda pair: pair[0])
    return [child for _index, child in matched]


BODY_UV_LAYER = "UVMap"


def relocateGeograftUvIsland(ob, original_name):
    """Shift a geograft's UV island onto the tile its profile reserves for it.

    Daz ships the G3F genitalia island at U in [0, 1) - the same tile the body uses for
    the FACE. Joining without relocating overlaps them.

    That overlap is harmless for SHADING: the graft has its own material and its own
    texture, and wrap sampling reads the same texels whichever tile the coordinate names.
    It is NOT harmless for anything that rasterises the mesh in UV SPACE - the paint and
    mask render targets, per-tile captures, bakes - where two islands on one tile write
    over each other.

    The destination comes from the profile's `uv_region_index`, in the material's
    Floor(U+1) numbering, so index 9 means the island lands at U in [8, 9). Hardcoded per
    geograft so a given graft is on the same tile in every export.

    The shift is measured from where the island ACTUALLY is (floor of the smallest U),
    not assumed to start at 0 - an asset that already ships elsewhere still lands on the
    reserved tile instead of being pushed past it.

    Every UV layer is shifted, not just the active one. Daz assets often carry several,
    the join picks by name, and leaving the others behind would mean the choice of layer
    silently decides where the graft ends up.

    V is untouched. Only the tile column moves.
    """
    profile = geograftProfile(original_name)
    if not profile or profile.get("uv_region_index") is None:
        print("relocateGeograftUvIsland: {0} has no reserved tile - UVs left alone"
              .format(ob.name))
        return None

    target_tile = int(profile["uv_region_index"]) - 1   # Floor(U+1) -> floor(U)

    uv_layers = list(ob.data.uv_layers)
    if not uv_layers:
        print("relocateGeograftUvIsland: {0} has no uv layer".format(ob.name))
        return None

    moved = 0
    for uv_layer in uv_layers:
        loop_count = len(uv_layer.data)
        if not loop_count:
            continue
        flat = [0.0] * (loop_count * 2)
        uv_layer.data.foreach_get("uv", flat)

        u_values = flat[0::2]
        u_min = min(u_values)
        u_max = max(u_values)
        current_tile = int(math.floor(u_min))

        # An island is only relocatable if it FITS inside the tile it starts in. If it
        # crosses a boundary, no integer shift can land it on a single tile, and shifting
        # anyway would leave part of it on the neighbour - the same overlap this function
        # exists to prevent, just somewhere less obvious. Say so and leave it alone.
        #
        # Tested against the tile's far EDGE, not against a width: an island can be a
        # full tile wide and still fit (U 0..1), while one only 1.0 wide can straddle
        # (U -0.001..0.999). The epsilon lets a coordinate sit exactly on the boundary,
        # which is a legitimate UV meaning "the edge of this tile".
        if u_max > current_tile + 1.0 + 1e-6:
            print("relocateGeograftUvIsland: {0} layer \"{1}\" spans U {2:.4f}..{3:.4f}, "
                  "crossing the tile {4} boundary - NOT relocated".format(
                      ob.name, uv_layer.name, u_min, u_max, current_tile))
            continue

        offset = target_tile - current_tile
        if offset == 0:
            print("relocateGeograftUvIsland: {0} layer \"{1}\" already on tile {2}"
                  .format(ob.name, uv_layer.name, target_tile))
            continue

        flat[0::2] = [u + offset for u in u_values]
        uv_layer.data.foreach_set("uv", flat)
        moved += 1
        print("relocateGeograftUvIsland: {0} layer \"{1}\" tile {2} -> {3} "
              "(U {4:+d}, region index {5})".format(
                  ob.name, uv_layer.name, current_tile, target_tile, offset,
                  profile["uv_region_index"]))

    return target_tile


def renameGeograftUvLayer(ob, target_name=BODY_UV_LAYER):
    """Rename the geograft's RENDER uv layer to match the body's, so the join merges them.

    The body's layer is renamed to UVMap by the conversion; a Diffeomorphic geograft
    arrives with whatever Daz called its uv set ("Default UVs" on the G3F genitalia).
    Different names mean bpy.ops.object.join() produces TWO layers, and the merge then
    relies on joinUvTextures to consolidate them by a heuristic: a loop whose uv is at
    the origin is treated as empty and filled from the first LATER layer that has data.

    That heuristic is fine for a graft with one uv set - there is nothing to pick wrongly.
    It is not fine for a graft carrying several, which Daz assets do: the first layer with
    data wins, and that is not necessarily the active_render one.

    Matching the name sidesteps it. The join merges the two by name into one layer, and
    joinUvTextures returns immediately on its `len(uv_layers) <= 1` guard. Extra uv sets
    stay as extra layers instead of competing to fill layer 0.

    Coordinates are untouched - only the label changes. relocateGeograftUvIsland is the
    one that moves them, and it runs straight after this in the same loop.
    """
    mesh = ob.data
    if not mesh.uv_layers:
        print("renameGeograftUvLayer: {0} has no uv layer".format(ob.name))
        return None

    # active_render lives on uv_textures (MeshTexturePolyLayer) in 2.79 - uv_layers
    # (MeshUVLoopLayer) has no such attribute. Both are views of the same CustomData
    # layer, so an index found on one indexes the other.
    render_index = 0
    for index, uv_texture in enumerate(mesh.uv_textures):
        if uv_texture.active_render:
            render_index = index
            break

    layer = mesh.uv_layers[render_index]
    if layer.name == target_name:
        return target_name

    # Renaming onto a name another layer already holds would make Blender disambiguate it
    # to "UVMap.001", which defeats the whole point.
    for index, other in enumerate(mesh.uv_layers):
        if index != render_index and other.name == target_name:
            print("renameGeograftUvLayer: {0} already has a layer called \"{1}\" - "
                  "leaving \"{2}\" alone".format(ob.name, target_name, layer.name))
            return None

    previous_name = layer.name
    layer.name = target_name
    print("renameGeograftUvLayer: {0} uv layer \"{1}\" -> \"{2}\"".format(
        ob.name, previous_name, target_name))
    return target_name


def bindGeograftToArmature(geograft_object, armature_object):
    """Point the geograft's ARMATURE modifier at `armature_object`, KEEPING its parent.

    Deliberately NOT bindMeshToArmature. That one clears the parent - correct for
    body_subdiv_cage, which must stay top-level - but the geograft's parent is
    load-bearing: exporter_unreal.get_geograft_children finds grafts by walking
    body_subdiv_cage.children, so an unparented graft is silently not exported.

    Until this existed the clone kept the modifier it was duplicated with, pointing at the
    GEOGRAFT'S OWN Daz rig. That rig is hidden by the end of Manny FULL but not deleted,
    so the graft went on deforming with an unposed Daz skeleton while the body followed
    Manny - the graft visibly detaching as soon as the Manny rig was posed.
    """
    modifier = None
    for mod in geograft_object.modifiers:
        if mod.type == 'ARMATURE':
            modifier = mod
            break
    if modifier is None:
        modifier = geograft_object.modifiers.new(name="Armature", type='ARMATURE')

    previous = modifier.object.name if modifier.object else None
    modifier.object = armature_object
    modifier.use_vertex_groups = True
    print("bindGeograftToArmature: {0} -> {1} (was {2}); parent {3} kept".format(
        geograft_object.name, armature_object.name, previous,
        geograft_object.parent.name if geograft_object.parent else None))
    return modifier


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
    """Replace the geograft's material slots with the one its profile's role resolves to.

    Only for geografts whose profile has a `material_role`. Anything else keeps its own
    materials - correct default for a tail or wings, which ship with textures worth
    keeping and have no reason to land on the body material.

    In the MODERN scheme the genital role resolves to mat_fullbody, so the graft ends up
    on the SAME material as the body. That is what the FullBody Unreal graph wants: it
    separates body from graft by UV tile, not by material slot.

    In SPLITBODY the same role resolves to mat_gens instead, and the graft stays a slot of
    its own through the join - a join merges slots by material DATABLOCK, and mat_gens is
    not any of the body's region materials, so there is nothing to fold into. That is the
    whole point of the mode: Unreal hides the graft by swapping that slot to DONT_RENDER,
    with no UV-tile test in the shader.

    DAZ is skipped entirely. "Keep the stock Daz surfaces exactly as imported" has to mean
    the geograft too - otherwise the body keeps its Daz surfaces while the graft gets a
    mat_ material the body does not even have.
    """
    if material_mode == 'DAZ':
        print("applyGeograftMaterial: DAZ mode - {0} keeps its stock Daz materials".format(
            ob.name))
        return None

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


# ---------------------------------------------------------------------------
# Censor vertex colours
#
# Replaces the censor MATERIAL. Instead of parking the censor region on its own material
# slot, the region is marked in vertex colour and the Unreal material masks on it:
#
#   whole body   white  (1, 1, 1)
#   censor region cyan  (0, 1, 1)   <- red channel is the mask
#
# The Unreal graph reads VertexColor -> ComponentMask(R) -> If(A > 0 ? 1 : 0), gated by a
# "Show Gens?" scalar, into Opacity Mask. Red exactly 0 hides the face; anything above 0
# keeps it. So the body's crotch geometry underneath the genital geograft can be switched
# off at runtime without a second material slot and without deleting geometry - the same
# job Daz's own face-hiding mask does, but reversible in the material.
#
# WHY VERTEX COLOUR IS PER-LOOP AND WHY THAT MATTERS
#
# Blender stores vertex colour per LOOP (per face-corner), not per vertex. Painting from
# the FACE list is therefore exactly right, and painting per-VERTEX would be wrong:
#
#   per-loop  every corner of a censor face is 0, so R interpolates to 0 across the whole
#             face -> hidden. Every corner of a neighbouring face is 1 -> visible. The
#             boundary lands exactly on the face edge.
#   per-vertex a boundary face would have some corners 0 and some 1, R would ramp across
#             it, and the material's `> 0` test would keep most of it visible - a ragged,
#             half-masked edge.
#
# So no vertex index list is needed, and one would actively make the mask worse.
# ---------------------------------------------------------------------------

CENSOR_VERTEX_COLOR_LAYER = "Col"
CENSOR_VERTEX_COLOR = (0.0, 1.0, 1.0)   # cyan - red channel 0 is what the mask reads
BODY_VERTEX_COLOR = (1.0, 1.0, 1.0)     # white - everything that stays visible


def ensureVertexColorLayer(ob, fill_color=BODY_VERTEX_COLOR):
    """Get or create the vertex colour layer on `ob`, filled with `fill_color`.

    Made active for render as well as active for edit: the 2.79 FBX exporter writes every
    layer it finds (there is no use_mesh_colors toggle to set), but Unreal keeps only one
    colour channel, so which layer is the render one decides what arrives.
    """
    mesh = ob.data
    layer = mesh.vertex_colors.get(CENSOR_VERTEX_COLOR_LAYER)
    if layer is None:
        layer = mesh.vertex_colors.new(name=CENSOR_VERTEX_COLOR_LAYER)
    mesh.vertex_colors.active = layer
    layer.active_render = True

    loop_count = len(mesh.loops)
    if loop_count:
        # 2.79 stores RGB, later versions RGBA. Read the stride off the data rather than
        # assuming, or foreach_set silently mismatches.
        stride = len(layer.data[0].color)
        channels = list(fill_color) + [1.0] * (stride - len(fill_color))
        layer.data.foreach_set("color", channels[:stride] * loop_count)
    return layer


def paintCensorVertexColors(ob, geograft_objects):
    """Paint the body white and the censor region cyan, per loop, from the FACE table.

    Returns the number of faces painted. Zero is a legitimate result - no geograft, or one
    with no table entry - and leaves the mesh uniformly white, i.e. nothing masked.
    """
    layer = ensureVertexColorLayer(ob, BODY_VERTEX_COLOR)

    face_indices = set()
    contributors = []
    for geograft_object in geograft_objects or []:
        faces = censorFacesForGeograft(geograft_object)
        if not faces:
            print("paintCensorVertexColors: geograft \"{0}\" has an empty DazMaskGroup "
                  "and no override - it contributes nothing".format(geograft_object.name))
            continue
        face_indices.update(faces)
        contributors.append(geograft_object.name)

    if not face_indices:
        print("paintCensorVertexColors: nothing to mask - body left fully white")
        return 0

    mesh = ob.data
    polygon_count = len(mesh.polygons)
    stride = len(layer.data[0].color)
    cyan = list(CENSOR_VERTEX_COLOR) + [1.0] * (stride - len(CENSOR_VERTEX_COLOR))
    cyan = cyan[:stride]

    painted = 0
    out_of_range = 0
    for face_index in face_indices:
        if not (0 <= face_index < polygon_count):
            out_of_range += 1
            continue
        polygon = mesh.polygons[face_index]
        for loop_index in range(polygon.loop_start,
                                polygon.loop_start + polygon.loop_total):
            layer.data[loop_index].color = cyan
        painted += 1

    mesh.update()
    if out_of_range:
        print("paintCensorVertexColors: {0} indices outside the mesh ({1} polygons) - "
              "wrong topology?".format(out_of_range, polygon_count))
    print("paintCensorVertexColors: {0} faces cyan from {1}".format(painted, contributors))
    return painted


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


def applySplitBodyMaterialConversion(ob):
    """One material per body REGION, instead of one for the whole body.

    Nine slots: mat_face, mat_torso, mat_legs, mat_arms, mat_mouth, mat_gens,
    mat_censor, mat_eyelashes, DONT_RENDER. The geograft and the censor region are filled
    in elsewhere (applyGeograftMaterial and assignCensorFaces respectively) - this pass
    handles the body's own surfaces.

    WHY, since this is the opposite of what FullBody does:

    Unreal cannot dynamically index separate texture objects, so a single body material
    has to multiplex its six UDIM tile textures with a Switch node. MaterialExpressionSwitch
    compiles to a SUM OF PRODUCTS, not a branch, so every input executes on every pixel.
    Measured on the albedo-only material: 8 pixel-shader texture lookups where 1 is used.
    Adding normal + ORM + displacement would take that to roughly 26. Per-region materials
    make it ~3, and a new map type then costs one fetch instead of six.

    HOW IT DIFFERS FROM FULLBODY: FullBody merges by EXCLUSION - protect two names, sweep
    the rest into the body material - which is robust because it needs no surface list.
    SplitBody cannot do that: it has to know which region a surface belongs to, so it
    matches by name against SPLIT_BODY_REGION_MATERIALS. The unmatched sweep at the end is
    what keeps that from silently losing a custom surface.
    """
    names = SPLIT_MATERIAL_NAMES

    # The two exceptions first, exactly as FullBody does them, and for the same reasons:
    # eyelashes need translucency in Unreal and cannot share a slot with opaque skin; the
    # eye interior is dropped outright rather than hidden inside the skull.
    #
    # Done first because each call removes slots and shifts every index behind it - the
    # region pass below re-reads the slot list each time for the same reason.
    reassignMaterialsAndRemoveSlots(ob, EYE_INTERIOR_MATERIALS, names['dont_render'])
    reassignMaterialsAndRemoveSlots(ob, EYELASH_MATERIALS, names['eyelashes'])

    # One region at a time. reassignMaterialsAndRemoveSlots re-reads ob.material_slots on
    # entry, so removals from the previous region cannot leave a stale index behind.
    for role, daz_surfaces in SPLIT_BODY_REGION_MATERIALS:
        target = names.get(role)
        if not target:
            print("applySplitBodyMaterialConversion: no material for role \"{0}\" - "
                  "skipped".format(role))
            continue
        reassignMaterialsAndRemoveSlots(ob, daz_surfaces, target)

    # Anything still standing matched no region list: a custom surface, a renamed one, or
    # a Daz figure that is not stock G3F. Sweep it into the fallback so it is still
    # skinned, and NAME IT, because silently skinning an unknown surface as torso is the
    # kind of thing that is only noticed three exports later.
    #
    # Every target name is protected, including the ones this pass did not create -
    # mat_gens and mat_censor may already exist if a geograft was processed first, and
    # sweeping either into the fallback would undo exactly what the mode is for.
    protected_names = [name for name in names.values() if name]
    protected_indices = set(_slotIndicesMatchingPrefixes(ob, protected_names))
    leftover_indices = [index for index in range(len(ob.material_slots))
                        if index not in protected_indices]
    if leftover_indices:
        leftover_names = [ob.material_slots[i].name for i in leftover_indices]
        print("applySplitBodyMaterialConversion: {0} unmatched surface(s) -> {1}: "
              "{2}".format(len(leftover_names), names[SPLIT_BODY_FALLBACK_ROLE],
                           leftover_names))
        reassignMaterialSlotIndices(ob, leftover_indices,
                                    names[SPLIT_BODY_FALLBACK_ROLE])
    else:
        print("applySplitBodyMaterialConversion: every surface matched a region")


# DAZSPLIT only. Daz surfaces folded into ANOTHER Daz surface's material instead of
# getting their own. Keyed by bare Daz name -> the bare Daz name whose material they join.
# Everything not listed keeps its own slot.
#
# A target need not be a real Daz surface: "Eyes" is ours, since the eyeball has no
# single Daz name. Such a group keeps the material of whichever of its slots comes first.
DAZSPLIT_SURFACE_MERGES = {
    "Ears": "Face",
    "EyeSocket": "Face",
    "Lips": "Face",
    "Teeth": "Mouth",
    "Sclera": "Eyes",
    "Irises": "Eyes",
    "Pupils": "Eyes",
    "EyeMoisture": "Cornea",
}


def dazSplitMaterialName(slot_name):
    """"Eyelashes-1.001" -> "mat_eyelashes", "Ears-1" -> "mat_face". Both import
    suffixes are stripped first (see normalizeMaterialName), DAZSPLIT_SURFACE_MERGES is
    applied, then the Daz name is lowercased and prefixed."""
    surface = normalizeMaterialName(slot_name)
    surface = DAZSPLIT_SURFACE_MERGES.get(surface, surface)
    return "mat_" + surface.lower()


def applyDazSplitMaterialConversion(ob):
    """One slot per Daz surface, renamed mat_<lowercased daz name>.

    Like SPLITBODY in that the body stays split and the graft / censor get mat_gens /
    mat_censor, but with almost no region grouping: Torso stays mat_torso, Arms stays
    mat_torso. The only merges are DAZSPLIT_SURFACE_MERGES (Ears + EyeSocket + Lips ->
    mat_face, Teeth -> mat_mouth, Sclera + Irises + Pupils -> mat_eyes, EyeMoisture ->
    mat_cornea). Nothing is sent to DONT_RENDER.

    The slot keeps its MATERIAL - the copy made at the top of the conversion is renamed
    in place, so the Daz textures and settings survive. If the name is already taken by
    another datablock (a previous conversion, typically) the slot is pointed at that one
    instead, because renaming onto a taken name gets a ".001" that would then reach
    Unreal as the section's material name.

    Slots that resolve to the same name are merged into one. The surviving material is
    the one whose OWN Daz name is the target (Face's for mat_face, not Ears'), so the
    merged-in surfaces take on its settings rather than the other way round.
    """
    if not _materialSlotsAreDataLinked(ob):
        # The operator path can only address slots by name; route each surface through
        # it one at a time. Loses the Daz material settings, but this path is not hit by
        # Diffeomorphic imports.
        for slot_name in [slot.name for slot in ob.material_slots]:
            target = dazSplitMaterialName(slot_name)
            if slot_name != target:
                reassignMaterialsAndRemoveSlots(ob, [slot_name], target)
        return

    mesh = ob.data

    # Group slots by target name, first-seen order, so the slot order stays Daz's.
    targets = []
    indices_by_target = {}
    for index, slot in enumerate(ob.material_slots):
        target = dazSplitMaterialName(slot.name)
        if target not in indices_by_target:
            indices_by_target[target] = []
            targets.append(target)
        indices_by_target[target].append(index)

    remap = {}
    keep = []
    for target in targets:
        indices = indices_by_target[target]
        own = [i for i in indices
               if "mat_" + normalizeMaterialName(ob.material_slots[i].name).lower()
               == target]
        first = own[0] if own else indices[0]
        mat = mesh.materials[first]
        if mat is None or mat.name != target:
            existing = bpy.data.materials.get(target)
            if existing is not None:
                mesh.materials[first] = existing
            elif mat is not None:
                mat.name = target
            else:
                mesh.materials[first] = bpy.data.materials.new(name=target)
        for index in indices:
            remap[index] = len(keep)
        keep.append(first)
        if len(indices) > 1:
            print("applyDazSplitMaterialConversion: {0} slots merged into {1}".format(
                len(indices), target))

    if len(keep) != len(mesh.materials):
        # rebuildMaterialSlots remaps only the KEPT indices; point the merged ones at
        # their survivor first, so it sees each dropped index as an already-kept one.
        _remapPolygonMaterialIndices(
            mesh, dict((i, keep[remap[i]]) for i in remap), fallback=0)
        rebuildMaterialSlots(ob, keep)

    print("applyDazSplitMaterialConversion: {0}".format(
        [slot.name for slot in ob.material_slots]))


def ensureLegacyGameMaterials(ob):
    """Make sure all 21 legacy body_* materials exist as slots, creating empties.

    LEGACY only. The other modes have no fixed material table to fill in - they end up
    with whatever the conversion actually produced and nothing reserved.
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


def convertG3FDifeomorphicToVXModFBody(material_mode='SPLITBODY') :
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

    # (original geograft object, clone). The ORIGINAL object is kept, not just its
    # name: profile lookups need the name, which the clone loses the moment it is
    # renamed, AND censorFacesForGeograft needs the mesh data, which is where
    # DazMaskGroup lives.
    geograftClones = []
    for geograftMesh in geograftMeshes:
        setActiveObject(geograftMesh)
        activateObject(geograftMesh)
        bpy.ops.object.duplicate(linked=False)
        clone = bpy.context.scene.objects.active
        clone.parent = None
        #actually reassign it
        clone.parent = bodyMeshCloned
        geograftClones.append((geograftMesh, clone))

    for original_object, new_name in zip([g for g, _c in geograftClones],
                                         assignGeograftNames(geograftClones)):
        print("geograft {0} -> {1}".format(original_object.name, new_name))

    # Match the body's uv layer NAME so the merge joins them by name rather than leaning
    # on joinUvTextures' origin-is-empty heuristic. renameGeograftUvLayer touches only the
    # label; relocateGeograftUvIsland is the one that moves coordinates, onto the tile the
    # graft's profile reserves - otherwise the graft lands on top of the body's FACE tile
    # and anything unwrapping the mesh into a texture writes the two over each other.
    #
    # Both run on the CLONE and before the join, so the merged body arrives with the
    # island already where Unreal expects it. The original name is what the profile
    # lookup needs - by here the clone has been renamed to geograft_<N>_<short>, which
    # matches no table key.
    for original_object, clone in geograftClones:
        renameGeograftUvLayer(clone)
        relocateGeograftUvIsland(clone, original_object.name)
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
    if material_mode not in ('DAZ', 'LEGACY', 'FULLBODY', 'SPLITBODY', 'DAZSPLIT'):
        print("unknown material conversion mode {0}, falling back to LEGACY".format(
            material_mode))
        material_mode = 'LEGACY'

    print("material conversion mode: {0}".format(material_mode))
    if material_mode == 'LEGACY':
        applyLegacyMaterialConversion(bodyMeshCloned)
    elif material_mode == 'FULLBODY':
        applyFullBodyMaterialConversion(bodyMeshCloned)
    elif material_mode == 'SPLITBODY':
        applySplitBodyMaterialConversion(bodyMeshCloned)
    elif material_mode == 'DAZSPLIT':
        applyDazSplitMaterialConversion(bodyMeshCloned)
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
    # NO placeholder material pass any more. Both placeholders it used to create are
    # gone: the censor region is vertex colour, and the genital geograft shares
    # mat_fullbody with the body. Nothing needs an empty slot reserved for it.
    #
    # LEGACY is unaffected - ensureLegacyGameMaterials above still creates
    # body_main_censor and body_genital01 from the frozen 21-name table.

    # The ORIGINAL geografts, not the clones - the clones have been renamed to
    # geograft_<N>_<short> by now and would never match a table key, and the original is
    # the one certain to carry Diffeomorphic's DazMaskGroup.
    geograftOriginals = [original_object for original_object, _clone in geograftClones]

    # SPLITBODY additionally puts the censor region on its OWN MATERIAL SLOT, so Unreal
    # can toggle it by swapping that slot rather than classifying vertex colour in the
    # shader. assignCensorFaces creates mat_censor itself when there is something to put
    # in it - the placeholder pass that used to reserve it is gone.
    #
    # Ordering: before paintCensorVertexColors only for readability; the two do not
    # interact. One writes material_index, the other writes a colour layer.
    if material_mode in ('SPLITBODY', 'DAZSPLIT'):
        assignCensorFaces(ob, material_mode, geograftOriginals)

    # The censor region is ALSO marked in vertex colour, in every mode including
    # SPLITBODY. It costs nothing, the other modes depend on it, and it keeps the
    # shader-side path available. To make a non-split mode use the material approach
    # instead, call assignCensorFaces unconditionally.
    paintCensorVertexColors(ob, geograftOriginals)

    # Geograft clones get an explicit white layer so the post-merge result is defined.
    # Without it they arrive at the join with no colour layer at all, and what the join
    # fills in for the missing side is not something to leave to chance on a mask that
    # decides whether geometry is visible.
    for _original_object, clone in geograftClones:
        ensureVertexColorLayer(clone, BODY_VERTEX_COLOR)

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

    # Per geograft, driven by its profile's material_role. The genital role resolves to
    # body_genital01 in LEGACY and to mat_fullbody in the modern scheme - i.e. the graft
    # shares the BODY material, which is what the Unreal graph expects since it separates
    # them by UV tile. DAZ is skipped so stock Daz surfaces stay stock. Anything with no
    # role - a tail, wings - keeps its own materials.
    for original_object, clone in geograftClones:
        applyGeograftMaterial(clone, original_object.name, material_mode)

    # Mark the output as THE converted body, so findConvertedBodyMesh finds it by
    # this stamp rather than by name - it survives a rename (body_subdiv_cage ->
    # BelaTest), and is set even when the rename above was skipped because an older
    # body_subdiv_cage was already in the scene.
    bodyMeshCloned[BODY_MARKER_PROP] = True

    #lets end
    activateObject(bodyMeshCloned)
    setActiveObject(bodyMeshCloned)
