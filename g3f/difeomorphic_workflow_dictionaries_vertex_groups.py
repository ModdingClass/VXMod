vertexGroupsForRemoval = [
    'lIndex3', 'lMid3', 'lRing3', 'lPinky3', 'rIndex3', 'rMid3', 'rRing3', 'rPinky3', 'lThumb3', 'lIndex2', 'lMid2', 'lRing2', 'lPinky2', 'rThumb3', 'rIndex2', 'rMid2', 'rRing2', 'rPinky2', 'lThumb2', 'lIndex1', 'lMid1', 'lRing1', 'lPinky1', 'rThumb2', 'rIndex1', 'rMid1', 'rRing1', 'rPinky1', 'lThumb1', 'lCarpal1', 'lCarpal2', 'lCarpal3', 'lCarpal4', 'rThumb1', 'rCarpal1', 'rCarpal2', 'rCarpal3', 'rCarpal4', 'lHand', 'rHand', 
    'lNasolabialLower', 'rNasolabialLower', 'lNasolabialMouthCorner', 'rNasolabialMouthCorner', 'lLipCorner', 'lLipLowerOuter', 'lLipLowerInner', 'LipLowerMiddle', 'rLipLowerInner', 'rLipLowerOuter', 'rLipCorner', 'LipBelow', 'Chin', 'lCheekLower', 'rCheekLower', 'BelowJaw', 'lJawClench', 'rJawClench', 'lForearmTwist', 'rForearmTwist', 'lowerTeeth', 'rBrowInner', 'rBrowMid', 'rBrowOuter', 'lBrowInner', 'lBrowMid', 'lBrowOuter', 'CenterBrow', 'MidNoseBridge', 'lEyelidInner', 'lEyelidUpperInner', 'lEyelidUpper', 'lEyelidUpperOuter', 'lEyelidOuter', 'lEyelidLowerOuter', 'lEyelidLower', 'lEyelidLowerInner', 'rEyelidInner', 'rEyelidUpperInner', 'rEyelidUpper', 'rEyelidUpperOuter', 'rEyelidOuter', 'rEyelidLowerOuter', 'rEyelidLower', 'rEyelidLowerInner', 'lSquintInner', 'lSquintOuter', 'rSquintInner', 'rSquintOuter', 'lCheekUpper', 'rCheekUpper', 'Nose', 'lNostril', 'rNostril', 'lLipBelowNose', 'rLipBelowNose', 'lLipUpperOuter', 'lLipUpperInner', 'LipUpperMiddle', 'rLipUpperInner', 'rLipUpperOuter', 'lLipNasolabialCrease', 'rLipNasolabialCrease', 'lNasolabialUpper', 'rNasolabialUpper', 'lNasolabialMiddle', 'rNasolabialMiddle', 
    'lSmallToe4_2', 'lSmallToe3_2', 'lSmallToe2_2', 'lSmallToe1_2', 'lBigToe_2', 'rSmallToe4_2', 'rSmallToe3_2', 'rSmallToe2_2', 'rSmallToe1_2', 'rBigToe_2', 
    'lForearmBend', 'rForearmBend', 
    'upperTeeth', 'lowerJaw', 
    'lEye', 'rEye', 'lEar', 'rEar', 
    'lSmallToe4', 'lSmallToe3', 'lSmallToe2', 'lSmallToe1', 'lBigToe', 'rSmallToe4', 'rSmallToe3', 'rSmallToe2', 'rSmallToe1', 'rBigToe', 
    'lShldrTwist', 'rShldrTwist', 
    'head', 
    'lMetatarsals', 'lHeel', 'rMetatarsals', 'rHeel', 
    'lShldrBend', 'rShldrBend', 
    'tongue04','tongue03','tongue02', 'tongue01',
    'neckUpper', 
    'lFoot', 'rFoot', 
    'lCollar', 'rCollar', 
    'neckLower', 
    'lShin', 'rShin', 
    'chestUpper', 'lPectoral', 'rPectoral', 
    'lThighTwist', 'rThighTwist', 
    'chestLower', 
    'lThighBend', 'rThighBend', 
    'abdomenUpper', 'abdomenLower']
jaw = ["lowerTeeth"]
head_weights = ['head', 'upperTeeth', 'lowerJaw', 'lEye', 'rEye', 'lEar', 'rEar','rBrowInner', 'rBrowMid', 'rBrowOuter', 'lBrowInner', 'lBrowMid', 'lBrowOuter', 'CenterBrow', 'MidNoseBridge', 'lEyelidInner', 'lEyelidUpperInner', 'lEyelidUpper', 'lEyelidUpperOuter', 'lEyelidOuter', 'lEyelidLowerOuter', 'lEyelidLower', 'lEyelidLowerInner', 'rEyelidInner', 'rEyelidUpperInner', 'rEyelidUpper', 'rEyelidUpperOuter', 'rEyelidOuter', 'rEyelidLowerOuter', 'rEyelidLower', 'rEyelidLowerInner', 'lSquintInner', 'lSquintOuter', 'rSquintInner', 'rSquintOuter', 'lCheekUpper', 'rCheekUpper', 'Nose', 'lNostril', 'rNostril', 'lLipBelowNose', 'rLipBelowNose', 'lLipUpperOuter', 'lLipUpperInner', 'LipUpperMiddle', 'rLipUpperInner', 'rLipUpperOuter', 'lLipNasolabialCrease', 'rLipNasolabialCrease', 'lNasolabialUpper', 'rNasolabialUpper', 'lNasolabialMiddle', 'rNasolabialMiddle', 'tongue01', 'lNasolabialLower', 'rNasolabialLower', 'lNasolabialMouthCorner', 'rNasolabialMouthCorner', 'lLipCorner', 'lLipLowerOuter', 'lLipLowerInner', 'LipLowerMiddle', 'rLipLowerInner', 'rLipLowerOuter', 'rLipCorner', 'LipBelow', 'Chin', 'lCheekLower', 'rCheekLower', 'BelowJaw', 'lJawClench', 'rJawClench']

head_weights_matching = [
# source bone used for head, source bone used for tail, target bone

["head", "head", "head"],
["Chin", "Chin", "chin_joint01"],
["LipBelow",  "BelowJaw", "lower_jaw_end"],
["lowerJaw","lJawClench","rJawClench","lower_jaw_joint01"],
["Nose","MidNoseBridge","lNostril","rNostril","nose_joint02"],
["lNasolabialUpper","lNasolabialMiddle","lCheekUpper","lCheekLower","cheek_joint01.L"],
["rNasolabialUpper","rNasolabialMiddle","rCheekUpper","rCheekLower","cheek_joint01.R"],

["rNasolabialLower","lower_lip_joint01.R"],
["lNasolabialLower","lower_lip_joint01.L"],

["lLipCorner","lLipLowerOuter","lower_lip_joint02.L"],
["rLipCorner","rLipLowerOuter","lower_lip_joint02.R"],

["lLipLowerInner","lower_lip_joint03.L"],
["rLipLowerInner","lower_lip_joint03.R"],

["LipLowerMiddle","lower_lip_end.L"],
["LipLowerMiddle","lower_lip_end.R"],

["lNasolabialMiddle","upper_lip_joint01.L"],
["rNasolabialMiddle","upper_lip_joint01.R"],

["lLipUpperOuter","lLipNasolabialCrease","upper_lip_joint02.L"],
["rLipUpperOuter","rLipNasolabialCrease","upper_lip_joint02.R"],

["lLipBelowNose","lLipUpperInner","upper_lip_joint03.L"],
["rLipBelowNose","rLipUpperInner","upper_lip_joint03.R"],

["LipUpperMiddle","upper_lip_end.L"],
["LipUpperMiddle","upper_lip_end.R"],

["lBrowInner","eye_brow_joint01.L"],
["rBrowInner","eye_brow_joint01.R"],

["lBrowMid","eye_brow_joint02.L"],
["rBrowMid","eye_brow_joint02.R"],

["lBrowOuter","eye_brow_end.L"],
["rBrowOuter","eye_brow_end.R"],

["CenterBrow","forehead_end"],

["lEar","ear_joint01.L"],
["rEar","ear_joint01.R"]

]


leg_weights_matching = [
# source weights, target weights bone
["lThighBend", "lThighBend", "thigh.L"],
["rThighBend", "rThighBend", "thigh.R"],

["lThighTwist", "lThighTwist", "thigh_twist_01.L"],
["lThighTwist", "lThighTwist", "thigh_twist_02.L"],
["rThighTwist", "rThighTwist", "thigh_twist_01.R"],
["rThighTwist", "rThighTwist", "thigh_twist_02.R"],

["lShin", "lShin", "calf.L"],
["rShin", "rShin", "calf.R"],

#["lFoot", "lFoot", "foot.L"],
#["rFoot", "rFoot", "foot.R"],

["lToe", "lToe", "ball.L"],
["rToe", "rToe", "ball.R"],

#["lBigToe_2","lBigToe_2","toe_deform01_joint01.L"],
#["rBigToe_2","rBigToe_2","toe_deform01_joint01.R"],

#["lSmallToe2_2","lSmallToe2_2","toe_deform02_joint01.L"],
#["rSmallToe2_2","rSmallToe2_2","toe_deform02_joint01.R"]

]

toes_weights_matching = [
# source weights, target weights bone

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

# source bone used for head, source bone used for tail, target bone
spine_weights_matching = [
["pelvis", "pelvis", "pelvis"],
["abdomenLower", "abdomenLower", "spine_01"],

["abdomenUpper", "abdomenUpper", "spine_02"],
["chestLower", "chestLower", "spine_03"], ####so and so , maybe I need a mix with joint_03
["chestUpper", "chestUpper", "spine_04"],
#["chestUpper", "chestUpper", "spine_05"],

["neckLower", "neckLower", "neck_01"],
["neckUpper", "neckUpper", "neck_02"],
#["head", "head", "head"]
]


hand_weights_matching = [
["lCollar", "lCollar", "clavicle.L"],
["rCollar", "rCollar", "clavicle.R"],

["lShldrBend", "lShldrBend", "upperarm.L"],
["rShldrBend", "rShldrBend", "upperarm.R"],
["lShldrTwist", "lShldrTwist", "upperarm_twist_01.L"],
["lShldrTwist", "lShldrTwist", "upperarm_twist_02.L"],
["rShldrTwist", "rShldrTwist", "upperarm_twist_01.R"],
["rShldrTwist", "rShldrTwist", "upperarm_twist_02.R"],

["lForearmBend", "lForearmBend", "lowerarm.L"],
["rForearmBend", "rForearmBend", "lowerarm.R"],
["lForearmTwist", "lForearmTwist", "lowerarm_twist_01.L"],
["lForearmTwist", "lForearmTwist", "lowerarm_twist_02.L"],
["rForearmTwist", "rForearmTwist", "lowerarm_twist_01.R"],
["rForearmTwist", "rForearmTwist", "lowerarm_twist_02.R"],

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


breast_weights_matching = [
["lPectoral", "lPectoral", "breast_joint.L"],
["rPectoral", "rPectoral", "breast_joint.R"]
]