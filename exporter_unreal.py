#17418 only body
#18105 with gens
#71523 subdiv body with gens
 
import bpy, math, mathutils
import re
from collections import OrderedDict
from collections import defaultdict
from itertools import combinations

import os
import sys
import time
from .utils import *
from .tools_message_box import *
from .diffeomorphic_merge_geografts import geograft_data_available, merge_geografts_into_active

from . import fbody_stats
#from . import strip_and_clean_op

from mathutils import Vector
from mathutils import Matrix
from math import radians

from math import degrees
from bpy_extras.io_utils import axis_conversion

import bpy
import json
import struct
import hashlib

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


def get_geograft_children(parent_obj):
    """
    Return a sorted list of all child meshes of parent_obj
    whose names match 'geograft_<number>_'.
    Sorted numerically by <number>.
    """
    pattern = re.compile(r"^geograft_(\d+)_")
    matched_children = []

    for child in parent_obj.children:
        if child.type != 'MESH':
            continue

        match = pattern.match(child.name)
        if match:
            index = int(match.group(1))
            matched_children.append((index, child))

    # Sort by the numeric index
    matched_children.sort(key=lambda x: x[0])

    # Return only the sorted child objects
    return [child for _, child in matched_children]


def get_refined_geograft_names(geograft_children):
    """Return a list of names after removing 'geograft_<number>_' from each object's name."""
    pattern = re.compile(r"^geograft_\d+_")
    refined = []

    for obj in geograft_children:
        new_name = pattern.sub("", obj.name)
        refined.append(new_name)

    return refined

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
    print("len(target_obj.data.vertices): {} ".format(len(target_obj.data.vertices)))
    # Bulk read all source vertex positions
    n_src = len(source_obj.data.vertices)
    src_cos = [0.0] * (n_src * 3)
    source_obj.data.vertices.foreach_get("co", src_cos)
    # Bulk read current target positions (for vertices not in the lookup dict)
    n_tgt = len(target_obj.data.vertices)
    tgt_cos = [0.0] * (n_tgt * 3)
    target_obj.data.vertices.foreach_get("co", tgt_cos)
    # Remap using lookup dict (pure Python, no Blender API calls per vertex)
    for tgt_idx, src_idx in loaded_int_key_dict.items():
        tgt_cos[tgt_idx * 3]     = src_cos[src_idx * 3]
        tgt_cos[tgt_idx * 3 + 1] = src_cos[src_idx * 3 + 1]
        tgt_cos[tgt_idx * 3 + 2] = src_cos[src_idx * 3 + 2]
    # Bulk write to target
    target_obj.data.vertices.foreach_set("co", tgt_cos)
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
    print("len(target_obj.data.vertices): {} ".format(len(target_obj.data.vertices)))
    # Bulk read all source vertex positions
    n_src = len(source_obj.data.vertices)
    src_cos = [0.0] * (n_src * 3)
    source_obj.data.vertices.foreach_get("co", src_cos)
    # Bulk read current shape key positions (Basis values as default)
    n_tgt = len(new_shape_key.data)
    tgt_cos = [0.0] * (n_tgt * 3)
    new_shape_key.data.foreach_get("co", tgt_cos)
    # Remap using lookup dict (pure Python, no Blender API calls per vertex)
    for tgt_idx, src_idx in loaded_int_key_dict.items():
        tgt_cos[tgt_idx * 3]     = src_cos[src_idx * 3]
        tgt_cos[tgt_idx * 3 + 1] = src_cos[src_idx * 3 + 1]
        tgt_cos[tgt_idx * 3 + 2] = src_cos[src_idx * 3 + 2]
    # Bulk write to shape key
    new_shape_key.data.foreach_set("co", tgt_cos)
    target_obj.data.update()
    # Final message
    print("Vertex positions from '{}' copied to new shape key '{}' on '{}'.".format(source_obj.name, new_shape_key_name, target_obj.name))


SHAPEKEY_CACHE_MAGIC = b'VXSK'
SHAPEKEY_CACHE_VERSION = 1


def compute_basis_fingerprint(mesh_obj):
    """Compute MD5 fingerprint of a mesh object's vertex positions."""
    n = len(mesh_obj.data.vertices)
    cos = [0.0] * (n * 3)
    mesh_obj.data.vertices.foreach_get("co", cos)
    raw = struct.pack('<%df' % len(cos), *cos)
    return hashlib.md5(raw).digest()


def save_shapekey_subdiv_cache(filepath, vxasset_hires, sk_names, fingerprint):
    """Save subdivided shape key data to a binary cache file."""
    n_verts = len(vxasset_hires.data.vertices)
    n_keys = len(sk_names)
    with open(filepath, 'wb') as f:
        # Header
        f.write(SHAPEKEY_CACHE_MAGIC)
        f.write(struct.pack('<III', SHAPEKEY_CACHE_VERSION, n_verts, n_keys))
        f.write(fingerprint)
        # Per shape key
        key_blocks = vxasset_hires.data.shape_keys.key_blocks
        for skname in sk_names:
            name_bytes = skname.encode('utf-8')
            f.write(struct.pack('<I', len(name_bytes)))
            f.write(name_bytes)
            sk = key_blocks[skname]
            cos = [0.0] * (n_verts * 3)
            sk.data.foreach_get("co", cos)
            f.write(struct.pack('<%df' % len(cos), *cos))
    print("Saved shape key cache ({} keys, {} verts) to {}".format(n_keys, n_verts, filepath))


def load_shapekey_subdiv_cache(filepath, n_verts, sk_names, fingerprint):
    """Load and validate a shape key subdivision cache.
    Returns dict {skname: float_list} or None if cache is invalid/missing."""
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, 'rb') as f:
            # Read and validate header
            magic = f.read(4)
            if magic != SHAPEKEY_CACHE_MAGIC:
                print("Cache invalid: bad magic")
                return None
            version, cached_n_verts, cached_n_keys = struct.unpack('<III', f.read(12))
            if version != SHAPEKEY_CACHE_VERSION:
                print("Cache invalid: version mismatch ({} != {})".format(version, SHAPEKEY_CACHE_VERSION))
                return None
            if cached_n_verts != n_verts:
                print("Cache invalid: vertex count mismatch ({} != {})".format(cached_n_verts, n_verts))
                return None
            if cached_n_keys != len(sk_names):
                print("Cache invalid: key count mismatch ({} != {})".format(cached_n_keys, len(sk_names)))
                return None
            cached_fp = f.read(16)
            if cached_fp != fingerprint:
                print("Cache invalid: fingerprint mismatch (mesh geometry changed)")
                return None
            # Read per-key data
            result = {}
            floats_per_key = n_verts * 3
            bytes_per_key = floats_per_key * 4
            for i in range(cached_n_keys):
                name_len = struct.unpack('<I', f.read(4))[0]
                name = f.read(name_len).decode('utf-8')
                if i >= len(sk_names) or name != sk_names[i]:
                    print("Cache invalid: key name mismatch at index {} ('{}' != '{}')".format(i, name, sk_names[i] if i < len(sk_names) else '?'))
                    return None
                cos = list(struct.unpack('<%df' % floats_per_key, f.read(bytes_per_key)))
                result[name] = cos
        print("Loaded shape key cache ({} keys) from {}".format(len(result), filepath))
        return result
    except (IOError, struct.error) as e:
        print("Cache read error: {}".format(e))
        return None


def duplicate_object_data_level(source_obj, new_name=None):
    """Data-level mesh duplication — creates a fresh object with a copy of the mesh data.
    Uses bpy.data.objects.new() instead of obj.copy() to avoid carrying stale
    internal references (animation data, drivers, undo state) that can crash
    when mixed with bpy.ops.object.delete() in loops."""
    new_mesh = source_obj.data.copy()
    new_obj = bpy.data.objects.new(new_name or source_obj.name + "_copy", new_mesh)
    bpy.context.scene.objects.link(new_obj)
    return new_obj

def delete_object_data_level(obj):
    """Data-level object removal — pairs with duplicate_object_data_level.
    Removes the object and its mesh data without operator dispatch."""
    mesh = obj.data
    bpy.context.scene.objects.unlink(obj)
    bpy.data.objects.remove(obj)
    if mesh and mesh.users == 0:
        bpy.data.meshes.remove(mesh)

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
    return new_object


# this function is supposed to take the base res mesh (or body) and make 2 duplicates
# hires from edit mode subdivide operator - vertices from 0 .. 18119 are coming from the base (unsubdivided) mesh
def build_subdivision_vertex_matching_table(params):
    """
    Builds and exports three JSON files that describe how the base mesh vertices relate to the
    subdivided mesh vertices. Must be run before FBX export when subdivision is needed.

    OVERVIEW
    --------
    Two temporary meshes are created from the active object:

      vxasset_from_editmode_subdivide_operator  (= "vxasset")
          The base mesh subdivided once using Blender's Edit Mode > Subdivide operator.
          This is the mesh that gets exported to Unreal as LOD0.
          The edit-mode subdivide keeps base vertex indices intact (0..N-1 are unchanged).

      vxasset_from_objmode_subsurf_modifier  (= "vxasset_hires")
          The base mesh with a Subdivision Surface modifier applied in Object Mode.
          Produces better smoothing than the edit-mode operator but uses a different
          vertex ordering. Used in Blender to author shape keys / morphs.

    THE VERTEX GROUP TRICK
    ----------------------
    Before subdividing, every base vertex is assigned its own vertex group named after its
    index ("0", "1", ...). After subdivision each new vertex inherits the groups of its
    parent vertices, revealing exactly which base vertices produced it:
      - 1 group  → "base"  vertex (unchanged from base mesh)
      - 2 groups → "edge"  vertex (midpoint of 2 base vertices)
      - 4 groups → "face"  vertex (centroid of 4 base vertices, one per quad corner)

    OUTPUT FILES  (written to params.exportFolderPathUnreal)
    --------------------------------------------------------
    1. {mergedMeshesName}_vertex_mapping_list.json   ← PRIMARY, used by Unreal
       JSON array. One entry per subdivided vertex:
         {"index": int, "type": "base"|"edge"|"face", "base_indices": [int, ...]}
       base entries also include: connected_base_neighbor_indices, connected_faces_base_indices
       edge entries also include: adjacent_face_point_indices, adjacent_faces_base_indices
       Written with inline arrays (dumps_inline_arrays) for compact but readable formatting.
       Linked to the Unreal asset via FBX custom property:
         vxasset_hires["lookupVertexIdTable"] = mergedMeshesName + "_vertex_mapping_list.json"

    2. {mergedMeshesName}_vertex_groups_dict.json    ← simple compact form, Blender reference
       JSON object: {"subdivIdx": "baseIdx1_baseIdx2_..."}
       Compact version of the mapping list — base indices joined by underscores.
       Superseded by the mapping list for Unreal use; kept as a simpler debug reference.

    3. {mergedMeshesName}_matching_index_dict.json   ← Blender-internal use ONLY
       JSON object: {"editModeVertIdx": subsurfVertIdx}
       Maps each edit-mode-subdivide vertex to the corresponding subsurf-modifier vertex.
       Used within Blender to transfer shape key deltas from vxasset_hires back to vxasset.
       NOT needed in Unreal — do not embed in .uasset.

    GEOGRAFT HANDLING
    -----------------
    If params.includeGeograftsOnExportUnreal is True, geograft children are merged into the
    base mesh before subdividing, and mergedMeshesName becomes the combined name
    (e.g. "Belle_genz" for Belle + genz geograft).

    CLEANUP
    -------
    Temporary meshes (vxasset, vxasset_hires) are deleted after export if
    params.cleanupTempMeshesMode is 'AFTER' or 'BOTH'.
    """
    obj = bpy.context.active_object
    if not obj or obj.type != 'MESH':
        ShowMessageBox("No mesh object selected for export.", "Error", 'ERROR')
        return None

    if obj.hide :
        ShowMessageBox("Object {} is not visible!".format(obj.name), "Error", 'ERROR')
        return None

    armature_modifier = next((mod for mod in obj.modifiers if mod.type == 'ARMATURE'), None)
    armature_object = armature_modifier.object if armature_modifier else None

    if armature_object is None:
        ShowMessageBox("Object {} has no armature!".format(obj.name), "Error", 'ERROR')
        return None        
    armature_object.hide = False
    
    exportfolderpath = os.path.join(params.exportFolderPathUnreal,"")    
    if not os.path.exists(exportfolderpath):
        os.makedirs(exportfolderpath)
    
    hiddenStatusGeografts = {}
    mergeGeografts = []
    anatomies = []
    
    mergedMeshesName = obj.name
    obj.select = True
    bpy.context.scene.objects.active = obj
    
    if not params.includeGeograftsOnExportUnreal:
        mergedMeshesName = obj.name
        pass
    else:
        if not geograft_data_available():
            ShowMessageBox("'Include Geografts' is checked, but the Difeomorphic addon (import_daz) is not enabled, so there is no geograft data", "Error", 'ERROR')
            return None
        #
        geograft_children = get_geograft_children(obj)
        if len(geograft_children)==0:
            ShowMessageBox("'Include Geografts' is checked, but there are no geograft_ children for the exported mesh", "Error", 'ERROR')
            return None
        else:
            for geograftObj in geograft_children:
                hiddenStatusGeografts[geograftObj.name] = geograftObj.hide
                if geograftObj.hide :
                    geograftObj.hide = False # we need to show it, otherwise can't merge using a hidden object
        geograft_refined = get_refined_geograft_names(geograft_children)
        mergedMeshesName = "_".join([obj.name] +geograft_refined)
    #
    obj.select = True
    bpy.context.scene.objects.active = obj
    bpy.ops.object.duplicate(linked=False)
    vxasset = bpy.context.scene.objects.active
    vxasset.name = "vxasset_base_res"

    if params.includeGeograftsOnExportUnreal:
        print("includeGeograftsOnExportUnreal is ON")
        #deselect_all_objects()
        #
        #
        for geograftObj in geograft_children:
            deselect_all_objects()
            geograftObj.select = True
            bpy.context.scene.objects.active = geograftObj
            bpy.ops.object.duplicate(linked=False)
            geoClone = bpy.context.scene.objects.active
            geoClone.parent = vxasset
            anatomies.append(geoClone)
            geograftObj.hide = hiddenStatusGeografts[geograftObj.name] # we need to restore the hidden status
        #
        deselect_all_objects()
        #
        for geo in anatomies:
            geo.select = True
            bpy.context.scene.objects.active = geo
        vxasset.select=True
        bpy.context.scene.objects.active = vxasset
        vxasset.select=True
        # merge operators live in diffeomorphic_merge_geografts.py (vxmod.merge_geografts*)
        merge_geografts_into_active()
    
    
    deselect_all_objects()
    vxasset.select=True
    bpy.context.scene.objects.active = vxasset
    #remove everything that is not required from vxasset
    bpy.ops.gmtt.object_strip_and_clean(vg=True, sk=True, mod=True)
    #
    bpy.ops.object.mode_set(mode='OBJECT')
    #
    # Clear existing vertex groups
    #vxasset.vertex_groups.clear()
    #
    # Iterate over all vertices in the mesh
    for i, vertex in enumerate(vxasset.data.vertices):
        # Create a new vertex group named after the vertex index
        vg = vxasset.vertex_groups.new(name=str(i))
        #
        # Add the vertex to the group with a weight of 1.0
        vg.add([i], 1.0, 'ADD')
        #
    print("Assigned weights to all vxasset vertices.")    
    #
    #
    obj = bpy.context.scene.objects.active
    print("Creating vxasset_hires!") 
    vxasset_hires = duplicate_object_by_name("vxasset_base_res","vxasset_from_objmode_subsurf_modifier")
    bpy.context.scene.objects.active = vxasset_hires
    #first lets remove all shapekeys and existing modifiers
    bpy.ops.gmtt.object_strip_and_clean(sk=True, mod=True)
    # Add a Subdivision Surface modifier
    bpy.ops.object.modifier_add(type='SUBSURF')
    subsurf_modifier = vxasset_hires.modifiers[-1] # get the last modifier (hence -1)
    subsurf_modifier.levels = 1  # Set the subdivision levels as needed
    # Apply the Subdivision Surface modifier
    bpy.ops.object.modifier_apply( modifier = subsurf_modifier.name )
    #
    vxasset.select = True 
    #
    bpy.context.scene.objects.active = vxasset
    # Switch to Edit Mode
    bpy.ops.object.mode_set(mode='EDIT')
    # Select all vertices
    bpy.ops.mesh.select_all(action='SELECT')
    # Subdivide the selected vertices
    bpy.ops.mesh.subdivide()
    # Switch back to Object Mode (optional)
    bpy.ops.object.mode_set(mode='OBJECT')
    vxasset.name = "vxasset_from_editmode_subdivide_operator"
    #
    deselect_all_objects()
    # lets create the lookup dict for vxasset (subdiv operator in edit mode)
    vxasset.select = True        
    #
    bpy.context.scene.objects.active = vxasset
    #
    vertex_groups_dict = {}
    # Ensure the object exists and is a mesh
    if vxasset and vxasset.type == 'MESH':
        # Initialize an empty dictionary to store vertex groups for each vertex
        # Loop through all vertices in the mesh
        for vertex in vxasset.data.vertices:
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
        file_path = os.path.join(exportfolderpath,mergedMeshesName+"_vertex_mapping_list.json")
        # Write to file with arrays forced inline
        with open(file_path, 'w') as json_file:
            json_file.write(dumps_inline_arrays(mapping_list))
        # with open(file_path, 'w') as json_file:
        #     json.dump(mapping_list, json_file, indent=2)
        #
        file_path = os.path.join(exportfolderpath,mergedMeshesName+"_vertex_groups_dict.json")
        # Save the lookup table to a JSON file
        with open(file_path, 'w') as json_file:
            json.dump(vertex_groups_dict, json_file)
    else:
        print("The specified object either does not exist or is not a mesh.")
    # lets create the lookup dict for vxasset_hires (subsurf modifier)
    deselect_all_objects()
    vxasset_hires.select = True        
    #
    bpy.context.scene.objects.active = vxasset_hires
    #
    vertex_groups_dict_backwards = {}
    # Ensure the object exists and is a mesh
    if vxasset_hires and vxasset_hires.type == 'MESH':
        # Initialize an empty dictionary to store vertex groups for each vertex\
        # Loop through all vertices in the mesh
        for vertex in vxasset_hires.data.vertices:
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
    vxasset.select = True        
    #
    bpy.context.scene.objects.active = vxasset
    # Ensure the object exists and is a mesh
    if vxasset and vxasset.type == 'MESH':
        vxasset_matching_index_dict = OrderedDict()
        # Loop through all vertices in the mesh
        for vertex in vxasset.data.vertices:
            vxasset_matching_index_dict[vertex.index]=vertex_groups_dict_backwards[vertex_groups_dict[vertex.index]]
        # Convert dictionary to a JSON string
        dict_as_string = json.dumps(vxasset_matching_index_dict)
        # Store it in the Scene's custom properties
        #or maybe not?!?!
        #bpy.context.scene['my_global_vxasset_matching_index_dict'] = dict_as_string
        # Specify the file path where you want to save the JSON file
        # Make sure you have permission to write to this location
        file_path = os.path.join(exportfolderpath,mergedMeshesName+"_matching_index_dict.json")
        # Save the lookup table to a JSON file
        with open(file_path, 'w') as json_file:
            json.dump(vxasset_matching_index_dict, json_file)
        print("Lookup table saved to:", file_path)
    
    deselect_all_objects()
    if params.cleanupTempMeshesMode=='AFTER' or params.cleanupTempMeshesMode=='BOTH':
        vxasset.select = True        
        bpy.context.scene.objects.active = vxasset
        vxasset_hires.select = True        
        bpy.context.scene.objects.active = vxasset_hires        
        bpy.ops.object.delete(use_global=True)   
    #
    deselect_all_objects()


def load_subdivision_vertex_matching_table(params) : 
    #
    obj = bpy.context.active_object
    if not obj or obj.type != 'MESH':
        ShowMessageBox("No mesh object selected.", "Error", 'ERROR')
        return None
    exportfolderpath = os.path.join(params.exportFolderPathUnreal,"")    
    if not os.path.exists(exportfolderpath):
        os.makedirs(exportfolderpath)    
    # Load the JSON data from the file
    file_path = os.path.join(exportfolderpath,"{}_matching_index_dict.json".format(obj.name))
    with open(file_path, 'r') as json_file:
        loaded_dict = json.load(json_file)
    # Convert the keys back to integers
    int_key_dict = {int(k): v for k, v in loaded_dict.items()}
    # Optionally convert it back to an OrderedDict if needed
    loaded_ordered_dict = OrderedDict(int_key_dict)
    print(loaded_ordered_dict)  # Output: {'a': 1, 'b': 2, 'c': 3}
    print("Dictionary size: {} ".format(len(loaded_ordered_dict)))
    deselect_all_objects()
    #



def _notify_export_complete():
    """Signal export completion. Windows: beep + flash taskbar. Other platforms: no-op."""
    if sys.platform == 'win32':
        import winsound
        import ctypes
        winsound.Beep(440, 1000)
        ctypes.windll.user32.FlashWindow(ctypes.windll.user32.GetActiveWindow(), True)



ORIENTATION_PROP = "vx_orientation"
ORIENTATION_BP = "BP"
ORIENTATION_UE5 = "UE5"
ORIENTATION_DAZ = "DAZ"


def _unreal_bone_name(name):
    """calf.L -> calf_l. The inverse of manny_blender_perfect_generated's
    normalizeBoneName. Bones with no side suffix pass through untouched.

    Blender accepts '.', '_', '-' and space as side separators, so .L/.R is a
    house style rather than a requirement - which is why the working rig can keep
    it and only the export clone gets the Unreal spelling."""
    if len(name) > 2 and name[-2] == '.':
        side = name[-1].lower()
        if side in ('l', 'r'):
            return name[:-2] + '_' + side
    return name


def rename_bones_for_unreal(armature_clone):
    """Rename the clone's bones from .L/.R to Epic's _l/_r.

    Vertex groups come along for free: renaming a bone propagates to the matching
    vertex group on every mesh whose ARMATURE modifier points at THIS armature.
    Meshes still bound to the original are silently left behind, which surfaces as
    an unweighted mesh in Unreal rather than an error here - so the bound meshes
    are logged.

    Must run LATE. In the animation path the retarget constraints use
    `subtarget = pbone.name` against the ORIGINAL armature, which still carries
    .L/.R; rename before the bake and no subtarget resolves and the animation
    comes out empty. Orientation, by contrast, is order independent - the roll
    tables are keyed on the _l form and normalizeBoneName leaves it alone.

    Returns the number of bones renamed, or None if it refused."""
    if bpy.context.object is not None and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')

    bones = armature_clone.data.bones
    pairs = [(b.name, _unreal_bone_name(b.name)) for b in bones]
    pairs = [(old, new) for old, new in pairs if old != new]
    if not pairs:
        print("rename_bones_for_unreal: nothing to rename on {}".format(armature_clone.name))
        return 0

    # A collision would make Blender uniquify to calf_l.001, which Unreal will not
    # recognise. Refuse the whole rename rather than half-apply it.
    keeping = set(b.name for b in bones) - set(old for old, new in pairs)
    clashes = []
    seen = set()
    for old, new in pairs:
        if new in keeping or new in seen:
            clashes.append("{} -> {}".format(old, new))
        seen.add(new)
    if clashes:
        message = ("Bone name collision renaming for Unreal, nothing renamed: "
                   + ", ".join(clashes))
        print("rename_bones_for_unreal: " + message)
        ShowMessageBox(message, "Export", 'ERROR')
        return None

    bound = [ob.name for ob in bpy.data.objects
             if ob.type == 'MESH' and any(m.type == 'ARMATURE' and m.object == armature_clone
                                          for m in ob.modifiers)]

    for old, new in pairs:
        bones[old].name = new

    print("rename_bones_for_unreal: renamed {} bones on {}; vertex groups followed "
          "on {} bound mesh(es): {}".format(len(pairs), armature_clone.name,
                                            len(bound), bound))
    if not bound:
        print("  WARNING: no mesh is bound to this armature - if a mesh is being "
              "exported alongside it, its vertex groups still carry the .L/.R names")
    return len(pairs)


def orient_bones_for_unreal(armature_clone, armature_object):
    """Put the clone into UE5 orientation, picking the route from the rig's stamp.

    A BlenderPerfect rig (anything the Manny builder produced) goes through the
    generated per-bone constants. Anything else - the old VXMod skeleton - falls
    through to the legacy hand-tuned pass so existing exports keep working."""
    state = armature_clone.data.get(ORIENTATION_PROP)
    if state == ORIENTATION_BP:
        return orient_bones_for_unreal_from_blender_perfect(armature_clone)
    if state == ORIENTATION_UE5:
        print("orient_bones_for_unreal: already in UE5 orientation, skipping")
        return
    if state == ORIENTATION_DAZ:
        # The roll comparison toggle was left switched off. Applying the
        # BlenderPerfect export constants to Daz rolls would mis-orient every
        # joint, and the legacy pass is not for this rig either.
        message = ("Armature rolls are toggled back to Diffeomorphic. Switch the "
                   "roll toggle back to PERFECT before exporting.")
        print("orient_bones_for_unreal: " + message)
        ShowMessageBox(message, "Export", 'ERROR')
        return
    print("orient_bones_for_unreal: no '{}' stamp (got {!r}) - using the legacy pass"
          .format(ORIENTATION_PROP, state))
    reorient_bones_for_unreal(armature_clone, armature_object)


def blender_perfect_to_blender_friendly(armature_clone):
    """Step 1 of 2: BlenderPerfect -> BlenderFriendly. Roll only.

    BlenderFriendly is the orientation defined by the property that a single
    +/-90 about each bone's own Z axis lands on UE5. Getting there from
    BlenderPerfect is a pure roll change, so heads, tails and directions are
    untouched and nothing here can move a bone.

    Returns the number of bones re-rolled."""
    from .g3f import manny_blender_perfect_generated as manny_bp

    _enter_edit_on(armature_clone)
    rolled = 0
    untouched = []
    for ebone in armature_clone.data.edit_bones:
        delta = manny_bp.getBpToBfRollDelta(ebone.name)
        if delta is None:
            untouched.append(ebone.name)
            continue
        ebone.roll -= math.radians(delta)
        rolled += 1
    bpy.ops.object.mode_set(mode='OBJECT')

    print("  BP -> BF: {} bones re-rolled, {} left alone".format(rolled, len(untouched)))
    if untouched:
        print("     no Manny counterpart: {}".format(sorted(untouched)))
    return rolled


def blender_friendly_to_ue5(armature_clone):
    """Step 2 of 2: BlenderFriendly -> UE5.

    +/-90 about each bone's own Z axis, the sign taken from flippedBones - the
    bones Epic runs 180 deg from the naive mirror. This is the step the whole
    convention is built around, and it is where the left/right asymmetry lives.

    Post-multiplying the edit bone matrix keeps the head exactly in place and does
    not depend on the pivot setting or on a 3D view being present, unlike the
    legacy transform.rotate approach.

    Returns (rotated, flipped_count)."""
    from .g3f import manny_blender_perfect_generated as manny_bp

    _enter_edit_on(armature_clone)
    ebones = armature_clone.data.edit_bones

    # A connected child is glued to its parent's tail, so rotating the parent
    # would drag the child's head with it. Break that link first - the heads are
    # already in the right place.
    disconnected = 0
    for ebone in ebones:
        if ebone.use_connect:
            ebone.use_connect = False
            disconnected += 1

    rotated = 0
    flipped_count = 0
    untouched = []
    for ebone in ebones:
        if manny_bp.getBpToBfRollDelta(ebone.name) is None:
            untouched.append(ebone.name)
            continue
        is_flipped = manny_bp.isFlipped(ebone.name)
        angle = -90.0 if is_flipped else 90.0
        ebone.matrix = ebone.matrix * Matrix.Rotation(math.radians(angle), 4, 'Z')
        rotated += 1
        flipped_count += 1 if is_flipped else 0
    bpy.ops.object.mode_set(mode='OBJECT')

    print("  BF -> UE5: {} bones rotated ({} at -90 from flippedBones, {} at +90), "
          "{} disconnected, {} left alone"
          .format(rotated, flipped_count, rotated - flipped_count,
                  disconnected, len(untouched)))
    return rotated, flipped_count


def _enter_edit_on(armature_clone):
    """Make the clone active before entering edit mode.

    bpy.ops.object.mode_set acts on the ACTIVE object, so without this a caller
    with something else selected silently edits an empty edit_bones collection
    and every orientation step becomes a no-op that still reports success. The
    export path happens to leave the clone active, but relying on that is how a
    whole conversion goes missing without an error."""
    scene = bpy.context.scene
    if scene.objects.active is not armature_clone:
        if scene.objects.active is not None and scene.objects.active.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        scene.objects.active = armature_clone
    bpy.ops.object.mode_set(mode='EDIT', toggle=False)


def _find_bone(ebones, base, side):
    """Look a bone up under either naming convention, .L/.R or _l/_r."""
    for name in (base + side, base + ('_l' if side == '.L' else '_r')):
        if name in ebones:
            return ebones[name]
    return None


def _find_either_spelling(ebones, name):
    """Find a bone given either spelling of its name, or None.

    The helper table is written in UE form (ik_foot_l) but the rig is still on
    Blender names (.L/.R) until rename_bones_for_unreal runs. Checking only one
    spelling is how you end up creating ik_foot_l next to an existing ik_foot.L.
    """
    if name in ebones:
        return ebones[name]
    if len(name) > 2 and name[-2] == '_' and name[-1] in ('l', 'r'):
        other = name[:-2] + '.' + name[-1].upper()
        if other in ebones:
            return ebones[other]
    return None


def reaim_feet_for_unreal(armature_clone):
    """Rebuild the foot and ball frames from the rig's own geometry.

    This is the one bone the +/-90 step cannot reach. In Blender the foot points
    at its child, the ball - the natural thing to build. Manny's does not: it
    follows the calf, sitting 64.38 deg away from the ball, with its own direction
    lying along the horizontal foot->ball line instead. A rotation about the
    bone's own Z axis can change a bone's roll but never where it points, so this
    has to set the frame outright.

    Measured from the UE5 reference, per side:

        Y (the bone's direction)  the horizontal foot->ball line,
                                  negated on the left
        X                         world DOWN on the left, world UP on the right
        Z = X x Y                 falls out pointing to the body's right on both

    and the ball is that same frame turned 90 deg about the shared Z, which the
    reference confirms on both sides.

    Heads are untouched, so this is safe to run after the two orientation steps -
    it reads only foot.head and ball.head, which neither of them moves. Epic's
    reason for the convention is foot roll and IK: pinning the frame to the toe
    line and the ground plane is what makes a foot behave on stairs and uneven
    ground.
    """
    _enter_edit_on(armature_clone)
    ebones = armature_clone.data.edit_bones

    done = []
    for side, vertical in (('.L', -1.0), ('.R', 1.0)):
        foot = _find_bone(ebones, 'foot', side)
        ball = _find_bone(ebones, 'ball', side)
        if foot is None or ball is None:
            print("  foot re-aim: no foot/ball pair for {} - skipped".format(side))
            continue

        toe = ball.head - foot.head
        flat = Vector((toe.x, toe.y, 0.0))
        if flat.length < 1e-6:
            print("  foot re-aim: {} foot and ball are vertically aligned, "
                  "no toe direction - skipped".format(side))
            continue
        flat.normalize()

        y = flat * (-1.0 if side == '.L' else 1.0)
        x = Vector((0.0, 0.0, vertical))
        z = x.cross(y).normalized()

        def frame(head):
            return Matrix(((x.x, y.x, z.x, head.x),
                           (x.y, y.y, z.y, head.y),
                           (x.z, y.z, z.z, head.z),
                           (0.0, 0.0, 0.0, 1.0)))

        foot_head = foot.head.copy()
        ball_head = ball.head.copy()
        foot.matrix = frame(foot_head)
        ball_frame = frame(ball_head) * Matrix.Rotation(math.radians(90), 4, 'Z')
        ball_frame.translation = ball_head
        ball.matrix = ball_frame
        done.append(side)

    bpy.ops.object.mode_set(mode='OBJECT')
    print("  foot re-aim: rebuilt foot and ball frames for {}".format(done or "nothing"))
    return done


def apply_ue5_roll_correction(armature_clone):
    """Add 180 deg to every bone's roll. REQUIRED for a correct export.

    Runs LAST and over EVERY bone, and both of those matter:

      * after reaim_feet_for_unreal, so the rebuilt foot and ball frames get it
        too - they are absolute, so anything applied before is discarded;
      * over the Daz extras (toes, breasts, eyes, teeth, tongue) as well, which
        skip the two conversion steps entirely because they have no Manny
        counterpart. Whether a bare 180 is *right* for them is unknowable - there
        is no reference to compare against - but it is what shipped and was
        confirmed, so it stays until something says otherwise.

    That is why this cannot be folded into blender_friendly_to_ue5: doing so
    would quietly drop it from the feet and from all 41 extras.

    Not a fudge, despite looking like one. The ArmatureUE5 reference that this
    whole convention was derived from is reconstructed by io_unreal_dump_importer
    180 deg ROLLED from the state the FBX writer needs: the bones look right in
    the viewport, but exporting them lands every bone flipped in Unreal. Measuring
    the reconstruction against Manny's real rotators in bone_data.csv shows it
    directly - UE red comes out as MINUS Blender X and UE green as MINUS Blender
    Y, which is exactly a 180 about each bone's own axis.
    (roll += 180 is X -> -X, Z -> -Z, direction unchanged.)
    Confirmed against a real Unreal import.

    The legacy reorient_bones_for_unreal ended with the same `roll += radians(180)`
    and was silently correcting for this all along.

    Note the algebra: Rz(sigma*90) * Ry(180) == Ry(180) * Rz(-sigma*90). Applying
    the 180 at the end is identical to inverting the flippedBones sign and
    applying it first - which is why "isFlipped looks backwards" is a reasonable
    reading of the same symptom."""
    _enter_edit_on(armature_clone)
    count = 0
    for ebone in armature_clone.data.edit_bones:
        ebone.roll += math.radians(180.0)
        count += 1
    bpy.ops.object.mode_set(mode='OBJECT')
    print("  UE5 roll correction (+180) applied to {} bones".format(count))
    return count


def add_missing_unreal_bones(armature_clone):
    """Add the Unreal helper bones the Daz rig never had.

    Manny carries ten bones the builder does not create - the IK markers plus
    interaction and center_of_mass. They deform nothing, but Unreal's retarget and
    IK setups expect them.

    Each is placed at the WORLD position of the bone it shadows, which is what
    Epic does. That matters because the hierarchy does not follow the geometry:
    ik_foot_l hangs off ik_foot_root, which sits at the origin, so its position
    cannot be inherited from the foot. Blender edit-bone heads are already in
    armature space, so copying foot.head across gives the world placement whatever
    the parenting is.

    See unreal_helper_bones in difeomorphic_workflow_dictionaries_bones for the
    table and the measurements behind it. `root` is not in it - the FBX exporter
    synthesises the root from the armature object, so adding one would give two.

    Anything already present is left alone, so this is safe to re-run and safe on
    a rig that does have them.
    """
    from .g3f import difeomorphic_workflow_dictionaries_bones as dict_bones

    _enter_edit_on(armature_clone)
    ebones = armature_clone.data.edit_bones

    # Fallback length for a helper with nothing to copy, scaled off the rig so it
    # stays visible whatever size the figure is.
    heights = [eb.head.z for eb in ebones] or [0.0]
    fallback = ((max(heights) - min(heights))
                * dict_bones.unreal_helper_bone_length_fraction) or 0.05

    added = []
    skipped = []
    for name, parent_name, shadow_name in dict_bones.unreal_helper_bones:
        existing = _find_either_spelling(ebones, name)
        if existing is not None:
            skipped.append(existing.name)
            continue

        shadow = None
        if shadow_name is not None:
            base = shadow_name[:-2] if shadow_name[-2:] in ('.L', '.R') else shadow_name
            side = shadow_name[-2:] if shadow_name[-2:] in ('.L', '.R') else None
            shadow = _find_bone(ebones, base, side) if side else ebones.get(base)
            if shadow is None:
                print("  helper bones: '{}' shadows '{}' which is not in the rig "
                      "- skipped".format(name, shadow_name))
                continue

        eb = ebones.new(name)
        if shadow is not None:
            eb.head = shadow.head.copy()
            eb.tail = eb.head + Vector((0.0, shadow.length or fallback, 0.0))
            eb.matrix = shadow.matrix.copy()
        else:
            eb.head = Vector((0.0, 0.0, 0.0))
            eb.tail = Vector((0.0, fallback, 0.0))

        # The FBX export runs with use_armature_deform_only=True, which drops any
        # bone whose use_deform is off. These have no vertex groups but still have
        # to reach Unreal, so they must be marked deforming or they vanish.
        eb.use_deform = True
        eb.use_connect = False
        parent = _find_either_spelling(ebones, parent_name)
        if parent is not None:
            eb.parent = parent
        added.append(name)

    bpy.ops.object.mode_set(mode='OBJECT')
    print("  helper bones: added {} {}{}".format(
        len(added), added, ", already present: %s" % skipped if skipped else ""))
    return added


# Copied straight across when a bone is rebuilt. Anything missing on this
# Blender build is skipped rather than raising, so the list can stay generous.
_EDIT_BONE_CARRIED_ATTRS = (
    "use_deform", "use_inherit_rotation", "use_inherit_scale", "use_local_location",
    "use_envelope_multiply", "envelope_distance", "envelope_weight",
    "head_radius", "tail_radius",
    "bbone_segments", "bbone_in", "bbone_out", "bbone_x", "bbone_z",
    "hide", "lock", "show_wire",
)


def _sibling_rank_table():
    """The export order table, normalised to the Unreal spelling of every name."""
    from .g3f import difeomorphic_workflow_dictionaries_bones as dict_bones
    table = {}
    for parent, wanted in dict_bones.export_bone_sibling_order.items():
        key = _unreal_bone_name(parent) if parent else ""
        table[key] = dict((_unreal_bone_name(n), i) for i, n in enumerate(wanted))
    return table


def sort_bones_for_export(armature_clone):
    """Reorder the clone's bones so Unreal's skeleton tree matches Epic's layout.

    This changes NOTHING about the rig - not a name, not a parent, not a
    transform. It only changes the order the bones sit in, which is the order
    they are written to the FBX and therefore the order Unreal indexes them.

    Why it takes a full rebuild: `armature.data.bones` is a depth first walk of
    the bone tree, and a parent's children come out in the order they sit in
    `edit_bones`. Blender has no API to move a bone within that collection -
    `ED_armature_from_edit` appends bones to their parent in edit_bones order and
    nothing else influences it - so the only way to reorder is to snapshot every
    bone, delete the lot, and create them again in the order wanted. Everything
    an EditBone carries is copied across, custom properties included.

    Two consequences of the rebuild, both fine where it is called from:
      * pose bone constraints on the clone do not survive it, so it must run
        before anything constrains the clone (the animation path) rather than
        after;
      * vertex groups are matched to bones by NAME, so the bound meshes are
        untouched - which is also why this is safe to run after
        rename_bones_for_unreal.

    Returns True if the order changed, False if it was already right.
    """
    ranks = _sibling_rank_table()

    _enter_edit_on(armature_clone)
    ebones = armature_clone.data.edit_bones

    snapshot = OrderedDict()
    for eb in ebones:
        rec = {
            "name": eb.name,
            "parent": eb.parent.name if eb.parent is not None else None,
            "head": eb.head.copy(),
            "tail": eb.tail.copy(),
            "roll": eb.roll,
            "use_connect": eb.use_connect,
            "layers": tuple(eb.layers),
            "props": dict((k, eb[k]) for k in eb.keys()),
        }
        for attr in _EDIT_BONE_CARRIED_ATTRS:
            if hasattr(eb, attr):
                rec[attr] = getattr(eb, attr)
        snapshot[eb.name] = rec

    if not snapshot:
        bpy.ops.object.mode_set(mode='OBJECT')
        print("sort_bones_for_export: {} has no bones".format(armature_clone.name))
        return False

    children = OrderedDict()
    for rec in snapshot.values():
        children.setdefault(rec["parent"], []).append(rec["name"])

    def ordered_children(parent_name):
        names = children.get(parent_name, [])
        key = _unreal_bone_name(parent_name) if parent_name else ""
        rank = ranks.get(key)
        if not rank:
            return names
        # sorted() is stable, so unlisted bones keep the order they already had
        # and simply follow the pinned ones.
        return sorted(names, key=lambda n: rank.get(_unreal_bone_name(n), len(rank)))

    flat = []
    stack = list(reversed(ordered_children(None)))
    while stack:
        name = stack.pop()
        flat.append(name)
        stack.extend(reversed(ordered_children(name)))

    # A bone unreachable from a root would mean a parent cycle, which Blender
    # does not allow - but losing bones silently is not an acceptable failure
    # mode for an exporter, so anything left over is appended rather than dropped.
    missed = [n for n in snapshot if n not in set(flat)]
    if missed:
        print("  WARNING: {} bone(s) not reachable from a root, appended as-is: {}"
              .format(len(missed), missed))
        flat.extend(missed)

    if flat == list(snapshot.keys()):
        bpy.ops.object.mode_set(mode='OBJECT')
        print("sort_bones_for_export: {} is already in export order"
              .format(armature_clone.name))
        return False

    # Reverse of the depth first order removes every child before its parent.
    for name in reversed(flat):
        ebones.remove(ebones[name])

    for name in flat:
        rec = snapshot[name]
        eb = ebones.new(name)
        if eb.name != name:
            print("  WARNING: Blender renamed '{}' to '{}' while rebuilding"
                  .format(name, eb.name))
        eb.head = rec["head"]
        eb.tail = rec["tail"]
        eb.roll = rec["roll"]
        eb.layers = rec["layers"]
        for attr in _EDIT_BONE_CARRIED_ATTRS:
            if attr in rec:
                setattr(eb, attr, rec[attr])
        for key, value in rec["props"].items():
            eb[key] = value

    # Parenting in a second pass, so a child never looks for a parent that has
    # not been created yet. use_connect goes last of all: setting it snaps the
    # head onto the parent's tail, so the parent has to be in place first.
    for name in flat:
        rec = snapshot[name]
        if rec["parent"] is not None:
            ebones[name].parent = ebones[rec["parent"]]
    for name in flat:
        rec = snapshot[name]
        if rec["use_connect"]:
            ebones[name].use_connect = True

    bpy.ops.object.mode_set(mode='OBJECT')

    top = [b.name for b in armature_clone.data.bones if b.parent is None]
    pelvis = _find_either_spelling(armature_clone.data.bones, "pelvis")
    print("sort_bones_for_export: reordered {} bones on {}"
          .format(len(flat), armature_clone.name))
    print("  top level: {}".format(top))
    if pelvis is not None:
        print("  under {}: {}".format(pelvis.name, [c.name for c in pelvis.children]))
    return True


def orient_bones_for_unreal_from_blender_perfect(armature_clone):
    """ArmatureBlenderPerfect -> the UE5 export orientation, via BlenderFriendly.

    Four passes, in this order, and the order is load bearing:

        1  BP -> BF                 roll only
        2  BF -> UE5                +/-90 about each bone's own Z
        3  foot and ball re-aim     absolute, discards what 1 and 2 did to them
        4  UE5 roll correction      +180 over EVERY bone, including the feet and
                                    the Daz extras that steps 1 and 2 skip
        5  helper bones             the IK markers Manny has and the Daz rig does
                                    not, copied off the finished deform bones

    Steps 1 and 2 do compose into a single constant per bone, and an earlier
    version shipped that table. It was removed: 89 stored matrices holding 4
    distinct values, read by nothing, while the stepped form is what anyone
    debugging a bad rig actually wants to inspect. Step 4 cannot be folded into
    step 2 at all - see apply_ue5_roll_correction.

    IMPORTANT: steps 1-3 land on ArmatureUE5 as reconstructed in Blender, which is
    NOT the state that exports correctly - it sits 180 deg rolled from it. Step 4
    closes that gap. Anything in this module saying a step "lands on ArmatureUE5"
    means the reconstruction, not Unreal.
    """
    print("orient_bones_for_unreal_from_blender_perfect: {}".format(armature_clone.name))
    blender_perfect_to_blender_friendly(armature_clone)
    blender_friendly_to_ue5(armature_clone)
    # Last, and absolute: it overwrites whatever the two steps did to the feet.
    reaim_feet_for_unreal(armature_clone)
    # After the feet, so the correction covers them too - the legacy pass was
    # the very last thing that touched a roll, and that ordering is load bearing.
    apply_ue5_roll_correction(armature_clone)
    # Last, so the markers copy bones that are already in their final orientation
    # rather than picking up a correction meant for someone else.
    add_missing_unreal_bones(armature_clone)
    armature_clone.data[ORIENTATION_PROP] = ORIENTATION_UE5


def reorient_bones_for_unreal(armature_clone, armature_object):
    # LEGACY - for the old VXMod skeleton only. Hand tuned per bone and per bone
    # group against a rig that predates ArmatureBlenderPerfect, and it goes
    # straight to something approximating ArmatureUE5. New rigs take
    # orient_bones_for_unreal_from_blender_perfect instead; this is kept so
    # existing old-skeleton exports keep working and can be removed once nothing
    # depends on it.
    #
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
    for ebone in ebones:
        bpy.ops.armature.select_all(action='DESELECT')  # Deselect all bones first
        ebone.select = True
        ebone.select_head = True  # Select both head and tail
        ebone.select_tail = True
        # Set the 3D cursor to the pelvis bone's head (rotation pivot point)
        bpy.context.scene.cursor_location = armature_object.matrix_world * ebone.head # 2.79 uses cursor_location
        # Rotate the selected bone by +/-90 degrees along the z-axis in NORMAL space
        if ebone.get("isFlipped") == True:
            bpy.ops.transform.rotate(value=math.radians(-90), axis=(0, 0, 1), constraint_axis=( False, False, True), constraint_orientation='NORMAL')
        else:
            bpy.ops.transform.rotate(value=math.radians(90), axis=(0, 0, 1), constraint_axis=( False, False, True), constraint_orientation='NORMAL')
        ebone.roll +=math.radians(180)
        # scene.update() removed — single update after all bone loops
    # first lets do the right bones, as those should follow the bone orientation for the right leg
    # Update the view
    bpy.context.scene.update()
    #
    #
    #we are done with making the bones friendly, lets go back to object mode to also transform the armature as a whole
    bpy.ops.object.mode_set(mode='OBJECT')
def export_to_unreal_v2(params) : #exportfolderpath,
    #exportfolderpath,exportFilename, includeGeograftsOnExportUnreal, cleanTempMeshesAfterExportUnreal, reorientBonesOnExportUnreal
    #
    obj = bpy.context.active_object
    if not obj or obj.type != 'MESH':
        ShowMessageBox("No mesh object selected for export.", "Error", 'ERROR')
        return None

    if obj.hide :
        ShowMessageBox("Object {} is not visible!".format(obj.name), "Error", 'ERROR')
        return None



    armature_modifier = next((mod for mod in obj.modifiers if mod.type == 'ARMATURE'), None)
    armature_object = armature_modifier.object if armature_modifier else None

    if armature_object is None:
        ShowMessageBox("Object {} has no armature!".format(obj.name), "Error", 'ERROR')
        return None    
    #    
    # lets make sure we are in object mode
    obj = bpy.context.active_object
    if obj is not None:
        if obj.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
    deselect_all_objects()
    #
    if params.cleanupTempMeshesMode =="BEFORE" or params.cleanupTempMeshesMode =="BOTH":
        vxasset_stripped = bpy.data.objects.get("vxasset_stripped")
        if vxasset_stripped is not None:
            vxasset_stripped.select=True
            bpy.context.scene.objects.active = vxasset_stripped
        #
        emptyLodGroup = bpy.data.objects.get("meshLodGroup")
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
    mergedMeshesName = obj.name
    obj.select = True
    bpy.context.scene.objects.active = obj
    #
    if not params.includeGeograftsOnExportUnreal:
        mergedMeshesName = obj.name
        pass
    else:
        if not geograft_data_available():
            ShowMessageBox("'Include Geografts' is checked, but the Difeomorphic addon (import_daz) is not enabled, so there is no geograft data", "Error", 'ERROR')
            return None
        #
        geograft_children = get_geograft_children(obj)
        if len(geograft_children)==0:
            ShowMessageBox("'Include Geografts' is checked, but there are no geograft_ children for the exported mesh", "Error", 'ERROR')
            return None
        else:
            for geograftObj in geograft_children:
                hiddenStatusGeografts[geograftObj.name] = geograftObj.hide
                if geograftObj.hide :
                    geograftObj.hide = False # we need to show it, otherwise can't merge using a hidden object
        geograft_refined = get_refined_geograft_names(geograft_children)
        mergedMeshesName = "_".join([obj.name] + geograft_refined)
    #
    print("mergedMeshesName : {}".format(mergedMeshesName))
    if (params.createSubdivMeshOnExportUnreal):    
        file_path = os.path.join(exportfolderpath,mergedMeshesName+"_matching_index_dict.json")
        if os.path.isfile(file_path) == False:
            ShowMessageBox("Missing subdiv matching file: {}_matching_index_dict.json, maybe try to build it first? ".format(mergedMeshesName), "Error", 'ERROR')    
            return None       
    print("$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$")
    deselect_all_objects()
    obj.select = True
    bpy.context.scene.objects.active = obj
    bpy.ops.object.duplicate(linked=False)
    vxasset = bpy.context.scene.objects.active
    vxasset.name = "vxasset"
    if params.includeGeograftsOnExportUnreal:
        #deselect_all_objects()       
        #
        #
        for geograftObj in geograft_children:
            deselect_all_objects()
            geograftObj.select = True
            bpy.context.scene.objects.active = geograftObj
            bpy.ops.object.duplicate(linked=False)
            geoClone = bpy.context.scene.objects.active
            geoClone.parent = vxasset
            anatomies.append(geoClone)
            geograftObj.hide = hiddenStatusGeografts[geograftObj.name] # we need to restore the hidden status
        #
        deselect_all_objects()
        #
        for geo in anatomies:
            geo.select = True
            bpy.context.scene.objects.active = geo        
        vxasset.select=True
        bpy.context.scene.objects.active = vxasset
        vxasset.select=True
        # merge operators live in diffeomorphic_merge_geografts.py (vxmod.merge_geografts*)
        merge_geografts_into_active()
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
    vxasset.select=True
    bpy.context.scene.objects.active = vxasset
    #
    # Clear modifiers
    bpy.ops.gmtt.object_strip_and_clean(mod=True)

    if not params.exportShapekeys:
        bpy.ops.gmtt.object_strip_and_clean(sk=True)
    #
    ob = bpy.context.scene.objects.active
    if (params.createSubdivMeshOnExportUnreal):
        print("Creating vxasset_hires!") 
        vxasset_hires = duplicate_object_by_name("vxasset","vxasset_hires")
        bpy.context.scene.objects.active = vxasset_hires
        if True==True:
            # Clear shapekeys + modifiers
            bpy.ops.gmtt.object_strip_and_clean(sk=True, mod=True)
            # Subdivide the mesh using the subdivide operator in Edit Mode
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.reveal()
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.subdivide(number_cuts=1)
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode="OBJECT")    
        print("Creating vxasset_stripped!") 
        #
        vxasset_stripped = duplicate_object_by_name("vxasset","vxasset_stripped")
        deselect_all_objects()
        vxasset_stripped.select=True
        bpy.context.scene.objects.active = vxasset_stripped
        print("strip_and_clean_selected_object!") 
        if False==False:
            bpy.ops.gmtt.object_strip_and_clean(vg=True, sk=True, mat=True, mod=True)
            print("strip_and_clean_selected_object! DOENE") 
        #
        #
        if False == False:
            print("Creating vxasset_stripped_subdiv!") 
            vxasset_stripped_subdiv = duplicate_object_by_name("vxasset_stripped","vxasset_stripped_subdiv")
            deselect_all_objects()
            vxasset_stripped_subdiv.select=True
            bpy.context.scene.objects.active = vxasset_stripped_subdiv
            bpy.ops.object.modifier_add(type='SUBSURF')
            subsurf_modifier = vxasset_stripped_subdiv.modifiers[-1] # get the last modifier (hence -1)
            subsurf_modifier.levels = 1  # Set the subdivision levels as needed
            # Apply the Subdivision Surface modifier
            bpy.ops.object.modifier_apply( modifier = subsurf_modifier.name )
            #    
            deselect_all_objects()
            print("vxasset, vxasset_hires , vxasset_stripped and vxasset_stripped_subdiv created!")
            #adjust_vertices_location_between_different_topology_meshes_using_lookup_dict (source_obj, target_obj)
            adjust_vertices_location_between_different_topology_meshes_using_lookup_dict(vxasset_stripped_subdiv, vxasset_hires)
            deselect_all_objects()
            #vxasset.select = True   
            #vxasset_stripped.select=True
            #vxasset_hires.select=True
            vxasset_stripped_subdiv.select=True
            bpy.context.scene.objects.active = vxasset_stripped_subdiv
            print("Removing vxasset_stripped_subdiv as we no longer need it")
            bpy.ops.object.delete(use_global=True)
        #
        #if (True == True):
        #    return   
        #vxasset.select = True        
        #bpy.context.scene.objects.active = vxasset
        #
        deselect_all_objects()
        #
        if not params.exportShapekeys:
            pass
        else :
            if vxasset.data.shape_keys is None:
                print("Source object has no shape keys!")
            else:
                sk_counter = len(vxasset.data.shape_keys.key_blocks)
                sk_names = [vxasset.data.shape_keys.key_blocks[i].name for i in range(1, sk_counter)]
                #
                cached = None
                cache_path = None
                if params.cacheShapekeys:
                    fingerprint = compute_basis_fingerprint(vxasset_stripped)
                    cache_path = os.path.join(exportfolderpath, mergedMeshesName + "_shapekeys_subdiv_cache.bin")
                    n_hires_verts = len(vxasset_hires.data.vertices)
                    cached = load_shapekey_subdiv_cache(cache_path, n_hires_verts, sk_names, fingerprint)
                #
                if cached is not None:
                    # FAST PATH: load from cache, skip all subsurf work
                    print("Using cached shape key data (skipping subdivision)")
                    for skname in sk_names:
                        print("Loading cached Shape Key - ", skname)
                        if not vxasset_hires.data.shape_keys:
                            vxasset_hires.shape_key_add(name="Basis")
                        new_sk = vxasset_hires.shape_key_add(name=skname)
                        new_sk.data.foreach_set("co", cached[skname])
                    vxasset_hires.data.update()
                else:
                    # SLOW PATH: subdivide each shape key and remap
                    for idx in range(1, sk_counter):  #range is 1 and not 0, because I dont want to transfer the Basis shapekey which comes first
                        vxasset.select = True
                        bpy.context.scene.objects.active = vxasset
                        vxasset.active_shape_key_index = idx
                        skname = vxasset.active_shape_key.name
                        print("Copying Shape Key - ", skname)
                        #
                        # Duplicate vxasset_stripped using data-level copy (no shape keys on it)
                        vxasset_chupacabra_morph = duplicate_object_data_level(vxasset_stripped, "chupacabramorph_" + skname)
                        #
                        # Read morphed vertex positions directly from vxasset's shape key data
                        # This replaces the expensive O(n^2) shape_key_transfer() proximity search
                        sk = vxasset.data.shape_keys.key_blocks[skname]
                        n = len(sk.data)
                        cos = [0.0] * (n * 3)
                        sk.data.foreach_get("co", cos)
                        # Write them directly onto chupacabra_morph's vertices
                        vxasset_chupacabra_morph.data.vertices.foreach_set("co", cos)
                        vxasset_chupacabra_morph.data.update()
                        #
                        # Add a Subdivision Surface modifier (data-level add, operator apply)
                        deselect_all_objects()
                        vxasset_chupacabra_morph.select = True
                        bpy.context.scene.objects.active = vxasset_chupacabra_morph
                        print("Apply subdiv... ")
                        subsurf_mod = vxasset_chupacabra_morph.modifiers.new(name="Subsurf", type='SUBSURF')
                        subsurf_mod.levels = 1
                        # Apply requires operator (no data-level apply in 2.79)
                        bpy.ops.object.modifier_apply(modifier=subsurf_mod.name)
                        deselect_all_objects()
                        #transfer vertex values from vxasset_chupacabra_morph into a new Shapekey on vxasset_hires using the lookup vertices list
                        copy_vertices_to_shape_key_between_different_topology_meshes_using_lookup_dict(vxasset_chupacabra_morph, vxasset_hires, skname)
                        #at last delete the chupacabra object (data-level to match data-level creation)
                        print("Deleting object: "+vxasset_chupacabra_morph.name)
                        delete_object_data_level(vxasset_chupacabra_morph)
                        print("Deleted object")
                    # Save cache for next export
                    if params.cacheShapekeys:
                        save_shapekey_subdiv_cache(cache_path, vxasset_hires, sk_names, fingerprint)
        #
        print("vxasset_chupacabra_morph (all) created!")
        # why do we need this actually?!?
        if (True == False):
            if ( operator_exists("export.shapekeys_to_json") ):
                print("export.shapekeys_to_json is available :)")
                deselect_all_objects()
                vxasset_hires.select=True
                bpy.context.scene.objects.active = vxasset_hires
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
    # Back to object mode BEFORE the conditional, not inside it. The transform_apply
    # calls further down need object mode, and with re-orientation switched off
    # nothing else would leave pose mode - transform_apply then fails its poll with
    # "context is incorrect". The animation exporter has always had this guard; this
    # path did not.
    bpy.ops.object.mode_set(mode='OBJECT')
    #
    if params.reorientBonesOnExportUnreal:
        orient_bones_for_unreal(armature_clone, armature_object)
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
    emptyLodGroup = bpy.data.objects.new( "meshLodGroup", None )
    emptyLodGroup["fbx_type"] = "LodGroup"
    #emptyLodGroup["lookupVertexIdTable"] = "some/path/on/computer"
    bpy.context.scene.objects.link( emptyLodGroup )
    emptyLodGroup.select=True
    bpy.context.scene.objects.active = emptyLodGroup
    emptyLodGroup.scale = scaleVector
    bpy.ops.object.transform_apply(scale = True)


    #add the armature modifier
    deselect_all_objects()
    if params.createSubdivMeshOnExportUnreal:
        vxasset_hires["lookupVertexIdTable"] = mergedMeshesName+"_vertex_mapping_list.json" #"some/custom/path/on/computer"
        vxasset_hires["isHiRes"] = True
        vxasset_hires.select=True
        bpy.context.scene.objects.active = vxasset_hires
        vxasset_hires.rotation_euler[0] = rotationOnXAxis
        bpy.ops.object.transform_apply(rotation=True)    
        vxasset_hires.scale = scaleVector
        bpy.ops.object.transform_apply(scale = True)    
        # Add the armature modifier
        bpy.ops.object.modifier_add(type='ARMATURE')
        armature_modifier = vxasset_hires.modifiers[-1]
        # Set the armature object for the modifier
        armature_modifier.object = armature_clone
        LODs.append(vxasset_hires)
    
    #add the armature modifier
    deselect_all_objects()
    vxasset["lookupVertexIdTable"] = ""
    vxasset["isHiRes"] = False
    vxasset.select=True
    bpy.context.scene.objects.active = vxasset
    vxasset.rotation_euler[0] = rotationOnXAxis
    #vxasset.rotation_euler[1] = rotationOnZAxis
    bpy.ops.object.transform_apply(rotation=True)   
    vxasset.scale = scaleVector
    bpy.ops.object.transform_apply(scale = True)      
    # Add the armature modifier
    bpy.ops.object.modifier_add(type='ARMATURE')
    armature_modifier = vxasset.modifiers[-1]
    # Set the armature object for the modifier
    armature_modifier.object = armature_clone
    LODs.append(vxasset)

    #the order in which we set the parent is important it seems, otherwise in Unreal it will appear in the wrong order
    for i,lod in enumerate(LODs):
        lod.name="mesh_LOD{}".format(i)
        lod.parent = emptyLodGroup
        bpy.context.scene.update()	
        #print(o.name, o.type, o.data)

    # #rename them
    # vxasset.name = "vxasset_LOD1"
    # vxasset_hires.name = "vxasset_LOD0"
    
    # vxasset_hires.parent = emptyLodGroup
    # bpy.context.scene.update()	
    # vxasset.parent = emptyLodGroup
    # bpy.context.scene.update()	
    #
    emptyLodGroup.parent = armature_clone

    fix_translation_orientation_scale_for_unreal(armature_clone)


    bpy.context.scene.unit_settings.system = 'METRIC'
    #bpy.context.scene.unit_settings.length_unit = 'CENTIMETERS'  # You can also set 'CENTIMETERS'
    bpy.context.scene.unit_settings.scale_length = 0.01

    # .L/.R -> _l/_r, last thing before the FBX is written. The LOD meshes had
    # their armature modifier retargeted to the clone above, so their vertex
    # groups get renamed along with the bones.
    rename_bones_for_unreal(armature_clone)

    # Pure reordering, no rig change - it only decides which bone Unreal lists
    # first under each parent. Must stay after the rename (the table is matched
    # on Unreal names either way, but the log reads as the FBX will) and after
    # every bone has been created, since it rebuilds the whole edit bone list.
    sort_bones_for_export(armature_clone)

    #fbx export:
    emptyLodGroup.select=True
    for i,lod in enumerate(LODs):
        lod.select=True
    armature_clone.select=True
    bpy.context.scene.objects.active = armature_clone
    export_params = {
    "filepath": os.path.join(exportfolderpath,"SKM_"+obj.name+".fbx"), # params.fbxFilename),#"SK_Belle.fbx"
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
    _notify_export_complete()
    #
    #
    deselect_all_objects()
    #
    if params.cleanupTempMeshesMode =="AFTER" or params.cleanupTempMeshesMode =="BOTH":
        #
        vxasset_stripped = bpy.data.objects.get("vxasset_stripped")
        if vxasset_stripped is not None:
            vxasset_stripped.select=True
            bpy.context.scene.objects.active = vxasset_stripped
        #
        vxasset_stripped_subdiv = bpy.data.objects.get("vxasset_stripped_subdiv")
        if vxasset_stripped_subdiv is not None:
            vxasset_stripped_subdiv.select=True
            bpy.context.scene.objects.active = vxasset_stripped_subdiv
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


def export_animation_to_unreal(params):
    scene = bpy.context.scene
    obj = bpy.context.active_object

    # --- Find armature (same pattern as export_to_unreal_v2) ---
    if not obj or obj.type != 'MESH':
        ShowMessageBox("No mesh object selected.", "Error", 'ERROR')
        return None
    if obj.hide:
        ShowMessageBox("Object {} is not visible!".format(obj.name), "Error", 'ERROR')
        return None
    armature_modifier = next((m for m in obj.modifiers if m.type == 'ARMATURE'), None)
    armature_object = armature_modifier.object if armature_modifier else None
    if armature_object is None:
        ShowMessageBox("No armature on object {}.".format(obj.name), "Error", 'ERROR')
        return None

    mesh_name = obj.name
    exportfolderpath = params.exportFolderPathUnreal

    # --- Duplicate armature only ---
    deselect_all_objects()
    armature_object.select = True
    scene.objects.active = armature_object
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.duplicate(linked=False)
    armature_clone = scene.objects.active
    armature_clone.name = armature_clone.name + "_clone"

    # --- Strip constraints from clone ---
    if bpy.context.object.mode != 'POSE':
        bpy.ops.object.mode_set(mode='POSE')
    for bone in armature_clone.pose.bones:
        while bone.constraints:
            bone.constraints.remove(bone.constraints[0])
    bpy.ops.object.mode_set(mode='OBJECT')

    # --- Bone reorientation ---
    if params.reorientBonesOnExportUnreal:
        orient_bones_for_unreal(armature_clone, armature_object)

    # --- Add Copy Transforms constraints for animation retargeting ---
    deselect_all_objects()
    armature_clone.select = True
    scene.objects.active = armature_clone
    bpy.ops.object.mode_set(mode='POSE')
    for pbone in armature_clone.pose.bones:
        c = pbone.constraints.new('COPY_TRANSFORMS')
        c.name = "_anim_retarget_tmp"
        c.target = armature_object
        c.subtarget = pbone.name
        c.target_space = 'WORLD'
        c.owner_space = 'LOCAL_WITH_PARENT'
    bpy.ops.object.mode_set(mode='OBJECT')

    # --- Bake animations (visual_keying converts world-space pose to new local space) ---
    deselect_all_objects()
    armature_clone.select = True
    scene.objects.active = armature_clone
    bpy.ops.object.mode_set(mode='POSE')
    bpy.ops.nla.bake(
        frame_start=scene.frame_start,
        frame_end=scene.frame_end,
        visual_keying=True,
        clear_constraints=True,
        use_current_action=True,
        bake_types={'POSE'},
    )
    bpy.ops.object.mode_set(mode='OBJECT')

    # --- Apply scale/transform for Unreal (same as export_to_unreal_v2) ---
    deselect_all_objects()
    armature_clone.select = True
    scene.objects.active = armature_clone
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    armature_clone.scale = Vector((100, 100, 100))
    bpy.ops.object.transform_apply(scale=True)
    armature_clone.name = 'root'

    # .L/.R -> _l/_r. Deliberately AFTER the bake: the retarget constraints above
    # resolve `subtarget` against the original armature, which still carries the
    # Blender names, so renaming any earlier would silently produce an empty
    # animation.
    rename_bones_for_unreal(armature_clone)

    # --- FBX Export ---
    bpy.context.scene.unit_settings.system = 'METRIC'
    bpy.context.scene.unit_settings.scale_length = 0.01

    deselect_all_objects()
    armature_clone.select = True
    scene.objects.active = armature_clone
    export_params = {
        "filepath": os.path.join(exportfolderpath, "ANIM_" + mesh_name + ".fbx"),
        "check_existing": False,
        "filter_glob": "*.fbx",
        "version": 'BIN7400',
        "use_selection": True,
        "global_scale": 1.0,
        "apply_unit_scale": True,
        "apply_scale_options": 'FBX_SCALE_NONE',
        "bake_space_transform": False,
        "object_types": {'ARMATURE'},
        "use_mesh_modifiers": False,
        "add_leaf_bones": False,
        "axis_forward": 'Y',
        "axis_up": 'Z',
        "primary_bone_axis": 'Y',
        "secondary_bone_axis": 'X',
        "use_armature_deform_only": True,
        "armature_nodetype": 'NULL',
        "bake_anim": True,
        "bake_anim_use_all_bones": True,
        "bake_anim_use_nla_strips": False,
        "bake_anim_use_all_actions": False,
        "bake_anim_force_startend_keying": True,
        "bake_anim_step": 1.0,
        "bake_anim_simplify_factor": 1.0,
        "use_anim": True,
        "use_default_take": True,
        "use_anim_optimize": False,
        "anim_optimize_precision": 6.0,
        "path_mode": 'AUTO',
        "embed_textures": False,
        "batch_mode": 'OFF',
        "use_metadata": True,
    }
    bpy.ops.export_scene.fbx(**export_params)

    bpy.context.scene.unit_settings.system = 'NONE'
    bpy.context.scene.unit_settings.scale_length = 1.0

    # --- Cleanup clone ---
    deselect_all_objects()
    armature_clone.select = True
    scene.objects.active = armature_clone
    bpy.ops.object.delete(use_global=True)

    _notify_export_complete()