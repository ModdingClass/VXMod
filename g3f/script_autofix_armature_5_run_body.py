
ebones["vagina_joint01.R"].head = amwi * vagina_joint01_R_head
ebones["vagina_joint01.R"].tail = amwi * vagina_joint01_R_tail

ebones["vagina_end.R"].head = amwi * vagina_end_R_head
ebones["vagina_end.R"].tail = amwi * vagina_end_R_tail

ebones["vagina_joint01.L"].head = amwi * vagina_joint01_L_head
ebones["vagina_joint01.L"].tail = amwi * vagina_joint01_L_tail

ebones["vagina_end.L"].head = amwi * vagina_end_L_head
ebones["vagina_end.L"].tail = amwi * vagina_end_L_tail

#########################################################################

ebones["anus_joint"].head = amwi * anus_head
ebones["anus_joint"].tail = amwi * anus_tail

ebones["thigh.R"].head = amwi * hip_R_head
ebones["thigh.R"].tail = amwi * knee_R_head

ebones["calf.R"].head = amwi * knee_R_head
ebones["calf.R"].tail = amwi * ankle_R_head

ebones["foot.R"].head = amwi * ankle_R_head
ebones["foot.R"].tail = amwi * ankle_R_tail

ebones["ball.R"].head = amwi * ball_R_head
ebones["ball.R"].tail = amwi * ball_R_tail

ebones["toe_joint.R"].head = amwi * toe_R_head
ebones["toe_joint.R"].tail = amwi * toe_R_tail


ebones["ball.R"].length /=2


ebones["toe_deform01_joint01.R"].head = amwi * toe_deform01_joint01_R_head
ebones["toe_deform01_joint01.R"].tail = amwi * toe_deform01_joint01_R_tail

ebones["toe_deform01_end.R"].head = amwi * toe_deform01_end_R_head
ebones["toe_deform01_end.R"].tail = amwi * toe_deform01_end_R_tail

ebones["toe_deform02_joint01.R"].head = amwi * toe_deform02_joint01_R_head
ebones["toe_deform02_joint01.R"].tail = amwi * toe_deform02_joint01_R_tail

ebones["toe_deform02_end.R"].head = amwi * toe_deform02_end_R_head
ebones["toe_deform02_end.R"].tail = amwi * toe_deform02_end_R_tail


ebones["thigh.L"].head = amwi * hip_L_head
ebones["thigh.L"].tail = amwi * knee_L_head

ebones["calf.L"].head = amwi * knee_L_head
ebones["calf.L"].tail = amwi * ankle_L_head

ebones["foot.L"].head = amwi * ankle_L_head
ebones["foot.L"].tail = amwi * ankle_L_tail

ebones["ball.L"].head = amwi * ball_L_head
ebones["ball.L"].tail = amwi * ball_L_tail

ebones["toe_joint.L"].head = amwi * toe_L_head
ebones["toe_joint.L"].tail = amwi * toe_L_tail


ebones["ball.L"].length /=2


ebones["toe_deform01_joint01.L"].head = amwi * toe_deform01_joint01_L_head
ebones["toe_deform01_joint01.L"].tail = amwi * toe_deform01_joint01_L_tail

ebones["toe_deform01_end.L"].head = amwi * toe_deform01_end_L_head
ebones["toe_deform01_end.L"].tail = amwi * toe_deform01_end_L_tail

ebones["toe_deform02_joint01.L"].head = amwi * toe_deform02_joint01_L_head
ebones["toe_deform02_joint01.L"].tail = amwi * toe_deform02_joint01_L_tail

ebones["toe_deform02_end.L"].head = amwi * toe_deform02_end_L_head
ebones["toe_deform02_end.L"].tail = amwi * toe_deform02_end_L_tail


#right hand
ebones["clavicle.R"].head = amwi * clavicle_R_head
ebones["clavicle.R"].tail = amwi * shoulder_R_head

ebones["upperarm.R"].head = amwi * shoulder_R_head
ebones["upperarm.R"].tail = amwi * elbow_R_head

ebones["lowerarm.R"].head = amwi * elbow_R_head
ebones["lowerarm.R"].tail = amwi * forearm_R_head

ebones["lowerarm_twist_01.R"].head = amwi * forearm_R_head
ebones["lowerarm_twist_01.R"].tail = amwi * wrist_R_head
ebones["lowerarm_twist_02.R"].head = amwi * forearm_R_head
ebones["lowerarm_twist_02.R"].tail = amwi * wrist_R_head

ebones["hand.R"].head = amwi * wrist_R_head
ebones["hand.R"].tail = amwi * hand_R_head

ebones["thumb_01.R"].head = amwi * finger01_joint01_R_head
ebones["thumb_01.R"].tail = amwi * finger01_joint02_R_head

ebones["thumb_02.R"].head = amwi * finger01_joint02_R_head
ebones["thumb_02.R"].tail = amwi * finger01_joint03_R_head

ebones["thumb_03.R"].head = amwi * finger01_joint03_R_head
ebones["thumb_03.R"].tail = amwi * finger01_end_R_head

ebones["thumb_end.R"].head = amwi * finger01_end_R_head
ebones["thumb_end.R"].tail = amwi * finger01_end_R_head + Vector ((0,0,0.005))

#############
ebones["index_metacarpal.R"].head = amwi * finger02_joint01_R_head
ebones["index_metacarpal.R"].tail = amwi * finger02_joint02_R_head

ebones["index_01.R"].head = amwi * finger02_joint02_R_head
ebones["index_01.R"].tail = amwi * finger02_joint03_R_head

ebones["index_02.R"].head = amwi * finger02_joint03_R_head
ebones["index_02.R"].tail = amwi * finger02_joint04_R_head

ebones["index_03.R"].head = amwi * finger02_joint04_R_head
ebones["index_03.R"].tail = amwi * finger02_end_R_head


ebones["index_end.R"].head = amwi * finger02_end_R_head
ebones["index_end.R"].tail = amwi * finger02_end_R_head + Vector ((0,0,0.005))

#############
ebones["middle_metacarpal.R"].head = amwi * finger03_joint01_R_head
ebones["middle_metacarpal.R"].tail = amwi * finger03_joint02_R_head

ebones["middle_01.R"].head = amwi * finger03_joint02_R_head
ebones["middle_01.R"].tail = amwi * finger03_joint03_R_head

ebones["middle_02.R"].head = amwi * finger03_joint03_R_head
ebones["middle_02.R"].tail = amwi * finger03_joint04_R_head

ebones["middle_03.R"].head = amwi * finger03_joint04_R_head
ebones["middle_03.R"].tail = amwi * finger03_end_R_head


ebones["middle_end.R"].head = amwi * finger03_end_R_head
ebones["middle_end.R"].tail = amwi * finger03_end_R_head + Vector ((0,0,0.005))

#############
ebones["ring_metacarpal.R"].head = amwi * finger04_joint01_R_head
ebones["ring_metacarpal.R"].tail = amwi * finger04_joint02_R_head

ebones["ring_01.R"].head = amwi * finger04_joint02_R_head
ebones["ring_01.R"].tail = amwi * finger04_joint03_R_head

ebones["ring_02.R"].head = amwi * finger04_joint03_R_head
ebones["ring_02.R"].tail = amwi * finger04_joint04_R_head

ebones["ring_03.R"].head = amwi * finger04_joint04_R_head
ebones["ring_03.R"].tail = amwi * finger04_end_R_head


ebones["ring_end.R"].head = amwi * finger04_end_R_head
ebones["ring_end.R"].tail = amwi * finger04_end_R_head + Vector ((0,0,0.005))

#############
ebones["pinky_metacarpal.R"].head = amwi * finger05_joint01_R_head
ebones["pinky_metacarpal.R"].tail = amwi * finger05_joint02_R_head

ebones["pinky_01.R"].head = amwi * finger05_joint02_R_head
ebones["pinky_01.R"].tail = amwi * finger05_joint03_R_head

ebones["pinky_02.R"].head = amwi * finger05_joint03_R_head
ebones["pinky_02.R"].tail = amwi * finger05_joint04_R_head

ebones["pinky_03.R"].head = amwi * finger05_joint04_R_head
ebones["pinky_03.R"].tail = amwi * finger05_end_R_head


ebones["pinky_end.R"].head = amwi * finger05_end_R_head
ebones["pinky_end.R"].tail = amwi * finger05_end_R_head + Vector ((0,0,0.005))


# fix right fingers on a straight line

finger_joint02_length = (ebones["index_01.R"].tail - ebones["index_01.R"].head).length
finger_joint03_length = (ebones["index_02.R"].tail - ebones["index_02.R"].head).length
finger_joint04_length = (ebones["index_03.R"].tail - ebones["index_03.R"].head).length

fingers_new_length = (ebones["index_end.R"].head - ebones["index_01.R"].head).length
fingers_old_length =  finger_joint02_length + finger_joint03_length + finger_joint04_length
finger_joint02_scale = finger_joint02_length/fingers_old_length
finger_joint03_scale = finger_joint03_length/fingers_old_length
finger_joint04_scale = finger_joint04_length/fingers_old_length



ebones["index_01.R"].head = ebones["index_01.R"].head
ebones["index_01.R"].tail = ebones["index_end.R"].head.copy()
ebones["index_01.R"].length = fingers_new_length * finger_joint02_scale

ebones["index_02.R"].head = ebones["index_01.R"].tail
ebones["index_02.R"].tail = ebones["index_end.R"].head
ebones["index_02.R"].length = fingers_new_length * finger_joint03_scale

ebones["index_03.R"].head = ebones["index_02.R"].tail
ebones["index_03.R"].tail = ebones["index_end.R"].head
ebones["index_03.R"].length = fingers_new_length * finger_joint04_scale


finger_joint02_length = (ebones["middle_01.R"].tail - ebones["middle_01.R"].head).length
finger_joint03_length = (ebones["middle_02.R"].tail - ebones["middle_02.R"].head).length
finger_joint04_length = (ebones["middle_03.R"].tail - ebones["middle_03.R"].head).length

fingers_new_length = (ebones["middle_end.R"].head - ebones["middle_01.R"].head).length
fingers_old_length =  finger_joint02_length + finger_joint03_length + finger_joint04_length
finger_joint02_scale = finger_joint02_length/fingers_old_length
finger_joint03_scale = finger_joint03_length/fingers_old_length
finger_joint04_scale = finger_joint04_length/fingers_old_length



ebones["middle_01.R"].head = ebones["middle_01.R"].head
ebones["middle_01.R"].tail = ebones["middle_end.R"].head.copy()
ebones["middle_01.R"].length = fingers_new_length * finger_joint02_scale

ebones["middle_02.R"].head = ebones["middle_01.R"].tail
ebones["middle_02.R"].tail = ebones["middle_end.R"].head
ebones["middle_02.R"].length = fingers_new_length * finger_joint03_scale

ebones["middle_03.R"].head = ebones["middle_02.R"].tail
ebones["middle_03.R"].tail = ebones["middle_end.R"].head
ebones["middle_03.R"].length = fingers_new_length * finger_joint04_scale

finger_joint02_length = (ebones["ring_01.R"].tail - ebones["ring_01.R"].head).length
finger_joint03_length = (ebones["ring_02.R"].tail - ebones["ring_02.R"].head).length
finger_joint04_length = (ebones["ring_03.R"].tail - ebones["ring_03.R"].head).length

fingers_new_length = (ebones["ring_end.R"].head - ebones["ring_01.R"].head).length
fingers_old_length =  finger_joint02_length + finger_joint03_length + finger_joint04_length
finger_joint02_scale = finger_joint02_length/fingers_old_length
finger_joint03_scale = finger_joint03_length/fingers_old_length
finger_joint04_scale = finger_joint04_length/fingers_old_length



ebones["ring_01.R"].head = ebones["ring_01.R"].head
ebones["ring_01.R"].tail = ebones["ring_end.R"].head.copy()
ebones["ring_01.R"].length = fingers_new_length * finger_joint02_scale

ebones["ring_02.R"].head = ebones["ring_01.R"].tail
ebones["ring_02.R"].tail = ebones["ring_end.R"].head
ebones["ring_02.R"].length = fingers_new_length * finger_joint03_scale

ebones["ring_03.R"].head = ebones["ring_02.R"].tail
ebones["ring_03.R"].tail = ebones["ring_end.R"].head
ebones["ring_03.R"].length = fingers_new_length * finger_joint04_scale


finger_joint02_length = (ebones["pinky_01.R"].tail - ebones["pinky_01.R"].head).length
finger_joint03_length = (ebones["pinky_02.R"].tail - ebones["pinky_02.R"].head).length
finger_joint04_length = (ebones["pinky_03.R"].tail - ebones["pinky_03.R"].head).length

fingers_new_length = (ebones["pinky_end.R"].head - ebones["pinky_01.R"].head).length
fingers_old_length =  finger_joint02_length + finger_joint03_length + finger_joint04_length
finger_joint02_scale = finger_joint02_length/fingers_old_length
finger_joint03_scale = finger_joint03_length/fingers_old_length
finger_joint04_scale = finger_joint04_length/fingers_old_length



ebones["pinky_01.R"].head = ebones["pinky_01.R"].head
ebones["pinky_01.R"].tail = ebones["pinky_end.R"].head.copy()
ebones["pinky_01.R"].length = fingers_new_length * finger_joint02_scale

ebones["pinky_02.R"].head = ebones["pinky_01.R"].tail
ebones["pinky_02.R"].tail = ebones["pinky_end.R"].head
ebones["pinky_02.R"].length = fingers_new_length * finger_joint03_scale

ebones["pinky_03.R"].head = ebones["pinky_02.R"].tail
ebones["pinky_03.R"].tail = ebones["pinky_end.R"].head
ebones["pinky_03.R"].length = fingers_new_length * finger_joint04_scale

#left hand
ebones["clavicle.L"].head = amwi * clavicle_L_head
ebones["clavicle.L"].tail = amwi * shoulder_L_head

ebones["upperarm.L"].head = amwi * shoulder_L_head
ebones["upperarm.L"].tail = amwi * elbow_L_head

ebones["lowerarm.L"].head = amwi * elbow_L_head
ebones["lowerarm.L"].tail = amwi * forearm_L_head

ebones["lowerarm_twist_01.L"].head = amwi * forearm_L_head
ebones["lowerarm_twist_01.L"].tail = amwi * wrist_L_head
ebones["lowerarm_twist_02.L"].head = amwi * forearm_L_head
ebones["lowerarm_twist_02.L"].tail = amwi * wrist_L_head

ebones["hand.L"].head = amwi * wrist_L_head
ebones["hand.L"].tail = amwi * hand_L_head

ebones["thumb_01.L"].head = amwi * finger01_joint01_L_head
ebones["thumb_01.L"].tail = amwi * finger01_joint02_L_head

ebones["thumb_02.L"].head = amwi * finger01_joint02_L_head
ebones["thumb_02.L"].tail = amwi * finger01_joint03_L_head

ebones["thumb_03.L"].head = amwi * finger01_joint03_L_head
ebones["thumb_03.L"].tail = amwi * finger01_end_L_head

ebones["thumb_end.L"].head = amwi * finger01_end_L_head
ebones["thumb_end.L"].tail = amwi * finger01_end_L_head + Vector ((0,0,0.005))

#############
ebones["index_metacarpal.L"].head = amwi * finger02_joint01_L_head
ebones["index_metacarpal.L"].tail = amwi * finger02_joint02_L_head

ebones["index_01.L"].head = amwi * finger02_joint02_L_head
ebones["index_01.L"].tail = amwi * finger02_joint03_L_head

ebones["index_02.L"].head = amwi * finger02_joint03_L_head
ebones["index_02.L"].tail = amwi * finger02_joint04_L_head

ebones["index_03.L"].head = amwi * finger02_joint04_L_head
ebones["index_03.L"].tail = amwi * finger02_end_L_head


ebones["index_end.L"].head = amwi * finger02_end_L_head
ebones["index_end.L"].tail = amwi * finger02_end_L_head + Vector ((0,0,0.005))


#armature_data = bpy.data.objects['Armature']
#ebones = armature_data.data.edit_bones


#############
ebones["middle_metacarpal.L"].head = amwi * finger03_joint01_L_head
ebones["middle_metacarpal.L"].tail = amwi * finger03_joint02_L_head

ebones["middle_01.L"].head = amwi * finger03_joint02_L_head
ebones["middle_01.L"].tail = amwi * finger03_joint03_L_head

ebones["middle_02.L"].head = amwi * finger03_joint03_L_head
ebones["middle_02.L"].tail = amwi * finger03_joint04_L_head

ebones["middle_03.L"].head = amwi * finger03_joint04_L_head
ebones["middle_03.L"].tail = amwi * finger03_end_L_head


ebones["middle_end.L"].head = amwi * finger03_end_L_head
ebones["middle_end.L"].tail = amwi * finger03_end_L_head + Vector ((0,0,0.005))


#############
ebones["ring_metacarpal.L"].head = amwi * finger04_joint01_L_head
ebones["ring_metacarpal.L"].tail = amwi * finger04_joint02_L_head

ebones["ring_01.L"].head = amwi * finger04_joint02_L_head
ebones["ring_01.L"].tail = amwi * finger04_joint03_L_head

ebones["ring_02.L"].head = amwi * finger04_joint03_L_head
ebones["ring_02.L"].tail = amwi * finger04_joint04_L_head

ebones["ring_03.L"].head = amwi * finger04_joint04_L_head
ebones["ring_03.L"].tail = amwi * finger04_end_L_head


ebones["ring_end.L"].head = amwi * finger04_end_L_head
ebones["ring_end.L"].tail = amwi * finger04_end_L_head + Vector ((0,0,0.005))


#############
ebones["pinky_metacarpal.L"].head = amwi * finger05_joint01_L_head
ebones["pinky_metacarpal.L"].tail = amwi * finger05_joint02_L_head

ebones["pinky_01.L"].head = amwi * finger05_joint02_L_head
ebones["pinky_01.L"].tail = amwi * finger05_joint03_L_head

ebones["pinky_02.L"].head = amwi * finger05_joint03_L_head
ebones["pinky_02.L"].tail = amwi * finger05_joint04_L_head

ebones["pinky_03.L"].head = amwi * finger05_joint04_L_head
ebones["pinky_03.L"].tail = amwi * finger05_end_L_head


ebones["pinky_end.L"].head = amwi * finger05_end_L_head
ebones["pinky_end.L"].tail = amwi * finger05_end_L_head + Vector ((0,0,0.005))

# fix left fingers on a straight line

finger_joint02_length = (ebones["index_01.L"].tail - ebones["index_01.L"].head).length
finger_joint03_length = (ebones["index_02.L"].tail - ebones["index_02.L"].head).length
finger_joint04_length = (ebones["index_03.L"].tail - ebones["index_03.L"].head).length

fingers_new_length = (ebones["index_end.L"].head - ebones["index_01.L"].head).length
fingers_old_length =  finger_joint02_length + finger_joint03_length + finger_joint04_length
finger_joint02_scale = finger_joint02_length/fingers_old_length
finger_joint03_scale = finger_joint03_length/fingers_old_length
finger_joint04_scale = finger_joint04_length/fingers_old_length



ebones["index_01.L"].head = ebones["index_01.L"].head
ebones["index_01.L"].tail = ebones["index_end.L"].head.copy()
ebones["index_01.L"].length = fingers_new_length * finger_joint02_scale

ebones["index_02.L"].head = ebones["index_01.L"].tail
ebones["index_02.L"].tail = ebones["index_end.L"].head
ebones["index_02.L"].length = fingers_new_length * finger_joint03_scale

ebones["index_03.L"].head = ebones["index_02.L"].tail
ebones["index_03.L"].tail = ebones["index_end.L"].head
ebones["index_03.L"].length = fingers_new_length * finger_joint04_scale


finger_joint02_length = (ebones["middle_01.L"].tail - ebones["middle_01.L"].head).length
finger_joint03_length = (ebones["middle_02.L"].tail - ebones["middle_02.L"].head).length
finger_joint04_length = (ebones["middle_03.L"].tail - ebones["middle_03.L"].head).length

fingers_new_length = (ebones["middle_end.L"].head - ebones["middle_01.L"].head).length
fingers_old_length =  finger_joint02_length + finger_joint03_length + finger_joint04_length
finger_joint02_scale = finger_joint02_length/fingers_old_length
finger_joint03_scale = finger_joint03_length/fingers_old_length
finger_joint04_scale = finger_joint04_length/fingers_old_length



ebones["middle_01.L"].head = ebones["middle_01.L"].head
ebones["middle_01.L"].tail = ebones["middle_end.L"].head.copy()
ebones["middle_01.L"].length = fingers_new_length * finger_joint02_scale

ebones["middle_02.L"].head = ebones["middle_01.L"].tail
ebones["middle_02.L"].tail = ebones["middle_end.L"].head
ebones["middle_02.L"].length = fingers_new_length * finger_joint03_scale

ebones["middle_03.L"].head = ebones["middle_02.L"].tail
ebones["middle_03.L"].tail = ebones["middle_end.L"].head
ebones["middle_03.L"].length = fingers_new_length * finger_joint04_scale

finger_joint02_length = (ebones["ring_01.L"].tail - ebones["ring_01.L"].head).length
finger_joint03_length = (ebones["ring_02.L"].tail - ebones["ring_02.L"].head).length
finger_joint04_length = (ebones["ring_03.L"].tail - ebones["ring_03.L"].head).length

fingers_new_length = (ebones["ring_end.L"].head - ebones["ring_01.L"].head).length
fingers_old_length =  finger_joint02_length + finger_joint03_length + finger_joint04_length
finger_joint02_scale = finger_joint02_length/fingers_old_length
finger_joint03_scale = finger_joint03_length/fingers_old_length
finger_joint04_scale = finger_joint04_length/fingers_old_length



ebones["ring_01.L"].head = ebones["ring_01.L"].head
ebones["ring_01.L"].tail = ebones["ring_end.L"].head.copy()
ebones["ring_01.L"].length = fingers_new_length * finger_joint02_scale

ebones["ring_02.L"].head = ebones["ring_01.L"].tail
ebones["ring_02.L"].tail = ebones["ring_end.L"].head
ebones["ring_02.L"].length = fingers_new_length * finger_joint03_scale

ebones["ring_03.L"].head = ebones["ring_02.L"].tail
ebones["ring_03.L"].tail = ebones["ring_end.L"].head
ebones["ring_03.L"].length = fingers_new_length * finger_joint04_scale


finger_joint02_length = (ebones["pinky_01.L"].tail - ebones["pinky_01.L"].head).length
finger_joint03_length = (ebones["pinky_02.L"].tail - ebones["pinky_02.L"].head).length
finger_joint04_length = (ebones["pinky_03.L"].tail - ebones["pinky_03.L"].head).length

fingers_new_length = (ebones["pinky_end.L"].head - ebones["pinky_01.L"].head).length
fingers_old_length =  finger_joint02_length + finger_joint03_length + finger_joint04_length
finger_joint02_scale = finger_joint02_length/fingers_old_length
finger_joint03_scale = finger_joint03_length/fingers_old_length
finger_joint04_scale = finger_joint04_length/fingers_old_length



ebones["pinky_01.L"].head = ebones["pinky_01.L"].head
ebones["pinky_01.L"].tail = ebones["pinky_end.L"].head.copy()
ebones["pinky_01.L"].length = fingers_new_length * finger_joint02_scale

ebones["pinky_02.L"].head = ebones["pinky_01.L"].tail
ebones["pinky_02.L"].tail = ebones["pinky_end.L"].head
ebones["pinky_02.L"].length = fingers_new_length * finger_joint03_scale

ebones["pinky_03.L"].head = ebones["pinky_02.L"].tail
ebones["pinky_03.L"].tail = ebones["pinky_end.L"].head
ebones["pinky_03.L"].length = fingers_new_length * finger_joint04_scale

#breast R

ebones["breast_joint.R"].head = amwi * breast_joint_R_head
ebones["breast_joint.R"].tail = amwi * breast_joint_R_tail

ebones["breast_scale_joint.R"].head = amwi * breast_scale_joint_R_head #actual breast_joint_R_tail
ebones["breast_scale_joint.R"].tail = amwi * breast_scale_joint_R_tail #actual nipple_joint01_R_head


ebones["nipple_joint01.R"].head = amwi * nipple_joint01_R_head
ebones["nipple_joint01.R"].tail = amwi * nipple_joint01_R_tail

#lets make the nipple twice distance to get the jointEnd tail then correct it back
ebones["nipple_joint01.R"].length *= 2
nipple_joint01_R_tail_doubled = ebones["nipple_joint01.R"].tail.copy()
ebones["nipple_joint01.R"].length /= 2

ebones["nipple_end.R"].head = amwi * nipple_joint01_R_tail
ebones["nipple_end.R"].tail = nipple_joint01_R_tail_doubled

#deform01
ebones["breast_deform01_joint01.R"].head = amwi * breast_joint_R_tail
ebones["breast_deform01_joint01.R"].tail = amwi * breast_deform01_joint01_R_tail
deform01_length = ebones["breast_deform01_joint01.R"].length
ebones["breast_deform01_joint01.R"].length += 	deform01_length*0.1							#make the tail a bit longer
breast_deform01_joint01_R_tail_longer = ebones["breast_deform01_joint01.R"].tail.copy()
ebones["breast_deform01_joint01.R"].length -= 	deform01_length*0.1							#fix the tail
#ebones["breast_deform01_joint01.R"].tail = amwi * breast_deform01_joint01_R_tail 	

ebones["breast_deform01_end.R"].head = amwi * breast_deform01_joint01_R_tail
ebones["breast_deform01_end.R"].tail = breast_deform01_joint01_R_tail_longer

#deform02
ebones["breast_deform02_joint01.R"].head = amwi * breast_joint_R_tail
ebones["breast_deform02_joint01.R"].tail = amwi * breast_deform02_joint01_R_tail
deform02_length = ebones["breast_deform02_joint01.R"].length
ebones["breast_deform02_joint01.R"].length += 	deform02_length*0.1							#make the tail a bit longer
breast_deform02_joint01_R_tail_longer = ebones["breast_deform02_joint01.R"].tail.copy()
ebones["breast_deform02_joint01.R"].length -= 	deform02_length*0.1							#fix the tail
#ebones["breast_deform02_joint01.R"].tail = amwi * breast_deform02_joint01_R_tail 	

ebones["breast_deform02_end.R"].head = amwi * breast_deform02_joint01_R_tail
ebones["breast_deform02_end.R"].tail = breast_deform02_joint01_R_tail_longer

#deform03
ebones["breast_deform03_joint01.R"].head = amwi * breast_joint_R_tail
ebones["breast_deform03_joint01.R"].tail = amwi * breast_deform03_joint01_R_tail
deform03_length = ebones["breast_deform03_joint01.R"].length
ebones["breast_deform03_joint01.R"].length += 	deform03_length*0.1							#make the tail a bit longer
breast_deform03_joint01_R_tail_longer = ebones["breast_deform03_joint01.R"].tail.copy()
ebones["breast_deform03_joint01.R"].length -= 	deform03_length*0.1							#fix the tail
#ebones["breast_deform03_joint01.R"].tail = amwi * breast_deform03_joint01_R_tail 	

ebones["breast_deform03_end.R"].head = amwi * breast_deform03_joint01_R_tail
ebones["breast_deform03_end.R"].tail = breast_deform03_joint01_R_tail_longer

#breast L

ebones["breast_joint.L"].head = amwi * breast_joint_L_head
ebones["breast_joint.L"].tail = amwi * breast_joint_L_tail

ebones["breast_scale_joint.L"].head = amwi * breast_scale_joint_L_head #actual breast_joint_L_tail
ebones["breast_scale_joint.L"].tail = amwi * breast_scale_joint_L_tail #actual nipple_joint01_L_head


ebones["nipple_joint01.L"].head = amwi * nipple_joint01_L_head
ebones["nipple_joint01.L"].tail = amwi * nipple_joint01_L_tail

#lets make the nipple twice distance to get the jointEnd tail then correct it back
ebones["nipple_joint01.L"].length *= 2
nipple_joint01_L_tail_doubled = ebones["nipple_joint01.L"].tail.copy()
ebones["nipple_joint01.L"].length /= 2

ebones["nipple_end.L"].head = amwi * nipple_joint01_L_tail
ebones["nipple_end.L"].tail = nipple_joint01_L_tail_doubled

#deform01
ebones["breast_deform01_joint01.L"].head = amwi * breast_joint_L_tail
ebones["breast_deform01_joint01.L"].tail = amwi * breast_deform01_joint01_L_tail
deform01_length = ebones["breast_deform01_joint01.L"].length
ebones["breast_deform01_joint01.L"].length += 	deform01_length*0.1							#make the tail a bit longer
breast_deform01_joint01_L_tail_longer = ebones["breast_deform01_joint01.L"].tail.copy()
ebones["breast_deform01_joint01.L"].length -= 	deform01_length*0.1							#fix the tail
#ebones["breast_deform01_joint01.L"].tail = amwi * breast_deform01_joint01_L_tail 	

ebones["breast_deform01_end.L"].head = amwi * breast_deform01_joint01_L_tail
ebones["breast_deform01_end.L"].tail = breast_deform01_joint01_L_tail_longer

#deform02
ebones["breast_deform02_joint01.L"].head = amwi * breast_joint_L_tail
ebones["breast_deform02_joint01.L"].tail = amwi * breast_deform02_joint01_L_tail
deform02_length = ebones["breast_deform02_joint01.L"].length
ebones["breast_deform02_joint01.L"].length += 	deform02_length*0.1							#make the tail a bit longer
breast_deform02_joint01_L_tail_longer = ebones["breast_deform02_joint01.L"].tail.copy()
ebones["breast_deform02_joint01.L"].length -= 	deform02_length*0.1							#fix the tail
#ebones["breast_deform02_joint01.L"].tail = amwi * breast_deform02_joint01_L_tail 	

ebones["breast_deform02_end.L"].head = amwi * breast_deform02_joint01_L_tail
ebones["breast_deform02_end.L"].tail = breast_deform02_joint01_L_tail_longer

#deform03
ebones["breast_deform03_joint01.L"].head = amwi * breast_joint_L_tail
ebones["breast_deform03_joint01.L"].tail = amwi * breast_deform03_joint01_L_tail
deform03_length = ebones["breast_deform03_joint01.L"].length
ebones["breast_deform03_joint01.L"].length += 	deform03_length*0.1							#make the tail a bit longer
breast_deform03_joint01_L_tail_longer = ebones["breast_deform03_joint01.L"].tail.copy()
ebones["breast_deform03_joint01.L"].length -= 	deform03_length*0.1							#fix the tail
#ebones["breast_deform03_joint01.L"].tail = amwi * breast_deform03_joint01_L_tail 	

ebones["breast_deform03_end.L"].head = amwi * breast_deform03_joint01_L_tail
ebones["breast_deform03_end.L"].tail = breast_deform03_joint01_L_tail_longer



ebones["stomach_joint01"].head = amwi * stomach_joint01_head
ebones["stomach_joint01"].tail = amwi * stomach_joint01_tail
ebones["stomach_end"].head = amwi * stomach_end_head
ebones["stomach_end"].tail = amwi * stomach_end_tail

ebones["rib_joint01.R"].head = amwi * rib_joint01_R_head
ebones["rib_joint01.R"].tail = amwi * rib_joint01_R_tail
ebones["rib_end.R"].head = amwi * rib_end_R_head
ebones["rib_end.R"].tail = amwi * rib_end_R_tail

ebones["butt_joint01.R"].head = amwi * butt_joint01_R_head
ebones["butt_joint01.R"].tail = amwi * butt_joint01_R_tail
ebones["butt_end.R"].head = amwi * butt_end_R_head
ebones["butt_end.R"].tail = amwi * butt_end_R_tail

ebones["rib_joint01.L"].head = amwi * rib_joint01_L_head
ebones["rib_joint01.L"].tail = amwi * rib_joint01_L_tail
ebones["rib_end.L"].head = amwi * rib_end_L_head
ebones["rib_end.L"].tail = amwi * rib_end_L_tail

ebones["butt_joint01.L"].head = amwi * butt_joint01_L_head
ebones["butt_joint01.L"].tail = amwi * butt_joint01_L_tail
ebones["butt_end.L"].head = amwi * butt_end_L_head
ebones["butt_end.L"].tail = amwi * butt_end_L_tail

