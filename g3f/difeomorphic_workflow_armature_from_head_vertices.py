import bpy
from mathutils import Matrix
from ..g3f.difeomorphic_workflow_init_custom_vertex_indices import *
from ..g3f.difeomorphic_workflow_armature_utils import *

def getArmatureBonesDictFromHeadVertices(bones_dict):
    print("getArmatureBonesDictFromHeadVertices()...")
    armature_data = bpy.data.objects['Armature']
    armature_bones = armature_data.data.bones

    # per extra_bones_eyes.json
    eyes_bone_names = [
        "eye_orbit.L", "eye_joint.L",
        "eye_orbit.R", "eye_joint.R",
    ]
    # per extra_bones_jaw.json
    jaw_bone_names = [
        "lower_jaw_joint01", "lower_jaw_end",
        "chin_joint01", "chin_end",
    ]
    # remaining face bones (ears, cheeks, eyebrows, nose, forehead, lips)
    face_bone_names = [
        "ear_joint01.L", "ear_end.L", "ear_joint01.R", "ear_end.R",
        "cheek_joint01.L", "cheek_end.L", "cheek_joint01.R", "cheek_end.R",
        "eye_brow_joint01.L", "eye_brow_joint02.L", "eye_brow_end.L",
        "eye_brow_joint01.R", "eye_brow_joint02.R", "eye_brow_end.R",
        "nose_joint01", "nose_joint02", "nose_end",
        "forehead_joint01", "forehead_end",
        "upper_lip_joint01.L", "upper_lip_joint02.L", "upper_lip_joint03.L", "upper_lip_end.L",
        "upper_lip_joint01.R", "upper_lip_joint02.R", "upper_lip_joint03.R", "upper_lip_end.R",
        "lower_lip_joint01.L", "lower_lip_joint02.L", "lower_lip_joint03.L", "lower_lip_end.L",
        "lower_lip_joint01.R", "lower_lip_joint02.R", "lower_lip_joint03.R", "lower_lip_end.R",
    ]

    has_eyes = any(b in armature_bones for b in eyes_bone_names)
    has_jaw = any(b in armature_bones for b in jaw_bone_names)
    has_face = any(b in armature_bones for b in face_bone_names)

    amw = armature_data.matrix_world
    amwi = amw.inverted()
    amwi = Matrix.Identity(4)
    difeomorphic_body = "Genesis 3 Female Mesh"
    
    #
    """                 bpy.ops.object.mode_set(mode='OBJECT')
                #
                bpy.ops.object.select_all(action='DESELECT')
                bpy.ops.object.mode_set(mode='OBJECT')
                bpy.data.objects[difeomorphic_body].select = True
                bpy.context.scene.objects.active = bpy.data.objects[difeomorphic_body] """
    obj = bpy.data.objects[difeomorphic_body]
    
    ############################################################
    ear_L_head = getCenter (ear_base_L, obj)
    ear_L_tail = getCenter (ear_tip_L, obj)
    ear_end_L_head = ear_L_tail.copy()
    ear_end_L_tail = ear_L_tail.copy()
    ear_end_L_tail.x += 0.01

    ear_R_head = getCenter (ear_base_R, obj)
    ear_R_tail = getCenter (ear_tip_R, obj)
    ear_end_R_head = ear_R_tail.copy()
    ear_end_R_tail = ear_R_tail.copy()
    ear_end_R_tail.x -= 0.01

    #############################################################
    cheek_joint01_L_head = getCenter (cheek_base_L, obj)
    cheek_joint01_L_tail = getCenter (cheek_top_L, obj)
    cheek_end_L_head = cheek_joint01_L_tail.copy()
    cheek_end_L_tail = cheek_joint01_L_tail.copy()
    cheek_end_L_tail.x += 0.01

    cheek_joint01_R_head = getCenter (cheek_base_R, obj)
    cheek_joint01_R_tail = getCenter (cheek_top_R, obj)
    cheek_end_R_head = cheek_joint01_R_tail.copy()
    cheek_end_R_tail = cheek_joint01_R_tail.copy()
    cheek_end_R_tail.x -= 0.01

    #############################################################
    eye_socket_joint_L_head = getCenter (eye_socket_base_L, obj)
    eye_socket_joint_L_tail = getCenter (eye_base_L, obj)
    eye_socket_joint_L_head.x=eye_socket_joint_L_tail.x
    eye_socket_joint_L_head.z=eye_socket_joint_L_tail.z
    eye_joint_L_head = eye_socket_joint_L_tail.copy()
    eye_joint_L_tail = eye_socket_joint_L_tail.copy()
    eye_joint_L_tail.x += 0.01

    eye_brow_joint01_L_head = getCenter (eye_brow_joint01_base_L, obj)
    eye_brow_joint02_L_head = getCenter (eye_brow_joint02_base_L, obj)
    eye_brow_end_L_head = getCenter (eye_brow_end_base_L, obj)
    eye_brow_end_L_tail = eye_brow_end_L_head.copy()
    eye_brow_end_L_tail.x += 0.01


    eye_socket_joint_R_head = getCenter (eye_socket_base_R, obj)
    eye_socket_joint_R_tail = getCenter (eye_base_R, obj)
    eye_socket_joint_R_head.x=eye_socket_joint_R_tail.x
    eye_socket_joint_R_head.z=eye_socket_joint_R_tail.z
    eye_joint_R_head = eye_socket_joint_R_tail.copy()
    eye_joint_R_tail = eye_socket_joint_R_tail.copy()
    eye_joint_R_tail.x -= 0.01

    eye_brow_joint01_R_head = getCenter (eye_brow_joint01_base_R, obj)
    eye_brow_joint02_R_head = getCenter (eye_brow_joint02_base_R, obj)
    eye_brow_end_R_head = getCenter (eye_brow_end_base_R, obj)
    eye_brow_end_R_tail = eye_brow_end_R_head.copy()
    eye_brow_end_R_tail.x -= 0.01

    #############################################################
    nose_joint01_head = getCenter (nose_joint01_base, obj)
    nose_joint02_tail = getCenter (nose_joint02_tip, obj)
    #
    nose_joint01_tail = nose_joint01_head.copy()
    nose_joint01_tail.z = nose_joint02_tail.z
    nose_joint02_head = nose_joint01_tail.copy() 
    nose_joint02_head.y = nose_joint01_head.y
    #
    nose_end_head = nose_joint02_tail.copy() 
    nose_end_tail = nose_end_head.copy() 
    nose_end_tail.x -= 0.01

    forehead_joint01_head = nose_joint01_head.copy()
    forehead_joint01_tail = getCenter (forehead, obj)

    forehead_end_head = forehead_joint01_tail.copy()
    forehead_end_tail = forehead_end_head.copy()
    forehead_end_tail.x -= 0.01
    #############################################################
    upper_lip_joint01_L_head = getCenter (upper_lip_joint01_base_L, obj)
    upper_lip_joint01_L_head.x -= 0.001
    upper_lip_joint02_L_head = getCenter (upper_lip_joint02_base_L, obj)
    upper_lip_joint03_L_head = getCenter (upper_lip_joint03_base_L, obj)
    
    #upper_lip_end_L_head = getCenter (upper_lip_end_center, obj)
    #upper_lip_end_L_head.x += 0.001 #slight adjust
    upper_lip_end_L_head = getCenter (upper_lip_end_L, obj)


    upper_lip_joint01_L_tail = upper_lip_joint02_L_head.copy()
    upper_lip_joint02_L_tail = upper_lip_joint03_L_head.copy()
    upper_lip_joint03_L_tail = upper_lip_end_L_head.copy()
    upper_lip_end_L_tail = upper_lip_end_L_head.copy()
    upper_lip_end_L_tail.x += 0.005

    upper_lip_joint01_R_head = getCenter (upper_lip_joint01_base_R, obj)
    upper_lip_joint01_R_head.x += 0.001
    upper_lip_joint02_R_head = getCenter (upper_lip_joint02_base_R, obj)
    upper_lip_joint03_R_head = getCenter (upper_lip_joint03_base_R, obj)
    #upper_lip_end_R_head = getCenter (upper_lip_end_center, obj)
    #upper_lip_end_R_head.x -= 0.001 #slight adjust
    upper_lip_end_R_head = getCenter (upper_lip_end_R, obj)

    upper_lip_joint01_R_tail = upper_lip_joint02_R_head.copy()
    upper_lip_joint02_R_tail = upper_lip_joint03_R_head.copy()
    upper_lip_joint03_R_tail = upper_lip_end_R_head.copy()
    upper_lip_end_R_tail = upper_lip_end_R_head.copy()
    upper_lip_end_R_tail.x -= 0.005
    ######################################
    lower_lip_joint01_L_head = getCenter (lower_lip_joint01_base_L, obj)
    lower_lip_joint01_L_head.x -= 0.001
    lower_lip_joint02_L_head = getCenter (lower_lip_joint02_base_L, obj)
    lower_lip_joint03_L_head = getCenter (lower_lip_joint03_base_L, obj)
    lower_lip_end_L_head = getCenter (lower_lip_end_center, obj)
    lower_lip_end_L_head.x += 0.001 #slight adjust

    lower_lip_joint01_L_tail = lower_lip_joint02_L_head.copy()
    lower_lip_joint02_L_tail = lower_lip_joint03_L_head.copy()
    lower_lip_joint03_L_tail = lower_lip_end_L_head.copy()
    lower_lip_end_L_tail = lower_lip_end_L_head.copy()
    lower_lip_end_L_tail.x += 0.005

    lower_lip_joint01_R_head = getCenter (lower_lip_joint01_base_R, obj)
    lower_lip_joint01_R_head.x += 0.001
    lower_lip_joint02_R_head = getCenter (lower_lip_joint02_base_R, obj)
    lower_lip_joint03_R_head = getCenter (lower_lip_joint03_base_R, obj)
    lower_lip_end_R_head = getCenter (lower_lip_end_center, obj)
    lower_lip_end_R_head.x -= 0.001 #slight adjust

    lower_lip_joint01_R_tail = lower_lip_joint02_R_head.copy()
    lower_lip_joint02_R_tail = lower_lip_joint03_R_head.copy()
    lower_lip_joint03_R_tail = lower_lip_end_R_head.copy()
    lower_lip_end_R_tail = lower_lip_end_R_head.copy()
    lower_lip_end_R_tail.x -= 0.005

    #############################################################
    lower_jaw_joint01_head = getCenter (lower_jaw_joint01_base, obj)
    lower_jaw_end_head = getCenter (lower_jaw_end_base, obj)
    chin_joint01_head = getCenter (lower_jaw_chin01_base, obj)
    chin_end_head = getCenter (lower_jaw_chin01_tip, obj)

    lower_jaw_joint01_tail = lower_jaw_end_head.copy()
    lower_jaw_end_tail = chin_joint01_head.copy()
    chin_joint01_tail = chin_end_head.copy()
    chin_end_tail = chin_joint01_tail.copy()
    chin_end_tail.x += 0.005
    #############################################################

    head01_head = getCenter (head_base, obj)
    head01_tail = head01_head.copy()
    head01_tail.z += 0.05
    head02_head = head01_head.copy()
    head02_tail = getCenter (head_top, obj)
    head02_tail.z +=0.03
    head_end_head = head02_tail.copy()
    head_end_tail = head02_tail.copy()
    head_end_tail.x += 0.02
    ##############################################################
    #right
    if has_face:
        bones_dict["ear_joint01.L"]= {"head" : amwi * ear_L_head, "tail" : amwi * ear_L_tail, "roll" : -90, "rollOverride" : 0, "connected" : False }
        bones_dict["ear_end.L"]= {"head" : amwi * ear_end_L_head, "tail" : amwi * ear_end_L_tail, "roll" : -180, "rollOverride" : 0, "connected" : False }

        bones_dict["ear_joint01.R"]= {"head" : amwi * ear_R_head, "tail" : amwi * ear_R_tail, "roll" : 90, "rollOverride" : 0, "connected" : False }
        bones_dict["ear_end.R"]= {"head" : amwi * ear_end_R_head, "tail" : amwi * ear_end_R_tail, "roll" : -180, "rollOverride" : 0, "connected" : False }

        bones_dict["cheek_joint01.R"]= {"head" : amwi * cheek_joint01_R_head, "tail" : amwi * cheek_joint01_R_tail, "roll" : 137, "rollOverride" : 0, "connected" : False }
        bones_dict["cheek_end.R"]= {"head" : amwi * cheek_end_R_head, "tail" : amwi * cheek_end_R_tail, "roll" : 180, "rollOverride" : 0, "connected" : False }

        bones_dict["cheek_joint01.L"]= {"head" : amwi * cheek_joint01_L_head, "tail" : amwi * cheek_joint01_L_tail, "roll" : -137, "rollOverride" : 0, "connected" : False }
        bones_dict["cheek_end.L"]= {"head" : amwi * cheek_end_L_head, "tail" : amwi * cheek_end_L_tail, "roll" : -180, "rollOverride" : 0, "connected" : False }

        bones_dict["eye_brow_joint01.L"]= {"head" : amwi * eye_brow_joint01_L_head, "tail" : amwi * eye_brow_joint02_L_head, "roll" : 90, "rollOverride" : 0, "connected" : False }
        bones_dict["eye_brow_joint02.L"]= {"head" : amwi * eye_brow_joint02_L_head, "tail" : amwi * eye_brow_end_L_head, "roll" : 103, "rollOverride" : 0, "connected" : False }
        bones_dict["eye_brow_end.L"]= {"head" : amwi * eye_brow_end_L_head, "tail" : amwi * eye_brow_end_L_tail, "roll" : -177, "rollOverride" : 0, "connected" : False }

        bones_dict["eye_brow_joint01.R"]= {"head" : amwi * eye_brow_joint01_R_head, "tail" : amwi * eye_brow_joint02_R_head, "roll" : -90, "rollOverride" : 0, "connected" : False }
        bones_dict["eye_brow_joint02.R"]= {"head" : amwi * eye_brow_joint02_R_head, "tail" : amwi * eye_brow_end_R_head, "roll" : -103, "rollOverride" : 0, "connected" : False }
        bones_dict["eye_brow_end.R"]= {"head" : amwi * eye_brow_end_R_head, "tail" : amwi * eye_brow_end_R_tail, "roll" : 177, "rollOverride" : 0, "connected" : False }

        bones_dict["nose_joint01"]= {"head" : amwi * nose_joint01_head, "tail" : amwi * nose_joint01_tail, "roll" : -90, "rollOverride" : 0, "connected" : False }
        bones_dict["nose_joint02"]= {"head" : amwi * nose_joint02_head, "tail" : amwi * nose_joint02_tail, "roll" : 90, "rollOverride" : 0, "connected" : False }
        bones_dict["nose_end"]= {"head" : amwi * nose_end_head, "tail" : amwi * nose_end_tail, "roll" : 0, "rollOverride" : 0, "connected" : False }

        bones_dict["forehead_joint01"]= {"head" : amwi * forehead_joint01_head, "tail" : amwi * forehead_joint01_tail, "roll" : 90, "rollOverride" : 0, "connected" : False }
        bones_dict["forehead_end"]= {"head" : amwi * forehead_end_head, "tail" : amwi * forehead_end_tail, "roll" : 0, "rollOverride" : 0, "connected" : False }

        bones_dict["upper_lip_joint01.L"]= {"head" : amwi * upper_lip_joint01_L_head, "tail" : amwi * upper_lip_joint01_L_tail, "roll" : 38, "rollOverride" : 0, "connected" : False }
        bones_dict["upper_lip_joint02.L"]= {"head" : amwi * upper_lip_joint02_L_head, "tail" : amwi * upper_lip_joint02_L_tail, "roll" : 122, "rollOverride" : 0, "connected" : False }
        bones_dict["upper_lip_joint03.L"]= {"head" : amwi * upper_lip_joint03_L_head, "tail" : amwi * upper_lip_joint03_L_tail, "roll" : 94, "rollOverride" : 0, "connected" : False }
        bones_dict["upper_lip_end.L"]= {"head" : amwi * upper_lip_end_L_head, "tail" : amwi * upper_lip_end_L_tail, "roll" : -180, "rollOverride" : 0, "connected" : False }

        bones_dict["lower_lip_joint01.L"]= {"head" : amwi * lower_lip_joint01_L_head, "tail" : amwi * lower_lip_joint01_L_tail, "roll" : 97, "rollOverride" : 0, "connected" : False }
        bones_dict["lower_lip_joint02.L"]= {"head" : amwi * lower_lip_joint02_L_head, "tail" : amwi * lower_lip_joint02_L_tail, "roll" : 84, "rollOverride" : 0, "connected" : False }
        bones_dict["lower_lip_joint03.L"]= {"head" : amwi * lower_lip_joint03_L_head, "tail" : amwi * lower_lip_joint03_L_tail, "roll" : 82, "rollOverride" : 0, "connected" : False }
        bones_dict["lower_lip_end.L"]= {"head" : amwi * lower_lip_end_L_head, "tail" : amwi * lower_lip_end_L_tail, "roll" : -180, "rollOverride" : 0, "connected" : False }

        bones_dict["upper_lip_joint01.R"]= {"head" : amwi * upper_lip_joint01_R_head, "tail" : amwi * upper_lip_joint01_R_tail, "roll" : -38, "rollOverride" : 0, "connected" : False }
        bones_dict["upper_lip_joint02.R"]= {"head" : amwi * upper_lip_joint02_R_head, "tail" : amwi * upper_lip_joint02_R_tail, "roll" : -122, "rollOverride" : 0, "connected" : False }
        bones_dict["upper_lip_joint03.R"]= {"head" : amwi * upper_lip_joint03_R_head, "tail" : amwi * upper_lip_joint03_R_tail, "roll" : -94, "rollOverride" : 0, "connected" : False }
        bones_dict["upper_lip_end.R"]= {"head" : amwi * upper_lip_end_R_head, "tail" : amwi * upper_lip_end_R_tail, "roll" : 180, "rollOverride" : 0, "connected" : False }

        bones_dict["lower_lip_joint01.R"]= {"head" : amwi * lower_lip_joint01_R_head, "tail" : amwi * lower_lip_joint01_R_tail, "roll" : -97, "rollOverride" : 0, "connected" : False }
        bones_dict["lower_lip_joint02.R"]= {"head" : amwi * lower_lip_joint02_R_head, "tail" : amwi * lower_lip_joint02_R_tail, "roll" : -84, "rollOverride" : 0, "connected" : False }
        bones_dict["lower_lip_joint03.R"]= {"head" : amwi * lower_lip_joint03_R_head, "tail" : amwi * lower_lip_joint03_R_tail, "roll" : -82, "rollOverride" : 0, "connected" : False }
        bones_dict["lower_lip_end.R"]= {"head" : amwi * lower_lip_end_R_head, "tail" : amwi * lower_lip_end_R_tail, "roll" : 180, "rollOverride" : 0, "connected" : False }

    if has_eyes:
        bones_dict["eye_socket_joint.L"]= {"head" : amwi * eye_socket_joint_L_head, "tail" : amwi * eye_socket_joint_L_tail, "roll" : 0, "rollOverride" : 0, "connected" : False }
        bones_dict["eye_joint.L"]= {"head" : amwi * eye_joint_L_head, "tail" : amwi * eye_joint_L_tail, "roll" : 0, "rollOverride" : 0, "connected" : False }
        bones_dict["eye_socket_joint.R"]= {"head" : amwi * eye_socket_joint_R_head, "tail" : amwi * eye_socket_joint_R_tail, "roll" : 0, "rollOverride" : 0, "connected" : False }
        bones_dict["eye_joint.R"]= {"head" : amwi * eye_joint_R_head, "tail" : amwi * eye_joint_R_tail, "roll" : 0, "rollOverride" : 0, "connected" : False }

    if has_jaw:
        bones_dict["lower_jaw_joint01"]= {"head" : amwi * lower_jaw_joint01_head, "tail" : amwi * lower_jaw_joint01_tail, "roll" : 0, "rollOverride" : 0, "connected" : False }
        bones_dict["lower_jaw_end"]= {"head" : amwi * lower_jaw_end_head, "tail" : amwi * lower_jaw_end_tail, "roll" : -180, "rollOverride" : 0, "connected" : False }
        bones_dict["chin_joint01"]= {"head" : amwi * chin_joint01_head, "tail" : amwi * chin_joint01_tail, "roll" : -180, "rollOverride" : 0, "connected" : False }
        bones_dict["chin_end"]= {"head" : amwi * chin_end_head, "tail" : amwi * chin_end_tail, "roll" : 0, "rollOverride" : 0, "connected" : False }

    bones_dict["head"]= {"head" : amwi * head02_head, "tail" : amwi * head02_tail, "roll" : 90, "rollOverride" : 0, "connected" : False }
    bones_dict["head_end"]= {"head" : amwi * head_end_head, "tail" : amwi * head_end_tail, "roll" : 0, "rollOverride" : 0, "connected" : False }

    bones_dict["head"]["roll"] = 90

    if has_eyes:
        bones_dict["eye_socket_joint.L"]["roll"] = 90
        bones_dict["eye_socket_joint.R"]["roll"] = -90
        bones_dict["eye_joint.L"]["roll"] = -177
        bones_dict["eye_joint.R"]["roll"] = 177

    