#last value in the array is the roll override
leg_bones_matching = [
# source bone used for head, source bone used for tail, target bone
["lThighBend", "lThighTwist", "thigh.L",0], ###"lThighBend + lThighTwist"
["rThighBend", "rThighTwist", "thigh.R",0], ###"rThighBend + rThighTwist"

["lShin", "lShin", "calf.L",0],
["rShin", "rShin", "calf.R",0],

["lFoot", "lMetatarsals", "foot.L",0],
["rFoot", "rMetatarsals", "foot.R",0],

["lToe", "lToe", "ball.L",0],
["rToe", "rToe", "ball.R",0],

["lThighTwist", "lThighTwist", "thigh_twist_01.L",0],
["lThighTwist", "lThighTwist", "thigh_twist_02.L",0],
["rThighTwist", "rThighTwist", "thigh_twist_01.R",0],
["rThighTwist", "rThighTwist", "thigh_twist_02.R",0]

]

#last value in the array is the roll override
toe_bones_matching = [
["lBigToe","lBigToe","big_toe_joint01.L"],
["lBigToe_2","lBigToe_2","big_toe_joint02.L"],

["lSmallToe1","lSmallToe1","small_toe1_joint01.L"],
["lSmallToe1_2","lSmallToe1_2","small_toe1_joint02.L"],

["lSmallToe2","lSmallToe2","small_toe2_joint01.L"],
["lSmallToe2_2","lSmallToe2_2","small_toe2_joint02.L"],

["lSmallToe3","lSmallToe3","small_toe3_joint01.L"],
["lSmallToe3_2","lSmallToe3_2","small_toe3_joint02.L"],

["lSmallToe4","lSmallToe4","small_toe4_joint01.L"],
["lSmallToe4_2","lSmallToe4_2","small_toe4_joint02.L"],
#############################################################
["rBigToe","rBigToe","big_toe_joint01.R"],
["rBigToe_2","rBigToe_2","big_toe_joint02.R"],

["rSmallToe1","rSmallToe1","small_toe1_joint01.R"],
["rSmallToe1_2","rSmallToe1_2","small_toe1_joint02.R"],

["rSmallToe2","rSmallToe2","small_toe2_joint01.R"],
["rSmallToe2_2","rSmallToe2_2","small_toe2_joint02.R"],

["rSmallToe3","rSmallToe3","small_toe3_joint01.R"],
["rSmallToe3_2","rSmallToe3_2","small_toe3_joint02.R"],

["rSmallToe4","rSmallToe4","small_toe4_joint01.R"],
["rSmallToe4_2","rSmallToe4_2","small_toe4_joint02.R"]
]

#last value in the array is the roll override
spine_bones_matching = [
# source bone used for head, source bone used for tail, target bone
["pelvis", "pelvis", "pelvis"],
["abdomenLower", "abdomenLower", "spine_01",90],

["abdomenUpper", "abdomenUpper", "spine_02",90],
["chestLower", "chestLower", "spine_03",90],
["chestUpper", "chestUpper", "spine_04",90],

["neckLower", "neckLower", "neck_01",90],
["neckUpper", "neckUpper", "neck_02",90],
["head", "head", "head",90]
]

#redefining the spine bones (current plugin does not support spine editor, so moving bones will create movements later in spines cause no ikhandles and effectors and init data for those matching the new joints)
#last value in the array is the roll override
spine_bones_matching_other = [
# source bone used for head, source bone used for tail, target bone
["head", "head", "head",90]
]


#last value in the array is the roll override
arm_bones_matching = [
["lCollar", "lCollar", "clavicle.L",0],
["rCollar", "rCollar", "clavicle.R",0],

["lShldrBend", "lShldrTwist", "upperarm.L",90],  ### ????", "lShldrBend + lShldrTwist"
["rShldrBend", "rShldrTwist", "upperarm.R",-90],  ### ????", "rShldrBend + rShldrTwist"

["lShldrTwist", "lShldrTwist", "upperarm_twist_01.L",90],
["lShldrTwist", "lShldrTwist", "upperarm_twist_02.L",90],
["rShldrTwist", "rShldrTwist", "upperarm_twist_01.R",-90],
["rShldrTwist", "rShldrTwist", "upperarm_twist_02.R",-90],

["lForearmBend", "lForearmTwist", "lowerarm.L",90],
["rForearmBend", "rForearmTwist", "lowerarm.R",-90],
["lForearmTwist", "lForearmTwist", "lowerarm_twist_01.L",90],
["lForearmTwist", "lForearmTwist", "lowerarm_twist_02.L",90],
["rForearmTwist", "rForearmTwist", "lowerarm_twist_01.R",-90],
["rForearmTwist", "rForearmTwist", "lowerarm_twist_02.R",-90],

["lHand", "lHand", "hand.L",90],
["rHand", "rHand", "hand.R",-90],
]

#last value in the array is the roll override
finger_bones_matching = [

["lThumb1", "lThumb1", "thumb_01.L"],
["lCarpal1", "lCarpal1", "index_metacarpal.L"],
["lCarpal2", "lCarpal2", "middle_metacarpal.L"],
["lCarpal3", "lCarpal3", "ring_metacarpal.L"],
["lCarpal4", "lCarpal4", "pinky_metacarpal.L"],

["lThumb2", "lThumb2", "thumb_02.L"],
["lThumb3", "lThumb3", "thumb_03.L"],

["lIndex1", "lIndex1", "index_01.L"],
["lIndex2", "lIndex2", "index_02.L"],
["lIndex3", "lIndex3", "index_03.L"],

["lMid1", "lMid1", "middle_01.L"],
["lMid2", "lMid2", "middle_02.L"],
["lMid3", "lMid3", "middle_03.L"],

["lRing1", "lRing1", "ring_01.L"],
["lRing2", "lRing2", "ring_02.L"],
["lRing3", "lRing3", "ring_03.L"],

["lPinky1", "lPinky1", "pinky_01.L"],
["lPinky2", "lPinky2", "pinky_02.L"],
["lPinky3", "lPinky3", "pinky_03.L"],

["rThumb1", "rThumb1", "thumb_01.R"],
["rCarpal1", "rCarpal1", "index_metacarpal.R"],
["rCarpal2", "rCarpal2", "middle_metacarpal.R"],
["rCarpal3", "rCarpal3", "ring_metacarpal.R"],
["rCarpal4", "rCarpal4", "pinky_metacarpal.R"],

["rThumb2", "rThumb2", "thumb_02.R"],
["rThumb3", "rThumb3", "thumb_03.R"],

["rIndex1", "rIndex1", "index_01.R"],
["rIndex2", "rIndex2", "index_02.R"],
["rIndex3", "rIndex3", "index_03.R"],

["rMid1", "rMid1", "middle_01.R"],
["rMid2", "rMid2", "middle_02.R"],
["rMid3", "rMid3", "middle_03.R"],

["rRing1", "rRing1", "ring_01.R"],
["rRing2", "rRing2", "ring_02.R"],
["rRing3", "rRing3", "ring_03.R"],

["rPinky1", "rPinky1", "pinky_01.R"],
["rPinky2", "rPinky2", "pinky_02.R"],
["rPinky3", "rPinky3", "pinky_03.R"]
]

#last value in the array is the roll override
bones_matching = [

# source bone used for head, source bone used for tail, target bone

["lThighBend", "lThighTwist", "thigh.L"], ###"lThighBend + lThighTwist"
["rThighBend", "rThighTwist", "thigh.R"], ###"rThighBend + rThighTwist"

["lShin", "lShin", "calf.L"],
["rShin", "rShin", "calf.R"],

["lFoot", "lFoot", "foot.L"],
["rFoot", "rFoot", "foot.R"],

["lToe", "lToe", "ball.L"],
["rToe", "rToe", "ball.R"],

["pelvis", "pelvis", "root"],
["abdomenLower", "abdomenLower", "spine_02"],

["abdomenUpper", "abdomenUpper", "spine_03"],
["chestLower", "chestLower", "spine_04"], ####so and so , maybe I need a mix with joint_03
["chestUpper", "chestUpper", "spine_05"],

["neckLower", "neckLower", "neck_01"],
["neckUpper", "neckUpper", "neck_02"],
["head", "head", "head"],

["lCollar", "lCollar", "clavicle.L"],
["rCollar", "rCollar", "clavicle.R"],

["lHand", "lHand", "hand.L"],
["rHand", "rHand", "hand.R"],

["lThumb1", "lThumb1", "thumb_01.L"],
["lCarpal1", "lCarpal1", "index_metacarpal.L"],
["lCarpal2", "lCarpal2", "middle_metacarpal.L"],
["lCarpal3", "lCarpal3", "ring_metacarpal.L"],
["lCarpal4", "lCarpal4", "pinky_metacarpal.L"],

["lThumb2", "lThumb2", "thumb_02.L"],
["lThumb3", "lThumb3", "thumb_03.L"],

["lIndex1", "lIndex1", "index_01.L"],
["lIndex2", "lIndex2", "index_02.L"],
["lIndex3", "lIndex3", "index_03.L"],

["lMid1", "lMid1", "middle_01.L"],
["lMid2", "lMid2", "middle_02.L"],
["lMid3", "lMid3", "middle_03.L"],

["lRing1", "lRing1", "ring_01.L"],
["lRing2", "lRing2", "ring_02.L"],
["lRing3", "lRing3", "ring_03.L"],

["lPinky1", "lPinky1", "pinky_01.L"],
["lPinky2", "lPinky2", "pinky_02.L"],
["lPinky3", "lPinky3", "pinky_03.L"],

["rThumb1", "rThumb1", "thumb_01.R"],
["rCarpal1", "rCarpal1", "index_metacarpal.R"],
["rCarpal2", "rCarpal2", "middle_metacarpal.R"],
["rCarpal3", "rCarpal3", "ring_metacarpal.R"],
["rCarpal4", "rCarpal4", "pinky_metacarpal.R"],

["rThumb2", "rThumb2", "thumb_02.R"],
["rThumb3", "rThumb3", "thumb_03.R"],

["rIndex1", "rIndex1", "index_01.R"],
["rIndex2", "rIndex2", "index_02.R"],
["rIndex3", "rIndex3", "index_03.R"],

["rMid1", "rMid1", "middle_01.R"],
["rMid2", "rMid2", "middle_02.R"],
["rMid3", "rMid3", "middle_03.R"],

["rRing1", "rRing1", "ring_01.R"],
["rRing2", "rRing2", "ring_02.R"],
["rRing3", "rRing3", "ring_03.R"],

["rPinky1", "rPinky1", "pinky_01.R"],
["rPinky2", "rPinky2", "pinky_02.R"],
["rPinky3", "rPinky3", "pinky_03.R"]
]

finger_jointend_bones_parents = [
["thumb_end.L","thumb_03.L"],
["index_end.L","index_03.L"],
["middle_end.L","middle_03.L"],
["ring_end.L","ring_03.L"],
["pinky_end.L","pinky_03.L"],

["thumb_end.R","thumb_03.R"],
["index_end.R","index_03.R"],
["middle_end.R","middle_03.R"],
["ring_end.R","ring_03.R"],
["pinky_end.R","pinky_03.R"]
]

toe_jointend_bones_parents = [
["big_toe_end.L","big_toe_joint02.L"],
["small_toe1_end.L","small_toe1_joint02.L"],
["small_toe2_end.L","small_toe2_joint02.L"],
["small_toe3_end.L","small_toe3_joint02.L"],
["small_toe4_end.L","small_toe4_joint02.L"],

["big_toe_end.R","big_toe_joint02.R"],
["small_toe1_end.R","small_toe1_joint02.R"],
["small_toe2_end.R","small_toe2_joint02.R"],
["small_toe3_end.R","small_toe3_joint02.R"],
["small_toe4_end.R","small_toe4_joint02.R"],
]


###############################################################################
# Daz (Diffeomorphic) -> Manny, matching the DazToUnreal plugin exactly.
#
# Transcribed from DazToUnreal's ConvertToEpicSkeleton rename block
# (DazToUnrealBlueprintUtils.cpp:165-261, the "// G3/G8/G8.1 Renaming" section),
# then translated from Unreal's _l/_r suffix to this project's .L/.R convention.
# 67 entries. Used by alignArmatureFromDifeomorphicToManny().
#
# Differences from the older `bones_matching` list above - deliberate, not oversights:
#   * `hip` -> `spine_01`, so the spine runs abdomenLower->spine_02 .. chestUpper->spine_05.
#     `bones_matching` instead maps pelvis->root and never fills spine_01.
#   * `pelvis` is NOT renamed. It keeps its name and becomes the top-level bone.
#     DazToUnreal parents it to a `root` bone; we do not create one, because the
#     Blender FBX exporter turns the "Armature" object itself into the root bone.
#   * Only ONE twist bone per joint is produced, because G3 only has one.
#     thigh_twist_02, upperarm_twist_02 and lowerarm_twist_01 have no Daz source.
#   * `lForearmTwist` maps to lowerarm_twist_*02*, not _01_ - see the note below.
#
# Bones with no entry here (lPectoral, lMetatarsals, lHeel, face rig, toes, tongue,
# eyes, ...) keep their Daz names, exactly as DazToUnreal leaves them.
###############################################################################
dtu_manny_bones_matching = {
    # Spine  (hip -> spine_01; pelvis keeps its name and becomes the top-level bone)
    "hip": "spine_01",
    "abdomenLower": "spine_02",
    "abdomenUpper": "spine_03",
    "chestLower": "spine_04",
    "chestUpper": "spine_05",

    # Neck
    "neckLower": "neck_01",
    "neckUpper": "neck_02",

    # Legs
    "lThighBend": "thigh.L",
    "lShin": "calf.L",
    "lFoot": "foot.L",
    "lToe": "ball.L",
    "rThighBend": "thigh.R",
    "rShin": "calf.R",
    "rFoot": "foot.R",
    "rToe": "ball.R",

    # Leg twists   - G3 has only ONE per side, so thigh_twist_02.L/R are NOT produced
    "lThighTwist": "thigh_twist_01.L",
    "rThighTwist": "thigh_twist_01.R",

    # Arm twists   - G3 has only ONE per side, so upperarm_twist_02.L/R are NOT produced
    "lShldrTwist": "upperarm_twist_01.L",
    "rShldrTwist": "upperarm_twist_01.R",

    # Forearm twists - DazToUnreal source comment: "The Lower Arm twists are swapped".
    # The single Daz forearm twist fills Epic slot _02_, NOT _01_.
    # lowerarm_twist_01.L/R are NOT produced.
    "lForearmTwist": "lowerarm_twist_02.L",
    "rForearmTwist": "lowerarm_twist_02.R",

    # Arms
    "lCollar": "clavicle.L",
    "lShldrBend": "upperarm.L",
    "lForearmBend": "lowerarm.L",
    "lHand": "hand.L",
    "rCollar": "clavicle.R",
    "rShldrBend": "upperarm.R",
    "rForearmBend": "lowerarm.R",
    "rHand": "hand.R",

    # Left hand   (Carpal numbering: 1=index, 2=middle, 3=ring, 4=pinky)
    "lCarpal1": "index_metacarpal.L",
    "lIndex1": "index_01.L",
    "lIndex2": "index_02.L",
    "lIndex3": "index_03.L",
    "lCarpal2": "middle_metacarpal.L",
    "lMid1": "middle_01.L",
    "lMid2": "middle_02.L",
    "lMid3": "middle_03.L",
    "lCarpal3": "ring_metacarpal.L",
    "lRing1": "ring_01.L",
    "lRing2": "ring_02.L",
    "lRing3": "ring_03.L",
    "lCarpal4": "pinky_metacarpal.L",
    "lPinky1": "pinky_01.L",
    "lPinky2": "pinky_02.L",
    "lPinky3": "pinky_03.L",
    "lThumb1": "thumb_01.L",
    "lThumb2": "thumb_02.L",
    "lThumb3": "thumb_03.L",

    # Right hand
    "rCarpal1": "index_metacarpal.R",
    "rIndex1": "index_01.R",
    "rIndex2": "index_02.R",
    "rIndex3": "index_03.R",
    "rCarpal2": "middle_metacarpal.R",
    "rMid1": "middle_01.R",
    "rMid2": "middle_02.R",
    "rMid3": "middle_03.R",
    "rCarpal3": "ring_metacarpal.R",
    "rRing1": "ring_01.R",
    "rRing2": "ring_02.R",
    "rRing3": "ring_03.R",
    "rCarpal4": "pinky_metacarpal.R",
    "rPinky1": "pinky_01.R",
    "rPinky2": "pinky_02.R",
    "rPinky3": "pinky_03.R",
    "rThumb1": "thumb_01.R",
    "rThumb2": "thumb_02.R",
    "rThumb3": "thumb_03.R",
}


###############################################################################
# Which child continues the chain, for bones that have more than one.
#
# Used by clampBoneLengthsToChildHeads() to decide what a bone's length is
# allowed to reach. Without this, chestUpper -> spine_05 would be clamped against
# lPectoral (which starts lower and nearer) instead of neck_01, leaving the
# upper spine stubby.
#
# Bones with exactly ONE child do not need an entry - that child is used.
# A value of None marks the bone as the end of its chain: its children exist
# (face rig under head, toes under ball) but are not a continuation, so the bone
# is left unclamped.
#
# Names are post-rename, i.e. Manny names for mapped bones and Daz names for the
# ones carried over untouched (lMetatarsals is a real Daz bone between lFoot and
# lToe, and is deliberately not renamed - Epic has no equivalent).
###############################################################################
manny_chain_successors = {
    # --- spine / neck ---------------------------------------------------------
    # Pinned end to end on purpose, not just where a bone is known to have
    # several children. Anything can end up parented into the torso - pectorals,
    # collars, breast helpers, clothing and prop bones - and a single unexpected
    # child is enough to push a spine bone down the "several children, no entry"
    # branch, where it is left UNCLAMPED and renders far too long. Pinning the
    # whole chain makes the clamp target independent of what else hangs off it.
    "pelvis": "spine_01",          # also parents thigh.L / thigh.R
    "spine_01": "spine_02",
    "spine_02": "spine_03",
    "spine_03": "spine_04",
    "spine_04": "spine_05",        # chestLower -> chestUpper
    "spine_05": "neck_01",         # also parents clavicle.L/R and lPectoral/rPectoral
    "neck_01": "neck_02",
    "neck_02": "head",
    "head": None,                  # face rig / eyes / jaw are not a continuation
    # lowerJaw keeps its Daz length. Once lowerTeeth is collapsed the tongue
    # becomes its only surviving child, which would otherwise put lowerJaw on the
    # single-child branch and resize it to reach tongue01 - the tongue is not a
    # continuation of the jaw any more than the face rig is of the head.
    "lowerJaw": None,

    # --- hands / feet ---------------------------------------------------------
    "hand.L": "middle_metacarpal.L",   # middle finger is the natural extension
    "hand.R": "middle_metacarpal.R",
    # A list is tried in order, first match wins. The foot is clamped twice: once when
    # the armature is built, while Daz's lMetatarsals is still in the chain, and again
    # after mergeBonesIntoTargets removes it and reparents ball onto foot.
    "foot.L": ["lMetatarsals", "ball.L"],
    "foot.R": ["rMetatarsals", "ball.R"],
    "ball.L": None,                # toes are not a continuation
    "ball.R": None,

    # --- limbs ----------------------------------------------------------------
    # Two candidates each, and the ORDER matters. The clamp runs three times: when
    # the armature is built and after the collapse, while Daz still has the twist
    # in-chain, and again after setupTwistBones makes the twists leaves. Listing
    # the joint bone first means it wins as soon as it becomes a direct child, and
    # the twist is only used as the fallback beforehand.
    "thigh.L": ["calf.L", "thigh_twist_01.L"],
    "thigh.R": ["calf.R", "thigh_twist_01.R"],
    "calf.L": "foot.L",
    "calf.R": "foot.R",
    "upperarm.L": ["lowerarm.L", "upperarm_twist_01.L"],
    "upperarm.R": ["lowerarm.R", "upperarm_twist_01.R"],
    "lowerarm.L": ["hand.L", "lowerarm_twist_02.L"],
    "lowerarm.R": ["hand.R", "lowerarm_twist_02.R"],
}


###############################################################################
# Non-Manny bones that are KEPT in the VX body, renamed to the VXMod convention.
#
# The Epic mannequin has no toe or breast bones, so DazToUnreal leaves these under
# their Daz names. VXMod wants them, under the <part>_joint<NN>.<side> convention
# already used by toe_bones_matching and breast_weights_matching.
#
# Kept separate from dtu_manny_bones_matching on purpose: that table is a pure
# transcription of the DazToUnreal plugin and should stay verifiable against it.
# Both are merged at use time by getMannyBoneRenameMap().
#
# The face rig is NOT here - it is collapsed into head / lowerJaw instead, see
# face_collapse_rules below.
###############################################################################
manny_extra_bones_matching = {
    # Breasts. pectoral_base is the FIRST link of a chain, not the whole bone:
    # setupPectoralChain cuts it 40/30/30 and adds a nipple handle at the tip, so
    # the finished rig has
    #     pectoral_base -> pectoral_joint01 -> pectoral_joint02 -> nipple_joint
    # The base carries NO weight - it spans the inner 40%, which sits inside the
    # ribcage. joint01 and joint02 are the deforming pair.
    "lPectoral": "pectoral_base.L",
    "rPectoral": "pectoral_base.R",

    # Toes - left
    "lBigToe": "big_toe_joint01.L",
    "lBigToe_2": "big_toe_joint02.L",
    "lSmallToe1": "small_toe1_joint01.L",
    "lSmallToe1_2": "small_toe1_joint02.L",
    "lSmallToe2": "small_toe2_joint01.L",
    "lSmallToe2_2": "small_toe2_joint02.L",
    "lSmallToe3": "small_toe3_joint01.L",
    "lSmallToe3_2": "small_toe3_joint02.L",
    "lSmallToe4": "small_toe4_joint01.L",
    "lSmallToe4_2": "small_toe4_joint02.L",

    # Toes - right
    "rBigToe": "big_toe_joint01.R",
    "rBigToe_2": "big_toe_joint02.R",
    "rSmallToe1": "small_toe1_joint01.R",
    "rSmallToe1_2": "small_toe1_joint02.R",
    "rSmallToe2": "small_toe2_joint01.R",
    "rSmallToe2_2": "small_toe2_joint02.R",
    "rSmallToe3": "small_toe3_joint01.R",
    "rSmallToe3_2": "small_toe3_joint02.R",
    "rSmallToe4": "small_toe4_joint01.R",
    "rSmallToe4_2": "small_toe4_joint02.R",
}


###############################################################################
# Bone-count reduction: the face rig, folded into head and lowerJaw.
#
# EXPLICIT lists rather than a runtime subtree walk, so exactly which bones get
# collapsed is visible here and can be edited without reasoning about hierarchy.
# Move a name out of a list and it survives as its own deform bone.
#
# Generated from the real Diffeomorphic G3F rig
# (custom_json_files/diffeomorphic_g3f/diffeomorphic_g3f.json, 172 bones) as
# exactly the upperFaceRig / lowerFaceRig subtrees, plus the two teeth bones
# added by hand (see the entries at the end of each list).
#
# Hierarchy, for reference:
#   head -> upperFaceRig (46 children)   -> merged into head
#   head -> lowerJaw -> lowerFaceRig (18 children) -> merged into lowerJaw
#   head -> upperTeeth                   -> merged into head      (rigid)
#   head -> lowerJaw -> lowerTeeth       -> merged into lowerJaw  (rigid)
#
# NOT in these lists, and therefore KEPT as deform bones - they hang off head and
# lowerJaw directly, not off the face rigs:
#   lEye, rEye, lEar, rEar                    (children of head)
#   tongue01 -> .. -> tongue04                (was under lowerTeeth; the collapse
#                                              walks tongue01 up onto lowerJaw)
#
# Names are Daz names: this runs BEFORE the Daz -> Manny vertex-group rename.
# Both targets survive that rename untouched - `head` maps to itself, `lowerJaw`
# is in no rename table.
#
# 48 + 20 = 68 bones removed, taking the rig from 172 to 104.
###############################################################################

# 47 bones -> head
face_bones_merged_to_head = [
    # rig root
    "upperFaceRig",

    # brows
    "CenterBrow", "lBrowInner", "lBrowMid", "lBrowOuter", "rBrowInner", "rBrowMid",
    "rBrowOuter",

    # eyelids
    "lEyelidInner", "lEyelidLower", "lEyelidLowerInner", "lEyelidLowerOuter",
    "lEyelidOuter", "lEyelidUpper", "lEyelidUpperInner", "lEyelidUpperOuter",
    "rEyelidInner", "rEyelidLower", "rEyelidLowerInner", "rEyelidLowerOuter",
    "rEyelidOuter", "rEyelidUpper", "rEyelidUpperInner", "rEyelidUpperOuter",

    # squints
    "lSquintInner", "lSquintOuter", "rSquintInner", "rSquintOuter",

    # cheeks
    "lCheekUpper", "rCheekUpper",

    # nose / nostrils
    "MidNoseBridge", "Nose", "lNostril", "rNostril",

    # upper lip
    "LipUpperMiddle", "lLipBelowNose", "lLipUpperInner", "lLipUpperOuter", "rLipBelowNose",
    "rLipUpperInner", "rLipUpperOuter",

    # nasolabial
    "lLipNasolabialCrease", "lNasolabialMiddle", "lNasolabialUpper", "rLipNasolabialCrease",
    "rNasolabialMiddle", "rNasolabialUpper",

    # teeth. NOT part of upperFaceRig - a direct child of head, folded in here
    # deliberately. It is a rigid bone: it never moves relative to head, so its
    # weights on head give identical deformation. Costs the option of animating
    # the upper teeth separately, which nothing in this pipeline does.
    "upperTeeth",
]

# 19 bones -> lowerJaw
face_bones_merged_to_lower_jaw = [
    # rig root
    "lowerFaceRig",

    # cheeks
    "lCheekLower", "rCheekLower",

    # jaw / chin
    "BelowJaw", "Chin", "lJawClench", "rJawClench",

    # lower lip
    "LipBelow", "LipLowerMiddle", "lLipCorner", "lLipLowerInner", "lLipLowerOuter",
    "rLipCorner", "rLipLowerInner", "rLipLowerOuter",

    # nasolabial
    "lNasolabialLower", "lNasolabialMouthCorner", "rNasolabialLower",
    "rNasolabialMouthCorner",

    # teeth. NOT part of lowerFaceRig - a direct child of lowerJaw, folded in
    # here deliberately. Rigid relative to lowerJaw, so its weights on lowerJaw
    # give identical deformation.
    #
    # This also REPARENTS THE TONGUE. Daz chains lowerJaw -> lowerTeeth ->
    # tongue01..04, and the collapse's nearest-surviving-ancestor pass walks
    # tongue01 up to lowerJaw once lowerTeeth is doomed - no bone_reparent_overrides
    # entry needed. What is lost is Daz's "anything that shifts the lower dental
    # arch carries the tongue with it", which nothing here relies on.
    "lowerTeeth",
]

###############################################################################
# Foot: Manny has ball_l as a DIRECT child of foot_l. Daz puts lMetatarsals in
# between (lFoot -> lMetatarsals -> lToe) and hangs lHeel off lFoot as well.
#
# Leaving lMetatarsals in the chain would make the rig Manny-incompatible, so its
# weight is folded into the foot and the bone is removed; mergeBonesIntoTargets then
# reparents ball.L onto foot.L.
#
# NOTE the mixed naming below, it is not a mistake. The collapse runs AFTER both the
# bone rename (done by alignArmatureFromDifeomorphicToManny) and the vertex-group
# rename, so mapped bones are already Manny-named - hence foot.L, not lFoot. Bones
# with no Manny equivalent (the whole face rig, lHeel, lMetatarsals, head, lowerJaw)
# were never renamed and so still carry Daz names.
###############################################################################
foot_bones_merged_to_left_foot = ["lHeel", "lMetatarsals"]
foot_bones_merged_to_right_foot = ["rHeel", "rMetatarsals"]


# {target bone: [bones whose weights are folded into it and are then deleted]}
# All bone/weight merging for the conversion lives here - switchVertexGroupsToManny
# is a pure 1:1 rename and does no merging of its own.
bone_collapse_rules = {
    "head": face_bones_merged_to_head,              # unmapped, keeps its Daz name
    "lowerJaw": face_bones_merged_to_lower_jaw,     # unmapped, keeps its Daz name
    "foot.L": foot_bones_merged_to_left_foot,       # renamed from lFoot in step 1
    "foot.R": foot_bones_merged_to_right_foot,      # renamed from rFoot in step 1
}


###############################################################################
# Parenting fixes applied after a collapse, {new parent: [children to move]}.
#
# When a bone is deleted its orphans go to the nearest surviving ancestor, which
# is right for most things but wrong for the toes. Daz hangs lToe AND all five
# toes off lMetatarsals as siblings:
#
#     lFoot -> lMetatarsals -> lToe
#                           -> lBigToe -> lBigToe_2
#                           -> lSmallToe1..4 -> ..._2
#
# so deleting lMetatarsals would drop the toes onto foot.L next to ball.L.
# Anatomically, and in every game rig, the toes belong UNDER the ball.
#
# Post-rename names, since this runs after the collapse. The _2 tip bones are not
# listed: they are children of the joint01 bones and move along with them.
###############################################################################
bone_reparent_overrides = {
    "ball.L": [
        "big_toe_joint01.L",
        "small_toe1_joint01.L", "small_toe2_joint01.L",
        "small_toe3_joint01.L", "small_toe4_joint01.L",
    ],
    "ball.R": [
        "big_toe_joint01.R",
        "small_toe1_joint01.R", "small_toe2_joint01.R",
        "small_toe3_joint01.R", "small_toe4_joint01.R",
    ],
}


###############################################################################
# Twist bones.
#
# Daz gives one twist per joint and chains it IN-LINE:
#     lShldrBend -> lShldrTwist -> lForearmBend -> lForearmTwist -> lHand
# Manny gives TWO per joint and hangs them off the parent as LEAVES:
#     upperarm_l -> lowerarm_l
#                -> upperarm_twist_01_l, upperarm_twist_02_l
#
# setupTwistBones fixes both differences. Taking the twists out of the chain is
# the same operation DazToUnreal does in FixTwistBones (DazToUnrealFbx.cpp:174),
# which it forces on for any Convert-To-Epic run.
#
# Placement: the twists are spaced along the parent at 1/3 and 2/3, each one a
# third of the parent long, roll copied from the parent.
#
# Ordering is _01 then _02 down the limb, except the calf, which is deliberately
# reversed:
#   thigh    _01 @ 1/3 (hip end)     _02 @ 2/3 (knee end)
#   calf     _01 @ 2/3 (ankle end)   _02 @ 1/3 (knee end)   <- reversed
#   upperarm _01 @ 1/3 (shoulder)    _02 @ 2/3 (elbow)
#   lowerarm _01 @ 2/3 (wrist end)   _02 @ 1/3 (elbow end)  <- reversed
# The two distal segments are reversed: their twist is driven from the far joint
# (ankle, wrist), so _01 sits at that end. Swap a pair's fractions to flip it.
#
# NOTE this does not match armature_vxnew_manny.json, which parks both twins at
# 50% with half the parent's length. These spaced positions were specified later
# and supersede it.
#
# Daz has NO shin twist - not in G3, G8 or G9, and DazToUnreal has no calf_twist
# mapping for any of them (it inherits those bones from Quinn, weightless). So
# calf_twist_01/02 have no source weights here either and start empty.
#
# (parent, [(twist name, head fraction along parent), ...], length fraction)
###############################################################################
twist_bone_pairs = [
    ("thigh.L",    [("thigh_twist_01.L", 1.0/3.0), ("thigh_twist_02.L", 2.0/3.0)], 1.0/3.0),
    ("thigh.R",    [("thigh_twist_01.R", 1.0/3.0), ("thigh_twist_02.R", 2.0/3.0)], 1.0/3.0),
    ("calf.L",     [("calf_twist_01.L", 2.0/3.0), ("calf_twist_02.L", 1.0/3.0)], 1.0/3.0),
    ("calf.R",     [("calf_twist_01.R", 2.0/3.0), ("calf_twist_02.R", 1.0/3.0)], 1.0/3.0),
    ("upperarm.L", [("upperarm_twist_01.L", 1.0/3.0), ("upperarm_twist_02.L", 2.0/3.0)], 1.0/3.0),
    ("upperarm.R", [("upperarm_twist_01.R", 1.0/3.0), ("upperarm_twist_02.R", 2.0/3.0)], 1.0/3.0),
    ("lowerarm.L", [("lowerarm_twist_01.L", 2.0/3.0), ("lowerarm_twist_02.L", 1.0/3.0)], 1.0/3.0),
    ("lowerarm.R", [("lowerarm_twist_01.R", 2.0/3.0), ("lowerarm_twist_02.R", 1.0/3.0)], 1.0/3.0),
]


###############################################################################
# Bones whose length is set EXACTLY to the distance to their chain successor,
# rather than merely being capped at it by clampBoneLengthsToChildHeads.
#
# Daz's tails stop short of where the next joint begins, so a cap alone leaves
# these short. Direction and roll are preserved; only the tail slides along the
# existing axis.
#
#   foot     -> should reach the ball
#   thigh    -> should reach the shin/calf head
#   calf     -> should reach the foot head
#   upperarm -> should reach the lowerarm head
#   lowerarm -> should reach the hand head
#
# Measured on the real G3F rig, every one of these is SHORT, not long, so the cap
# alone would never fire: thigh/upperarm/lowerarm/foot fall ~53% short of the next
# joint and the calf ~4%.
#
# The twist fractions are measured off these lengths, so setupTwistBones settles
# them (step 2) before placing anything (step 3). The calf matters here even at 4%:
# a short calf pushes calf_twist_01/02 about 1.3 cm up the shin, away from the ankle.
###############################################################################
# Bones re-AIMED at their chain successor, i.e. tail moved onto the child's head.
#
# THE WHOLE CHAIN, which is MORE than DazToUnreal does. Measured against the real
# UE5 skeleton (bone_data.csv): every bone from pelvis to head is connected
# tail-to-head, each child's local translation being exactly (parent.Length, 0, 0)
# along the parent's +X:
#
#     spine_01 (2.4719 vs len 2.4719)   spine_02 (4.9875 / 4.9875)
#     spine_03 (7.6259 / 7.6259)        spine_04 (8.8511 / 8.8511)
#     spine_05 (17.4988 / 17.4988)      neck_01  (11.9150 / 11.9150)
#     neck_02  (5.8488 / 5.8488)        head     (5.7585 / 5.7585)
#
# So aiming every one of them at its child reproduces Epic's structure exactly,
# and any bone left out ends up pointing somewhere Epic does not.
#
# DTU only aims five (DazToUnrealBlueprintUtils.cpp:442-448) - spine_02..spine_05
# and neck_01. The gaps are omissions, not design:
#   pelvis    - AlignBone commented out at :441. DTU instead SETS the orientation to
#               FRotator(90,-90,-90) at :379, which points it up; the real Quinn
#               value is (-90, 86.397, -90), the same thing rounded. Without that
#               orientation pass - which this addon does not have - a straight
#               transcription leaves the Daz pelvis pointing DOWN, because that is
#               the way Daz's pelvis bone runs.
#   spine_01  - commented out at :445. Its head IS moved by the midpoint
#               re-positioning and nothing re-aimed it, so it kept pointing at where
#               spine_02 sat relative to its OLD head.
#   neck_02   - DTU never wrote the call, so head was never aimed at.
#
# head is not listed because its manny_chain_successors entry is None.
#
# The successor comes from manny_chain_successors, so the chain is defined once.
#
# This still does NOT reproduce Quinn's S-curve. DazToUnreal never reads the target
# skeleton's geometry (TargetEpicSkeleton is only used for GetSkeleton()), and
# neither does this - the curvature stays the Daz figure's. Only the direction each
# bone points along that curve is corrected.
spine_bones_aimed_at_children = [
    "pelvis",
    "spine_01", "spine_02", "spine_03", "spine_04", "spine_05",
    "neck_01", "neck_02",
]


bones_length_set_to_successor = [
    "foot.L", "foot.R",
    "thigh.L", "thigh.R",
    "calf.L", "calf.R",
    "upperarm.L", "upperarm.R",
    "lowerarm.L", "lowerarm.R",
]


###############################################################################
# Bones that must survive the collapse. Asserted at run time so a careless edit
# to the lists above cannot quietly delete something the later pipeline needs.
###############################################################################
bones_that_must_be_kept = [
    "lEye", "rEye", "lEar", "rEar",
    # Teeth deliberately removed from the guard: they are now in the collapse
    # lists above, merged into head / lowerJaw. Leaving them here would not
    # "protect" them - the clash check ABORTS the whole merge and returns
    # ({}, []), so the entire 68-bone face collapse would silently not run.
    # "upperTeeth", "lowerTeeth",
    "tongue01", "tongue02", "tongue03", "tongue04",
]


# ---------------------------------------------------------------------------
# BlenderPerfect roll deltas
# ---------------------------------------------------------------------------
#
# Degrees to ADD to whatever roll Diffeomorphic delivers, to reach the working
# convention: X on the joint's natural hinge, so flexion is a positive rotation
# about X and you can pose a limb on one axis.
#
# Measured once with vxmod.report_roll_rule_deltas against a real G3F rig, then
# frozen here. Deriving hinges at runtime was tried and abandoned: it needs a
# cross product of two nearly parallel bones, and on G3F the ring and pinky have
# only 0.82 and 0.57 degrees of rest bend, which made adjacent fingers disagree
# by 87 degrees. Frozen numbers have no such failure mode.
#
# The headline result is that Diffeomorphic is ALREADY in the convention almost
# everywhere, so this table is deliberately tiny - a bone with no entry keeps its
# Daz roll, which is the correct answer for it, not a placeholder:
#
#   spine, neck, head, pelvis   0.000 deg from the rule, to three decimals
#   thigh / calf                within 2.3 and 7.2 deg, rounds to 0
#   upperarm / lowerarm         rounds to 0; confirmed by eye that Z already
#                               points away from where the elbow pole belongs
#   fingers                     kept as Daz delivers them - all four sit at
#                               about -175, so they are at least self consistent,
#                               and the measured hinges were too noisy to trust
#   clavicle                    the one bone genuinely out of step
#
# Deltas MUST mirror between sides, because the Daz rolls do (thigh.L -6.819 vs
# thigh.R +6.819). A non-mirrored delta would silently break left/right symmetry.
# Empty is the expected state, not an oversight. Every bone that needed an offset
# turned out to need zero - Diffeomorphic already delivers the convention - and
# the two that did not (clavicle, hand) are handled by aiming and by a hinge
# below, which adapt per rig instead of assuming G3F proportions. Kept as the
# documented place to put a per-bone offset if one ever proves necessary.
blender_perfect_roll_deltas = {
}

# Bones whose roll is set by AIMING rather than by a delta: the value is the
# direction the bone's secondary axis (Blender local Z) should point, in armature
# space, fed to EditBone.align_roll.
#
# Only the clavicle needs this. It has no hinge to derive a roll from, so it was
# briefly a hand-measured +/-90; aiming is better because it is rig-intrinsic and
# adapts to whatever shoulder angle a figure has. Verified against the UE5
# reference, where "secondary axis toward the front of the character" reproduces
# Epic's clavicle roll to 0.184 deg. Aiming at the upperarm's own secondary axis
# instead - the obvious guess - is 3.256 deg out, because the upper arm sits
# 3.64 deg off pure front.
#
# Unlike a hinge, this is numerically safe: aiming at a fixed world direction has
# no near-parallel cancellation to worry about.
#
# The clavicle already points at its child in the built rig (0.0000 deg), so the
# direction needs nothing - only the roll.
FRONT = (0.0, -1.0, 0.0)

blender_perfect_roll_axis_targets = {
    "clavicle.L": FRONT,
    "clavicle.R": FRONT,
}

# Bones whose X axis is a HINGE derived from two bone directions:
#   bone -> (bone A, bone B, sign)   ->   X = sign * normalize(dir(A) x dir(B))
#
# Only the hand needs this. The wrist is 2-DOF, but flexion/extension is clearly
# the primary axis - the motion of slapping a ball toward the ground - and like
# any hinge it is perpendicular to both segments it joins. Verified against the
# UE5 reference: Manny's hand X sits 89.51 deg from the forearm, i.e. exactly
# perpendicular, and this rule lands 2.5 deg from Epic's roll.
#
# The obvious alternative, aiming along the knuckles, was measured and rejected:
# it comes out 178 deg wrong and is not even mirrored between the two hands
# (-97.9 / -82.1), so it would need a per-side sign flip. The hinge form is
# mirrored for free (+86.5 / -86.5), matching the reference's +84.0 / -84.0.
#
# Order matters. For the knee the bone being rolled is the PARENT and the hinge
# is parent x child; here the bone being rolled is the CHILD, so it is hand x
# forearm. Flexion has to stay a positive rotation either way.
blender_perfect_hinge_rules = {
    "hand.L": ("hand.L", "lowerarm.L", +1.0),
    "hand.R": ("hand.R", "lowerarm.R", +1.0),
    # The thumb is opposable, so it does NOT share the finger plane - aiming it
    # along the knuckle line is 85 deg wrong. Its own joint gives 17.6 deg from
    # Manny, and the rest bend is 21.7 deg on G3F, well clear of the guard.
    "thumb_01.L": ("thumb_01.L", "thumb_02.L", +1.0),
    "thumb_02.L": ("thumb_01.L", "thumb_02.L", +1.0),
    "thumb_03.L": ("thumb_01.L", "thumb_02.L", +1.0),
    "thumb_01.R": ("thumb_01.R", "thumb_02.R", +1.0),
    "thumb_02.R": ("thumb_01.R", "thumb_02.R", +1.0),
    "thumb_03.R": ("thumb_01.R", "thumb_02.R", +1.0),
}

# Fingers: X aimed along the line across the knuckles, from the index metacarpal
# to the pinky metacarpal.
#
#   (bones to roll, from bone, to bone, sign)   X = sign * normalize(to.head - from.head)
#
# This exists because Unreal's "compatible skeleton" playback applies Manny's
# LOCAL bone rotations to ours by name, so any bone whose reference orientation
# differs from Manny's plays back wrong. Everything else in the rig is within a
# few degrees; the fingers, left on their Daz rolls, were 80-102 deg out, which
# is why retargeted clips wrecked the hands while posing looked fine.
#
# Measured against Manny: median 11.2 deg, max 26.3 (middle 0.6, index 11,
# ring 11, pinky 25). The fan toward the pinky is real - Manny's little finger
# curls at an angle to the index - and could be closed by per-finger constants
# measured off Manny, at the cost of baking Manny's anatomy into a Daz rig.
#
# Deriving each finger's own hinge was tried and rejected: G3F's ring and pinky
# have 0.82 and 0.57 deg of rest bend, and adjacent fingers came out 87 deg
# apart. The knuckle line is a long, well-conditioned vector with no such
# failure mode.
#
# The sign is per side and cannot be folded away - the two hands are not mirrors
# of each other in this respect.
_LEFT_FINGERS = [f + p + '.L' for f in ('index', 'middle', 'ring', 'pinky')
                 for p in ('_metacarpal', '_01', '_02', '_03')]
_RIGHT_FINGERS = [n[:-2] + '.R' for n in _LEFT_FINGERS]

blender_perfect_knuckle_rules = [
    (_LEFT_FINGERS,  "index_metacarpal.L", "pinky_metacarpal.L", +1.0),
    (_RIGHT_FINGERS, "index_metacarpal.R", "pinky_metacarpal.R", -1.0),
]

# Below this the two directions are too close to parallel for the cross product
# to mean anything, so the bone is left alone and reported rather than given a
# confidently wrong axis. Manny's wrist bend is 11.08 deg for reference.
minimum_hinge_bend_degrees = 2.0

# Twist bones take their parent's roll rather than a table entry - they share the
# parent's axis by definition, so a separate value could only ever disagree.
# This also sidesteps a caching trap: setupTwistBones creates the missing twists
# AFTER the first roll pass, so any baseline captured for them is the parent's
# already-adjusted roll, not a Daz roll.
twist_bone_name_marker = "_twist_"


# ---------------------------------------------------------------------------
# Unreal helper bones the Daz rig does not have
# ---------------------------------------------------------------------------
#
# Manny carries ten bones the builder never creates: the IK markers, plus
# interaction and center_of_mass. They deform nothing, but Unreal's retarget and
# IK setups expect them, so the exporter adds them to the clone.
#
# Measured from bone_data.csv, they are not placed arbitrarily - each one shadows
# a deform bone:
#
#   ik_foot_root, ik_hand_root, interaction, center_of_mass   exactly on root
#   ik_foot_l / ik_foot_r        0.0312 from foot_l / foot_r
#   ik_hand_l / ik_hand_r        0.2157 from hand_l / hand_r
#   ik_hand_gun                  0.2157 from hand_r  (it shadows the RIGHT hand)
#
# Those residuals are Epic's own authoring slop, well under a millimetre, so
# copying the shadowed bone exactly is both simpler and arguably tidier than
# reproducing them. Orientation is copied too: Epic's differs by ~3 deg on the
# feet and ~12 deg on the hands, which is inside the tolerance everything else
# here works to, and copying keeps the marker agreeing with the bone it marks.
#
# `root` is deliberately absent. The Blender FBX exporter synthesises the root
# from the armature object, so creating one here would produce two.
#
# Order matters: parents are listed before their children.
#
#   (bone, parent, bone whose position and orientation to copy or None for the origin)
unreal_helper_bones = [
    ("ik_foot_root",   "root",         None),
    ("ik_foot_l",      "ik_foot_root", "foot.L"),
    ("ik_foot_r",      "ik_foot_root", "foot.R"),
    ("ik_hand_root",   "root",         None),
    ("ik_hand_gun",    "ik_hand_root", "hand.R"),
    ("ik_hand_l",      "ik_hand_gun",  "hand.L"),
    ("ik_hand_r",      "ik_hand_gun",  "hand.R"),
    ("interaction",    "root",         None),
    ("center_of_mass", "root",         None),
]

# Length for a helper with nothing to copy, as a fraction of the rig's height, so
# it stays visible whatever scale the figure is built at.
unreal_helper_bone_length_fraction = 0.05


def getMannyBoneRenameMap():
    """
    The single source of truth for Daz -> Manny naming.

    Both the armature builder and the vertex-group renamer call this, so bone names
    and vertex-group names cannot drift apart. (They already had: the old
    spine_weights_matching table was off by one against dtu_manny_bones_matching -
    abdomenLower -> spine_01 as a group but spine_02 as a bone.)
    """
    combined = dict(dtu_manny_bones_matching)
    combined.update(manny_extra_bones_matching)
    return combined



###############################################################################
# Sibling order for the exported skeleton
###############################################################################
# Unreal builds its reference skeleton by walking the FBX node tree in child
# order, and Blender's FBX exporter emits bones in the order of
# `armature.data.bones` - which is a depth first walk whose sibling order is the
# order the bones sit in `edit_bones`. That order came from Daz, so the Daz
# extras (butt, gens, stomach, hip twist ends) land ahead of spine_01 and the
# skeleton tree in Unreal looks nothing like Epic's, even though every bone,
# parent and transform is identical.
#
# Each entry names a parent and the children that must come FIRST under it, in
# order. Anything not listed keeps the relative order it already had, appended
# after the listed ones - so this is a "pin these to the top" table, not a full
# ordering, and adding a bone to the rig never needs an edit here.
#
# The empty key "" is the top level, i.e. the bones with no parent. They become
# the children of the root that the FBX exporter synthesises from the armature
# object, so `pelvis` first there is what puts the deform skeleton above the IK
# markers - the same layout Epic ships.
#
# Names may be written either way, `thigh.L` or `thigh_l`; both the table and
# the rig are normalised to the Unreal spelling before matching, so the table
# reads the same whether the sort runs before or after rename_bones_for_unreal.
export_bone_sibling_order = {
    "":       ["pelvis", "ik_foot_root", "ik_hand_root", "interaction", "center_of_mass"],
    "pelvis": ["spine_01", "thigh_l", "thigh_r"],
}
