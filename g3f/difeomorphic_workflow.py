import bpy
import mathutils
import math
from math import radians
import json
from mathutils import Vector

from ..tools_message_box import *

from ..ik_tools import *

from ..g3f import difeomorphic_workflow_dictionaries_bones as dict_bones
from ..g3f.difeomorphic_workflow_dictionaries_vertex_groups import *
from ..g3f.difeomorphic_workflow_init_custom_vertex_indices import *

from ..g3f.difeomorphic_workflow_armature_utils import *

from ..g3f.difeomorphic_workflow_armature_from_gens_vertices import *
from ..g3f.difeomorphic_workflow_armature_from_other_vertices import *
from ..g3f.difeomorphic_workflow_armature_from_head_vertices import *
from ..g3f.difeomorphic_workflow_armature_from_breast_vertices import *

from ..helper_vgroups import *

from ..g3f import manny_blender_perfect_generated as manny_bp

if "bpy" in locals():
    import imp
    imp.reload(dict_bones)
    imp.reload(manny_bp)
else:
    from ..g3f import difeomorphic_workflow_dictionaries_bones as dict_bones
    from ..g3f import manny_blender_perfect_generated as manny_bp

# Orientation stamp, so the exporter can tell a BlenderPerfect rig from the old
# VXMod skeleton and pick the right conversion. Kept in step with
# io_unreal_dump_importer/manny_roll_convention.py.
ORIENTATION_PROP = "vx_orientation"
ORIENTATION_BP = "BP"
ORIENTATION_UE5 = "UE5"
# The builder's output with rolls exactly as Diffeomorphic delivered them. Only
# reachable by toggling the BlenderPerfect rolls back off, for comparison.
ORIENTATION_DAZ = "DAZ"

# Per-bone cache of the roll a bone had before applyBlenderPerfectRolls first
# touched it, so the toggle can put it back. Written on the EditBone: Blender
# copies custom properties both ways across an edit-mode round trip, so the value
# is readable as bone[...] in object mode and eb[...] in edit mode.
ROLL_CACHE_PROP = "roll_before_bp"


def _wrapDegrees(degrees):
    """Into (-180, 180]. Blender never does this itself, which is how you end up
    reading -261.98 in the N panel instead of +98.02."""
    wrapped = math.fmod(degrees, 360.0)
    if wrapped <= -180.0:
        wrapped += 360.0
    elif wrapped > 180.0:
        wrapped -= 360.0
    return wrapped


def _beginEditBones(armature_object):
    """Get at edit_bones while disturbing the user's mode as little as possible.

    If the armature is already the object being edited, nothing changes at all
    and the caller stays in edit mode - which is what lets the roll toggle be
    used while posing bones. Otherwise the previous active object and mode are
    captured so _endEditBones can put them back.

    Returns a token for _endEditBones, or None if nothing was changed."""
    scene = bpy.context.scene
    active = scene.objects.active
    if active is armature_object and armature_object.mode == 'EDIT':
        return None

    previous = (active, active.mode if active is not None else 'OBJECT')
    if active is not None and active.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    scene.objects.active = armature_object
    bpy.ops.object.mode_set(mode='EDIT')
    return previous


def _endEditBones(token):
    if token is None:
        return
    previous_active, previous_mode = token
    bpy.ops.object.mode_set(mode='OBJECT')
    if previous_active is not None:
        bpy.context.scene.objects.active = previous_active
        if previous_mode != 'OBJECT':
            bpy.ops.object.mode_set(mode=previous_mode)

def alignArmatureFromDifeomorphicToManny():
    """
    Build a Manny-named armature named "Armature" from the selected
    Diffeomorphic-imported G3F armature.

    Mirrors what the DazToUnreal plugin's ConvertToEpicSkeleton does, minus the
    re-orientation pass (see reorientArmatureFromDifeomorphicToManny below).

    What it does
      1. Refuses to run if an object called "Armature" already exists.
      2. Copies EVERY bone of the source rig, head/tail/roll unchanged.
      3. Renames via dict_bones.getMannyBoneRenameMap() - the 67 DazToUnreal names
         plus the 22 extras VXMod keeps (toes, breasts). Bones with no entry
         (lMetatarsals, lHeel, the face rig, tongue, eyes, ...) are carried over
         under their Daz names, exactly as DazToUnreal leaves them. Nothing is
         dropped here; the face rig is collapsed later by mergeBonesIntoTargets.
      4. Rebuilds the parenting, then applies DazToUnreal's one hierarchy change:
         pelvis becomes top-level and spine_01 (was hip) becomes its child.
      5. Applies the two DazToUnreal re-positionings (pelvis drop, spine_01 midpoint).
      6. Clamps every bone's length so it never overshoots its nearest child's head
         (see clampBoneLengthsToChildHeads).

    No `root` bone is created: the Blender FBX exporter promotes the "Armature"
    object itself to the root bone, so a root bone here would be a duplicate.

    Re-positioning is applied as a PURE TRANSLATION - head and tail move together,
    so bone direction, length and roll are untouched. Orientation is the separate
    pass that is deliberately not implemented yet.

    Note: this only builds the armature. The G3F mesh is still bound to the
    Diffeomorphic rig and its vertex groups still carry Daz names; re-binding and
    vertex-group renaming are separate steps.
    """
    ZERO_LENGTH_EPS = 1e-6

    # ------------------------------------------------------------------ guards
    if "Armature" in bpy.data.objects:
        msg = "An object named 'Armature' already exists. Delete or rename it first."
        print(msg)
        ShowMessageBox(msg, "Warning", 'INFO')
        return {'CANCELLED'}

    source_armature = bpy.context.scene.objects.active
    if source_armature is None or source_armature.type != 'ARMATURE':
        msg = "Difeomorphic Armature must be selected"
        print(msg)
        ShowMessageBox(msg, "Warning", 'INFO')
        return {'CANCELLED'}

    if source_armature.get("DazRig") is None or source_armature["DazRig"] != "genesis3":
        msg = "Difeomorphic Armature must be selected (DazRig == 'genesis3')"
        print(msg)
        ShowMessageBox(msg, "Warning", 'INFO')
        return {'CANCELLED'}

    # -------------------------------------------------- cache the source bones
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    source_armature.select = True
    bpy.context.scene.objects.active = source_armature
    bpy.ops.object.mode_set(mode='EDIT')
    cachedBonesData = cacheEditBonesData(source_armature)
    bpy.ops.object.mode_set(mode='OBJECT')

    print("alignArmatureFromDifeomorphicToManny: cached {} source bones from '{}'"
          .format(len(cachedBonesData), source_armature.name))

    # --------------------------------------- create the target armature object
    # Created at the origin on purpose: the "Armature" object becomes the root
    # bone on FBX export, and Epic expects root at the origin.
    vx_armature_data = bpy.data.armatures.new("Armature")
    vx_armature = bpy.data.objects.new("Armature", vx_armature_data)
    bpy.context.scene.objects.link(vx_armature)
    vx_armature.location = (0.0, 0.0, 0.0)
    bpy.context.scene.update()

    if vx_armature.name != "Armature":
        # Blender uniquified the name, so something still holds it. Back out
        # rather than silently producing "Armature.001", which would not be
        # promoted to the root bone on export.
        msg = ("Could not create an object named exactly 'Armature' "
               "(Blender produced '{}'). Aborting.".format(vx_armature.name))
        print(msg)
        bpy.data.objects.remove(vx_armature)
        ShowMessageBox(msg, "Warning", 'INFO')
        return {'CANCELLED'}

    bpy.ops.object.select_all(action='DESELECT')
    vx_armature.select = True
    bpy.context.scene.objects.active = vx_armature
    bpy.ops.object.mode_set(mode='EDIT')
    ebones = vx_armature_data.edit_bones

    # ------------------------------------------------- create + rename the bones
    rename_map = dict_bones.getMannyBoneRenameMap()
    created = {}              # source bone name -> new bone name
    skipped_zero_length = []
    name_collisions = []

    for source_name, bone_data in cachedBonesData.items():
        head = bone_data["head"]
        tail = bone_data["tail"]
        if (tail - head).length < ZERO_LENGTH_EPS:
            # Blender silently deletes zero-length bones, so skip them loudly.
            skipped_zero_length.append(source_name)
            continue

        target_name = rename_map.get(source_name, source_name)
        eb = ebones.new(target_name)
        eb.head = head
        eb.tail = tail
        eb.roll = bone_data["roll"]
        # Never connect: connected children are forced to follow the parent tail,
        # which would break the pure-translation re-positioning below.
        eb.use_connect = False

        if eb.name != target_name:
            name_collisions.append((source_name, target_name, eb.name))
        created[source_name] = eb.name

    # ----------------------------------------------------- rebuild the parenting
    for source_name, target_name in created.items():
        source_parent = cachedBonesData[source_name]["parent"]
        # Walk up past anything that was skipped so the chain stays connected.
        while source_parent is not None and source_parent not in created:
            source_parent = cachedBonesData[source_parent]["parent"]
        if source_parent is None:
            ebones[target_name].parent = None
        else:
            ebones[target_name].parent = ebones[created[source_parent]]

    # ------------------------------------- DazToUnreal's hierarchy change
    # DazToUnrealBlueprintUtils.cpp:157-159 does:
    #     ParentBone("pelvis", "root");  ParentBone("hip", "pelvis");
    # With no root bone, "pelvis" simply becomes top-level.
    if "pelvis" in ebones:
        ebones["pelvis"].parent = None
    if "spine_01" in ebones and "pelvis" in ebones:
        ebones["spine_01"].parent = ebones["pelvis"]

    # ------------------------------------------------------- re-positioning
    # Applied as pure translations (head and tail move by the same delta) so that
    # bone direction, length and roll survive untouched.

    # DazToUnreal op 3 - drop the pelvis 70% of the way toward the thighs.
    #   adj = (pelvis.z - thigh_l.z) * 0.7 ; pelvis.location += (0,0,-adj)
    if "pelvis" in ebones and "thigh.L" in ebones:
        pelvis_drop = (ebones["pelvis"].head.z - ebones["thigh.L"].head.z) * 0.7
        delta = Vector((0.0, 0.0, -pelvis_drop))
        ebones["pelvis"].head = ebones["pelvis"].head + delta
        ebones["pelvis"].tail = ebones["pelvis"].tail + delta
        print("  pelvis lowered by {:.6f}".format(pelvis_drop))
    else:
        print("  WARNING: pelvis / thigh.L missing - pelvis drop skipped")

    # DazToUnreal op 4 - place spine_01 between pelvis and spine_02.
    #
    # DazToUnreal writes a LOCAL translation of (rel.z, rel.y, 0), where
    #     rel = (spine_02.global - pelvis.global) * 0.5
    # inside the pelvis frame that op 2 has rotated by (90,-90,-90). Rather than
    # replicate that frame - it belongs to the re-orientation pass, which is not
    # implemented - the head is computed DIRECTLY in global space, one axis at a
    # time. Blender axes: X = side, Y = forward/back, Z = up.
    #
    #   X (side)    the figure's centreline, ~0 on a centred G3F. Taken from the
    #               pelvis rather than hardcoded to 0.0, so an off-centre or
    #               posed rig stays on its own centreline instead of being
    #               yanked to the world origin.
    #   Y (forward) taken from the pelvis. DazToUnreal writes 0 into the third
    #               component, i.e. no forward offset from the parent, so
    #               spine_01 stays level with the pelvis front-to-back rather
    #               than drifting toward spine_02.
    #   Z (up)      half way between pelvis and spine_02 - the "* 0.5" above.
    #
    # If spine_01 ends up sitting too far back on a real figure, the Y line is
    # the one to change; the alternative reading is the plain midpoint:
    #     (pelvis_head.y + spine_02_head.y) / 2.0
    if "spine_01" in ebones and "pelvis" in ebones and "spine_02" in ebones:
        pelvis_head = ebones["pelvis"].head.copy()
        spine_02_head = ebones["spine_02"].head.copy()
        new_head = Vector((
            pelvis_head.x,
            pelvis_head.y,
            (pelvis_head.z + spine_02_head.z) / 2.0,
        ))
        # Tail follows by the same delta so direction, length and roll survive;
        # the length clamp below then pulls the tail in to reach spine_02.
        delta = new_head - ebones["spine_01"].head
        ebones["spine_01"].head = new_head
        ebones["spine_01"].tail = ebones["spine_01"].tail + delta
        print("  spine_01 head set to {} (moved by {})".format(new_head, delta))
    else:
        print("  WARNING: spine_01 / pelvis / spine_02 missing - spine_01 move skipped")

    # ------------------------------------------------------- clamp bone lengths
    # Must run LAST: the two re-positionings above move heads without moving the
    # children, which changes the head-to-child-head distances this depends on.
    clamped = clampBoneLengthsToChildHeads(vx_armature)

    bpy.ops.object.mode_set(mode='OBJECT')

    # ------------------------------------------------- BlenderPerfect rolls
    # Heads and tails are final by this point, so roll is the only remaining
    # degree of freedom. Twist bones created later by setupTwistBones inherit
    # their parent's roll, so they come out correct too - and the full pipeline
    # calls this again at the end anyway, which is safe because it is idempotent.
    applyBlenderPerfectRolls(vx_armature)

    # ------------------------------------------------------------------ report
    renamed_count = sum(1 for n in created if n in rename_map)
    carried_count = len(created) - renamed_count
    print("alignArmatureFromDifeomorphicToManny: created {} bones "
          "({} renamed to Manny, {} carried over with Daz names)"
          .format(len(created), renamed_count, carried_count))

    unmatched = [n for n in rename_map if n not in cachedBonesData]
    if unmatched:
        print("  WARNING: {} mapping entries had no source bone: {}"
              .format(len(unmatched), sorted(unmatched)))
    if skipped_zero_length:
        print("  WARNING: skipped {} zero-length bones: {}"
              .format(len(skipped_zero_length), sorted(skipped_zero_length)))
    if name_collisions:
        print("  WARNING: {} name collisions (Blender uniquified): {}"
              .format(len(name_collisions), name_collisions))
    if clamped:
        print("  clamped {} bone lengths to their nearest child head:".format(len(clamped)))
        for bone_name, was, now in clamped:
            print("      {:<24} {:.6f} -> {:.6f}".format(bone_name, was, now))

    return {'FINISHED'}


def clampBoneLengthsToChildHeads(vx_armature, min_length=1e-5):
    """
    Shorten any bone that overshoots its children, so that

        bone.length <= distance(bone.head, nearest child head)

    Daz bone tails routinely reach past where the next joint starts, and the two
    re-positionings in alignArmatureFromDifeomorphicToManny make it worse - moving
    spine_01's head to the pelvis/spine_02 midpoint roughly halves the distance to
    its child while leaving its tail where it was.

    The bone is shortened ALONG ITS EXISTING DIRECTION, so head position, direction
    and roll are all preserved - only the tail slides in. That keeps this consistent
    with the rest of the function, which deliberately does not re-orient anything.

    Bones are only ever shortened, never extended: the rule is an upper bound.

    Which child counts: only the ONE that logically continues the chain, never
    just the nearest. chestUpper -> spine_05 parents lPectoral and the clavicles
    as well as neck_01, and lPectoral starts lower and nearer - clamping against
    it would leave the upper spine stubby. Selection order:

      1. exactly one child        -> that child
      2. dict_bones.manny_chain_successors has an entry -> that child
         (a None entry marks the bone as the end of its chain: head, ball.L/R)
      3. several children, no entry -> NOT clamped. Warned about if the bone is
         Manny-named, silent for carried-over Daz bones (face rig and friends,
         which are not part of the Manny chain and are nobody's business here).

    Leaf bones are left alone (no children, no constraint). A bone whose chain
    child sits on top of its own head is also left alone rather than being reduced
    to zero length, which Blender would delete.

    The armature must already be in EDIT mode.

    Returns a list of (bone_name, old_length, new_length) for whatever was changed.
    """
    ebones = vx_armature.data.edit_bones
    successors = dict_bones.manny_chain_successors
    snap_to_successor = set(getattr(dict_bones, "bones_length_set_to_successor", []))
    manny_names = set(dict_bones.getMannyBoneRenameMap().values())
    manny_names.add("pelvis")

    # Build the children map from .parent rather than using EditBone.children,
    # which is not reliably exposed in the 2.79 API.
    children_map = {}
    for eb in ebones:
        if eb.parent is not None:
            children_map.setdefault(eb.parent.name, []).append(eb.name)

    clamped = []
    unresolved = []
    for bone_name, child_names in sorted(children_map.items()):
        eb = ebones[bone_name]

        if bone_name in successors:
            candidates = successors[bone_name]
            if candidates is None:
                continue                        # end of chain, deliberately unclamped
            if isinstance(candidates, str):
                candidates = [candidates]
            # First candidate that is actually a child wins, so one entry can cover both
            # sides of a collapse (foot.L -> lMetatarsals before it, ball.L after).
            chain_child = None
            for candidate in candidates:
                if candidate in child_names:
                    chain_child = candidate
                    break
            if chain_child is None:
                print("  WARNING: none of '{}' successors {} are children of it "
                      "{} - not clamped".format(bone_name, candidates, sorted(child_names)))
                continue
        elif len(child_names) == 1:
            chain_child = child_names[0]
        else:
            if bone_name in manny_names:
                unresolved.append((bone_name, sorted(child_names)))
            continue

        max_length = (ebones[chain_child].head - eb.head).length
        if max_length < min_length:
            print("  WARNING: '{}' chain child '{}' head is {:.9f} away - not clamped"
                  .format(bone_name, chain_child, max_length))
            continue

        current_length = eb.length
        if bone_name in snap_to_successor:
            # Set the length EXACTLY, extending as well as shortening. The foot needs
            # this: Daz's lFoot tail stops short of where the ball begins, so capping
            # alone would leave it short of ball.L.
            if abs(current_length - max_length) > min_length:
                direction = (eb.tail - eb.head).normalized()
                eb.tail = eb.head + direction * max_length
                clamped.append((bone_name, current_length, max_length))
        elif current_length > max_length:
            direction = (eb.tail - eb.head).normalized()
            eb.tail = eb.head + direction * max_length
            clamped.append((bone_name, current_length, max_length))

    if unresolved:
        print("  WARNING: {} Manny bone(s) have several children and no "
              "manny_chain_successors entry - left unclamped:".format(len(unresolved)))
        for bone_name, child_names in unresolved:
            print("      {:<24} children: {}".format(bone_name, child_names))

    return clamped


def findDiffeomorphicArmature():
    """
    Locate the Diffeomorphic G3F armature in the scene without relying on the selection.

    Matches on the DazRig property that the import_daz addon writes, which is the same
    test alignArmatureFromDifeomorphicToManny does on the active object - so anything this
    finds will pass that guard.

    The already-converted "Armature" is skipped, so re-running after a partial conversion
    finds the source rig rather than the output.

    Returns (armature_object, error_message). Exactly one of the two is None.
    """
    candidates = []
    for ob in bpy.context.scene.objects:
        if ob.type != 'ARMATURE' or ob.name == "Armature":
            continue
        if ob.get("DazRig") == "genesis3":
            candidates.append(ob)

    if not candidates:
        return (None, "No Difeomorphic G3F armature in the scene "
                      "(looked for an ARMATURE with DazRig == 'genesis3').")
    if len(candidates) > 1:
        return (None, "Found {} Difeomorphic G3F armatures ({}). Delete or rename the "
                      "ones you are not converting.".format(
                          len(candidates), ", ".join(sorted(ob.name for ob in candidates))))
    return (candidates[0], None)


def findConvertedBodyMesh(preferred_name=""):
    """
    Locate the mesh produced by the G3F -> VX body conversion.

    body_subdiv_cage is the canonical name importer_g3f_difeomorphic.py:419 gives it, so
    it is tried first and the panel's mesh selector is only a fallback - the selector
    auto-follows the active object, which makes it an unreliable primary source.

    Returns (mesh_object, error_message). Exactly one of the two is None.
    """
    mesh = bpy.data.objects.get("body_subdiv_cage")
    if mesh is not None and mesh.type == 'MESH':
        return (mesh, None)

    if preferred_name and preferred_name in bpy.data.objects:
        mesh = bpy.data.objects[preferred_name]
        if mesh.type == 'MESH':
            print("findConvertedBodyMesh: no 'body_subdiv_cage', using the selector's "
                  "'{}'".format(mesh.name))
            return (mesh, None)

    return (None, "No converted body mesh found. Run 'G3F->VX body' first, or pick the "
                  "mesh in the VXMod mesh selector.")


def bindMeshToArmature(mesh_object, armature_object, modifier_name="Armature"):
    """
    Give a mesh an ARMATURE modifier pointing at an armature.

    The mesh is deliberately NOT parented to the armature - only the modifier is linked.
    body_subdiv_cage stays a top-level object. The exporter builds its own hierarchy at
    export time (exporter_unreal.py:1486 parents the LOD group under the armature clone),
    so parenting the source mesh here would only get in the way.

    Nothing else in this addon does even this much. The G3F -> VX body conversion detaches
    the body clone (importer_g3f_difeomorphic.py:83 sets parent = None) and never links an
    armature, so it has been a manual step. The exporter only CHECKS the modifier exists
    (exporter_unreal.py:421 aborts with "Object ... has no armature!"), and the panel label
    at __init__.py:392 switches between "Export SM_" and "Export SKM_" on it.

    The modifier is created explicitly rather than through
    bpy.ops.object.parent_set(type='ARMATURE_NAME') - that operator would parent the mesh,
    which is exactly what we do not want, and its result depends on the current selection.

    Re-running is safe: an existing ARMATURE modifier is retargeted instead of a second one
    being added, and a parent left over from an earlier run is cleared.

    Returns the modifier, or None if the arguments were wrong.
    """
    if mesh_object is None or mesh_object.type != 'MESH':
        print("bindMeshToArmature: first argument must be a mesh.")
        return None
    if armature_object is None or armature_object.type != 'ARMATURE':
        print("bindMeshToArmature: second argument must be an armature.")
        return None

    modifier = None
    for mod in mesh_object.modifiers:
        if mod.type == 'ARMATURE':
            modifier = mod
            break

    if modifier is None:
        modifier = mesh_object.modifiers.new(name=modifier_name, type='ARMATURE')

    modifier.object = armature_object
    modifier.use_vertex_groups = True

    # Explicitly NOT parented. Clear one if an earlier run (or a manual
    # Ctrl+P > Armature Deform) left the mesh as a child, keeping it where it is.
    if mesh_object.parent is not None:
        previous_parent = mesh_object.parent.name
        matrix = mesh_object.matrix_world.copy()
        mesh_object.parent = None
        mesh_object.matrix_world = matrix
        print("bindMeshToArmature: cleared parent '{}' - the mesh stays top-level"
              .format(previous_parent))

    print("bindMeshToArmature: '{}' -> ARMATURE modifier on '{}' (not parented)"
          .format(mesh_object.name, armature_object.name))
    return modifier


def mergeBonesIntoTargets(mesh_object, armature_object, rules=None, delete_bones=True):
    """
    Fold several bones' weights into one, then delete the merged bones.

    This is the bone-count reduction step. With the defaults it collapses the G3F face
    rig using dict_bones.bone_collapse_rules - 47 bones into head, 19 into lowerJaw,
    taking the rig from 172 to 106.

    `rules` is {target bone: [bones to absorb]}, taken LITERALLY. There is deliberately
    no hierarchy walking: dict_bones.face_bones_merged_to_head / _to_lower_jaw are
    explicit hardcoded lists precisely so the collapsed set is inspectable and editable,
    rather than an emergent property of the rig. Move a name out of a list and that bone
    survives.

    Names not present in the rig are reported and skipped, and the target is never taken
    as one of its own sources.

    (For the interactive "select bones, merge into the active one" workflow, use
    gmtt.mesh_merge_weights in the Game Mod Tiny Tools addon - it is not duplicated here.)

    Runs AFTER both renames (bones in step 1, vertex groups in step 3), so bone names and
    group names agree. Mapped bones appear here under their Manny names (foot.L), unmapped
    ones under their Daz names (head, lowerJaw, lHeel, lMetatarsals, the face rig).

    Weights are merged with merge_vgroups_into_existing (helper_vgroups.py), NOT
    mergeSubgroupsIntoGroup - the latter wipes the target group first and would throw
    away head's and lowerJaw's own weights.

    Returns (merged_summary, deleted_bone_names).
    """
    if rules is None:
        rules = dict_bones.bone_collapse_rules

    if mesh_object is None or mesh_object.type != 'MESH':
        print("mergeBonesIntoTargets: first argument must be a mesh.")
        return ({}, [])
    if armature_object is None or armature_object.type != 'ARMATURE':
        print("mergeBonesIntoTargets: second argument must be an armature.")
        return ({}, [])

    # A careless edit to the hardcoded lists must not be able to delete a bone the rest
    # of the pipeline depends on (lEye, upperTeeth, tongue01, ...).
    protected = set(getattr(dict_bones, "bones_that_must_be_kept", []))
    if protected:
        for target_name, source_names in rules.items():
            clash = protected.intersection(source_names)
            if clash:
                print("mergeBonesIntoTargets: ABORTED - {} are in the collapse list for "
                      "'{}' but are marked must-keep.".format(sorted(clash), target_name))
                return ({}, [])

    bpy.ops.object.mode_set(mode='OBJECT')

    summary = {}
    all_swept = []

    for target_name, root_names in rules.items():
        if target_name not in armature_object.data.bones:
            print("mergeBonesIntoTargets: target bone '{}' not in armature - skipped"
                  .format(target_name))
            continue

        # Literal list. Keep only bones the rig actually has, and never the target.
        bone_names = armature_object.data.bones.keys()
        subtree = [n for n in root_names if n != target_name and n in bone_names]
        absent = [n for n in root_names if n not in bone_names]
        if absent:
            print("  note: {} listed for '{}' but not in this rig".format(absent, target_name))

        if not subtree:
            print("mergeBonesIntoTargets: nothing to collapse into '{}'".format(target_name))
            continue

        written, used = merge_vgroups_into_existing(mesh_object, target_name, subtree)
        summary[target_name] = {"swept": subtree, "groups_merged": used, "vertices": written}
        all_swept.extend(subtree)

        print("mergeBonesIntoTargets: -> '{}'  ({} bones, {} carried weight, {} verts)"
              .format(target_name, len(subtree), len(used), written))

    # The emptied source groups are now redundant; drop them so the later rename pass and
    # the exporter do not see stale Daz groups.
    for bone_name in all_swept:
        deleteVertexGroup(mesh_object, bone_name)

    deleted = []
    if delete_bones and all_swept:
        previous_active = bpy.context.scene.objects.active
        bpy.ops.object.select_all(action='DESELECT')
        armature_object.select = True
        bpy.context.scene.objects.active = armature_object
        bpy.ops.object.mode_set(mode='EDIT')
        ebones = armature_object.data.edit_bones
        doomed = set(all_swept)

        # Reparent survivors BEFORE deleting, rather than trusting whatever Blender does
        # with the children of a removed edit bone.
        #
        # This is what keeps the rig Manny-compatible at the foot: Manny has ball_l as a
        # DIRECT child of foot_l, while Daz has lFoot -> lMetatarsals -> lToe. Dropping
        # lMetatarsals without this would leave lToe orphaned; with it, lToe moves up onto
        # lFoot and the rename gives foot.L -> ball.L.
        reparented = []
        for eb in ebones:
            if eb.name in doomed or eb.parent is None:
                continue
            new_parent = eb.parent
            while new_parent is not None and new_parent.name in doomed:
                new_parent = new_parent.parent
            if new_parent is not eb.parent:
                reparented.append((eb.name, eb.parent.name,
                                   new_parent.name if new_parent else None))
                eb.parent = new_parent
        for child_name, was, now in reparented:
            print("  reparented '{}': {} -> {}".format(child_name, was, now))

        # Explicit overrides on top of the nearest-surviving-ancestor rule. Daz parents
        # the toes to lMetatarsals as siblings of lToe, so without this they would land
        # on foot.L beside ball.L instead of under it.
        for new_parent_name, child_names in getattr(dict_bones,
                                                    "bone_reparent_overrides", {}).items():
            new_parent = ebones.get(new_parent_name)
            if new_parent is None:
                print("  WARNING: reparent target '{}' not in the rig - {} left alone"
                      .format(new_parent_name, child_names))
                continue
            for child_name in child_names:
                child = ebones.get(child_name)
                if child is None or child.name in doomed:
                    continue
                if child.parent is not new_parent:
                    print("  reparented '{}': {} -> {} (override)".format(
                        child_name, child.parent.name if child.parent else None,
                        new_parent_name))
                    child.parent = new_parent

        # Deepest first, so removing a parent never orphans a bone we still have to visit.
        for bone_name in sorted(doomed, key=len, reverse=True):
            eb = ebones.get(bone_name)
            if eb is not None:
                ebones.remove(eb)
                deleted.append(bone_name)

        # The chains just changed shape, so re-derive the bone lengths. foot.L in
        # particular was clamped against lMetatarsals and must now reach ball.L.
        clampBoneLengthsToChildHeads(armature_object)

        bpy.ops.object.mode_set(mode='OBJECT')
        if previous_active is not None:
            bpy.context.scene.objects.active = previous_active
        print("mergeBonesIntoTargets: deleted {} collapsed bones, reparented {} survivors"
              .format(len(deleted), len(reparented)))

    return (summary, deleted)


def setupTwistBones(mesh_object, armature_object, pairs=None):
    """
    Make the twist bones Manny-shaped: out of the chain, in pairs, weights blended.

    Daz gives one twist per joint and puts it IN the chain
    (lShldrBend -> lShldrTwist -> lForearmBend); Manny gives two and hangs them off the
    parent as leaves. Three things are therefore done, in order:

    1. TAKE THE TWISTS OUT OF THE CHAIN. Every child of a twist bone is reparented to
       that twist's own parent, so calf.L moves from thigh_twist_01.L onto thigh.L,
       lowerarm.L onto upperarm.L and hand.L onto lowerarm.L. This is exactly what
       DazToUnreal's FixTwistBones (DazToUnrealFbx.cpp:174) does, and it forces it on for
       every Convert-To-Epic run. Without it the limb hierarchy does not match Manny.

    2. SETTLE THE PARENT LENGTHS. Only now that the twists are leaves does thigh.L
       actually have calf.L as a direct child, so only now can it be stretched to reach
       it. Ordering matters: the twist fractions in step 3 are measured off these
       lengths, so clamping afterwards would leave them measured against stale ones.

    3. CREATE AND REPOSITION BOTH TWISTS of each pair, from dict_bones.twist_bone_pairs -
       spaced at 1/3 and 2/3 along the settled parent, each a third of it long, roll
       copied from the parent. Existing Daz-derived twists are moved onto the same rule.

    4. SPLIT THE WEIGHTS smoothly. Whichever of the pair already carries weight (usually
       _01, but the forearm's single Daz twist maps to _02) is the source. Each weighted
       vertex is projected onto the twist axis to get t in [0,1], and the weight is split
       (1-t) to _01 and t to _02 - so influence hands over gradually along the limb
       instead of switching abruptly. The sum is preserved exactly, so nothing changes at
       rest; the pair only differs once they rotate.

    Daz has no shin twist, so calf_twist_01/02 get no source weights. They are still
    created, because Manny expects them, and are reported as empty.

    Returns (created, repositioned, split_summary).
    """
    if pairs is None:
        pairs = dict_bones.twist_bone_pairs

    if mesh_object is None or mesh_object.type != 'MESH':
        print("setupTwistBones: first argument must be a mesh.")
        return ([], [], [])
    if armature_object is None or armature_object.type != 'ARMATURE':
        print("setupTwistBones: second argument must be an armature.")
        return ([], [], [])

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    armature_object.select = True
    bpy.context.scene.objects.active = armature_object
    bpy.ops.object.mode_set(mode='EDIT')
    ebones = armature_object.data.edit_bones

    # --- 1. take the twists out of the chain ---------------------------------------
    children_map = {}
    for eb in ebones:
        if eb.parent is not None:
            children_map.setdefault(eb.parent.name, []).append(eb.name)

    unchained = []
    for bone_name, child_names in sorted(children_map.items()):
        if "twist" not in bone_name.lower():
            continue
        twist_eb = ebones[bone_name]
        new_parent = twist_eb.parent
        for child_name in child_names:
            child = ebones[child_name]
            child.parent = new_parent
            unchained.append((child_name, bone_name,
                              new_parent.name if new_parent else None))
    for child_name, was, now in unchained:
        print("  twist out of chain: '{}' {} -> {}".format(child_name, was, now))

    # --- 2. settle the PARENT lengths before measuring anything off them -------------
    # This has to happen here, not after the twists are placed. Until step 1 ran, the
    # joint bones' chain successors were hidden behind the in-line twists, so thigh.L
    # was still clamped against thigh_twist_01.L rather than reaching calf.L. Placing
    # the twists first would measure 1/3 and 2/3 of a length that is about to change.
    clampBoneLengthsToChildHeads(armature_object)

    # --- 3. create / reposition both twists of each pair -----------------------------
    created, repositioned = [], []
    parent_geometry = {}   # parent name -> (head, unit direction, length)
    for parent_name, twists, length_fraction in pairs:
        parent_eb = ebones.get(parent_name)
        if parent_eb is None:
            print("  WARNING: twist parent '{}' not in the rig - {} skipped"
                  .format(parent_name, [n for n, f in twists]))
            continue
        parent_length = parent_eb.length
        if parent_length <= 0.0:
            print("  WARNING: '{}' has zero length - twists skipped".format(parent_name))
            continue
        direction = (parent_eb.tail - parent_eb.head).normalized()
        parent_geometry[parent_name] = (parent_eb.head.copy(), direction.copy(), parent_length)

        for twist_name, head_fraction in twists:
            head = parent_eb.head + direction * (parent_length * head_fraction)
            tail = head + direction * (parent_length * length_fraction)
            eb = ebones.get(twist_name)
            if eb is None:
                eb = ebones.new(twist_name)
                created.append(twist_name)
            else:
                repositioned.append(twist_name)
            eb.head = head
            eb.tail = tail
            eb.roll = parent_eb.roll
            eb.use_connect = False
            eb.parent = parent_eb
            print("  {:<22} at {:.0f}% of {}".format(
                twist_name, head_fraction * 100.0, parent_name))

    bpy.ops.object.mode_set(mode='OBJECT')
    print("setupTwistBones: {} created, {} repositioned, {} bones taken out of chain"
          .format(len(created), len(repositioned), len(unchained)))

    # --- 4. split the weights smoothly ----------------------------------------------
    split_summary = []
    for parent_name, twists, length_fraction in pairs:
        if parent_name not in parent_geometry:
            continue
        (name_01, fraction_01), (name_02, fraction_02) = twists[0], twists[1]
        written = _splitTwistWeights(mesh_object, name_01, name_02,
                                     parent_geometry[parent_name],
                                     fraction_01, fraction_02)
        if written is None:
            print("  '{}' / '{}': no source weights (Daz has no twist here) - "
                  "created empty".format(name_01, name_02))
            for twist_name in (name_01, name_02):
                if mesh_object.vertex_groups.get(twist_name) is None:
                    mesh_object.vertex_groups.new(name=twist_name)
        else:
            split_summary.append((name_01, name_02, written))
            print("  split {} verts between '{}' and '{}'".format(written, name_01, name_02))

    return (created, repositioned, split_summary)


def _splitTwistWeights(mesh_object, name_01, name_02, parent_geometry,
                       fraction_01, fraction_02):
    """
    Blend one twist group's weights smoothly across the _01 / _02 pair.

    Each weighted vertex is projected onto the PARENT bone's axis to give t in [0, 1]
    (0 at the parent's head, 1 at its tail), which is then remapped onto the span the
    two twists occupy. The twist sitting nearer the parent's head takes (1-u), the
    other takes u, so influence hands over gradually instead of switching abruptly.

    Which bone gets which end is derived from the fractions, not assumed - the calf
    pair is deliberately reversed (_01 at 2/3 near the ankle, _02 at 1/3 near the
    knee), and hard-coding "_01 gets the near end" would blend it backwards.

    w*(1-u) + w*u == w, so total influence per vertex is unchanged and the mesh does
    not move at rest; the pair only diverges once they rotate.

    The source is whichever of the two already has a group - usually _01, but the Daz
    forearm twist maps to _02 (DazToUnreal's "// The Lower Arm twists are swapped").

    Returns the number of vertices written, or None if neither group has weights.
    """
    groups = mesh_object.vertex_groups
    source = groups.get(name_01)
    if source is None:
        source = groups.get(name_02)
    if source is None:
        return None

    head, direction, length = parent_geometry
    if length <= 0.0:
        return None

    low = min(fraction_01, fraction_02)
    high = max(fraction_01, fraction_02)
    span = high - low
    # Whichever twist sits nearer the parent's head owns the (1-u) end.
    near_is_01 = fraction_01 <= fraction_02

    matrix = mesh_object.matrix_world
    source_index = source.index

    # Read everything first: the source is one of the two groups about to be written.
    samples = []
    for v in mesh_object.data.vertices:
        for g in v.groups:
            if g.group == source_index and g.weight > 0.0:
                world_co = matrix * v.co
                t = (world_co - head).dot(direction) / length
                if span > 0.0:
                    u = (t - low) / span
                else:
                    u = 0.5
                u = max(0.0, min(1.0, u))
                samples.append((v.index, g.weight, u))
                break

    if not samples:
        return None

    group_01 = groups.get(name_01) or groups.new(name=name_01)
    group_02 = groups.get(name_02) or groups.new(name=name_02)
    for v_index, weight, u in samples:
        near_weight = weight * (1.0 - u)
        far_weight = weight * u
        if near_is_01:
            group_01.add([v_index], near_weight, 'REPLACE')
            group_02.add([v_index], far_weight, 'REPLACE')
        else:
            group_01.add([v_index], far_weight, 'REPLACE')
            group_02.add([v_index], near_weight, 'REPLACE')

    return len(samples)


def switchVertexGroupsToManny(mesh_object, armature_object=None, delete_unmapped=False):
    """
    Rename the mesh's Daz vertex groups to Manny names, matching the armature built by
    alignArmatureFromDifeomorphicToManny.

    The mapping is GENERATED from dict_bones.getMannyBoneRenameMap() rather than being a
    second hand-written table. That is deliberate: the old VXMod path keeps its bone names
    in difeomorphic_workflow_dictionaries_bones.py and its group names in
    difeomorphic_workflow_dictionaries_vertex_groups.py, and the two had already drifted -
    spine_weights_matching maps abdomenLower -> spine_01 while the bone table maps it to
    spine_02, so the whole spine was off by one and spine_05 got no weights at all. With
    one source of truth that cannot happen again.

    This is a PURE 1:1 rename. All weight merging - the face rig into head/lowerJaw, the
    heel and metatarsals into the foot - is done AFTERWARDS by mergeBonesIntoTargets,
    which also deletes the bones. Keeping the two apart means this function cannot invent
    a group that has no bone.

    Order matters: the armature builder renamed the bones already, so this has to run
    before the collapse or the two would still be in different name spaces and a rule
    targeting foot.L would match the bone but not the group.

    delete_unmapped is OFF by default. Anything it would remove is reported instead, so a
    group that unexpectedly has no bone surfaces as a message rather than as silent data
    loss.

    Returns (renamed, merged, leftover_groups). `merged` is always empty and is kept only
    so existing callers do not break.
    """
    if mesh_object is None or mesh_object.type != 'MESH':
        print("switchVertexGroupsToManny: argument must be a mesh.")
        return ([], [], [])

    rename_map = dict_bones.getMannyBoneRenameMap()
    merge_rules = {}
    merged = []

    # --- 1:1 renames ---------------------------------------------------------------
    renamed = []
    for daz_name, manny_name in rename_map.items():
        if daz_name == manny_name:
            continue
        if daz_name not in mesh_object.vertex_groups:
            continue
        if manny_name in mesh_object.vertex_groups:
            print("  WARNING: cannot rename '{}' -> '{}', target group already exists"
                  .format(daz_name, manny_name))
            continue
        renameVertexGroup(mesh_object, daz_name, manny_name)
        renamed.append((daz_name, manny_name))

    # --- 3. report / optionally remove groups with no bone -------------------------
    # Checked against the armature's actual bone names rather than guessing from the
    # spelling of the group. This is the invariant that matters: a group with no bone
    # deforms nothing, and a bone with no group is dead weight in the export.
    if armature_object is not None and armature_object.type == 'ARMATURE':
        bone_names = set(armature_object.data.bones.keys())
        leftover = sorted(vg.name for vg in mesh_object.vertex_groups
                          if vg.name not in bone_names)
        boneless = sorted(bone_names - set(vg.name for vg in mesh_object.vertex_groups))
    else:
        manny_targets = set(rename_map.values()) | set(merge_rules.keys())
        leftover = sorted(vg.name for vg in mesh_object.vertex_groups
                          if vg.name not in manny_targets)
        boneless = []

    print("switchVertexGroupsToManny: {} renamed, {} merge rules applied".format(
        len(renamed), len(merged)))

    if leftover:
        if delete_unmapped:
            for group_name in leftover:
                deleteVertexGroup(mesh_object, group_name)
            print("  deleted {} groups with no matching bone: {}".format(len(leftover), leftover))
        else:
            print("  {} groups have NO matching bone (left in place, not deleted):"
                  .format(len(leftover)))
            print("      {}".format(leftover))

    if boneless:
        print("  {} bones have no vertex group (they will not deform anything):"
              .format(len(boneless)))
        print("      {}".format(boneless))

    return (renamed, merged, leftover)


def applyBlenderPerfectRolls(vx_armature=None, verbose=True):
    """
    Put the rig into ArmatureBlenderPerfect orientation - the convention all
    Blender work happens in, and the one the exporter converts out of.

    Under it every joint flexes about its local +X, the spine/neck/head sit at
    roll 0, left and right mirror the way Blender's Symmetrize expects, and the
    IK pole angle is -90 everywhere with the pole on its natural side (in front
    of the knee, behind the elbow).

    Only ROLL is touched. Heads, tails, lengths, parenting and the bone set are
    left exactly as the builder placed them.

    Diffeomorphic already delivers this convention almost everywhere - the spine
    column is exact to three decimals, the legs are within a couple of degrees,
    and the arms were confirmed by eye - so the table in
    difeomorphic_workflow_dictionaries_bones is deliberately tiny. A bone with no
    entry keeps its Daz roll because that IS the right answer for it.

    Idempotent in practice: re-running re-adds the delta, so it is guarded by the
    orientation stamp rather than by the arithmetic. Safe to call again after
    setupTwistBones, which is why the pipeline does - freshly created twists need
    to pick up their parent's roll.
    """
    if vx_armature is None:
        vx_armature = bpy.data.objects.get("Armature")
    if vx_armature is None or vx_armature.type != 'ARMATURE':
        print("applyBlenderPerfectRolls: no armature named 'Armature' found")
        return {'CANCELLED'}

    # A delta ADDS, so applying it twice would double it. The stamp is the guard:
    # on a rig already in BP only the twist inheritance re-runs, which is what the
    # second call in the pipeline is actually for.
    already_bp = vx_armature.data.get(ORIENTATION_PROP) == ORIENTATION_BP

    token = _beginEditBones(vx_armature)

    adjusted = []
    for eb in ([] if already_bp else vx_armature.data.edit_bones):
        delta = dict_bones.blender_perfect_roll_deltas.get(eb.name)
        if not delta:
            continue
        # First write wins, so calling this twice (the pipeline does) keeps the
        # original Daz roll rather than caching the adjusted one over it.
        if eb.get(ROLL_CACHE_PROP) is None:
            eb[ROLL_CACHE_PROP] = math.degrees(eb.roll)
        eb.roll = radians(_wrapDegrees(math.degrees(eb.roll) + delta))
        adjusted.append(eb.name)

    # Bones aimed rather than offset. Absolute, so unlike a delta this is safe to
    # re-apply and does not need the already_bp guard.
    aimed = []
    for eb in vx_armature.data.edit_bones:
        target = dict_bones.blender_perfect_roll_axis_targets.get(eb.name)
        if target is None:
            continue
        if eb.get(ROLL_CACHE_PROP) is None:
            eb[ROLL_CACHE_PROP] = math.degrees(eb.roll)
        eb.align_roll(Vector(target))
        aimed.append(eb.name)

    # Bones whose X is a hinge derived from two bone directions. Also absolute.
    hinged = []
    for name, (a_name, b_name, sign) in sorted(
            dict_bones.blender_perfect_hinge_rules.items()):
        eb = vx_armature.data.edit_bones.get(name)
        a = vx_armature.data.edit_bones.get(a_name)
        b = vx_armature.data.edit_bones.get(b_name)
        if eb is None or a is None or b is None:
            print("  WARNING: hinge rule for '{}' needs {} and {} - skipped"
                  .format(name, a_name, b_name))
            continue
        da = (a.tail - a.head).normalized()
        db = (b.tail - b.head).normalized()
        bend = math.degrees(da.angle(db))
        if bend < dict_bones.minimum_hinge_bend_degrees:
            print("  WARNING: '{}' hinge is only {:.2f} deg of bend - left on its "
                  "own roll rather than guessed".format(name, bend))
            continue
        if eb.get(ROLL_CACHE_PROP) is None:
            eb[ROLL_CACHE_PROP] = math.degrees(eb.roll)
        axis = da.cross(db).normalized() * sign
        eb.align_roll(axis.cross((eb.tail - eb.head).normalized()))
        hinged.append(eb.name)

    # Fingers: X along the knuckle line. Uses bone HEADS, so unlike the hinge
    # rules it is immune to how straight the finger happens to be.
    knuckled = []
    for members, from_name, to_name, sign in dict_bones.blender_perfect_knuckle_rules:
        a = vx_armature.data.edit_bones.get(from_name)
        b = vx_armature.data.edit_bones.get(to_name)
        if a is None or b is None:
            print("  WARNING: knuckle rule needs {} and {} - {} bones skipped"
                  .format(from_name, to_name, len(members)))
            continue
        across = (b.head - a.head)
        if across.length < 1e-6:
            print("  WARNING: {} and {} are in the same place - {} bones skipped"
                  .format(from_name, to_name, len(members)))
            continue
        axis = across.normalized() * sign
        for name in members:
            eb = vx_armature.data.edit_bones.get(name)
            if eb is None:
                continue
            if eb.get(ROLL_CACHE_PROP) is None:
                eb[ROLL_CACHE_PROP] = math.degrees(eb.roll)
            eb.align_roll(axis.cross((eb.tail - eb.head).normalized()))
            knuckled.append(name)

    # Twists share their parent's axis by definition, so they follow rather than
    # carry their own value. Done after the table so a parent that moved takes
    # its twists with it.
    twisted = 0
    for eb in vx_armature.data.edit_bones:
        if dict_bones.twist_bone_name_marker not in eb.name or eb.parent is None:
            continue
        if eb.get(ROLL_CACHE_PROP) is None:
            eb[ROLL_CACHE_PROP] = math.degrees(eb.roll)
        eb.roll = eb.parent.roll
        twisted += 1

    _endEditBones(token)

    vx_armature.data[ORIENTATION_PROP] = ORIENTATION_BP

    if verbose:
        print("applyBlenderPerfectRolls: {} offset {}, {} aimed {}, {} hinged {}, "
              "{} knuckle-aligned, {} twists took their parent's roll, everything "
              "else kept its Daz roll{}"
              .format(len(adjusted), sorted(adjusted), len(aimed), sorted(aimed),
                      len(hinged), sorted(hinged), len(knuckled), twisted,
                      " (already BP, offsets skipped)" if already_bp else ""))
        missing = sorted((set(dict_bones.blender_perfect_roll_deltas)
                          | set(dict_bones.blender_perfect_roll_axis_targets))
                         - set(b.name for b in vx_armature.data.bones))
        if missing:
            print("  WARNING: table entries with no such bone: {}".format(missing))
    return {'FINISHED'}


def _rollRuleGroups(edit_bones):
    """The intrinsic definition of a 'perfect' roll, as bone -> (hinge source).

    X is the joint's natural hinge, so flexion is a positive rotation about X.
    Where a hinge can be measured from the rig's own rest pose we use it; the
    spine column has no bend to measure, so its hinge is simply the body's
    left/right axis, which makes forward bending +X.

    A limb shares one hinge along its whole chain - the knee plane drives thigh,
    calf and their twists; the elbow plane drives upperarm, lowerarm and theirs -
    which is what keeps the limb planar and the IK solver happy. Verified against
    the UE5 reference rig, where this reproduces Epic's own rolls to 0.000 deg for
    legs, arms and spine.

    Bones with no entry (foot, ball, hand, clavicle and every Daz extra) are
    deliberately absent: they have no natural hinge, so their Daz roll stands."""
    groups = []
    for side in ('.L', '.R'):
        groups.append((('thigh' + side, 'calf' + side),
                       ['thigh' + side, 'calf' + side,
                        'thigh_twist_01' + side, 'thigh_twist_02' + side,
                        'calf_twist_01' + side, 'calf_twist_02' + side]))
        groups.append((('upperarm' + side, 'lowerarm' + side),
                       ['upperarm' + side, 'lowerarm' + side,
                        'upperarm_twist_01' + side, 'upperarm_twist_02' + side,
                        'lowerarm_twist_01' + side, 'lowerarm_twist_02' + side]))
        for finger in ('index', 'middle', 'ring', 'pinky'):
            groups.append(((finger + '_01' + side, finger + '_02' + side),
                           [finger + '_metacarpal' + side, finger + '_01' + side,
                            finger + '_02' + side, finger + '_03' + side]))
        groups.append((('thumb_01' + side, 'thumb_02' + side),
                       ['thumb_01' + side, 'thumb_02' + side, 'thumb_03' + side]))
    spine = ['pelvis', 'spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05',
             'neck_01', 'neck_02', 'head']
    groups.append((None, [n for n in spine if n in edit_bones]))
    return groups


def _rollAimGroups():
    """Bones whose rule is 'aim the secondary axis', not 'X on a hinge'."""
    return dict(dict_bones.blender_perfect_roll_axis_targets)


def _boneDirection(eb):
    return (eb.tail - eb.head).normalized()


def reportRollRuleDeltas(vx_armature=None, min_bend_degrees=0.5):
    """Print, per bone, how far the Diffeomorphic roll is from the rule.

    Run this ONCE on a rig in its Daz state. The point is the 'delta' column: if
    those land on multiples of 90 they can be frozen into a hardcoded table and
    applied blindly to any G3F-generation rig, with no geometry needed at
    runtime - which also removes the conditioning problem, since a knee with only
    a degree of rest bend is a poor basis for a cross product.

    'off90' is the distance from the nearest multiple of 90. Small values mean the
    delta is safe to freeze; large ones mean that bone genuinely needs deciding.
    """
    if vx_armature is None:
        vx_armature = bpy.data.objects.get("Armature")
    if vx_armature is None or vx_armature.type != 'ARMATURE':
        print("reportRollRuleDeltas: no armature named 'Armature' found")
        return {'CANCELLED'}

    token = _beginEditBones(vx_armature)
    ebones = vx_armature.data.edit_bones
    rows = []
    weak = []
    for hinge_source, members in _rollRuleGroups(ebones):
        if hinge_source is None:
            hinge = Vector((1.0, 0.0, 0.0))          # body left/right
            bend = None
        else:
            parent_name, child_name = hinge_source
            if parent_name not in ebones or child_name not in ebones:
                continue
            pd = _boneDirection(ebones[parent_name])
            cd = _boneDirection(ebones[child_name])
            bend = math.degrees(pd.angle(cd))
            if bend < min_bend_degrees:
                weak.append((parent_name, bend))
                continue
            hinge = pd.cross(cd).normalized()
        for name in members:
            eb = ebones.get(name)
            if eb is None:
                continue
            keep = eb.roll
            daz = math.degrees(keep)
            eb.align_roll(hinge.cross(_boneDirection(eb)).normalized())
            perfect = math.degrees(eb.roll)
            eb.roll = keep
            delta = ((perfect - daz) + 180.0) % 360.0 - 180.0
            nearest = round(delta / 90.0) * 90.0
            rows.append((name, daz, perfect, delta, nearest,
                         abs(delta - nearest), bend))
    def _record(name, target_z, bend):
        eb = ebones.get(name)
        if eb is None:
            return
        keep = eb.roll
        daz = math.degrees(keep)
        eb.align_roll(target_z)
        perfect = math.degrees(eb.roll)
        eb.roll = keep
        delta = ((perfect - daz) + 180.0) % 360.0 - 180.0
        nearest = round(delta / 90.0) * 90.0
        rows.append((name, daz, perfect, delta, nearest, abs(delta - nearest), bend))

    # aimed bones: the rule is a direction for the secondary axis, not a hinge
    for name, target in sorted(_rollAimGroups().items()):
        _record(name, Vector(target), None)

    # fingers aimed along the knuckle line
    for members, from_name, to_name, sign in dict_bones.blender_perfect_knuckle_rules:
        a, b = ebones.get(from_name), ebones.get(to_name)
        if a is None or b is None or (b.head - a.head).length < 1e-6:
            continue
        axis = (b.head - a.head).normalized() * sign
        for name in members:
            eb = ebones.get(name)
            if eb is not None:
                _record(name, axis.cross(_boneDirection(eb)), None)

    # hinge-derived bones (the wrist and the thumb)
    for name, (a_name, b_name, sign) in sorted(
            dict_bones.blender_perfect_hinge_rules.items()):
        eb, a, b = ebones.get(name), ebones.get(a_name), ebones.get(b_name)
        if eb is None or a is None or b is None:
            continue
        da = _boneDirection(a)
        db = _boneDirection(b)
        bend = math.degrees(da.angle(db))
        if bend < dict_bones.minimum_hinge_bend_degrees:
            weak.append((name, bend))
            continue
        axis = da.cross(db).normalized() * sign
        _record(name, axis.cross(_boneDirection(eb)), bend)

    unruled = sorted(eb.name for eb in ebones
                     if eb.name not in [r[0] for r in rows])
    _endEditBones(token)

    print("")
    print("=== roll rule report for {} ===".format(vx_armature.name))
    print("    X = the joint's natural hinge, so flexion is +X")
    print("")
    print("  %-24s %9s %9s %9s %8s %7s %7s"
          % ("bone", "daz", "rule", "delta", "near90", "off90", "bend"))
    for name, daz, perfect, delta, nearest, off, bend in rows:
        print("  %-24s %+9.3f %+9.3f %+9.3f %+8.0f %7.3f %7s"
              % (name, daz, perfect, delta, nearest, off,
                 "-" if bend is None else "%.2f" % bend))
    if rows:
        worst = max(rows, key=lambda r: r[5])
        print("")
        print("  worst distance from a multiple of 90: %.3f deg on %s"
              % (worst[5], worst[0]))
    if weak:
        print("  joints too straight to give a reliable hinge (<%.2f deg), skipped: %s"
              % (min_bend_degrees, weak))
    print("  no rule, Daz roll stands (%d): %s" % (len(unruled), unruled))
    print("")
    return {'FINISHED'}


def restoreDazRolls(vx_armature=None, verbose=True):
    """Put every roll back to what Diffeomorphic delivered, for comparison.

    Reads the per-bone cache applyBlenderPerfectRolls left behind. Rolls only, so
    the rig is otherwise untouched and toggling back and forth is lossless.

    The armature is stamped DAZ afterwards, which the exporter refuses to convert
    - a rig in this state would get BlenderPerfect export constants applied to Daz
    rolls and come out wrong in every joint.
    """
    if vx_armature is None:
        vx_armature = bpy.data.objects.get("Armature")
    if vx_armature is None or vx_armature.type != 'ARMATURE':
        print("restoreDazRolls: no armature named 'Armature' found")
        return {'CANCELLED'}

    token = _beginEditBones(vx_armature)
    restored = 0
    for eb in vx_armature.data.edit_bones:
        cached = eb.get(ROLL_CACHE_PROP)
        if cached is None:
            continue
        eb.roll = radians(cached)
        restored += 1
    _endEditBones(token)

    if restored == 0:
        print("restoreDazRolls: no cached rolls on {} - has "
              "applyBlenderPerfectRolls run on it?".format(vx_armature.name))
        return {'CANCELLED'}

    vx_armature.data[ORIENTATION_PROP] = ORIENTATION_DAZ
    if verbose:
        print("restoreDazRolls: restored {} rolls on {}"
              .format(restored, vx_armature.name))
    return {'FINISHED'}


def toggleBlenderPerfectRolls(vx_armature=None):
    """Flip between the BlenderPerfect rolls and the original Daz ones.

    Only rolls move, so nothing else about the rig changes and you can flip as
    often as you like to see the difference."""
    if vx_armature is None:
        vx_armature = bpy.data.objects.get("Armature")
    if vx_armature is None or vx_armature.type != 'ARMATURE':
        print("toggleBlenderPerfectRolls: no armature named 'Armature' found")
        return {'CANCELLED'}, None

    state = vx_armature.data.get(ORIENTATION_PROP)
    if state == ORIENTATION_UE5:
        print("toggleBlenderPerfectRolls: {} is in UE5 orientation, not a roll "
              "difference - nothing to toggle".format(vx_armature.name))
        return {'CANCELLED'}, state
    if state == ORIENTATION_BP:
        return restoreDazRolls(vx_armature), ORIENTATION_DAZ
    return applyBlenderPerfectRolls(vx_armature), ORIENTATION_BP


def reorientArmatureFromDifeomorphicToManny(vx_armature=None):
    """
    SUPERSEDED by applyBlenderPerfectRolls above - kept for the research notes.

    Porting DazToUnreal's re-orientation pass turned out to be unnecessary. It
    solves a problem this pipeline does not have: DazToUnreal has to fix bone
    DIRECTIONS, because it inherits whatever Daz hands it. Here the builder
    already places every head and tail, so direction is correct and roll is the
    only remaining degree of freedom - which makes a per-bone roll table a
    complete orientation fix.

    What the DazToUnreal pass did, for reference. It is the second half of
    ConvertToEpicSkeleton: the
    re-orientation pass at DazToUnrealBlueprintUtils.cpp:369-527. It changes bone
    ORIENTATION only; alignArmatureFromDifeomorphicToManny above already handles
    naming, hierarchy and position.

    For G3F it touches 53 bones via three primitives:

      SetBoneOrientation(bone, quat)       - REPLACES the local rotation
      AdditiveBoneOrientation(bone, quat)  - POST-MULTIPLIES onto it
      AlignBone(parent, child, axis)       - rotates parent so its local +X
                                             points at child; angle computed
                                             from the mesh, not a constant

    Only 7 bones get a non-trivial absolute rotation - pelvis (90,-90,-90),
    clavicle.L (-87,-180,180), clavicle.R (-87,0,180), thigh.R (0,-180,0),
    ball.L/ball.R (0,90,0). Everything else is zeroed and then aligned.

    Three things to be careful about when this gets written:
      * The whole right hand (hand.R + its 16 index/middle/ring/pinky bones)
        receives NO rotation at all in DazToUnreal, while the left hand gets a
        -180 roll. That asymmetry is real in the plugin - verify it is correct
        against an actual export before reproducing it.
      * DazToUnreal's AlignBone uses atan (not atan2) and has no guard for a zero
        X component, which is why lowerarm->hand is applied twice per side. In
        Blender the same intent is just `tail = child.head`, which sidesteps it.
      * Rotation values are in Unreal convention: FRotator(Pitch, Yaw, Roll) =
        (Y, Z, X) degrees, left-handed, Z-up, 1uu = 1cm. They are NOT
        pre-converted to Blender's right-handed system.

    Full per-bone op list, in order, with source line numbers:
        D:\\code\\DazToUnreal\\blender_reference\\g3f_bone_transforms.json
        D:\\code\\DazToUnreal\\blender_reference\\G3F_bone_transforms.md
    """
    print("reorientArmatureFromDifeomorphicToManny: superseded by "
          "applyBlenderPerfectRolls")
    return {'CANCELLED'}


def alignArmatureToDifeomorphicNew():
    bones_dict = {}
    activeObject = bpy.context.scene.objects.active
    if (activeObject.type == 'ARMATURE'):
        pass
    else:
        print ("Difeomorphic Armature must be selected")
        ShowMessageBox("Difeomorphic Armature must be selected", "Warning", 'INFO')
        return {'FINISHED'}
    if activeObject.get("DazRig") is not None and activeObject["DazRig"] == "genesis3" :
        pass
    else:
        print ("Difeomorphic Armature must be selected")
        ShowMessageBox("Difeomorphic Armature must be selected", "Warning", 'INFO')
        return {'FINISHED'}
    bpy.ops.object.mode_set(mode='EDIT')
    cachedBonesData =cacheEditBonesData(activeObject)
    bpy.ops.armature.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')    
    #
    bpy.ops.object.select_all(action='DESELECT')
    bpy.data.objects["Armature"].select = True
    bpy.context.scene.objects.active = bpy.data.objects["Armature"]
    bpy.data.objects["Armature"].hide=False
    vx_armature = bpy.data.objects["Armature"]
    #bpy.ops.object.editmode_toggle()
    bpy.ops.object.mode_set(mode='EDIT')
    #
    ebones = vx_armature.data.edit_bones
    #
    for index, row in enumerate(dict_bones.spine_bones_matching):
        print("{} - {} - {}".format(row[0],row[1],row[2]))
        #align_bones(difeomorphic_armature, row[0],row[1], vx_armature, row[2])
        #row[0] - difeomorphic bone name used for head 
        #row[1] - difeomorphic bone name used for tail
        #row[2] - vxmod bone name that must be set 
        difeomorphic_eb_head_world = cachedBonesData[row[0]]["head"]
        difeomorphic_eb_tail_world = cachedBonesData[row[1]]["tail"]        
        #fast_align_bones(row[0], row[1], vx_armature, row[2])
    #
    fast_align_bones(cachedBonesData["pelvis"]["head"], cachedBonesData["pelvis"]["tail"], vx_armature, "pelvis")
    #
    ebones["pelvis"].tail.x =  ebones["pelvis"].head.x
    ebones["pelvis"].tail.y =  ebones["pelvis"].head.y
    ebones["pelvis"].tail.z =  ebones["pelvis"].head.z + 0.02
    #
    #
    fast_align_bones(cachedBonesData["pelvis"]["head"], (cachedBonesData["pelvis"]["head"]+cachedBonesData["pelvis"]["tail"])/2, vx_armature, "pelvis")
    fast_align_bones(cachedBonesData["abdomenLower"]["head"], cachedBonesData["abdomenLower"]["tail"], vx_armature, "spine_01")
    fast_align_bones(cachedBonesData["abdomenLower"]["tail"], cachedBonesData["chestLower"]["head"], vx_armature, "spine_02")
    fast_align_bones(cachedBonesData["chestLower"]["head"], (cachedBonesData["chestLower"]["tail"]+cachedBonesData["chestUpper"]["head"])/2, vx_armature, "spine_03")
    fast_align_bones((cachedBonesData["chestLower"]["tail"]+cachedBonesData["chestUpper"]["head"])/2, cachedBonesData["chestUpper"]["tail"], vx_armature, "spine_04")
    fast_align_bones(cachedBonesData["chestUpper"]["tail"], cachedBonesData["neckLower"]["head"], vx_armature, "spine_05")
    average_spine_y = (ebones["spine_01"].head.y + ebones["spine_04"].tail.y)/2
    #ebones["spine_02"].head.y =  ebones["spine_01"].tail.y
    #ebones["spine_02"].tail.y =  average_spine_y
    #ebones["spine_03"].head.y =  average_spine_y
    #ebones["spine_03"].tail.y =  average_spine_y
    #ebones["spine_04"].head.y =  average_spine_y
    #
    #the pelvis bone should be straight up maybe?!?
    #ebones["pelvis"].tail.y =  ebones["pelvis"].head.y 
    #
    #["pelvis", "pelvis", "pelvis"],         #!!!!!!!!!!!!!!!! not going to set the root yet, as it could be hardcoded in many other places
    #["abdomenLower", "abdomenLower", "spine_joint01",90],
    #
    #["abdomenUpper", "abdomenUpper", "spine_joint02",90],
    #["chestLower", "chestLower", "spine_joint03",90], ####so and so , maybe I need a mix with joint_03
    #["chestUpper", "chestUpper", "spine_joint04",90],
    #
    #["neckLower", "neckLower", "neck_joint01",90],
    #["neckUpper", "neckUpper", "neck_end",90],
    #["head", "head", "head_joint01",90],
    #["head", "head", "head_joint02",90]
    #
    #
    # lets do the legs
    fast_align_bones(cachedBonesData["lThighBend"]["head"],cachedBonesData["lShin"]["head"] , vx_armature, "thigh.L",radians(0) ) # cachedBonesData["lThighBend"]["roll"])
    fast_align_bones(cachedBonesData["lThighTwist"]["head"],cachedBonesData["lShin"]["head"] , vx_armature, "thigh_twist_01.L", radians(0) ) #cachedBonesData["lThighTwist"]["roll"])
    fast_align_bones(cachedBonesData["lThighTwist"]["head"],cachedBonesData["lShin"]["head"] , vx_armature, "thigh_twist_02.L", radians(0) )
    fast_align_bones(cachedBonesData["lShin"]["head"],cachedBonesData["lFoot"]["head"] , vx_armature, "calf.L", radians(0) ) #cachedBonesData["lShin"]["roll"])
    fast_align_bones(cachedBonesData["lFoot"]["head"],cachedBonesData["lToe"]["head"] , vx_armature, "foot.L", radians(0) ) #cachedBonesData["lFoot"]["roll"])
    fast_align_bones(cachedBonesData["lToe"]["head"],cachedBonesData["lToe"]["tail"] , vx_armature, "ball.L", radians(0) ) #cachedBonesData["lToe"]["roll"])
    #
    fast_align_bones(cachedBonesData["rThighBend"]["head"],cachedBonesData["rShin"]["head"] , vx_armature, "thigh.R", radians(0) ) #cachedBonesData["rThighBend"]["roll"])
    fast_align_bones(cachedBonesData["rThighTwist"]["head"],cachedBonesData["rShin"]["head"] , vx_armature, "thigh_twist_01.R", radians(0) ) #cachedBonesData["rThighTwist"]["roll"])
    fast_align_bones(cachedBonesData["rThighTwist"]["head"],cachedBonesData["rShin"]["head"] , vx_armature, "thigh_twist_02.R", radians(0) )
    fast_align_bones(cachedBonesData["rShin"]["head"],cachedBonesData["rFoot"]["head"] , vx_armature, "calf.R", radians(0) ) #cachedBonesData["rShin"]["roll"])
    fast_align_bones(cachedBonesData["rFoot"]["head"],cachedBonesData["rToe"]["head"] , vx_armature, "foot.R", radians(0) ) #cachedBonesData["rFoot"]["roll"])
    fast_align_bones(cachedBonesData["rToe"]["head"],cachedBonesData["rToe"]["tail"] , vx_armature, "ball.R", radians(0) ) #cachedBonesData["rToe"]["roll"])
    #makeBonesCollinearFromBoneHeadToBoneTail ????
    '''
    for index, row in enumerate(leg_bones_matching):
        print("{} - {} - {}".format(row[0],row[1],row[2]))
        #row[0] - difeomorphic bone name used for head 
        #row[1] - difeomorphic bone name used for tail
        #row[2] - vxmod bone name that must be set 
        difeomorphic_eb_head_world = cachedBonesData[row[0]]["head"]
        difeomorphic_eb_tail_world = cachedBonesData[row[1]]["tail"]        
        fast_align_bones(difeomorphic_eb_head_world, difeomorphic_eb_tail_world, vx_armature, row[2])
    #
    '''
    '''
    for index, row in enumerate(hand_bones_matching):
        print("{} - {} - {}".format(row[0],row[1],row[2]))
        #row[0] - difeomorphic bone name used for head 
        #row[1] - difeomorphic bone name used for tail
        #row[2] - vxmod bone name that must be set 
        difeomorphic_eb_head_world = cachedBonesData[row[0]]["head"]
        difeomorphic_eb_tail_world = cachedBonesData[row[1]]["tail"] 
        difeomorphic_eb_roll = cachedBonesData[row[0]]["roll"]      
        fast_align_bones(difeomorphic_eb_head_world, difeomorphic_eb_tail_world, vx_armature, row[2],difeomorphic_eb_roll)
    #
    '''
    # lets do the arms
    fast_align_bones(cachedBonesData["lCollar"]["head"],cachedBonesData["lCollar"]["tail"] , vx_armature, "clavicle.L",radians(0) ) # cachedBonesData["lCollar"]["roll"])
    fast_align_bones(cachedBonesData["lShldrBend"]["head"],cachedBonesData["lForearmBend"]["head"] , vx_armature, "upperarm.L", radians(90)) # cachedBonesData["lShldrBend"]["roll"])
    fast_align_bones(cachedBonesData["lShldrTwist"]["head"],cachedBonesData["lForearmBend"]["head"] , vx_armature, "upperarm_twist_01.L", radians(90)) #cachedBonesData["lShldrTwist"]["roll"])
    fast_align_bones(cachedBonesData["lShldrTwist"]["head"],cachedBonesData["lForearmBend"]["head"] , vx_armature, "upperarm_twist_02.L", radians(90))
    fast_align_bones(cachedBonesData["lForearmBend"]["head"],cachedBonesData["lHand"]["head"] , vx_armature, "lowerarm.L", radians(90)) #cachedBonesData["lForearmBend"]["roll"])
    fast_align_bones(cachedBonesData["lForearmTwist"]["head"],cachedBonesData["lHand"]["head"] , vx_armature, "lowerarm_twist_01.L", radians(90)) #cachedBonesData["lForearmTwist"]["roll"])
    fast_align_bones(cachedBonesData["lForearmTwist"]["head"],cachedBonesData["lHand"]["head"] , vx_armature, "lowerarm_twist_02.L", radians(90))
    fast_align_bones(cachedBonesData["lHand"]["head"],cachedBonesData["lHand"]["tail"] , vx_armature, "hand.L", cachedBonesData["lHand"]["roll"])
    #
    fast_align_bones(cachedBonesData["rCollar"]["head"],cachedBonesData["rCollar"]["tail"] , vx_armature, "clavicle.R", radians(0) ) #cachedBonesData["rCollar"]["roll"])
    fast_align_bones(cachedBonesData["rShldrBend"]["head"],cachedBonesData["rForearmBend"]["head"] , vx_armature, "upperarm.R", radians(-90)) #cachedBonesData["rShldrBend"]["roll"])
    fast_align_bones(cachedBonesData["rShldrTwist"]["head"],cachedBonesData["rForearmBend"]["head"] , vx_armature, "upperarm_twist_01.R", radians(-90)) #cachedBonesData["rShldrTwist"]["roll"])
    fast_align_bones(cachedBonesData["rShldrTwist"]["head"],cachedBonesData["rForearmBend"]["head"] , vx_armature, "upperarm_twist_02.R", radians(-90))
    fast_align_bones(cachedBonesData["rForearmBend"]["head"],cachedBonesData["rHand"]["head"] , vx_armature, "lowerarm.R", radians(-90)) #cachedBonesData["rForearmBend"]["roll"])
    fast_align_bones(cachedBonesData["rForearmTwist"]["head"],cachedBonesData["rHand"]["head"] , vx_armature, "lowerarm_twist_01.R",  radians(-90)) #cachedBonesData["rForearmTwist"]["roll"])
    fast_align_bones(cachedBonesData["rForearmTwist"]["head"],cachedBonesData["rHand"]["head"] , vx_armature, "lowerarm_twist_02.R",  radians(-90))
    fast_align_bones(cachedBonesData["rHand"]["head"],cachedBonesData["rHand"]["tail"] , vx_armature, "hand.R", cachedBonesData["rHand"]["roll"])
    #
    for index, row in enumerate(dict_bones.finger_bones_matching):
        print("{} - {} - {}".format(row[0],row[1],row[2]))
        #row[0] - difeomorphic bone name used for head 
        #row[1] - difeomorphic bone name used for tail
        #row[2] - vxmod bone name that must be set 
        difeomorphic_eb_head_world = cachedBonesData[row[0]]["head"]
        difeomorphic_eb_tail_world = cachedBonesData[row[1]]["tail"] 
        difeomorphic_eb_roll = cachedBonesData[row[0]]["roll"]      
        fast_align_bones(difeomorphic_eb_head_world, difeomorphic_eb_tail_world, vx_armature, row[2],difeomorphic_eb_roll)
    #
    for index, row in enumerate(dict_bones.toe_bones_matching):
        print("{} - {} - {}".format(row[0],row[1],row[2]))
        #row[0] - difeomorphic bone name used for head 
        #row[1] - difeomorphic bone name used for tail
        #row[2] - vxmod bone name that must be set 
        difeomorphic_eb_head_world = cachedBonesData[row[0]]["head"]
        difeomorphic_eb_tail_world = cachedBonesData[row[1]]["tail"]        
        fast_align_bones(difeomorphic_eb_head_world, difeomorphic_eb_tail_world, vx_armature, row[2])    
    #
    #lets do the breasts
    fast_align_bones(cachedBonesData["lPectoral"]["head"], cachedBonesData["lPectoral"]["tail"], vx_armature, "breast_joint.L")
    fast_align_bones(cachedBonesData["rPectoral"]["head"], cachedBonesData["rPectoral"]["tail"], vx_armature, "breast_joint.R")                     
    #


def alignArmatureToDifeomorphic():
    bones_dict = {}
    activeObject = bpy.context.scene.objects.active
    if (activeObject.type == 'ARMATURE'):
        pass
    else:
        print ("Difeomorphic Armature must be selected")
        ShowMessageBox("Difeomorphic Armature must be selected", "Warning", 'INFO')
        return {'FINISHED'}
    #if ("Genesis 3 Female" in activeObject.name):
    #        children = getChildren(activeObject) 
    #        extractSpecificBonesFromG3FArmatureFastVersion(activeObject.name, bones_dict)
    #        setupSpecificBonesFromG3FArmature(activeObject.name, "Armature")
    if ("Genesis 3 Female" in activeObject.name):
            #
            # using the difeomorphic armature we extract bone's data as head, tail, roll, and we also append the roll override values to the dict items
            # this gets the data only from the original armature difeomorphic bones 
            extractSpecificBonesFromG3FArmatureFastVersion(activeObject.name, bones_dict)
            #
            #
            #setupSpecificBonesFromG3FArmature(activeObject.name, "Armature")
            children = getChildren(activeObject) #should return main body mesh + geograft children
            for c in children: 
                #print (c.name)
                 if ("Genesis 3 Female Mesh" in c.name):
                    print("bla")
                    getArmatureBonesDictFromBreastVertices(bones_dict)
                    getArmatureBonesDictFromOtherVertices(bones_dict) # other = stomach, rib, butt joints
                    getArmatureBonesDictFromHeadVertices(bones_dict)
                    getArmatureBonesDictFromGensVertices(bones_dict)
                    #setupSpecificBonesRollFromG3FBodyMesh()
                #if ("Genesis 3 Female Genitalia" in c.name):
                #    setupBonesFromGenitalGeoGraftMesh()
                #print (bones_dict)
    #
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects["Armature"].select = True
    bpy.context.scene.objects.active = bpy.data.objects["Armature"]
    bpy.ops.object.editmode_toggle()

    armature_data = bpy.data.objects['Armature']
    # amw is armature matrix world, amwi is the inverse
    amw = armature_data.matrix_world
    amwi = amw.inverted()
    ebones = armature_data.data.edit_bones
    for key,value in bones_dict.items():
        #print(key)
        #print(value)
        try:
            ebones[key].head = amwi * value['head']
            ebones[key].tail = amwi * value['tail']
            ebones[key].roll = radians(value['rollOverride']) if value['rollOverride'] else radians(0)
        except KeyError as e:
            print("KeyError occurred. missing bone named: {}".format(key))
    #
    bpy.ops.object.mode_set(mode='OBJECT')



def fixBreastJointEndsDifeomorphic(target_armature):
    print ("fixBreastJointEndsDifeomorphic")
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects[target_armature].select = True
    bpy.context.scene.objects.active = bpy.data.objects[target_armature]
    ob = bpy.data.objects[target_armature]
    bpy.ops.object.editmode_toggle()
    armature_data = bpy.data.objects[target_armature]
    ebones = armature_data.data.edit_bones
    nipple_joint01_R = ebones["breastNipple.R"]
    nipple_end_R = ebones["breastNipple_end.R"]
    matrix = breast_scale_joint_R.matrix.copy()
    nipple_joint01_R_head = nipple_joint01_R.head.copy()
    nipple_joint01_R_tail = nipple_joint01_R.tail.copy()
    nipple_end_R_head = nipple_end_R.head.copy()
    nipple_end_R_tail = nipple_end_R.tail.copy()
    #
    nipple_joint01_R.matrix = matrix
    nipple_joint01_R.head = nipple_joint01_R_head
    nipple_joint01_R.tail = nipple_joint01_R_tail
    nipple_end_R.matrix = nipple_joint01_R.matrix.copy()
    nipple_end_R.head = nipple_joint01_R.tail
    nipple_end_R.tail = nipple_joint01_R.head
    nipple_end_R.length *= -1
    #
    breast_deform02_joint01_R = ebones["breast_deform02_joint01.R"]
    breast_deform02_end_R = ebones["breast_deform02_end.R"]
    matrix = breast_deform02_joint01_R.matrix.copy()
    breast_deform02_end_R_head = breast_deform02_joint01_R.tail.copy()
    breast_deform02_end_R_tail = breast_deform02_end_R.tail.copy()
    length = breast_deform02_joint01_R.length
    breast_deform02_joint01_R.length *= 1.05 
    breast_deform02_end_R.matrix = matrix
    breast_deform02_end_R.head = breast_deform02_end_R_head
    breast_deform02_end_R.tail = breast_deform02_joint01_R.tail.copy()
    breast_deform02_joint01_R.length = length
    #
    breast_deform03_joint01_R = ebones["breast_deform03_joint01.R"]
    breast_deform03_end_R = ebones["breast_deform03_end.R"]
    matrix = breast_deform03_joint01_R.matrix.copy()
    breast_deform03_end_R_head = breast_deform03_joint01_R.tail.copy()
    breast_deform03_end_R_tail = breast_deform03_end_R.tail.copy()
    length = breast_deform03_joint01_R.length
    breast_deform03_joint01_R.length *= 1.05 
    breast_deform03_end_R.matrix = matrix
    breast_deform03_end_R.head = breast_deform03_end_R_head
    breast_deform03_end_R.tail = breast_deform03_joint01_R.tail.copy()
    breast_deform03_joint01_R.length = length
    #
    breast_deform03_joint01_R = ebones["breast_deform03_joint01.R"]
    breast_deform03_end_R = ebones["breast_deform03_end.R"]
    matrix = breast_deform03_joint01_R.matrix.copy()
    breast_deform03_end_R_head = breast_deform03_joint01_R.tail.copy()
    breast_deform03_end_R_tail = breast_deform03_end_R.tail.copy()
    length = breast_deform03_joint01_R.length
    breast_deform03_joint01_R.length *= 1.05 
    breast_deform03_end_R.matrix = matrix
    breast_deform03_end_R.head = breast_deform03_end_R_head
    breast_deform03_end_R.tail = breast_deform03_joint01_R.tail.copy()
    breast_deform03_joint01_R.length = length
    #
    breast_deform01_joint01_R = ebones["breast_deform01_joint01.R"]
    breast_deform01_end_R = ebones["breast_deform01_end.R"]
    matrix = breast_deform01_joint01_R.matrix.copy()
    breast_deform01_end_R_head = breast_deform01_joint01_R.tail.copy()
    breast_deform01_end_R_tail = breast_deform01_end_R.tail.copy()
    length = breast_deform01_joint01_R.length
    breast_deform01_joint01_R.length *= 1.05 
    breast_deform01_end_R.matrix = matrix
    breast_deform01_end_R.head = breast_deform01_end_R_head
    breast_deform01_end_R.tail = breast_deform01_joint01_R.tail.copy()
    breast_deform01_joint01_R.length = length
    breast_scale_joint_L = ebones["breast_scale_joint.L"]
    nipple_joint01_L = ebones["nipple_joint01.L"]
    nipple_end_L = ebones["nipple_end.L"]
    matrix = breast_scale_joint_L.matrix.copy()
    nipple_joint01_L_head = nipple_joint01_L.head.copy()
    nipple_joint01_L_tail = nipple_joint01_L.tail.copy()
    nipple_end_L_head = nipple_end_L.head.copy()
    nipple_end_L_tail = nipple_end_L.tail.copy()
    nipple_joint01_L.matrix = matrix
    nipple_joint01_L.head = nipple_joint01_L_head
    nipple_joint01_L.tail = nipple_joint01_L_tail
    nipple_end_L.matrix = nipple_joint01_L.matrix.copy()
    nipple_end_L.head = nipple_joint01_L.tail
    nipple_end_L.tail = nipple_joint01_L.head
    nipple_end_L.length *= -1
    #
    breast_deform02_joint01_L = ebones["breast_deform02_joint01.L"]
    breast_deform02_end_L = ebones["breast_deform02_end.L"]
    matrix = breast_deform02_joint01_L.matrix.copy()
    breast_deform02_end_L_head = breast_deform02_joint01_L.tail.copy()
    breast_deform02_end_L_tail = breast_deform02_end_L.tail.copy()
    length = breast_deform02_joint01_L.length
    breast_deform02_joint01_L.length *= 1.05 
    breast_deform02_end_L.matrix = matrix
    breast_deform02_end_L.head = breast_deform02_end_L_head
    breast_deform02_end_L.tail = breast_deform02_joint01_L.tail.copy()
    breast_deform02_joint01_L.length = length
    #
    breast_deform03_joint01_L = ebones["breast_deform03_joint01.L"]
    breast_deform03_end_L = ebones["breast_deform03_end.L"]
    matrix = breast_deform03_joint01_L.matrix.copy()
    breast_deform03_end_L_head = breast_deform03_joint01_L.tail.copy()
    breast_deform03_end_L_tail = breast_deform03_end_L.tail.copy()
    length = breast_deform03_joint01_L.length
    breast_deform03_joint01_L.length *= 1.05 
    breast_deform03_end_L.matrix = matrix
    breast_deform03_end_L.head = breast_deform03_end_L_head
    breast_deform03_end_L.tail = breast_deform03_joint01_L.tail.copy()
    breast_deform03_joint01_L.length = length
    #
    breast_deform03_joint01_L = ebones["breast_deform03_joint01.L"]
    breast_deform03_end_L = ebones["breast_deform03_end.L"]
    matrix = breast_deform03_joint01_L.matrix.copy()
    breast_deform03_end_L_head = breast_deform03_joint01_L.tail.copy()
    breast_deform03_end_L_tail = breast_deform03_end_L.tail.copy()
    length = breast_deform03_joint01_L.length
    breast_deform03_joint01_L.length *= 1.05 
    breast_deform03_end_L.matrix = matrix
    breast_deform03_end_L.head = breast_deform03_end_L_head
    breast_deform03_end_L.tail = breast_deform03_joint01_L.tail.copy()
    breast_deform03_joint01_L.length = length
    #
    breast_deform01_joint01_L = ebones["breast_deform01_joint01.L"]
    breast_deform01_end_L = ebones["breast_deform01_end.L"]
    matrix = breast_deform01_joint01_L.matrix.copy()
    breast_deform01_end_L_head = breast_deform01_joint01_L.tail.copy()
    breast_deform01_end_L_tail = breast_deform01_end_L.tail.copy()
    length = breast_deform01_joint01_L.length
    breast_deform01_joint01_L.length *= 1.05 
    breast_deform01_end_L.matrix = matrix
    breast_deform01_end_L.head = breast_deform01_end_L_head
    breast_deform01_end_L.tail = breast_deform01_joint01_L.tail.copy()
    breast_deform01_joint01_L.length = length


def fixHeadJointsDifeomorphic(target_armature):
    print ("fixHeadJointsDifeomorphic")
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects[target_armature].select = True
    bpy.context.scene.objects.active = bpy.data.objects[target_armature]
    ob = bpy.data.objects[target_armature]
    bpy.ops.object.editmode_toggle()
    armature_data = bpy.data.objects[target_armature]
    ebones = armature_data.data.edit_bones
    #
    ebones["head"].tail.y = ebones["head"].head.y


def fixSpineJointsDifeomorphic(target_armature):
    print ("fixSpineJointsDifeomorphic")
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects[target_armature].select = True
    bpy.context.scene.objects.active = bpy.data.objects[target_armature]
    ob = bpy.data.objects[target_armature]
    bpy.ops.object.editmode_toggle()
    armature_data = bpy.data.objects[target_armature]
    ebones = armature_data.data.edit_bones
    #
    ebones["spine_05"].tail = ebones["neck_01"].head
    boneArray = ["spine_01","spine_02","spine_03","spine_04","spine_05"]
    makeBonesCollinearFromBoneHeadToBoneTail("Armature", boneArray)


def fixFingersJointEndsDifeomorphic(target_armature):
    print ("fixFingersJointEndsDifeomorphic")
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects[target_armature].select = True
    bpy.context.scene.objects.active = bpy.data.objects[target_armature]
    ob = bpy.data.objects[target_armature]
    bpy.ops.object.editmode_toggle()
    armature_data = bpy.data.objects[target_armature]
    ebones = armature_data.data.edit_bones
    for index, row in enumerate(dict_bones.finger_jointend_bones_parents):
        ebones[row[0]].head = ebones[row[1]].tail
        ebones[row[0]].tail = ebones[row[0]].head + Vector ((0,0,0.005))
        print(row[0])


def fixToesJointEndsDifeomorphic(target_armature):
    print ("fixToesJointEndsDifeomorphic")
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects[target_armature].select = True
    bpy.context.scene.objects.active = bpy.data.objects[target_armature]
    ob = bpy.data.objects[target_armature]
    bpy.ops.object.editmode_toggle()
    armature_data = bpy.data.objects[target_armature]
    ebones = armature_data.data.edit_bones
    for index, row in enumerate(dict_bones.toe_jointend_bones_parents):
        ebones[row[0]].head = ebones[row[1]].tail
        ebones[row[0]].tail = ebones[row[0]].head + Vector ((0.01,0,0))
        print(row[0])



def extractSpecificBonesFromG3FArmatureFastVersion(difeomorphic_armature, bones_dict):
    """
    This function walks through dict_bones.leg_bones_matching and others ... and builds the bones_dict (head, tail, roll, rollOverride)

    Returns:
    type: Description of the return value.
    """    
    print("extractSpecificBonesFromG3FArmatureFastVersion()...")
    #
    bpy.ops.object.mode_set(mode='OBJECT')
    #
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects[difeomorphic_armature].select = True
    bpy.context.scene.objects.active = bpy.data.objects[difeomorphic_armature]
    ob = bpy.data.objects[difeomorphic_armature]
    bpy.ops.object.editmode_toggle()
    #
    difeomorphic_armature_data = bpy.data.objects[difeomorphic_armature]
    #
    difeomorphic_ebones = difeomorphic_armature_data.data.edit_bones
    # amw is armature matrix world, amwi is the inverse
    difeomorphic_amw = difeomorphic_armature_data.matrix_world
    difeomorphic_amwi = difeomorphic_amw.inverted()
    #
    #last value in the array (for leg_bones_matching, arm_bones_matching, spine_bones_matching, etc.) is the roll override
    bones_matching = (
        dict_bones.leg_bones_matching + 
        dict_bones.arm_bones_matching + 
        dict_bones.spine_bones_matching + 
        dict_bones.finger_bones_matching + 
        dict_bones.toe_bones_matching
    )
    #
    for index, row in enumerate(bones_matching):
        if (row[0] == row[1]):
            eb = difeomorphic_ebones[row[0]]
            difeomorphic_eb_matrix_world = difeomorphic_amw * eb.matrix
            #eb.matrix = difeomorphic_eb_matrix_world
            difeomorphic_eb_head_world = eb.head + difeomorphic_armature_data.location 
            difeomorphic_eb_tail_world =  eb.tail + difeomorphic_armature_data.location    
        else:
            # first head
            eb = difeomorphic_ebones[row[0]]
            difeomorphic_eb_head_world =  eb.head + difeomorphic_armature_data.location      
            # then tail
            eb = difeomorphic_ebones[row[1]]
            difeomorphic_eb_tail_world =  eb.tail + difeomorphic_armature_data.location             
        #
        bones_dict[row[2]]= {"head":difeomorphic_eb_head_world, "tail":difeomorphic_eb_tail_world, "roll":0, "rollOverride":0, "connected":False }
    #
    # lets get the roll if defined
    for index, row in enumerate(bones_matching):
        eb = difeomorphic_ebones[row[0]]
        bones_dict[row[2]]['roll']= math.degrees(eb.roll)
        rollOverride  = row[3] if 3 < len(row) else 0          # check if it exists defined, otherwise is 0
        #print("RollOverride for bone {0} is {1}".format(row[2],rollOverride))
        bones_dict[row[2]]['rollOverride']= rollOverride
    #    
    bpy.ops.object.mode_set(mode='OBJECT')
    return bones_dict

def extractSpecificBonesFromG3FBodyMesh(difeomorphic_body, bones_dict):
    print("setupSpecificBonesFromG3FGensGeograftMesh()...")
    #
    bpy.ops.object.mode_set(mode='OBJECT')
    #
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects[difeomorphic_body].select = True
    bpy.context.scene.objects.active = bpy.data.objects[difeomorphic_body]
    ob = bpy.data.objects[difeomorphic_body]
    vagina_center = getCenterFromVertices (vagina_center, obj )

    #
    #bones_dict[]= {"head":difeomorphic_eb_head_world, "tail":difeomorphic_eb_tail_world, "roll":0, "rollOverride":0, "connected":False }
    return bones_dict

def extractSpecificBonesFromG3FGensGeograftMesh(difeomorphic_gens, bones_dict):
    print("setupSpecificBonesFromG3FGensGeograftMesh()...")
    #
    bpy.ops.object.mode_set(mode='OBJECT')
    #
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects[difeomorphic_gens].select = True
    bpy.context.scene.objects.active = bpy.data.objects[difeomorphic_gens]
    ob = bpy.data.objects[difeomorphic_gens]
    bpy.ops.object.editmode_toggle()
    #
    #bones_dict[]= {"head":difeomorphic_eb_head_world, "tail":difeomorphic_eb_tail_world, "roll":0, "rollOverride":0, "connected":False }
    return bones_dict


def findGensMesh():
    meshes = [ob for ob in bpy.data.objects if (ob.type == 'MESH' and 'Genesis 3 Female Genitalia' in ob.name )]
    if len(meshes)>0:
        return meshes[0]
    return None

# setupSpecificBonesFromG3FArmature is no longer used?!?!
def setupSpecificBonesFromG3FArmature(difeomorphic_armature, vx_armature ):
    print("setupSpecificBonesFromG3FArmature()...")
    for index, row in enumerate(dict_bones.leg_bones_matching):
        align_bones(difeomorphic_armature,row[0],row[1], vx_armature, row[2])
        print(row[2])
    for index, row in enumerate(dict_bones.arm_bones_matching):
        align_bones(difeomorphic_armature, row[0],row[1], vx_armature, row[2])
        print(row[2])
    for index, row in enumerate(dict_bones.spine_bones_matching):
        align_bones(difeomorphic_armature, row[0],row[1], vx_armature, row[2])
        print(row[2])
    for index, row in enumerate(dict_bones.finger_bones_matching):
        align_bones(difeomorphic_armature, row[0],row[1], vx_armature, row[2])
        print(row[2])  
    for index, row in enumerate(dict_bones.toe_bones_matching):
        align_bones(difeomorphic_armature, row[0],row[1], vx_armature, row[2])
        print(row[2])                  

def setupSpecificBonesRollFromG3FBodyMesh():
    print("setupSpecificBonesRollFromG3FBodyMesh()...")

def setupBonesFromGenitalGeoGraftMesh():
    print("setupBonesFromGenitalGeoGraftMesh()...")



def getChildren(myObject): 
    children = [] 
    for ob in bpy.data.objects: 
        if ob.parent == myObject: 
            children.append(ob) 
    return children 
 
 

#cacheEditBonesData(bpy.data.objects["Genesis 3 Female"])
def cacheEditBonesData(armature):
    ebones = armature.data.edit_bones
    amw = armature.matrix_world
    amwi = amw.inverted()
    ebDict={}
    for eb in ebones:
        eb_matrix_world = amw * eb.matrix
        eb_head_world = eb.head + armature.location
        eb_tail_world = eb.tail + armature.location
        eb_roll = eb.roll
        eb_parent= eb.parent
        ebDict[eb.name]= {}
        ebDict[eb.name]["head"] = eb_head_world
        ebDict[eb.name]["tail"] = eb_tail_world
        ebDict[eb.name]["roll"] = eb_roll
        ebDict[eb.name]["parent"] = eb_parent.name if eb_parent else None
    return ebDict


def fast_align_bones(head, tail, vx_armature, vx_bone, roll = None):
    #
    ebones = vx_armature.data.edit_bones
    #
    amw = vx_armature.matrix_world
    amwi = amw.inverted()
    #
    eb = ebones[vx_bone]
    eb.head = amwi * head
    eb.tail = amwi * tail
    if roll != None:
        eb.roll = roll


def align_bones(difeomorphic_armature, difeomorphic_bone_for_head, difeomorphic_bone_for_tail, vx_armature, vx_bone):
    bpy.ops.object.mode_set(mode='OBJECT')
    #
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects[difeomorphic_armature].select = True
    bpy.context.scene.objects.active = bpy.data.objects[difeomorphic_armature]
    ob = bpy.data.objects[difeomorphic_armature]
    bpy.ops.object.editmode_toggle()
    #
    difeomorphic_armature_data = bpy.data.objects[difeomorphic_armature]
    #
    difeomorphic_ebones = difeomorphic_armature_data.data.edit_bones
    # amw is armature matrix world, amwi is the inverse
    difeomorphic_amw = difeomorphic_armature_data.matrix_world
    difeomorphic_amwi = difeomorphic_amw.inverted()
    #
    eb = difeomorphic_ebones[difeomorphic_bone_for_head]
    difeomorphic_eb_matrix_world = difeomorphic_amw * eb.matrix
    difeomorphic_eb_head_world = eb.head + difeomorphic_armature_data.location
    #
    eb = difeomorphic_ebones[difeomorphic_bone_for_tail]
    difeomorphic_eb_matrix_world = difeomorphic_amw * eb.matrix
    difeomorphic_eb_tail_world = eb.tail + difeomorphic_armature_data.location
    #
    #
    #
    bpy.ops.object.editmode_toggle()
    #
    #
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects[vx_armature].select = True
    bpy.context.scene.objects.active = bpy.data.objects[vx_armature]
    ob = bpy.data.objects[vx_armature]
    bpy.ops.object.editmode_toggle()
    #
    armature_data = bpy.data.objects[vx_armature]
    ebones = armature_data.data.edit_bones
    #
    amw = armature_data.matrix_world
    amwi = amw.inverted()
    #
    eb = ebones[vx_bone]
    #eb_matrix_world = difeomorphic_amw * difeomorphic_eb.matrix    
    #
    #eb.matrix = amwi * difeomorphic_eb_matrix_world    
    eb.head = amwi * difeomorphic_eb_head_world
    eb.tail = amwi * difeomorphic_eb_tail_world




def mainGoOverBonesAndAlignThem():
    for index, row in enumerate(dict_bones.leg_bones_matching):
        align_bones(row[0],row[1], row[2])
        print(row[2])
    for index, row in enumerate(dict_bones.hand_bones_matching):
        align_bones(row[0],row[1], row[2])
        print(row[2])
    for index, row in enumerate(dict_bones.spine_bones_matching):
        align_bones(row[0],row[1], row[2])
        print(row[2])            


#mainGoOverBonesAndAlignThem()


def getAlignVectorFromTwoVertices(source_mesh, v1, v2):
    #get align vector in world space from two vertices indexes
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    #fa is the face array indices
    obj = bpy.data.objects[source_mesh]
    vector_from_verts = obj.data.vertices[v1].co - obj.data.vertices[v2].co
    vector_from_verts.normalize()
    alignVector = obj.matrix_world * vector_from_verts
    alignVector.normalize()
    alignVector
    return alignVector


def getAlignVectorFromVertexNormals(source_mesh, va):
    #get align vector in world space from vertex array normals (vertices defined by their indices)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    #fa is the face array indices
    obj = bpy.data.objects[source_mesh]
    averageNormal = mathutils.Vector()
    for v_index in va:
        vertex = obj.data.vertices[f_index]
        # set vertex normal to average of face normals
        averageNormal += vertex.normal
    averageNormal /= len(va)
    alignVector = obj.matrix_world * averageNormal
    alignVector.normalize()
    alignVector
    return alignVector


def getAlignVectorFromFacesArray(source_mesh, fa):
    #get align vector in world space from faces normal averaged
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    #fa is the face array indices
    obj = bpy.data.objects[source_mesh]
    averageNormal = mathutils.Vector()
    for f_index in fa:
        face = obj.data.polygons[f_index]
        # set vertex normal to average of face normals
        averageNormal += face.normal
    averageNormal /= len(fa)
    alignVector = obj.matrix_world * averageNormal
    alignVector.normalize()
    alignVector
    return alignVector


def alignRollWithVector(vector, target_armature, target_bone, offset):
    #set the target_bone roll value to match the vector
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.data.objects[target_armature].select = True
    bpy.context.scene.objects.active = bpy.data.objects[target_armature]
    ob = bpy.data.objects[target_armature]
    bpy.ops.object.editmode_toggle()
    #
    #
    armature_data = bpy.data.objects[target_armature]
    ebones = armature_data.data.edit_bones
    eb = ebones[target_bone]
    #
    eb.align_roll(vector)
    eb.roll += radians(offset)


genesis3Toes = {
    "lFoot" : ["lMetatarsals"],
    "rFoot" : ["rMetatarsals"],
    "lToe" : ["lBigToe", "lSmallToe1", "lSmallToe2", "lSmallToe3", "lSmallToe4", "lBigToe_2", "lSmallToe1_2", "lSmallToe2_2", "lSmallToe3_2", "lSmallToe4_2"],
    "rToe" : ["rBigToe", "rSmallToe1", "rSmallToe2", "rSmallToe3", "rSmallToe4", "rBigToe_2", "rSmallToe1_2", "rSmallToe2_2", "rSmallToe3_2", "rSmallToe4_2"]
}

def checkIfVertexGroupExistAndRecreateIt(ob, group):
    if group in ob.vertex_groups.keys():
        vgrp = ob.vertex_groups[group]
        ob.vertex_groups.remove(vgrp)
        vgrp = ob.vertex_groups.new(name=group)
    else:
        vgrp = ob.vertex_groups.new(name=group)
    return vgrp

def renameVertexGroup(ob, oldGroupName, newGroupName):
    if oldGroupName in ob.vertex_groups.keys() and oldGroupName!=newGroupName:
        vgrp = ob.vertex_groups[oldGroupName]
        vgrp.name = newGroupName


def deleteVertexGroup(ob, group):
    if group in ob.vertex_groups.keys():
        print("Removing vertex group: {}".format(group))
        vgrp = ob.vertex_groups[group]
        ob.vertex_groups.remove(vgrp)



def mergeSubgroupsIntoGroup(ob, mergers):
    vg_dict = {}
    for group,subGroups in mergers.items():
        #
        vgrp = checkIfVertexGroupExistAndRecreateIt(ob,group)
        #
        subgrps = []
        for subGroup in subGroups:
            if subGroup in ob.vertex_groups.keys():
                subgrps.append(ob.vertex_groups[subGroup])
        idxs = [vg.index for vg in subgrps]
        idxs.append(vgrp.index)
        weights = dict([(vn,0) for vn in range(len(ob.data.vertices))])
        for v in ob.data.vertices:
            for g in v.groups:
                if g.group in idxs:
                    weights[v.index] += g.weight
        #for subgrp in subgrps:
        #    ob.vertex_groups.remove(subgrp)
        #result_string = json.dumps(weights)
        #print (result_string)
        #
        vg_dict[vgrp.name] = weights 
        #       
        for vn,w in weights.items():
            if w > 1e-3:
                #vgrp.add([vn], 0, 'REPLACE')
                vgrp.add([vn], w, 'REPLACE')
        #
        #with open("C:\\Users\\Neon\\Desktop\\dump\dump.txt", 'w') as outfile:
        #    json.dump(vg_dict, outfile, indent=4)


def getCenterFromVertices(vertex_index_list, obj):
	print (obj.name)
	vertex_list = [obj.data.vertices[i] for i in vertex_index_list]
	count = float(len(vertex_list))
	x, y, z = [ sum( [v.co[i] for v in vertex_list] ) for i in range(3)]
	center = (Vector( (x, y, z ) ) / count ) 
	return center



def check_vertices_count_of_the_body(mesh_name, number_of_vertices_the_object_should_have):
    ob = bpy.data.objects[mesh_name] #Genesis 3 Female Mesh
    me = ob.data
    return (len(me.vertices) == number_of_vertices_the_object_should_have)
    
 
#https://blender.stackexchange.com/questions/46584/how-to-align-an-object-so-one-of-its-faces-are-axis-aligned-make-an-object-upr

# obj = bpy.data.objects['Plane']
# face = obj.data.polygons[5951]
# alignVector = obj.matrix_world * face.normal
# alignVector.normalize()
# alignVector

# bpy.ops.object.select_all(action='DESELECT')
# bpy.ops.object.mode_set(mode='OBJECT')
# bpy.data.objects["Armature"].select = True
# bpy.context.scene.objects.active = bpy.data.objects["Armature"]
# ob = bpy.data.objects["Armature"]
# bpy.ops.object.editmode_toggle()


# armature_data = bpy.data.objects['Armature']
# ebones = armature_data.data.edit_bones
# eb = ebones["finger02_joint03.L"]


# eb.align_roll(alignVector)





# import bpy
# import bmesh

# obj = bpy.context.edit_object
# me = obj.data
# bm = bmesh.from_edit_mesh(me)

# for f in bm.faces:
    # if f.select:
        # print(f.index)



#knee_centerX_L=[3410, 4675]
#knee_centerX_R=[10293, 11533]

def armatureMakeFriendlyIKJoints(ob):
    assert ob is not None and ob.type == 'ARMATURE', "active object invalid"
    #Must make armature active and in edit mode to create a bone
    bpy.context.scene.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    amw = ob.matrix_world
    amwi = amw.inverted()

    armature = bpy.data.armatures[ob.name]
    
    center=dict()
    k = 1
    list_of_bones = ["thigh","calf","foot","ball","thigh_twist_01","thigh_twist_02"]


    difeomorphic_body = "Genesis 3 Female Mesh"
    if difeomorphic_body in bpy.data.objects:
        obj = bpy.data.objects[difeomorphic_body]
        center["centerX.L"]= getCenter (knee_centerX_L, obj )[0]
        center["centerX.R"]= getCenter (knee_centerX_R, obj )[0]
    else:
        center["centerX.L"]= armature.edit_bones["calf.L"].head.x
        center["centerX.R"]= armature.edit_bones["calf.R"].head.x
        #for suffix in [".L",".R"]:
        #    for bonename in list_of_bones:
        #        ebone = armature.edit_bones[bonename+suffix]

    for suffix in [".L",".R"]:
        if suffix == ".R":
            k = -1
        for bonename in list_of_bones:
            ebone = armature.edit_bones[bonename+suffix]
            ebone.head.x = center["centerX"+suffix]
            ebone.tail.x = center["centerX"+suffix]


        armature.edit_bones["thigh"+suffix].tail = armature.edit_bones["calf"+suffix].head
        armature.edit_bones["calf"+suffix].tail = armature.edit_bones["foot"+suffix].head
        armature.edit_bones["foot"+suffix].tail = armature.edit_bones["ball"+suffix].head
        #armature.edit_bones["toe_joint"+suffix].head =  armature.edit_bones["ball"+suffix].tail
        armature.edit_bones["thigh_twist_01"+suffix].tail = armature.edit_bones["calf"+suffix].head
        armature.edit_bones["thigh_twist_01"+suffix].head = (armature.edit_bones["thigh"+suffix].head+armature.edit_bones["thigh"+suffix].tail)/2
        armature.edit_bones["thigh_twist_02"+suffix].tail = armature.edit_bones["calf"+suffix].head
        armature.edit_bones["thigh_twist_02"+suffix].head = (armature.edit_bones["thigh"+suffix].head+armature.edit_bones["thigh"+suffix].tail)/2

        armature.edit_bones["thigh"+suffix].roll = radians(0)
        armature.edit_bones["calf"+suffix].roll = radians(0)
        armature.edit_bones["foot"+suffix].roll = radians(90) #kradians(180) * k
        armature.edit_bones["ball"+suffix].roll = radians(90) #radians(180) * k

        armature.edit_bones["thigh_twist_01"+suffix].roll = radians(0)
        armature.edit_bones["thigh_twist_02"+suffix].roll = radians(0)

        #armature.edit_bones["toe_joint"+suffix].length =  0.025
        #armature.edit_bones["toe_joint"+suffix].roll = radians(0) 






    center.clear()
    k = 1
    list_of_bones = ["upperarm","lowerarm","hand","upperarm_twist_01","upperarm_twist_02","lowerarm_twist_01","lowerarm_twist_02"]


    difeomorphic_body = "Genesis 3 Female Mesh"
    if difeomorphic_body in bpy.data.objects:
        obj = bpy.data.objects[difeomorphic_body]
        center["centerX.L"]= getCenter (elbow_center_L, obj )[2]
        center["centerX.R"]= getCenter (elbow_center_R, obj )[2]
    else:
        center["centerX.L"]= armature.edit_bones["lowerarm.L"].head.z
        center["centerX.R"]= armature.edit_bones["lowerarm.R"].head.z
        #for suffix in [".L",".R"]:
        #    for bonename in list_of_bones:
        #        ebone = armature.edit_bones[bonename+suffix]

    for suffix in [".L",".R"]:
        if suffix == ".R":
            k = -1
        for bonename in list_of_bones:
            ebone = armature.edit_bones[bonename+suffix]
            ebone.head.z = center["centerX"+suffix]
            ebone.tail.z = center["centerX"+suffix]
        #
        armature.edit_bones["upperarm"+suffix].tail = armature.edit_bones["lowerarm"+suffix].head
        armature.edit_bones["lowerarm"+suffix].tail = armature.edit_bones["hand"+suffix].head
        armature.edit_bones["upperarm_twist_01"+suffix].tail = armature.edit_bones["lowerarm"+suffix].head
        armature.edit_bones["upperarm_twist_01"+suffix].head = (armature.edit_bones["upperarm"+suffix].head+armature.edit_bones["upperarm"+suffix].tail)/2
        armature.edit_bones["upperarm_twist_02"+suffix].tail = armature.edit_bones["lowerarm"+suffix].head
        armature.edit_bones["upperarm_twist_02"+suffix].head = (armature.edit_bones["upperarm"+suffix].head+armature.edit_bones["upperarm"+suffix].tail)/2
        armature.edit_bones["lowerarm_twist_01"+suffix].head = (armature.edit_bones["lowerarm"+suffix].head+armature.edit_bones["lowerarm"+suffix].tail)/2
        armature.edit_bones["lowerarm_twist_02"+suffix].head = (armature.edit_bones["lowerarm"+suffix].head+armature.edit_bones["lowerarm"+suffix].tail)/2
        #
        #armature.edit_bones["upperarm"+suffix].roll = radians(90)
        #armature.edit_bones["lowerarm"+suffix].roll = radians(90)
        #
        #armature.edit_bones["upperarm_twist_01"+suffix].roll = radians(90)
        #armature.edit_bones["lowerarm_twist_01"+suffix].roll = radians(90)
    #
    startBone = "breast_joint.L"
    endBone = "breast_scale_joint.L"
    armature.edit_bones[startBone].tail = armature.edit_bones[endBone].tail
    localCo, worldCo, distance, translationAlongY = getClosestPointFromBoneProjection(ob.name,startBone, endBone)
    armature.edit_bones[endBone].head = localCo
    armature.edit_bones["breast_top_joint.L"].head = localCo
    armature.edit_bones["breast_bottom_joint.L"].head = localCo
    armature.edit_bones["breast_outer_joint.L"].head = localCo
    armature.edit_bones["breast_inner_joint.L"].head = localCo

    startBone = "breast_joint.R"
    endBone = "breast_scale_joint.R"
    armature.edit_bones[startBone].tail = armature.edit_bones[endBone].tail
    localCo, worldCo, distance, translationAlongY = getClosestPointFromBoneProjection(ob.name,startBone, endBone)
    armature.edit_bones[endBone].head = localCo
    armature.edit_bones["breast_top_joint.R"].head = localCo
    armature.edit_bones["breast_bottom_joint.R"].head = localCo
    armature.edit_bones["breast_outer_joint.R"].head = localCo
    armature.edit_bones["breast_inner_joint.R"].head = localCo
