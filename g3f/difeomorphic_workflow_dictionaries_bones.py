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

