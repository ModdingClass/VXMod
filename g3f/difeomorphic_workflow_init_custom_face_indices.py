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
# These are valid against the STOCK Diffeomorphic G3F body topology, as it stands during
# "G3F -> VX body". Nothing in that conversion deletes geometry - the material work only
# remaps polygon material_index and prunes slots - so the clone keeps the source
# polygon order and these indices stay meaningful all the way through.
#
# They are NOT valid after the geograft merge (diffeomorphic_merge_geografts.py), which
# joins meshes and therefore renumbers polygons.


# ---------------------------------------------------------------------------
# Censor faces - PER GEOGRAFT
#
# These live on the BODY mesh, but which faces belong to the censor region is decided by
# the geograft that gets merged in later: the region has to cover the graft's footprint
# and the body around it, so a different geograft implies a different set. An array here
# is therefore only meaningful paired with one specific geograft.
#
# Keyed by the geograft's OBJECT NAME, which is what the conversion has in hand -
# importer_g3f_difeomorphic looks the geograft up by exact object name.
#
# Adding a geograft means TWO edits, and they are in different files:
#   1. a new array + registry entry here
#   2. the lookup in convertG3FDifeomorphicToVXModFBody, which currently hardcodes
#      "Genesis 3 Female Genitalia" as the only geograft it searches for
# Doing only (1) leaves the new array unreachable.
#
# No entry for a geograft means NO censor faces are assigned. The material slot is still
# created - empty - so the Unreal side keeps its guarantee that the slot exists.
# ---------------------------------------------------------------------------

# The stock Daz G3F genitalia geograft.
censor_faces_genesis_3_female_genitalia = [
    8658, 8659, 8660, 8661, 8704, 9169, 9246, 9254, 9376, 9377,
    9380, 9381, 9767, 9768, 9769, 9770, 9803, 9804, 9805, 9806,
    9807, 9808, 9809, 9810, 9811, 9812, 9813, 9814, 9816, 9821,
    9824, 9940, 9941, 9942, 9943, 9944, 9945, 9946, 9947, 9948,
    9949, 10067, 10068, 10069, 10070, 10113, 10578, 10655, 10663, 10785,
    10786, 10789, 10790, 11176, 11177, 11178, 11179, 11212, 11213, 11214,
    11215, 11216, 11217, 11218, 11219, 11220, 11221, 11222, 11223, 11225,
    11230, 11233, 11349, 11350, 11351, 11352, 11353, 11354, 11355, 11356,
    11357, 11358,
]


# Geograft object name -> censor face indices on the body mesh.
censor_faces_by_geograft = {
    "Genesis 3 Female Genitalia": censor_faces_genesis_3_female_genitalia,
}
