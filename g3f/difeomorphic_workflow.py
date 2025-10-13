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

if "bpy" in locals():
    import imp
    imp.reload(dict_bones)
else:
    from ..g3f import difeomorphic_workflow_dictionaries_bones as dict_bones



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
    fast_align_bones(cachedBonesData["pelvis"]["head"], cachedBonesData["pelvis"]["tail"], vx_armature, "base")
    #
    ebones["base"].tail.x =  ebones["base"].head.x
    ebones["base"].tail.y =  ebones["base"].head.y
    ebones["base"].tail.z =  ebones["base"].head.z + 0.02
    #
    #
    fast_align_bones(cachedBonesData["pelvis"]["head"], (cachedBonesData["pelvis"]["head"]+cachedBonesData["pelvis"]["tail"])/2, vx_armature, "pelvis_joint")
    fast_align_bones(cachedBonesData["abdomenLower"]["head"], cachedBonesData["abdomenLower"]["tail"], vx_armature, "spine_joint01")
    fast_align_bones(cachedBonesData["abdomenLower"]["tail"], cachedBonesData["chestLower"]["head"], vx_armature, "spine_joint02")
    fast_align_bones(cachedBonesData["chestLower"]["head"], (cachedBonesData["chestLower"]["tail"]+cachedBonesData["chestUpper"]["head"])/2, vx_armature, "spine_joint03")
    fast_align_bones((cachedBonesData["chestLower"]["tail"]+cachedBonesData["chestUpper"]["head"])/2, cachedBonesData["chestUpper"]["tail"], vx_armature, "spine_joint04")
    fast_align_bones(cachedBonesData["chestUpper"]["tail"], cachedBonesData["neckLower"]["head"], vx_armature, "spine_jointEnd")
    average_spine_y = (ebones["spine_joint01"].head.y + ebones["spine_joint04"].tail.y)/2
    #ebones["spine_joint02"].head.y =  ebones["spine_joint01"].tail.y
    #ebones["spine_joint02"].tail.y =  average_spine_y
    #ebones["spine_joint03"].head.y =  average_spine_y 
    #ebones["spine_joint03"].tail.y =  average_spine_y
    #ebones["spine_joint04"].head.y =  average_spine_y
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
    #["neckUpper", "neckUpper", "neck_jointEnd",90],
    #["head", "head", "head_joint01",90],
    #["head", "head", "head_joint02",90]
    #
    #
    # lets do the legs
    fast_align_bones(cachedBonesData["lThighBend"]["head"],cachedBonesData["lShin"]["head"] , vx_armature, "hip_joint.L",radians(0) ) # cachedBonesData["lThighBend"]["roll"])
    fast_align_bones(cachedBonesData["lThighTwist"]["head"],cachedBonesData["lShin"]["head"] , vx_armature, "thigh_twist_joint.L", radians(0) ) #cachedBonesData["lThighTwist"]["roll"])    
    fast_align_bones(cachedBonesData["lShin"]["head"],cachedBonesData["lFoot"]["head"] , vx_armature, "knee_joint.L", radians(0) ) #cachedBonesData["lShin"]["roll"])    
    fast_align_bones(cachedBonesData["lFoot"]["head"],cachedBonesData["lToe"]["head"] , vx_armature, "ankle_joint.L", radians(0) ) #cachedBonesData["lFoot"]["roll"])  
    fast_align_bones(cachedBonesData["lToe"]["head"],cachedBonesData["lToe"]["tail"] , vx_armature, "ball_joint.L", radians(0) ) #cachedBonesData["lToe"]["roll"])  
    #
    fast_align_bones(cachedBonesData["rThighBend"]["head"],cachedBonesData["rShin"]["head"] , vx_armature, "hip_joint.R", radians(0) ) #cachedBonesData["rThighBend"]["roll"])
    fast_align_bones(cachedBonesData["rThighTwist"]["head"],cachedBonesData["rShin"]["head"] , vx_armature, "thigh_twist_joint.R", radians(0) ) #cachedBonesData["rThighTwist"]["roll"])    
    fast_align_bones(cachedBonesData["rShin"]["head"],cachedBonesData["rFoot"]["head"] , vx_armature, "knee_joint.R", radians(0) ) #cachedBonesData["rShin"]["roll"])    
    fast_align_bones(cachedBonesData["rFoot"]["head"],cachedBonesData["rToe"]["head"] , vx_armature, "ankle_joint.R", radians(0) ) #cachedBonesData["rFoot"]["roll"])  
    fast_align_bones(cachedBonesData["rToe"]["head"],cachedBonesData["rToe"]["tail"] , vx_armature, "ball_joint.R", radians(0) ) #cachedBonesData["rToe"]["roll"])  
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
    fast_align_bones(cachedBonesData["lCollar"]["head"],cachedBonesData["lCollar"]["tail"] , vx_armature, "clavicle_joint.L",radians(0) ) # cachedBonesData["lCollar"]["roll"])
    fast_align_bones(cachedBonesData["lShldrBend"]["head"],cachedBonesData["lForearmBend"]["head"] , vx_armature, "shoulder_joint.L", radians(90)) # cachedBonesData["lShldrBend"]["roll"])    
    fast_align_bones(cachedBonesData["lShldrTwist"]["head"],cachedBonesData["lForearmBend"]["head"] , vx_armature, "shoulder_twist_joint.L", radians(90)) #cachedBonesData["lShldrTwist"]["roll"])        
    fast_align_bones(cachedBonesData["lForearmBend"]["head"],cachedBonesData["lHand"]["head"] , vx_armature, "elbow_joint.L", radians(90)) #cachedBonesData["lForearmBend"]["roll"])    
    fast_align_bones(cachedBonesData["lForearmTwist"]["head"],cachedBonesData["lHand"]["head"] , vx_armature, "forearm_twist_joint.L", radians(90)) #cachedBonesData["lForearmTwist"]["roll"])  
    fast_align_bones(cachedBonesData["lHand"]["head"],cachedBonesData["lHand"]["tail"] , vx_armature, "wrist_joint.L", cachedBonesData["lHand"]["roll"])  
    #
    fast_align_bones(cachedBonesData["rCollar"]["head"],cachedBonesData["rCollar"]["tail"] , vx_armature, "clavicle_joint.R", radians(0) ) #cachedBonesData["rCollar"]["roll"])
    fast_align_bones(cachedBonesData["rShldrBend"]["head"],cachedBonesData["rForearmBend"]["head"] , vx_armature, "shoulder_joint.R", radians(-90)) #cachedBonesData["rShldrBend"]["roll"])    
    fast_align_bones(cachedBonesData["rShldrTwist"]["head"],cachedBonesData["rForearmBend"]["head"] , vx_armature, "shoulder_twist_joint.R", radians(-90)) #cachedBonesData["rShldrTwist"]["roll"])        
    fast_align_bones(cachedBonesData["rForearmBend"]["head"],cachedBonesData["rHand"]["head"] , vx_armature, "elbow_joint.R", radians(-90)) #cachedBonesData["rForearmBend"]["roll"])    
    fast_align_bones(cachedBonesData["rForearmTwist"]["head"],cachedBonesData["rHand"]["head"] , vx_armature, "forearm_twist_joint.R",  radians(-90)) #cachedBonesData["rForearmTwist"]["roll"])  
    fast_align_bones(cachedBonesData["rHand"]["head"],cachedBonesData["rHand"]["tail"] , vx_armature, "wrist_joint.R", cachedBonesData["rHand"]["roll"])  
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
    nipple_jointEnd_R = ebones["breastNipple_jointEnd.R"]
    matrix = breast_scale_joint_R.matrix.copy()
    nipple_joint01_R_head = nipple_joint01_R.head.copy()
    nipple_joint01_R_tail = nipple_joint01_R.tail.copy()
    nipple_jointEnd_R_head = nipple_jointEnd_R.head.copy()
    nipple_jointEnd_R_tail = nipple_jointEnd_R.tail.copy()
    #
    nipple_joint01_R.matrix = matrix
    nipple_joint01_R.head = nipple_joint01_R_head
    nipple_joint01_R.tail = nipple_joint01_R_tail
    nipple_jointEnd_R.matrix = nipple_joint01_R.matrix.copy()
    nipple_jointEnd_R.head = nipple_joint01_R.tail
    nipple_jointEnd_R.tail = nipple_joint01_R.head
    nipple_jointEnd_R.length *= -1
    #
    breast_deform02_joint01_R = ebones["breast_deform02_joint01.R"]
    breast_deform02_jointEnd_R = ebones["breast_deform02_jointEnd.R"]
    matrix = breast_deform02_joint01_R.matrix.copy()
    breast_deform02_jointEnd_R_head = breast_deform02_joint01_R.tail.copy()
    breast_deform02_jointEnd_R_tail = breast_deform02_jointEnd_R.tail.copy()
    length = breast_deform02_joint01_R.length
    breast_deform02_joint01_R.length *= 1.05 
    breast_deform02_jointEnd_R.matrix = matrix
    breast_deform02_jointEnd_R.head = breast_deform02_jointEnd_R_head
    breast_deform02_jointEnd_R.tail = breast_deform02_joint01_R.tail.copy()
    breast_deform02_joint01_R.length = length
    #
    breast_deform03_joint01_R = ebones["breast_deform03_joint01.R"]
    breast_deform03_jointEnd_R = ebones["breast_deform03_jointEnd.R"]
    matrix = breast_deform03_joint01_R.matrix.copy()
    breast_deform03_jointEnd_R_head = breast_deform03_joint01_R.tail.copy()
    breast_deform03_jointEnd_R_tail = breast_deform03_jointEnd_R.tail.copy()
    length = breast_deform03_joint01_R.length
    breast_deform03_joint01_R.length *= 1.05 
    breast_deform03_jointEnd_R.matrix = matrix
    breast_deform03_jointEnd_R.head = breast_deform03_jointEnd_R_head
    breast_deform03_jointEnd_R.tail = breast_deform03_joint01_R.tail.copy()
    breast_deform03_joint01_R.length = length
    #
    breast_deform03_joint01_R = ebones["breast_deform03_joint01.R"]
    breast_deform03_jointEnd_R = ebones["breast_deform03_jointEnd.R"]
    matrix = breast_deform03_joint01_R.matrix.copy()
    breast_deform03_jointEnd_R_head = breast_deform03_joint01_R.tail.copy()
    breast_deform03_jointEnd_R_tail = breast_deform03_jointEnd_R.tail.copy()
    length = breast_deform03_joint01_R.length
    breast_deform03_joint01_R.length *= 1.05 
    breast_deform03_jointEnd_R.matrix = matrix
    breast_deform03_jointEnd_R.head = breast_deform03_jointEnd_R_head
    breast_deform03_jointEnd_R.tail = breast_deform03_joint01_R.tail.copy()
    breast_deform03_joint01_R.length = length
    #
    breast_deform01_joint01_R = ebones["breast_deform01_joint01.R"]
    breast_deform01_jointEnd_R = ebones["breast_deform01_jointEnd.R"]
    matrix = breast_deform01_joint01_R.matrix.copy()
    breast_deform01_jointEnd_R_head = breast_deform01_joint01_R.tail.copy()
    breast_deform01_jointEnd_R_tail = breast_deform01_jointEnd_R.tail.copy()
    length = breast_deform01_joint01_R.length
    breast_deform01_joint01_R.length *= 1.05 
    breast_deform01_jointEnd_R.matrix = matrix
    breast_deform01_jointEnd_R.head = breast_deform01_jointEnd_R_head
    breast_deform01_jointEnd_R.tail = breast_deform01_joint01_R.tail.copy()
    breast_deform01_joint01_R.length = length
    breast_scale_joint_L = ebones["breast_scale_joint.L"]
    nipple_joint01_L = ebones["nipple_joint01.L"]
    nipple_jointEnd_L = ebones["nipple_jointEnd.L"]
    matrix = breast_scale_joint_L.matrix.copy()
    nipple_joint01_L_head = nipple_joint01_L.head.copy()
    nipple_joint01_L_tail = nipple_joint01_L.tail.copy()
    nipple_jointEnd_L_head = nipple_jointEnd_L.head.copy()
    nipple_jointEnd_L_tail = nipple_jointEnd_L.tail.copy()
    nipple_joint01_L.matrix = matrix
    nipple_joint01_L.head = nipple_joint01_L_head
    nipple_joint01_L.tail = nipple_joint01_L_tail
    nipple_jointEnd_L.matrix = nipple_joint01_L.matrix.copy()
    nipple_jointEnd_L.head = nipple_joint01_L.tail
    nipple_jointEnd_L.tail = nipple_joint01_L.head
    nipple_jointEnd_L.length *= -1
    #
    breast_deform02_joint01_L = ebones["breast_deform02_joint01.L"]
    breast_deform02_jointEnd_L = ebones["breast_deform02_jointEnd.L"]
    matrix = breast_deform02_joint01_L.matrix.copy()
    breast_deform02_jointEnd_L_head = breast_deform02_joint01_L.tail.copy()
    breast_deform02_jointEnd_L_tail = breast_deform02_jointEnd_L.tail.copy()
    length = breast_deform02_joint01_L.length
    breast_deform02_joint01_L.length *= 1.05 
    breast_deform02_jointEnd_L.matrix = matrix
    breast_deform02_jointEnd_L.head = breast_deform02_jointEnd_L_head
    breast_deform02_jointEnd_L.tail = breast_deform02_joint01_L.tail.copy()
    breast_deform02_joint01_L.length = length
    #
    breast_deform03_joint01_L = ebones["breast_deform03_joint01.L"]
    breast_deform03_jointEnd_L = ebones["breast_deform03_jointEnd.L"]
    matrix = breast_deform03_joint01_L.matrix.copy()
    breast_deform03_jointEnd_L_head = breast_deform03_joint01_L.tail.copy()
    breast_deform03_jointEnd_L_tail = breast_deform03_jointEnd_L.tail.copy()
    length = breast_deform03_joint01_L.length
    breast_deform03_joint01_L.length *= 1.05 
    breast_deform03_jointEnd_L.matrix = matrix
    breast_deform03_jointEnd_L.head = breast_deform03_jointEnd_L_head
    breast_deform03_jointEnd_L.tail = breast_deform03_joint01_L.tail.copy()
    breast_deform03_joint01_L.length = length
    #
    breast_deform03_joint01_L = ebones["breast_deform03_joint01.L"]
    breast_deform03_jointEnd_L = ebones["breast_deform03_jointEnd.L"]
    matrix = breast_deform03_joint01_L.matrix.copy()
    breast_deform03_jointEnd_L_head = breast_deform03_joint01_L.tail.copy()
    breast_deform03_jointEnd_L_tail = breast_deform03_jointEnd_L.tail.copy()
    length = breast_deform03_joint01_L.length
    breast_deform03_joint01_L.length *= 1.05 
    breast_deform03_jointEnd_L.matrix = matrix
    breast_deform03_jointEnd_L.head = breast_deform03_jointEnd_L_head
    breast_deform03_jointEnd_L.tail = breast_deform03_joint01_L.tail.copy()
    breast_deform03_joint01_L.length = length
    #
    breast_deform01_joint01_L = ebones["breast_deform01_joint01.L"]
    breast_deform01_jointEnd_L = ebones["breast_deform01_jointEnd.L"]
    matrix = breast_deform01_joint01_L.matrix.copy()
    breast_deform01_jointEnd_L_head = breast_deform01_joint01_L.tail.copy()
    breast_deform01_jointEnd_L_tail = breast_deform01_jointEnd_L.tail.copy()
    length = breast_deform01_joint01_L.length
    breast_deform01_joint01_L.length *= 1.05 
    breast_deform01_jointEnd_L.matrix = matrix
    breast_deform01_jointEnd_L.head = breast_deform01_jointEnd_L_head
    breast_deform01_jointEnd_L.tail = breast_deform01_joint01_L.tail.copy()
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
    ebones["head_joint02"].tail.y = ebones["head_joint02"].head.y
    ebones["head_joint01"].tail.y = ebones["head_joint02"].head.y
    ebones["head_joint01"].head.y = ebones["head_joint02"].head.y
    ebones["head_joint01"].head.z = ebones["head_joint02"].head.z


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
    ebones["spine_jointEnd"].tail = ebones["neck_joint01"].head
    boneArray = ["spine_joint01","spine_joint02","spine_joint03","spine_joint04","spine_jointEnd"]
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
    list_of_bones = ["hip_joint","knee_joint","ankle_joint","ball_joint","thigh_twist_joint"]

    
    difeomorphic_body = "Genesis 3 Female Mesh"
    if difeomorphic_body in bpy.data.objects:
        obj = bpy.data.objects[difeomorphic_body]
        center["centerX.L"]= getCenter (knee_centerX_L, obj )[0]
        center["centerX.R"]= getCenter (knee_centerX_R, obj )[0]
    else:
        center["centerX.L"]= armature.edit_bones["knee_joint.L"].head.x
        center["centerX.R"]= armature.edit_bones["knee_joint.R"].head.x
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


        armature.edit_bones["hip_joint"+suffix].tail = armature.edit_bones["knee_joint"+suffix].head
        armature.edit_bones["knee_joint"+suffix].tail = armature.edit_bones["ankle_joint"+suffix].head
        armature.edit_bones["ankle_joint"+suffix].tail = armature.edit_bones["ball_joint"+suffix].head
        #armature.edit_bones["toe_joint"+suffix].head =  armature.edit_bones["ball_joint"+suffix].tail
        armature.edit_bones["thigh_twist_joint"+suffix].tail = armature.edit_bones["knee_joint"+suffix].head
        armature.edit_bones["thigh_twist_joint"+suffix].head = (armature.edit_bones["hip_joint"+suffix].head+armature.edit_bones["hip_joint"+suffix].tail)/2

        armature.edit_bones["hip_joint"+suffix].roll = radians(0)
        armature.edit_bones["knee_joint"+suffix].roll = radians(0)
        armature.edit_bones["ankle_joint"+suffix].roll = radians(90) #kradians(180) * k
        armature.edit_bones["ball_joint"+suffix].roll = radians(90) #radians(180) * k

        armature.edit_bones["thigh_twist_joint"+suffix].roll = radians(0)

        #armature.edit_bones["toe_joint"+suffix].length =  0.025
        #armature.edit_bones["toe_joint"+suffix].roll = radians(0) 






    center.clear()
    k = 1
    list_of_bones = ["shoulder_joint","elbow_joint","wrist_joint","shoulder_twist_joint","forearm_twist_joint"]

    
    difeomorphic_body = "Genesis 3 Female Mesh"
    if difeomorphic_body in bpy.data.objects:
        obj = bpy.data.objects[difeomorphic_body]
        center["centerX.L"]= getCenter (elbow_center_L, obj )[2]
        center["centerX.R"]= getCenter (elbow_center_R, obj )[2]
    else:
        center["centerX.L"]= armature.edit_bones["elbow_joint.L"].head.z
        center["centerX.R"]= armature.edit_bones["elbow_joint.R"].head.z
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
        armature.edit_bones["shoulder_joint"+suffix].tail = armature.edit_bones["elbow_joint"+suffix].head
        armature.edit_bones["elbow_joint"+suffix].tail = armature.edit_bones["wrist_joint"+suffix].head
        armature.edit_bones["shoulder_twist_joint"+suffix].tail = armature.edit_bones["elbow_joint"+suffix].head
        armature.edit_bones["shoulder_twist_joint"+suffix].head = (armature.edit_bones["shoulder_joint"+suffix].head+armature.edit_bones["shoulder_joint"+suffix].tail)/2
        armature.edit_bones["forearm_twist_joint"+suffix].head = (armature.edit_bones["elbow_joint"+suffix].head+armature.edit_bones["elbow_joint"+suffix].tail)/2
        #
        #armature.edit_bones["shoulder_joint"+suffix].roll = radians(90)
        #armature.edit_bones["elbow_joint"+suffix].roll = radians(90)
        #
        #armature.edit_bones["shoulder_twist_joint"+suffix].roll = radians(90)
        #armature.edit_bones["forearm_twist_joint"+suffix].roll = radians(90)
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
