import bpy
aob = bpy.data.objects["gens"]
mesh_A_name = "g3f"  # Replace with your source mesh name
mesh_B_name = "gens"  # Replace with your target mesh name
mesh_A = bpy.data.objects[mesh_A_name]
mesh_B = bpy.data.objects[mesh_B_name]
vertex_groups_A = mesh_A.vertex_groups
vertex_groups_B = mesh_B.vertex_groups

def transfer_weights(vertex_A_index, vertex_B_index):
    print("transfer from: {} to {}".format(vertex_A_index, vertex_B_index))
    vertex_A = mesh_A.data.vertices[vertex_A_index]
    for vg_A in vertex_groups_A:
        try:
            print("transfering:{}".format(vg_A.name))
            weight_A = vg_A.weight(vertex_A_index)
            vg_B = vertex_groups_B.get(vg_A.name)
            if vg_B is None:
                vg_B = mesh_B.vertex_groups.new(name=vg_A.name)
            vg_B.add([vertex_B_index], weight_A, 'REPLACE')
        except RuntimeError:
            pass

for pair in aob.data.DazGraftGroup:
    transfer_weights(pair.b, pair.a)

print("Weights transferred successfully.")
