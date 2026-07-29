import bpy

from ..g3f.difeomorphic_workflow_convert_body import *
from ..tools_message_box import *
from ..utils_bpy import *


def checkIfMaterialExistElseCreateIt(ob, material_name):
    mat = bpy.data.materials.get(material_name)
    #if it doesnt exist, create it.
    if mat is None:
        # create material
        mat = bpy.data.materials.new(name=material_name)
        #assign material
    if mat.name not in ob.material_slots.keys():
        ob.data.materials.append(mat) 
    index = bpy.context.object.material_slots.find(mat.name)    
    return mat,index

def _materialSlotsAreDataLinked(ob):
    """The fast paths below rewrite ob.data.materials, which only mirrors the object's
    slots while every slot is DATA-linked. Diffeomorphic imports always are, but check
    rather than assume - the callers fall back to the operator path if not."""
    for slot in ob.material_slots:
        if slot.link != 'DATA':
            return False
    return True


def _remapPolygonMaterialIndices(mesh, remap, fallback=0):
    """Bulk-rewrite every polygon's material_index through `remap`.

    foreach_get/foreach_set move the whole array in C, so this is one pass over the mesh
    rather than a Python loop, and it triggers no scene update.
    """
    count = len(mesh.polygons)
    if not count:
        return
    indices = [0] * count
    mesh.polygons.foreach_get("material_index", indices)
    mesh.polygons.foreach_set("material_index",
                              [remap.get(i, fallback) for i in indices])


def rebuildMaterialSlots(ob, keep_indices):
    """Reorder and/or prune material slots without a single bpy.ops call.

    `keep_indices` is the list of CURRENT slot indices to keep, in the order wanted.
    Polygons on a dropped slot fall back to slot 0.

    This replaces material_slot_remove / material_slot_move loops. Each of those is an
    operator, and bpy/ops.py runs a full scene.update() after every operator - measured
    at 53 ms in this scene, which is where ~98% of the conversion's runtime was going.
    """
    mesh = ob.data
    old_materials = [m for m in mesh.materials]
    remap = {}
    for new_index, old_index in enumerate(keep_indices):
        remap[old_index] = new_index

    while len(mesh.materials):
        mesh.materials.pop(index=len(mesh.materials) - 1, update_data=False)
    for old_index in keep_indices:
        mesh.materials.append(old_materials[old_index])

    _remapPolygonMaterialIndices(mesh, remap, fallback=0)
    ob.active_material_index = 0


def _slotIndicesMatchingPrefixes(ob, prefixes):
    """Slot indices whose name startswith any prefix - the match the original
    removeMaterialListFromObject and selectByMaterials both used."""
    matched = []
    for index, slot in enumerate(ob.material_slots):
        for prefix in prefixes:
            if slot.name.startswith(prefix):
                matched.append(index)
                break
    return matched


def removeMaterialListFromObject(ob, deletion_list):
    """Drop every material slot whose name starts with an entry in deletion_list.

    Same signature and semantics as before; the operator loop is gone. This was the
    single most expensive helper in the conversion - 10 calls, 5.96 s.
    """
    if not _materialSlotsAreDataLinked(ob):
        _removeMaterialListFromObjectSlow(ob, deletion_list)
        return

    doomed = set(_slotIndicesMatchingPrefixes(ob, deletion_list))
    if not doomed:
        return
    keep = [i for i in range(len(ob.material_slots)) if i not in doomed]
    rebuildMaterialSlots(ob, keep)


def _removeMaterialListFromObjectSlow(ob, deletion_list):
    """Original operator-based implementation, kept as a fallback for the
    OBJECT-linked-slot case the fast path cannot handle."""
    saved_context_mode = ob.mode
    #
    bpy.ops.object.mode_set(mode='OBJECT')
    #
    materials_list = bpy.context.object.material_slots.keys()
    del_slots = []
    for mat in materials_list:
        for del_mat in deletion_list:
            if mat.startswith(del_mat):
                del_index = bpy.context.object.material_slots.find(mat)
                del_slots.append(del_index)
    #
    for i in reversed(range(len(ob.material_slots))):
        if i in del_slots:
            ob.active_material_index = i
            bpy.ops.object.material_slot_remove()

    bpy.ops.object.mode_set(mode=saved_context_mode)
    #

def reassignMaterialsAndRemoveSlots(ob, source_prefixes, target_material_name):
    """Move every polygon on a source slot onto `target_material_name`, then drop the
    now-unused source slots.

    Operator-free equivalent of the block that was repeated nine times:

        selectByMaterials(ob, working_mats)          # EDIT mode + material_slot_select
        mat, i = checkIfMaterialExistElseCreateIt(ob, target)
        bpy.context.object.active_material_index = i
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.material_slot_assign()
        bpy.ops.mesh.select_all(action='DESELECT')
        removeMaterialListFromObject(ob, working_mats)

    Nine of those cost roughly 80 operator calls and, at ~53 ms of scene update each,
    the bulk of the conversion's runtime.
    """
    if not _materialSlotsAreDataLinked(ob):
        selectByMaterials(ob, source_prefixes)
        mat, mat_index = checkIfMaterialExistElseCreateIt(ob, target_material_name)
        bpy.context.object.active_material_index = mat_index
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.object.material_slot_assign()
        bpy.ops.mesh.select_all(action='DESELECT')
        removeMaterialListFromObject(ob, source_prefixes)
        return

    source_indices = set(_slotIndicesMatchingPrefixes(ob, source_prefixes))
    mat, target_index = checkIfMaterialExistElseCreateIt(ob, target_material_name)
    # checkIfMaterialExistElseCreateIt may have appended a slot, so never treat the
    # target as one of its own sources.
    source_indices.discard(target_index)

    if source_indices:
        remap = dict((i, target_index) for i in source_indices)
        mesh = ob.data
        count = len(mesh.polygons)
        indices = [0] * count
        mesh.polygons.foreach_get("material_index", indices)
        mesh.polygons.foreach_set("material_index",
                                  [remap.get(i, i) for i in indices])

    keep = [i for i in range(len(ob.material_slots)) if i not in source_indices]
    if len(keep) != len(ob.material_slots):
        rebuildMaterialSlots(ob, keep)


def selectByMaterials(ob, selection_list):
    #reload the materials list
    materials_list = bpy.context.object.material_slots.keys()
    saved_context_mode = ob.mode
    bpy.ops.object.mode_set(mode='EDIT')  # we need to be in EDIT mode so we can select vertices from materials
    #
    #g3f body has too many vertices that we don't need, so we are going to select them based on materials and remove them
    mat_slots = []
    for mat in materials_list:
        for sel_mat in selection_list:
            if mat.startswith(sel_mat):
                mat_index = bpy.context.object.material_slots.find(mat)
                bpy.context.object.active_material_index = mat_index
                bpy.ops.object.material_slot_select()
    bpy.ops.object.mode_set(mode=saved_context_mode)



def convertG3FDifeomorphicToVXModFBody() :
    isMyArmature = checkIfActiveObjectIs("ARMATURE","Genesis 3 Female")
    if (isMyArmature):
        pass
    else:
        ShowMessageBox("Genesis 3 Female Armature is not the active object","Error",icon="ERROR")
        return
    #
    activeObject = bpy.context.scene.objects.active
    bodyMesh = checkIfActiveObjectHasChild("MESH","Genesis 3 Female Mesh")
    gensMesh = checkIfActiveObjectHasChild("MESH","Genesis 3 Female Genitalia")
    if (bodyMesh != None):
        pass
    else:
        ShowMessageBox("Genesis 3 Female Mesh is not a child of the active object","Error",icon="ERROR")
        return
    #
   
    if (bodyMesh != None):
        setActiveObject(bodyMesh)
        activateObject(bodyMesh)
        active_object = bpy.context.scene.objects.active
        bpy.ops.object.duplicate(linked=False)
        bodyMeshCloned = bpy.context.scene.objects.active
        bodyMeshCloned.parent = None
    #
    gensMeshCloned = None
    if (gensMesh != None):
        setActiveObject(gensMesh)
        activateObject(gensMesh)
        active_object = bpy.context.scene.objects.active
        bpy.ops.object.duplicate(linked=False)
        gensMeshCloned = bpy.context.scene.objects.active
        gensMeshCloned.parent = None
        #actually reassign it
        gensMeshCloned.parent = bodyMeshCloned
    #     
    #gensMeshCloned.parent
    
    # no, we are not going to merge yet... we need to do that later
    #activateObject(gensMeshCloned) # activate this to maybe deselect all in scene first?
    #gensMeshCloned.select = True
    #bodyMeshCloned.select = True
    #setActiveObject(bodyMeshCloned)
    #if (True == False):
    #    return  
    #bpy.ops.daz.merge_geografts()
    activateObject(bodyMeshCloned)
    setActiveObject(bodyMeshCloned)
    """     #
    #setActiveObject(gensMesh)
    setActiveObject(bodyMesh)
    activateObject(bodyMesh)
    active_object = bpy.context.scene.objects.active
    bpy.ops.object.duplicate(linked=False)
    cloned_object = bpy.context.scene.objects.active
    setActiveObject(cloned_object)
    activateObject(cloned_object) 
    cloned_object.parent = None """
    #
    #activateObject(gensMesh)
    #if (1==1):
    #    return
    scene = bpy.context.scene
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.editmode_toggle()
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    #
    # we need to make clones of the materials, otherwise we will overwrite on the stock materials assigned to difeomorphic body
    materials_list = bpy.context.object.material_slots.keys()
    for mat_name in materials_list:
        mat_index = bpy.context.object.material_slots.find(mat_name)
        bpy.context.object.active_material_index = mat_index
        active_material = bodyMeshCloned.active_material
        bodyMeshCloned.active_material = active_material.copy()
    #
    #reload the materials list
    materials_list = bpy.context.object.material_slots.keys()
    #
    #g3f body has too many vertices that we don't need, so we are going to select them based on materials and remove them
    #the eye interior is folded into the head material rather than deleted; it ends up
    #hidden inside the head and is fixed later with an aa (auto apply) shapekey
    working_mats =  ["Irises", "Cornea", "EyeMoisture", "Pupils", "Sclera"]
    reassignMaterialsAndRemoveSlots(bodyMeshCloned, working_mats, "body_head01")

    #
    removeMaterialListFromObject(bodyMeshCloned, ["Irises", "Cornea", "EyeMoisture", "Pupils", "Sclera"])
    #

    #
    working_mats = ["EyeSocket", "Ears", "Lips","Face"]
    reassignMaterialsAndRemoveSlots(bodyMeshCloned, working_mats, "body_head01")

    working_mats = ["Mouth", "Teeth"]
    reassignMaterialsAndRemoveSlots(bodyMeshCloned, working_mats, "body_teeth01")

    #
    working_mats = ["Arms"]
    reassignMaterialsAndRemoveSlots(bodyMeshCloned, working_mats, "body_hand01_L")

    working_mats = ["Torso"]
    reassignMaterialsAndRemoveSlots(bodyMeshCloned, working_mats, "body_main_upper")

    working_mats = ["Toenails", "Legs" ]
    reassignMaterialsAndRemoveSlots(bodyMeshCloned, working_mats, "body_foot_L")

    working_mats = ["Genitalia"]
    reassignMaterialsAndRemoveSlots(bodyMeshCloned, working_mats, "body_genital01")

    working_mats = ["Eyelashes"]
    reassignMaterialsAndRemoveSlots(bodyMeshCloned, working_mats, "body_eyelash01")
    
    
    working_mats = ["Fingernails"]
    reassignMaterialsAndRemoveSlots(bodyMeshCloned, working_mats, "body_fingernails_L.001")



    bpy.ops.object.mode_set(mode='OBJECT')

    #delete unused materials
    ob = bpy.context.active_object
    used_indices = set()
    polygon_count = len(ob.data.polygons)
    if polygon_count:
        indices = [0] * polygon_count
        ob.data.polygons.foreach_get("material_index", indices)
        used_indices = set(indices)

    if _materialSlotsAreDataLinked(ob):
        keep = [i for i in range(len(ob.material_slots)) if i in used_indices]
        if keep and len(keep) != len(ob.material_slots):
            rebuildMaterialSlots(ob, keep)
    else:
        for i in reversed(range(len(ob.material_slots))):
            if i not in used_indices:
                bpy.context.scene.objects.active = ob
                ob.active_material_index = i
                bpy.ops.object.material_slot_remove()



    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.object.mode_set(mode='OBJECT')

    game_material_names = [
    'body_teeth01',
    'body_leg_lower_R',
    'body_leg_lower_L',
    'body_main_lower',
    'body_arm_lower_R',
    'body_arm_lower_L',
    'body_fingernails_R',
    'body_arm_upper_R',
    'body_arm_upper_L',
    'body_leg_upper_R',
    'body_leg_upper_L',
    'body_foot_L',
    'body_hand01_L',
    'body_genital01',
    'body_head01',
    'body_main_upper',
    'body_main_censor',
    'body_hand01_R',
    'body_foot_R',
    'body_fingernails_L',
    'body_eyelash01']

    if (True == False):
        return
    #refresh the materials_list array
    current_materials_list = bpy.context.object.material_slots.keys()
    print ("size of current_materials_list:{0}".format(len(current_materials_list)))
    #
    for i,game_mat_name in enumerate(game_material_names): 
        print ("current index {0} and size of current_materials_list:{1}".format(i,len(current_materials_list)))
        mat = None
        for existing_mat in current_materials_list:
            if (game_mat_name in existing_mat):
                # Get material
                print("Found material: {0} in current_materials_list as {1}".format(game_mat_name,existing_mat))
                mat = bpy.data.materials.get(existing_mat)
        #if mat not found in body, lets look in the entire project
        if mat is None:
            print("Material: {0} not found, lets look for it in the entire project".format(game_mat_name))
            mat = bpy.data.materials.get(game_mat_name)
            if mat is not None:
                #assign material
                ob.data.materials.append(mat) 
        #if mat still doesnt exist, create it.
        if mat is None:
            # create material
            print("Material: {0} not found, lets create it".format(game_mat_name))
            mat = bpy.data.materials.new(name=game_mat_name)
            print("\t Material added as : {0}".format(mat.name))
            #assign material
            ob.data.materials.append(mat) 
        #
        #             
        if (mat.name != game_mat_name):
            print("\t Material should be renamed as : {0}".format(game_mat_name))
            mat.name = game_mat_name
            print("\t Material new name is : {0}".format(mat.name))
        #otherwise
    """         else:
            #mat.name = target_mat_name
            #get material
            #mat = bpy.data.materials.get(target_mat_name)
            found = False
            for idx, m in enumerate(ob.material_slots):
                if (m.name == game_mat_name):
                    bpy.context.object.active_material_index = idx
                    bpy.ops.object.material_slot_select()
                    found = True
                    break
            if (found == False):
                ob.data.materials.append(mat) """
    #
    if (True == False):
        return






    ob = bpy.context.active_object

    # Sort the material slots by the last underscore-separated token of their name, then
    # rotate the first slot down to position 15.
    #
    # This used to be a bubble sort with bpy.ops.object.material_slot_move inside the
    # inner loop, followed by 15 more move calls. With 21 slots that is 420 iterations
    # and ~150 operator invocations - and bpy/ops.py runs a full scene.update() after
    # every operator, measured at 53 ms here. It was the single largest cost in the
    # conversion. The permutation is now computed in Python and applied in one pass.
    #
    # Semantics are preserved exactly: Python's sorted() is stable and the original
    # bubble sort used a strict <, so equal keys keep their relative order either way.
    if _materialSlotsAreDataLinked(ob):
        slot_names = [slot.name for slot in ob.material_slots]
        order = sorted(range(len(slot_names)),
                       key=lambda i: slot_names[i].split("_")[-1])
        if order:
            # 15 x move DOWN on slot 0 puts it at index 15 (clamped to the last slot).
            insert_at = min(15, len(order) - 1)
            order = order[1:insert_at + 1] + [order[0]] + order[insert_at + 1:]
        rebuildMaterialSlots(ob, order)
        print("material slot order: {}".format([slot.name for slot in ob.material_slots]))
    else:
        for j in range (len(ob.material_slots)):
            for i in range (len(ob.material_slots)-1):
                ob.active_material_index = i
                tempStr = ob.active_material.name
                ob.active_material_index = i+1
                if ob.active_material.name.split("_")[-1] < tempStr.split("_")[-1]:
                    bpy.ops.object.material_slot_move(direction='UP')
        ob.active_material_index = 0
        for _ in range(15):
            bpy.ops.object.material_slot_move(direction='DOWN')

    bpy.data.materials["body_teeth01"]["localname"]="local_custommouth_RS"
    bpy.data.materials["body_teeth01"]["objectname"]="body_teeth01_SG"
    #
    bpy.data.materials["body_main_censor"]["localname"]="local_customcensor_RS"
    bpy.data.materials["body_main_censor"]["objectname"]="body_main_censor_SG"

    # DISABLED - LEGACY. The 14 fake "bbb_*" shape keys plus a Basis were inherited from
    # the pre-Difeomorphic importer (importer_g3f.py:309 still sets the same property).
    # They carry no deltas; they only reserved names that dictionary_shapekeys.py maps to
    # body_blends_* ids. The real shape keys are imported later from a custom file with
    # the Game Mod Tiny Tools (GMTT) addon, which creates whatever it needs.
    #
    # Leaving them out means the converted mesh has NO shape keys at all, i.e.
    # ob.data.shape_keys is None. Checked against every consumer in the addon:
    #   safe   exporter_unreal.py:193-194  adds a Basis when one is missing
    #   safe   exporter_unreal.py:1293     checks for None before reading key_blocks
    #   fixed  legacy_tools_import_export_shape_keys_json.py  (dead module, now guarded)
    #   fixed  tools_duplicate_object_remove_mats_shapekeys.py:18  (now guarded)
    #
    #verts = ob.data.vertices
    #
    #sk_basis = ob.shape_key_add('Basis')
    #ob.data.shape_keys.use_relative = True
    #
    #shape_keys = [
    #'bbb_asian02_morph',
    #'bbb_vagfix_morph',
    #'bbb_eye_L_morph',
    #'bbb_asian01_morph',
    #'bbb_atomic01',
    #'bbb_hentai01_morph',
    #'bbb_eye_R_morph',
    #'bbb_african01_morph',
    #'bbb_vag_morph',
    #'bbb_jenna01_morph',
    #'bbb_capelli01_morph',
    #'bbb_ear01',
    #'bbb_pregnant',
    #'bbb_ear02'
    #]
    #
    ## Create 10 sequential deformations
    #for shape_key in shape_keys:
    #    # Create new shape key
    #    sk = ob.shape_key_add(shape_key)
    #    sk.slider_min = -1



    body_subdiv_cage_object = bpy.context.scene.objects.get("body_subdiv_cage")

    if body_subdiv_cage_object:
        print ("\"body_subdiv_cage\" object found in scene, using original name")
    else:
        ob.name= "body_subdiv_cage"
        ob.data.name = "M_body_subdiv_cage"

    
    #lets flip eyelashes normals
    eyelashes_faces_that_needs_to_have_flipped_normals = [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 83, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 126, 127, 128, 129, 130, 131, 132, 133, 134, 135, 136, 137, 138, 139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152, 153, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165, 166, 167, 168, 169, 170, 171, 172, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 184, 185, 186, 187, 188, 189, 190, 191, 192, 193, 194, 195, 196, 197]
    
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_mode(type="FACE")
    bpy.ops.object.mode_set(mode='OBJECT')
    for i in eyelashes_faces_that_needs_to_have_flipped_normals:
        ob.data.polygons[i].select = True
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.flip_normals() 
    bpy.ops.object.mode_set(mode='OBJECT')

    ob.data.uv_layers[0].name = "UVMap"
    #lets add this property
    ob.data["json_sk_exporter"] = "bbb_eye_L_morph,bbb_eye_R_morph,bbb_vagfix_morph"

    if (gensMeshCloned != None):
        setActiveObject(gensMeshCloned)
        activateObject(gensMeshCloned)
        active_object = bpy.context.scene.objects.active
        for i in reversed(range(len(active_object.material_slots))):
            active_object.active_material_index = i
            bpy.ops.object.material_slot_remove()
        mat = bpy.data.materials["body_genital01"]
        #assign material
        active_object.data.materials.append(mat) 
    
    #lets end
    activateObject(bodyMeshCloned)
    setActiveObject(bodyMeshCloned)
