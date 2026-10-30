import json
import math
import os

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

# High heel pose: from a heeled armature's JSON (Export Edit Bones of a Manny FULL run on the figure
# wearing the shoes) to a Pose Library pose on the default Armature, and from that pose to the numbers
# Unreal's UVersaHeelData wants (BoneOverrides + PelvisLift), stamped on the shoe's exported LODs.

# On the shoe mesh: the name of the Pose Library pose that is its heel pose. Not exported (stripped
# from the LODs); the computed numbers go out as VXMOD_HEEL_POSE_PROP instead.
HEEL_POSE_PROP = "vx_heel_pose"
# Stamped on every exported LOD of a garment with a heel pose (FBX custom property -> package metadata
# "FBX.mesh_LOD<n>.vxmod_heel_pose"). JSON in UVersaHeelData's own field names, so the Unreal side can
# hand it to FJsonObjectConverter: {"BoneOverrides": [{"BoneName", "Rotation": {"Pitch", "Yaw", "Roll"},
# "Translation": {"X", "Y", "Z"}}], "PelvisLift"} - degrees, cm, bone space as ApplyOverrideToLocal reads it.
VXMOD_HEEL_POSE_PROP = "vxmod_heel_pose"
HEEL_POSE_PREFIX = "HH_"

# A bone turned or moved less than this counts as unchanged (float noise from the JSON's 6 decimals).
MIN_ANGLE_DEGREES = 0.05
MIN_MOVE = 5e-4         # Blender units (metres on a Manny FULL rig)

# Unreal's FBX import mirrors Y (FFbxDataConverter: positions (x, -y, z), quaternions (x, -y, z, -w)),
# so a bone-local rotation D arrives as MIRROR_Y * D * MIRROR_Y and a local offset as MIRROR_Y * t.
MIRROR_Y = Matrix(((1.0, 0.0, 0.0), (0.0, -1.0, 0.0), (0.0, 0.0, 1.0)))


def heelPoseNameForJson(filepath):
    """HH_<the shoe's folder>: Armature_HH.json sits in the shoe's own folder."""
    folder = os.path.basename(os.path.dirname(os.path.abspath(bpy.path.abspath(filepath))))
    return HEEL_POSE_PREFIX + (folder or os.path.splitext(os.path.basename(filepath))[0])


def armatureRestMatricesFromJson(filepath):
    """matrix_local of every bone in an edit bones JSON (name, head, tail, roll in degrees), built by
    Blender itself on a temporary armature, which is removed again. OBJECT mode in, OBJECT mode out."""
    with open(bpy.path.abspath(filepath)) as f:
        bones_json = json.load(f)
    scene = bpy.context.scene
    data = bpy.data.armatures.new("_vx_heel_tmp")
    ob = bpy.data.objects.new("_vx_heel_tmp", data)
    scene.objects.link(ob)
    previous = scene.objects.active
    scene.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    for b in bones_json:
        eb = data.edit_bones.new(b["name"])
        eb.head = Vector([float(v) for v in b["head"]])
        eb.tail = Vector([float(v) for v in b["tail"]])
        eb.roll = math.radians(float(b["roll"]))
    bpy.ops.object.mode_set(mode='OBJECT')
    mats = dict((bone.name, bone.matrix_local.copy()) for bone in data.bones)
    scene.objects.unlink(ob)
    bpy.data.objects.remove(ob)
    bpy.data.armatures.remove(data)
    scene.objects.active = previous
    return mats


def _isMoved(matrix_basis):
    loc, rot, _ = matrix_basis.decompose()
    return math.degrees(rot.angle) > MIN_ANGLE_DEGREES or loc.length > MIN_MOVE


def _removePoseKeys(action, frame):
    """Every key the pose library holds at frame, so a re-load does not keep a bone the new pose left out."""
    for fcurve in action.fcurves:
        for i in reversed(range(len(fcurve.keyframe_points))):
            if abs(fcurve.keyframe_points[i].co.x - frame) < 0.5:
                fcurve.keyframe_points.remove(fcurve.keyframe_points[i])


def loadHeelPoseFromJson(armature_object, filepath, pose_name):
    """Pose armature_object so every bone sits where the heeled armature has it at rest (armature
    space, parents first), keep only the bones that moved, store that as pose_name in the armature's
    Pose Library (replacing a pose of that name), then put the armature back in its rest pose.

    Returns [(bone name, matrix_basis)] of the posed bones."""
    scene = bpy.context.scene
    if bpy.context.object is not None and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    hh_mats = armatureRestMatricesFromJson(filepath)

    scene.objects.active = armature_object
    armature_object.select = True
    bpy.ops.object.mode_set(mode='POSE')
    for pb in armature_object.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    scene.update()

    # pb.matrix (armature space) is solved against the parent's evaluated pose: one level at a time.
    levels = {}
    for bone in armature_object.data.bones:
        levels.setdefault(len(bone.parent_recursive), []).append(bone.name)
    for level in sorted(levels):
        for name in levels[level]:
            if name in hh_mats:
                armature_object.pose.bones[name].matrix = hh_mats[name]
        scene.update()

    posed = []
    for pb in armature_object.pose.bones:
        if _isMoved(pb.matrix_basis):
            posed.append((pb.name, pb.matrix_basis.copy()))
        else:
            pb.matrix_basis = Matrix.Identity(4)
    scene.update()

    names = set(name for name, _ in posed)
    for bone in armature_object.data.bones:
        bone.select = bone.name in names
    if armature_object.pose_library is None:
        bpy.ops.poselib.new()
    library = armature_object.pose_library
    marker = library.pose_markers.get(pose_name)
    if marker is not None:
        frame = marker.frame
        _removePoseKeys(library, frame)
    else:
        frame = max([m.frame for m in library.pose_markers] + [0]) + 1
    if posed:
        # Replaces the marker at that frame (and its name) rather than adding a second one.
        bpy.ops.poselib.pose_add(frame=frame, name=pose_name)

    for pb in armature_object.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    scene.update()
    bpy.ops.object.mode_set(mode='OBJECT')
    return posed


def readPoseLibraryPose(armature_object, pose_name):
    """{bone name: matrix_basis} of a Pose Library pose, read from its keys - the scene is not touched.
    None when the armature has no pose of that name."""
    library = armature_object.pose_library
    marker = library.pose_markers.get(pose_name) if library is not None else None
    if marker is None:
        return None
    channels = {}
    for fcurve in library.fcurves:
        path = fcurve.data_path
        if not path.startswith('pose.bones["'):
            continue
        bone_name, _, prop = path[len('pose.bones["'):].partition('"].')
        channels.setdefault(bone_name, {}).setdefault(prop, {})[fcurve.array_index] = fcurve.evaluate(marker.frame)

    basis = {}
    for bone_name, props in channels.items():
        pb = armature_object.pose.bones.get(bone_name)
        if pb is None:
            continue
        loc = props.get("location", {})
        scale = props.get("scale", {})
        mat_loc = Matrix.Translation(Vector([loc.get(i, 0.0) for i in range(3)]))
        mat_scale = Matrix.Identity(4)
        for i in range(3):
            mat_scale[i][i] = scale.get(i, 1.0)
        if "rotation_quaternion" in props:
            q = props["rotation_quaternion"]
            mat_rot = Quaternion([q.get(0, 1.0), q.get(1, 0.0), q.get(2, 0.0), q.get(3, 0.0)]).normalized().to_matrix().to_4x4()
        elif "rotation_euler" in props:
            e = props["rotation_euler"]
            order = pb.rotation_mode if pb.rotation_mode in ('XYZ', 'XZY', 'YXZ', 'YZX', 'ZXY', 'ZYX') else 'XYZ'
            mat_rot = Euler([e.get(i, 0.0) for i in range(3)], order).to_matrix().to_4x4()
        else:
            mat_rot = Matrix.Identity(4)
        basis[bone_name] = mat_loc * mat_rot * mat_scale
    return basis


def posedArmatureMatrices(armature_object, basis):
    """Armature-space matrix of every bone with the given matrix_basis per bone (missing = rest),
    the plain parent chain: no constraints, every bone inheriting rotation and scale."""
    out = {}
    # data.bones is in creation order, and Manny FULL creates children before some parents.
    for bone in sorted(armature_object.data.bones, key=lambda b: len(b.parent_recursive)):
        local = basis.get(bone.name, Matrix.Identity(4))
        if bone.parent is None:
            out[bone.name] = bone.matrix_local * local
        else:
            rel = bone.parent.matrix_local.inverted() * bone.matrix_local
            out[bone.name] = out[bone.parent.name] * rel * local
    return out


def _ueRotator(quat):
    """FQuat::Rotator: (Pitch, Yaw, Roll) in degrees of the quaternion (w, x, y, z)."""
    w, x, y, z = quat.w, quat.x, quat.y, quat.z
    singularity = z * x - w * y
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, 2.0 * singularity))))
    yaw = math.degrees(math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z)))
    roll = math.degrees(math.atan2(-2.0 * (w * x + y * z), 1.0 - 2.0 * (x * x + y * y)))
    return pitch, yaw, roll


def _rotation(matrix):
    return matrix.to_3x3().normalized()


def heelPoseForUnreal(armature_object, armature_clone, pose_name):
    """The heel pose as UVersaHeelData wants it, for the bones of armature_clone in their EXPORT frames.

    Call it on the export clone after its bones are oriented for Unreal and before anything applies a
    transform or renames them: the clone's bone frames then live in the same armature space as
    armature_object's, which holds the Pose Library pose. Each posed bone gets its rotation relative to
    its parent (pose-world turn W, Delta = F^T * W_parent^-1 * W * F in the bone's export frame F, then
    mirrored into Unreal), and a translation where its head moved relative to the parent (toes: Daz
    hangs them off the metatarsals, Manny off the ball). The root's (pelvis) upward move is PelvisLift.

    Returns (dict, report lines), or (None, report lines) when the armature has no such pose."""
    from .exporter_unreal import _unreal_bone_name

    basis = readPoseLibraryPose(armature_object, pose_name)
    if basis is None:
        return None, ["heel pose: '{}' has no Pose Library pose '{}'".format(armature_object.name, pose_name)]
    posed = posedArmatureMatrices(armature_object, basis)
    bones = armature_object.data.bones
    world_rotation = _rotation(armature_object.matrix_world)
    to_cm = 100.0 * armature_object.matrix_world.to_scale().x

    def turn(name):
        return _rotation(posed[name]) * _rotation(bones[name].matrix_local).inverted()

    overrides = []
    pelvis_lift = 0.0
    report = []
    for bone in sorted(bones, key=lambda b: len(b.parent_recursive)):
        name = bone.name
        if name not in basis or not _isMoved(basis[name]):
            continue
        export_bone = armature_clone.data.bones.get(name)
        if export_bone is None:
            report.append("  {} is posed but not exported - skipped".format(name))
            continue
        parent = bone.parent
        w_parent = turn(parent.name) if parent is not None else Matrix.Identity(3)
        frame = _rotation(export_bone.matrix_local)
        delta = MIRROR_Y * (frame.transposed() * w_parent.inverted() * turn(name) * frame) * MIRROR_Y
        pitch, yaw, roll = _ueRotator(delta.to_quaternion())

        translation = Vector((0.0, 0.0, 0.0))
        if parent is None:
            move = world_rotation * (posed[name].translation - bone.matrix_local.translation) * to_cm
            pelvis_lift = move.z
            if Vector((move.x, move.y)).length > 0.05:
                report.append("  {} also moves {:.2f} cm sideways - not in PelvisLift, left out"
                              .format(name, Vector((move.x, move.y)).length))
        else:
            export_parent = armature_clone.data.bones.get(parent.name)
            parent_frame = _rotation(export_parent.matrix_local) if export_parent else Matrix.Identity(3)
            rest = parent_frame.transposed() * (bone.matrix_local.translation - parent.matrix_local.translation)
            now = (w_parent * parent_frame).transposed() * (posed[name].translation - posed[parent.name].translation)
            if (now - rest).length > MIN_MOVE:
                translation = MIRROR_Y * (now - rest) * to_cm

        rotated = abs(pitch) > 1e-4 or abs(yaw) > 1e-4 or abs(roll) > 1e-4
        if parent is None and not rotated:
            continue        # the pelvis only lifts: that is PelvisLift, not an override
        overrides.append({
            "BoneName": _unreal_bone_name(name),
            "Rotation": {"Pitch": round(pitch, 4), "Yaw": round(yaw, 4), "Roll": round(roll, 4)},
            "Translation": {"X": round(translation.x, 4), "Y": round(translation.y, 4), "Z": round(translation.z, 4)},
        })
        report.append("  {:<24} P {:9.3f}  Y {:9.3f}  R {:9.3f}   T {:7.3f} {:7.3f} {:7.3f} cm".format(
            _unreal_bone_name(name), pitch, yaw, roll, translation.x, translation.y, translation.z))

    report.insert(0, "heel pose '{}': {} bone override(s), PelvisLift {:.3f} cm".format(
        pose_name, len(overrides), pelvis_lift))
    data = {"Version": 1, "Pose": pose_name, "PelvisLift": round(pelvis_lift, 4), "BoneOverrides": overrides}
    return data, report


def heelPoseMetadata(source_object, armature_object, armature_clone):
    """The VXMOD_HEEL_POSE_PROP string for an exported garment, or None (no heel pose on it, or the
    armature lost the pose - that one is reported)."""
    pose_name = source_object.get(HEEL_POSE_PROP, "")
    if not pose_name:
        return None
    data, report = heelPoseForUnreal(armature_object, armature_clone, pose_name)
    for line in report:
        print(line)
    if data is None:
        return None
    return json.dumps(data, separators=(",", ":"))
