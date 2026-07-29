bl_info = {
    "name": "VXMod Unreal Workflow",
    "description": "VXMod Unreal Workflow",
    "author": "ModdingClass",
    "version": (0, 1, 6),
    "blender": (2, 7, 9),
    "location": "Toolpanel > Misc",
    "warning": "This code is still very much alpha!",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import-Export"
}
import collections
import os
import sys
import subprocess
import shutil
import zipfile
import inspect
import math
import threading
import time
import bmesh
import bpy
import mathutils
import math
import importlib
from mathutils import Vector
from bpy.app.handlers import persistent
from bpy.props import StringProperty, BoolProperty 
from bpy_extras.io_utils import ImportHelper 
from bpy_extras.io_utils import ExportHelper 
from bpy.types import Operator
import bpy.utils.previews
import re
from tempfile import NamedTemporaryFile

import decimal
from .utilz import *
from .h5m import *

from .armature import *
from .parent_to_child_adjust_bone_length import *


from .face_default import *

from .clear_armature_rotation import *
from .tools_message_box import *

from .exporter_unreal import *
from .importer_g3f import *
from .importer_g3f_morphs import *
from .exporter_fake_bones import *
from .exporter_z_cleanup_values import *

from .tools_duplicate_object_remove_mats_shapekeys import *
from .helper_vgroups import *
from .g3f.importer_g3f_difeomorphic import *
from .g3f.difeomorphic_workflow import *
from .tools_import_export_vertex_groups_json import *
from .tools_import_export_shape_keys_json import *
from .tools_import_export_materials_json import *
from .tools_import_export_edit_bones_json import *
from .ik_tools import *

from .fbody_stats import *

from bpy.app.handlers import persistent
from bpy.props import *
import mathutils
import bpy_extras.io_utils
from math import *
from mathutils import *
from .configobj import ConfigObj


if "bpy" in locals():
    import imp
    imp.reload(utilz)

    imp.reload(h5m)
    imp.reload(armature)
    imp.reload(parent_to_child_adjust_bone_length)


    imp.reload(face_default)

    imp.reload(clear_armature_rotation)
    imp.reload(tools_message_box)

    imp.reload(diffeomorphic_merge_geografts)
    imp.reload(exporter_unreal)
    imp.reload(importer_g3f)
    imp.reload(importer_g3f_morphs)
    imp.reload(exporter_fake_bones)
    imp.reload(exporter_z_cleanup_values)

    imp.reload(tools_duplicate_object_remove_mats_shapekeys)
    imp.reload(helper_vgroups)
    imp.reload(g3f.importer_g3f_difeomorphic)
    imp.reload(g3f.difeomorphic_workflow)
    imp.reload(g3f.difeomorphic_workflow_init_custom_vertex_indices)
    imp.reload(tools_import_export_vertex_groups_json)
    imp.reload(tools_import_export_shape_keys_json)
    imp.reload(tools_import_export_materials_json)
    imp.reload(fbody_stats)
    imp.reload(ik_tools)
    print("Reloaded multifiles")
else:
    from . import utilz

    from . import h5m
    from . import armature
    from . import parent_to_child_adjust_bone_length
    
    from . import face_default

    from . import clear_armature_rotation
    from . import tools_message_box

    from . import diffeomorphic_merge_geografts
    from . import exporter_unreal
    from . import importer_g3f_morphs
    from . import exporter_fake_bones
    from . import exporter_z_cleanup_values

    from . import tools_duplicate_object_remove_mats_shapekeys
    from . import helper_vgroups
    from .g3f import importer_g3f_difeomorphic
    from .g3f import difeomorphic_workflow
    from .g3f import difeomorphic_workflow_init_custom_vertex_indices
    from . import tools_import_export_vertex_groups_json
    from . import tools_import_export_shape_keys_json
    from . import tools_import_export_materials_json
    from . import fbody_stats 
    from . import ik_tools
    print("Imported multifiles")

version = 'v%s.%s'%(bl_info['version'][0],bl_info['version'][1])


fbody_global_matching_index_dict = OrderedDict()




def load_config2(self,context) :
    scene = bpy.context.scene
    
## addon configuration file (config)
def load_config(self,context) :
    print ('load_config -> ()')
    scene = bpy.context.scene
    #vxmod is a new object created in scene context 
    vxmod = bpy.context.scene.vxmod
    print('opening file: %s'%vxmod.filepath)
    
    
def save_config(self,context) :
    print ('save_config -> ()')
    scene = bpy.context.scene
    vxmod = bpy.context.scene.vxmod
    print('opening file: %s'%vxmod.filepath)

    
## ADDON INTERFACE CLASS
def ui_tab(elm,tab=0.05) :
    split = elm.split(tab)
    col = split.column()
    return split.column()

## MAIN CLASS
class VXMOD_vars(bpy.types.PropertyGroup) :
    ## file ops
    def update_func_exportfolderpath(self, context):
        #self.exportfolderpath = os.path.join(self.exportfolderpath,"")
        new_value = os.path.join(self.exportfolderpath,"")
        if new_value == self.exportfolderpath:
            pass
        else:
            self.exportfolderpath = new_value
        print("exportfolderpath: ", self.exportfolderpath)

    def update_func_exportFolderPathUnreal(self, context):
        new_value = os.path.join(self.exportFolderPathUnreal,"")
        if new_value == self.exportFolderPathUnreal:
            pass
        else:
            self.exportFolderPathUnreal = new_value
        print("exportFolderPathUnreal: ", self.exportFolderPathUnreal)

    def get_all_mesh_items(self, context):
        items = []
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH':
                items.append((obj.name, obj.name, "Mesh object"))
        if not items:
            items.append(('NONE', "(No meshes)", "No mesh objects in scene"))
        return items


    def update_exportable_mesh(self, context):
        # Optional: print when changed manually
        print("Exportable mesh set to:", self.exportable_mesh)
        


    #exportfolderpath =  bpy.props.StringProperty(name="exportfolderpath", default='',subtype='DIR_PATH', update=update_func_exportfolderpath)
    #
    filepath =  bpy.props.StringProperty(name="filepath", default='',subtype='FILE_PATH')
    filepath_h5m =  bpy.props.StringProperty(name="filepath_h5m", default='',subtype='FILE_PATH')
    #
    #fbxFilename =  bpy.props.StringProperty(name="fbxFilename", default='',subtype='FILE_NAME')
    #
    #exportfolderpath =  bpy.props.StringProperty(name="exportfolderpath", default='',subtype='DIR_PATH', update=update_func_exportfolderpath)
    exportFolderPathUnreal = bpy.props.StringProperty(name="exportFolderPathUnreal", default='',subtype='DIR_PATH', update=update_func_exportFolderPathUnreal)
    bodyNo = bpy.props.StringProperty(name="bodyNo",description="Body No", default="01")
    dontExportJointEnds = bpy.props.BoolProperty(name="dontExportJointEnds", description="Weightless jointEnds are not exported",    default=True)
    dontExportMaleJoints = bpy.props.BoolProperty(name="dontExportMaleJoints", description="Male specific joints are not exported",    default=True)
    #
    #includeGeograftsOnExport = bpy.props.BoolProperty(name="includeGeograftsOnExport", description="Bake children Geografts when exporting",    default=True)
    includeGeograftsOnExportUnreal = bpy.props.BoolProperty(name="includeGeograftsOnExportUnreal", description="Bake children Geografts when exporting",    default=True)
    createSubdivMeshOnExportUnreal = bpy.props.BoolProperty(name="createSubdivMeshOnExportUnreal", description="Add a subdivided mesh when exporting",    default=True)
    cleanTempMeshesBeforeExportUnreal = bpy.props.BoolProperty(name="cleanTempMeshesBeforeExportUnreal", description="Delete temp/work meshes before exporting",    default=True)
    cleanTempMeshesAfterExportUnreal = bpy.props.BoolProperty(name="cleanTempMeshesAfterExportUnreal", description="Delete temp/work meshes after exporting",    default=True)
    reorientBonesOnExportUnreal = bpy.props.BoolProperty(name="reorientBonesOnExportUnreal", description="Reorient bones (Unreal friendly) before exporting",    default=True)
    exportShapekeys = bpy.props.BoolProperty(name="exportShapekeys", description="Export shapekeys for base and subdivided mesh (uncheck for exporting faster/DEBUG)",    default=True)
    cacheShapekeys = bpy.props.BoolProperty(name="cacheShapekeys", description="Cache subdivided shape key data to disk. Speeds up subsequent exports by skipping subdivision",    default=True)
    #
    cleanupTempMeshesMode = bpy.props.EnumProperty(
        name="Cleanup Temp Meshes",
        description="Cleanup temporary objects created during export",
        items=[
            ('BEFORE', "Before", "Before only"),
            ('AFTER', "After", "After only"),
            ('BOTH', "Before+After", "Both before and after"),
        ],
        default='AFTER',
    )
    exportable_mesh = bpy.props.EnumProperty(
        name="Exportable Mesh",
        description="Choose which mesh to export",
        items=get_all_mesh_items,
        update=update_exportable_mesh
    )
    pin_exportable_mesh = bpy.props.BoolProperty(
        name="Pin Mesh",
        description="If pinned, the selected mesh won’t change when you change the active object",
        default=False
    )

        

class VXMOD_CONVERTER_OT_PanelDifeomorphicToVXMod(bpy.types.Panel):
    """Creates a Panel in the Tool Shelf"""
    bl_label = "VXMod Workflow"
    bl_idname = "vxmod.converter_difeomorphic_to_vxmod"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = "VXMod"
    def draw(self,context):
        layout=self.layout
        scene=context.scene
        vxmod  = scene.vxmod

        # --- Step 1: mesh + materials. Shared by both skeleton paths below, because
        #     each of them needs body_subdiv_cage to exist first.
        step1_box = layout.box()
        step1_box.label(text="1. Mesh", icon='OBJECT_DATA')
        step1_box.label(text="Select the Difeomorphic G3F armature")
        step1_box.operator('vxmod.convert_g3fdifeo_to_vxmodf',
                           text='G3F'+u'→'+'VX body', icon='OBJECT_DATA')

        # --- Step 2: the current path. One button does armature + bind + face collapse
        #     + vertex groups, and finds both objects on its own.
        step2_box = layout.box()
        step2_box.label(text="2. Manny skeleton", icon='POSE_HLT')
        step2_box.label(text="Nothing to select")
        step2_box.operator('vxmod.convert_g3fdifeo_to_vxmodf_manny_full',
                           text='Manny FULL', icon='POSE_HLT')
        step2_box.label(text="or run the steps separately:")
        row = step2_box.row(align=True)
        row.operator('vxmod.convert_g3fdifeo_to_vxmodf_manny',
                     text='Armature only', icon='ARMATURE_DATA')
        row.operator('vxmod.switch_to_manny_vertex_groups',
                     text='Vertex Groups only', icon='GROUP_VERTEX')

        # --- The original VXMod skeleton. Kept working and deliberately untouched, but
        #     it targets a different skeleton than the Manny path - do not mix the two.
        legacy_box = layout.box()
        legacy_box.label(text="Legacy VXMod skeleton", icon='ARMATURE_DATA')
        legacy_box.label(text="Needs an 'Armature' in the scene already")
        row = legacy_box.row(align=True)
        row.operator('vxmod.convert_g3fdifeo_to_vxmodf_new',
                     text='Difeo '+u'→'+' VXMod', icon='ARMATURE_DATA')
        row.operator('vxmod.armature_adjust_rig_to_shape',
                     text='Adjust Rig to VX body',
                     icon_value=custom_icons["wand_icon"].icon_id)
        row = legacy_box.row(align=True)
        row.operator('vxmod.switch_to_vxmod_vertex_groups',
                     text='Switch Vertex Groups', icon='GROUP_VERTEX')
        row.operator('vxmod.armature_make_friendly_ik_joints',
                     text='Force friendly IK joints',
                     icon_value=custom_icons["wand_icon"].icon_id)



class ARMATURE_OT_ConstraintsPanel(bpy.types.Panel):
    """Creates a Panel in the Tool Shelf"""
    bl_label = "Constraints and IKs"
    bl_idname = "armature.constraints_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = "VXMod"
    def draw(self,context):
        layout=self.layout
        box = layout.box()
        scene=context.scene
        vxmod  = scene.vxmod
        row=box.row(align=True)
        row.operator('vxmod.fake',text='              ')
        row.operator('vxmod.hh_pose_ik',text='HH Pose IK',icon='OUTLINER_DATA_POSE')
        #row.operator('vxmod.add_legs_ik',text='Ignore this',icon='POSE_DATA')
        row.operator('vxmod.add_finger_hand_close_constraints',text='Finger Constraints',icon='CONSTRAINT_BONE')
        row=box.row(align=True)
        row.operator('vxmod.fake',text='              ')
        row.operator('vxmod.add_custom_ik_bones',text='Custom IK('+u'β'+')',icon='OUTLINER_DATA_POSE')
        row.operator('vxmod.fake',text='              ')


class DebugBonesPanel(bpy.types.Panel):
    """Creates a Panel in the Tool Shelf"""
    bl_label = "Debug Bones"
    bl_idname = "vxmod.debug_bones_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = "VXMod"

    def draw(self,context):
        layout=self.layout
        box = layout.box()
        scene=context.scene
        vxmod  = scene.vxmod
        row=box.row(align=True)
        row.operator('armature.move_twist_bones_to_custom_layer',text='Hide Twist Bones')
        row.operator('vxmod.fake',text='              ')
        row.operator('vxmod.fake',text='              ')
        row=box.row(align=True)
        
        #row.operator('vxmod.add_fake_shape_bones',text='Add Fake Shape Bones',icon='PMARKER')
        #row.operator('vxmod.remove_fake_bones',text='Remove Fake Bones',icon='PMARKER')
        #row.operator('vxmod.fake',text='              ')
        #row=box.row(align=True)
        #row.operator('vxmod.add_fake_axis_bones',text='Add Fake Axis Bones',icon='PMARKER')
        #row.operator('vxmod.merge_fakes_in_single_object',text='Merge fakes',icon='OUTLINER_OB_GROUP_INSTANCE')
        #row.operator('vxmod.export_fake_bones',text='Export Fake Bones')
        #row=box.row(align=True)
        row.operator('armature.move_jointend_bones_to_custom_layer',text='Hide jointEnd Bones')
        row.operator('vxmod.fake',text='              ')
        row.operator('vxmod.fake',text='              ')


class EXPORT_PT_VXModToUnreal(bpy.types.Panel):
    """Creates a Panel in the Tool Shelf"""
    bl_label = "Unreal Exporter"
    bl_idname = "export.vxmod_to_unreal_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'TOOLS'
    bl_category = "VXMod"
    def draw(self,context):
        layout=self.layout
        scene=context.scene
        vxmod  = scene.vxmod

        # Dependency checks
        missing = []
        if not operator_exists("gmtt.object_strip_and_clean"):
            missing.append("Game Mod Tiny Tools (GMTT)")
        if not geograft_data_available():
            missing.append("Diffeomorphic (import_daz)")
        if missing:
            box = layout.box()
            box.alert = True
            box.label(text="Missing required addons:", icon='ERROR')
            for name in missing:
                box.label(text="  " + name)

        row = layout.row(align=True)
        # Combobox for mesh selection
        row.prop(vxmod, "exportable_mesh", text="")
        # Small pin icon toggle
        icon = 'PINNED' if vxmod.pin_exportable_mesh else 'UNPINNED'
        row.prop(vxmod, "pin_exportable_mesh", text="", icon=icon)
        #
        box = layout.box()
        row=box.row(align=True)
        row.operator('vxmod.fake',text='              ')
        row.operator('vxmod.fake',text='              ')
        row.operator('vxmod.fake',text='              ')
        #box.row().separator()
        row=box.row(align=True)
        row.operator('vxmod.fake',text='              ')        
        row.operator('vxmod.build_subdivision_vertex_matching_table',text='Build subdiv match', icon='GROUP_VERTEX')  
        row.operator('vxmod.load_subdivision_vertex_matching_table',text='Load subdiv match',icon='GROUP_VERTEX')
        #box.row().separator()
        row=box.row(align=True)
        row.operator('vxmod.fake',text='              ')
        row.operator('vxmod.fake',text='              ')
        #
        export_label = "Export Mesh"
        obj = bpy.data.objects.get(vxmod.exportable_mesh)
        # check if it has an Armature modifier
        if obj and any(mod.type == 'ARMATURE' for mod in obj.modifiers):
            export_label = "Export SKM_" # + obj.name
        elif obj:
            export_label = "Export SM_" #+ obj.name
        else:
            export_label = "Export bugged"
        row.operator('vxmod.export_skeletalmesh_unreal',text=export_label, icon='TIME')
        row=box.row(align=True)
        row.operator('export.vxmod_animation_to_unreal', text="Export ANIM_" + vxmod.exportable_mesh, icon='RENDER_ANIMATION')
        row=box.row()
        
        #row.separator()
        
        #row.operator('test.open_filebrowser',text='Import Blenda body',icon='OBJECT_DATA')    
        extra_export_box = row.box()
        extra_export_box.label(text="Extra Export: ")
        row_extra=extra_export_box.row(align=True)
        row_extra.prop(vxmod,'includeGeograftsOnExportUnreal',text="Include Geografts")
        #row_extra.alignment = 'RIGHT'
        row_extra.prop(vxmod,'reorientBonesOnExportUnreal',text="Re-Orient Bones (TODO)")
        
        #row_extra=extra_export_box.row(align=True)
        #extra_subdiv_box = row_extra.column()
        #extra_subdiv_box.label(text="Subdivision: ")

        row_extra=extra_export_box.row(align=True)
        row_extra.prop(vxmod,'createSubdivMeshOnExportUnreal',text="Create Subdiv")
        row_extra=extra_export_box.row(align=True)
        #row_extra.alignment = 'RIGHT'
        row_extra.prop(vxmod,'exportShapekeys',text="Export Shapekeys")
        sub = extra_export_box.row(align=True)
        sub.active = vxmod.exportShapekeys
        sub.separator()
        sub.prop(vxmod,'cacheShapekeys',text="Shapekeys Caching")
        #
        row_extra=extra_export_box.row(align=True)
        col = row_extra.column()
        col.label(text="Cleanup Mode: ")
        row_extra=extra_export_box.row(align=True)
        row_extra.prop(vxmod, "cleanupTempMeshesMode", expand=True)
        #
        #row_extra=new_box.row(align=True)
        #row_extra.prop(vxmod,'cleanTempMeshesBeforeExportUnreal',text="Cleanup before export")
        #row_extra=new_box.row(align=True)
        #row_extra.prop(vxmod,'cleanTempMeshesAfterExportUnreal',text="Cleanup after export")
        

        row=box.row(align=True)
        subbox_exporter=row.box()
        subbox_row = subbox_exporter.row()
        
        icon='FILE_FOLDER'
        subbox_row.label(text='Folder location:',icon=icon)
        subbox_row = subbox_exporter.row()
        subbox_row.prop(vxmod,'exportFolderPathUnreal',text='')        
        #subbox_row = subbox_exporter.row()
        #subbox_row.label(text='Body#:',icon='QUESTION')
        #subbox_row.prop(vxmod,'fbxFilename',text='Fbx filename')







class OT_fake(bpy.types.Operator):
    ''''''
    bl_idname = "vxmod.fake"
    bl_label = ""

    group = bpy.props.StringProperty(name="ALL")

    def execute(self, context):
        return {'FINISHED'}



class ARMATURE_OT_move_twist_bones_to_custom_layer(bpy.types.Operator):
    ''''''
    bl_idname = "armature.move_twist_bones_to_custom_layer"
    bl_label = ""
    bl_description = "Move Twist Bones to other layer"

    group = bpy.props.StringProperty(name="ALL")

    def execute(self, context):
        scene  = bpy.context.scene
        vxmod  = scene.vxmod
        moveTwistBonesToCustomLayer()
        return {'FINISHED'}        

class ARMATURE_OT_move_jointend_bones_to_custom_layer(bpy.types.Operator):
    ''''''
    bl_idname = "armature.move_jointend_bones_to_custom_layer"
    bl_label = ""
    bl_description = "Move jointEnd Bones to other layer"

    group = bpy.props.StringProperty(name="ALL")

    def execute(self, context):
        scene  = bpy.context.scene
        vxmod  = scene.vxmod
        moveJointEndBonesToCustomLayer()
        return {'FINISHED'}  

class ARMATURE_OT_hh_pose_ik(bpy.types.Operator):
    ''''''
    bl_idname = "vxmod.hh_pose_ik"
    bl_label = ""
    bl_description = "High Heels Pose IK"

    group = bpy.props.StringProperty(name="ALL")

    def execute(self, context):
        scene  = bpy.context.scene
        vxmod  = scene.vxmod
        create_HHPoseIk(bpy.context.scene.objects["Armature"])
        return {'FINISHED'}        



class ARMATURE_OT_add_custom_ik_bones(bpy.types.Operator):
    ''''''
    bl_idname = "vxmod.add_custom_ik_bones"
    bl_label = ""
    u = u'β'
    s = u.encode('utf8')
    bl_description = "Temporary Add IK to the body (beta)"

    group = bpy.props.StringProperty(name="ALL")

    def execute(self, context):
        scene  = bpy.context.scene
        vxmod  = scene.vxmod
        create_IKs(bpy.context.scene.objects["Armature"])
        return {'FINISHED'}        


class ARMATURE_OT_add_legs_ik(bpy.types.Operator):
    ''''''
    bl_idname = "vxmod.add_legs_ik"
    bl_label = ""
    bl_description = "Add IK to the legs. Useful for posing and creating inverse bind matrix for high heels poses"

    group = bpy.props.StringProperty(name="ALL")

    def execute(self, context):
        scene  = bpy.context.scene
        vxmod  = scene.vxmod
        ShowMessageBox("Not implemented", "Warning", 'INFO')
        return {'FINISHED'}        
        
class ARMATURE_OT_add_finger_hand_close_constraints(bpy.types.Operator):
    ''''''
    bl_idname = "vxmod.add_finger_hand_close_constraints"
    bl_label = ""
    bl_description = "Add finger constraints useful for hand closing"

    group = bpy.props.StringProperty(name="ALL")

    def execute(self, context):
        scene  = bpy.context.scene
        vxmod  = scene.vxmod
        ShowMessageBox("Not implemented", "Warning", 'INFO')
        return {'FINISHED'}            


class ARMATURE_OT_correct_final_rolls(bpy.types.Operator):
    ''''''
    bl_idname = "vxmod.correct_final_rolls"
    bl_label = ""
    bl_description = "Add a required -90 rotation to the armature before exporting"

    group = bpy.props.StringProperty(name="ALL")

    def execute(self, context):
        scene  = bpy.context.scene
        vxmod  = scene.vxmod
        armature_object = bpy.data.objects["Armature"]
        fix_rolls(armature_object)
        return {'FINISHED'}
        
        
        

class ARMATURE_OT_adjust_rig_to_shape(bpy.types.Operator):
    ''''''
    bl_idname = "vxmod.adjust_rig_to_shape"
    bl_label = ""
    bl_description = "Adjust armature to shape of the custom g3f body."

    group = bpy.props.StringProperty(name="ALL")

    def execute(self, context):
        scene  = bpy.context.scene
        vxmod  = scene.vxmod
        
        script_file = os.path.realpath(__file__)
        directory = os.path.dirname(script_file)
        
        exec(open(os.path.join(directory,"g3f","script_autofix_armature_0_init_vertex_groups.py")).read())
        exec(open(os.path.join(directory,"g3f","script_autofix_armature_1_functions.py")).read())
        exec(open(os.path.join(directory,"g3f","script_autofix_armature_3_start_boilerplate.py")).read())
        #
        exec(open(os.path.join(directory,"g3f","script_autofix_armature_4_calculate_body.py")).read())
        exec(open(os.path.join(directory,"g3f","script_autofix_armature_4_calculate_head.py")).read())
        #
        exec(open(os.path.join(directory,"g3f","script_autofix_armature_5_preinit_boilerplate.py")).read())
        #
        exec(open(os.path.join(directory,"g3f","script_autofix_armature_5_run_body.py")).read())
        exec(open(os.path.join(directory,"g3f","script_autofix_armature_5_run_head.py")).read())
        #
        exec(open(os.path.join(directory,"g3f","script_autofix_armature_9_end_boilerplate.py")).read())
        return {'FINISHED'}        




class MESH_OT_clone_as_weighted_object(bpy.types.Operator):
    ''''''
    bl_idname = "vxmod.clone_as_weighted_object"
    bl_label = ""
    bl_description = "Duplicate an object but clears materials, shapekeys and modifiers from it. \nUseful to make a copy of the object and keep the weights for later use."

    group = bpy.props.StringProperty(name="ALL")

    def execute(self, context):
        scene  = bpy.context.scene
        vxmod  = scene.vxmod
        duplicate_object_keep_only_VG()
        return {'FINISHED'}        



def flatten(mat):
    dim = len(mat)
    return [mat[j][i] for i in range(dim) for j in range(dim)]
                      

class ARMATURE_OT_import_armature(bpy.types.Operator, ImportHelper):
    ''''''
    bl_idname = "vxmod.import_armature"
    bl_label = "Import TXT File"
    bl_description = "Import armature for CollaTkane txt anim file"


    filter_glob = StringProperty(
        default='*.txt',
        options={'HIDDEN'}
    )
    
    def execute(self, context):
        scene  = bpy.context.scene
        vxmod  = scene.vxmod
        bpy.ops.object.select_all(action='DESELECT')
        print('Selected file:', self.filepath)
        path_to_file = self.filepath
        return {'FINISHED'}

class IMPORT_OT_Import_fbody_matching_index_dict_from_json(bpy.types.Operator):
    ''''''
    bl_idname = "vxmod.load_subdivision_vertex_matching_table"
    bl_label = ""
    bl_description = "Load subdivision vertex matching table from json"
    
    group = bpy.props.StringProperty(name="ALL")

    def execute(self, context):
        scene  = bpy.context.scene
        vxmod  = scene.vxmod
        mesh_name = vxmod.exportable_mesh
        bpy.context.scene.objects.active = bpy.data.objects[mesh_name]
        if os.path.isdir(vxmod.exportFolderPathUnreal):
            load_subdivision_vertex_matching_table(vxmod)
        else:
            ShowMessageBox("Missing the import/export folder", "Error", 'ERROR')
            return {'FINISHED'}        
        return {'FINISHED'}


class EXPORT_OT_Export_subdivision_vertex_matching_table(bpy.types.Operator):
    ''''''
    bl_idname = "vxmod.build_subdivision_vertex_matching_table"
    bl_label = ""
    bl_description = "Build subdivision vertex matching table as \"key\":val where key is vertex on mesh (edit mode subdivided) and val is vertex on mesh_hires(modifier)"
    
    group = bpy.props.StringProperty(name="ALL")

    def execute(self, context):
        scene  = bpy.context.scene
        vxmod  = scene.vxmod
        mesh_name = vxmod.exportable_mesh
        bpy.context.scene.objects.active = bpy.data.objects[mesh_name]
        if os.path.isdir(vxmod.exportFolderPathUnreal):
            print ("Exporting to: "+vxmod.exportFolderPathUnreal)
            build_subdivision_vertex_matching_table(vxmod)
        else:
            ShowMessageBox("Missing the export folder", "Error", 'ERROR')
            return {'FINISHED'}        
        return {'FINISHED'}

class EXPORT_OT_VXModBodyToUnreal(bpy.types.Operator):
    ''''''
    bl_idname = "vxmod.export_skeletalmesh_unreal"
    bl_label = ""
    bl_description = "Export SkeletalMesh for Unreal"
    
    group = bpy.props.StringProperty(name="ALL")

    def execute(self, context):
        #scene = context.scene
        scene  = bpy.context.scene
        vxmod  = scene.vxmod
        mesh_name = vxmod.exportable_mesh
        bpy.context.scene.objects.active = bpy.data.objects[mesh_name]
        #mesh_obj = bpy.data.objects.get(mesh_name)
        if os.path.isdir(vxmod.exportFolderPathUnreal):
            print ("Exporting to: "+vxmod.exportFolderPathUnreal)
            export_to_unreal_v2(vxmod)
        else:
            ShowMessageBox("Missing the export folder", "Error", 'ERROR')
            return {'FINISHED'}        
        return {'FINISHED'}



class EXPORT_OT_VXModAnimationToUnreal(bpy.types.Operator):
    ''''''
    bl_idname = "export.vxmod_animation_to_unreal"
    bl_label = ""
    bl_description = "Export Animation (armature only) for Unreal"

    def execute(self, context):
        scene = bpy.context.scene
        vxmod = scene.vxmod
        mesh_name = vxmod.exportable_mesh
        bpy.context.scene.objects.active = bpy.data.objects[mesh_name]
        if os.path.isdir(vxmod.exportFolderPathUnreal):
            export_animation_to_unreal(vxmod)
        else:
            ShowMessageBox("Missing the export folder", "Error", 'ERROR')
        return {'FINISHED'}


class CONVERT_OT_G3F_Body_Difeomorphic_new(bpy.types.Operator):
    ''''''
    bl_idname = "vxmod.convert_g3fdifeo_to_vxmodf_new"
    bl_label = ""
    bl_description = "Convert a Difeomorphic G3F body into a VXMod body"    
    def execute(self, context):
        alignArmatureToDifeomorphicNew()
        return {'FINISHED'}

class CONVERT_OT_G3F_Body_Difeomorphic_manny(bpy.types.Operator):
    ''''''
    bl_idname = "vxmod.convert_g3fdifeo_to_vxmodf_manny"
    bl_label = ""
    bl_description = "Build the Manny armature from the selected Difeomorphic G3F rig"
    bl_options = {'UNDO'}
    def execute(self, context):
        alignArmatureFromDifeomorphicToManny()
        return {'FINISHED'}


class CONVERT_OT_G3F_Body_Difeomorphic_manny_full(bpy.types.Operator):
    '''
    Full Manny conversion: armature, bind, face collapse, vertex-group rename.

    Nothing needs to be selected. The Difeomorphic G3F armature and the converted body
    mesh are both found automatically; just run "G3F->VX body" first so the mesh exists.
    '''
    bl_idname = "vxmod.convert_g3fdifeo_to_vxmodf_manny_full"
    bl_label = ""
    bl_description = "Full Manny conversion: armature + bind + face collapse + vertex groups"
    bl_options = {'UNDO'}

    def execute(self, context):
        scene = bpy.context.scene
        vxmod = scene.vxmod

        # Find both objects up front so we fail before changing anything.
        source_armature, error = findDiffeomorphicArmature()
        if error:
            ShowMessageBox(error, "Error", 'ERROR')
            return {'CANCELLED'}

        mesh_object, error = findConvertedBodyMesh(vxmod.exportable_mesh)
        if error:
            ShowMessageBox(error, "Error", 'ERROR')
            return {'CANCELLED'}

        print("Manny FULL: armature '{}' -> mesh '{}'".format(
            source_armature.name, mesh_object.name))

        # alignArmatureFromDifeomorphicToManny reads the ACTIVE object, so make it so
        # rather than asking the user to get the selection right.
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        source_armature.select = True
        source_armature.hide = False
        bpy.context.scene.objects.active = source_armature

        # 1. Build the armature. Guards live inside; it refuses if "Armature" exists.
        result = alignArmatureFromDifeomorphicToManny()
        if result == {'CANCELLED'} or "Armature" not in bpy.data.objects:
            return {'CANCELLED'}
        vx_armature = bpy.data.objects["Armature"]

        # 2. Link the ARMATURE modifier (no parenting) so the exporter guard at
        #    exporter_unreal.py:421 is satisfied.
        bindMeshToArmature(mesh_object, vx_armature)

        # 3. Rename the vertex groups to match the bones, using the same map the armature
        #    builder used. This MUST come before the collapse: step 1 already renamed the
        #    bones, so until the groups catch up the two are in different name spaces and
        #    a rule targeting foot.L would find the bone but not the group.
        switchVertexGroupsToManny(mesh_object, vx_armature)

        # 4. Collapse the face rig into head / lowerJaw and the heel + metatarsals into
        #    the foot, then delete those bones and reparent the survivors.
        mergeBonesIntoTargets(mesh_object, vx_armature)

        # 5. Twist bones: take them out of the chain (Manny wants them as leaves), build
        #    both halves of each pair, and blend the weights across them.
        setupTwistBones(mesh_object, vx_armature)

        # Leave the mesh selected and pointed at by the selector, ready to export.
        if bpy.context.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        mesh_object.select = True
        bpy.context.scene.objects.active = mesh_object

        self.report({'INFO'}, "Manny conversion complete - see the console for the report")
        return {'FINISHED'}


class MESH_OT_Switch_To_Manny_Vertex_Groups(bpy.types.Operator):
    ''''''
    bl_idname = "vxmod.switch_to_manny_vertex_groups"
    bl_label = ""
    bl_description = "Rename Daz vertex groups to Manny names matching the Manny armature"
    bl_options = {'UNDO'}

    def execute(self, context):
        scene = bpy.context.scene
        vxmod = scene.vxmod
        mesh_name = vxmod.exportable_mesh
        if not mesh_name or mesh_name not in bpy.data.objects:
            ShowMessageBox("Pick the body mesh in the VXMod mesh selector first.",
                           "Error", 'ERROR')
            return {'CANCELLED'}
        mesh_object = bpy.data.objects[mesh_name]

        vx_armature = None
        for mod in mesh_object.modifiers:
            if mod.type == 'ARMATURE':
                vx_armature = mod.object
                break

        switchVertexGroupsToManny(mesh_object, vx_armature)
        return {'FINISHED'}


class CONVERT_OT_G3F_Body_Difeomorphic(bpy.types.Operator):
    ''''''
    bl_idname = "vxmod.convert_g3fdifeo_to_vxmodf"
    bl_label = ""
    bl_description = "Convert a Difeomorphic G3F body into a VXMod body"    
    def execute(self, context):
        obj_object = bpy.context.selected_objects[0] ####<--Fix
        bpy.context.scene.objects.active = obj_object
        print('Imported name: ', obj_object.name)        
        convertG3FDifeomorphicToVXModFBody()
        return {'FINISHED'}




class ARMATURE_OT_VXMod_Friendly_IK(bpy.types.Operator):
    ''''''
    bl_idname = "vxmod.armature_make_friendly_ik_joints"
    bl_label = ""
    bl_description = "Make armature bones to be friendly/maximum compatibility with IK systems. For example straight legs."
    def execute(self, context):
        scene  = bpy.context.scene
        #vxmod  = scene.vxmod
        armatureMakeFriendlyIKJoints(bpy.data.objects['Armature'])
        return {'FINISHED'}        



class ARMATURE_OT_Adjust_G3F_Rig_Difeomorphic(bpy.types.Operator):
    ''''''
    bl_idname = "vxmod.armature_adjust_rig_to_shape"
    bl_label = ""
    bl_description = "Adjust object rig \"Armature\" to a Difeomorphic imported armature/body"    
    def execute(self, context):
        #obj_object = bpy.context.selected_objects[0] ####<--Fix
        #bpy.context.scene.objects.active = obj_object
        #print('Imported name: ', obj_object.name)        
        alignArmatureToDifeomorphic()
        #extractSpecificBonesFromG3FArmatureFastVersion
        #
        fixFingersJointEndsDifeomorphic("Armature")
        fixToesJointEndsDifeomorphic("Armature")
        #
        fixJointsUsedAsEffectors("Armature")
        fixHeadJointsDifeomorphic("Armature")
        fixSpineJointsDifeomorphic("Armature")
        bpy.ops.object.mode_set(mode='OBJECT')
        isCompatibleBody = check_vertices_count_of_the_body("Genesis 3 Female Mesh",17418)
        if isCompatibleBody:
            print("body is compatible")
            ShowMessageBox("Body vertex count is OK, need to abort", "Warning", 'INFO')
        else:
            ShowMessageBox("Body vertex count is not matching, need to abort", "Warning", 'INFO')
        return {'FINISHED'}

class MESH_OT_Switch_To_VX_Vertex_Groups(bpy.types.Operator):
    ''''''
    bl_idname = "vxmod.switch_to_vxmod_vertex_groups"
    bl_label = ""
    bl_description = "Convert vertex groups from Daz to VX"    
    def execute(self, context):
        '''
        toe_deform01_joint01_L = {
            "toe_deform01_joint01.L" : ["lBigToe", "lBigToe_2"]
        }
        toe_deform01_joint01_R = {
            "toe_deform01_joint01.R" : ["rBigToe", "rBigToe_2"]
        }  
        toe_deform02_joint01_L = {
            "toe_deform02_joint01.L" : ["lSmallToe1", "lSmallToe2", "lSmallToe3", "lSmallToe4", "lSmallToe1_2", "lSmallToe2_2", "lSmallToe3_2", "lSmallToe4_2"]
        }   
        toe_deform02_joint01_R = {
            "toe_deform02_joint01.R" : ["rSmallToe1", "rSmallToe2", "rSmallToe3", "rSmallToe4", "rSmallToe1_2", "rSmallToe2_2", "rSmallToe3_2", "rSmallToe4_2"]
        } 
        '''

        '''ball_joint_L = {
            "ball_joint.L" : [ "lMetatarsals"]
        }
        ball_joint_R = {
            "ball_joint.R" : [ "rMetatarsals"]
        }  '''      
        '''ball_joint_L = {
            "ball_joint.L" : [ "lMetatarsals","lBigToe","lSmallToe1", "lSmallToe2", "lSmallToe3", "lSmallToe4"]
        }
        ball_joint_R = {
            "ball_joint.R" : [ "rMetatarsals","rBigToe","rSmallToe1", "rSmallToe2", "rSmallToe3", "rSmallToe4"]
        } '''

        head = {
            "head": ['head', 'upperTeeth', 'lowerJaw', 'lEye', 'rEye', 'lEar', 'rEar','rBrowInner', 'rBrowMid', 'rBrowOuter', 'lBrowInner', 'lBrowMid', 'lBrowOuter', 'CenterBrow', 'MidNoseBridge', 'lEyelidInner', 'lEyelidUpperInner', 'lEyelidUpper', 'lEyelidUpperOuter', 'lEyelidOuter', 'lEyelidLowerOuter', 'lEyelidLower', 'lEyelidLowerInner', 'rEyelidInner', 'rEyelidUpperInner', 'rEyelidUpper', 'rEyelidUpperOuter', 'rEyelidOuter', 'rEyelidLowerOuter', 'rEyelidLower', 'rEyelidLowerInner', 'lSquintInner', 'lSquintOuter', 'rSquintInner', 'rSquintOuter', 'lCheekUpper', 'rCheekUpper', 'Nose', 'lNostril', 'rNostril', 'lLipBelowNose', 'rLipBelowNose', 'lLipUpperOuter', 'lLipUpperInner', 'LipUpperMiddle', 'rLipUpperInner', 'rLipUpperOuter', 'lLipNasolabialCrease', 'rLipNasolabialCrease', 'lNasolabialUpper', 'rNasolabialUpper', 'lNasolabialMiddle', 'rNasolabialMiddle', 'tongue01', 'lNasolabialLower', 'rNasolabialLower', 'lNasolabialMouthCorner', 'rNasolabialMouthCorner', 'lLipCorner', 'lLipLowerOuter', 'lLipLowerInner', 'LipLowerMiddle', 'rLipLowerInner', 'rLipLowerOuter', 'rLipCorner', 'LipBelow', 'Chin', 'lCheekLower', 'rCheekLower', 'BelowJaw', 'lJawClench', 'rJawClench']
        }




        '''
        genesis3Toes = {
            "lFoot" : ["lMetatarsals"],
            "rFoot" : ["rMetatarsals"],
            "lToe" : ["lBigToe", "lSmallToe1", "lSmallToe2", "lSmallToe3", "lSmallToe4", "lBigToe_2", "lSmallToe1_2", "lSmallToe2_2", "lSmallToe3_2", "lSmallToe4_2"],
            "rToe" : ["rBigToe", "rSmallToe1", "rSmallToe2", "rSmallToe3", "rSmallToe4", "rBigToe_2", "rSmallToe1_2", "rSmallToe2_2", "rSmallToe3_2", "rSmallToe4_2"]
        } 
        '''       
        obj_object = bpy.context.selected_objects[0] ####<--Fix
        bpy.context.scene.objects.active = obj_object
        #mergeSubgroupsIntoGroup(obj_object, toe_deform01_joint01_L)
        #mergeSubgroupsIntoGroup(obj_object, toe_deform01_joint01_R)
        #mergeSubgroupsIntoGroup(obj_object, toe_deform02_joint01_L)
        #mergeSubgroupsIntoGroup(obj_object, toe_deform02_joint01_R)
        #
        #mergeSubgroupsIntoGroup(obj_object, ball_joint_L) 
        #mergeSubgroupsIntoGroup(obj_object, ball_joint_R) 
        #
        foot_L = {
            "foot.L" : [ "lFoot","lHeel","lMetatarsals"]
        }
        foot_R = {
            "foot.R" : [ "rFoot","rHeel","rMetatarsals"]
        }
        mergeSubgroupsIntoGroup(obj_object, foot_L)
        mergeSubgroupsIntoGroup(obj_object, foot_R)
        #mergeSubgroupsIntoGroup(obj_object, thigh_L)
        #mergeSubgroupsIntoGroup(obj_object, thigh_R)
        #mergeSubgroupsIntoGroup(obj_object, upperarm_L)
        #mergeSubgroupsIntoGroup(obj_object, upperarm_R)
        mergeSubgroupsIntoGroup(obj_object, head)
        #
        head_weights_matching = [
        ["head", "head", "head"],
        ["Chin", "Chin", "chin_joint01"],
        ["LipBelow", "BelowJaw", "lower_jaw_end"],
        ["lowerJaw","lJawClench","rJawClench","lower_jaw_joint01"],
        ["Nose","MidNoseBridge","lNostril","rNostril","nose_joint02"],
        ["lNasolabialUpper","lNasolabialMiddle","lCheekUpper","lCheekLower","cheek_joint01.L"],
        ["rNasolabialUpper","rNasolabialMiddle","rCheekUpper","rCheekLower","cheek_joint01.R"],
        ["rNasolabialLower","lower_lip_joint01.R"],
        ["lNasolabialLower","lower_lip_joint01.L"],
        ["lLipCorner","lLipLowerOuter","lower_lip_joint02.L"],
        ["rLipCorner","rLipLowerOuter","lower_lip_joint02.R"],
        ["lLipLowerInner","lower_lip_joint03.L"],
        ["rLipLowerInner","lower_lip_joint03.R"],
        ["LipLowerMiddle","lower_lip_end.L"],
        ["LipLowerMiddle","lower_lip_end.R"],
        ["lNasolabialMiddle","upper_lip_joint01.L"],
        ["rNasolabialMiddle","upper_lip_joint01.R"],
        ["lLipUpperOuter","lLipNasolabialCrease","upper_lip_joint02.L"],
        ["rLipUpperOuter","rLipNasolabialCrease","upper_lip_joint02.R"],
        ["lLipBelowNose","lLipUpperInner","upper_lip_joint03.L"],
        ["rLipBelowNose","rLipUpperInner","upper_lip_joint03.R"],
        ["LipUpperMiddle","upper_lip_end.L"],
        ["LipUpperMiddle","upper_lip_end.R"],
        ["lBrowInner","eye_brow_joint01.L"],
        ["rBrowInner","eye_brow_joint01.R"],
        ["lBrowMid","eye_brow_joint02.L"],
        ["rBrowMid","eye_brow_joint02.R"],
        ["lBrowOuter","eye_brow_end.L"],
        ["rBrowOuter","eye_brow_end.R"],
        ["CenterBrow","forehead_end"],
        ["lEar","ear_joint01.L"],
        ["rEar","ear_joint01.R"]
        ]        
        for row in head_weights_matching:
            param = {row[-1]:row[:-1]} #row[-1] - get last element (vx bone)   ------   row[:-1] returns the list without the last element (daz bones)
            mergeSubgroupsIntoGroup(obj_object, param)  
        #
        '''
        #obj_object = bpy.context.active_object
        modifierVertexWeightMixL = obj_object.modifiers.new("modifierVertexWeightMixL", type='VERTEX_WEIGHT_MIX')
        modifierVertexWeightMixL.vertex_group_a = "ball_joint.L"
        modifierVertexWeightMixL.vertex_group_b = "ankle_joint.L"
        modifierVertexWeightMixL.mix_mode = 'SUB'
        modifierVertexWeightMixL.mix_set = 'A'
        bpy.ops.object.modifier_apply(modifier="customVertexWeightMix")
        #         
        modifierVertexWeightMixR = obj_object.modifiers.new("modifierVertexWeightMixR", type='VERTEX_WEIGHT_MIX')
        modifierVertexWeightMixR.vertex_group_a = "ball_joint.R"
        modifierVertexWeightMixR.vertex_group_b = "ankle_joint.R"
        modifierVertexWeightMixR.mix_mode = 'SUB'
        modifierVertexWeightMixR.mix_set = 'A'
        bpy.ops.object.modifier_apply(modifier="customVertexWeightMix")        
        '''
        #
        #
        for row in spine_weights_matching + leg_weights_matching + toes_weights_matching + hand_weights_matching:
            firstName= row[0]
            secondName= row[1]
            newName= row[2]
            print("Renaming vertex group {0} into {1}".format(firstName,newName))
            if firstName == secondName:
                renameVertexGroup(obj_object, firstName, newName)
        #
        #
        #for row in spine_weights_matching + leg_weights_matching + hand_weights_matching:
        #    vertexGroupForDelete = row[0] 
        #    deleteVertexGroup(obj_object, vertexGroupForDelete) 
        #      
        for row in breast_weights_matching:
            firstName= row[0]
            secondName= row[1]
            newName= row[2]
            print("Renaming vertex group {0} into {1}".format(firstName,newName))
            if firstName == secondName:
                renameVertexGroup(obj_object, firstName, newName)
        #
        #add any missing vertex groups
        nipple_vertex_groups = ['breast_nipple_joint.L','breast_nipple_joint.R']
        breast_vertex_groups = ["breast_top_joint.L","breast_bottom_joint.L","breast_inner_joint.L","breast_outer_joint.L", "breast_top_joint.R","breast_bottom_joint.R","breast_inner_joint.R","breast_outer_joint.R"]
        for group in nipple_vertex_groups + breast_vertex_groups:
            if group in obj_object.vertex_groups.keys():
                pass
            else:
                vg = obj_object.vertex_groups.new(group)
        #    
        for vi in nipple_transfer_10_L:              
            move_vertex_weights_between_groups(obj_object,vi,"breast_joint.L","breast_nipple_joint.L",10)
        for vi in nipple_transfer_35_L:              
            move_vertex_weights_between_groups(obj_object,vi,"breast_joint.L","breast_nipple_joint.L",35)
        for vi in nipple_transfer_55_L:              
            move_vertex_weights_between_groups(obj_object,vi,"breast_joint.L","breast_nipple_joint.L",55)
        for vi in nipple_transfer_75_L:              
            move_vertex_weights_between_groups(obj_object,vi,"breast_joint.L","breast_nipple_joint.L",75)
        for vi in nipple_transfer_100_L:              
            move_vertex_weights_between_groups(obj_object,vi,"breast_joint.L","breast_nipple_joint.L",100)
        #
        vi_processed = []
        for vi in breastTop_L+breastBottom_L+breastInner_L+breastOuter_L:
            if vi in vi_processed:
                continue
            target_groups=[]
            if vi in breastTop_L:
                target_groups.append("breast_top_joint.L")
            if vi in breastBottom_L:
                target_groups.append("breast_bottom_joint.L")
            if vi in breastInner_L:
                target_groups.append("breast_inner_joint.L")
            if vi in breastOuter_L:
                target_groups.append("breast_outer_joint.L")                                                            
            split_vertex_weights_between_multiple_groups(obj_object,vi,"breast_joint.L",target_groups,50)
            vi_processed.append(vi)
        #
        vi_processed = []
        for vi in breastTop_R+breastBottom_R+breastInner_R+breastOuter_R:
            if vi in vi_processed:
                continue
            target_groups=[]
            if vi in breastTop_R:
                target_groups.append("breast_top_joint.R")
            if vi in breastBottom_R:
                target_groups.append("breast_bottom_joint.R")
            if vi in breastInner_R:
                target_groups.append("breast_inner_joint.R")
            if vi in breastOuter_R:
                target_groups.append("breast_outer_joint.R")                                                            
            split_vertex_weights_between_multiple_groups(obj_object,vi,"breast_joint.R",target_groups,50)
            vi_processed.append(vi)
        #
        for vi in nipple_transfer_10_R:              
            move_vertex_weights_between_groups(obj_object,vi,"breast_joint.R","breast_nipple_joint.R",10)
        for vi in nipple_transfer_35_R:              
            move_vertex_weights_between_groups(obj_object,vi,"breast_joint.R","breast_nipple_joint.R",35)
        for vi in nipple_transfer_55_R:              
            move_vertex_weights_between_groups(obj_object,vi,"breast_joint.R","breast_nipple_joint.R",55)
        for vi in nipple_transfer_75_R:              
            move_vertex_weights_between_groups(obj_object,vi,"breast_joint.R","breast_nipple_joint.R",75)
        for vi in nipple_transfer_100_R:              
            move_vertex_weights_between_groups(obj_object,vi,"breast_joint.R","breast_nipple_joint.R",100)        
        #
        print("Cleanup leftover vertex groups...")
        for vg in vertexGroupsForRemoval:
            deleteVertexGroup(obj_object, vg)
        #mergeSubgroupsIntoGroup(obj_object, genesis3Toes)

        #add any missing vertex groups
        all_vertex_groups = ['base',
                             'spine_01', 'spine_02', 'spine_03', 'spine_04', 'spine_05',
                             'neck_01', 'neck_02',
                             'head',
                             'lower_jaw_joint01', 'lower_jaw_end',
                             'chin_joint01', 'chin_end',
                             'lower_lip_joint01.R', 'lower_lip_joint02.R', 'lower_lip_joint03.R', 'lower_lip_end.R',
                             'lower_lip_joint01.L', 'lower_lip_joint02.L', 'lower_lip_joint03.L', 'lower_lip_end.L',
                             'upper_lip_joint01.L', 'upper_lip_joint02.L', 'upper_lip_joint03.L', 'upper_lip_end.L',
                             'upper_lip_joint01.R', 'upper_lip_joint02.R', 'upper_lip_joint03.R', 'upper_lip_end.R',
                             'eye_socket_joint.L', 'eye_joint.L', 'eye_brow_joint01.L', 'eye_brow_joint02.L', 'eye_brow_end.L', 'eye_socket_joint.R', 'eye_joint.R', 'eye_brow_joint01.R', 'eye_brow_joint02.R', 'eye_brow_end.R',
                             'nose_joint01', 'nose_joint02', 'nose_end',
                             'forehead_joint01', 'forehead_end',
                             'cheek_joint01.L', 'cheek_end.L', 'cheek_joint01.R', 'cheek_end.R',
                             'ear_joint01.L', 'ear_end.L', 'ear_joint01.R', 'ear_end.R',
                             'head_end',
                             'clavicle.L', 'upperarm.L', 'upperarm_twist_01.L', 'upperarm_twist_02.L', 'lowerarm.L', 'lowerarm_twist_01.L', 'lowerarm_twist_02.L', 'hand.L',
                             'thumb_01.L', 'thumb_02.L', 'thumb_03.L', 'thumb_end.L', 'index_metacarpal.L', 'index_01.L', 'index_02.L', 'index_03.L', 'index_end.L', 'middle_metacarpal.L', 'middle_01.L', 'middle_02.L', 'middle_03.L', 'middle_end.L', 'ring_metacarpal.L', 'ring_01.L', 'ring_02.L', 'ring_03.L', 'ring_end.L', 'pinky_metacarpal.L', 'pinky_01.L', 'pinky_02.L', 'pinky_03.L', 'pinky_end.L',
                             'clavicle.R', 'upperarm.R', 'upperarm_twist_01.R', 'upperarm_twist_02.R', 'lowerarm.R', 'lowerarm_twist_01.R', 'lowerarm_twist_02.R', 'hand.R',
                             'thumb_01.R', 'thumb_02.R', 'thumb_03.R', 'thumb_end.R', 'index_metacarpal.R', 'index_01.R', 'index_02.R', 'index_03.R', 'index_end.R', 'middle_metacarpal.R', 'middle_01.R', 'middle_02.R', 'middle_03.R', 'middle_end.R', 'ring_metacarpal.R', 'ring_01.R', 'ring_02.R', 'ring_03.R', 'ring_end.R', 'pinky_metacarpal.R', 'pinky_01.R', 'pinky_02.R', 'pinky_03.R', 'pinky_end.R',
                             'breast_joint.L', 'breast_scale_joint.L', 'nipple_joint01.L', 'nipple_end.L',
                             'breast_joint.R', 'breast_scale_joint.R', 'nipple_joint01.R', 'nipple_end.R',
                             'rib_joint01.L', 'rib_end.L', 'rib_joint01.R', 'rib_end.R',
                             'stomach_joint01', 'stomach_end',
                             'thigh.L', 'thigh_twist_01.L', 'thigh_twist_02.L', 'calf.L', 'foot.L', 'ball.L',
                             'thigh.R', 'thigh_twist_01.R', 'thigh_twist_02.R', 'calf.R', 'foot.R', 'ball.R',
                             'penis_joint01', 'penis_joint02', 'penis_joint03', 'penis_end',
                             'testicles_joint01', 'testicles_joint02', 'testicles_end',
                             'vagina_joint01.L', 'vagina_joint01.R', 'vagina_end.L', 'vagina_end.R',
                             'butt_joint01.L', 'butt_end.L', 'butt_joint01.R', 'butt_end.R',
                             'anus_joint'
                            ]
        for group in all_vertex_groups:
            if group in obj_object.vertex_groups.keys():
                pass
            else:
                vg = obj_object.vertex_groups.new(group)

        return {'FINISHED'}



# this class extends ImportHelper !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
class IMPORT_OT_Import_G3F_Body(Operator, ImportHelper):
    ''''''
    bl_idname = "test.import_g3f_body"
    bl_label = "Pick Obj file"
    bl_description = "Import G3F body from obj file"

    filter_glob = StringProperty(
        default='*.obj',
        options={'HIDDEN'}
    )
    extra_processing = BoolProperty(
        name='Process object after import',
        description='Fix materials, UV name, add vertex groups, add shapes, and other fixes',
        default=True
    )
    
    def execute(self, context):
        bpy.context.scene.objects.active = None
        for obj in bpy.data.objects:
            obj.select = False        
        bpy.ops.object.select_all(action='DESELECT')
        print('Selected file:', self.filepath)
        path_to_file = self.filepath
        print('Extra Processing:', self.extra_processing)
        bpy.ops.import_scene.obj(filepath = path_to_file,split_mode='OFF')
        obj_object = bpy.context.selected_objects[0] ####<--Fix
        bpy.context.scene.objects.active = obj_object
        print('Imported name: ', obj_object.name)        
        import_g3f()
        return {'FINISHED'}
    
# when implemented this class should extend ImportHelper !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
class IMPORT_OT_Import_G3F_Morph(Operator, ImportHelper):
    ''''''
    bl_idname = "vxmod.import_g3f_morph"
    bl_label = "Pick Obj file"
    bl_description = "Import G3F morph body from obj file"
    
    filter_glob = StringProperty(
        default='*.obj',
        options={'HIDDEN'}
    )
    extra_processing = BoolProperty(
        name='Process object after import',
        description='Fix materials, UV name, add vertex groups, add shapes, and other fixes',
        default=True
    )
    
    def execute(self, context):
        base_body_mesh = None
        if (bpy.context.scene.objects.active != None):
            if (bpy.context.scene.objects.active.select == True):
                base_body_mesh = bpy.context.scene.objects.active
        bpy.context.scene.objects.active = None
        for obj in bpy.data.objects:
            obj.select = False        
        bpy.ops.object.select_all(action='DESELECT')
        print('Selected file:', self.filepath)
        path_to_file = self.filepath
        print('Extra Processing:', self.extra_processing)
        encoding = 'utf-8'
        pattern ='usemtl\\s*.*\\n'
        matched = re.compile(pattern).search
        with open(path_to_file, encoding=encoding) as input_file:
            with NamedTemporaryFile(mode='w', encoding=encoding,suffix='.obj', dir=os.path.dirname(path_to_file), delete=False) as outfile:
                for line in input_file:
                    if not matched(line):
                        print(line, end='', file=outfile)
                outfile.close()
                bpy.ops.import_scene.obj(filepath = outfile.name,split_mode='OFF')
                morph_object = bpy.context.selected_objects[0] ####<--Fix
                bpy.context.scene.objects.active = morph_object
                head, tail = os.path.split(path_to_file)
                new_morph_name = os.path.splitext(tail)[0]
                morph_object.name = new_morph_name
                print('Imported name: ', morph_object.name)    
                import_g3f_morph(base_body_mesh, morph_object)
                os.remove(outfile.name)
        return {'FINISHED'}



@bpy.app.handlers.persistent
def post_ob_data_updated(scene):
    ob = scene.objects.active
    if ob is not None and ob.type=='ARMATURE' and ob.data.is_updated: #
        print (ob.type)
        print("%s - Armature Object data is_updated (post)" % ob.data.name)
        mode = ob.mode
        if mode=="EDIT":
            for eb in ob.data.edit_bones:
                pb = ob.pose.bones[eb.name]
                pb.dp_helper.shouldUpdate = False
                pb.dp_helper.roll = eb.roll
            for eb in ob.data.edit_bones:
                pb = ob.pose.bones[eb.name]
                pb.dp_helper.shouldUpdate = True


def update_active_mesh(scene):
    if not scene.vxmod.pin_exportable_mesh:
        obj = bpy.context.object
        if obj and obj.type == 'MESH':
            if scene.vxmod.exportable_mesh != obj.name:
                scene.vxmod.exportable_mesh = obj.name

@persistent
def addon_handler(scene):
    bpy.app.handlers.scene_update_post.remove(addon_handler)
    vxmod = bpy.data.scenes[0].vxmod
    #vxmod.updated = 0
    # todo
    #load_config('','')
    #bsLookupRead()
    return {'FINISHED'}

@persistent
def load_post_handler(dummyArg):
    load_config2('','')
    #load_config('','')
    #bsLookupRead()
    #return {'FINISHED'}
    
#bpy.app.handlers.load_post.append(load_post_handler)

def register_handlers():
    if update_active_mesh not in bpy.app.handlers.scene_update_post:
        bpy.app.handlers.scene_update_post.append(update_active_mesh)


def register() :
    global custom_icons
    custom_icons = bpy.utils.previews.new()
    script_path = os.path.realpath(__file__)
    directory = os.path.dirname(script_path)
    icons_dir = os.path.join(directory, "icons")
    custom_icons.load("matrix_icon", os.path.join(icons_dir, "matrix.png"), 'IMAGE')
    custom_icons.load("wand_icon", os.path.join(icons_dir, "auto-fix.png"), 'IMAGE')
    custom_icons.load("ik_arm_icon", os.path.join(icons_dir, "ik_arm.png"), 'IMAGE')
    #bpy.utils.register_class(VXMOD_panel)
    #
    #when there are many classes or a packages submodule has its own classes it can be tedious to list them all for registration. For more convenient loading bpy.utils.register_module (module)
    #Internally Blender collects subclasses on registrable types, storing them by the module in which they are defined. By passing the module name to bpy.utils.register_module Blender can register all classes created by this module and its submodules.
    bpy.utils.register_module(__name__)
    #bpy.types.PoseBone.hfg_bone=bpy.props.PointerProperty(type=hfg_bone_collection)
    bpy.types.Scene.vxmod = bpy.props.PointerProperty(type=VXMOD_vars)    
    vxmod = bpy.types.Scene.vxmod    
    #bpy.app.handlers.scene_update_post.append(addon_handler)
    register_handlers()

def unregister() :
    global custom_icons
    bpy.utils.previews.remove(custom_icons)
    del bpy.types.Scene.vxmod
    #del bpy.types.PoseBone.hfg_bone
    if update_active_mesh in bpy.app.handlers.scene_update_post:
        bpy.app.handlers.scene_update_post.remove(update_active_mesh)
    bpy.app.handlers.scene_update_post.clear()
    #when there are many classes or a packages submodule has its own classes it can be tedious to list them all for un-registration. For more convenient loading bpy.utils.unregister_module (module)
    #Internally Blender collects subclasses on registrable types, storing them by the module in which they are defined. By passing the module name to bpy.utils.register_module Blender can register all classes created by this module and its submodules.
    bpy.utils.unregister_module(__name__)  

if __name__ == "__main__":
    register()
#
#https://gist.github.com/tin2tin/ce4696795ad918448dfbad56668ed4d5
#https://sinestesia.co/blog/tutorials/using-uilists-in-blender/