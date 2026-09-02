# Geograft merging operators, cloned into io_vxmod_workflow.
#
# The three operators below used to live in the Diffeomorphic addon
# (import_daz/merge.py), where they had been added by hand. They are our code,
# so they belong in our addon rather than patched into somebody else's source:
# that keeps import_daz pristine (it has its own maintainers), survives
# swapping in a clean copy of it, and keeps this code editable by us. They now
# live here under the vxmod.* namespace:
#
#   vxmod.merge_geografts_nondestructive_bmesh  (fast bmesh version)
#   vxmod.merge_geografts_nondestructive        (safe version)
#   vxmod.merge_geografts_fast                  (destructive, deletes masked edges)
#
# daz.merge_geografts is deliberately NOT cloned here: that operator is
# Diffeomorphic's own code and ships with their addon, so merge_geografts_into_active()
# simply calls it as the last fallback.
#
# The merge code is derived from Diffeomorphic
# (Copyright (c) 2016-2020, Thomas Larsson - BSD 2-clause license), see the
# license header of import_daz/merge.py.
#
# Diffeomorphic is still required to *import* the geografts: the mesh
# properties DazGraftGroup / DazMaskGroup / DazVertexCount and the object
# property DazScale are registered by import_daz and are read here. What is no
# longer required is a patched import_daz/merge.py.
#
# Helper functions that used to be imported from import_daz (getSceneObjects,
# getSelected, setSelected, activateObject, getUvTextures, updateDrivers,
# replaceNodeNames, the shape key driver helpers and the MaterialMerger mixin)
# are reimplemented at the top of this file for Blender 2.79 only.


import bpy
import bmesh
from collections import OrderedDict


#-------------------------------------------------------------
#   Blender 2.79 helpers (replacing import_daz.utils)
#-------------------------------------------------------------

def getSceneObjects(context):
    return context.scene.objects


def getSelected(ob):
    return ob.select


def setSelected(ob, value):
    ob.select = value


def getUvTextures(me):
    return me.uv_textures


def activateObject(context, ob):
    try:
        if context.object:
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        ob.select = True
    except RuntimeError:
        print("Could not activate", ob)
    context.scene.objects.active = ob


def updateDrivers(ob):
    if ob and ob.animation_data:
        for fcu in ob.animation_data.drivers:
            expression = str(fcu.driver.expression)
            fcu.driver.expression = expression


#-------------------------------------------------------------
#   Shape key driver helpers (replacing import_daz.driver)
#-------------------------------------------------------------

def getRnaDriver(rna, path, type):
    if rna and rna.animation_data:
        for fcu in rna.animation_data.drivers:
            if path == fcu.data_path:
                if not type:
                    return fcu
                for var in fcu.driver.variables:
                    if var.type == type:
                        return fcu
    return None


def getShapekeyDriver(skeys, sname):
    return getRnaDriver(skeys, 'key_blocks["%s"].value' % (sname), None)


def getShapekeyDrivers(ob, drivers={}):
    if (ob.data.shape_keys is None or
        ob.data.shape_keys.animation_data is None):
        return drivers

    for fcu in ob.data.shape_keys.animation_data.drivers:
        words = fcu.data_path.split('"')
        if (words[0] == "key_blocks[" and
            len(words) == 3 and
            words[2] == "].value"):
            drivers[words[1]] = fcu

    return drivers


def copyDriver(fcu1, rna2, id=None):
    channel = fcu1.data_path.rsplit(".",2)[-1]
    if channel == "value":
        idx = -1
    else:
        idx = fcu1.array_index
    words = fcu1.data_path.split('"')
    if (words[0] == "pose.bones[" and
        hasattr(rna2, "pose")):
        rna2 = rna2.pose.bones[words[1]]
    fcu2 = rna2.driver_add(channel, idx)
    fcu2.driver.type = fcu1.driver.type
    if hasattr(fcu1.driver, "use_self"):
        fcu2.driver.use_self = fcu1.driver.use_self
    fcu2.driver.expression = fcu1.driver.expression
    for var1 in fcu1.driver.variables:
        var2 = fcu2.driver.variables.new()
        var2.type = var1.type
        var2.name = var1.name
        trg1 = var1.targets[0]
        trg2 = var2.targets[0]
        if id:
            trg2.id = id
        else:
            trg2.id = trg1.id
        trg2.bone_target = trg1.bone_target
        trg2.data_path = trg1.data_path
        trg2.transform_type = trg1.transform_type
        trg2.transform_space = trg1.transform_space
    return fcu2


def copyShapeKeyDrivers(ob, drivers):
    skeys = ob.data.shape_keys
    if skeys is None:
        return
    for sname,fcu in drivers.items():
        if (getShapekeyDriver(skeys, sname) or
            sname not in skeys.key_blocks.keys()):
            continue
        skey = skeys.key_blocks[sname]
        copyDriver(fcu, skey)


#-------------------------------------------------------------
#   Material helpers (replacing import_daz.material.MaterialMerger)
#-------------------------------------------------------------

class MaterialMerger:

    def mergeMaterials(self, ob):
        if ob.type != 'MESH':
            return

        self.matlist = []
        self.assoc = {}
        self.reindex = {}
        m = 0
        reduced = False
        for n,mat in enumerate(ob.data.materials):
            if self.keepMaterial(n, mat, ob):
                self.matlist.append(mat)
                self.reindex[n] = self.assoc[mat.name] = m
                m += 1
            else:
                reduced = True
        if reduced:
            for f in ob.data.polygons:
                f.material_index = self.reindex[f.material_index]
            for n,mat in enumerate(self.matlist):
                ob.data.materials[n] = mat
            for n in range(len(self.matlist), len(ob.data.materials)):
                ob.data.materials.pop()


def replaceNodeNames(mat, oldname, newname):
    texco = None
    for node in mat.node_tree.nodes:
        if node.type == 'TEX_COORD':
            texco = node
            break

    uvmaps = []
    for node in mat.node_tree.nodes:
        if isinstance(node, bpy.types.ShaderNodeUVMap):
            if node.uv_map == oldname:
                node.uv_map = newname
                uvmaps.append(node)
        elif isinstance(node, bpy.types.ShaderNodeAttribute):
            if node.attribute_name == oldname:
                node.attribute_name = newname
        elif isinstance(node, bpy.types.ShaderNodeNormalMap):
            if node.uv_map == oldname:
                node.uv_map = newname

    if texco and uvmaps:
        fromsocket = texco.outputs["UV"]
        tosockets = []
        for link in mat.node_tree.links:
            if link.from_node in uvmaps:
                tosockets.append(link.to_socket)
        for tosocket in tosockets:
            mat.node_tree.links.new(fromsocket, tosocket)

    for node in uvmaps:
        mat.node_tree.nodes.remove(node)


#-------------------------------------------------------------
#   Operator base classes (replacing import_daz.error)
#-------------------------------------------------------------

class GeograftError(Exception):
    """Raised when the selection is not a valid geograft/body combination."""
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class IsMesh:
    @classmethod
    def poll(self, context):
        return (context.object and context.object.type == 'MESH')


class GeograftOperator:
    """Mirrors import_daz's DazOperator: force OBJECT mode around run(),
    restore the original mode afterwards, report errors to the user.

    This is a plain mixin, not a bpy.types.Operator subclass, so that
    bpy.utils.register_module() in __init__.py does not try to register it."""

    def execute(self, context):
        self.prequel(context)
        try:
            self.run(context)
        except GeograftError as err:
            print("Geograft merge failed: %s" % err.value)
            self.report({'ERROR'}, err.value)
            return {'CANCELLED'}
        finally:
            self.sequel(context)
        return {'FINISHED'}

    def prequel(self, context):
        self.mode = None
        if context.object:
            self.mode = context.object.mode
            bpy.ops.object.mode_set(mode='OBJECT')

    def sequel(self, context):
        if self.mode and context.object:
            bpy.ops.object.mode_set(mode=self.mode)


def getAnatomies(context, cob):
    """Collect the selected geografts (everything selected except the active
    body mesh that carries a DazGraftGroup) and sanity check them against the
    body vertex count."""
    if not hasattr(cob.data, "DazGraftGroup"):
        raise GeograftError("Diffeomorphic (import_daz) is not enabled, "
                            "geograft data is unavailable.")

    ncverts = len(cob.data.vertices)
    anatomies = []
    for aob in getSceneObjects(context):
        if (aob.type == 'MESH' and
            getSelected(aob) and
            aob != cob and
            aob.data.DazGraftGroup):
            anatomies.append(aob)

    if len(anatomies) < 1:
        raise GeograftError("At least two meshes must be selected.\n"
                            "Geografts selected and target active.")

    for aob in anatomies:
        if not geograftFitsBody(aob, cob):
            if cob.data.DazVertexCount == len(aob.data.vertices):
                msg = ("Meshes selected in wrong order.\n"
                       "Geografts selected and target active.   ")
            else:
                msg = ("Geograft %s fits mesh with %d vertices,      \n"
                       "but %s has %d vertices (base %d)." %
                       (aob.name, aob.data.DazVertexCount, cob.name, ncverts,
                        cob.data.DazVertexCount))
            raise GeograftError(msg)

    return anatomies


def geograftFitsBody(aob, cob):
    """Whether geograft `aob` can be merged into body `cob` right now.

    Two ways to fit:

    1. aob.DazVertexCount == the body's LIVE vertex count. This is Diffeomorphic's own
       rule. It covers a pristine body, and it also covers a STACKED geograft - one
       authored against the mesh that RESULTS from merging an earlier geograft.

    2. aob.DazVertexCount == the body's OWN DazVertexCount, once the body has grown past
       it. DazVertexCount is written once at import (geometry.py setHideInfoMesh) and is
       never updated by a merge, so a body that has already absorbed a geograft still
       carries the ORIGINAL figure's vertex count - which is exactly what a second
       base-level geograft was authored against.

    Rule 2 is what makes merging geografts ONE AT A TIME work. Under rule 1 alone the
    first merge grows the live count and every later base-level graft is rejected, even
    though its graft pairs are still perfectly valid.

    They stay valid because this merge is non-destructive: it only APPENDS the graft's
    vertices and then welds pairs, and the weld loop runs high-to-low
    (`reversed(dazGraftGroupAfterJoinDict.items())`) so the vertex each weld removes is
    always one of the appended ones. Base indices 0..N-1 are never renumbered - which the
    existing loop already depends on, since it keeps looking up body indices between
    welds.

    Rule 2 deliberately requires live > base, so it only ever relaxes the check on a body
    that has actually been merged into. On a pristine body rule 1 already applies, and a
    genuine mismatch is still rejected.
    """
    live_count = len(cob.data.vertices)
    if aob.data.DazVertexCount == live_count:
        return True

    base_count = cob.data.DazVertexCount
    if base_count and aob.data.DazVertexCount == base_count and live_count > base_count:
        print("geograftFitsBody: %s targets the base figure (%d verts); %s has already "
              "grown to %d. Accepting - base indices are preserved by the "
              "non-destructive merge." % (aob.name, base_count, cob.name, live_count))
        return True

    return False


class GeograftMergerBase(MaterialMerger):
    """Shared bits of the four merge operators."""

    def keepMaterial(self, mn, mat, ob):
        keep = self.mathits[mn]
        if not keep:
            print("Remove material %s" % mat.name)
        return keep


    def moveGraftVerts(self, aob, cob):
        """ This function moves all common geograft vertices to the location of the coresponding vertices.\n It also `fixes` the vertices in shared shapekey names"""
        for pair in aob.data.DazGraftGroup:
            aob.data.vertices[pair.a].co = cob.data.vertices[pair.b].co
        if cob.data.shape_keys and aob.data.shape_keys:
            for cskey in cob.data.shape_keys.key_blocks:
                if cskey.name in aob.data.shape_keys.key_blocks.keys():
                    askey = aob.data.shape_keys.key_blocks[cskey.name]
                    for pair in aob.data.DazGraftGroup:
                        askey.data[pair.a].co = cskey.data[pair.b].co


    def collectUvNames(self, context, cob, anatomies, drivers):
        """Move the graft verts into place, collect shape key drivers and
        remember which UV layers must survive the merge."""
        cname = self.getUvName(cob.data)
        anames = []

        # Keep extra UVs
        self.keepUv = []
        for ob in [cob] + anatomies:
            for uvtex in getUvTextures(ob.data):
                if not uvtex.active_render:
                    self.keepUv.append(uvtex.name)

        # Select graft group for each anatomy
        for aob in anatomies:
            activateObject(context, aob)
            self.moveGraftVerts(aob, cob) # moveGraftVerts: moves all common geograft vertices to the location of the coresponding vertices. It also `fixes` the vertices in shared shapekey names
            getShapekeyDrivers(aob, drivers)
            for uvtex in getUvTextures(aob.data):
                if uvtex.active_render:
                    anames.append(uvtex.name)
                else:
                    self.keepUv.append(uvtex.name)

        return cname, anames


    def finishMerge(self, cob, cname, anames, drivers):
        """Join the UV layers, rename UV references in the materials, drop the
        materials that no longer have faces and restore the shape key drivers."""
        self.joinUvTextures(cob.data)

        newname = self.getUvName(cob.data)
        for mat in cob.data.materials:
            if mat.use_nodes:
                replaceNodeNames(mat, cname, newname)
                for aname in anames:
                    replaceNodeNames(mat, aname, newname)

        # Remove unused materials
        self.mathits = dict([(mn,False) for mn in range(len(cob.data.materials))])
        for f in cob.data.polygons:
            self.mathits[f.material_index] = True
        self.mergeMaterials(cob)

        copyShapeKeyDrivers(cob, drivers)
        updateDrivers(cob)


    def collectRemovableEdges(self, cob, anatomies):
        """Find the body edges that are covered by the geograft and are not
        needed to keep the surrounding faces intact.

        Returns (preservableVertexIndices, removableEdgeIndices)."""
        preservableVertexIndices = []
        removableEdgeIndices = []
        for aob in anatomies:

            # those are the faces on geograft that daz is supposed to mask/hide/remove when the geograft is applied
            # all faces !!! included in the geograft boundaries/replaceable faces also the ones to be removed
            # but this is a complicated problem, if we delete the edges a bit later, it also shifts the faces count, so maybe we can't delete them?!? maybe later?!?
            maskedFaceIndices = [ item.a for item in aob.data.DazMaskGroup ]

            # but from those faces, we are going to get the vertices that makes them
            # all vertices !!! included in the geograft boundaries/replaceable vertices also the ones to be removed
            maskedVertexIndices = []
            for findex in maskedFaceIndices:
                vIndexArray = [cob.data.polygons[findex].vertices[i] for i in range(len(cob.data.polygons[findex].vertices))]  #there can be faces made from 3 or 4 vertices
                maskedVertexIndices.extend(vIndexArray)

            # list of vertices that are merged in the body
            mergingBodyVerticesList=[]
            for item in aob.data.DazGraftGroup:
                mergingBodyVerticesList.append(item.b)

            # those are the vertices we should in theory to keep (those are not on the merging boundary)
            preservableVertexIndices = []
            for element in maskedVertexIndices:
                if element not in mergingBodyVerticesList:
                    preservableVertexIndices.append(element)

            for edge in cob.data.edges:
                v1 = edge.vertices[0]
                v2 = edge.vertices[1]
                if v1 in maskedVertexIndices and v2 in maskedVertexIndices: #if both vertices of the edge are in the geograft merging/replaceable vertices list
                    if v1 in mergingBodyVerticesList and v2 in mergingBodyVerticesList: #if both vertices of the edge are to be merged/replaced then ignore this edge
                        continue
                    if v1 in preservableVertexIndices and v2 in preservableVertexIndices: #this is the edge we want to keep in order to maintain the face (easy scaling)
                        continue
                    removableEdgeIndices.append(edge.index) # finally we find an edge that is not in the boundary and we dont want to keep

        return preservableVertexIndices, removableEdgeIndices


    def joinUvTextures(self, me):
        if len(me.uv_layers) <= 1:
            return
        for n,data in enumerate(me.uv_layers[0].data):
            if data.uv.length < 1e-6:
                for uvloop in me.uv_layers[1:]:
                    if uvloop.data[n].uv.length > 1e-6:
                        data.uv = uvloop.data[n].uv
                        break
        for uvtex in list(getUvTextures(me)[1:]):
            if uvtex.name not in self.keepUv:
                try:
                    getUvTextures(me).remove(uvtex)
                except RuntimeError:
                    print("Cannot remove texture layer '%s'" % uvtex.name)


    def getUvName(self, me):
        for uvtex in getUvTextures(me):
            if uvtex.active_render:
                return uvtex.name
        return None


#-------------------------------------------------------------
#   Merge geografts Non Destructive (safe, slow)
#-------------------------------------------------------------

class MESH_OT_MergeGeograftsNonDestructive(GeograftOperator, GeograftMergerBase, IsMesh, bpy.types.Operator):
    bl_idname = "vxmod.merge_geografts_nondestructive"
    bl_label = "Merge Geografts Safe"
    bl_description = "Merge selected geografts to active object Non Destructive (keep original mesh faces)"
    bl_options = {'UNDO'}


    def run(self, context):
        cob = context.object
        anatomies = getAnatomies(context, cob)

        drivers = {}
        cname, anames = self.collectUvNames(context, cob, anatomies, drivers)

        # NOTE: the original version called collectRemovableEdges() here as well,
        # but this version deletes nothing so the result was never used.

        activateObject(context, cob)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type="VERT")
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_mode(type="EDGE")
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        #
        # in this version of merge geografts we don't remove edges/vertices/whatsoever, we try to keep original geometry intact
        # (the destructive versions delete removableEdgeIndices here)
        #
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type="VERT")
        bpy.ops.object.mode_set(mode='OBJECT')
        #
        #
        for aob in anatomies:
            dazGraftGroupBoundaryVertices = self.get_boundary_vertices_from_daz_graft_group(aob)
            dazGraftGroupAfterJoinDict=OrderedDict()
            for item in aob.data.DazGraftGroup:
                print("original matching: {0}:{1}".format(item.a,item.b))
                if item.a in dazGraftGroupBoundaryVertices: #only if is a boundary vertex, if is inside and there is a suggestion to merge it, then don't do it!!!
                    dazGraftGroupAfterJoinDict[item.a+len(cob.data.vertices)]=item.b                  #the vertex offset after the join is very important, tricky!!!
            for k, v in dazGraftGroupAfterJoinDict.items():
                print("shifted matching: {0}:{1}".format(k,v))

            setSelected(aob, True)
            activateObject(context, cob)
            setSelected(aob, True)
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')

            bpy.ops.object.join()
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')
            rvs = reversed(dazGraftGroupAfterJoinDict.items())
            for k, v in rvs:
                print("merging - {0}:{1}".format(k,v))
                cob.data.vertices[v].select = True # this is the vertex added from the aob (anatomy)
                cob.data.vertices[k].select = True # this is the original vertex from cob (body)
                #
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.merge(type='CENTER', uvs=False)
                bpy.ops.mesh.select_all(action='DESELECT')
                bpy.ops.object.mode_set(mode='OBJECT')
            #
            # we no longer need to hide (scale = 0 ) the unconected vertices, because those are still connected
            #

        bpy.ops.object.mode_set(mode='OBJECT')
        self.finishMerge(cob, cname, anames, drivers)


    # Function 1: Build the edge-face count dictionary
    def build_edge_face_count(self,mesh):
        edge_face_count = {}
        #
        # Loop through the polygons (faces) to count how many faces are connected to each edge
        for poly in mesh.polygons:
            # Loop through all edges in the face (polygon)
            for i, v1 in enumerate(poly.vertices):
                v2 = poly.vertices[(i + 1) % len(poly.vertices)]  # Get the next vertex to form the edge
                edge_key = tuple(sorted([v1, v2]))  # Sort the vertices to create an edge key
                if edge_key in edge_face_count:
                    edge_face_count[edge_key] += 1
                else:
                    edge_face_count[edge_key] = 1
        #
        return edge_face_count

    # Function 2: Check if a vertex is a boundary vertex
    def is_vertex_boundary(self,vertex_index, edge_face_count, mesh):
        # Loop through all edges connected to the vertex
        for edge in mesh.edges:
            if vertex_index in edge.vertices:
                edge_key = tuple(sorted(edge.vertices))  # Create an edge key from the vertices of the edge
                # If the edge is connected to only one face, it's a boundary edge
                if edge_face_count.get(edge_key, 0) == 1:
                    return True  # The vertex is on a boundary edge
        return False  # No boundary edge found for this vertex

    # Function to get boundary vertices from DazGraftGroup
    def get_boundary_vertices_from_daz_graft_group(self,aob):
        # Build the edge_face_count first
        edge_face_count = self.build_edge_face_count(aob.data)
        #
        boundary_vertices = []
        #
        # Loop through the DazGraftGroup pairs
        for pair in aob.data.DazGraftGroup:
            vertex_indices = [pair.a, pair.b]
            #
            for vertex_index in vertex_indices:
                # Check if the vertex is a boundary vertex
                if self.is_vertex_boundary(vertex_index, edge_face_count, aob.data):
                    boundary_vertices.append(vertex_index)
        #
        return boundary_vertices


#-------------------------------------------------------------
#   Merge geografts Non Destructive Bmesh (fast)
#-------------------------------------------------------------

class MESH_OT_MergeGeograftsNonDestructiveBmesh(GeograftOperator, GeograftMergerBase, IsMesh, bpy.types.Operator):
    bl_idname = "vxmod.merge_geografts_nondestructive_bmesh"
    bl_label = "Merge Geografts Safe (Bmesh)"
    bl_description = "Merge selected geografts to active object Non Destructive using bmesh (fast version)"
    bl_options = {'UNDO'}


    def run(self, context):
        cob = context.object
        anatomies = getAnatomies(context, cob)

        drivers = {}
        cname, anames = self.collectUvNames(context, cob, anatomies, drivers)

        # Merge each anatomy using bmesh weld_verts
        # Instead of per-pair OBJECT<->EDIT mode switching, we do a single
        # bmesh weld_verts call per anatomy = only 2 mode switches total per anatomy
        activateObject(context, cob)
        for aob in anatomies:
            # Fast boundary detection using bmesh (O(1) per vertex via vert.is_boundary)
            dazGraftGroupBoundaryVertices = self.get_boundary_vertices_bmesh_fast(aob)

            # Build merge mapping with offset for post-join vertex indices
            cob_vert_count = len(cob.data.vertices)
            dazGraftGroupAfterJoinDict = OrderedDict()
            for item in aob.data.DazGraftGroup:
                if item.a in dazGraftGroupBoundaryVertices:
                    dazGraftGroupAfterJoinDict[item.a + cob_vert_count] = item.b

            # Join anatomy mesh into body mesh
            setSelected(aob, True)
            activateObject(context, cob)
            setSelected(aob, True)
            bpy.ops.object.join()

            # Merge all boundary vertex pairs at once using bmesh weld_verts
            if dazGraftGroupAfterJoinDict:
                bpy.ops.object.mode_set(mode='EDIT')
                bm = bmesh.from_edit_mesh(cob.data)
                bm.verts.ensure_lookup_table()

                targetmap = {}
                for src_idx, dst_idx in dazGraftGroupAfterJoinDict.items():
                    if src_idx < len(bm.verts) and dst_idx < len(bm.verts):
                        targetmap[bm.verts[src_idx]] = bm.verts[dst_idx]

                if targetmap:
                    bmesh.ops.weld_verts(bm, targetmap=targetmap)

                bmesh.update_edit_mesh(cob.data)
                bpy.ops.object.mode_set(mode='OBJECT')

        bpy.ops.object.mode_set(mode='OBJECT')
        self.finishMerge(cob, cname, anames, drivers)


    def get_boundary_vertices_bmesh_fast(self, aob):
        """Fast boundary vertex detection using bmesh without mode switching.
        Uses bmesh.new() in object mode - O(1) per vertex check via vert.is_boundary."""
        bm = bmesh.new()
        bm.from_mesh(aob.data)
        bm.verts.ensure_lookup_table()

        boundary_vertices = set()
        for pair in aob.data.DazGraftGroup:
            if pair.a < len(bm.verts) and bm.verts[pair.a].is_boundary:
                boundary_vertices.add(pair.a)

        bm.free()
        return boundary_vertices


#-------------------------------------------------------------
#   Merge geografts Fast (destructive, deletes the masked edges)
#-------------------------------------------------------------

class MESH_OT_MergeGeograftsFast(GeograftOperator, GeograftMergerBase, IsMesh, bpy.types.Operator):
    bl_idname = "vxmod.merge_geografts_fast"
    bl_label = "Merge Geografts Fast"
    bl_description = "Merge selected geografts to active object (fast version)"
    bl_options = {'UNDO'}


    def run(self, context):
        cob = context.object
        anatomies = getAnatomies(context, cob)

        drivers = {}
        cname, anames = self.collectUvNames(context, cob, anatomies, drivers)

        preservableVertexIndices, removableEdgeIndices = self.collectRemovableEdges(cob, anatomies)

        activateObject(context, cob)
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_mode(type="VERT")
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_mode(type="EDGE")
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        for edgeIndex in removableEdgeIndices:
            cob.data.edges[edgeIndex].select= True
        bpy.ops.object.mode_set(mode='EDIT')
        ##############################################################################################################
        bpy.ops.mesh.delete(type='EDGE')                        # DELETE EDGE
        ##############################################################################################################
        bpy.ops.mesh.select_mode(type="VERT")
        bpy.ops.object.mode_set(mode='OBJECT')

        for aob in anatomies:
            dazGraftGroupAfterJoinDict=OrderedDict()
            for item in aob.data.DazGraftGroup:
                print("original matching: {0}:{1}".format(item.a,item.b))
                dazGraftGroupAfterJoinDict[item.a+len(cob.data.vertices)]=item.b                  #the vertex offset after the join is very important, tricky!!!
            for k, v in dazGraftGroupAfterJoinDict.items():
                print("shifted matching: {0}:{1}".format(k,v))

            setSelected(aob, True)
            activateObject(context, cob)
            setSelected(aob, True)
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')

            bpy.ops.object.join()
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='DESELECT')
            bpy.ops.object.mode_set(mode='OBJECT')
            rvs = reversed(dazGraftGroupAfterJoinDict.items())
            for k, v in rvs:
                print("merging - {0}:{1}".format(k,v))
                cob.data.vertices[v].select = True # this is the vertex added from the aob (anatomy)
                cob.data.vertices[k].select = True # this is the original vertex from cob (body)
                #
                bpy.ops.object.mode_set(mode='EDIT')
                bpy.ops.mesh.merge(type='CENTER', uvs=False)
                bpy.ops.mesh.select_all(action='DESELECT')
                bpy.ops.object.mode_set(mode='OBJECT')
            #
            # the leftover body vertices under the geograft are collapsed to a point so they don't show
            for p in preservableVertexIndices:
                cob.data.vertices[p].select = True
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.transform.resize(value=(0.0, 0.0, 0.0) )
            bpy.ops.mesh.select_all(action='DESELECT')

        bpy.ops.object.mode_set(mode='OBJECT')
        self.finishMerge(cob, cname, anames, drivers)


#-------------------------------------------------------------
#   Dispatch helper used by the exporter
#-------------------------------------------------------------

MERGE_GEOGRAFT_OPERATORS = [
    ("vxmod.merge_geografts_nondestructive_bmesh", "fast bmesh version"),
    ("vxmod.merge_geografts_nondestructive", "safe version"),
    ("vxmod.merge_geografts_fast", "destructive fast version"),
    # last resort: Diffeomorphic's own operator. Not cloned here on purpose -
    # it is their code, it ships with their addon, no reason to duplicate it.
    ("daz.merge_geografts", "Diffeomorphic's own destructive version"),
]


def geograft_data_available():
    """The merge code itself is local now, but the geograft data it reads
    (DazGraftGroup / DazMaskGroup / DazVertexCount) is still registered by the
    Diffeomorphic addon, so it has to be enabled."""
    return hasattr(bpy.types.Mesh, "DazGraftGroup")


def merge_geografts_into_active():
    """Merge the selected geografts into the active object.

    Assumes the geografts are selected and the body mesh is active, which is
    what export_to_unreal_v2 sets up. Uses the fast bmesh version and falls
    back through the other implementations if it is unavailable."""
    from bpy.ops import op_as_string
    for idname, label in MERGE_GEOGRAFT_OPERATORS:
        try:
            op_as_string(idname)
        except Exception:
            continue
        print("%s is available (%s)" % (idname, label))
        module, opname = idname.split(".")
        return getattr(getattr(bpy.ops, module), opname)()
    raise RuntimeError("No geograft merge operator is registered")
