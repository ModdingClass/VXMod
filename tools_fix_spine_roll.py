import bpy
import math

# The midline bones lie in the figure's mirror plane, so their BlenderPerfect roll is 0: X points
# straight across the body and the UE5 export puts Z (the hinge) across too. Manny FULL leaves a
# little roll on them (aimSpineAtChildren turns each spine bone onto its child after Diffeomorphic
# set the roll, and a roll is measured against the bone's own direction), which twists the spine
# slightly to one side in Unreal.
# Roll 0 alone is not enough: Blender's roll 0 is the least turn from +Y to the bone, so a bone that
# leans sideways comes out twisted by about its lean. The Daz joints sit up to 0.005 cm off x = 0
# (neck_02 leaned 0.037 deg and twisted 0.040 deg in Unreal, 2026-10-30), so heads and tails go onto
# x = 0 first. Armature space: the figure's mirror plane is the armature's x = 0.
MIDLINE_BONES = ('spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05',
                 'neck_01', 'neck_02', 'head')
# Centred, roll kept: the pelvis frame already came out exact (0.0000 deg twist / lean in Unreal,
# 2026-10-30) and its head and tail share one x, so moving both keeps its direction. Its head sat
# 0.0026 cm off x = 0.
CENTRE_ONLY_BONES = ('pelvis',)


def findArmature(ob):
    """The armature itself, or the one a selected mesh is deformed by / parented to; None if neither."""
    if ob is None:
        return None
    if ob.type == 'ARMATURE':
        return ob
    for mod in getattr(ob, 'modifiers', ()):
        if mod.type == 'ARMATURE' and mod.object is not None:
            return mod.object
    if ob.parent is not None and ob.parent.type == 'ARMATURE':
        return ob.parent
    return None


def centreMidlineBones(arm, names=MIDLINE_BONES, centre_only=CENTRE_ONLY_BONES):
    """Put the pelvis, spine, neck and head edit bones on the centre line: head and tail x = 0;
    roll 0 for names, roll kept for centre_only.

    Call with arm active. Returns ([(bone, old roll in degrees, largest x moved, roll zeroed)],
    [names not in the rig]). Only these bones' joints move (by their x); the mesh does not."""
    prev_mode = arm.mode
    if prev_mode != 'EDIT':
        bpy.ops.object.mode_set(mode='EDIT')
    ebones = arm.data.edit_bones
    changed = []
    missing = []
    for name in tuple(centre_only) + tuple(names):
        eb = ebones.get(name)
        if eb is None:
            missing.append(name)
            continue
        moved = max(abs(eb.head.x), abs(eb.tail.x))
        old_roll = math.degrees(eb.roll)
        eb.head.x = 0.0
        eb.tail.x = 0.0
        zeroed = name not in centre_only
        if zeroed:
            eb.roll = 0.0
        changed.append((name, old_roll, moved, zeroed))
    if prev_mode != 'EDIT':
        bpy.ops.object.mode_set(mode=prev_mode)
    return changed, missing


class ARMATURE_OT_fix_spine_midline(bpy.types.Operator):
    ''''''
    bl_idname = "vxmod.fix_spine_midline"
    bl_label = "Centre spine"
    bl_description = "Put pelvis, spine_01-05, neck_01/02 and head on the centre line: joints at x 0, roll 0 (pelvis keeps its roll). Select the armature or the body"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        arm = findArmature(context.active_object)
        if arm is None:
            self.report({'WARNING'}, "Select the armature or its body mesh first.")
            return {'CANCELLED'}
        previous = context.scene.objects.active
        if previous is not None and previous is not arm and previous.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        context.scene.objects.active = arm
        changed, missing = centreMidlineBones(arm)
        context.scene.objects.active = previous
        if not changed:
            self.report({'WARNING'}, "No spine, neck or head bones in {}.".format(arm.name))
            return {'CANCELLED'}
        for name, old, moved, zeroed in changed:
            print("Centre spine: {:<10} roll {:+.4f} {}, x moved {:.6f}".format(
                name, old, "-> 0 deg" if zeroed else "deg (kept)", moved))
        worst_roll = max((c for c in changed if c[3]), key=lambda c: abs(c[1]),
                         default=(changed[0][0], 0.0))
        worst_move = max(changed, key=lambda c: c[2])
        message = ("Centre spine: {} bone(s) on {}, largest roll {} {:+.3f} deg, "
                   "largest x move {} {:.6f}").format(len(changed), arm.name, worst_roll[0],
                                                      worst_roll[1], worst_move[0], worst_move[2])
        if missing:
            message += ", not found: " + ', '.join(missing)
        print(message)
        self.report({'WARNING'} if missing else {'INFO'}, message)
        return {'FINISHED'}
