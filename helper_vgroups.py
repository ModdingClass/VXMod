import bpy


def merge_vgroups_into_third(object_name, vgroup_A_name, vgroup_B_name, vgroup_C_name):
	#
	ob = bpy.data.objects[object_name]
	# EDIT THIS
	#vgroup_A_name = groupA
	#vgroup_B_name = groupB
	#vgroup_C_name = groupC
	# Get both groups and add them into third
	if (vgroup_A_name in ob.vertex_groups and vgroup_B_name in ob.vertex_groups):
		vgroup = ob.vertex_groups.new(name=vgroup_C_name)
		for id, vert in enumerate(ob.data.vertices):
			available_groups = [v_group_elem.group for v_group_elem in vert.groups]
			A = B = 0
			if ob.vertex_groups[vgroup_A_name].index in available_groups:
				A = ob.vertex_groups[vgroup_A_name].weight(id)
			if ob.vertex_groups[vgroup_B_name].index in available_groups:
				B = ob.vertex_groups[vgroup_B_name].weight(id)
			# only add to vertex group is weight is > 0
			sum = A + B
			if sum > 0:
				vgroup.add([id], sum ,'REPLACE')





def move_vertex_weights_between_groups(obj, v_index, original_vg_name, new_vg_name, percentage):
    # Ensure object is of type 'MESH'
    if obj.type != 'MESH':
        print("The object is not a mesh.")
        return
    #
    # Get the original and new vertex groups
    original_vg = obj.vertex_groups.get(original_vg_name)
    new_vg = obj.vertex_groups.get(new_vg_name)
    #
    # Check if both vertex groups exist
    if original_vg is None or new_vg is None:
        print("One or both of the specified vertex groups do not exist.")
        return
    #
    # Initialize the original weight to 0
    orig_weight = 0.0	
    # Get the weight of the vertex in the original vertex group
    try:
        orig_weight = original_vg.weight(v_index)
    except RuntimeError:
        # Vertex is not in the original vertex group
        print("Vertex {} is not in the original vertex group.".format(v_index))
        return
    #
    # Calculate the amount to transfer based on the given percentage
    transfer_amount = orig_weight * (percentage / 100.0)
    
    # Subtract the transfer amount from the original vertex group
    original_vg.add([v_index], orig_weight - transfer_amount, 'REPLACE')
    
    # Add the transfer amount to the new vertex group
    new_vg.add([v_index], transfer_amount, 'ADD')

# Example usage:
# transfer_vertex_weight(0, "GroupA", "GroupB", 30)


def split_vertex_weights_between_multiple_groups(obj, v_index, original_vg_name, target_vgs, percentage):
    # Ensure object is of type 'MESH'
    if obj.type != 'MESH':
        print("The object is not a mesh.")
        return
    #
    # Get the original and new vertex groups
    original_vg = obj.vertex_groups.get(original_vg_name)
    #
    # Check if original vertex groups exist
    if original_vg is None:
        print("One or both of the specified vertex groups do not exist.")
        return
    #
    for new_vg_name in target_vgs:
        new_vg = obj.vertex_groups.get(new_vg_name)
        # Check if target vertex groups exist
        if new_vg is None:
            print("One of the specified target vertex groups do not exist.")
            return         
    # Initialize the original weight to 0
    orig_weight = 0.0	
    # Get the weight of the vertex in the original vertex group
    try:
        orig_weight = original_vg.weight(v_index)
    except RuntimeError:
        # Vertex is not in the original vertex group
        print("Vertex {} is not in the original vertex group.".format(v_index))
        return
    #
    # Calculate the amount to transfer based on the given percentage
    transfer_amount = orig_weight * (percentage / 100.0)
    
    # Subtract the transfer amount from the original vertex group
    original_vg.add([v_index], orig_weight - transfer_amount, 'REPLACE')
    for new_vg_name in target_vgs:
        new_vg = obj.vertex_groups.get(new_vg_name)
        # Add the transfer amount to the new vertex group
        new_vg.add([v_index], transfer_amount/len(target_vgs), 'ADD')


def merge_vgroups_into_existing(ob, target_name, source_names, epsilon=1e-3):
    """
    Additively merge several vertex groups into one, PRESERVING whatever weight the
    target group already holds.

    This is the non-destructive counterpart of mergeSubgroupsIntoGroup() in
    g3f/difeomorphic_workflow.py. That one calls checkIfVertexGroupExistAndRecreateIt()
    first, which deletes and recreates the target BEFORE collecting the sources - so the
    target's own weights are gone by the time the sum is taken. (Its
    `idxs.append(vgrp.index)` looks like it guards against that, but it reads the
    already-emptied group.) That behaviour is fine when the target is a brand new group;
    it is wrong when merging into head / lowerJaw / foot.L, which already carry weight.

    Sources that do not exist on the mesh are skipped silently, matching the house style.
    The target is skipped if it appears in source_names - it is already accounted for.

    No explicit clamp: Blender clamps vertex_groups.add() into [0, 1] itself.

    Returns (vertices_written, sources_used).
    """
    if ob.type != 'MESH':
        print("merge_vgroups_into_existing: '{}' is not a mesh.".format(ob.name))
        return (0, [])

    target_vg = ob.vertex_groups.get(target_name)
    if target_vg is None:
        target_vg = ob.vertex_groups.new(name=target_name)

    source_vgs = []
    for source_name in source_names:
        if source_name == target_name:
            continue
        vg = ob.vertex_groups.get(source_name)
        if vg is not None:
            source_vgs.append(vg)

    if not source_vgs:
        return (0, [])

    # Index set includes the TARGET, so its existing weight is summed in rather than lost.
    source_idxs = set(vg.index for vg in source_vgs)
    accumulate_idxs = set(source_idxs)
    accumulate_idxs.add(target_vg.index)

    weights = {}
    for v in ob.data.vertices:
        total = 0.0
        touched = False
        for g in v.groups:
            if g.group in accumulate_idxs:
                total += g.weight
                if g.group in source_idxs:
                    touched = True
        # Only rewrite vertices a source actually contributed to; leaving the rest alone
        # keeps this a no-op for the untouched part of the mesh.
        if touched and total > epsilon:
            weights[v.index] = total

    for v_index, w in weights.items():
        target_vg.add([v_index], w, 'REPLACE')

    return (len(weights), [vg.name for vg in source_vgs])
