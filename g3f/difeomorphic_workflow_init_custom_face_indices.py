import bpy

# Custom FACE (polygon) indices for G3F.
#
# Same role and same rule as difeomorphic_workflow_init_custom_vertex_indices.py: an
# index never appears at a call site, it lives here under a name, so implementing G3M /
# G8F / G9 later is a module swap rather than a hunt through the conversion code.
#
# Kept in its OWN module rather than added to the vertex file, because these are
# polygon indices and mixing the two index spaces in one namespace is exactly the kind
# of thing that reads fine and then silently indexes the wrong array.
#
# Face indices are valid against the STOCK Diffeomorphic G3F body topology, as it stands
# during "G3F -> VX body". Nothing in that conversion deletes geometry - the material work
# only remaps polygon material_index and prunes slots - so the clone keeps the source
# polygon order and these indices stay meaningful all the way through.
#
# They are NOT valid after the geograft merge (diffeomorphic_merge_geografts.py), which
# joins meshes and therefore renumbers polygons.


# ---------------------------------------------------------------------------
# Censor faces - DERIVED, not tabulated
#
# The censor region is read from each geograft's own DazMaskGroup: Daz's list of
# base-mesh faces to hide when that graft is applied. That IS the region to censor, and
# it ships with the geograft, so nothing has to be collected by hand.
#
# Verified 2026-09-03 against the G3F genitalia: DazMaskGroup returned exactly the 82
# indices that had been hand-collected for it - same count, same values, empty diff both
# ways. The hardcoded array is therefore gone; recover it from git (commit 3b18dc7) if a
# geograft ever needs one written out.
#
# Consequence: a tail, wings, vampire teeth or any future geograft masks its own footprint
# with no entry to write here.
#
# This dict survives only as an OVERRIDE, for a geograft whose DazMaskGroup is not the
# region you actually want censored - too small, too large, or a graft you want masked
# differently from how Daz hides it. Keyed like every other geograft table: by the bare
# FIGURE name, matched by prefix, so the ".NNN" the mesh object carries does not matter.
#
# An entry here WINS over DazMaskGroup. Add one only to deviate deliberately.
# ---------------------------------------------------------------------------

censor_faces_by_geograft = {
}
