# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**VXMod Workflow** is a Blender 2.79 addon (`io_vxmod_workflow`) for converting Daz3D Genesis 3 Female (G3F) bodies into Unreal Engine-compatible skeletal meshes. It handles armature conversion, vertex group remapping, shape key transfer, subdivision surface matching, and FBX export.

## Environment

- **Blender 2.79** (Python 3.5 bundled) — all code uses the Blender 2.79 Python API (`bpy`)
- The addon lives inside Blender's addons directory and is activated via Blender preferences
- No external build system, linting, or test suite exists — testing is done manually inside Blender
- Windows-only: uses `winsound` and `ctypes.wintypes` in some modules

## Architecture

### Entry Point
`__init__.py` — Registers all Blender operators, panels, and the `VXMOD_vars` PropertyGroup (stored as `scene.vxmod`). Uses `bpy.utils.register_module(__name__)` for bulk class registration. Module reloading uses `imp.reload()`.

### Core Pipeline (Daz → VXMod → Unreal)
1. **Import**: `importer_g3f.py` / `importer_g3f_morphs.py` — Import G3F OBJ files and morph targets
2. **Difeo Conversion**: `g3f/difeomorphic_workflow.py` + related `g3f/difeomorphic_workflow_*.py` — Convert Diffeomorphic-imported G3F armatures/meshes to VXMod format
3. **Armature Adjustment**: `g3f/script_autofix_armature_*.py` (numbered 0-9) — Executed sequentially via `exec(open(...).read())` in `__init__.py`'s `ARMATURE_OT_adjust_rig_to_shape` operator. These scripts calculate bone positions from vertex data.
4. **Vertex Group Remapping**: `__init__.py` `MESH_OT_Switch_To_VX_Vertex_Groups` operator — Maps Daz bone names to VXMod naming convention (e.g., `lShldrBend` → `shoulder_joint.L`)
5. **Export**: `exporter_unreal.py` (`export_to_unreal_v2()`) — Main export function producing FBX for Unreal. Handles geograft baking, subdivision, shape key transfer, and bone reorientation.

### Bone Naming Convention
- The project now uses **Manny UE5 bone names** throughout (rename completed 2026-03-31)
- Manny names: `thigh.L/R`, `calf.L/R`, `foot.L/R`, `ball.L/R`, `spine_01`–`spine_05`, `neck_01/02`, `head`, `upperarm.L/R`, `lowerarm.L/R`, `hand.L/R`, `clavicle.L/R`, plus twist variants `thigh_twist_01/02`, `upperarm_twist_01/02`, `lowerarm_twist_01/02`
- Fingers: `thumb_01/02/03`, `index/middle/ring/pinky_metacarpal`, `index/middle/ring/pinky_01/02/03`
- VXMod-specific extra bones (face, breasts, toes, etc.) keep their own `<part>_joint<NN>.<side>` format
- `utils.py` has `blendifyname()` (Daz→Blender `.L`/`.R` suffix) and `villafyname()` (Blender→VXMod `_L`/`_R` infix) — these utilities remain but the internal bone names are now Manny-style
- Joint end bones follow `<part>_end.<side>` pattern

### Key Modules
- `armature.py` — **Confirmed dead code** (legacy from io_tk_armature). None of its functions are called from the live plugin. Safe to delete along with its import at `__init__.py:113`.
- `ik_tools.py` — IK constraint setup (foot IK, high-heel pose IK, custom IK bones)
- `helper_vgroups.py` — Vertex group operations (merge, move weights, split weights between groups)
- `exporter_fake_bones.py` — Debug visualization bones
- `fjson.py` — Custom JSON serializer with controlled float formatting (used for skeleton export)
- `tools_import_export_*_json.py` — JSON import/export for vertex groups, shape keys, materials, edit bones
- `dictionary_g3f_vertices.py` — Hardcoded vertex index lists for G3F body regions (breasts, nipples, etc.)
- `dictionary_shapekeys.py` / `dictionary_materials.py` — Name mapping dictionaries
- `globals.py` — Shared state: `animSkeletonValuesExtra` (OrderedDict) and `sharedGlobals` class
- `configobj.py`, `six.py`, `angles.py` — Vendored third-party libraries (do not modify)

### G3F Subfolder (`g3f/`)
Contains the Diffeomorphic import workflow and autofix scripts. The `difeomorphic_workflow_armature_from_*.py` files hold vertex index dictionaries for computing bone positions from mesh vertices for different body regions (breasts, head, gens, other).

### UI Panels
All panels appear in the 3D View Tool Shelf under the "VXMod" tab category:
- `VXMOD_CONVERTER_OT_PanelDifeomorphicToVXMod` — Main conversion workflow
- `ARMATURE_OT_ConstraintsPanel` — IK and constraint tools
- `DebugBonesPanel` — Debug bone visibility
- `EXPORT_PT_VXModToUnreal` — Unreal export panel with mesh selector and export options

## Key Patterns

- Operators access shared settings via `bpy.context.scene.vxmod` (the `VXMOD_vars` PropertyGroup)
- The exportable mesh is tracked via an EnumProperty with a "pin" toggle to prevent auto-switching
- Export folder path is stored in `vxmod.exportFolderPathUnreal`
- G3F body compatibility is checked by vertex count (17418 for body-only, 18105 with gens)
- Subdivision vertex matching tables are built and saved as JSON to correlate base mesh vertices with subdivided mesh vertices — see "Subdivision Output Files" section below for full details

## Subdivision Output Files

Produced by `build_subdivision_vertex_matching_table()` in `exporter_unreal.py`.
All three files are written to `params.exportFolderPathUnreal` with the merged mesh name as prefix
(e.g. `Belle_genz` when geografts are merged).

### The Vertex Group Trick
Before subdividing, every vertex in the base mesh is assigned its own vertex group named after its
index (`"0"`, `"1"`, ..., `"18119"`). After subdivision, each new vertex inherits the groups of
its parent vertices — so the group membership reveals exactly which base vertices produced each
subdivided vertex. Group count indicates vertex type: 1 = base, 2 = edge, 4 = face.

---

### `{name}_vertex_groups_dict.json` — Simple base-index lookup
**Format:** `{"subdivIdx": "baseIdx1_baseIdx2_..."}` — string values, indices joined by underscores.

**Content:**
- Base vertices (indices 0..N-1): `"0": "0"` — maps to itself (one group = original vertex)
- Edge vertices: `"18120": "5006_5200"` — midpoint of 2 base vertices
- Face vertices: `"53865": "17881_17882_18039_18042"` — centroid of 4 base vertices

**Usage:** Compact reverse-lookup. Superseded by `_vertex_mapping_list.json` for Unreal (the list
contains all the same info plus explicit type field). Retained as a simpler debug reference.

---

### `{name}_vertex_mapping_list.json` — Rich per-vertex mapping (**used by Unreal**)
**Format:** JSON array, one object per subdivided vertex, written with inline arrays via `dumps_inline_arrays()`.

**Fields present on all entries:**
```json
{"index": 0, "type": "base", "base_indices": [0]}
```
- `index` — subdivided vertex index (redundant but used as authoritative key for non-ordered loading)
- `type` — `"base"` | `"edge"` | `"face"` | `"unknown"`
- `base_indices` — list of 1, 2, or 4 base mesh vertex indices

**Additional fields for `"base"` type:**
```json
"connected_base_neighbor_indices": [81, 3210, ...],
"connected_faces_base_indices": [[0, 3210, 10110, 10111], ...]
```

**Additional fields for `"edge"` type:**
```json
"adjacent_face_point_indices": [68523, 68524],
"adjacent_faces_base_indices": [[...4 base verts...], [...4 base verts...]]
```

**Unreal import:** VersaMap plugin embeds this file into the `.uasset` via `USubdivMappingData`
(dense `TArray<FSubdivVertEntry>`). Linked via FBX custom property:
`vxasset_hires["lookupVertexIdTable"] = mergedMeshesName + "_vertex_mapping_list.json"`
The plugin reads `FBX.mesh_LOD0.lookupVertexIdTable` (Legacy FBX) or
`INTERCHANGE.mesh_LOD0.lookupVertexIdTable` (Interchange) from package metadata.

**Morph propagation rule (in Unreal):**
- `base` → delta = base_delta[base_indices[0]] directly
- `edge` → delta = average of the 2 base vertex deltas
- `face` → delta = average of the 4 base vertex deltas (Catmull-Clark interpolation)

---

### `{name}_matching_index_dict.json` — Blender-internal use only
**Format:** `{"subdivIdx": subsurfIdx}` — flat int→int mapping, saved via `json.dump(OrderedDict)`.

**Purpose:** Maps each vertex in the **edit-mode-subdivide mesh** (`vxasset_from_editmode_subdivide_operator`)
to the corresponding vertex in the **subsurf-modifier mesh** (`vxasset_from_objmode_subsurf_modifier`).

**Why needed in Blender:** The two subdivision methods produce different vertex orderings. The
subsurf modifier produces better smoothing, so morphs/shape keys are authored on the subsurf mesh.
This dict is used to transfer shape key deltas from the subsurf mesh back to the edit-mode mesh
(which is the one exported to Unreal as the actual LOD0 asset).

**NOT needed in Unreal** — this mapping is Blender-pipeline-internal. Do not embed in `.uasset`.

---

## External Dependency: Diffeomorphic (`import_daz`) Addon

The import pipeline depends on the Diffeomorphic addon located at `E:\devtools\3D\blender-2.79b-windows64\2.79\scripts\addons\import_daz\`. This is a third-party addon (Thomas Larsson, BSD license) with its own maintainers — **do not modify it**. VXMod only reads the mesh/object properties it registers (`DazGraftGroup`, `DazMaskGroup`, `DazVertexCount`, `DazScale`).

### Geograft Merge Operators (in `diffeomorphic_merge_geografts.py`)

Three merge operators used to be hand-added to `import_daz/merge.py`. They are VXMod's code, so they live in VXMod: `import_daz` stays pristine (it has its own maintainers), a clean copy of it can be swapped in at any time, and the merge code stays ours to edit. Note the 2.79 branch of Diffeomorphic is effectively frozen — the project moved to newer Blender versions — so this is about ownership and cleanliness, not about surviving upstream updates.

They now live in this addon under the `vxmod.*` namespace, with all `import_daz` helpers (`getSceneObjects`, `getSelected`, `setSelected`, `activateObject`, `getUvTextures`, `updateDrivers`, `replaceNodeNames`, the shape key driver helpers, `MaterialMerger`, `DazOperator`) reimplemented locally for Blender 2.79. `merge_geografts_into_active()` walks this priority list:

1. `vxmod.merge_geografts_nondestructive_bmesh` — **Fast bmesh version**, the one actually used. Uses `bmesh.ops.weld_verts()` for single-operation vertex merging instead of per-pair mode switching. Also uses `bmesh` `vert.is_boundary` for O(1) boundary detection.
2. `vxmod.merge_geografts_nondestructive` — Non-destructive version (keeps original geometry faces). Slow due to per-vertex-pair OBJECT↔EDIT mode switching.
3. `vxmod.merge_geografts_fast` — Destructive version (deletes masked edges).
4. `daz.merge_geografts` — **Diffeomorphic's own operator**, called externally as the last fallback. Deliberately *not* cloned: it is their code and ships with their addon.

Provenance (from the git history of the `import_daz` repo): commit `1e1c109 "original"` contains only `daz.merge_geografts`; the other three were added later in `8bb70e0`, `cf4448b` and `2218025`. Note that `daz.merge_geografts` was itself modified in `6d5e59f` ("maintaining vertex index"), so an installed copy may differ from upstream — one more reason not to depend on its exact behavior.

`exporter_unreal.py` checks `geograft_data_available()` (tests for `bpy.types.Mesh.DazGraftGroup`) instead of probing for `daz.*` merge operators.

**Important**: never re-add merge operators to `import_daz/merge.py` — it has its own maintainers. Fixes belong in `diffeomorphic_merge_geografts.py`.

---

## Extra Bones Reference Data

Per-category JSON files for non-Manny extra bones live in:
`vx_extra_bones/` (relative to addon root)

Source armature: `F:\Assets\Daz3D\Projects\G3F_SI\custom_json_files\armature_vxnew_based_on_manny_with_extra_Bones.json`

| File | Category | Count |
|---|---|---|
| `extra_bones_toes.json` | Toes | 30 |
| `extra_bones_finger_ends.json` | Finger end caps | 10 |
| `extra_bones_breasts.json` | Breasts | 26 |
| `extra_bones_face_full.json` | Full face | 48 |
| `extra_bones_eyes.json` | Eye orbit + joint | 4 |
| `extra_bones_jaw.json` | Lower jaw + chin | 4 |
| `extra_bones_gens.json` | Genitalia | 12 |
| `extra_bones_butt.json` | Butt | 4 |
| `extra_bones_torso.json` | Ribs + stomach | 6 |
| `extra_bones_leg_extras.json` | Hip twist ends | 2 |

**Naming note:** `eye_socket_joint.L/R` was renamed to `eye_orbit.L/R` in both `extra_bones_eyes.json` and `extra_bones_face_full.json` to avoid confusion with Unreal Engine socket attachments.

---

## Material conversion modes (`G3F→VX body`)

`convertG3FDifeomorphicToVXModFBody(material_mode='FULLBODY')` in
`g3f/importer_g3f_difeomorphic.py`. The mode comes from `vxmod.materialConversionMode`,
an `EnumProperty` rendered `expand=True` under the label **"Convert Materials
Pipeline:"**, directly beneath the `G3F→VX body` button in step 1 of the panel.

`FULLBODY` is the default in **both** places — the property and the function signature —
so "the default" means one thing. `LEGACY` is still the fallback for an *unrecognised*
mode string, which is a separate concern from being the default.

Like the pectoral options, this is a **build option** — changing it after a conversion
does nothing until the next run.

| Mode | What it does |
|------|--------------|
| `DAZ` | Nothing. Stock Daz surfaces stay exactly as imported. They are still **copied** first (that step is shared), so the originals on the Difeomorphic body are never touched. |
| `LEGACY` | The original conversion, unchanged — collapse onto the 21 `body_*` names, pad the table, sort slots into legacy engine index order. |
| `FULLBODY` | Everything onto `mat_fullbody`, with two exceptions. **Default.** |

### FullBody exceptions

1. **Eyelashes** keep `body_eyelash01` — they need a translucent material in Unreal and
   cannot share a slot with opaque skin.
2. **Eye interior** (`Cornea`, `Pupils`, `Sclera`, `Irises`, `EyeMoisture`) goes to a
   material named `DONT_RENDER`, so Unreal can skip it outright.

See "Material names, per mode" below — FullBody's targets are `mat_fullbody` and
`mat_eyelashes`, not the `body_*` names LEGACY uses. This is the one real
   behavioural split from LEGACY, which instead folds the eye interior into
   `body_head01` and relies on it ending up hidden inside the skull.

### Material names carry TWO suffixes — never compare naively

This bites any comparison against a bare Daz surface name.

| Source | Suffix | Example |
|---|---|---|
| Diffeomorphic import | `-N` on **every** surface | `Eyelashes` → `Eyelashes-1` |
| Blender datablock collision | `.NNN` | `Eyelashes-1` → `Eyelashes-1.001` |

The `.NNN` is not hypothetical — the conversion's own material *copy* step (which exists
so the stock Difeomorphic materials are not overwritten) triggers it on every slot. So by
the time any matching runs, a slot is typically named `Eyelashes-1.001`.

`normalizeMaterialName()` strips both, `.NNN` first since it lands on the outside.
`_slotIndicesMatchingPrefixes` now tests the **normalized** name as well as the raw one.

Raw `startswith` already absorbed a suffix on the *slot* side by luck
(`"Eyelashes-1".startswith("Eyelashes")`), which is why LEGACY worked. The normalized
pass is what handles a suffix on the *prefix* side, and it makes the tolerance
deliberate rather than incidental. The change is **strictly additive** — every prefix
that matched before still matches, verified against a full suffixed G3F slot list.

Not covered, and left alone: `ensureLegacyGameMaterials` matches with substring `in`
against `body_*` game names, which never carry `-N`. Pre-existing, LEGACY-only.

### Design notes

- **FullBody merges by EXCLUSION, not by listing Daz surface names.** Anything not
  protected is swept into the body material, so a custom or non-stock surface is folded
  in too instead of being silently left as its own slot.
- **The bulk merge is done by INDEX, never by name.** `reassignMaterialSlotIndices` is
  the index-based twin of `reassignMaterialsAndRemoveSlots`, added so the merge does not
  round-trip slot names back through prefix matching — precisely the step the `-N`/`.NNN`
  suffixes make fragile. The only name matching left in FullBody is the two exception
  lists (bare Daz names) and the three target names, which are ours.
- **Order matters:** the two exception passes run FIRST, then the merge indices are
  computed. Each reassign drops slots and shifts every index behind it, so indices
  captured before those calls would be stale.
- Target names (`mat_fullbody`, `DONT_RENDER`, `mat_eyelashes`) are protected from
  the merge, or a second run would eat its own output.
- **An unrecognised mode string is normalized to `LEGACY` up front**, before any work,
  not handled in a fallback branch. Everything downstream asks `materialNamesForMode`,
  which hands anything that is not LEGACY the modern names — so a fallback that ran the
  LEGACY conversion while leaving the mode string unknown would produce `body_*`
  materials with `mat_*` placeholders on top. Two schemes on one mesh is exactly what
  per-mode naming exists to prevent.

### Material names, per mode

**TWO schemes, not three.** `materialNamesForMode()` returns `LEGACY_MATERIAL_NAMES` for
`LEGACY` and `MODERN_MATERIAL_NAMES` for everything else — `DAZ` and `FULLBODY` share the
modern scheme.

| Role | LEGACY | DAZ / FULLBODY |
|------|--------|----------------|
| whole body | — (no single body material) | `mat_fullbody` |
| eyelashes | `body_eyelash01` | `mat_eyelashes` |
| eye interior | — (folded into `body_head01`) | `DONT_RENDER` |
| censor | `body_main_censor` | `mat_censor` |
| genital | `body_genital01` | `mat_genital` |

**LEGACY's names are frozen.** They are the keys the legacy engine tables look up —
`dictionary_materials.stock_materials` (duplicated in `helper_material_lists_lookup`, which
also `import *`s the first copy and then shadows it — pre-existing latent bug) and
`importer_g3f.py`. Renaming them means editing four places in lockstep for no gain on the
Unreal side.

**Modern scheme rules:**
- `mat_` prefix marks the material as VX-authored — same idea as the `_joint0N` suffix on
  VX-authored bones.
- **No numeric suffix.** `body_eyelash01`'s `01` never had an `02`.
- **No vestigial words.** `main` in `body_main_censor` came from the
  `body_main_upper` / `body_main_lower` family, which does not exist here, so `mat_censor`.
- **`DONT_RENDER` is deliberately NOT prefixed** and deliberately shouty. It is a delete-me
  marker; it should look nothing like the materials that are kept.

**The schemes share no name**, which is what makes it safe for
`ensurePlaceholderMaterials` to run in every mode — no mesh can end up with `mat_censor`
and `body_main_censor` both.

**The `_SG` / `_RS` engine ids do NOT follow the rename.** `tagMaterialEngineIds` is still
called with `body_teeth01` / `body_main_censor`, which simply do not exist in the modern
modes, so it self-disables there through its existing missing-material guard. Those strings
belong to the legacy engine's namespace, not Blender's.

### Placeholders — created in EVERY mode

`ensurePlaceholderMaterials(ob, material_mode)` guarantees the censor and genital slots
exist on the body mesh, **under the mode's own names**. Unreal swaps a censor / genital
material in at runtime and can only do that if the slot already exists.

It takes the mode precisely because the two schemes must never both appear on one mesh:
creating the modern names unconditionally would leave LEGACY carrying `mat_censor` AND
`body_main_censor`, two slots for one region.

Runs **last**, after the mode-specific pass and after the unused-slot sweep, so nothing
downstream can delete them. In LEGACY it is a no-op — `ensureLegacyGameMaterials` already
made both.

Face state per mode:

| Role | DAZ | LEGACY | FULLBODY |
|---|---|---|---|
| censor | `mat_censor`, 82 faces* | `body_main_censor`, 82 faces* | `mat_censor`, 82 faces* |
| genital | `mat_genital`, empty | `body_genital01`, faces (Genitalia remap) | `mat_genital`, empty |

\* censor faces only when a geograft with a table entry is present — otherwise the slot
exists but stays empty. See below.

The genital material carrying faces in LEGACY is deliberate — LEGACY is frozen as "the
current conversion" and its `Genitalia → body_genital01` remap runs first. The separate
**geograft object** is assigned the mode's genital material in all three modes; existing
behaviour, and it keeps that region separable.

### Censor faces (`assignCensorFaces`)

The censor material is **not** empty — it gets 82 polygons on the body mesh. The faces
come off whatever material otherwise owned them (`body_main_upper` in LEGACY,
`mat_fullbody` in FULLBODY, the stock Daz surface in DAZ).

**Which faces depends on the GEOGRAFT, not on the material mode.** The censor region has
to cover the graft's footprint and the body around it, so a different geograft implies a
different face set. The table is keyed by the geograft's **object name**, which is what
the conversion has in hand:

```
censor_faces_genesis_3_female_genitalia = [...]          # the stock Daz G3F graft
censor_faces_by_geograft = {
    "Genesis 3 Female Genitalia": censor_faces_genesis_3_female_genitalia,
}
```

`assignCensorFaces(ob, material_mode, geograft_name)` is passed the name of the
**original** geograft, not the clone — `bpy.ops.object.duplicate` names the clone
`"... .001"`, which would never match a key.

**No geograft, or one with no table entry → nothing is assigned**, with a console line
saying so. The slot still exists (empty), so Unreal keeps its guarantee. Borrowing a face
set from a different geograft would put the censor in the wrong place, which is worse
than an empty slot.

**Adding a geograft is TWO edits in different files.** A new array plus registry entry in
`difeomorphic_workflow_init_custom_face_indices.py`, *and* the lookup in
`convertG3FDifeomorphicToVXModFBody`, which currently hardcodes
`"Genesis 3 Female Genitalia"` as the only geograft it searches for. Doing only the first
leaves the new array unreachable. That is the point: the region has to be its own slot for Unreal to swap
what renders there without touching the rest of the body.

**Ordering is load-bearing.** `assignCensorFaces` runs:
- **after** the unused-slot sweep — created any earlier, `body_main_censor` would be
  empty at sweep time and get pruned before it could be filled;
- **after** `sortLegacyMaterialSlots` — which is why it looks the slot up by name rather
  than trusting an index captured before the sort.

The arrays are named for the **geograft**, not for a material — the material name varies
by mode while the face set varies by geograft, so those are two independent axes and
neither belongs in the other's name. Putting a material name (let alone a legacy one)
into a per-figure index file would tie figure data to pipeline naming.

`assignFacesToMaterial` counts out-of-range indices and prints a warning instead of
raising, so a figure with different topology produces a loud console line rather than
aborting an otherwise fine conversion.

### Reload order in `__init__.py` is load-bearing

The `imp.reload(...)` block must reload **data modules before their consumers**.

`importer_g3f_difeomorphic` and `difeomorphic_workflow` both pull the index modules in
with `from ... import *`, which **copies** the arrays into their own globals at import
time. Reloading a consumer first makes it re-copy data that is still stale, so an edit to
an index file appears to do nothing and you have to restart Blender to see it.

This was wrong for `difeomorphic_workflow_init_custom_vertex_indices`, which was listed
*after* both of its consumers. Correct order now:

```
imp.reload(g3f.difeomorphic_workflow_init_custom_vertex_indices)
imp.reload(g3f.difeomorphic_workflow_init_custom_face_indices)
imp.reload(g3f.importer_g3f_difeomorphic)
imp.reload(g3f.difeomorphic_workflow)
```

Note also that `if "bpy" in locals():` at the top is **always true** — `import bpy` is at
line 24, well above it — so the reload branch always runs and the `else` branch never
does. The real loading is done by the `from .X import *` lines above the guard, which also
bind each submodule as an attribute of the package, which is what makes the `imp.reload`
names resolve at all.

### Geografts: discovery, ordering, renaming

`G3F→VX body` now finds **every** geograft, clones it, parents it to the body clone and
renames it `geograft_<N>_<short>`. It used to hardcode one name.

**Discovery mirrors Diffeomorphic's own `getAnatomies()`:** a mesh is a geograft iff its
data carries a non-empty `DazGraftGroup`, and it belongs to this body iff its
`DazVertexCount` equals the body's vertex count. Authoritative, and it picks up genitalia,
tails, wings, vampire teeth with no name list to maintain.

**There is NO application order to recover.** Verified by enumerating every property
`import_daz` registers — Mesh gets `DazRigidityGroups / DazGraftGroup / DazMaskGroup /
DazVertexCount / DazMaterialSets / DazHDMaterials`, Object gets `DazId / DazUrl / DazMesh /
DazRig / DazScale` and friends. All identity and geometry, none of them an index.
Scene order is no substitute either: `bpy.data.objects` is name-sorted, and any delete or
re-add reshuffles it.

So the order is **ours to define, and what matters is determinism, not fidelity**:
`exporter_unreal` builds the merged mesh name from the geograft order (`Belle_genz`), and
that name is the prefix of the subdivision JSON files VersaMap reads in Unreal. If the
order moves between runs, the exported filenames move with it.

`sortGeografts` sorts by the profile's `order`, then by object name. Unlisted geografts
take `GEOGRAFT_UNKNOWN_ORDER` and sort after every listed one, so **adding an unlisted
geograft never renumbers the listed ones.** `N` is then assigned sequentially from the
sorted result, so gaps in the `order` values are harmless.

**Profiles** live in `g3f/difeomorphic_workflow_init_geografts.py`, keyed by the geograft's
**original Daz object name**:

| field | meaning |
|---|---|
| `order` | sort key; only relative values matter |
| `short_name` | what follows the prefix — `genz` → `geograft_0_genz`; ends up in the exported merged name |
| `material_role` | key into the per-mode material table (`'genital'`). **Omit** to leave the geograft's own materials alone — the right default for a tail or wings |

A geograft with no entry still works: it is found, cloned, renamed with a sanitized
version of its object name, sorts last, and keeps its materials. Entries exist only to pin
the order and give a nicer short name.

### Table lookups match by PREFIX

`geograftTableKey()` resolves an object name against a table by **prefix, longest key
wins**, and both `geograftProfile()` and `censorFacesForGeograft()` go through it.

Prefix rather than exact because the mesh's object name is not something we control: it
is the figure name plus whatever gets bolted on — `.001` because the geograft's own
armature took the bare name first, sometimes a descriptive tail too. One table entry
absorbs all of it. Verified against `Genesis 3 Female Genitalia`, `.001`, `.002`,
`... Mesh` and `... HD.003` — all resolve to `genz` with 82 censor faces.

Longest-key-wins means a more specific entry added later is not shadowed by a shorter
one: with both `Genesis 3 Female Genitalia` and `Genesis 3 Female Genitalia 2` listed,
the second stops resolving to the first.

`short_name` in the profile is the maintained rename table the prefix match feeds.

### Merging geografts ONE AT A TIME (`geograftFitsBody`)

Diffeomorphic's rule is `aob.DazVertexCount == len(cob.data.vertices)` — the graft's
authored target size against the body's **live** count. That rejects the second
base-level geograft whenever you merge sequentially: the first merge grows the live
count, and graft B was authored against the *original* figure.

`geograftFitsBody` accepts either:

1. `aob.DazVertexCount == live count` — Diffeomorphic's rule. Covers a pristine body and
   also a **stacked** graft authored against a post-merge mesh.
2. `aob.DazVertexCount == cob.data.DazVertexCount`, when `live > base` — the graft
   targets the same base figure as the body, on a body that has already absorbed one.

Rule 2 works because **`DazVertexCount` is written once at import and never updated by a
merge** (`geometry.py` `setHideInfoMesh`), so on a merged body it still holds the original
figure's count — exactly what a second base-level graft was authored against.

And it is *safe* because the non-destructive merge only appends and welds, with the weld
loop running high-to-low (`reversed(dazGraftGroupAfterJoinDict.items())`) so every removed
vertex is one of the appended ones. **Base indices 0..N-1 are never renumbered** — which
the existing loop already relies on, since it keeps looking up body indices between welds.

The `live > base` guard keeps rule 2 from firing on a pristine body, so a genuine
figure mismatch is still rejected. Verified: pristine→accept, post-merge base-level
graft→accept (previously rejected), stacked graft→accept via rule 1, G8F graft→reject.

### A geograft is TWO objects — the mesh always carries a `.NNN` suffix

This is the normal case, not an edge case. A geograft imports as a **figure in its own
right**, so it arrives as:

| Object | Type | Name |
|---|---|---|
| the geograft's rig | ARMATURE | `Genesis 3 Female Genitalia` |
| the geograft's mesh | MESH | `Genesis 3 Female Genitalia.001` |

The armature claims the bare name first, so the **mesh** — the object the conversion
actually clones and renames — is always left with the suffix. Which number lands on it
depends on Blender's collision resolution, so it cannot be assumed to be `.001`.

Observed in the console when the tables were keyed on the raw name:

```
assignCensorFaces: no censor face table for geograft "Genesis 3 Female Genitalia.001"
```

**Key the profile and censor tables on the bare FIGURE name**, never on what the outliner
shows for the mesh object.

This is also why the old code worked: `checkIfActiveObjectHasChild` matched by
**substring**, and `"Genesis 3 Female Genitalia"` is a substring of `"...Genitalia.001"`.
Moving to exact-key tables is what broke it.

`normalizeObjectName()` strips the suffix (and handles it stacking, `.001.001`, from
append-between-files). Every lookup goes through an accessor that normalizes —
`geograftProfile()` and `censorFacesForGeograft()`. **No call site touches
`geograft_profiles` or `censor_faces_by_geograft` directly**, which is what keeps the next
lookup from reintroducing the bug.

**It strips only `.NNN`, never `-N`.** `normalizeMaterialName` strips both and must NOT be
reused for objects: a geograft legitimately named `Tail-2` would lose its `-2`. Two
normalizers, two namespaces, on purpose.

`sortGeografts` uses the normalized name as its tie-break so `X` and `X.001` sort
adjacently, with the raw name last to keep the ordering total. Discovery filters on
`ob.type == 'MESH'`, so the geograft's armature is never mistaken for the geograft.

**Short names are still forced unique** by `assignGeograftNames`. It will not fire for the
armature/mesh pair (only one mesh exists), but it remains the guard against a genuine
duplicate: two grafts normalizing to the same profile would otherwise both become `genz`
and export as `Belle_genz_genz`, with no way to tell which file was which.

**Original names are captured before renaming.** Both the profile table and
`censor_faces_by_geograft` are keyed by the Daz name, which is gone from the clone the
moment it is renamed, so `geograftClones` carries `(original_name, clone)` pairs.

**Censor faces are the UNION** across every present geograft that has a table entry — a
body can carry several at once.

**Re-run safety:** `geograftShortName` strips an existing `^geograft_\d+_` before
rebuilding the name, so nothing ever becomes `geograft_0_geograft_0_genz`.

**This removes the old trap.** Previously the conversion looked for the literal name
`"Genesis 3 Female Genitalia"` (substring match), so a geograft already hand-renamed to
`geograft_0_genz` was invisible: no clone, no genital material, no censor faces, silently.

### Where index data lives

`g3f/difeomorphic_workflow_init_custom_face_indices.py` — new module, same rule as
`difeomorphic_workflow_init_custom_vertex_indices.py`: **an index never appears at a call
site**, so G3M / G8F / G9 later is a module swap.

Kept as its **own module** rather than added to the vertex file because these are polygon
indices. Mixing two index spaces in one namespace reads fine and then silently indexes
the wrong array — and the vertex file is already crowded.

Validity: correct against the stock Diffeomorphic G3F topology *during* `G3F→VX body`.
Nothing in that conversion deletes geometry — the material work only remaps
`material_index` and prunes slots — so polygon order survives. They are **not** valid
after `diffeomorphic_merge_geografts.py`, which joins meshes and renumbers polygons.

### Refactor that came with it

The material block inside `convertG3FDifeomorphicToVXModFBody` was flat inline code; it
is now five module-level functions — `applyLegacyMaterialConversion`,
`applyFullBodyMaterialConversion`, `ensureLegacyGameMaterials`,
`sortLegacyMaterialSlots`, `ensurePlaceholderMaterials` — plus `tagMaterialEngineIds`.

`tagMaterialEngineIds` exists because the old code did a bare
`bpy.data.materials["body_teeth01"][...] = ...`. `body_teeth01` only exists in LEGACY, so
that line raises `KeyError` in both new modes. It is now a guarded no-op when the material
is absent.

`ensureLegacyGameMaterials` and `sortLegacyMaterialSlots` are **LEGACY only**. The other
modes have no fixed material table to pad and no engine index order to sort into —
FULLBODY deliberately ends up with three or four slots.

### Downstream, not yet checked

`helper_material_lists_lookup.build_materials_list_lookup` and `dictionary_materials.py`
both hardcode the 19/21-entry legacy `stock_materials` table and read `body_subdiv_cage`.
Those target the **legacy engine** export path, not Unreal. Running the exporter after a
`DAZ` or `FULLBODY` conversion has **not been tested** and will almost certainly not
produce a valid legacy material list. Not a bug in the new modes — just an untested
combination worth knowing about.

---

## Session State — extra bones + jiggle system (2026-09-02)

**Actively being worked on:** the bones `Manny FULL` adds beyond the Epic skeleton, and the
weight machinery behind them. `Manny FULL` is now **9 steps** (see "The Manny path").

**Status: committed and pushed.** Everything below is commit `eacc146` on `manny_armature`,
pushed to `origin` — which carried **7 commits**, since six earlier ones had never been
pushed either. Working tree clean.

That commit also contains work **predating this session** that was already uncommitted: the
export bone ordering in `exporter_unreal.py` (`sort_bones_for_export`,
`_sibling_rank_table`, `_EDIT_BONE_CARRIED_ATTRS`) plus its `export_bone_sibling_order`
table. It shares a file with this session's changes so it could not be split out; the commit
message says so.

**Active files** — all in `eacc146`:

| file | what changed |
|---|---|
| `g3f/difeomorphic_workflow.py` | all the new passes (see the function list below) |
| `g3f/difeomorphic_workflow_dictionaries_bones.py` | teeth into the collapse lists, `spine_bones_aimed_at_children`, `"lowerJaw": None`, pectoral rename |
| `g3f/difeomorphic_workflow_init_custom_vertex_indices.py` | `butt_crease_L/R`, `lower_jaw_tail`, `cyclops_joint01_base` |
| `__init__.py` | steps 6–9 wired in, build-options panel, Toggle fishing button, UE5 check button, end-of-run hide/select |
| `CLAUDE.md` | this file — untracked, still needs a first commit |

New functions in `difeomorphic_workflow.py`: `aimSpineBonesAtChildren`,
`levelFootRollHinges`, `checkUE5Compatibility`, `moveEndBonesToLayer`,
`setupPectoralChain`, `_createFishingChain`, `rebuildPectoralFishingChains`,
`enablePectoralFishingRig` / `disablePectoralFishingRig` / `toggleFishingRig`,
`_buildJiggleBone`, `setupStomachBone`, `setupButtBones`, `setupCyclopsBone`,
`setBoneTailToVertices`.

**Tested and accepted:** foot hinges; pectoral chain and its axial/radial split; fishing
chain geometry and computed rolls; toggle + IK + `STRETCH_TO` on joint01/joint02; spine
aim; stomach bone; butt falloff through the `peak_depth 0.45 / overshoot 1.55` pass.

**NOT yet tested — start here after resuming:**

1. Run `G3F→VX body` then `Manny FULL`, read the console report.
2. Check `plateau_below=0.0` softened the lower butt edges as intended.
3. Check `moveEndBonesToLayer` hid `stomach_end`, `butt_end.L/.R`, `cyclops_end` on layer 1.
4. Check the recursive source-hide left the new `Armature` selected and active, and hid
   nothing it should not have.
5. Check `lowerJaw` now aims at `lower_jaw_tail=[36, 64]`.
6. Check `setupCyclopsBone` produced `cyclops_joint01` + `cyclops_end` on the skin surface
   between the eyes.

*(Committing was step 7 and is done — see Status above.)*

**Environment follow-up, deferred:** `git push` prints
`git: 'credential-manager-core' is not a git command.` before succeeding.
`credential.helper` points at `manager-core`, renamed to `manager` in Git Credential
Manager 2.4+; the push works only because a cached credential covers it, so this will fail
once that cache expires. Suspected source is SmartGit, used alongside the CLI. Diagnose with
`git config --show-origin --get-all credential.helper` — multiple entries are normal when a
GUI client and a Git install each register one, and the fix is usually deleting the stale
line rather than adding another.

**Conventions established this session** (also folded into "New conventions" below):
vertex indices never appear at a call site; `use_deform = True` even on weightless bones;
weight passes must reclaim before borrowing; do not pin a curve's extremum to the boundary
you care about.

---

## Session State — Manny conversion pipeline (2026-07-29)

Branch `manny_armature`. Three commits landed this session:

| commit | what |
|---|---|
| `50503da` | Full Difeomorphic G3F → Manny conversion pipeline |
| `dde0b16` | Removed `bpy.ops` loops from the G3F→VX body conversion (26 s → fast, user-confirmed) |
| `bc35358` | Dropped legacy placeholder shape keys, renamed the superseded module |

Uncommitted: `show_x_ray` / `show_axes` set on the produced armature at the end of
`Manny FULL` (`__init__.py`).

### The Manny path

**Panel** (`VXMOD_CONVERTER_OT_PanelDifeomorphicToVXMod`) is now three labelled boxes:
`1. Mesh` (shared) · `2. Manny skeleton` · `Legacy VXMod skeleton`. The old VXMod path
is untouched and targets a **different, incompatible skeleton** — do not mix them.

**To run:** select the `Genesis 3 Female` armature → `G3F→VX body`, then press
`Manny FULL` (finds the armature and mesh itself, nothing to select).

**`Manny FULL` = `vxmod.convert_g3fdifeo_to_vxmodf_manny_full`**, in strict order:

1. `alignArmatureFromDifeomorphicToManny` — creates `Armature`, renames, reparents,
   repositions, clamps lengths, **levels the foot hinges**
2. `bindMeshToArmature` — ARMATURE modifier **only, never parents**; clears a parent if
   it finds one (the exporter builds its own hierarchy at export time)
3. `switchVertexGroupsToManny` — pure 1:1 rename, no merging
4. `mergeBonesIntoTargets` — face rig + teeth → head/lowerJaw, heel+metatarsals → foot;
   deletes bones and reparents survivors
5. `setupTwistBones` — unchain → clamp → measure → place → blend weights
6. `setupPectoralChain` — splits each pectoral 40/30/30 + a nipple handle, moves the
   weights outward onto `joint01`/`joint02`, and builds the non-deforming fishing chain
7. `applyBlenderPerfectRolls` — again, so bones created in 5 and 6 land on the table
8. `levelFootRollHinges` — again, on the FINAL geometry (see ordering below)

Bone arithmetic, derived from the tables rather than remembered:

| stage | count |
|---|---|
| Diffeomorphic G3F source | 172 |
| − face rig + teeth (48 → head, 20 → lowerJaw) | 104 |
| − heel + metatarsals (2 per side) | 100 |
| + twists (8 pairs × 2) | 116 |
| + pectoral deform chain (`joint01`, `joint02`, `nipple_joint` × 2) | 122 |
| + fishing chain (`rod`, `line`, `hook` × 2) | **128** |

`pectoral_base` is not new — it is `lPectoral`/`rPectoral` renamed, so it is already counted
in the 172. Only the six bones per pair below it are additions.

### Ordering constraints that fail SILENTLY

- **Step 3 must precede step 4.** Step 1 already renamed the bones; until the groups
  catch up the two are in different name spaces and `mergeBonesIntoTargets` skips any
  rule whose target it cannot find. A rule written as `lFoot` instead of `foot.L` is a
  no-op with only a console note.
- **Inside `setupTwistBones`: unchain → clamp → measure → place.** The clamp can only
  reach `calf.L` once the twists are leaves, and the 1/3 & 2/3 fractions are measured
  off the settled parent length.
- **Step 6 must follow step 3.** `setupPectoralChain` looks the weights up under the
  Manny group name (`pectoral_base.L`), not the Daz one (`lPectoral`).
- **Step 8 must be last, and repeats step 1's work deliberately.** Steps 4 and 5 re-clamp
  the foot once `mergeBonesIntoTargets` has removed the metatarsals, and step 7 rewrites
  rolls. Only the final pass sees the geometry that ships. Idempotent — an already level
  hinge is inside tolerance and skipped.
- **A name in BOTH a collapse list and `bones_that_must_be_kept` ABORTS the whole
  collapse.** `mergeBonesIntoTargets` returns `({}, [])` with one console line, so all 72
  bones silently survive and the rig looks untouched rather than partly merged. When you
  move a bone into a merge list, delete it from the guard in the same edit.
- **Never use `mergeSubgroupsIntoGroup` when the target already has weight.** It calls
  `checkIfVertexGroupExistAndRecreateIt` first, destroying the target group;
  `idxs.append(vgrp.index)` at `:1158` reads an already-emptied group. Use
  `merge_vgroups_into_existing` (`helper_vgroups.py`). The existing 72-name head merge
  in `MESH_OT_Switch_To_VX_Vertex_Groups` has this latent bug — left alone deliberately.

### New conventions

- **`getMannyBoneRenameMap()` is the single source of truth** for Daz→Manny naming.
  Both the armature builder and the vertex-group renamer call it. The old tables had
  drifted a full spine segment apart (`abdomenLower` → `spine_01` as a group but
  `spine_02` as a bone), orphaning `hip`'s weights and leaving `spine_05` empty.
- **All bone data lives in `g3f/difeomorphic_workflow_dictionaries_bones.py`** as
  inspectable tables: `dtu_manny_bones_matching` (67, a pure DazToUnreal transcription),
  `manny_extra_bones_matching` (22 toes+breasts), `face_bones_merged_to_head` (48),
  `face_bones_merged_to_lower_jaw` (20), `bone_collapse_rules`,
  `bone_reparent_overrides`, `twist_bone_pairs`, `bones_length_set_to_successor`,
  `manny_chain_successors`, `bones_that_must_be_kept`.
- **`manny_chain_successors` values may be a list** — tried in order, first match wins,
  so one entry covers both sides of a collapse.
- **VERTEX INDICES NEVER APPEAR AT A CALL SITE.** They live in
  `g3f/difeomorphic_workflow_init_custom_vertex_indices.py` as named arrays, always a
  LIST even when it holds one entry (`stomach_top=[31]`, `lower_jaw_tail=[36]`), and are
  read through `getCenter` so a single point and an averaged ring go through the same
  path. Functions take the array, never a bare number — `setBoneTailToVertices(...,
  lower_jaw_tail)`, not `..., 36`. This is what makes supporting another figure (G3M,
  G8F, G9) a matter of swapping that one module rather than hunting hardcoded numbers
  through the pipeline.
- **Performance: `bpy.ops` call COUNT is the metric.** `bpy/ops.py:147` runs a full
  `scene.update()` after every operator — 53 ms in this scene. Prefer direct data API:
  `materials.pop(update_data=False)`, `polygons.foreach_get/foreach_set`, compute
  permutations in Python and apply once.
- **Legacy modules get a `legacy_` filename prefix** plus a docstring saying what
  replaced them (see `legacy_tools_import_export_shape_keys_json.py`).
- **`use_deform = True` even on weightless bones.** The FBX writer runs with
  `use_armature_deform_only=True`, which drops bones by that FLAG, not by whether they
  carry weight — and Blender only spares a non-deforming bone when it has a **deforming
  child**, which a leaf never has. So `_end` tips, `nipple_joint`, the fishing chain and
  `cyclops_*` all keep it on. `dontExportJointEnds` (`__init__.py:219`) is a dead
  property, declared and never read; it governs nothing.
- **Any weight pass must RECLAIM before it borrows.** `Manny FULL` rebuilds the BONES but
  never the MESH, so vertex groups survive a re-run. Without a reclaim, re-running stacks:
  it took `spine_02` from 0.65 to 0.12 over five runs, and `_splitTwistWeights` was
  *losing* 76% of the weight outright. Where two groups sum to the original (the twists)
  summing them IS the reclaim; otherwise hand it back proportionally to what the sources
  still hold, which is exact rather than approximate.
- **Never pin a curve's extremum to the boundary you care about.** Putting the falloff's
  ZERO on the gluteal crease gave the crease no weight; putting the PEAK there made it the
  heaviest band. Both times the fix was moving the extremum off the boundary
  (`lower_limit_overshoot`, `peak_depth`).
- **A `draw()` that raises truncates the panel silently** from that row down — no error in
  the UI, just missing buttons. Look up anything shared across rows once at the top.
- **Blender's interactive console cannot take a dedent inside a pasted block.** When
  handing the user a snippet, make every line a standalone statement — even a one-line
  `for` leaves the console in block mode and swallows what follows.

### Added since 2026-07-29

**Foot roll hinges** (`levelFootRollHinges`, steps 1 and 8). Measured off the real UE5
mannequin: the hinge axis (UE local Z) runs `pelvis 0.0000 → thigh -2.5398 → calf -2.5398
→ foot -0.0015`, and `foot`'s local Pitch is exactly `-2.5398` — the negated accumulated
tilt. Epic solves for a **level hinge**, nothing else: the bone direction ends 88.19° from
horizontal, not a clean 90. A level hinge is what makes ankle pitch and ball roll clean
rotations. In BlenderPerfect the hinge is local **+X**, so this is a roll-only fix, applied
to `foot.L/.R` and `ball.L/.R`. Sign-safe: of the two horizontal perpendiculars it picks
whichever is nearer the rig's existing X, so it inherits the mirroring instead of imposing
one. Does **not** change the export — `reaim_feet_for_unreal` rebuilds those frames
absolutely — it is for the Blender-side rig.

Related, and easy to get backwards: **the UE5 foot points down the shin, not at the ball.**
The ball absorbs the toe direction one joint later. DazToUnreal's author wrote
`AlignBone(foot_l, ball_l)` and then commented it out.

**Teeth collapsed.** `upperTeeth` → `head`, `lowerTeeth` → `lowerJaw`; both are rigid
children of their parent, so the deformation is identical. `tongue01` is reparented onto
`lowerJaw` automatically by the nearest-surviving-ancestor walk — no
`bone_reparent_overrides` entry. Both were removed from `bones_that_must_be_kept` (see the
abort gotcha above).

**Pectoral chain** (`setupPectoralChain`). `lPectoral`/`rPectoral` → `pectoral_base`
(renamed in `manny_extra_bones_matching`, previously `breast_joint`), then split 40/30/30
with `nipple_joint` as a ~1.5 cm selectable stub. **Weights land on `pectoral_joint01` +
`pectoral_joint02`, and `pectoral_base` is cleared** — measured on G3F, the breast does not
begin until `t ≈ 0.47` along the Daz bone, so the base's whole 0–40% span sits inside the
ribcage. It is a structural root the breast swings from.

`_splitPectoralWeights` **moves** weight — it clears the source after writing. Copying
instead leaves every vertex at 2× influence, which reads as the mesh inflating when the
chain rotates.

The falloff normalises against **the weighted vertices' own p5–p95 span, not bone length**.
The first version divided by bone length — the assumption that holds for twists (`thigh.L`
does span the thigh) but not here — and put the median vertex at `u = 1.02`, so the near
bone came out empty. Two modes, chosen per side in the panel: `axial` (projection onto the
bone axis) and `radial` (distance from the chest wall). They are identical on-axis and
diverge only off it, so expect a subtle difference.

**Fishing chain** (`_createFishingChain`, `rebuildPectoralFishingChains`). A SECOND chain
off the same base, parallel to the deforming one and carrying no weight:

```
pectoral_base ┬→ pectoral_joint01 → pectoral_joint02 → nipple_joint   (deforms)
              └→ pectoral_rod → pectoral_line → pectoral_hook          (mechanism)
```

MCH bones in Rigify's vocabulary. **Leave `use_deform` ON** despite them deforming nothing —
the FBX writer runs with `use_armature_deform_only=True` (`exporter_unreal.py:1141`), so
marking them non-deform the usual Blender way deletes them from the export.

*Geometry.* The rod angle is the only input; the line length is derived. The line can be
vertical AND land on the hook only if the rod tip is directly above the nipple, so the two
are not independent. Holding the rod's HORIZONTAL run equal to `base.tail → nipple` and
raising only its vertical component puts the tip on the nipple's X/Y **exactly** (verified
at `0.0e+00`), so the line is vertical by construction, not to within a rounding error. At
10° on G3F: rod 14.4 cm, line drop 2.5 cm. At 0° the tip lands on the nipple and the line
has no length — refused, because Blender silently deletes zero-length bones.

*Rolls are computed, not inherited.* Copying `base.roll` (the first version) is meaningless:
roll is a scalar measured against a frame built from the bone's OWN direction, so the same
number on differently-aimed bones gives unrelated world axes. Rod gets a **level hinge**
(local X horizontal, the `levelFootRollHinges` rule) so rotating about +X is a pure vertical
swing; the sign is taken from `pectoral_joint01`'s X so the two chains read alike and L/R
mirror for free. The line then inherits the rod's hinge, so both swing about **one shared
horizontal axis**. Levelling cannot be used on the line itself — it is vertical, so every
perpendicular is already horizontal and the rule picks no roll at all.

### How `pectoral_line` is forced to point down (the gravity trick)

**`use_inherit_rotation = False` on the line bone. Not a constraint.** Two facts combine:

1. The line's **rest** orientation is already exactly vertical, because `_createFishingChain`
   puts its head at the rod tip and its tail on the nipple, and the rod tip is built to sit
   directly above the nipple.
2. `use_inherit_rotation = False` splits position from orientation: the head still follows
   the parent (it rides the rod's tail as the rod swings) but the parent's **rotation** is
   never composed into the child's orientation.

Together: head tracks the rod tip, orientation stays pinned to rest — a plumb line. It blocks
**every** ancestor, not just the rod, so bending the spine does not tilt it either. That is
what a Damped Track to a fixed point could not give you (the direction to any finite point is
not truly vertical), and what a Copy Rotation would need a purpose-built target to mean.

Limits, in order of how likely they are to bite:

- It only blocks **inherited** rotation. The bone's own local pose rotation still applies,
  which is why `enablePectoralFishingRig` also sets `lock_rotation` and `lock_rotation_w` on
  the line — and on **nothing else**. `lock_location` is deliberately NOT set, so translating
  the line in pose mode can still pull its head off the rod tip.
- It is **armature-space** down, not world down. A yaw is fine (Z is unchanged); pitching or
  rolling the armature object tilts "down" with it.
- It **does not reach Unreal**. The flag is carried by `_EDIT_BONE_CARRIED_ATTRS` through the
  exporter's bone rebuild, but FBX/UE skeletal bones always inherit their parent's transform.
  The exported rest skeleton is identical either way, since nothing is rotated at rest.

### Enabling the mechanism (`toggleFishingRig`)

Button: **Toggle fishing**, first in a new row under `Constraints and IKs`. Adds the setup if
absent, removes it if present. `enablePectoralFishingRig` / `disablePectoralFishingRig` do the
two halves; the toggle treats "the named IK exists on ANY side" as on, so a half-wired rig
toggles OFF first rather than stacking a second copy on the side that already had one.

**Constraints are NAMED**, and everything is matched on name *and* type via
`_namedConstraint()`, so a hand-made IK or Stretch To on the same bones is never touched or
removed:

| constant | value | on |
|---|---|---|
| `FISHING_IK_CONSTRAINT_NAME` | `VX Fishing IK` | `pectoral_joint02` |
| `FISHING_STRETCH_CONSTRAINT_NAME` | `VX Fishing Stretch` | `pectoral_joint01` **and** `pectoral_joint02` |

Per side:

- **IK on `pectoral_joint02`**, target `pectoral_hook`, `chain_count = 2`, **`use_stretch`
  OFF** — bend only. The IK goes on joint02, NOT on `nipple_joint`: Blender drives the
  CONSTRAINED bone's tail to the target and counts the chain upward from it inclusive, so
  joint02 + count 2 is exactly `{joint01, joint02}`. On `nipple_joint` it would be
  `{nipple_joint, joint02}` and leave joint01 rigid. The nipple still follows the hook because
  `joint02.tail` **is** `nipple_joint.head`, and also the hook's head — so the IK is satisfied
  with zero deviation at rest and the rig does not twitch when enabled.
- **`STRETCH_TO` on both chain bones**, target `pectoral_hook`, `volume = 'NO_VOLUME'`.
  Reaching has to happen somehow — see the reach limit above — and this is how.
- The line pinned and locked, as above. **`nipple_joint` gets nothing**; it is a marker only.

#### Stretch influences, and why they are what they are

`stretch_influence` is a **`(joint01, joint02)` pair, tuned to `(0.15, 0.25)`**. Written on
every run, not just on create — the code is the source of truth, so pressing Toggle re-applies
it. A value tweaked by hand in the N-panel is therefore overwritten on the next Toggle.

Influence is the dial rather than an on/off because **1.0 on `joint01` is degenerate**: at full
influence the constraint aims that bone at the hook as well, both bones point at the same place,
and the chain straightens out — defeating the IK bend entirely. Partial influence on both lets
them share the stretch *and* still bend.

`rest_length` is measured **per bone** as its head→hook distance at rest, not the bone's own
length. For joint02 those coincide (its tail *is* the hook); for joint01 the hook is a whole
bone further on, so using its own length would read as "already stretched 2×" and it would
double the instant the constraint switched on.

**IK `use_stretch` was tried first and rejected.** The solver distributes scaling across the
chain by its own rule, so joint01 grew as much as joint02 and the deformation read wrong. If it
is ever revisited, note the trap: `use_stretch` on the constraint does nothing on its own,
because `PoseBone.ik_stretch` defaults to `0.0` and every chain bone refuses to scale. Both are
explicitly zeroed now. An earlier attempt also put a `STRETCH_TO` on `pectoral_hook` itself
(stretching the *target* toward the effector, as an IK-error readout) — that is gone, and
`_clearLegacyHookStretch()` removes it on sight so older rigs get cleaned up.

No dependency cycle: the hook hangs off `line → rod → pectoral_base` while joint02 hangs off
`joint01 → pectoral_base`. Siblings, so the target does not depend on what the IK drives.

**Blender-side only.** Constraints and bone flags do not survive FBX export; in Unreal this
has to be rebuilt as a Control Rig or anim graph node, using the exported rod/line/hook as
the scaffold.

### Jiggle bones (`_buildJiggleBone`, `setupStomachBone`, `setupButtBones`)

Step 7 of `Manny FULL`. Deform bones for AnimDynamics / KawaiiPhysics secondary motion —
NOT drivers, unlike the fishing chain. All built from the **mesh**, so they track the
figure's actual shape rather than a fraction of some bone:

```
stomach_joint01 -> stomach_end     parent spine_02,  source spine_02
butt_joint01.L  -> butt_end.L      parent pelvis,    source pelvis + thigh.L + thigh_twist_01.L
butt_joint01.R  -> butt_end.R                        (per side, "{side}" substituted at call time)
```

`head` = centre of a vertex ring (averaged, lands inside the body), `tail` = a surface
vertex, `_end` = a short stub past it. The aim is free — the joint's tail *is* the end's
head. `flatten_head_z` snaps the head to the tail's height so the physics gets a clean
swing axis. Vertex sets live in `difeomorphic_workflow_init_custom_vertex_indices.py`
(`stomach_base/top`, `butt_base/top_L/R`, `butt_crease_L/R`), all assuming the 17418-vert
G3F topology. `rib_joint01.L/R` sit in `extra_bones_torso.json` with the same structure
whenever they're wanted — a two-line addition now.

**`use_deform = True` on the `_end` bones too**, despite them carrying no weight. Same trap
as the fishing chain: the FBX writer filters on that flag, and Blender only spares a
non-deforming bone if it has a *deforming child*, which a leaf never has. The tips exist so
Unreal draws the joint as a bone rather than a nub, so losing them defeats the purpose.
`moveEndBonesToLayer` parks them on armature layer 1 and hides it — **visibility only**,
layers never affect FBX export.

#### Weights are MOVED, and the pass is idempotent

What the joint gains is subtracted from the source, so total influence per vertex is
unchanged and the mesh does not shift at rest. Before taking anything it **reclaims** what a
previous run borrowed, distributed back across the sources **proportionally** — which is
exact, not approximate: the borrow took `max × falloff` of each source, so the remainder is
still in the original proportions. Without that, `Manny FULL` re-runs stacked, and five runs
took `spine_02` from 0.65 to 0.12. Caveat: weight painted onto a jiggle group by hand is
folded back in and redistributed.

Two bugs that only appear with several sources, both fixed: the target is written **once per
vertex with the summed take** (writing per sample would `REPLACE` repeatedly, keeping only
the last take while every source was already debited), and the reclaim is proportional
rather than dumping everything on `source_groups[0]`.

#### The falloff: horizontal and vertical are SEPARATE profiles, multiplied

This is the part worth understanding before touching the numbers. It was one radial distance
originally, and that **cannot** express a glute: any single metric centred on the bone tip is
strongest *at* the tip and weakest at the crease, which is upside down for the shape. No
reshaping of one curve fixes it — the two axes need different profiles, so they get them.

| parameter | does |
|---|---|
| `radius` | horizontal extent |
| `plateau` | fraction of radius held at FULL value before the horizontal taper |
| `plateau_below` | the plateau to ease toward BELOW the tail. 0.0 spreads the taper over the whole radius, widening the transition band ~24% and softening the lower edges |
| `upper_scale` | vertical weight AT THE APEX, ramping to full at the lower limit. Below 1.0 keeps a glute bone off the lumbar back |
| `peak_depth` | where the vertical profile maxes, in apex→limit units. **1.0 peaks ON the limit**, making the limit the heaviest band |
| `lower_limit_indices` | verts along an anatomical floor (the gluteal crease). Their mean height sets the downward reach — measured, not guessed |
| `lower_limit_overshoot` | how far PAST that floor the falloff reaches. **1.0 puts zero exactly on the floor, so the floor gets NO weight**. Higher = longer, gentler tail |
| `vertical_reach` | `(up, down)` as fractions of radius. Only `up` matters once a lower limit is measured |
| `max_weight` | scales everything uniformly |
| `forward_only`, `side_sign` | see below |

**Tuned values, arrived at over several passes against weight-paint screenshots** — butt:
`radius 0.22`, `max_weight 0.50`, `plateau 0.20`, `plateau_below 0.0`, `upper_scale 0.55`,
`peak_depth 0.45`, `lower_limit_overshoot 1.55`. Stomach keeps the plain symmetric decay
(`radius 0.16`, `max_weight 0.35`, no lower limit, so no ramp).

Everything is smoothstepped and **blended by depth rather than switched at `z = 0`**. A hard
switch at the tail's height leaves a horizontal seam at mid-radius; this bit me twice, once
with a gamma and once with `plateau_below`.

The recurring mistake worth remembering: **pinning a curve's extremum to the boundary you
care about.** Putting the *zero* on the crease gave it no weight; putting the *peak* on it
made it the heaviest band. Both times the fix was to move the extremum off the boundary.

**`side_sign` is load-bearing on paired bones.** `.L` and `.R` borrow from the SAME source
groups, so without it an overlapping radius lets both claim a vertex, the second `REPLACE`
clobbers the first, and the source is debited twice but credited once. `.L` keeps `x > 0`,
`.R` keeps `x < 0`; midline verts fall to neither, which is right.

**Measure the source before choosing it.** The butt first borrowed from `pelvis` alone
(4.109 of 6.000, 68%, over the cheek surface and flanks) and the crease came out near zero —
because down there `pelvis` has faded and `thigh.L`/`thigh_twist_01.L` own the region, and
the borrow is `source_weight × max_weight × falloff`. A perfect falloff over an empty source
yields nothing.

**Build options panel.** A `Build options (per side)` box under `Manny FULL` holds
`pectoralWeightModeL` / `pectoralWeightModeR` (`EnumProperty`, `expand=True`) and
`pectoralRodAngle` (plain degrees — deliberately NOT `subtype='ANGLE'`, which stores radians
and would need converting on every read). Weight modes are split L/R on purpose so a feature
can be A/B'd on one figure. These are **build** options — changing one does nothing until the
next `Manny FULL`, with one exception: the rod angle is also read by the ⟳ button beside it,
which re-cuts the fishing chain on the rig as it stands. That is safe to repeat because the
fishing chain carries no weight, unlike `setupPectoralChain`, which refuses to re-run.

**Panel gotcha, learned the hard way.** A `draw()` that raises stops dead and silently
truncates the panel from that row down — no error in the UI, just missing buttons. It cost a
round trip when `manny_armature` was used above the line that assigned it. Anything shared
across rows is now looked up once at the top of `draw()`.

**UE5 compatibility check** (`checkUE5Compatibility`, button `Check UE5 compatibility`).
Read-only audit: (1) all 67 Manny bones present, twists counted separately since they only
exist after step 5; (2) `spine_01` on the pelvis/spine_02 midpoint; (3)/(4) foot and ball
hinges level. The pelvis 0.7 drop is deliberately **not** checked — it is unverifiable from
the finished rig, and testing it would mean depending on the source Diffeomorphic armature
still being in the scene.

### Gotchas found

- Manny needs `ball` as a **direct child of `foot`**, so `lMetatarsals` cannot stay
  mid-chain; the five toes per side go under **`ball`**, not `foot`.
- **`setupPectoralChain` refuses to re-run.** If `pectoral_joint01.{side}` exists that side
  is skipped whole. Re-splitting already-split weights drags everything back onto the near
  bone. To retry you need a pre-split rig: undo, or `G3F→VX body` + `Manny FULL` again —
  re-running `Manny FULL` alone will not restore overwritten weights.
- **`_splitPectoralWeights` MOVES weights, it does not copy them.** The source group is
  cleared after writing. Skipping that leaves every vertex with 2× influence, which shows
  up as the mesh inflating when the chain rotates.
- Daz chains twists **in-line**; Manny wants them as **leaves** (this is DazToUnreal's
  `FixTwistBones`). Fixing that also moves `calf.L`, `lowerarm.L` and `hand.L` onto their
  correct parents.
- Every limb bone's Daz tail falls **~53% short** of the next joint (calf ~4%), so a
  length *cap* never fires — hence `bones_length_set_to_successor`, which sets exactly.
- Converted bodies now have **`ob.data.shape_keys == None`**. Guarded the two unguarded
  consumers; `exporter_unreal.py` was already safe at `:193-194` and `:1293`.
- Knee bend is only **2.3°** (elbow 16°). Do not force leg bones collinear — that is an
  IK singularity. `makeBonesCollinearFromBoneHeadToBoneTail` is spine/forearm only; the
  leg call at `ik_tools.py:382-383` is commented out.

### Next steps

1. ~~Scaffold the two roll tables~~ **DONE, differently.** The convention landed as
   `applyBlenderPerfectRolls` plus three tables in the dictionaries module:
   `blender_perfect_roll_deltas` (currently `{}` — Diffeomorphic already delivers the
   convention almost everywhere), `blender_perfect_roll_axis_targets` (aiming, clavicles
   only) and the hinge rules (hand). Note it ADDS a delta and is guarded by the
   `vx_orientation` stamp, not the SET-absolute practice this item assumed.
2. ~~Blocked on a trustworthy Manny reference~~ **UNBLOCKED.** A real one now exists:
   `MyFirstProject 5.4 5.6/Saved/bone_data.csv`, 89 bones dumped from the UE5 skeleton
   with local translation, rotation (Roll/Pitch/Yaw), and length. Verified sound by
   reconstructing world positions from it — head Z `162.50`, pelvis `98.69`, ankle `8.13`,
   ball `1.17`, and foot→ball length matching the `Length` column to 4 dp. Use it, not
   `armature_vxnew_manny.json`, whose values remain unverified.
   Two things already measured off it, both now implemented: the foot/ball hinge
   convention, and confirmation that `ball`'s local rotation is exactly `(0, 0, 90)`.
   Caveat: the figure reconstructs yawed ~90° from Manny's usual +X facing, so trust
   elevation angles (unaffected by yaw about Z) and check the exporter's world convention
   before reading horizontal components as forward/right.
3. `reorientArmatureFromDifeomorphicToManny` is still a stub — and with head/tail correct
   (direction within ~1°), **roll is the only remaining degree of freedom**, so a roll
   table is a complete fix. Do not port DazToUnreal's 37-op pass.
4. Materials will be replaced from a custom JSON later — check whether
   `tools_import_export_materials_json.py` is live or legacy, and whether the conversion
   still needs to build the 21-slot layout at all. **Partly answered:** the 21-slot
   layout is now optional, gated behind the `LEGACY` mode of
   `vxmod.materialConversionMode` (see "Material conversion modes"). Still open: whether
   the legacy-engine export path is ever used again, and what `DAZ` / `FULLBODY` do to
   `build_materials_list_lookup`, which is untested against them.
5. **PLANNED FEATURE — body-type profiles driving the extra bones.** Measure the loaded
   body, classify it, and use the result to pick tuning profiles for everything the
   Manny path adds: fishing bone placement and rod angle, butt weights, belly/navel
   weights, pectoral split fractions, possibly twist blends. `Manny FULL` would take a
   profile parameter (or one per axis) instead of the single hardcoded set of numbers
   tuned against one figure.

   *Why it is more tractable than it sounds:* the jiggle/pectoral refactor already
   exposes every knob as a named keyword argument — `radius`, `max_weight`, `plateau`,
   `plateau_below`, `upper_scale`, `peak_depth`, `lower_limit_overshoot`,
   `vertical_reach`, `first_split`, `rod_angle_degrees`, `stretch_influence`. **A profile
   is just a dict of those kwargs.** No restructuring needed; the plumbing exists.

   *Measurement is cheap because topology is fixed.* Every G3F body is 17418 verts in the
   same order, so nothing needs ML - record bust / underbust / waist / hip / thigh /
   upper-arm vertex RINGS once, exactly as `butt_crease_L` was recorded, and a
   circumference is the sum of consecutive distances. `difeomorphic_workflow_init_custom_vertex_indices.py`
   already holds 12 region tables (`head_top`, `breast_top_`, `breast_base_`,
   `knee_center`, `elbow_center_`, ...) to build on, and `getCenter` is the helper.

   *Classify on SEPARATE AXES, not one flat label set.* The obvious tag list mixes
   independent things, which is what would make a single classifier thrash:

   | axis | measure | labels |
   |---|---|---|
   | proportion | bust / waist / hip ratios | hourglass, pear, apple, rectangle, inverted triangle |
   | mass | mesh volume / height^3 | skinny, average, thicc, fat, obese |
   | composition | (thigh + upperarm) / waist | bodybuilder vs voluptuous |
   | local signature | breast upper-pole convexity | implants; natural upper poles are straight-to-concave, implants convex |

   Wanted tags then become DERIVED from coordinates - "thicc" = pear/hourglass + high
   mass, "voluptuous" = hourglass + high mass + soft composition - so a new label is a
   rule, not another measuring pass. This is also why the operator likely wants two or
   three profile parameters rather than one.

   *Do not invent the proportion thresholds.* FFIT (Female Figure Identification
   Technique, NC State) is a published system using exactly bust/waist/hip cutoffs for
   those five shapes. Borrow its numbers.

   *Traps:* normalise every measurement by height or a tall thin figure reads as
   massive; and read the EVALUATED mesh, `obj.to_mesh(scene, True, 'PREVIEW')` in 2.79 -
   `obj.data.vertices` is the unmorphed cage when shape keys are live, which would
   measure the base body no matter what was loaded.

   *If a corpus ever exists:* PCA over delta-from-base vectors tends to recover mass and
   hourglass-ness as its first two components. Rule-based works on body one though.

6. Optional: `MESH_OT_clone_as_weighted_object` (`__init__.py:632`) is registered but in
   no panel — same as `gmtt.mesh_merge_weights`.
