import bpy
import mathutils
import math

# Get the armature object directly (assuming it exists)
armature_name = "Armature"
armature = bpy.data.objects[armature_name]

# Get the active object
obj = bpy.data.objects["body_subdiv_cage"]

# Set the common vertex index
common_vertex_index = 6957
common_vertex = obj.data.vertices[common_vertex_index]

# List of vertex indices for which to calculate the average position
vertex_indices = [
    1628, 1629, 1630, 1631, 1632, 1633, 1634, 1635, 1636, 1637, 1638, 1639,
    1640, 1641, 1642, 1895, 1896, 4489, 4491, 4492, 4509, 4515, 4521, 4532
]

# Calculate the average position of the specified vertices
total_position = mathutils.Vector((0.0, 0.0, 0.0))
for index in vertex_indices:
    total_position += obj.data.vertices[index].co

average_position = total_position / len(vertex_indices)

# Calculate the new stop position at double the distance
direction = average_position - common_vertex.co
double_distance_position = common_vertex.co + direction.normalized() * direction.length * 2

# Print the coordinates
print("Common Vertex Coordinate:", common_vertex.co)
print("Average Position:", average_position)
print("Stop Position (Double Distance):", double_distance_position)

# Place the 3D cursor at the stop position
bpy.context.scene.cursor_location = double_distance_position

# Get the top hint vertex
top_hint_vertex_index = 6826
top_hint_vertex = obj.data.vertices[top_hint_vertex_index]

# Define the positions and vectors
start_position = common_vertex.co
stop_position = double_distance_position
top_hint_position = top_hint_vertex.co
vec_stop_to_top_hint = top_hint_position - stop_position
vec_start_to_stop = stop_position - start_position

# Calculate the normal of the plane defined by the three points (start, stop, top hint)
plane_normal = vec_start_to_stop.cross(vec_stop_to_top_hint).normalized()

# Calculate the direction for the ray originating from the stop position at 135 degrees (for top)
angle_top = math.radians(135)
rotation_quat_top = mathutils.Quaternion(plane_normal, angle_top)
ray_direction_45_top = rotation_quat_top * vec_start_to_stop.normalized()

# Cast the ray from the stop position to find the top location
stop_global = obj.matrix_world * stop_position
direction_global_top = obj.matrix_world.to_3x3() * ray_direction_45_top

# Perform ray cast using the active object (the mesh) to get the top location
result, top_location, normal, index = obj.ray_cast(stop_global, direction_global_top)
print("Top Intersection Point:", top_location)

# Calculate the direction for the ray originating from the stop position at 225 degrees (for bottom)
angle_bottom = math.radians(135 + 90)  # Equivalent to 225 degrees
rotation_quat_bottom = mathutils.Quaternion(plane_normal, angle_bottom)
ray_direction_45_bottom = rotation_quat_bottom * vec_start_to_stop.normalized()

# Cast the ray from the stop position to find the bottom location
direction_global_bottom = obj.matrix_world.to_3x3() * ray_direction_45_bottom
result, bottom_location, normal, index = obj.ray_cast(stop_global, direction_global_bottom)
print("Bottom Intersection Point:", bottom_location)

# Create the perpendicular plane normal by rotating the initial plane normal 90 degrees around the start-stop vector
perpendicular_plane_normal = vec_start_to_stop.cross(plane_normal).normalized()

# Calculate the direction for outer and inner within the perpendicular plane
angle_outer = math.radians(135)  # 135 degrees in the perpendicular plane
angle_inner = math.radians(225)  # 225 degrees in the perpendicular plane

# Rotation quaternions around the perpendicular plane normal
rotation_quat_outer = mathutils.Quaternion(perpendicular_plane_normal, angle_outer)
rotation_quat_inner = mathutils.Quaternion(perpendicular_plane_normal, angle_inner)

# outer and inner ray directions
ray_direction_outer = rotation_quat_outer * vec_start_to_stop.normalized()
ray_direction_inner = rotation_quat_inner * vec_start_to_stop.normalized()

# Cast the rays from the stop position to find the outer and inner locations
direction_global_outer = obj.matrix_world.to_3x3() * ray_direction_outer
direction_global_inner = obj.matrix_world.to_3x3() * ray_direction_inner

# Ray cast for outer location
result, outer_location, normal, index = obj.ray_cast(stop_global, direction_global_outer)
print("outer Intersection Point:", outer_location)

# Ray cast for inner location
result, inner_location, normal, index = obj.ray_cast(stop_global, direction_global_inner)
print("inner Intersection Point:", inner_location)

# Now add bones to the armature
bpy.context.scene.objects.active = armature  # Set the armature as active
bpy.ops.object.mode_set(mode='EDIT')  # Switch to Edit mode
armature.select = True  # Select the armature
armature.data.edit_bones.active = None  # Make sure no bone is active

# Create bones
# breastScale.L bone (from stop to start)
bone_name = "breastScale.L"
bone = armature.data.edit_bones.get(bone_name)
if bone:
    pass
else:
    bone = armature.data.edit_bones.new(bone_name)

bone.head = stop_position
bone.tail = start_position

# breastTop.L bone (from stop to top)
bone_name = "breast_top_joint.L"
bone = armature.data.edit_bones.get(bone_name)
if bone:
    pass
else:
    bone = armature.data.edit_bones.new(bone_name)

bone.head = stop_position
bone.tail = top_location

# breastBottom.L bone (from stop to bottom)
bone_name = "breast_bottom_joint.L"
bone = armature.data.edit_bones.get(bone_name)
if bone:
    pass
else:
    bone = armature.data.edit_bones.new(bone_name)

bone.head = stop_position
bone.tail = bottom_location

# breastOuter.L bone (from stop to outer)
bone_name = "breast_outer_joint.L"
bone = armature.data.edit_bones.get(bone_name)
if bone:
    pass
else:
    bone = armature.data.edit_bones.new(bone_name)

bone.head = stop_position
bone.tail = outer_location

# breastInner.L bone (from stop to inner)
bone_name = "breast_inner_joint.L"
bone = armature.data.edit_bones.get(bone_name)
if bone:
    pass
else:
    bone = armature.data.edit_bones.new(bone_name)

bone.head = stop_position
bone.tail = inner_location

# Return to Object mode
bpy.ops.object.mode_set(mode='OBJECT')
