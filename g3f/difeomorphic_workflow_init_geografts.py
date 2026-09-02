import bpy

# Geograft profiles for G3F.
#
# Geografts are figure-specific by construction - Diffeomorphic only accepts one whose
# DazVertexCount matches the body's vertex count - so this table lives under g3f/ with
# the rest of the per-figure data.
#
# Keyed by the geograft's FIGURE name - the bare Daz name, with no ".NNN" suffix.
#
# A geograft is imported as a figure in its own right, so it arrives as TWO objects: an
# ARMATURE holding the bare name, and its child MESH. The armature claims the name first,
# so the mesh is always left with a suffix ("Genesis 3 Female Genitalia.001"). The mesh is
# the object the conversion clones and renames, so every lookup runs its name through
# normalizeObjectName first - key these entries on the bare figure name, never on what
# you see on the mesh object in the outliner.
#
#   order         sort key deciding the geograft_<N>_ number. Lower goes first.
#                 Only the relative values matter; N itself is assigned sequentially
#                 from the sorted result, so gaps here are fine.
#   short_name    what follows the prefix, e.g. "genz" -> geograft_0_genz. This is the
#                 fragment that ends up in the exported merged mesh name (Belle_genz),
#                 so it should be short and stable.
#   material_role key into the per-mode material name table in
#                 importer_g3f_difeomorphic (LEGACY_MATERIAL_NAMES /
#                 MODERN_MATERIAL_NAMES). The geograft's own material slots are dropped
#                 and replaced with that one. OMIT the key to leave the geograft's
#                 materials untouched - which is the right default for anything that is
#                 not genitalia: a tail or wings have their own textures worth keeping.
#
# A geograft with NO entry here is still found, cloned, parented and renamed. It just
# gets a sanitized version of its object name as short_name, sorts after every known
# geograft, and keeps its own materials. Nothing needs an entry to work; entries exist
# to pin the order and give a nicer short name.


# ---------------------------------------------------------------------------
# ORDER: Diffeomorphic does NOT record the order geografts were applied in Daz.
#
# Verified by enumerating every property import_daz registers: on Mesh it is
# DazRigidityGroups / DazGraftGroup / DazMaskGroup / DazVertexCount / DazMaterialSets /
# DazHDMaterials, and on Object DazId / DazUrl / DazMesh / DazRig / DazScale and friends.
# All identity and geometry - none of them an index or a sequence.
#
# So the order here is OURS to define, and the requirement is not fidelity to some Daz
# application order but DETERMINISM: exporter_unreal builds the merged mesh name from
# the geograft order (Belle_genz), and that name is the prefix of the subdivision JSON
# files VersaMap reads on the Unreal side. If the order moves between runs, the exported
# filenames move with it.
#
# Scene order is not usable as a substitute - bpy.data.objects is name-sorted, and any
# delete / re-add reshuffles the rest.
# ---------------------------------------------------------------------------

# Geografts with no entry sort after every known one, then alphabetically among
# themselves, so adding an unlisted geograft never renumbers the listed ones.
GEOGRAFT_UNKNOWN_ORDER = 10000


geograft_profiles = {
    "Genesis 3 Female Genitalia": {
        "order": 0,
        "short_name": "genz",
        "material_role": "genital",
    },
}
