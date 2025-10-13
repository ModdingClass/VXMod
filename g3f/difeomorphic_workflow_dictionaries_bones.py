#last value in the array is the roll override
leg_bones_matching = [
# source bone used for head, source bone used for tail, target bone
["lThighBend", "lThighTwist", "hip_joint.L",0], ###"lThighBend + lThighTwist"
["rThighBend", "rThighTwist", "hip_joint.R",0], ###"rThighBend + rThighTwist" 

["lShin", "lShin", "knee_joint.L",0],
["rShin", "rShin", "knee_joint.R",0],

["lFoot", "lMetatarsals", "ankle_joint.L",0],
["rFoot", "rMetatarsals", "ankle_joint.R",0],

["lToe", "lToe", "ball_joint.L",0],
["rToe", "rToe", "ball_joint.R",0],

["lThighTwist", "lThighTwist", "thigh_twist_joint.L",0], 
["rThighTwist", "rThighTwist", "thigh_twist_joint.R",0]

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
["pelvis", "pelvis", "pelvis_joint"],         #!!!!!!!!!!!!!!!! not going to set the root yet, as it could be hardcoded in many other places
["abdomenLower", "abdomenLower", "spine_joint01",90],

["abdomenUpper", "abdomenUpper", "spine_joint02",90],
["chestLower", "chestLower", "spine_joint03",90], ####so and so , maybe I need a mix with joint_03
["chestUpper", "chestUpper", "spine_joint04",90],

["neckLower", "neckLower", "neck_joint01",90],
["neckUpper", "neckUpper", "neck_jointEnd",90],
["head", "head", "head_joint01",90],
["head", "head", "head_joint02",90]
]

#redefining the spine bones (current plugin does not support spine editor, so moving bones will create movements later in spines cause no ikhandles and effectors and init data for those matching the new joints)
#last value in the array is the roll override
spine_bones_matching_other = [
# source bone used for head, source bone used for tail, target bone
#["pelvis", "pelvis", "root"],         #!!!!!!!!!!!!!!!! not going to set the root yet, as it could be hardcoded in many other places
#["neckLower", "neckLower", "neck_joint01",90],
#["neckUpper", "neckUpper", "neck_jointEnd",90],
["head", "head", "head_joint01",90],
["head", "head", "head_joint02",90]
]


#last value in the array is the roll override
arm_bones_matching = [
["lCollar", "lCollar", "clavicle_joint.L",0],
["rCollar", "rCollar", "clavicle_joint.R",0],

["lShldrBend", "lShldrTwist", "shoulder_joint.L",90],  ### ????", "lShldrBend + lShldrTwist"
["rShldrBend", "rShldrTwist", "shoulder_joint.R",-90],  ### ????", "rShldrBend + rShldrTwist"


["lShldrTwist", "lShldrTwist", "shoulder_twist_joint.L",90], 
["rShldrTwist", "rShldrTwist", "shoulder_twist_joint.R",-90], 


["lForearmBend", "lForearmTwist", "elbow_joint.L",90],
["rForearmBend", "rForearmTwist", "elbow_joint.R",-90],
["lForearmTwist", "lForearmTwist", "forearm_twist_joint.L",90],
["rForearmTwist", "rForearmTwist", "forearm_twist_joint.R",-90],

["lHand", "lHand", "wrist_joint.L",90], #,90
["rHand", "rHand", "wrist_joint.R",-90], #-90
]

#last value in the array is the roll override
finger_bones_matching = [

["lThumb1", "lThumb1", "finger01_joint01.L"],
["lCarpal1", "lCarpal1", "finger02_joint01.L"],
["lCarpal2", "lCarpal2", "finger03_joint01.L"],
["lCarpal3", "lCarpal3", "finger04_joint01.L"],
["lCarpal4", "lCarpal4", "finger05_joint01.L"],

["lThumb2", "lThumb2", "finger01_joint02.L"],
["lThumb3", "lThumb3", "finger01_joint03.L"],

["lIndex1", "lIndex1", "finger02_joint02.L"],
["lIndex2", "lIndex2", "finger02_joint03.L"],
["lIndex3", "lIndex3", "finger02_joint04.L"],

["lMid1", "lMid1", "finger03_joint02.L"],
["lMid2", "lMid2", "finger03_joint03.L"],
["lMid3", "lMid3", "finger03_joint04.L"],

["lRing1", "lRing1", "finger04_joint02.L"],
["lRing2", "lRing2", "finger04_joint03.L"],
["lRing3", "lRing3", "finger04_joint04.L"],

["lPinky1", "lPinky1", "finger05_joint02.L"],
["lPinky2", "lPinky2", "finger05_joint03.L"],
["lPinky3", "lPinky3", "finger05_joint04.L"],

["rThumb1", "rThumb1", "finger01_joint01.R"],
["rCarpal1", "rCarpal1", "finger02_joint01.R"],
["rCarpal2", "rCarpal2", "finger03_joint01.R"],
["rCarpal3", "rCarpal3", "finger04_joint01.R"],
["rCarpal4", "rCarpal4", "finger05_joint01.R"],

["rThumb2", "rThumb2", "finger01_joint02.R"],
["rThumb3", "rThumb3", "finger01_joint03.R"],
           
["rIndex1", "rIndex1", "finger02_joint02.R"],
["rIndex2", "rIndex2", "finger02_joint03.R"],
["rIndex3", "rIndex3", "finger02_joint04.R"],

["rMid1", "rMid1", "finger03_joint02.R"],
["rMid2", "rMid2", "finger03_joint03.R"],
["rMid3", "rMid3", "finger03_joint04.R"],

["rRing1", "rRing1", "finger04_joint02.R"],
["rRing2", "rRing2", "finger04_joint03.R"],
["rRing3", "rRing3", "finger04_joint04.R"],

["rPinky1", "rPinky1", "finger05_joint02.R"],
["rPinky2", "rPinky2", "finger05_joint03.R"],
["rPinky3", "rPinky3", "finger05_joint04.R"]
]

#last value in the array is the roll override
bones_matching = [

# source bone used for head, source bone used for tail, target bone

["lThighBend", "lThighTwist", "hip_joint.L"], ###"lThighBend + lThighTwist"
["rThighBend", "rThighTwist", "hip_joint.R"], ###"rThighBend + rThighTwist" 

["lShin", "lShin", "knee_joint.L"],
["rShin", "rShin", "knee_joint.R"],

["lFoot", "lFoot", "ankle_joint.L"],
["rFoot", "rFoot", "ankle_joint.R"],

["lToe", "lToe", "ball_joint.L"],
["rToe", "rToe", "ball_joint.R"],

["pelvis", "pelvis", "root"],
["abdomenLower", "abdomenLower", "spine_joint02"],

["abdomenUpper", "abdomenUpper", "spine_joint03"],
["chestLower", "chestLower", "spine_joint04"], ####so and so , maybe I need a mix with joint_03
["chestUpper", "chestUpper", "spine_jointEnd"],

["neckLower", "neckLower", "neck_joint01"],
["neckUpper", "neckUpper", "neck_jointEnd"],
["head", "head", "head_joint02"],

["lCollar", "lCollar", "clavicle_joint.L"],
["rCollar", "rCollar", "clavicle_joint.R"],
#["lShldrBend", "lShldrTwist", "shoulder_joint.L"],  ### ????", "lShldrBend + lShldrTwist"
#["rShldrBend", "rShldrTwist", "shoulder_joint.R"],  ### ????", "rShldrBend + rShldrTwist"

#["lForearmBend", "lForearmBend", "elbow_joint.L"],
#["rForearmBend", "rForearmBend", "elbow_joint.R"],
#["lForearmTwist", "lForearmTwist", "forearm_twist_joint.L"],
#["rForearmTwist", "rForearmTwist", "forearm_twist_joint.R"],

["lHand", "lHand", "wrist_joint.L"],
["rHand", "rHand", "wrist_joint.R"],

["lThumb1", "lThumb1", "finger01_joint01.L"],
["lCarpal1", "lCarpal1", "finger02_joint01.L"],
["lCarpal2", "lCarpal2", "finger03_joint01.L"],
["lCarpal3", "lCarpal3", "finger04_joint01.L"],
["lCarpal4", "lCarpal4", "finger05_joint01.L"],

["lThumb2", "lThumb2", "finger01_joint02.L"],
["lThumb3", "lThumb3", "finger01_joint03.L"],

["lIndex1", "lIndex1", "finger02_joint02.L"],
["lIndex2", "lIndex2", "finger02_joint03.L"],
["lIndex3", "lIndex3", "finger02_joint04.L"],

["lMid1", "lMid1", "finger03_joint02.L"],
["lMid2", "lMid2", "finger03_joint03.L"],
["lMid3", "lMid3", "finger03_joint04.L"],

["lRing1", "lRing1", "finger04_joint02.L"],
["lRing2", "lRing2", "finger04_joint03.L"],
["lRing3", "lRing3", "finger04_joint04.L"],

["lPinky1", "lPinky1", "finger05_joint02.L"],
["lPinky2", "lPinky2", "finger05_joint03.L"],
["lPinky3", "lPinky3", "finger05_joint04.L"],

["rThumb1", "rThumb1", "finger01_joint01.R"],
["rCarpal1", "rCarpal1", "finger02_joint01.R"],
["rCarpal2", "rCarpal2", "finger03_joint01.R"],
["rCarpal3", "rCarpal3", "finger04_joint01.R"],
["rCarpal4", "rCarpal4", "finger05_joint01.R"],

["rThumb2", "rThumb2", "finger01_joint02.R"],
["rThumb3", "rThumb3", "finger01_joint03.R"],
           
["rIndex1", "rIndex1", "finger02_joint02.R"],
["rIndex2", "rIndex2", "finger02_joint03.R"],
["rIndex3", "rIndex3", "finger02_joint04.R"],

["rMid1", "rMid1", "finger03_joint02.R"],
["rMid2", "rMid2", "finger03_joint03.R"],
["rMid3", "rMid3", "finger03_joint04.R"],

["rRing1", "rRing1", "finger04_joint02.R"],
["rRing2", "rRing2", "finger04_joint03.R"],
["rRing3", "rRing3", "finger04_joint04.R"],

["rPinky1", "rPinky1", "finger05_joint02.R"],
["rPinky2", "rPinky2", "finger05_joint03.R"],
["rPinky3", "rPinky3", "finger05_joint04.R"]
]

finger_jointend_bones_parents = [
["finger01_jointEnd.L","finger01_joint03.L"],
["finger02_jointEnd.L","finger02_joint04.L"],
["finger03_jointEnd.L","finger03_joint04.L"],
["finger04_jointEnd.L","finger04_joint04.L"],
["finger05_jointEnd.L","finger05_joint04.L"],

["finger01_jointEnd.R","finger01_joint03.R"],
["finger02_jointEnd.R","finger02_joint04.R"],
["finger03_jointEnd.R","finger03_joint04.R"],
["finger04_jointEnd.R","finger04_joint04.R"],
["finger05_jointEnd.R","finger05_joint04.R"]
]

toe_jointend_bones_parents = [
["big_toe_jointEnd.L","big_toe_joint02.L"],
["small_toe1_jointEnd.L","small_toe1_joint02.L"],
["small_toe2_jointEnd.L","small_toe2_joint02.L"],
["small_toe3_jointEnd.L","small_toe3_joint02.L"],
["small_toe4_jointEnd.L","small_toe4_joint02.L"],

["big_toe_jointEnd.R","big_toe_joint02.R"],
["small_toe1_jointEnd.R","small_toe1_joint02.R"],
["small_toe2_jointEnd.R","small_toe2_joint02.R"],
["small_toe3_jointEnd.R","small_toe3_joint02.R"],
["small_toe4_jointEnd.R","small_toe4_joint02.R"],
]

