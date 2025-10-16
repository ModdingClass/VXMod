#17418 only body
#18105 with gens
#71523 subdiv body with gens
 
import bpy, math, mathutils
import re
from collections import OrderedDict
from collections import defaultdict
from itertools import combinations

import winsound
import ctypes
from ctypes import wintypes
import os
import time
from .utils import *
from .tools_message_box import *

from . import fbody_stats
#from . import strip_and_clean_op

from mathutils import Vector
from mathutils import Matrix
from math import radians

from math import degrees
from bpy_extras.io_utils import axis_conversion

import bpy
import json

import json

def dumps_inline_arrays(obj):
    """Custom JSON pretty-printer that keeps arrays on one line."""
    def _encode(o, level=0):
        indent_str = '  ' * level
        if isinstance(o, dict):
            items = []
            for k, v in o.items():
                encoded = _encode(v, level + 1)
                items.append('%s  "%s": %s' % (indent_str, k, encoded))
            return '{\n' + ',\n'.join(items) + '\n' + indent_str + '}'
        elif isinstance(o, list):
            if all(not isinstance(i, (list, dict)) for i in o):
                return '[%s]' % ', '.join(str(i) for i in o)
            else:
                return '[%s]' % ', '.join(_encode(i, 0) for i in o)
        elif isinstance(o, str):
            return '"%s"' % o
        else:
            return str(o)
    #
    return '[\n' + ',\n'.join(_encode(item, 1) for item in obj) + '\n]'


loaded_int_key_dict = OrderedDict()

def deselect_all_objects():
    #bpy.ops.object.select_all(action='DESELECT')
    for ob in bpy.context.selected_objects:
        ob.select = False

def operator_exists(idname):
    from bpy.ops import op_as_string
    try:
        op_as_string(idname)
        return True
    except:
        return False

def create_vertex_groups_dict(obj):
    # ensure we got the latest assignments and weights
    obj.update_from_editmode()
    mesh = obj.data
    # create vertex group lookup dictionary for names
    vgroup_names = {vgroup.index: vgroup.name for vgroup in obj.vertex_groups}
    # create dictionary of vertex group assignments per vertex
    vgroups = {v.index: [int(vgroup_names[g.group].lstrip("Group_")) for g in v.groups] for v in mesh.vertices}
    return vgroups

def save_to_csv(vgroups, filepath):
    with open(filepath, 'w') as csvfile:
        # Write header
        csvfile.write('Vertex_Index,Vertex_Groups\n')
        # Write data
        for vertex_index, groups in vgroups.items():
            # Enclose vertex groups in parentheses and join them as a string
            groups_str = '({})'.format(', '.join(map(str, groups)))
            csvfile.write('{},{}\n'.format(vertex_index, groups_str))


def assign_vertex_groups(obj):
    mesh = obj.data
    vertex_groups = []
    # Create vertex groups for each vertex
    for i in range(len(mesh.vertices)):
        group_name = "Group_{}".format(i)
        vertex_groups.append(group_name)
        obj.vertex_groups.new(name=group_name)
    # Assign vertices to their respective groups
    for v in mesh.vertices:
        obj.vertex_groups["Group_{}".format(v.index)].add([v.index], 1, 'REPLACE')

def adjust_vertices_location_between_different_topology_meshes_using_lookup_dict(source_obj, target_obj):
    if not source_obj or not target_obj:
        print("Source or Target object not found.")
        return
    # Ensure both objects are of type MESH
    if source_obj.type != 'MESH' or target_obj.type != 'MESH':
        print("Both objects must be of type MESH.")
        return
    # Ensure both objects have the same number of vertices
    if len(source_obj.data.vertices) != len(target_obj.data.vertices):
        print("Vertex counts do not match. Cannot copy vertex positions.")
        pass
    # Access the vertices of the source object
    source_vertices = source_obj.data.vertices
    target_vertices = target_obj.data.vertices
    # Copy vertex positions from the source object to target object
    print("len(target_obj.data.vertices): {} ".format(len(target_obj.data.vertices)))
    if (True == True):
        for i in range(len(target_obj.data.vertices)):
            if i not in loaded_int_key_dict:
                #print("Missing {}".format(i))
                continue
            else:
                #print("Transfering {} - {}".format(i,loaded_int_key_dict[i] )) 
                src_vertex = source_vertices[loaded_int_key_dict[i]]
                tgt_vertex = target_vertices[i]
                tgt_vertex.co = src_vertex.co.copy()
    # Update the target object to reflect changes
    target_obj.data.update()
    # Final message
    print("Vertex positions from '{}' copied to '{}'.".format(source_obj.name, target_obj.name))





def copy_vertices_to_shape_key_between_different_topology_meshes_using_lookup_dict(source_obj, target_obj, new_shape_key_name):
    # Get source and target objects
    if not source_obj or not target_obj:
        print("Source or Target object not found.")
        return
    # Ensure both objects are of type MESH
    if source_obj.type != 'MESH' or target_obj.type != 'MESH':
        print("Both objects must be of type MESH.")
        return
    # Ensure both objects have the same number of vertices
    if len(source_obj.data.vertices) != len(target_obj.data.vertices):
        print("Vertex counts do not match. Cannot copy vertex positions.")
        pass
    # Access the vertices of the source object
    source_vertices = source_obj.data.vertices
    target_vertices = target_obj.data.vertices
    # Create a new shape key on the target object if necessary
    if not target_obj.data.shape_keys:
        target_obj.shape_key_add(name="Basis")
    shape_keys = target_obj.data.shape_keys.key_blocks
    if new_shape_key_name in shape_keys:
        print("Shape key '{}' already exists.".format(new_shape_key_name))
        pass
        #return
    # Create a new shape key on the target object
    new_shape_key = target_obj.shape_key_add(name=new_shape_key_name)
    # Copy vertex positions from the source object to the new shape key on the target object
    print("len(target_obj.data.vertices): {} ".format(len(target_obj.data.vertices)))
    #
    # print(loaded_int_key_dict[0])
    if (True == True):
        for i in range(len(target_obj.data.vertices)):
            if i not in loaded_int_key_dict:
                #print("Missing {}".format(i))
                continue
            else:
                #print("Transfering {} - {}".format(i,loaded_int_key_dict[i] )) 
                src_vertex = source_vertices[loaded_int_key_dict[i]]
                #tgt_vertex = target_vertices[loaded_int_key_dict[i]]
                #tgt_delta = src_vertex.co - tgt_vertex.co
                tgt_vertex = new_shape_key.data[i]#.co=tgt_delta.copy()
                tgt_vertex.co = src_vertex.co.copy()
    # Update the target object to reflect changes
    target_obj.data.update()
    # Final message
    print("Vertex positions from '{}' copied to new shape key '{}' on '{}'.".format(source_obj.name, new_shape_key_name, target_obj.name))



def duplicate_selected_object(newObjectName=None):
    if len(bpy.context.selected_objects)==0:
        ShowMessageBox("No object is selected", "Error", 'ERROR')
        return None              
    return duplicate_object_by_name( bpy.context.selected_objects[0].name , newObjectName)

def duplicate_object_by_name(sourceObjectName=None, newObjectName=None):
    if sourceObjectName is None:
        # Select the active object (assumes only one is selected)
        bpy.context.scene.objects.active = bpy.context.selected_objects[0]
    #
    if bpy.data.objects.get(sourceObjectName) is None:
        ShowMessageBox("Can't find object: "+sourceObjectName, "Error", 'ERROR')
        return None
    deselect_all_objects()
    ob = bpy.data.objects[sourceObjectName]
    ob.select = True
    bpy.context.scene.objects.active = ob
    # Duplicate the selected object
    bpy.ops.object.duplicate(linked=False)
    # The new duplicated object becomes the active object
    new_object = bpy.context.active_object
    if newObjectName is not None:
        new_object.name = newObjectName
    #bpy.context.scene.update()        
    return new_object


# this function is supposed to take the base res body_subdiv_cage and make 2 duplicates
# hires from edit mode subdivide operator - vertices from 0 .. 18119 are coming from the base (unsubdivided) mesh
# hires from object mode subsurf modifier
# lookup table from operator to modifier is created and saved to json file as a dictionary of key:val pairs
def build_subdivision_vertex_matching_table(params) : 
    # a ton of boilerplate checks comes next
    if bpy.data.objects.get("body_subdiv_cage") is None:
        ShowMessageBox("Can't find object: body_subdiv_cage", "Error", 'ERROR')
        return None

    if bpy.data.objects["body_subdiv_cage"].hide :
        ShowMessageBox("'body_subdiv_cage' object is not visible!", "Error", 'ERROR')
        return None

    armature_modifier = next((mod for mod in bpy.data.objects["body_subdiv_cage"].modifiers if mod.type == 'ARMATURE'), None)
    armature_object = armature_modifier.object if armature_modifier else None

    if armature_object is None:
        ShowMessageBox("'body_subdiv_cage' object has no armature!", "Error", 'ERROR')
        return None        
    armature_object.hide = False
    
    exportfolderpath = os.path.join(params.exportFolderPathUnreal,"")    
    if not os.path.exists(exportfolderpath):
        os.makedirs(exportfolderpath)
    
    hiddenStatusGeografts = {}
    mergeGeografts = []
    anatomies = []
    ob = bpy.data.objects["body_subdiv_cage"]
    mergedMeshesName = ob.name
    ob.select = True
    bpy.context.scene.objects.active = ob
    
    if not params.includeGeograftsOnExportUnreal:
        pass
    else:
        if ( operator_exists("daz.merge_geografts_fast") or operator_exists("daz.merge_geografts") or operator_exists("daz.merge_geografts_nondestructive")):
            pass
        else:
            ShowMessageBox("'Include Geografts' is checked, but can't find `modded` Difeomorphic addon for Blender", "Error", 'ERROR')
            return None
        if ob.data.get("mergeGeografts") is None:
                ShowMessageBox("'Include Geografts' is checked, but you are missing 'mergeGeografts' property in data block Custom Properties", "Error", 'ERROR')
                return None
        if len(ob.data["mergeGeografts"].strip()) == 0 :
                ShowMessageBox("'Include Geografts' is checked, but empty 'mergeGeografts' in data block Custom Properties", "Error", 'ERROR')
                return None
        mergeGeografts = ob.data["mergeGeografts"].split(",")
        if len(mergeGeografts)==0:
            ShowMessageBox("'Include Geografts' is checked, but empty 'mergeGeografts' in data block Custom Properties", "Error", 'ERROR')
            return None
        else:
            for geo in mergeGeografts:
                ob = bpy.data.objects.get(geo)
                if ob is None:
                    ShowMessageBox("'Include Geografts' is checked, but the object with name: "+geo+" is missing", "Error", 'ERROR')    
                    return None
                if ob.type != 'MESH':
                    ShowMessageBox("'Include Geografts' is checked, but the object with name: "+geo+" is not a Mesh type", "Error", 'ERROR')    
                    return None       
                hiddenStatusGeografts[ob.name] = ob.hide      
                if ob.hide :
                    ob.hide = False # we need to show it
                    #ShowMessageBox("Geograft object '"+ ob.name +"' is not visible!", "Error", 'ERROR')
                    #return None                
        mergedMeshesName = "_".join(["body_subdiv_cage"] +mergeGeografts)
    ob = bpy.data.objects["body_subdiv_cage"]
    ob.select = True
    bpy.context.scene.objects.active = ob
    bpy.ops.object.duplicate(linked=False)
    fbody = bpy.context.scene.objects.active
    fbody.name = "fbody_base_res"
    
    if params.includeGeograftsOnExportUnreal:
        print("includeGeograftsOnExportUnreal is ON")
        #deselect_all_objects()       
        #
        #
        for geo in mergeGeografts:
            deselect_all_objects()
            ob = bpy.data.objects[geo]
            ob.select = True
            bpy.context.scene.objects.active = ob
            bpy.ops.object.duplicate(linked=False)
            geoClone = bpy.context.scene.objects.active
            geoClone.parent = fbody
            anatomies.append(geoClone)
            bpy.data.objects[geo].hide = hiddenStatusGeografts[ob.name] # we need to restore the hidden status
        #
        deselect_all_objects()
        #
        for geo in anatomies:
            geo.select = True
            bpy.context.scene.objects.active = geo        
        fbody.select=True
        bpy.context.scene.objects.active = fbody
        fbody.select=True
        if ( operator_exists("daz.merge_geografts_nondestructive") ):
            print("daz.merge_geografts_nondestructive is available :)")
            bpy.ops.daz.merge_geografts_nondestructive()        
        elif ( operator_exists("daz.merge_geografts_fast") ):
            print("daz.merge_geografts_fast is available")
            bpy.ops.daz.merge_geografts_fast()
        else: 
            print("daz.merge_geografts fallback :(")
            bpy.ops.daz.merge_geografts()
    
    
    deselect_all_objects()
    fbody.select=True
    bpy.context.scene.objects.active = fbody
    #remove everything that is not required from fbody
    bpy.ops.object.strip_and_clean(vg=True, sk=True, mod=True)
    #
    bpy.ops.object.mode_set(mode='OBJECT')
    #
    # Clear existing vertex groups
    #fbody.vertex_groups.clear()
    #
    # Iterate over all vertices in the mesh
    for i, vertex in enumerate(fbody.data.vertices):
        # Create a new vertex group named after the vertex index
        vg = fbody.vertex_groups.new(name=str(i))
        #
        # Add the vertex to the group with a weight of 1.0
        vg.add([i], 1.0, 'ADD')
        #
    print("Assigned weights to all fbody vertices.")    
    #
    #
    ob = bpy.context.scene.objects.active
    print("Creating fbody_hires!") 
    fbody_hires = duplicate_object_by_name("fbody_base_res","fbody_from_objmode_subsurf_modifier")
    bpy.context.scene.objects.active = fbody_hires
    #first lets remove all shapekeys and existing modifiers
    bpy.ops.object.strip_and_clean(sk=True, mod=True)
    # Add a Subdivision Surface modifier
    bpy.ops.object.modifier_add(type='SUBSURF')
    subsurf_modifier = fbody_hires.modifiers[-1] # get the last modifier (hence -1)
    subsurf_modifier.levels = 1  # Set the subdivision levels as needed
    # Apply the Subdivision Surface modifier
    bpy.ops.object.modifier_apply( modifier = subsurf_modifier.name )
    #
    fbody.select = True 
    #
    bpy.context.scene.objects.active = fbody
    # Switch to Edit Mode
    bpy.ops.object.mode_set(mode='EDIT')
    # Select all vertices
    bpy.ops.mesh.select_all(action='SELECT')
    # Subdivide the selected vertices
    bpy.ops.mesh.subdivide()
    # Switch back to Object Mode (optional)
    bpy.ops.object.mode_set(mode='OBJECT')
    fbody.name = "fbody_from_editmode_subdivide_operator"
    #
    deselect_all_objects()
    # lets create the lookup dict for fbody (subdiv operator in edit mode)
    fbody.select = True        
    #
    bpy.context.scene.objects.active = fbody
    #
    vertex_groups_dict = {}
    # Ensure the object exists and is a mesh
    if fbody and fbody.type == 'MESH':
        # Initialize an empty dictionary to store vertex groups for each vertex
        # Loop through all vertices in the mesh
        for vertex in fbody.data.vertices:
            # List to store the vertex group indices for the current vertex
            group_indices = []
            # Loop through the vertex groups assigned to the vertex
            for group_element in vertex.groups:
                # Get the group index
                group_indices.append(str(group_element.group))
            # Sort the group indices
            group_indices.sort(key=int)
            # Concatenate the group indices with underscores and add to dictionary
            vertex_groups_dict[vertex.index] = "_".join(group_indices)
        # Print the resulting dictionary
        print(vertex_groups_dict)
        #
        mapping_list = []
        for vidx, group_str in vertex_groups_dict.items():
            group_ids = list(map(int, group_str.split("_")))
            if len(group_ids) == 1:
                vtype = "base"
            elif len(group_ids) == 2:
                vtype = "edge"
            elif len(group_ids) == 4:
                vtype = "face"
            else:
                vtype = "unknown"
            #
            mapping_list.append({
                "index": int(vidx),
                "type": vtype,
                "base_indices": group_ids
            })
        #
        # Build lookup of face points: base indices tuple -> subdivided vertex index
        face_point_lookup = {}  # old
        face_point_data = {}    # new
        #
        for entry in mapping_list:
            if entry["type"] == "face":
                base_key = tuple(sorted(entry["base_indices"]))
                face_point_lookup[base_key] = entry["index"]
                face_point_data[base_key] = {
                    "vertex_index": entry["index"],
                    "base_indices": entry["base_indices"]
                }                        
        #
        # Build a vertex-to-face map (face as base_indices)
        vertex_to_faces = defaultdict(list)       
        for face_bases in face_point_lookup.keys():
            for v in face_bases:
                vertex_to_faces[v].append(list(face_bases))
        #
        edge_to_face_points = defaultdict(list)
        edge_to_face_bases = defaultdict(list)
        #
        for face_base_indices, face_vert_idx in face_point_lookup.items():
            # All 2-combinations of the 4 verts in a face (6 edges per quad)
            for edge in combinations(face_base_indices, 2):
                key = tuple(sorted(edge))
                edge_to_face_points[key].append(face_vert_idx)
        #
        for face_base_indices, face_data in face_point_data.items():
            for edge in combinations(face_base_indices, 2):
                key = tuple(sorted(edge))
                edge_to_face_bases[key].append(face_data["base_indices"])                
        #
        # //old code
        #
        for entry in mapping_list:
            #
            if entry["type"] == "base":
                base_idx = entry["base_indices"][0]
                # Connected face base quads
                face_bases = vertex_to_faces.get(base_idx, [])
                # Collect all neighbor base vertices
                neighbor_set = set()
                for face in face_bases:
                    for v in face:
                        if v != base_idx:
                            neighbor_set.add(v)
                #
                entry["connected_faces_base_indices"] = face_bases
                entry["connected_base_neighbor_indices"] = sorted(neighbor_set)            
            #
            if entry["type"] == "edge":
                key = tuple(sorted(entry["base_indices"]))
                entry["adjacent_face_point_indices"] = edge_to_face_points.get(key, [])       
                entry["adjacent_faces_base_indices"] = edge_to_face_bases.get(key, [])                 
            #
        #
        file_path = os.path.join(exportfolderpath,"fbody_vertex_mapping_list.json")
        # Write to file with arrays forced inline
        with open(file_path, 'w') as json_file:
            json_file.write(dumps_inline_arrays(mapping_list))
        # with open(file_path, 'w') as json_file:
        #     json.dump(mapping_list, json_file, indent=2)
        #
        file_path = os.path.join(exportfolderpath,"fbody_vertex_groups_dict.json")
        # Save the lookup table to a JSON file
        with open(file_path, 'w') as json_file:
            json.dump(vertex_groups_dict, json_file)
    else:
        print("The specified object either does not exist or is not a mesh.")
    # lets create the lookup dict for fbody_hires (subsurf modifier)
    deselect_all_objects()
    fbody_hires.select = True        
    #
    bpy.context.scene.objects.active = fbody_hires
    #
    vertex_groups_dict_backwards = {}
    # Ensure the object exists and is a mesh
    if fbody_hires and fbody_hires.type == 'MESH':
        # Initialize an empty dictionary to store vertex groups for each vertex\
        # Loop through all vertices in the mesh
        for vertex in fbody_hires.data.vertices:
            # List to store the vertex group indices for the current vertex
            group_indices = []
            # Loop through the vertex groups assigned to the vertex
            for group_element in vertex.groups:
                # Get the group index
                group_indices.append(str(group_element.group))
            # Sort the group indices
            group_indices.sort(key=int)
            # Concatenate the group indices with underscores and add to dictionary
            vertex_groups_dict_backwards["_".join(group_indices)] = vertex.index
        # Print the resulting dictionary
        print(vertex_groups_dict_backwards)
    else:
        print("The specified object either does not exist or is not a mesh.")
    #
    deselect_all_objects()
    # lets create the final matching lookup dict 
    fbody.select = True        
    #
    bpy.context.scene.objects.active = fbody
    # Ensure the object exists and is a mesh
    if fbody and fbody.type == 'MESH':
        fbody_matching_index_dict = OrderedDict()
        # Loop through all vertices in the mesh
        for vertex in fbody.data.vertices:
            fbody_matching_index_dict[vertex.index]=vertex_groups_dict_backwards[vertex_groups_dict[vertex.index]]
        # Convert dictionary to a JSON string
        dict_as_string = json.dumps(fbody_matching_index_dict)
        # Store it in the Scene's custom properties
        #or maybe not?!?!
        #bpy.context.scene['my_global_fbody_matching_index_dict'] = dict_as_string
        # Specify the file path where you want to save the JSON file
        # Make sure you have permission to write to this location
        file_path = os.path.join(exportfolderpath,mergedMeshesName+"_matching_index_dict.json")
        # Save the lookup table to a JSON file
        with open(file_path, 'w') as json_file:
            json.dump(fbody_matching_index_dict, json_file)
        print("Lookup table saved to:", file_path)
    
    deselect_all_objects()
    if params.cleanupTempMeshesMode=='AFTER' or params.cleanupTempMeshesMode=='BOTH':
        fbody.select = True        
        bpy.context.scene.objects.active = fbody
        fbody_hires.select = True        
        bpy.context.scene.objects.active = fbody_hires        
        bpy.ops.object.delete(use_global=True)   
    #
    deselect_all_objects()



def load_fbody_matching_index_dict_from_json(exportfolderpath, includeGeograftsOnExportUnreal) : 
    #
    #if 'my_global_fbody_matching_index_dict' in bpy.context.scene:
    #    stored_string = bpy.context.scene['my_global_fbody_matching_index_dict']
    # Load the JSON data from the file
    file_path = os.path.join(exportfolderpath,"fbody_matching_index_dict.json")
    with open(file_path, 'r') as json_file:
        loaded_dict = json.load(json_file)
    # Convert the keys back to integers
    int_key_dict = {int(k): v for k, v in loaded_dict.items()}
    # Optionally convert it back to an OrderedDict if needed
    loaded_ordered_dict = OrderedDict(int_key_dict)
    print(loaded_ordered_dict)  # Output: {'a': 1, 'b': 2, 'c': 3}
    print("Dictionary size: {} ".format(len(loaded_ordered_dict)))
    #



def export_to_unreal_v2(params) : #exportfolderpath,
    #exportfolderpath,exportFilename, includeGeograftsOnExportUnreal, cleanTempMeshesAfterExportUnreal, reorientBonesOnExportUnreal
    #
    # a ton of boilerplate checks comes next
    if bpy.data.objects.get("body_subdiv_cage") is None:
        ShowMessageBox("Can't find object: body_subdiv_cage", "Error", 'ERROR')
        return None

    if bpy.data.objects["body_subdiv_cage"].hide :
        ShowMessageBox("'body_subdiv_cage' object is not visible!", "Error", 'ERROR')
        return None

    armature_modifier = next((mod for mod in bpy.data.objects["body_subdiv_cage"].modifiers if mod.type == 'ARMATURE'), None)
    armature_object = armature_modifier.object if armature_modifier else None

    if armature_object is None:
        ShowMessageBox("'body_subdiv_cage' object has no armature!", "Error", 'ERROR')
        return None        
    # lets make sure we are in object mode
    obj = bpy.context.active_object
    if obj is not None:
        if obj.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
    deselect_all_objects()
    #
    if params.cleanupTempMeshesMode =="BEFORE" or params.cleanupTempMeshesMode =="BOTH":
        fbody_stripped = bpy.data.objects.get("fbody_stripped")
        if fbody_stripped is not None:
            fbody_stripped.select=True
            bpy.context.scene.objects.active = fbody_stripped
        #
        emptyLodGroup = bpy.data.objects.get("fbodyLodGroup")
        if emptyLodGroup is not None:
            emptyLodGroup.select=True
            #
            #find the armature as it should be an armature from one of the children
            armature_from_first_emptyLodGroup = None
            for child in emptyLodGroup.children:
                for mod in child.modifiers:
                    if mod.type == 'ARMATURE' and mod.object is not None:
                        armature_from_first_emptyLodGroup = mod.object
                        print("Found child Armature object:", armature_from_first_emptyLodGroup.name)
                        break
                if armature_from_first_emptyLodGroup:
                    break
            # select all children from lodGroup
            for child in emptyLodGroup.children:
                child.select=True                
            if armature_from_first_emptyLodGroup is not None:
                armature_from_first_emptyLodGroup.select=True
                bpy.context.scene.objects.active = armature_from_first_emptyLodGroup        
        #
        #armature_modifier = next((mod for mod in bpy.data.objects["body_subdiv_cage"].modifiers if mod.type == 'ARMATURE'), None)
        #armature_object = armature_modifier.object if armature_modifier else None
        #fbody_hires.select=True
        #fbody.select=True
        #armature_clone.select=True
        #bpy.context.scene.objects.active = armature_clone        
        bpy.ops.object.delete(use_global=True)   
        #
    deselect_all_objects()            
    #
    #!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    #make sure the armature_object is the actual Armature and not a different armature that has different bones like difeomorphic
    #
    armature_object.hide = False
    print("should we be making friendly bones for: {}".format(armature_object.name))
    #
    exportfolderpath = os.path.join(params.exportFolderPathUnreal,"")    
    if not os.path.exists(exportfolderpath):
        os.makedirs(exportfolderpath)
    #    
    hiddenStatusGeografts = {}
    mergeGeografts = []
    anatomies = []
    ob = bpy.data.objects["body_subdiv_cage"]
    mergedMeshesName = ob.name
    ob.select = True
    bpy.context.scene.objects.active = ob
    #
    if not params.includeGeograftsOnExportUnreal:
        mergedMeshesName = "body_subdiv_cage"
        pass
    else:
        if ( operator_exists("daz.merge_geografts_fast") or operator_exists("daz.merge_geografts") or operator_exists("daz.merge_geografts_nondestructive")):
            pass
        else:
            ShowMessageBox("'Include Geografts' is checked, but can't find `modded` Difeomorphic addon for Blender", "Error", 'ERROR')
            return None
        if ob.data.get("mergeGeografts") is None:
                ShowMessageBox("'Include Geografts' is checked, but you are missing 'mergeGeografts' property in data block Custom Properties", "Error", 'ERROR')
                return None
        if len(ob.data["mergeGeografts"].strip()) == 0 :
                ShowMessageBox("'Include Geografts' is checked, but empty 'mergeGeografts' in data block Custom Properties", "Error", 'ERROR')
                return None
        mergeGeografts = ob.data["mergeGeografts"].split(",")
        if len(mergeGeografts)==0:
            ShowMessageBox("'Include Geografts' is checked, but empty 'mergeGeografts' in data block Custom Properties", "Error", 'ERROR')
            return None
        else:
            for geoName in mergeGeografts:
                ob = bpy.data.objects.get(geoName)
                if ob is None:
                    ShowMessageBox("'Include Geografts' is checked, but the object with name: "+geoName+" is missing", "Error", 'ERROR')    
                    return None
                if ob.type != 'MESH':
                    ShowMessageBox("'Include Geografts' is checked, but the object with name: "+geoName+" is not a Mesh type", "Error", 'ERROR')    
                    return None       
                hiddenStatusGeografts[ob.name] = ob.hide      
                if ob.hide :
                    ob.hide = False # we need to show it
                    #ShowMessageBox("Geograft object '"+ ob.name +"' is not visible!", "Error", 'ERROR')
                    #return None    
        mergedMeshesName = "_".join(["body_subdiv_cage"] +mergeGeografts)
    #
    print("mergedMeshesName : {}".format(mergedMeshesName))
    if (params.createSubdivMeshOnExportUnreal):    
        file_path = os.path.join(exportfolderpath,mergedMeshesName+"_matching_index_dict.json")
        if os.path.isfile(file_path) == False:
            ShowMessageBox("Missing subdiv matching file: {}_matching_index_dict.json, maybe try to build it first? ".format(mergedMeshesName), "Error", 'ERROR')    
            return None       
    print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    deselect_all_objects()
    ob = bpy.data.objects["body_subdiv_cage"]
    ob.select = True
    bpy.context.scene.objects.active = ob
    bpy.ops.object.duplicate(linked=False)
    fbody = bpy.context.scene.objects.active
    fbody.name = "fbody"
    if params.includeGeograftsOnExportUnreal:
        #deselect_all_objects()       
        #
        #
        for geoName in mergeGeografts:
            deselect_all_objects()
            ob = bpy.data.objects[geoName]
            ob.select = True
            bpy.context.scene.objects.active = ob
            bpy.ops.object.duplicate(linked=False)
            geoClone = bpy.context.scene.objects.active
            geoClone.parent = fbody
            anatomies.append(geoClone)
            bpy.data.objects[geoName].hide = hiddenStatusGeografts[ob.name] # we need to restore the hidden status
        #
        deselect_all_objects()
        #
        for geo in anatomies:
            geo.select = True
            bpy.context.scene.objects.active = geo        
        fbody.select=True
        bpy.context.scene.objects.active = fbody
        fbody.select=True
        if ( operator_exists("daz.merge_geografts_nondestructive") ):
            print("daz.merge_geografts_nondestructive is available :)")
            bpy.ops.daz.merge_geografts_nondestructive()        
        elif ( operator_exists("daz.merge_geografts_fast") ):
            print("daz.merge_geografts_fast is available")
            bpy.ops.daz.merge_geografts_fast()
        else: 
            print("daz.merge_geografts fallback :(")
            bpy.ops.daz.merge_geografts()
    ############################################################################################
    global loaded_int_key_dict
    loaded_int_key_dict = OrderedDict()
    if (params.createSubdivMeshOnExportUnreal):    
        # daz_to_blender_subdiv_matching_index_dict.json
        file_path = os.path.join(exportfolderpath,mergedMeshesName+"_matching_index_dict.json")
        with open(file_path, 'r') as json_file:
            loaded_dict = json.load(json_file)
        # Convert the keys back to integers
        int_key_dict = {int(k): v for k, v in loaded_dict.items()}
        # Optionally convert it back to an OrderedDict if needed
        loaded_int_key_dict = OrderedDict(int_key_dict)
        print("loaded_ordered_dict size : ")
        print(len(loaded_int_key_dict))        
    ############################################################################################
    #
    deselect_all_objects()
    fbody.select=True
    bpy.context.scene.objects.active = fbody
    #
    # Clear modifiers
    bpy.ops.object.strip_and_clean(mod=True)
    
    if not params.exportShapekeys:
        bpy.ops.object.strip_and_clean(sk=True)
    #
    ob = bpy.context.scene.objects.active
    if (params.createSubdivMeshOnExportUnreal):
        print("Creating fbody_hires!") 
        fbody_hires = duplicate_object_by_name("fbody","fbody_hires")
        bpy.context.scene.objects.active = fbody_hires
        if True==True:
            # Clear shapekeys + modifiers
            bpy.ops.object.strip_and_clean(sk=True, mod=True)
            # Subdivide the mesh using the subdivide operator in Edit Mode
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.reveal()
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.subdivide(number_cuts=1)
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode="OBJECT")    
        print("Creating fbody_stripped!") 
        #
        fbody_stripped = duplicate_object_by_name("fbody","fbody_stripped")
        deselect_all_objects()
        fbody_stripped.select=True
        bpy.context.scene.objects.active = fbody_stripped
        print("strip_and_clean_selected_object!") 
        if False==False:
            bpy.ops.object.strip_and_clean(vg=True, sk=True, mat=True, mod=True)
            print("strip_and_clean_selected_object! DOENE") 
        #
        #
        if False == False:
            print("Creating fbody_stripped_subdiv!") 
            fbody_stripped_subdiv = duplicate_object_by_name("fbody_stripped","fbody_stripped_subdiv")
            deselect_all_objects()
            fbody_stripped_subdiv.select=True
            bpy.context.scene.objects.active = fbody_stripped_subdiv
            bpy.ops.object.modifier_add(type='SUBSURF')
            subsurf_modifier = fbody_stripped_subdiv.modifiers[-1] # get the last modifier (hence -1)
            subsurf_modifier.levels = 1  # Set the subdivision levels as needed
            # Apply the Subdivision Surface modifier
            bpy.ops.object.modifier_apply( modifier = subsurf_modifier.name )
            #    
            deselect_all_objects()
            print("fbody, fbody_hires , fbody_stripped and fbody_stripped_subdiv created!")
            #adjust_vertices_location_between_different_topology_meshes_using_lookup_dict (source_obj, target_obj)
            adjust_vertices_location_between_different_topology_meshes_using_lookup_dict(fbody_stripped_subdiv, fbody_hires)
            deselect_all_objects()
            #fbody.select = True   
            #fbody_stripped.select=True
            #fbody_hires.select=True
            fbody_stripped_subdiv.select=True
            bpy.context.scene.objects.active = fbody_stripped_subdiv
            print("Removing fbody_stripped_subdiv as we no longer need it")
            bpy.ops.object.delete(use_global=True)
        #
        #if (True == True):
        #    return   
        #fbody.select = True        
        #bpy.context.scene.objects.active = fbody
        #
        deselect_all_objects()
        #
        if not params.exportShapekeys:
            pass
        else :
            if fbody.data.shape_keys is None:
                print("Source object has no shape keys!") 
            else:        
                sk_counter = len(fbody.data.shape_keys.key_blocks)
                for idx in range(1, sk_counter):  #range is 1 and not 0, because I dont want to transfer the Basis shapekey which comes first
                    fbody.select = True
                    bpy.context.scene.objects.active = fbody
                    fbody.active_shape_key_index = idx
                    skname = fbody.active_shape_key.name
                    print("Copying Shape Key - ", skname)
                    fbody.active_shape_key_index=0
                    fbody_chupacabra_morph = duplicate_object_by_name("fbody_stripped","chupacabramorph_"+skname)
                    deselect_all_objects()
                    fbody.select = True
                    bpy.context.scene.objects.active = fbody
                    fbody.active_shape_key_index = idx            
                    fbody_chupacabra_morph.select = True
                    bpy.context.scene.objects.active = fbody_chupacabra_morph
                    bpy.ops.object.shape_key_transfer()
                    #there is no reason to set the active active_shape_key_index and clear the weights applied for the shapekey, is clean, only one and we set it anyway
                    fbody_chupacabra_morph.data.shape_keys.key_blocks[skname].value = 1.0
                    # set index to Basis shapekey and remove it so that the next shapekeys becomes basis
                    fbody_chupacabra_morph.active_shape_key_index = 0
                    bpy.ops.object.shape_key_remove(all=False)
                    # Apply the shapekey
                    print("Apply the shapekey - ", skname)
                    # Remove the real shapekey which now is the Basis (because next we want to apply the subsurf modifier)
                    bpy.ops.object.shape_key_remove(all=True)
                    # Add a Subdivision Surface modifier
                    print("Apply subdiv... ")
                    bpy.ops.object.modifier_add(type='SUBSURF')
                    chupacabra_subsurf_modifier_name = fbody_chupacabra_morph.modifiers[-1].name # get the last modifier (hence -1)
                    fbody_chupacabra_morph.modifiers[-1].levels = 1  # Set the subdivision levels as needed
                    # Apply the Subdivision Surface modifier
                    bpy.ops.object.modifier_apply( modifier = chupacabra_subsurf_modifier_name )  
                    #chupacabra_subsurf_modifier = None 
                    deselect_all_objects()
                    #transfer vertex values from fbody_chupacabra_morph into a new Shapekey on fbody_hires using the lookup vertices list
                    copy_vertices_to_shape_key_between_different_topology_meshes_using_lookup_dict(fbody_chupacabra_morph, fbody_hires, skname)                
                    #at last delete the chupacabra object
                    deselect_all_objects()
                    fbody_chupacabra_morph.select=True
                    bpy.context.scene.objects.active = fbody_chupacabra_morph
                    #
                    print("Deleting object: "+fbody_chupacabra_morph.name)
                    bpy.ops.object.delete()
                    print("Deleted object")
        #
        print("fbody_chupacabra_morph (all) created!")
        # why do we need this actually?!?
        if (True == False):
            if ( operator_exists("export.shapekeys_to_json") ):
                print("export.shapekeys_to_json is available :)")
                deselect_all_objects()
                fbody_hires.select=True
                bpy.context.scene.objects.active = fbody_hires
                cached_shapekeys_file_path = os.path.join(exportfolderpath,"cached_shapekeys.json")
                bpy.ops.export.shapekeys_to_json_non_interactive('EXEC_DEFAULT',filepath = cached_shapekeys_file_path)
            else:
                print("export.shapekeys_to_json is NOT available :(")
            #
    deselect_all_objects()
    #
    p = axis_conversion(
        from_forward='Y',
        from_up='Z',
        to_forward='X',
        to_up='Y'
        ).to_4x4()
    #
    deselect_all_objects()
    armature_object.select=True
    bpy.context.scene.objects.active = armature_object
    print("before duplicating the name is : {}".format(armature_object.name))
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.duplicate(linked=False)
    armature_clone = bpy.context.scene.objects.active
    armature_clone.name = armature_clone.name + "_clone"
    print("making friendly bones for: {}".format(armature_clone.name))
    #
    #first remove all constraints!!!
    # Ensure we are in Pose Mode
    if bpy.context.object.mode != 'POSE':
        bpy.ops.object.mode_set(mode='POSE')
    # Iterate through all pose bones
    for bone in armature_clone.pose.bones:
        # Remove all constraints from the bone
        while bone.constraints:  # Loop through all constraints
            bone.constraints.remove(bone.constraints[0])    
    #
    if params.reorientBonesOnExportUnreal:
        #lets make the bones friendly with Unreal
        #Note: changing the roll of the bone in Blender will rotate the bone on the Green (Y) axis in Unreal
        # Blender Y axis is the Unreal Y axis (green)
        # Blender X axis is the Unreal Z axis (blue)
        # Blender Z axis is the Unreal X axis (red)
        #
        # For a start, try to adjust the green axis in Unreal to match what you need, then adjust roll in Blender to match the Unreal axis
        #
        bpy.ops.object.mode_set(mode='EDIT', toggle=False)
        ebones = armature_clone.data.edit_bones
        #
        legLeftBones = ['thigh.L', 'calf.L', 'thigh_twist_01.L','thigh_twist_02.L']
        legRightBones = ['thigh.R', 'calf.R', 'thigh_twist_01.R','thigh_twist_02.R']#, 'hip_twist_jointEnd.R']
        ankleLeftBones=['foot.L']
        ankleRightBones=['foot.R']
        ballLeftBones=['ball.L']
        ballRightBones=['ball.R']  
        clavicleLeftBones =['clavicle.L']
        clavicleRightBones =['clavicle.R']
        armLeftBones = [ 'upperarm.L', 'lowerarm.L', 'upperarm_twist_01.L', 'upperarm_twist_02.L', 'lowerarm_twist_01.L', 'lowerarm_twist_02.L']
        armRightBones = [ 'upperarm.R', 'lowerarm.R', 'upperarm_twist_01.R','upperarm_twist_02.R', 'lowerarm_twist_01.R', 'lowerarm_twist_02.R']
        handLeftBones = [ 'hand.L']
        handRightBones = [ 'hand.R']
        fingerLeftBones=[
                            'index_metacarpal.L','index_01.L','index_02.L','index_03.L',
                            'middle_metacarpal.L','middle_01.L','middle_02.L','middle_03.L',
                            'ring_metacarpal.L','ring_01.L','ring_02.L','ring_03.L',
                            'pinky_metacarpal.L','pinky_01.L','pinky_02.L','pinky_03.L',
                            'thumb_01.L','thumb_02.L','thumb_03.L'
        ]
        breastLeftBones = ['breast_scale_joint.L','breast_joint01.L','breast_joint02.L','breast_nipple_joint.L','breast_nipple_jointEnd.L']
        breastRightBones = ['breast_scale_joint.R','breast_joint01.R','breast_joint02.R','breast_nipple_joint.R','breast_nipple_jointEnd.R']
        #
        spineBones = ['spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05', 'neck_01', 'neck_02', 'head', 'head_jointEnd']
        #
        rootBones = ['base'] 
        rootBones = []
        pelvisBones = ['pelvis'] 
        #
        # very important, we need to set the pivot center for rotation/scaling, otherwise we get strange results in armature orientation
        # it seems we need to go with individual origins or 3d cursor as a pivot point
        bpy.context.space_data.pivot_point = 'INDIVIDUAL_ORIGINS'
        #bpy.context.space_data.pivot_point = 'CURSOR'
        #
        #
        for boneName in rootBones:
            ebone = ebones[boneName]
            bpy.ops.armature.select_all(action='DESELECT')  # Deselect all bones first
            ebone.select = True
            ebone.select_head = True  # Select both head and tail
            ebone.select_tail = True
            # Set the 3D cursor to the pelvis bone's head (rotation pivot point)
            bpy.context.scene.cursor_location = armature_object.matrix_world * ebone.head # 2.79 uses cursor_location
            # Rotate the selected bone by 90 degrees along the X-axis in local space
            bpy.ops.transform.rotate(value=math.radians(-90), axis=(1, 0, 0), constraint_axis=(True, False, False), constraint_orientation='LOCAL')
            ebone.roll +=math.radians(0)
            # Update the scene to reflect changes
            bpy.context.scene.update()
        #
        for boneName in pelvisBones:
            ebone = ebones[boneName]
            bpy.ops.armature.select_all(action='DESELECT')  # Deselect all bones first
            ebone.select = True
            ebone.select_head = True  # Select both head and tail
            ebone.select_tail = True
            # Set the 3D cursor to the pelvis bone's head (rotation pivot point)
            bpy.context.scene.cursor_location = armature_object.matrix_world * ebone.head # 2.79 uses cursor_location
            # Rotate the selected bone by 90 degrees along the X-axis in local space
            bpy.ops.transform.rotate(value=math.radians(-90), axis=(1, 0, 0), constraint_axis=(True, False, False), constraint_orientation='LOCAL')
            ebone.roll +=math.radians(180)
            # Update the scene to reflect changes
            bpy.context.scene.update()
        #
        for boneName in spineBones:
            ebone = ebones[boneName]
            bpy.ops.armature.select_all(action='DESELECT')  # Deselect all bones first
            ebone.select = True
            ebone.select_head = True  # Select both head and tail
            ebone.select_tail = True
            # Set the 3D cursor to the pelvis bone's head (rotation pivot point)
            bpy.context.scene.cursor_location = armature_object.matrix_world * ebone.head # 2.79 uses cursor_location
            # Rotate the selected bone by 90 degrees along the X-axis in local space
            bpy.ops.transform.rotate(value=math.radians(-90), axis=(0, 0, 1), constraint_axis=( False, False, True), constraint_orientation='NORMAL')
            ebone.roll +=math.radians(180)
            # Update the scene to reflect changes
            bpy.context.scene.update()
        # first lets do the right bones, as those should follow the bone orientation for the right leg
        for boneName in legRightBones:
            ebone = ebones[boneName]
            bpy.ops.armature.select_all(action='DESELECT')  # Deselect all bones first
            ebone.select = True
            ebone.select_head = True  # Select both head and tail
            ebone.select_tail = True
            # Set the 3D cursor to the bone's head (rotation pivot point)
            bpy.context.scene.cursor_location = armature_object.matrix_world * ebone.head # 2.79 uses cursor_location
            # Rotate the selected bone by 90 degrees along the X-axis in local space
            #bpy.ops.transform.rotate(value=math.radians(-90), axis=(1, 0, 0), constraint_axis=(True, False, False), constraint_orientation='LOCAL')
            bpy.ops.transform.rotate(value=math.radians(-90), axis=(0, 0, 1), constraint_axis=(False,False,True), constraint_orientation='NORMAL')
            ebone.roll +=math.radians(180)
            # Update the scene to reflect changes
            bpy.context.scene.update()   
        #second lets do the left leg bones, as those should follow the other way, not along the the bones
        for boneName in legLeftBones:
            ebone = ebones[boneName]
            bpy.ops.armature.select_all(action='DESELECT')  # Deselect all bones first
            ebone.select = True
            ebone.select_head = True  # Select both head and tail
            ebone.select_tail = True
            # Set the 3D cursor to the pelvis bone's head (rotation pivot point)
            bpy.context.scene.cursor_location = armature_object.matrix_world * ebone.head # 2.79 uses cursor_location
            # Rotate the selected bone by 90 degrees along the X-axis in local space
            bpy.ops.transform.rotate(value=math.radians(-90), axis=(0, 0, 1), constraint_axis=(False,False,True), constraint_orientation='NORMAL')
            ebone.roll +=math.radians(0)
            # Update the scene to reflect changes
            bpy.context.scene.update()            
        #
        for boneName in ankleRightBones:
            ebone = ebones[boneName]
            bpy.ops.armature.select_all(action='DESELECT')  # Deselect all bones first
            ebone.select = True
            ebone.select_head = True  # Select both head and tail
            ebone.select_tail = True
            # Set the 3D cursor to the bone's head (rotation pivot point)
            bpy.context.scene.cursor_location = armature_object.matrix_world * ebone.head # 2.79 uses cursor_location
            # Rotate the selected bone by 90 degrees along the X-axis in local space
            bpy.ops.transform.rotate(value=math.radians(0), axis=(1, 0, 0), constraint_axis=(True, False, False), constraint_orientation='LOCAL')
            ebone.roll = math.radians(-90)
            # Update the scene to reflect changes
            bpy.context.scene.update()  
        for boneName in ankleLeftBones:
            ebone = ebones[boneName]
            bpy.ops.armature.select_all(action='DESELECT')  # Deselect all bones first
            ebone.select = True
            ebone.select_head = True  # Select both head and tail
            ebone.select_tail = True
            # Set the 3D cursor to the bone's head (rotation pivot point)
            bpy.context.scene.cursor_location = armature_object.matrix_world * ebone.head # 2.79 uses cursor_location
            # Rotate the selected bone by 90 degrees along the X-axis in local space
            bpy.ops.transform.rotate(value=math.radians(180), axis=(1, 0, 0), constraint_axis=(True, False, False), constraint_orientation='LOCAL')
            ebone.roll = math.radians(-90)
            # Update the scene to reflect changes
            bpy.context.scene.update()         
        #
        for boneName in ballLeftBones:
            ebone = ebones[boneName]
            bpy.ops.armature.select_all(action='DESELECT')  # Deselect all bones first
            ebone.select = True
            ebone.select_head = True  # Select both head and tail
            ebone.select_tail = True
            # Set the 3D cursor to the bone's head (rotation pivot point)
            bpy.context.scene.cursor_location = armature_object.matrix_world * ebone.head # 2.79 uses cursor_location
            # Rotate the selected bone by 90 degrees along the X-axis in local space
            bpy.ops.transform.rotate(value=math.radians(-90), axis=(1, 0, 0), constraint_axis=(True, False, False), constraint_orientation='LOCAL')
            ebone.roll = math.radians(270)
            # Update the scene to reflect changes
            bpy.context.scene.update()   
        for boneName in ballRightBones:
            ebone = ebones[boneName]
            bpy.ops.armature.select_all(action='DESELECT')  # Deselect all bones first
            ebone.select = True
            ebone.select_head = True  # Select both head and tail
            ebone.select_tail = True
            # Set the 3D cursor to the bone's head (rotation pivot point)
            bpy.context.scene.cursor_location = armature_object.matrix_world * ebone.head # 2.79 uses cursor_location
            # Rotate the selected bone by 90 degrees along the X-axis in local space
            bpy.ops.transform.rotate(value=math.radians(90), axis=(1, 0, 0), constraint_axis=(True, False, False), constraint_orientation='LOCAL')
            ebone.roll = math.radians(270)
            # Update the scene to reflect changes
            bpy.context.scene.update()   
        #
        for boneName in clavicleLeftBones:
            ebone = ebones[boneName]
            bpy.ops.armature.select_all(action='DESELECT')  # Deselect all bones first
            ebone.select = True
            ebone.select_head = True  # Select both head and tail
            ebone.select_tail = True
            # Set the 3D cursor to the bone's head (rotation pivot point)
            bpy.context.scene.cursor_location = armature_object.matrix_world * ebone.head # 2.79 uses cursor_location
            # Rotate the selected bone by 90 degrees along the X-axis in local space
            bpy.ops.transform.rotate(value=math.radians(90), axis=(0, 0, 1), constraint_axis=(False, False, True), constraint_orientation='NORMAL')
            ebone.roll += math.radians(0)
            # Update the scene to reflect changes
            bpy.context.scene.update()
        #
        for boneName in clavicleRightBones:
            ebone = ebones[boneName]
            bpy.ops.armature.select_all(action='DESELECT')  # Deselect all bones first
            ebone.select = True
            ebone.select_head = True  # Select both head and tail
            ebone.select_tail = True
            # Set the 3D cursor to the bone's head (rotation pivot point)
            bpy.context.scene.cursor_location = armature_object.matrix_world * ebone.head # 2.79 uses cursor_location
            bpy.ops.transform.rotate(value=math.radians(90), axis=(0, 0, 1), constraint_axis=(False, False, True), constraint_orientation='NORMAL')
            ebone.roll += math.radians(180)
            # Update the scene to reflect changes
            bpy.context.scene.update()     
        #   
        for boneName in armLeftBones:
            ebone = ebones[boneName]
            bpy.ops.armature.select_all(action='DESELECT')  # Deselect all bones first
            ebone.select = True
            ebone.select_head = True  # Select both head and tail
            ebone.select_tail = True
            # Set the 3D cursor to the bone's head (rotation pivot point)
            bpy.context.scene.cursor_location = armature_object.matrix_world * ebone.head # 2.79 uses cursor_location
            # Rotate the selected bone by 90 degrees along the X-axis in local space
            bpy.ops.transform.rotate(value=math.radians(90), axis=(0, 0, 1), constraint_axis=(False, False, True), constraint_orientation='LOCAL')
            ebone.roll += math.radians(-90)
            # Update the scene to reflect changes
            bpy.context.scene.update()     
        for boneName in armRightBones:
            ebone = ebones[boneName]
            bpy.ops.armature.select_all(action='DESELECT')  # Deselect all bones first
            ebone.select = True
            ebone.select_head = True  # Select both head and tail
            ebone.select_tail = True
            # Set the 3D cursor to the bone's head (rotation pivot point)
            bpy.context.scene.cursor_location = armature_object.matrix_world * ebone.head # 2.79 uses cursor_location
            # Rotate the selected bone by 90 degrees along the X-axis in local space
            bpy.ops.transform.rotate(value=math.radians(90), axis=(0, 0, 1), constraint_axis=(False, False, True), constraint_orientation='LOCAL')
            ebone.roll += math.radians(-90)
            # Update the scene to reflect changes
            bpy.context.scene.update()  
        for boneName in handLeftBones:
            ebone = ebones[boneName]
            bpy.ops.armature.select_all(action='DESELECT')  # Deselect all bones first
            ebone.select = True
            ebone.select_head = True  # Select both head and tail
            ebone.select_tail = True
            # Set the 3D cursor to the bone's head (rotation pivot point)
            bpy.context.scene.cursor_location = armature_object.matrix_world * ebone.head # 2.79 uses cursor_location
            #ebone.roll = math.radians(0)
            # Rotate the selected bone by 90 degrees along the X-axis in local space
            bpy.ops.transform.rotate(value=math.radians(90), axis=(0, 1, 0), constraint_axis=(False, True, False), constraint_orientation='LOCAL')
            ebone.roll += math.radians(180)
            # Update the scene to reflect changes
            bpy.context.scene.update()         
        for boneName in handRightBones:
            ebone = ebones[boneName]
            bpy.ops.armature.select_all(action='DESELECT')  # Deselect all bones first
            ebone.select = True
            ebone.select_head = True  # Select both head and tail
            ebone.select_tail = True
            # Set the 3D cursor to the bone's head (rotation pivot point)
            bpy.context.scene.cursor_location = armature_object.matrix_world * ebone.head # 2.79 uses cursor_location
            #ebone.roll = math.radians(0)
            # Rotate the selected bone by 90 degrees along the X-axis in local space
            bpy.ops.transform.rotate(value=math.radians(90), axis=(0, 1, 0), constraint_axis=(False, True, False), constraint_orientation='LOCAL')
            ebone.roll += math.radians(0)
            # Update the scene to reflect changes
            bpy.context.scene.update()   
        #armature_clone.rotation_mode = 'ZXY'           
        for boneName in fingerLeftBones:
            ebone = ebones[boneName]
            bpy.ops.armature.select_all(action='DESELECT')  # Deselect all bones first
            ebone.select = True
            ebone.select_head = True  # Select both head and tail
            ebone.select_tail = True
            # Set the 3D cursor to the bone's head (rotation pivot point)
            bpy.context.scene.cursor_location = armature_object.matrix_world * ebone.head # 2.79 uses cursor_location
            #ebone.roll = math.radians(0)
            # Rotate the selected bone by 90 degrees along the X-axis in local space
            bpy.ops.transform.rotate(value=math.radians(270), axis=(1, 0, 0), constraint_axis=(True,False,False), constraint_orientation='NORMAL')
            ebone.roll += math.radians(-90)
            # Update the scene to reflect changes
            bpy.context.scene.update()       
        for boneName in breastRightBones:
            ebone = ebones[boneName]
            bpy.ops.armature.select_all(action='DESELECT')  # Deselect all bones first
            ebone.select = True
            ebone.select_head = True  # Select both head and tail
            ebone.select_tail = True
            # Set the 3D cursor to the bone's head (rotation pivot point)
            bpy.context.scene.cursor_location = armature_object.matrix_world * ebone.head # 2.79 uses cursor_location
            #ebone.roll = math.radians(0)
            # Rotate the selected bone by 90 degrees along the X-axis in local space
            bpy.ops.transform.rotate(value=math.radians(90), axis=(1, 0, 0), constraint_axis=(True, False, False), constraint_orientation='NORMAL')
            ebone.roll += math.radians(90)
            # Update the scene to reflect changes
            bpy.context.scene.update()     
        for boneName in breastLeftBones:
            ebone = ebones[boneName]
            bpy.ops.armature.select_all(action='DESELECT')  # Deselect all bones first
            ebone.select = True
            ebone.select_head = True  # Select both head and tail
            ebone.select_tail = True
            # Set the 3D cursor to the bone's head (rotation pivot point)
            bpy.context.scene.cursor_location = armature_object.matrix_world * ebone.head # 2.79 uses cursor_location
            #ebone.roll = math.radians(0)
            # Rotate the selected bone by 90 degrees along the X-axis in local space
            bpy.ops.transform.rotate(value=math.radians(90), axis=(1, 0, 0), constraint_axis=(True, False, False), constraint_orientation='NORMAL')
            ebone.roll += math.radians(-90)
            # Update the scene to reflect changes
            bpy.context.scene.update()                         
    #
    # Update the view
    bpy.context.scene.update()
    #
    #
    #we are done with making the bones friendly, lets go back to object mode to also transform the armature as a whole
    bpy.ops.object.mode_set(mode='OBJECT')
    #
    #if True==True:
    #    return
    #
    scaleVector = Vector((100,100,100))
    rotationOnXAxis =  radians(-0)
    rotationOnYAxis =  radians(0)
    rotationOnZAxis =  radians(0)
    #
    #scaleVector = Vector((1,1,1))
    #rotationOnXAxis =  radians(0)
    #
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    #armature_clone.rotation_euler[0] = rotationOnXAxis
    bpy.ops.object.transform_apply(rotation=True)
    armature_clone.scale = scaleVector
    bpy.ops.object.transform_apply(scale = True)
    armature_clone.name='root'
    #
    #
    LODs = []
    emptyLodGroup = bpy.data.objects.new( "fbodyLodGroup", None )
    emptyLodGroup["fbx_type"] = "LodGroup"
    emptyLodGroup["lookupVertexIdTable"] = "some/path/on/computer"
    bpy.context.scene.objects.link( emptyLodGroup )
    emptyLodGroup.select=True
    bpy.context.scene.objects.active = emptyLodGroup
    emptyLodGroup.scale = scaleVector
    bpy.ops.object.transform_apply(scale = True)
    #fbody_hires.parent = emptyLodGroup
    #fbody.parent = emptyLodGroup

    #add the armature modifier
    deselect_all_objects()
    if params.createSubdivMeshOnExportUnreal:
        fbody_hires.select=True
        bpy.context.scene.objects.active = fbody_hires
        fbody_hires.rotation_euler[0] = rotationOnXAxis
        bpy.ops.object.transform_apply(rotation=True)    
        fbody_hires.scale = scaleVector
        bpy.ops.object.transform_apply(scale = True)    
        # Add the armature modifier
        bpy.ops.object.modifier_add(type='ARMATURE')
        armature_modifier = fbody_hires.modifiers[-1]
        # Set the armature object for the modifier
        armature_modifier.object = armature_clone
        LODs.append(fbody_hires)
    
    #add the armature modifier
    deselect_all_objects()
    fbody.select=True
    bpy.context.scene.objects.active = fbody
    fbody.rotation_euler[0] = rotationOnXAxis
    #fbody.rotation_euler[1] = rotationOnZAxis
    bpy.ops.object.transform_apply(rotation=True)   
    fbody.scale = scaleVector
    bpy.ops.object.transform_apply(scale = True)      
    # Add the armature modifier
    bpy.ops.object.modifier_add(type='ARMATURE')
    armature_modifier = fbody.modifiers[-1]
    # Set the armature object for the modifier
    armature_modifier.object = armature_clone
    LODs.append(fbody)

    #the order in which we set the parent is important it seems, otherwise in Unreal it will appear in the wrong order
    for i,lod in enumerate(LODs):
        lod.name="fbody_LOD{}".format(i)
        lod.parent = emptyLodGroup
        bpy.context.scene.update()	
        #print(o.name, o.type, o.data)

    # #rename them
    # fbody.name = "fbody_LOD1"
    # fbody_hires.name = "fbody_LOD0"
    
    # fbody_hires.parent = emptyLodGroup
    # bpy.context.scene.update()	
    # fbody.parent = emptyLodGroup
    # bpy.context.scene.update()	
    #
    emptyLodGroup.parent = armature_clone

    fix_translation_orientation_scale_for_unreal(armature_clone)


    bpy.context.scene.unit_settings.system = 'METRIC'
    #bpy.context.scene.unit_settings.length_unit = 'CENTIMETERS'  # You can also set 'CENTIMETERS'
    bpy.context.scene.unit_settings.scale_length = 0.01

    #fbx export:
    emptyLodGroup.select=True
    for i,lod in enumerate(LODs):
        lod.select=True
    armature_clone.select=True
    bpy.context.scene.objects.active = armature_clone
    export_params = {
    "filepath": os.path.join(exportfolderpath,params.fbxFilename),#"SK_Belle.fbx"
    "check_existing": False,
    "filter_glob": "*.fbx",
    "version": 'BIN7400',
    "ui_tab": 'MAIN',
    "use_selection": True,
    "global_scale": 1.0,
    "apply_unit_scale": True,
    "apply_scale_options": 'FBX_SCALE_NONE',
    "bake_space_transform": False,
    "object_types": {'ARMATURE', 'EMPTY', 'MESH' }, #'OTHER'
    "use_mesh_modifiers": False,
    "use_mesh_modifiers_render": False,
    "mesh_smooth_type": 'FACE',
    "use_mesh_edges": False,
    "use_tspace": True,
    "use_custom_props": True,
    "add_leaf_bones": False,
    #working - also appears in blueraven
    "axis_forward": 'Y',
    "axis_up": 'Z',
    #v1
    #"primary_bone_axis": 'Y',
    #"secondary_bone_axis": 'X',
    #chatgpt1
    #"axis_forward": '-Z',
    #"axis_up": 'X',
    "primary_bone_axis": 'Y',
    "secondary_bone_axis": 'X',    
    "use_armature_deform_only": True,
    "armature_nodetype": 'NULL', # ???????
    "bake_anim": False,
    "bake_anim_use_all_bones": False,
    "bake_anim_use_nla_strips": False,
    "bake_anim_use_all_actions": False,
    "bake_anim_force_startend_keying": False,
    "bake_anim_step": 1.0,
    "bake_anim_simplify_factor": 1.0,
    "use_anim": False,
    "use_anim_action_all": False,
    "use_default_take": False,
    "use_anim_optimize": False,
    "anim_optimize_precision": 6.0,
    "path_mode": 'COPY',
    "embed_textures": True,
    "batch_mode": 'OFF',
    "use_batch_own_dir": True,
    "use_metadata": True,
    }

    bpy.ops.export_scene.fbx(**export_params)

    bpy.context.scene.unit_settings.system = 'NONE'
    bpy.context.scene.unit_settings.scale_length = 1.0 
    #
    duration = 1000  # milliseconds
    freq = 440  # Hz
    winsound.Beep(freq, duration)
    #
    #
    ctypes.windll.user32.FlashWindow(ctypes.windll.user32.GetActiveWindow(), True )
    #
    #
    deselect_all_objects()
    #
    if params.cleanupTempMeshesMode =="AFTER" or params.cleanupTempMeshesMode =="BOTH":
        #
        fbody_stripped = bpy.data.objects.get("fbody_stripped")
        if fbody_stripped is not None:
            fbody_stripped.select=True
            bpy.context.scene.objects.active = fbody_stripped
        #
        fbody_stripped_subdiv = bpy.data.objects.get("fbody_stripped_subdiv")
        if fbody_stripped_subdiv is not None:
            fbody_stripped_subdiv.select=True
            bpy.context.scene.objects.active = fbody_stripped_subdiv
        #
        emptyLodGroup.select=True
        for i,lod in enumerate(LODs):
            lod.select=True
        armature_clone.select=True
        bpy.context.scene.objects.active = armature_clone        
        bpy.ops.object.delete(use_global=True)   
    deselect_all_objects()
    #end


def fix_translation_orientation_scale_for_unreal(armature_object):
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    if (armature_object.rotation_euler.x!=0 or armature_object.rotation_euler.y!=0 or armature_object.rotation_euler.z!=0):
        print("Armature has a rotation applied, fix that first")
        ShowMessageBox("Armature has a rotation applied, fix that first", "Error", 'ERROR')
        return None
    
    mirror_x_flag = armature_object.data.use_mirror_x
    armature_object.data.use_mirror_x = False

    

    
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)
    armature_object.select = True
    bpy.context.scene.objects.active = armature_object
    
    bpy.ops.object.transform_apply(location = True)

    armature_object.rotation_euler.z= radians(0)#90
    bpy.ops.object.transform_apply(rotation = True)
    #

    #armature_object.scale = Vector((100,100,100))
    #bpy.ops.object.transform_apply(scale = True)


    """
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)
    ebones = armature_object.data.edit_bones
    ebones["root"].head  = Vector((0,0,0))
    tail = ebones["root"].tail.copy()
    ebones["root"].tail = Vector((0,0,tail.z))
    """
    #
    bpy.ops.object.mode_set(mode='OBJECT', toggle=False)