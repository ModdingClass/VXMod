import bpy

def delete_hierarchy(parent_obj_name):
    bpy.ops.object.select_all(action='DESELECT')
    obj = bpy.data.objects[parent_obj_name]
    obj.animation_data_clear()
    names = set()
    # Go over all the objects in the hierarchy like @zeffi suggested:
    def get_child_names(obj):
        for child in obj.children:
            names.add(child.name)
            if child.children:
                get_child_names(child)

    get_child_names(obj)

    print(names)
    objects = bpy.data.objects
    setattr(obj, 'select', True)
    [setattr(objects[n], 'select', True) for n in names]
    # Remove the animation from the all the child objects
    for child_name in names:
        bpy.data.objects[child_name].animation_data_clear()

    result = bpy.ops.object.delete()
    if result == {'FINISHED'}:
        print ("Successfully deleted object")
    else:
        print ("Could not delete object")
