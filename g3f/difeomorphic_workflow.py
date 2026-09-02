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
      7. Levels each foot's hinge axis to the ground, for foot-roll compatibility
         (see levelFootRollHinges). Roll only, and NOT from DazToUnreal - it is
         measured off the UE5 skeleton, which does exactly this.

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

    # ================================================================ SPINE AIM
    # DazToUnreal's spine pass, transcribed: point spine_02..spine_05 and neck_01
    # at their chain successors. Curvature is NOT touched - only the direction each
    # bone points along the curve the Daz figure already has.
    #
    # Runs after the re-positionings because spine_01's head moves up there, and
    # before the clamp because moving a tail onto the child's head already sets the
    # length the clamp would have set - so the clamp comes out a no-op on these
    # rather than fighting them.
    # ============================================================================
    aimed_spine = aimSpineBonesAtChildren(vx_armature)

    # ------------------------------------------------------- clamp bone lengths
    # Must run after the re-positionings above: they move heads without moving the
    # children, which changes the head-to-child-head distances this depends on.
    clamped = clampBoneLengthsToChildHeads(vx_armature)

    # ================================================================= FOOT HINGE
    # DazToUnreal has no equivalent of this step - it is taken from the UE5
    # skeleton itself, where the foot's local Pitch is exactly the negated tilt
    # its parents accumulated, putting the hinge axis back on the horizontal.
    # That level hinge is what makes foot roll and ball roll clean rotations.
    #
    # Runs AFTER the clamp on purpose: the foot is in bones_length_set_to_successor,
    # so the clamp is what lands its tail exactly on ball's head. Solving against
    # the bone direction before that would aim at the wrong line.
    #
    # ROLL ONLY - heads, tails and lengths are already final at this point and are
    # not touched. See levelFootRollHinges for the measurements and the reason this
    # does not change the exported FBX (reaim_feet_for_unreal rebuilds those frames
    # absolutely at export time).
    # ============================================================================
    levelled_hinges = levelFootRollHinges(vx_armature)

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
    if aimed_spine:
        print("  aimed {} spine bone(s) at their chain successor:".format(len(aimed_spine)))
        for bone_name, child_name, turned in aimed_spine:
            print("      {:<12} -> {:<12} turned {:6.3f} deg"
                  .format(bone_name, child_name, turned))
    if clamped:
        print("  clamped {} bone lengths to their nearest child head:".format(len(clamped)))
        for bone_name, was, now in clamped:
            print("      {:<24} {:.6f} -> {:.6f}".format(bone_name, was, now))
    if levelled_hinges:
        print("  levelled {} foot hinge(s) to the ground:".format(len(levelled_hinges)))
        for bone_name, roll_was, roll_now, tilt_was, tilt_now in levelled_hinges:
            print("      {:<24} roll {:+8.3f} -> {:+8.3f}   hinge tilt {:+7.3f} -> {:+7.3f}"
                  .format(bone_name, roll_was, roll_now, tilt_was, tilt_now))

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


def aimSpineBonesAtChildren(vx_armature, bone_names=None, min_length=1e-5):
    """
    Point each listed spine bone at its chain successor, DazToUnreal style.

    Transcribes DTU's five AlignBone calls (DazToUnrealBlueprintUtils.cpp:442-448)
    - see dict_bones.spine_bones_aimed_at_children for which five and why not the
    others. It does NOT reproduce Quinn's S-curve: DTU never reads the target
    skeleton's geometry, so the curvature remains the Daz figure's and this only
    fixes which way each bone points along it.

    SIMPLER THAN DTU, ON PURPOSE, in two ways:

    - DTU aims in YAW ONLY (axis (0,0,1), Pitch left at 0), which is a 1-DOF
      approximation - and it uses plain atan rather than atan2, so it loses the
      quadrant. Here the tail is simply moved onto the child's head, a full 3-D
      aim with no trig at all. The two agree whenever the offset lies in the yaw
      plane, which for a symmetric figure's spine it does; where they differ, the
      full aim is the correct one.

    - Order is irrelevant. DTU has to work down the chain (04, 03, 02, then 05,
      then neck_01) because AlignBone reads the child's LOCAL offset and rotating a
      parent changes it. Blender edit bones store head and tail in armature space,
      so aiming a parent does not disturb its children and each bone is independent.

    Moving the tail onto the child's head also sets the LENGTH to reach it, which
    is what clampBoneLengthsToChildHeads would do for these bones anyway - so the
    clamp afterwards is a no-op on them rather than a conflict.

    KNOWN SIDE EFFECT: changing a bone's direction changes what its existing roll
    number means in world space, because roll is measured against a frame built
    from the bone's own direction. applyBlenderPerfectRolls has no spine entries
    (blender_perfect_roll_deltas is empty) precisely because Diffeomorphic already
    delivers the convention there "exact to three decimals" - that claim is about
    the UN-aimed spine, so re-check it if the rolls start looking off. The report
    below prints how far each bone actually turned, which is the number to judge
    that by.

    The armature must already be in EDIT mode.

    Returns a list of (bone_name, child_name, degrees_turned).
    """
    if bone_names is None:
        bone_names = getattr(dict_bones, "spine_bones_aimed_at_children", [])

    ebones = vx_armature.data.edit_bones
    successors = dict_bones.manny_chain_successors
    aimed = []

    for bone_name in bone_names:
        eb = ebones.get(bone_name)
        if eb is None:
            print("  spine aim: '{}' not in the rig - skipped".format(bone_name))
            continue

        candidates = successors.get(bone_name)
        if candidates is None:
            print("  spine aim: '{}' has no chain successor - skipped".format(bone_name))
            continue
        if isinstance(candidates, str):
            candidates = [candidates]

        child = None
        for candidate in candidates:
            child = ebones.get(candidate)
            if child is not None:
                break
        if child is None:
            print("  spine aim: none of '{}' successors {} are in the rig - skipped"
                  .format(bone_name, candidates))
            continue

        before = eb.tail - eb.head
        after = child.head - eb.head
        if before.length < min_length or after.length < min_length:
            print("  spine aim: '{}' and '{}' are coincident - skipped"
                  .format(bone_name, child.name))
            continue

        turned = math.degrees(before.normalized().angle(after.normalized()))
        eb.tail = child.head.copy()
        aimed.append((bone_name, child.name, turned))

    return aimed


def levelFootRollHinges(vx_armature,
                        bone_names=("foot.L", "foot.R", "ball.L", "ball.R"),
                        tolerance_degrees=0.01, vertical_guard_degrees=1.0):
    """
    Level each foot's HINGE axis to the ground, for foot-roll compatibility.

    Measured from the UE5 reference (bone_data.csv), this is the one property
    Epic actually solved for on the foot. Tracing the hinge axis (UE local Z,
    the blue one) down the leg:

        pelvis   0.0000 deg from horizontal
        thigh   -2.5398          <- leg splay tips it
        calf    -2.5398          <- passed straight through, its local
                                    rotation is a pure yaw
        foot    -0.0015          <- levelled again

    and foot's local Pitch is exactly -2.5398, the negated accumulated tilt.
    That is a deliberate correction, not inheritance. Note what is NOT
    constrained: the foot's own direction ends 88.19 deg from horizontal rather
    than a clean 90, and the toe axis 1.81 deg off level. Both are leftovers.
    Only the hinge lands on an exact value, because a level hinge is what makes
    ankle pitch and ball roll clean rotations for an animator.

    In BlenderPerfect the hinge is the bone's local +X ("every joint flexes
    about its local +X"), so levelling the hinge means putting local X in the
    horizontal plane. Only ROLL is touched - heads, tails, lengths and parenting
    are left exactly as the builder placed them.

    BALL IS IN THE LIST TOO, and has to be. In the UE5 reference ball's local
    rotation relative to foot is exactly (0, 0, 90) - a pure yaw about the axis
    the two share - so ball's hinge IS foot's hinge, and levelling one without
    the other leaves the toe joint rolling about a tilted axis. Each is levelled
    against its own direction rather than copied from the foot: that guarantees
    "X parallel to the ground" for both even when the toe line and the
    foot->ball line differ in azimuth, and the two agree anyway when they do
    not, which is the normal case.

    Must run AFTER clampBoneLengthsToChildHeads. The foot is in
    bones_length_set_to_successor, so the clamp is what puts its tail exactly on
    ball's head; until then the bone direction this solves against is not final.

    Sign-safe by construction: the only horizontal directions perpendicular to
    the bone are +/-(direction x UP), and the one closest to the rig's existing
    X is chosen. That makes this the SMALLEST roll that levels the hinge, and it
    inherits whatever left/right mirroring the Daz rig already had instead of
    imposing a convention. Idempotent for the same reason - a level hinge is
    already within tolerance and is skipped.

    Does NOT affect the exported FBX. exporter_unreal.reaim_feet_for_unreal
    rebuilds the foot and ball frames outright at export time (it has to: in
    Blender the foot points at the ball, in Manny it follows the calf), and an
    absolute frame discards anything set here. This is for the Blender-side rig,
    so the hinge is right while posing and inspecting.

    Handles its own edit-mode entry via _beginEditBones, which is a no-op when
    the caller is already editing this armature. So it works both inline in the
    builder and as a standalone pass at the end of the pipeline.

    Returns a list of (bone_name, roll_before, roll_after, tilt_before,
    tilt_after), all in degrees.
    """
    UP = Vector((0.0, 0.0, 1.0))
    token = _beginEditBones(vx_armature)
    ebones = vx_armature.data.edit_bones
    levelled = []

    try:
        for bone_name in bone_names:
            eb = ebones.get(bone_name)
            if eb is None:
                print("  foot hinge: '{}' not found - skipped".format(bone_name))
                continue

            direction = eb.tail - eb.head
            if direction.length < 1e-6:
                print("  foot hinge: '{}' is zero length - skipped".format(bone_name))
                continue
            direction.normalize()

            # A vertical bone has EVERY perpendicular horizontal, so its hinge is
            # already level and "level it" does not pick out a roll. Leave it
            # rather than snapping to an arbitrary one.
            if abs(direction.dot(UP)) > math.cos(math.radians(vertical_guard_degrees)):
                print("  foot hinge: '{}' is within {:.1f} deg of vertical - hinge "
                      "is level at any roll, skipped"
                      .format(bone_name, vertical_guard_degrees))
                continue

            current_x = eb.matrix.to_3x3() * Vector((1.0, 0.0, 0.0))
            tilt_before = math.degrees(math.asin(max(-1.0, min(1.0, current_x.z))))
            if abs(tilt_before) <= tolerance_degrees:
                continue                   # already level - keeps this idempotent

            hinge = direction.cross(UP).normalized()
            if hinge.dot(current_x) < 0.0:
                hinge = -hinge             # keep the side the rig already uses

            # align_roll aims the bone's local Z, so hand it the Z that belongs
            # with the X we want. Blender frames are right handed, so Z = X x Y.
            roll_before = math.degrees(eb.roll)
            eb.align_roll(hinge.cross(direction))
            roll_after = math.degrees(eb.roll)

            after_x = eb.matrix.to_3x3() * Vector((1.0, 0.0, 0.0))
            tilt_after = math.degrees(math.asin(max(-1.0, min(1.0, after_x.z))))

            levelled.append((bone_name,
                             _wrapDegrees(roll_before), _wrapDegrees(roll_after),
                             tilt_before, tilt_after))
    finally:
        _endEditBones(token)

    return levelled


def checkUE5Compatibility(vx_armature=None, tolerance_degrees=0.05,
                          position_tolerance=1e-4, verbose=True):
    """
    Read-only audit of the built rig against what Unreal expects. Changes NOTHING.

    Four checks, each reported independently so a partial rig still tells you
    something:

      1. Every Manny bone present. The reference set is derived from
         dtu_manny_bones_matching (the DazToUnreal transcription) plus "pelvis",
         which the builder adds by hand. Twists are counted separately because
         they only exist after setupTwistBones - missing twists mean "you ran
         Armature only", not "the rig is broken".

      2. spine_01 placed the way DazToUnreal places it: its head at the
         pelvis/spine_02 midpoint in Z, and on the pelvis in X and Y. Note this
         is measured RELATIVE to the pelvis, so a mispositioned pelvis shows up
         here too.

         The pelvis's own 0.7 drop is deliberately NOT checked. It is not
         verifiable from the finished rig - the drop consumed the original
         height - so the only way to test it is against the source Diffeomorphic
         rig, and this audit will not depend on that still being in the scene.
         Do not "fix" this by reaching for the source armature.

      3./4. foot and ball hinges parallel to the sole. In BlenderPerfect the
         hinge is the bone's local +X, and the sole is the ground plane in the
         rest pose, so the test is simply that local X has no Z component. This
         is what levelFootRollHinges sets, and what Epic solved for on the real
         mannequin - see that function for the measurements.

    Returns (all_ok, results), where results is a list of
    (title, ok, [detail lines]).
    """
    if vx_armature is None:
        vx_armature = bpy.data.objects.get("Armature")
    if vx_armature is None or vx_armature.type != 'ARMATURE':
        print("checkUE5Compatibility: no armature named 'Armature' found")
        return False, [("armature", False, ["no armature named 'Armature' found"])]

    UP = Vector((0.0, 0.0, 1.0))
    results = []

    token = _beginEditBones(vx_armature)
    try:
        ebones = vx_armature.data.edit_bones
        present = set(eb.name for eb in ebones)

        # ---------------------------------------------- 1. Manny bones present
        expected = set(dict_bones.dtu_manny_bones_matching.values())
        expected.add("pelvis")
        missing = sorted(expected - present)

        expected_twists = set()
        for _parent, twists, _blend in dict_bones.twist_bone_pairs:
            for twist_name, _fraction in twists:
                expected_twists.add(twist_name)
        missing_twists = sorted(expected_twists - present)

        lines = ["{}/{} Manny bones present".format(
            len(expected) - len(missing), len(expected))]
        for name in missing:
            lines.append("MISSING  {}".format(name))
        if missing_twists:
            lines.append("{}/{} twist bones present - run setupTwistBones "
                         "(or 'Manny FULL') if you expected them"
                         .format(len(expected_twists) - len(missing_twists),
                                 len(expected_twists)))
            for name in missing_twists:
                lines.append("missing twist  {}".format(name))
        else:
            lines.append("{}/{} twist bones present".format(
                len(expected_twists), len(expected_twists)))
        results.append(("1. Manny bones present", not missing, lines))

        # ------------------------------------------------ 2. spine_01 placement
        # Relative to the pelvis on purpose. That keeps the check self-contained:
        # the pelvis drop itself cannot be verified after the fact (the drop
        # consumed the original height), and testing it would mean depending on
        # the source Diffeomorphic rig still existing - which it may not.
        lines = []
        ok_positions = True

        if "spine_01" in present and "pelvis" in present and "spine_02" in present:
            pelvis_head = ebones["pelvis"].head
            spine_02_head = ebones["spine_02"].head
            wanted = Vector((pelvis_head.x, pelvis_head.y,
                             (pelvis_head.z + spine_02_head.z) / 2.0))
            offset = (ebones["spine_01"].head - wanted).length
            good = offset <= position_tolerance
            ok_positions = good
            lines.append("spine_01 head {} the midpoint rule, off by {:.6f}"
                         .format("MATCHES" if good else "MISSES", offset))
            lines.append("(measured against pelvis and spine_02 - the pelvis drop "
                         "itself is not verifiable post hoc and is not checked)")
        else:
            ok_positions = False
            lines.append("spine_01 / pelvis / spine_02 not all present - "
                         "midpoint rule not checked")

        results.append(("2. spine_01 placement", ok_positions, lines))

        # ------------------------------------------- 3./4. foot and ball hinges
        for title, names in (("3. foot hinge parallel to the sole",
                              ("foot.L", "foot.R")),
                             ("4. ball hinge parallel to the sole",
                              ("ball.L", "ball.R"))):
            lines = []
            ok_hinges = True
            for bone_name in names:
                eb = ebones.get(bone_name)
                if eb is None:
                    ok_hinges = False
                    lines.append("{:<10} MISSING".format(bone_name))
                    continue
                axis = eb.matrix.to_3x3() * Vector((1.0, 0.0, 0.0))
                tilt = math.degrees(math.asin(max(-1.0, min(1.0, axis.z))))
                good = abs(tilt) <= tolerance_degrees
                ok_hinges = ok_hinges and good
                lines.append("{:<10} hinge tilt {:+8.4f} deg  {}"
                             .format(bone_name, tilt,
                                     "ok" if good else "NOT LEVEL"))
            results.append((title, ok_hinges, lines))
    finally:
        _endEditBones(token)

    all_ok = all(ok for _title, ok, _lines in results)

    if verbose:
        print("")
        print("UE5 compatibility check on '{}'".format(vx_armature.name))
        print("=" * 64)
        for title, ok, lines in results:
            print("[{}] {}".format("PASS" if ok else "FAIL", title))
            for line in lines:
                print("       {}".format(line))
        print("=" * 64)
        print("{}".format("ALL CHECKS PASSED" if all_ok
                          else "SOME CHECKS FAILED - see above"))
        print("")

    return all_ok, results


def moveEndBonesToLayer(armature_object=None, layer_index=1, suffix="_end"):
    """
    Park the weightless _end tips on their own armature layer and hide it.

    They exist only so their parent has a child - Unreal draws a childless bone as
    a nub rather than a bone - and they clutter the viewport otherwise. Layer 1 is
    the convention already used for this in armature.py:555.

    VISIBILITY ONLY. Layers do not affect the FBX export: Blender filters bones by
    use_deform (see _buildJiggleBone), never by layer, and exporter_unreal carries
    `layers` across its bone rebuild at :1217 / :1279 - so the tips still reach
    Unreal, which is the whole reason they exist.

    Matches the suffix after any .L / .R, so butt_end.L counts as well as
    stomach_end. The layer list is assigned whole rather than toggled bit by bit,
    because Blender rejects a bone that ends up on no layer at all.

    Returns the names moved.
    """
    if armature_object is None:
        armature_object = bpy.data.objects.get("Armature")
    if armature_object is None or armature_object.type != 'ARMATURE':
        print("moveEndBonesToLayer: no armature named 'Armature' found")
        return []

    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    target_layers = [i == layer_index for i in range(32)]
    moved = []
    for bone in armature_object.data.bones:
        name = bone.name
        if name.endswith(".L") or name.endswith(".R"):
            name = name[:-2]
        if not name.endswith(suffix):
            continue
        bone.layers = target_layers
        bone.select = False
        bone.select_head = False
        bone.select_tail = False
        moved.append(bone.name)

    if moved:
        # Layer 0 stays on so the rig is still visible; the tips' layer goes off.
        armature_object.data.layers[0] = True
        armature_object.data.layers[layer_index] = False

    print("moveEndBonesToLayer: {} bone(s) moved to layer {} and hidden: {}"
          .format(len(moved), layer_index, moved or "none"))
    return moved


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
    # of the pipeline depends on (lEye, tongue01, ...). Note this ABORTS the whole
    # collapse rather than skipping the offending bone, so a name that belongs in a
    # merge list must be removed from bones_that_must_be_kept, not left in both.
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

    IDEMPOTENT, and this is why the source is the SUM of the two groups rather than
    whichever one already exists. Manny FULL rebuilds the BONES but never the MESH,
    so on a re-run both groups are present holding run-1's already-split weights.
    Reading one of them would re-split an already-split value and pull influence
    steadily toward whichever twist sits nearer the parent's head - it degrades a
    little more every run. Because w*(1-u) + w*u == w, their sum is exactly the
    original weight, so summing recovers it and a re-run reproduces run 1.

    On the FIRST run only one of the two exists - usually _01, but the Daz forearm
    twist maps to _02 (DazToUnreal's "// The Lower Arm twists are swapped") - and
    the sum is just that group, so the same code path covers both cases.

    The same caveat as everywhere else in this file: weight painted onto either
    twist by hand is folded back in and redistributed.

    Returns the number of vertices written, or None if neither group has weights.
    """
    groups = mesh_object.vertex_groups
    existing_01 = groups.get(name_01)
    existing_02 = groups.get(name_02)
    if existing_01 is None and existing_02 is None:
        return None
    # The SUM of the two, not one of them - see the docstring. This is what makes
    # a re-run idempotent.
    source_indices = set(g.index for g in (existing_01, existing_02) if g is not None)

    head, direction, length = parent_geometry
    if length <= 0.0:
        return None

    low = min(fraction_01, fraction_02)
    high = max(fraction_01, fraction_02)
    span = high - low
    # Whichever twist sits nearer the parent's head owns the (1-u) end.
    near_is_01 = fraction_01 <= fraction_02

    matrix = mesh_object.matrix_world

    # Read everything first: the sources ARE the two groups about to be written.
    samples = []
    for v in mesh_object.data.vertices:
        weight = 0.0
        for g in v.groups:
            if g.group in source_indices:
                weight += g.weight
        if weight <= 0.0:
            continue
        world_co = matrix * v.co
        t = (world_co - head).dot(direction) / length
        if span > 0.0:
            u = (t - low) / span
        else:
            u = 0.5
        u = max(0.0, min(1.0, u))
        samples.append((v.index, weight, u))

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


def setupPectoralChain(mesh_object, armature_object, sides=None,
                       first_split=0.40, nipple_length_fraction=0.0625,
                       split_low=0.25, split_high=0.75,
                       build_fishing_chain=True, rod_angle_degrees=10.0):
    """
    Split each pectoral into a chain and hang a nipple handle off the tip.

    Daz gives one bone per breast (lPectoral / rPectoral, renamed to
    pectoral_base by the builder). This turns each into TWO chains off one base:

        spine_05 -> pectoral_base -> pectoral_joint01 -> pectoral_joint02
                                                      -> nipple_joint
                                  -> pectoral_rod -> pectoral_line
                                                  -> pectoral_hook

    The first is the deforming chain. The second is the "fishing rod": a rod
    cantilevered out and up from the base, a line hanging vertically off its tip,
    and a hook sitting on the nipple. Like a rod held over water with a weighted
    line, the line stays perpendicular to the world plane, so gravity-style
    motion becomes a rotation of the rod alone. It carries no weight - it is a
    mechanism to drive the deforming chain from, not a deformer.

    `rod_angle_degrees` tilts the rod UP from the base->nipple line. The angle and
    the line length are not independent: the line can only be vertical AND land on
    the hook if the rod tip is directly above the nipple, so the angle is the input
    and the line length falls out (printed on each build).

    Cut twice: first at `first_split` (0.40, so 40/60), then the outer 60 halved,
    putting the second cut at 0.70. Segments are therefore 40% / 30% / 30% of the
    original bone, and nipple_joint is a short leaf past the tip - something
    selectable to hang constraints or manual posing off later.

    `nipple_length_fraction` is a fraction of the ORIGINAL bone, not of the
    segment it extends. 0.0625 is a sixteenth, which on a 0.2324 G3F pectoral
    gives a ~1.5 cm stub: big enough to click, small enough not to read as a
    deforming bone in the viewport.

    WEIGHTS GO ON joint02 AND joint03, NOT joint01. The split reads joint01 (the
    renamed Daz group, where all the weight starts) and writes the near half to
    joint02 and the far half to joint03, then clears joint01. The gradient is
    exactly the one the two-bone version produced - it just rides one bone
    further out.

    That is deliberate rather than incidental. Measured on G3F, the breast does
    not begin until t ~= 0.47 along the Daz bone, so joint01's whole 0..0.40 span
    is inside the ribcage. Leaving it weightless makes it a structural root the
    breast swings from, and puts the two deforming bones where the geometry
    actually is.

    TWO SPLIT MODES, ONE PER SIDE, DELIBERATELY. The left breast is split
    "axial" and the right "radial" so the two can be compared on the same
    figure. Both hand a vertex's weight over from joint01 to joint02 across the
    band between split_low and split_high, and both preserve total influence
    (w*(1-u) + w*u == w), so neither moves the mesh at rest. They differ only in
    what "how far along the breast" means:

        axial   t = ((co - head) . direction) / length
                Planes perpendicular to the bone. Distance off the axis is
                ignored, so the underside and the topside of the breast hand
                over at the same t. Same maths as _splitTwistWeights.

        radial  t = |co - head| / length
                Spherical shells centred on the chest wall. Follows the breast's
                actual shape more closely, but a vertex that sits far off-axis
                reads as "further along" than the axial version says it is.

    Set both sides to the same mode once you have picked a winner - see the
    `sides` argument, which is (side letter, mode) pairs.

    Idempotent by refusing to re-run: if pectoral_joint01 already exists on a
    side, that side is skipped whole. Splitting already-split weights would pull
    everything back toward the base.

    Must run AFTER switchVertexGroupsToManny - it looks for the vertex group
    under the Manny name (pectoral_base.L), not the Daz one (lPectoral).

    Returns a list of (side, mode, created_bone_names, verts_split).
    """
    if sides is None:
        sides = (("L", "axial"), ("R", "radial"))

    if armature_object is None or armature_object.type != 'ARMATURE':
        print("setupPectoralChain: no armature given")
        return []

    token = _beginEditBones(armature_object)
    ebones = armature_object.data.edit_bones

    # 40 / 60, then the 60 halved: boundaries at 0.40 and 0.70 of the original.
    second_split = first_split + (1.0 - first_split) * 0.5

    geometry = {}      # side -> (head, direction, length)
    created = {}       # side -> [names]
    try:
        for side, _mode in sides:
            root_name = "pectoral_base.{}".format(side)
            second_name = "pectoral_joint01.{}".format(side)
            third_name = "pectoral_joint02.{}".format(side)
            nipple_name = "nipple_joint.{}".format(side)

            root = ebones.get(root_name)
            if root is None:
                print("  pectoral: '{}' not in the rig - {} side skipped"
                      .format(root_name, side))
                continue
            if ebones.get(second_name) is not None:
                print("  pectoral: '{}' already exists - {} side skipped "
                      "(re-splitting would collapse the blend)"
                      .format(second_name, side))
                continue

            length = root.length
            if length <= 0.0:
                print("  pectoral: '{}' has zero length - {} side skipped"
                      .format(root_name, side))
                continue

            head = root.head.copy()
            tail = root.tail.copy()
            direction = (tail - head).normalized()
            cut_1 = head + direction * (length * first_split)
            cut_2 = head + direction * (length * second_split)
            geometry[side] = (head.copy(), direction.copy(), length)

            # joint01 keeps its head, parent and roll; only its tail moves in.
            root.tail = cut_1

            second = ebones.new(second_name)
            second.head = cut_1
            second.tail = cut_2
            second.roll = root.roll
            second.use_connect = False
            second.parent = root

            third = ebones.new(third_name)
            third.head = cut_2
            third.tail = tail
            third.roll = root.roll
            third.use_connect = False
            third.parent = second

            nipple = ebones.new(nipple_name)
            nipple.head = tail
            nipple.tail = tail + direction * (length * nipple_length_fraction)
            nipple.roll = root.roll
            nipple.use_connect = False
            nipple.parent = third

            created[side] = [second.name, third.name, nipple.name]
            wanted = (second_name, third_name, nipple_name)
            if tuple(created[side]) != wanted:
                print("  WARNING: pectoral names were uniquified by Blender: {}"
                      .format(created[side]))

            # --- fishing chain: rod -> line -> hook ------------------------------
            if build_fishing_chain:
                _createFishingChain(ebones, side, root, nipple, rod_angle_degrees,
                                    created.setdefault(side, []))
    finally:
        _endEditBones(token)

    # Weights need OBJECT mode, and the bones must be final before we measure.
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    results = []
    for side, mode in sides:
        if side not in geometry:
            continue
        base_name = "pectoral_base.{}".format(side)
        name_01 = "pectoral_joint01.{}".format(side)
        name_02 = "pectoral_joint02.{}".format(side)
        # The SOURCE is pectoral_base - it is the renamed Daz lPectoral group and
        # holds all the weight - but the two DESTINATIONS are joint01 and joint02.
        # The split lands one bone further out than the source, leaving the base as
        # weightless structure. That is deliberate: pectoral_base spans the inner
        # 40% of the Daz bone, which measures out as sitting inside the ribcage,
        # well behind where any breast vertex actually is.
        result = _splitPectoralWeights(mesh_object, base_name, name_01, name_02,
                                       geometry[side], mode,
                                       split_low, split_high)
        if result is None:
            print("  pectoral {}: no source weights on '{}' - groups left empty"
                  .format(side, base_name))
            for name in (name_01, name_02):
                if mesh_object.vertex_groups.get(name) is None:
                    mesh_object.vertex_groups.new(name=name)
            written = 0
        else:
            written, lo, hi = result
            # lo/hi are raw t along the bone. Far from 0..1 is normal and worth
            # seeing: on G3F the breast sits at roughly t 0.5..1.0 because the
            # Daz bone starts behind the sternum.
            print("  pectoral {}: moved {} verts onto '{}' + '{}' ({}, "
                  "breast spans t {:.2f}..{:.2f} of the bone; '{}' left empty)"
                  .format(side, written, name_01, name_02, mode, lo, hi, base_name))
        # The base, the nipple and the whole fishing chain carry no weight, but keep
        # empty groups so they survive an armature-modifier round trip and can be
        # painted later. The fishing bones are a mechanism, not deformers.
        weightless = ["nipple_joint.{}".format(side), base_name]
        if build_fishing_chain:
            weightless += ["pectoral_rod.{}".format(side),
                           "pectoral_line.{}".format(side),
                           "pectoral_hook.{}".format(side)]
        for name in weightless:
            if mesh_object is not None and mesh_object.vertex_groups.get(name) is None:
                mesh_object.vertex_groups.new(name=name)
        results.append((side, mode, created.get(side, []), written))

    print("setupPectoralChain: {} side(s) built - {}"
          .format(len(results),
                  ", ".join("{}={}".format(s, m) for s, m, _c, _w in results) or "none"))
    return results


FISHING_CHAIN_SUFFIXES = ("pectoral_rod", "pectoral_line", "pectoral_hook")


def _createFishingChain(ebones, side, base_eb, nipple_eb, rod_angle_degrees,
                        created=None):
    """
    Build (or rebuild) one side's rod -> line -> hook off pectoral_base.

    Mechanism bones - MCH in Rigify's vocabulary - carrying no weight. They exist
    to drive the deforming chain: a rod cantilevered out and up from the base, a
    line hanging vertically off its tip, and a hook on the nipple. Rotating the
    rod swings the line like a weighted fishing line over water.

    NOTE they are left with use_deform ON despite deforming nothing. The exporter
    runs the FBX writer with use_armature_deform_only=True (exporter_unreal.py:1141),
    which drops any bone whose use_deform is off - so marking these as non-deform
    the usual Blender way would silently delete them from the export.

    THE ANGLE IS THE ONLY INPUT; the line length is derived. The line can be
    vertical AND land on the hook only if the rod tip is directly above the
    nipple, so the two are not independent. Holding the rod's HORIZONTAL run
    equal to base.tail -> nipple and raising only its vertical component puts the
    tip on the nipple's X/Y exactly, making the line vertical by construction
    rather than to within a rounding error.

    ROLLS ARE COMPUTED, NOT INHERITED. Rod gets a level hinge (local X horizontal)
    so rotating it about +X is a pure vertical swing; the line is given the rod's
    hinge so both swing about ONE shared horizontal axis. The hook alone copies its
    source, because it is meant to BE nipple_joint's frame. See the inline notes.

    Note the line's X and Z are always horizontal whatever the angle - its Y is the
    vertical one - and the hook never moves with the angle at all.

    Existing rod/line/hook are removed first, leaf first so nothing is orphaned
    mid-delete, which is what makes this safe to re-run at a new angle.

    Returns (names, line_drop) or None if the geometry will not support a chain -
    including a rod angle so small that the line would have no length.
    """
    for suffix in reversed(FISHING_CHAIN_SUFFIXES):        # hook, line, rod
        old = ebones.get("{}.{}".format(suffix, side))
        if old is not None:
            ebones.remove(old)

    B = base_eb.tail.copy()
    tip = nipple_eb.head.copy()             # the original pectoral tail
    V = tip - B
    flat = Vector((V.x, V.y, 0.0))
    run = flat.length
    if run < 1e-6:
        print("  pectoral {}: bone is vertical, no horizontal run - "
              "fishing chain skipped".format(side))
        return None

    elevation = math.atan2(V.z, run)
    tilted = elevation + math.radians(rod_angle_degrees)
    if tilted >= math.radians(89.0):
        print("  pectoral {}: rod angle {:.1f} deg would stand the rod up past "
              "vertical - fishing chain skipped".format(side, rod_angle_degrees))
        return None

    rod_tip = B + flat + Vector((0.0, 0.0, run * math.tan(tilted)))
    drop = rod_tip.z - tip.z
    if drop < 1e-5:
        # At 0 deg the rod tip lands ON the nipple and the line has no length -
        # Blender deletes zero length bones, so the chain would come out missing a
        # link rather than failing. Refuse instead.
        print("  pectoral {}: rod angle {:.2f} deg leaves the line {:.6f} long - "
              "too short to build, raise the angle".format(side, rod_angle_degrees, drop))
        return None

    UP = Vector((0.0, 0.0, 1.0))

    rod = ebones.new("pectoral_rod.{}".format(side))
    rod.head = B
    rod.tail = rod_tip
    rod.use_connect = False
    rod.parent = base_eb

    # ROLL, both bones, is chosen rather than inherited. Copying base_eb.roll (what
    # this used to do) is meaningless: roll is a scalar measured against a frame
    # built from the bone's OWN direction, so the same number on bones pointing
    # different ways gives unrelated axes in world space. The rod sits 10 deg off
    # the base and the line ~85 deg off it, so both were effectively arbitrary.
    #
    # Rod: level the hinge, exactly the rule levelFootRollHinges uses - local X
    # horizontal, so rotating the rod about +X is a pure vertical swing, which is
    # the gravity motion this whole construct exists to model.
    #
    # SIGN comes from the deforming chain, not from the cross product. Levelling
    # leaves two candidates, +/-(rod_dir x UP), and both are equally level; taking
    # the raw cross product picked one arbitrarily and it came out pointing the
    # opposite way to pectoral_joint01's X. Matching joint01 instead keeps the two
    # chains readable side by side, mirrors L/R for free (joint01's own X mirrors),
    # and costs nothing - swinging about +X or -X is the same plane either way,
    # only the sign of the rotation differs.
    #
    # If the two are near perpendicular the dot product cannot pick a side
    # meaningfully, so fall back to the cross product handedness rather than let
    # numerical noise decide.
    rod_dir = (rod_tip - B).normalized()
    hinge = rod_dir.cross(UP).normalized()
    reference = ebones.get("pectoral_joint01.{}".format(side)) or base_eb
    reference_x = reference.matrix.to_3x3() * Vector((1.0, 0.0, 0.0))
    alignment = hinge.dot(reference_x)
    if abs(alignment) > 1e-3 and alignment < 0.0:
        hinge = -hinge
    rod.align_roll(hinge.cross(rod_dir))

    line = ebones.new("pectoral_line.{}".format(side))
    line.head = rod_tip
    line.tail = tip                         # straight down onto the nipple
    line.use_connect = False
    line.parent = rod

    # Line: levelling cannot work here - it points straight down, so EVERY
    # perpendicular is already horizontal and "make X level" picks no roll at all
    # (the same degenerate case levelFootRollHinges guards against). Give it the
    # rod's hinge instead, so rod and line swing about ONE shared horizontal axis,
    # which is what makes a two link pendulum predictable to drive.
    #
    # align_roll aims local Z, so hand it the Z that belongs with the X we want:
    # frames are right handed, Z = X x Y. Well conditioned because rod_x and the
    # line's direction are perpendicular by construction.
    rod_x = rod.matrix.to_3x3() * Vector((1.0, 0.0, 0.0))
    line_dir = (tip - rod_tip).normalized()
    line.align_roll(rod_x.cross(line_dir))

    hook = ebones.new("pectoral_hook.{}".format(side))
    hook.head = nipple_eb.head              # same coordinates as nipple_joint
    hook.tail = nipple_eb.tail
    hook.roll = nipple_eb.roll
    hook.use_connect = False
    hook.parent = line

    names = [rod.name, line.name, hook.name]
    if created is not None:
        created += names
    print("  pectoral {}: fishing chain - rod {:.1f} deg above the joint01 line, "
          "line drops {:.4f}".format(side, rod_angle_degrees, drop))
    return (names, drop)


def rebuildPectoralFishingChains(armature_object=None, rod_angle_degrees=10.0,
                                 sides=("L", "R")):
    """
    Re-cut the fishing chains on an already built rig, at a new rod angle.

    Reads everything it needs off the rig itself - `pectoral_base` for the rod's
    root and `nipple_joint` for where the hook goes - so it does not care how the
    rig was produced or how long ago. Bones only; no vertex groups are touched,
    which is safe precisely because the fishing chain never carries weight.

    Returns a list of (side, line_drop) for the sides that were rebuilt.
    """
    if armature_object is None:
        armature_object = bpy.data.objects.get("Armature")
    if armature_object is None or armature_object.type != 'ARMATURE':
        print("rebuildPectoralFishingChains: no armature named 'Armature' found")
        return []

    rebuilt = []
    token = _beginEditBones(armature_object)
    try:
        ebones = armature_object.data.edit_bones
        for side in sides:
            base_eb = ebones.get("pectoral_base.{}".format(side))
            nipple_eb = ebones.get("nipple_joint.{}".format(side))
            if base_eb is None or nipple_eb is None:
                print("  pectoral {}: needs pectoral_base and nipple_joint - "
                      "skipped".format(side))
                continue
            result = _createFishingChain(ebones, side, base_eb, nipple_eb,
                                         rod_angle_degrees)
            if result is not None:
                rebuilt.append((side, result[1]))
    finally:
        _endEditBones(token)

    print("rebuildPectoralFishingChains: {} side(s) at {:.1f} deg"
          .format(len(rebuilt), rod_angle_degrees))
    return rebuilt


# Named so the toggle can find its own work and never touch a hand made IK that
# happens to sit on the same bone.
FISHING_IK_CONSTRAINT_NAME = "VX Fishing IK"
FISHING_STRETCH_CONSTRAINT_NAME = "VX Fishing Stretch"


def _namedConstraint(pose_bone, constraint_type, name):
    """One of OUR constraints on this bone, or None. Matched by name AND type, so
    a hand made constraint of the same type is never picked up or removed."""
    if pose_bone is None:
        return None
    for constraint in pose_bone.constraints:
        if constraint.type == constraint_type and constraint.name == name:
            return constraint
    return None


def _fishingIKConstraint(pose_bone):
    """Our IK on this bone, or None. Matched by NAME, not just by type."""
    return _namedConstraint(pose_bone, 'IK', FISHING_IK_CONSTRAINT_NAME)


def _clearLegacyHookStretch(armature_object, side):
    """
    Drop the STRETCH_TO an earlier version put on pectoral_hook.

    That was the wrong place for it: the stretching belongs on the CHAIN, so that
    joint02's tail actually reaches the target, not on the target itself.
    """
    hook_pose = armature_object.pose.bones.get("pectoral_hook.{}".format(side))
    if hook_pose is None:
        return
    for constraint in list(hook_pose.constraints):
        if constraint.type == 'STRETCH_TO':
            hook_pose.constraints.remove(constraint)
            print("  fishing {}: removed the old hook STRETCH_TO".format(side))


def enablePectoralFishingRig(armature_object=None, sides=("L", "R"),
                             stretch_influence=(0.15, 0.25)):
    """
    Wire the fishing chain up so it drives the deforming chain.

    Per side:

    1. IK named FISHING_IK_CONSTRAINT_NAME on pectoral_joint02, target
       pectoral_hook, chain_count 2. Bend only - use_stretch is OFF.

       The IK goes on joint02, NOT on nipple_joint. Blender drives the CONSTRAINED
       bone's tail to the target and counts the chain upward from it inclusive, so
       joint02 + count 2 is exactly {joint01, joint02}. On nipple_joint it would be
       {nipple_joint, joint02} and leave joint01 rigid.

    2. STRETCH_TO named FISHING_STRETCH_CONSTRAINT_NAME on BOTH joint01 and
       joint02, targeting pectoral_hook, at `stretch_influence` - a
       (joint01, joint02) pair, tuned to (0.15, 0.25).

       Reaching has to happen somehow: joint01 + joint02 ARE the segment from
       base.tail to the nipple, and the hook sits on the nipple at rest, so
       |base.tail -> hook| equals the chain length EXACTLY (0.13942 on G3F). The
       chain is straight and fully extended at rest, and rotating the rod DOWN -
       the gravity direction this whole construct models - puts the hook out of
       reach:

           rod -30 deg  0.15227 vs 0.13942 reach -> 0.0128 short
           rod   0 deg  0.13942 vs 0.13942 reach -> singular
           rod +30 deg  0.12732 vs 0.13942 reach -> bends fine

       IK use_stretch was tried first and rejected: the solver distributes scaling
       across the chain by its own rule, so joint01 grew as much as joint02 and the
       deformation read wrong. (It also needs PoseBone.ik_stretch raised off its
       0.0 default or the constraint flag silently does nothing - a trap worth
       remembering if it is ever revisited. Both are zeroed here.)

    3. pectoral_line gets use_inherit_rotation = False and its rotation locked.

       That is the "line hangs straight down" behaviour, and it is a bone flag
       rather than a constraint on purpose. The line's REST orientation is already
       exactly vertical, so refusing to inherit rotation pins it there while its
       head still follows the rod tip - a plumb line. It blocks EVERY ancestor, not
       just the rod, so bending the spine does not tilt it either.

       The lock is on the line ONLY. use_inherit_rotation blocks rotation arriving
       from ancestors but not the bone's own, so a stray keyframe could still tip
       it. The rod is the bone you drive, the hook's rotation is inert (IK reads its
       HEAD, which its own rotation cannot move), and joint01/joint02 are IK driven.

    nipple_joint gets NOTHING. It is a marker for pectoral_joint02's tail, kept for
    readability and as a convenient place for the hook to borrow coordinates from.
    Its use_deform is deliberately left ON despite it deforming nothing - the FBX
    writer runs with use_armature_deform_only=True (exporter_unreal.py:1141) and
    drops non-deform bones, so turning it off would delete it from the export.

    No dependency cycle: the hook hangs off line -> rod -> pectoral_base while
    joint02 hangs off joint01 -> pectoral_base. Siblings, so the IK target does not
    depend on the bones the IK drives.

    NOTE Blender-side only. Constraints and bone flags do not survive FBX export -
    in Unreal this has to be rebuilt as a Control Rig or an anim graph node.

    Returns a list of (side, ik_bone, target_bone) for the sides wired up.
    """
    if armature_object is None:
        armature_object = bpy.data.objects.get("Armature")
    if armature_object is None or armature_object.type != 'ARMATURE':
        print("enablePectoralFishingRig: no armature named 'Armature' found")
        return []

    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    wired = []
    for side in sides:
        ik_name = "pectoral_joint02.{}".format(side)
        near_name = "pectoral_joint01.{}".format(side)
        hook_name = "pectoral_hook.{}".format(side)
        line_name = "pectoral_line.{}".format(side)

        pose_bone = armature_object.pose.bones.get(ik_name)
        near_pose = armature_object.pose.bones.get(near_name)
        bones = armature_object.data.bones
        if (pose_bone is None or near_pose is None
                or hook_name not in bones or line_name not in bones):
            print("  fishing {}: needs {}, {}, {} and {} - skipped"
                  .format(side, near_name, ik_name, hook_name, line_name))
            continue

        _clearLegacyHookStretch(armature_object, side)

        ik = _fishingIKConstraint(pose_bone)
        if ik is None:
            ik = pose_bone.constraints.new('IK')
            ik.name = FISHING_IK_CONSTRAINT_NAME
        ik.target = armature_object
        ik.subtarget = hook_name
        ik.chain_count = 2
        ik.use_stretch = False

        # IK stretch OFF, on both halves of the setting. The solver distributes
        # scaling across every bone in the chain by its own rule, which is what
        # made the deformation look wrong - joint01 grew as much as joint02 even
        # though only the outer bone needs to make up the gap.
        near_pose.ik_stretch = 0.0
        pose_bone.ik_stretch = 0.0

        # STRETCH_TO on BOTH chain bones instead, so the reach can be shared
        # between them by influence rather than distributed by the solver's own
        # rule. Appended AFTER the IK, and Blender evaluates the stack in order,
        # so these win on aim and length while the IK still sets the bend.
        #
        # rest_length is measured per bone as its head -> hook distance AT REST,
        # not the bone's own length. For joint02 those happen to be equal (its
        # tail IS the hook), but for joint01 the hook is a whole bone further on,
        # so using its own length would read as "already stretched 2x" and it
        # would double the moment the constraint switched on.
        #
        # INFLUENCE IS THE DIAL. At 1.0 on joint01 the constraint fully aims that
        # bone at the hook too, both bones point at the same place, and the chain
        # straightens out - which defeats the IK bend entirely. Partial influence
        # on both is what lets them share the stretch and still bend, hence the
        # 0.5 default.
        #
        # NO_VOLUME keeps it a pure lengthwise stretch. Switch to 'VOLUME_XZX' if
        # you want the breast to thin as it extends - more soft-tissue-like, but
        # it couples the stretch into the mesh's width.
        for stretch_pose, influence in ((near_pose, stretch_influence[0]),
                                        (pose_bone, stretch_influence[1])):
            stretch = _namedConstraint(stretch_pose, 'STRETCH_TO',
                                       FISHING_STRETCH_CONSTRAINT_NAME)
            if stretch is None:
                stretch = stretch_pose.constraints.new('STRETCH_TO')
                stretch.name = FISHING_STRETCH_CONSTRAINT_NAME
            stretch.target = armature_object
            stretch.subtarget = hook_name
            # Written every run, not only on create: the tuned values live in the
            # `stretch_influence` default, so the code is the source of truth and
            # re-running enable re-applies them rather than preserving whatever is
            # currently on the bone.
            stretch.influence = influence
            stretch.rest_length = (bones[hook_name].head_local
                                   - bones[stretch_pose.name].head_local).length
            stretch.volume = 'NO_VOLUME'

        bones[line_name].use_inherit_rotation = False
        line_pose = armature_object.pose.bones.get(line_name)
        if line_pose is not None:
            line_pose.lock_rotation = (True, True, True)
            line_pose.lock_rotation_w = True

        wired.append((side, ik_name, hook_name))
        print("  fishing {}: '{}' on '{}' -> '{}' (chain 2, STRETCH_TO on "
              "joint01+joint02 at influence {}), "
              "'{}' pinned vertical and locked"
              .format(side, FISHING_IK_CONSTRAINT_NAME, ik_name, hook_name,
                      tuple(stretch_influence), line_name))

    bpy.context.scene.update()
    print("enablePectoralFishingRig: {} side(s) wired".format(len(wired)))
    return wired


def disablePectoralFishingRig(armature_object=None, sides=("L", "R")):
    """
    Undo enablePectoralFishingRig, leaving the bones themselves alone.

    Removes ONLY the named IK, so a hand made IK on the same bone survives. Puts
    back everything enable changed: ik_stretch to 0, the line inheriting rotation
    again and unlocked. Bones, weights and hierarchy are untouched.

    Returns a list of sides that had something to remove.
    """
    if armature_object is None:
        armature_object = bpy.data.objects.get("Armature")
    if armature_object is None or armature_object.type != 'ARMATURE':
        print("disablePectoralFishingRig: no armature named 'Armature' found")
        return []

    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    cleared = []
    for side in sides:
        ik_name = "pectoral_joint02.{}".format(side)
        near_name = "pectoral_joint01.{}".format(side)
        line_name = "pectoral_line.{}".format(side)
        bones = armature_object.data.bones
        touched = False

        pose_bone = armature_object.pose.bones.get(ik_name)
        ik = _fishingIKConstraint(pose_bone)
        if ik is not None:
            pose_bone.constraints.remove(ik)
            touched = True

        stretch = _namedConstraint(pose_bone, 'STRETCH_TO',
                                   FISHING_STRETCH_CONSTRAINT_NAME)
        if stretch is not None:
            pose_bone.constraints.remove(stretch)
            touched = True

        for name in (near_name, ik_name):
            chain_pose = armature_object.pose.bones.get(name)
            if chain_pose is not None and chain_pose.ik_stretch:
                chain_pose.ik_stretch = 0.0
                touched = True

        _clearLegacyHookStretch(armature_object, side)

        if line_name in bones and not bones[line_name].use_inherit_rotation:
            bones[line_name].use_inherit_rotation = True
            touched = True
        line_pose = armature_object.pose.bones.get(line_name)
        if line_pose is not None:
            line_pose.lock_rotation = (False, False, False)
            line_pose.lock_rotation_w = False

        if touched:
            cleared.append(side)
            print("  fishing {}: IK removed, '{}' back to inheriting rotation"
                  .format(side, line_name))

    bpy.context.scene.update()
    print("disablePectoralFishingRig: {} side(s) cleared".format(len(cleared)))
    return cleared


def toggleFishingRig(armature_object=None, sides=("L", "R"),
                     stretch_influence=(0.15, 0.25)):
    """
    Off -> on -> off. Returns (is_enabled_now, affected_sides).

    "Currently on" means the named IK exists on ANY side, so a half wired rig - one
    side built, or a side skipped for missing bones - toggles OFF first rather than
    stacking a second copy onto the side that already had one.
    """
    if armature_object is None:
        armature_object = bpy.data.objects.get("Armature")
    if armature_object is None or armature_object.type != 'ARMATURE':
        print("toggleFishingRig: no armature named 'Armature' found")
        return (False, [])

    enabled = any(
        _fishingIKConstraint(
            armature_object.pose.bones.get("pectoral_joint02.{}".format(side)))
        is not None
        for side in sides)

    if enabled:
        return (False, disablePectoralFishingRig(armature_object, sides))
    wired = enablePectoralFishingRig(armature_object, sides, stretch_influence)
    return (bool(wired), [side for side, _ik, _target in wired])


def _splitPectoralWeights(mesh_object, source_name, near_name, far_name, geometry,
                          mode, low, high, percentile=0.05):
    """
    Split source_name's weights between near_name and far_name across [low, high].

    The source is a THIRD group, not one of the destinations: on the pectoral
    chain the weight lives on joint01 (the renamed Daz lPectoral) but belongs on
    joint01 and joint02. Whatever is read is removed from the source afterwards,
    so influence is moved rather than duplicated. If source_name IS one of the
    destinations the removal is skipped, which keeps the two-bone case working.

    `mode` picks what "how far along" means - see setupPectoralChain:
        "axial"  scalar projection onto the bone axis (ignores off-axis distance)
        "radial" straight-line distance from the chain's head (spherical shells)

    NORMALISED AGAINST THE WEIGHTED VERTICES, NOT THE BONE. The first version
    divided by bone length and assumed the bone spans the geometry it weights.
    That holds for the twists - thigh.L really does span the thigh - but not
    here. Measured on G3F, lPectoral originates behind the sternum, near the
    spine, and the breast does not begin until 42% along it:

        axial t: min 0.42  p10 0.51  med 0.76  p90 1.00  max 1.02

    so a [0.25, 0.75] band on raw t put the MEDIAN vertex at u = 1.02, clamped
    to 1.0, and joint01 came out empty. Instead the raw t values are collected
    first, the `percentile`..(1 - `percentile`) range of them is mapped onto
    [0, 1], and the band is applied to that. One stray vertex therefore cannot
    skew the range, and the result is independent of where Daz chose to root the
    bone or how long it is.

    low/high stay fractions of the BREAST's own extent, so the two sides remain
    directly comparable across the axial/radial A/B.

    All samples are read before anything is written, because name_01 is both the
    source and one of the destinations.

    Returns (verts_written, lo, hi) where lo/hi are the raw t values that got
    mapped to 0 and 1, or None if name_01 has no weights.
    """
    groups = mesh_object.vertex_groups
    source = groups.get(source_name)
    if source is None:
        return None

    head, direction, length = geometry
    if length <= 0.0:
        return None

    matrix = mesh_object.matrix_world
    source_index = source.index

    samples = []
    for v in mesh_object.data.vertices:
        for g in v.groups:
            if g.group == source_index and g.weight > 0.0:
                offset = (matrix * v.co) - head
                if mode == "radial":
                    t = offset.length / length
                else:
                    t = offset.dot(direction) / length
                samples.append((v.index, g.weight, t))
                break

    if not samples:
        return None

    # Percentile rather than min/max so a single stray weighted vertex - a stray
    # from a morph, or bleed from a neighbouring group - cannot stretch the range
    # and flatten the gradient for everything else.
    ordered = sorted(t for _i, _w, t in samples)
    last = len(ordered) - 1
    lo = ordered[int(percentile * last)]
    hi = ordered[int((1.0 - percentile) * last)]
    extent = hi - lo
    band = high - low

    group_near = groups.get(near_name) or groups.new(name=near_name)
    group_far = groups.get(far_name) or groups.new(name=far_name)
    for v_index, weight, t in samples:
        if extent > 0.0:
            s = (t - lo) / extent          # 0..1 across the breast itself
            u = (s - low) / band if band > 0.0 else 0.5
        else:
            u = 0.5                        # every vertex at the same depth
        u = max(0.0, min(1.0, u))
        group_near.add([v_index], weight * (1.0 - u), 'REPLACE')
        group_far.add([v_index], weight * u, 'REPLACE')

    # Move, do not copy: the source keeps its weights otherwise and every vertex
    # ends up with 2x influence, which shows up as the mesh inflating when the
    # chain rotates.
    if source_name not in (near_name, far_name):
        source.remove([v_index for v_index, _w, _t in samples])

    return (len(samples), lo, hi)


def _buildJiggleBone(mesh_object, armature_object, joint_name, end_name,
                     base_indices, top_indices, parent_name, source_groups,
                     radius, max_weight, forward_only=True, side_sign=None,
                     end_length=0.02, flatten_head_z=True,
                     vertical_reach=(1.0, 1.0), lower_fullness=0.0,
                     lower_limit_indices=None, lower_limit_overshoot=1.0,
                     plateau=0.0, plateau_below=None,
                     upper_scale=1.0, peak_depth=1.0):
    """
    Build one mesh-derived jiggle bone plus its _end stub, and borrow it weight.

    Shared by setupStomachBone and setupButtBones - and shaped to take the rib
    bones too, which sit in extra_bones_torso.json waiting for the same treatment.

        <joint_name>  head = centre of `base_indices` (a ring of verts, averaged,
                             which lands inside the body)
                      tail = centre of `top_indices` (the surface point)
        <end_name>    head = that surface point
                      tail = a short stub further along the same direction

    The aim is free: the joint's tail IS the end's head, so it already points at it.

    `flatten_head_z` snaps the head to the tail's height, making the bone perfectly
    horizontal. The legacy VXMod builder does this for both stomach and butt
    (difeomorphic_workflow_armature_from_other_vertices.py:25, :47, :54) and it
    gives the physics a clean swing axis instead of one tilted by whatever the
    vertex ring averaged to.

    BOTH BONES GET use_deform = True, the _end included even though it carries no
    weight. The FBX writer runs with use_armature_deform_only=True
    (exporter_unreal.py:1864, :2064) and drops bones by that FLAG, not by whether
    they actually have weight - and Blender only spares a non-deforming bone if it
    has a DEFORMING CHILD, which a leaf never has. Without the flag the stub
    vanishes from the export and Unreal draws the joint as a nub, not a bone.
    (`dontExportJointEnds` is NOT what governs this - declared at __init__.py:219
    and never read anywhere.)

    WEIGHTS are moved, not added: what the joint gains is subtracted from the
    source, so total influence per vertex is unchanged and the mesh does not shift
    at rest. Three tests decide what is in range:

      radius      distance from the SURFACE point, smoothstep falloff to zero at
                  the edge so there is no hard seam.
      forward     the vertex must be on the tail side of the head, tested against
                  the bone's own axis. Cheap, since the axis is already to hand.
      vertical_reach
                  (up, down) as fractions of radius, applied to the z offset.
                  (1.0, 1.0) is a sphere; the butt uses (0.55, 1.25) so the
                  region reaches under the glutes instead of climbing into the
                  lumbar spine.
      lower_limit_indices
                  verts along an anatomical floor. Their mean height overrides
                  vertical_reach[1] - a measured boundary instead of a guessed
                  radius, and seamless because the curve arrives at zero rather
                  than being cut off.
      lower_limit_overshoot
                  how far PAST that floor the falloff actually reaches, as a
                  multiple of the span. 1.0 puts zero exactly on the boundary -
                  which means the boundary itself gets NO weight. Above 1.0
                  pushes the zero below it so the boundary keeps a real value,
                  at the cost of a little spill past it.
      upper_scale scales the weight AT THE APEX, ramping smoothly to full value
                  at the lower limit. 1.0 is flat. Below 1.0 the region gets
                  lighter the higher it goes, which is what keeps a glute bone
                  off the lumbar back while staying strong at the crease. Needs
                  lower_limit_indices - without a measured floor there is no
                  height to ramp between.
      peak_depth  where the vertical profile maxes, in units of the apex->limit
                  span. 1.0 peaks ON the limit, which makes the limit itself the
                  heaviest band. Below 1.0 moves the peak up into the body so the
                  limit lands on the falling side and reads softer.
      plateau_below
                  the plateau to ease toward BELOW the tail, blended in by depth.
                  None keeps `plateau` everywhere. 0.0 spreads the horizontal
                  taper across the whole radius down there, which is what softens
                  the lower edges without moving the boundary or touching the
                  region above the tail.
      plateau     fraction of the radius held at FULL value before the taper
                  starts. 0.0 is a pure smoothstep from the tip, which peaks on
                  the tip and sheds weight all the way down. Raising it flattens
                  the middle so the region reads evenly instead of as a hot spot.
      lower_fullness
                  0.0 leaves the falloff alone. Higher values fatten it below
                  the apex - weight only, the region's extent does not move -
                  which is what the under-glute crease needs.
      side_sign   +1 keeps only x > 0, -1 only x < 0, None disables it. REQUIRED
                  for paired bones: .L and .R borrow from the SAME source group, so
                  without it an overlapping radius lets both claim a vertex, the
                  second REPLACE silently clobbers the first, and the source has
                  weight taken twice but credited once. Midline verts (x ~= 0) fall
                  to neither side, which is correct - the cleft should not jiggle
                  sideways.

    IDEMPOTENT. Weight borrowed by an earlier run is handed back before anything is
    taken, so re-running Manny FULL neither stacks nor strands vertices that a
    smaller radius no longer covers. Note that folds in any weight painted onto the
    joint by hand, treating it as borrowed.

    Returns (created_bone_names, verts_touched, weight_moved).
    """
    if mesh_object is None or mesh_object.type != 'MESH':
        print("  jiggle '{}': no mesh given".format(joint_name))
        return ([], 0, 0.0)
    if armature_object is None or armature_object.type != 'ARMATURE':
        print("  jiggle '{}': no armature given".format(joint_name))
        return ([], 0, 0.0)

    vertices = mesh_object.data.vertices
    needed = max(list(base_indices) + list(top_indices))
    if needed >= len(vertices):
        print("  jiggle '{}': mesh has {} verts, needs index {} - wrong topology, "
              "skipped".format(joint_name, len(vertices), needed))
        return ([], 0, 0.0)

    centre = getCenter(list(base_indices), mesh_object)
    surface = getCenter(list(top_indices), mesh_object)
    if flatten_head_z:
        centre.z = surface.z
    axis = surface - centre
    if axis.length < 1e-6:
        print("  jiggle '{}': head and tail are coincident - skipped".format(joint_name))
        return ([], 0, 0.0)
    axis = axis.normalized()

    crease_span = 0.0
    # A mesh-derived floor beats a guessed radius. Given verts along an anatomical
    # boundary - the gluteal crease, say - take their mean height and set the
    # DOWNWARD reach so the smoothstep hits exactly zero there. The boundary then
    # IS the crease: nothing below is in range, and because the falloff arrives at
    # zero rather than being chopped off, there is no seam along it.
    if lower_limit_indices:
        limit_needed = max(lower_limit_indices)
        if limit_needed >= len(vertices):
            print("  jiggle '{}': limit index {} past the end of the mesh - ignored"
                  .format(joint_name, limit_needed))
        else:
            limit_z = getCenter(list(lower_limit_indices), mesh_object).z
            crease_span = surface.z - limit_z      # raw, for the upper_scale ramp
            span = crease_span * lower_limit_overshoot
            if span > 1e-6:
                vertical_reach = (vertical_reach[0], span / radius)
                print("  jiggle '{}': lower limit from {} verts at z {:.4f} -> reach "
                      "down {:.4f} m ({:.2f} x radius)"
                      .format(joint_name, len(lower_limit_indices), limit_z, span,
                              vertical_reach[1]))
            else:
                print("  jiggle '{}': limit verts are at or above the tail - ignored"
                      .format(joint_name))

    # --- bones -------------------------------------------------------------
    created = []
    token = _beginEditBones(armature_object)
    try:
        ebones = armature_object.data.edit_bones
        parent = ebones.get(parent_name)
        if parent is None:
            print("  jiggle '{}': parent '{}' not in the rig - skipped"
                  .format(joint_name, parent_name))
            return ([], 0, 0.0)

        for name in (end_name, joint_name):          # leaf first, never orphan
            old = ebones.get(name)
            if old is not None:
                ebones.remove(old)

        joint = ebones.new(joint_name)
        joint.head = centre
        joint.tail = surface
        joint.roll = parent.roll
        joint.use_connect = False
        joint.use_deform = True
        joint.parent = parent

        end = ebones.new(end_name)
        end.head = surface
        end.tail = surface + axis * end_length
        end.roll = joint.roll
        end.use_connect = False
        end.use_deform = True        # see the docstring - without this it is dropped
        end.parent = joint

        created = [joint.name, end.name]
    finally:
        _endEditBones(token)

    if not created:
        return ([], 0, 0.0)

    # --- weights -----------------------------------------------------------
    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    groups = mesh_object.vertex_groups
    target = groups.get(joint_name) or groups.new(name=joint_name)
    if groups.get(end_name) is None:
        groups.new(name=end_name)                # empty, keeps group/bone parity

    source_indices = {}
    for group_name in source_groups:
        group = groups.get(group_name)
        if group is None:
            print("  jiggle '{}': source group '{}' not on the mesh - ignored"
                  .format(joint_name, group_name))
            continue
        source_indices[group.index] = group
    if not source_indices:
        print("  jiggle '{}': no source groups found, created with an empty group"
              .format(joint_name))
        return (created, 0, 0.0)

    # Reclaim first - see the docstring. Given back PROPORTIONALLY to whatever the
    # sources still hold at that vertex, which is exact rather than approximate:
    # the borrow took max*falloff of EACH source, so what is left is still in the
    # original proportions, and splitting the total the same way restores them.
    # Only when no source has any weight left does it fall back to source_groups[0].
    primary = source_indices[list(source_indices)[0]]
    reclaimed = []
    for v in vertices:
        target_weight = 0.0
        shares = []
        for g in v.groups:
            if g.group == target.index:
                target_weight = g.weight
            elif g.group in source_indices:
                shares.append((source_indices[g.group], g.weight))
        if target_weight > 0.0:
            reclaimed.append((v.index, target_weight, shares))
    for v_index, weight, shares in reclaimed:
        total = sum(w for _group, w in shares)
        if total > 0.0:
            for group, w in shares:
                group.add([v_index], w + weight * (w / total), 'REPLACE')
        else:
            primary.add([v_index], weight, 'ADD')
        target.remove([v_index])

    # Read every sample before writing - the sources are about to be edited.
    #
    # HORIZONTAL AND VERTICAL ARE SEPARATE PROFILES, multiplied together. They were
    # one radial distance before, and that could not express what a glute needs: any
    # single metric centred on the bone tip is strongest AT the tip and weakest at
    # the crease, which is the opposite of the shape. No amount of reshaping one
    # curve fixes that - the two axes want different profiles, so they get them.
    #
    #   horizontal   smoothstep out to `radius`, held flat inside `plateau`
    #   vertical     ramps from `upper_scale` at the apex to FULL at the lower
    #                limit, then falls to zero across the overshoot below it;
    #                above the apex it fades out over vertical_reach[0] * radius
    #
    # With no lower_limit_indices there is no measured floor to ramp between, so it
    # falls back to the old symmetric decay and the stomach behaves as before.
    up_span = radius * vertical_reach[0]
    samples = []
    for v in vertices:
        if side_sign is not None and v.co.x * side_sign <= 0.0:
            continue
        offset = v.co - surface

        # --- vertical ---
        if crease_span > 0.0:
            if offset.z > 0.0:                      # above the apex
                if up_span <= 0.0 or offset.z > up_span:
                    continue
                a = offset.z / up_span
                vertical = upper_scale * (1.0 - (3.0 * a * a - 2.0 * a * a * a))
            else:
                # Depth in units of the apex->limit span: 0 at the apex, 1 at the
                # limit, beyond that below it. The profile PEAKS at `peak_depth`
                # and decays from there to zero at `lower_limit_overshoot`.
                #
                # peak_depth < 1 puts the maximum ABOVE the limit, so the limit
                # itself sits on the falling side. Ramping monotonically to the
                # limit makes the limit the peak by construction, which reads as a
                # heavy band right on the crease.
                d = -offset.z / crease_span
                if d <= peak_depth:
                    r = d / peak_depth if peak_depth > 0.0 else 1.0
                    vertical = upper_scale + (1.0 - upper_scale) * (
                        3.0 * r * r - 2.0 * r * r * r)
                else:
                    tail = lower_limit_overshoot - peak_depth
                    if tail <= 0.0:
                        continue
                    b = (d - peak_depth) / tail
                    if b > 1.0:
                        continue
                    vertical = 1.0 - (3.0 * b * b - 2.0 * b * b * b)
        else:
            reach = vertical_reach[0] if offset.z > 0.0 else vertical_reach[1]
            span = radius * reach
            if span <= 0.0:
                continue
            a = abs(offset.z) / span
            if a > 1.0:
                continue
            vertical = 1.0 - (3.0 * a * a - 2.0 * a * a * a)
        if vertical <= 0.0:
            continue

        # --- horizontal ---
        horizontal_distance = math.sqrt(offset.x * offset.x + offset.y * offset.y)
        if horizontal_distance > radius:
            continue
        t = horizontal_distance / radius
        # A softer horizontal edge BELOW the tail only. What reads as a hard edge is
        # a narrow transition band, not the curve shape - smoothstep is already flat
        # at both ends - so the fix is to widen the band, which means shrinking the
        # plateau. Above the tail it is left alone; below it eases toward
        # `plateau_below` (0.0 = the ramp spans the whole radius).
        #
        # Blended BY DEPTH rather than switched at z = 0, or the two plateaus would
        # disagree at mid radius and leave a seam right along the tail's height.
        effective_plateau = plateau
        if plateau_below is not None and offset.z < 0.0 and crease_span > 0.0:
            pd = max(0.0, min(1.0, -offset.z / crease_span))
            pd = 3.0 * pd * pd - 2.0 * pd * pd * pd
            effective_plateau = plateau + (plateau_below - plateau) * pd
        if effective_plateau > 0.0 and t <= effective_plateau:
            horizontal = 1.0
        else:
            u = ((t - effective_plateau) / (1.0 - effective_plateau)
                 if effective_plateau < 1.0 else 1.0)
            u = max(0.0, min(1.0, u))
            horizontal = 1.0 - (3.0 * u * u - 2.0 * u * u * u)
        if horizontal <= 0.0:
            continue

        if forward_only and (v.co - centre).dot(axis) <= 0.0:
            continue

        falloff = horizontal * vertical
        if falloff <= 0.0:
            continue
        for g in v.groups:
            if g.group in source_indices and g.weight > 0.0:
                samples.append((v.index, source_indices[g.group], g.weight,
                                g.weight * max_weight * falloff))

    # Each source is reduced by its OWN take, but the target is written ONCE with
    # the SUM. Writing per sample would REPLACE the target repeatedly on any vertex
    # that has several sources, keeping only the last take while every source had
    # already been debited - weight would vanish. Harmless while there was one
    # source; a real bug the moment the thighs were added alongside pelvis.
    moved = 0.0
    per_source = {}
    takes = {}
    for v_index, source_group, weight, take in samples:
        source_group.add([v_index], weight - take, 'REPLACE')
        takes[v_index] = takes.get(v_index, 0.0) + take
        per_source[source_group.name] = per_source.get(source_group.name, 0.0) + take
        moved += take
    for v_index, total_take in takes.items():
        target.add([v_index], total_take, 'REPLACE')

    breakdown = ", ".join("%s %.3f" % (n, w) for n, w in
                          sorted(per_source.items(), key=lambda kv: -kv[1]))
    print("  jiggle '{}': {} verts borrowed {:.4f} (radius {:.3f}, max {:.2f}{}{}{})"
          .format(joint_name, len(takes), moved, radius, max_weight,
                  ", front only" if forward_only else "",
                  ", side %+d" % side_sign if side_sign else "",
                  ", reclaimed %d" % len(reclaimed) if reclaimed else ""))
    print("      from: {}".format(breakdown or "nothing"))
    return (created, len(takes), moved)


def setupCyclopsBone(mesh_object, armature_object, parent_name="head",
                     bone_name="cyclops_joint01", end_name="cyclops_end",
                     length=0.04, end_length=0.02):
    """
    Aim helper for the eyes: one bone between them, on the skin surface.

    Intended to be pointed at a look-at target, with lEye and rEye taking their
    rotation from it. NO WEIGHTS - it deforms nothing and never should.

    HEAD comes from cyclops_joint01_base, a surface point between the eyes above the
    nose. Deliberately not the midpoint of lEye/rEye, which sit inside the skull -
    this bone is meant to be seen, and a helper buried in the head is useless.

    DIRECTION does come from the eye bones, averaged. That is a different question
    from position: the gaze axis is exactly what the eye bones already encode, so
    inheriting it means the helper points where the eyes point on any figure. Falls
    back to world forward (-Y) if they are missing.

    use_deform is ON despite there being no weights - the FBX writer runs with
    use_armature_deform_only=True and drops bones by that flag, so without it the
    helper never reaches Unreal. Same trap as nipple_joint and the fishing chain.

    NOTE the constraints themselves are Unreal-side work. Blender constraints do not
    survive FBX export, so this only places the scaffold; the aiming and the
    copy-rotation belong in Control Rig.

    Also note: both eyes copying ONE bone's rotation gives PARALLEL gaze, not
    convergence. Real convergence needs a per-eye yaw offset of opposite sign, ideally
    driven by target distance. Fine for distant targets, visibly wall-eyed up close.

    The _end stub exists for the same reason as stomach_end and butt_end: Unreal
    draws a childless bone as a nub rather than a bone, and this one is meant to be
    looked at. It carries no weight either, and needs its own use_deform - Blender
    only spares a non-deforming bone when it has a DEFORMING child, which a leaf
    never has.

    Returns the created bone names, or [].
    """
    if mesh_object is None or mesh_object.type != 'MESH':
        print("setupCyclopsBone: no mesh given")
        return []
    if armature_object is None or armature_object.type != 'ARMATURE':
        print("setupCyclopsBone: no armature given")
        return []

    indices = list(cyclops_joint01_base)
    if max(indices) >= len(mesh_object.data.vertices):
        print("setupCyclopsBone: needs index {} but the mesh has {} - wrong topology, "
              "skipped".format(max(indices), len(mesh_object.data.vertices)))
        return []
    position = getCenter(indices, mesh_object)

    created = []
    token = _beginEditBones(armature_object)
    try:
        ebones = armature_object.data.edit_bones
        parent = ebones.get(parent_name)
        if parent is None:
            print("setupCyclopsBone: parent '{}' not in the rig - skipped"
                  .format(parent_name))
            return []

        forward = Vector((0.0, 0.0, 0.0))
        for eye_name in ("lEye", "rEye"):
            eye = ebones.get(eye_name)
            if eye is not None and (eye.tail - eye.head).length > 1e-6:
                forward += (eye.tail - eye.head).normalized()
        if forward.length < 1e-6:
            forward = Vector((0.0, -1.0, 0.0))     # figure forward, see the docstring
            print("  cyclop: no usable lEye/rEye - falling back to world forward")
        forward = forward.normalized()

        for name in (end_name, bone_name):          # leaf first, never orphan
            old = ebones.get(name)
            if old is not None:
                ebones.remove(old)

        eb = ebones.new(bone_name)
        eb.head = position
        eb.tail = position + forward * length
        eb.roll = parent.roll
        eb.use_connect = False
        eb.use_deform = True
        eb.parent = parent

        end = ebones.new(end_name)
        end.head = eb.tail.copy()
        end.tail = eb.tail + forward * end_length
        end.roll = eb.roll
        end.use_connect = False
        end.use_deform = True       # see the docstring - a leaf needs its own flag
        end.parent = eb
        created = [eb.name, end.name]
    finally:
        _endEditBones(token)

    if not created:
        return []

    if bpy.context.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    for name in created:
        if mesh_object.vertex_groups.get(name) is None:
            mesh_object.vertex_groups.new(name=name)  # empty, keeps group/bone parity

    print("setupCyclopsBone: {} at {} off '{}', pointing {} ({:.3f} + {:.3f} long)"
          .format(created, indices, parent_name,
                  tuple(round(c, 3) for c in forward), length, end_length))
    return created


def setBoneTailToVertices(mesh_object, armature_object, bone_name, vertex_indices,
                          min_length=1e-5):
    """
    Aim a bone at a mesh location by moving its tail onto it.

    Takes a LIST of vertex indices and averages them through getCenter, matching
    every other consumer of the vertex tables - a single-element list is fine and
    is how lower_jaw_tail is expressed. Indices themselves NEVER appear at a call
    site: they live in difeomorphic_workflow_init_custom_vertex_indices.py so that
    supporting another figure (G3M, G8F, G9) is a matter of swapping that module,
    not hunting hardcoded numbers through the pipeline.

    For bones whose direction is anatomical rather than structural - lowerJaw wants
    to point at the chin, and no parent/child relationship expresses that. Head,
    parenting and length-to-children are untouched; only the tail moves.

    Object-local coordinates, matching getCenter and the jiggle bones. Sound only
    because the builder creates "Armature" at the origin and the body sits there
    too - the same assumption the rest of this module makes.

    NOTE the roll number is left alone, so it now means a different orientation in
    world space: roll is measured against a frame built from the bone's OWN
    direction, which just changed. Nothing in blender_perfect_roll_deltas covers
    lowerJaw, so it keeps its Daz roll either way, but re-check if the jaw's axes
    start looking wrong.

    Returns (moved, degrees_turned) - moved is False if it could not be done.
    """
    if mesh_object is None or mesh_object.type != 'MESH':
        print("  tail-to-vertex: no mesh given")
        return (False, 0.0)
    if armature_object is None or armature_object.type != 'ARMATURE':
        print("  tail-to-vertex: no armature given")
        return (False, 0.0)
    if not vertex_indices:
        print("  tail-to-vertex: '{}' given no vertices - skipped".format(bone_name))
        return (False, 0.0)
    needed = max(vertex_indices)
    if needed >= len(mesh_object.data.vertices):
        print("  tail-to-vertex: '{}' needs index {} but the mesh has {} - wrong "
              "topology, skipped".format(bone_name, needed,
                                         len(mesh_object.data.vertices)))
        return (False, 0.0)

    target = getCenter(list(vertex_indices), mesh_object)

    turned = 0.0
    token = _beginEditBones(armature_object)
    try:
        eb = armature_object.data.edit_bones.get(bone_name)
        if eb is None:
            print("  tail-to-vertex: '{}' not in the rig - skipped".format(bone_name))
            return (False, 0.0)
        before = eb.tail - eb.head
        after = target - eb.head
        if after.length < min_length:
            print("  tail-to-vertex: {} sits on '{}' head - skipped"
                  .format(list(vertex_indices), bone_name))
            return (False, 0.0)
        if before.length >= min_length:
            turned = math.degrees(before.normalized().angle(after.normalized()))
        eb.tail = target
    finally:
        _endEditBones(token)

    print("  tail-to-vertex: '{}' tail -> {}, turned {:.3f} deg, length {:.4f}"
          .format(bone_name, list(vertex_indices), turned, after.length))
    return (True, turned)


def setupStomachBone(mesh_object, armature_object, parent_name="spine_02",
                     source_groups=("spine_02",), radius=0.16, max_weight=0.35,
                     forward_only=True, end_length=0.02):
    """
    Belly jiggle bone: stomach_joint01 -> stomach_end, off spine_02.

    Central, so no side test. Borrows from spine_02, which is what owns the belly.
    See _buildJiggleBone for the mechanics and the export/idempotency notes.
    """
    created, touched, moved = _buildJiggleBone(
        mesh_object, armature_object, "stomach_joint01", "stomach_end",
        stomach_base, stomach_top, parent_name, source_groups,
        radius, max_weight, forward_only=forward_only, side_sign=None,
        end_length=end_length)
    print("setupStomachBone: {}".format(created or "nothing built"))
    return (created, touched, moved)


def setupButtBones(mesh_object, armature_object, parent_name="pelvis",
                   source_groups=("pelvis", "thigh.{side}",
                                  "thigh_twist_01.{side}"),
                   radius=0.22, max_weight=0.50,
                   forward_only=True, end_length=0.02,
                   vertical_reach=(0.55, 1.25), lower_fullness=0.0,
                   lower_limit_overshoot=1.55, plateau=0.20, plateau_below=0.0,
                   upper_scale=0.55, peak_depth=0.45):
    """
    Glute jiggle bones: butt_joint01.L/.R -> butt_end.L/.R, off pelvis.

    PARENTED TO pelvis, not thigh and not spine_01. The glutes originate on the
    ilium and sacrum - they do not rotate with the femur, they are compressed and
    stretched as it moves past them, and that compression is the ordinary skin
    weights' job. On thigh the bone would be thrown around by every leg swing. On
    spine_01 it would pick up the lumbar bend as well, since spine_01 is a child of
    pelvis. Walking pelvis bob and tilt is exactly the input the physics wants.

    BORROWS PER SIDE from pelvis AND the thigh, "{side}" being substituted at
    call time. pelvis alone is not enough, and the screenshot showed why: over
    the butt surface and flank verts pelvis holds 4.109 of 6.000 (68%), but
    those verts are all up at the cheek apex. Down at the gluteal fold pelvis
    has faded out and thigh.L / thigh_twist_01.L own the region - and since the
    borrow is source_weight * max_weight * falloff, there was nothing there to
    take, however good the falloff. That is why the crease stayed near zero
    while the apex went green.

    SIDE TEST IS LOAD BEARING here in a way it is not for the stomach. Both sides
    borrow from the SAME pelvis group, so without it an overlapping radius lets
    both claim a vertex and the second REPLACE clobbers the first. .L is +x and .R
    is -x, matching the legacy extra_bones_butt.json head positions.
    """
    # Defined in difeomorphic_workflow_init_custom_vertex_indices.py alongside the
    # other sets. Looked up rather than imported by name so the behaviour simply
    # falls back to the plain radius while they are absent.
    crease = {"L": globals().get("butt_crease_L"),
              "R": globals().get("butt_crease_R")}
    results = []
    for side, base, top, sign in (("L", butt_base_L, butt_top_L, 1.0),
                                  ("R", butt_base_R, butt_top_R, -1.0)):
        results.append(_buildJiggleBone(
            mesh_object, armature_object,
            "butt_joint01.{}".format(side), "butt_end.{}".format(side),
            base, top, parent_name,
            [g.format(side=side) for g in source_groups],
            radius, max_weight, forward_only=forward_only, side_sign=sign,
            end_length=end_length, vertical_reach=vertical_reach,
            lower_fullness=lower_fullness,
            lower_limit_indices=crease.get(side),
            lower_limit_overshoot=lower_limit_overshoot, plateau=plateau,
            plateau_below=plateau_below,
            upper_scale=upper_scale, peak_depth=peak_depth))
    created = [n for c, _t, _m in results for n in c]
    print("setupButtBones: {}".format(created or "nothing built"))
    return results


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
