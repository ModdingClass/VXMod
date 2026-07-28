import bpy
import math
from mathutils import Matrix
from mathutils import Vector
from mathutils import Quaternion
from ..g3f.difeomorphic_workflow_init_custom_vertex_indices import *
from ..g3f.difeomorphic_workflow_armature_utils import *

def getArmatureBonesDictFromBreastVertices(bones_dict):
    print("getArmatureBonesFromBreastVertices()...")
    armature_data = bpy.data.objects['Armature']
    breast_bone_names = [
        "nipple_joint01.R", "nipple_end.R", "nipple_joint01.L", "nipple_end.L",
        "breast_scale_joint.L", "breast_top_joint.L", "breast_bottom_joint.L",
        "breast_outer_joint.L", "breast_inner_joint.L",
        "breast_scale_joint.R", "breast_top_joint.R", "breast_bottom_joint.R",
        "breast_outer_joint.R", "breast_inner_joint.R",
    ]
    has_breast = any(b in armature_data.data.bones for b in breast_bone_names)
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
    
    #right
    breast_joint_R_head = getCenter (breast_base_R, obj)
    breast_joint_R_tail = getCenter (breast_top_R, obj)

    nipple_joint01_R_head = getCenter (nipple_base_R, obj)
    nipple_joint01_R_tail = getCenter (nipple_top_R, obj)

    breast_scale_joint_R_head = breast_joint_R_tail
    breast_scale_joint_R_tail = nipple_joint01_R_head

    breast_deform01_joint01_R_head = breast_joint_R_tail
    breast_deform02_joint01_R_head = breast_joint_R_tail
    breast_deform02_joint01_R_head = breast_joint_R_tail

    breast_deform01_joint01_R_tail = getCenter (breast_deform01_R, obj)
    breast_deform02_joint01_R_tail = getCenter (breast_deform02_R, obj)
    breast_deform03_joint01_R_tail = getCenter (breast_deform03_R, obj)

    #left
    breast_joint_L_head = getCenter (breast_base_L, obj)
    breast_joint_L_tail = getCenter (breast_top_L, obj)

    nipple_joint01_L_head = getCenter (nipple_base_L, obj)
    nipple_joint01_L_tail = getCenter (nipple_top_L, obj)

    breast_scale_joint_L_head = breast_joint_L_tail
    breast_scale_joint_L_tail = nipple_joint01_L_head

    breast_deform01_joint01_L_head = breast_joint_L_tail
    breast_deform02_joint01_L_head = breast_joint_L_tail
    breast_deform02_joint01_L_head = breast_joint_L_tail

    breast_deform01_joint01_L_tail = getCenter (breast_deform01_L, obj)
    breast_deform02_joint01_L_tail = getCenter (breast_deform02_L, obj)
    breast_deform03_joint01_L_tail = getCenter (breast_deform03_L, obj)

    breast_dz_joint_L_head = getCenter (dz_breast_base_L, obj)
    breast_dz_joint_L_head.y = getCenter (dz_breast_base_y_L, obj).y
    breast_dz_joint_R_head = getCenter (dz_breast_base_R, obj)
    breast_dz_joint_R_head.y = getCenter (dz_breast_base_y_R, obj).y
    
    extra = Vector((0,0,0.01))

    #bones_dict["breast_joint.R"]= {"head" : amwi * breast_dz_joint_R_head, "tail" : amwi * nipple_joint01_R_head, "roll" : 0, "rollOverride" : 0, "connected" : False }
    #bones_dict["breast_joint.L"]= {"head" : amwi * breast_dz_joint_L_head, "tail" : amwi * nipple_joint01_L_head, "roll" : 0, "rollOverride" : 0, "connected" : False }
    if has_breast:
        bones_dict["nipple_joint01.R"]= {"head" : amwi * nipple_joint01_R_head, "tail" : amwi * nipple_joint01_R_tail, "roll" : -2, "rollOverride" : 0, "connected" : False }
        bones_dict["nipple_end.R"]= {"head" : amwi * nipple_joint01_R_tail, "tail" : amwi * nipple_joint01_R_tail + extra, "roll" : 90, "rollOverride" : 0, "connected" : False }
        bones_dict["nipple_joint01.L"]= {"head" : amwi * nipple_joint01_L_head, "tail" : amwi * nipple_joint01_L_tail, "roll" : 2, "rollOverride" : 0, "connected" : False }
        bones_dict["nipple_end.L"]= {"head" : amwi * nipple_joint01_L_tail, "tail" : amwi * nipple_joint01_L_tail + extra, "roll" : -90, "rollOverride" : 0, "connected" : False }

    '''
    #right
    #bones_dict["breast_dz_joint.R"]= {"head" : amwi * breast_dz_joint_R_head, "tail" : amwi * nipple_joint01_R_head, "roll" : 0, "rollOverride" : 0, "connected" : False }
    bones_dict["breast_joint.R"]= {"head" : amwi * breast_dz_joint_R_head, "tail" : amwi * nipple_joint01_R_head, "roll" : 0, "rollOverride" : 0, "connected" : False }
    #bones_dict["breast_joint.R"]= {"head" : amwi * breast_joint_R_head, "tail" : amwi * breast_joint_R_tail, "roll" : 125, "rollOverride" : 0, "connected" : False }
    bones_dict["breast_scale_joint.R"]= {"head" : amwi * breast_scale_joint_R_head, "tail" : amwi * breast_scale_joint_R_tail, "roll" : -7.2, "rollOverride" : 0, "connected" : False }

    bones_dict["nipple_joint01.R"]= {"head" : amwi * nipple_joint01_R_head, "tail" : amwi * nipple_joint01_R_tail, "roll" : -2, "rollOverride" : 0, "connected" : False }
    bones_dict["nipple_end.R"]= {"head" : amwi * nipple_joint01_R_tail, "tail" : amwi * nipple_joint01_R_tail + extra, "roll" : 90, "rollOverride" : 0, "connected" : False }


    bones_dict["breast_deform01_joint01.R"]= {"head" : amwi * breast_joint_R_tail, "tail" : amwi * breast_deform01_joint01_R_tail, "roll" : 152, "rollOverride" : 0, "connected" : False }
    bones_dict["breast_deform01_end.R"]= {"head" : amwi * breast_deform01_joint01_R_tail, "tail" : amwi * breast_deform01_joint01_R_tail + extra, "roll" : 152, "rollOverride" : 0, "connected" : False }

    bones_dict["breast_deform02_joint01.R"]= {"head" : amwi * breast_joint_R_tail, "tail" : amwi * breast_deform02_joint01_R_tail, "roll" : 147, "rollOverride" : 0, "connected" : False }
    bones_dict["breast_deform02_end.R"]= {"head" : amwi * breast_deform02_joint01_R_tail, "tail" : amwi * breast_deform02_joint01_R_tail + extra, "roll" : 147, "rollOverride" : 0, "connected" : False }

    bones_dict["breast_deform03_joint01.R"]= {"head" : amwi * breast_joint_R_tail, "tail" : amwi * breast_deform03_joint01_R_tail, "roll" : -35, "rollOverride" : 0, "connected" : False }
    bones_dict["breast_deform03_end.R"]= {"head" : amwi * breast_deform03_joint01_R_tail, "tail" : amwi * breast_deform03_joint01_R_tail + extra, "roll" : -35, "rollOverride" : 0, "connected" : False }


    #left
    #bones_dict["breast_dz_joint.L"]= {"head" : amwi * breast_dz_joint_L_head, "tail" : amwi * nipple_joint01_L_head, "roll" : 0, "rollOverride" : 0, "connected" : False }
    bones_dict["breast_joint.L"]= {"head" : amwi * breast_dz_joint_L_head, "tail" : amwi * nipple_joint01_L_head, "roll" : 0, "rollOverride" : 0, "connected" : False }
    #bones_dict["breast_joint.L"]= {"head" : amwi * breast_joint_L_head, "tail" : amwi * breast_joint_L_tail, "roll" : -125, "rollOverride" : 0, "connected" : False }
    bones_dict["breast_scale_joint.L"]= {"head" : amwi * breast_scale_joint_L_head, "tail" : amwi * breast_scale_joint_L_tail, "roll" : 7.2, "rollOverride" : 0, "connected" : False }

    bones_dict["nipple_joint01.L"]= {"head" : amwi * nipple_joint01_L_head, "tail" : amwi * nipple_joint01_L_tail, "roll" : 2, "rollOverride" : 0, "connected" : False }
    bones_dict["nipple_end.L"]= {"head" : amwi * nipple_joint01_L_tail, "tail" : amwi * nipple_joint01_L_tail + extra, "roll" : -90, "rollOverride" : 0, "connected" : False }


    bones_dict["breast_deform01_joint01.L"]= {"head" : amwi * breast_joint_L_tail, "tail" : amwi * breast_deform01_joint01_L_tail, "roll" : -152, "rollOverride" : 0, "connected" : False }
    bones_dict["breast_deform01_end.L"]= {"head" : amwi * breast_deform01_joint01_L_tail, "tail" : amwi * breast_deform01_joint01_L_tail + extra, "roll" : -152, "rollOverride" : 0, "connected" : False }

    bones_dict["breast_deform02_joint01.L"]= {"head" : amwi * breast_joint_L_tail, "tail" : amwi * breast_deform02_joint01_L_tail, "roll" : -147, "rollOverride" : 0, "connected" : False }
    bones_dict["breast_deform02_end.L"]= {"head" : amwi * breast_deform02_joint01_L_tail, "tail" : amwi * breast_deform02_joint01_L_tail + extra, "roll" : -147, "rollOverride" : 0, "connected" : False }

    bones_dict["breast_deform03_joint01.L"]= {"head" : amwi * breast_joint_L_tail, "tail" : amwi * breast_deform03_joint01_L_tail, "roll" : 35, "rollOverride" : 0, "connected" : False }
    bones_dict["breast_deform03_end.L"]= {"head" : amwi * breast_deform03_joint01_L_tail, "tail" : amwi * breast_deform03_joint01_L_tail + extra, "roll" : 35, "rollOverride" : 0, "connected" : False }
    '''

    #left side
    # Set the common vertex index
    # this is actually the nipple center
    common_vertex_index = 6957
    common_vertex = obj.data.vertices[common_vertex_index]
    #actually, common vertex should be calculated based on the nipple head
    nipple_joint01_L_head = getCenter (nipple_base_L, obj)

    # List of vertex indices for which to calculate the average position
    vertex_indices = [
        1628, 1629, 1630, 1631, 1632, 1633, 1634, 1635, 1636, 1637, 1638, 1639,
        1640, 1641, 1642, 1895, 1896, 4489, 4491, 4492, 4509, 4515, 4521, 4532
    ]

    # Calculate the average position of the specified vertices
    total_position = Vector((0.0, 0.0, 0.0))
    for index in vertex_indices:
        total_position += obj.data.vertices[index].co

    average_position = total_position / len(vertex_indices)

    # Calculate the new stop position at double the distance
    direction = average_position - nipple_joint01_L_head #common_vertex.co
    double_distance_position = nipple_joint01_L_head + direction.normalized() * direction.length * 2 #common_vertex.co
    
    # Get the top hint vertex
    top_hint_vertex_index = 6826
    top_hint_vertex = obj.data.vertices[top_hint_vertex_index]

    # Define the positions and vectors
    start_position = nipple_joint01_L_head #common_vertex.co
    stop_position = double_distance_position
    top_hint_position = top_hint_vertex.co
    vec_stop_to_top_hint = top_hint_position - stop_position
    vec_start_to_stop = stop_position - start_position

    # Calculate the normal of the plane defined by the three points (start, stop, top hint)
    plane_normal = vec_start_to_stop.cross(vec_stop_to_top_hint).normalized()

    # Calculate the direction for the ray originating from the stop position at 135 degrees (for top)
    angle_top = math.radians(135)
    rotation_quat_top = Quaternion(plane_normal, angle_top)
    ray_direction_45_top = rotation_quat_top * vec_start_to_stop.normalized()

    # Cast the ray from the stop position to find the top location
    stop_global = obj.matrix_world * stop_position
    direction_global_top = obj.matrix_world.to_3x3() * ray_direction_45_top

    # Perform ray cast using the active object (the mesh) to get the top location
    result, top_location, normal, index = obj.ray_cast(stop_global, direction_global_top)
    #print("Top Intersection Point:", top_location)

    # Calculate the direction for the ray originating from the stop position at 225 degrees (for bottom)
    angle_bottom = math.radians(135 + 90)  # Equivalent to 225 degrees
    rotation_quat_bottom = Quaternion(plane_normal, angle_bottom)
    ray_direction_45_bottom = rotation_quat_bottom * vec_start_to_stop.normalized()

    # Cast the ray from the stop position to find the bottom location
    direction_global_bottom = obj.matrix_world.to_3x3() * ray_direction_45_bottom
    result, bottom_location, normal, index = obj.ray_cast(stop_global, direction_global_bottom)
    #print("Bottom Intersection Point:", bottom_location)

    # Create the perpendicular plane normal by rotating the initial plane normal 90 degrees around the start-stop vector
    perpendicular_plane_normal = vec_start_to_stop.cross(plane_normal).normalized()

    # Calculate the direction for outer and inner within the perpendicular plane
    angle_outer = math.radians(135)  # 135 degrees in the perpendicular plane
    angle_inner = math.radians(225)  # 225 degrees in the perpendicular plane

    # Rotation quaternions around the perpendicular plane normal
    rotation_quat_outer = Quaternion(perpendicular_plane_normal, angle_outer)
    rotation_quat_inner = Quaternion(perpendicular_plane_normal, angle_inner)

    # outer and inner ray directions
    ray_direction_outer = rotation_quat_outer * vec_start_to_stop.normalized()
    ray_direction_inner = rotation_quat_inner * vec_start_to_stop.normalized()

    # Cast the rays from the stop position to find the outer and inner locations
    direction_global_outer = obj.matrix_world.to_3x3() * ray_direction_outer
    direction_global_inner = obj.matrix_world.to_3x3() * ray_direction_inner

    # Ray cast for outer location
    result, outer_location, normal, index = obj.ray_cast(stop_global, direction_global_outer)
    #print("outer Intersection Point:", outer_location)

    # Ray cast for inner location
    result, inner_location, normal, index = obj.ray_cast(stop_global, direction_global_inner)

    if has_breast:
        bones_dict["breast_scale_joint.L"]= {"head" : amwi * stop_position, "tail" : amwi * start_position, "roll" : 0, "rollOverride" : 0, "connected" : False }
        bones_dict["breast_top_joint.L"]= {"head" : amwi * stop_position, "tail" : amwi * top_location, "roll" : 0, "rollOverride" : 0, "connected" : False }
        bones_dict["breast_bottom_joint.L"]= {"head" : amwi * stop_position, "tail" : amwi * bottom_location, "roll" : 0, "rollOverride" : 0, "connected" : False }
        bones_dict["breast_outer_joint.L"]= {"head" : amwi * stop_position, "tail" : amwi * outer_location, "roll" : 0, "rollOverride" : 0, "connected" : False }
        bones_dict["breast_inner_joint.L"]= {"head" : amwi * stop_position, "tail" : amwi * inner_location, "roll" : 0, "rollOverride" : 0, "connected" : False }


    #right side
    # Set the common vertex index
    # this is actually the nipple center
    common_vertex_index = 13725
    common_vertex = obj.data.vertices[common_vertex_index]
    #actually, common vertex should be calculated based on the nipple head
    nipple_joint01_R_head = getCenter (nipple_base_R, obj)


    # List of vertex indices for which to calculate the average position
    vertex_indices = [
        8526, 8527, 8528, 8529, 8530, 8531, 8532, 8533, 8534, 8535, 8536, 8537, 
        8538, 8539, 8540, 8793, 8794, 11356, 11358, 11359, 11375, 11381, 11387, 11398
    ]

    # Calculate the average position of the specified vertices
    total_position = Vector((0.0, 0.0, 0.0))
    for index in vertex_indices:
        total_position += obj.data.vertices[index].co

    average_position = total_position / len(vertex_indices)

    # Calculate the new stop position at double the distance
    direction = average_position - nipple_joint01_R_head #common_vertex.co
    double_distance_position = nipple_joint01_R_head + direction.normalized() * direction.length * 2 #common_vertex.co
    
    # Get the top hint vertex
    top_hint_vertex_index = 13598
    top_hint_vertex = obj.data.vertices[top_hint_vertex_index]

    # Define the positions and vectors
    start_position = nipple_joint01_R_head #common_vertex.co
    stop_position = double_distance_position
    top_hint_position = top_hint_vertex.co
    vec_stop_to_top_hint = top_hint_position - stop_position
    vec_start_to_stop = stop_position - start_position

    # Calculate the normal of the plane defined by the three points (start, stop, top hint)
    plane_normal = vec_start_to_stop.cross(vec_stop_to_top_hint).normalized()

    # Calculate the direction for the ray originating from the stop position at 135 degrees (for top)
    angle_top = math.radians(135)
    rotation_quat_top = Quaternion(plane_normal, angle_top)
    ray_direction_45_top = rotation_quat_top * vec_start_to_stop.normalized()

    # Cast the ray from the stop position to find the top location
    stop_global = obj.matrix_world * stop_position
    direction_global_top = obj.matrix_world.to_3x3() * ray_direction_45_top

    # Perform ray cast using the active object (the mesh) to get the top location
    result, top_location, normal, index = obj.ray_cast(stop_global, direction_global_top)
    #print("Top Intersection Point:", top_location)

    # Calculate the direction for the ray originating from the stop position at 225 degrees (for bottom)
    angle_bottom = math.radians(135 + 90)  # Equivalent to 225 degrees
    rotation_quat_bottom = Quaternion(plane_normal, angle_bottom)
    ray_direction_45_bottom = rotation_quat_bottom * vec_start_to_stop.normalized()

    # Cast the ray from the stop position to find the bottom location
    direction_global_bottom = obj.matrix_world.to_3x3() * ray_direction_45_bottom
    result, bottom_location, normal, index = obj.ray_cast(stop_global, direction_global_bottom)
    #print("Bottom Intersection Point:", bottom_location)

    # Create the perpendicular plane normal by rotating the initial plane normal 90 degrees around the start-stop vector
    perpendicular_plane_normal = vec_start_to_stop.cross(plane_normal).normalized()

    # Calculate the direction for outer and inner within the perpendicular plane
    angle_outer = math.radians(225)  # 135 degrees in the perpendicular plane
    angle_inner = math.radians(135)  # 225 degrees in the perpendicular plane

    # Rotation quaternions around the perpendicular plane normal
    rotation_quat_outer = Quaternion(perpendicular_plane_normal, angle_outer)
    rotation_quat_inner = Quaternion(perpendicular_plane_normal, angle_inner)

    # outer and inner ray directions
    ray_direction_outer = rotation_quat_outer * vec_start_to_stop.normalized()
    ray_direction_inner = rotation_quat_inner * vec_start_to_stop.normalized()

    # Cast the rays from the stop position to find the outer and inner locations
    direction_global_outer = obj.matrix_world.to_3x3() * ray_direction_outer
    direction_global_inner = obj.matrix_world.to_3x3() * ray_direction_inner

    # Ray cast for outer location
    result, outer_location, normal, index = obj.ray_cast(stop_global, direction_global_outer)
    #print("outer Intersection Point:", outer_location)

    # Ray cast for inner location
    result, inner_location, normal, index = obj.ray_cast(stop_global, direction_global_inner)

    if has_breast:
        bones_dict["breast_scale_joint.R"]= {"head" : amwi * stop_position, "tail" : amwi * start_position, "roll" : 0, "rollOverride" : 0, "connected" : False }
        bones_dict["breast_top_joint.R"]= {"head" : amwi * stop_position, "tail" : amwi * top_location, "roll" : 0, "rollOverride" : 0, "connected" : False }
        bones_dict["breast_bottom_joint.R"]= {"head" : amwi * stop_position, "tail" : amwi * bottom_location, "roll" : 0, "rollOverride" : 0, "connected" : False }
        bones_dict["breast_outer_joint.R"]= {"head" : amwi * stop_position, "tail" : amwi * outer_location, "roll" : 0, "rollOverride" : 0, "connected" : False }
        bones_dict["breast_inner_joint.R"]= {"head" : amwi * stop_position, "tail" : amwi * inner_location, "roll" : 0, "rollOverride" : 0, "connected" : False }        



