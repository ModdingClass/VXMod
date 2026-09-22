# -*- coding: utf-8 -*-
"""
Sparse morph export for Unreal (VXMB).

Writes shape keys to a binary side-car INSTEAD OF into the FBX, for VersaMap to
inject after the import. The FBX importer spends most of its time pre-reading and
parsing blend shape channels, and a body with hundreds of them makes that the
dominant cost of every import and reimport.

Instead of, not as well as: exporter_unreal.py calls shape_key_clear() on the LOD
meshes once this file is safely on disk, because a .vxmb sitting beside an FBX that
still carries its blend shapes saves nothing at all.

This is NOT the same thing as the subdivision cache in exporter_unreal.py
(save_shapekey_subdiv_cache). That cache is internal bookkeeping: it stores
ABSOLUTE positions for EVERY vertex of the hi-res mesh so a re-export can skip
re-subdividing the shape keys. It is dense on purpose - it is a snapshot meant
to be pasted straight back onto a mesh.

What Unreal wants is the opposite: DELTAS, only for the vertices that actually
moved, for every LOD. Hence a separate writer rather than a flag on that one.

------------------------------------------------------------------------------
FORMAT (little-endian throughout)

  HEADER
    magic          4s    b'VXMB'
    version        u32   1
    flags          u32   bit 0 = normal deltas present
    fingerprint    16s   md5 of the BASE mesh's basis positions
    morph_count    u32
    lod_count      u32

  NAME TABLE                            morph_count entries, shared by all LODs
    name_len       u32
    name           utf-8 bytes

  PER LOD                               lod_count blocks, in LOD order
    lod_index      u32                  0 = hi-res/subdivided, 1 = base
    vert_count     u32                  total vertices in this LOD's mesh
    verify_count   u32
    verify_idx     u32 * verify_count   sampled vertex indices
    verify_pos     f32 * 3 * verify_count   their basis positions, BLENDER space

    then morph_count morph blocks, in name-table order:
      delta_count  u32
      indices      u32 * delta_count
      positions    f32 * 3 * delta_count
      normals      f32 * 3 * delta_count    only when flags bit 0 is set

Arrays are stored one after another rather than interleaved so each one is a
single bulk read on both sides.

------------------------------------------------------------------------------
WHY THERE IS A VERIFY BLOCK

The deltas are written in Blender's own local space. Getting them into Unreal's
means knowing which axis permutation, which signs and which scale the FBX
pipeline ended up applying - and that is decided by export settings, scene unit
scale and the FBX exporter's own conversion, all of which can be changed later
by someone who has no idea this file exists.

Rather than hardcode a convention and hope, every LOD carries a sample of its
basis positions. The Unreal side reads the same vertices out of the mesh it
just imported, tries the handful of plausible mappings, and takes the one whose
error is nil - or refuses to import the morphs at all and says why. A wrong
guess would otherwise produce morphs that are subtly, silently wrong.

------------------------------------------------------------------------------
NORMALS

Unreal derives a morph's normals from the morphed positions unless the morph
carries normal deltas, and deriving them is the expensive half of the build
(LODUtilities.cpp: PrepareTangents + ComputeTangents run per morph, per LOD,
and are skipped outright when the normal attribute is present).

Two things about granularity, both from the engine side:

  - Only the NORMAL is ever stored per morph. FMorphTargetDelta holds a
    PositionDelta and a TangentZDelta and nothing else, so there is no such
    thing as a per-morph tangent to export.
  - Unreal reads the normal delta from a vertex's FIRST vertex instance and
    ignores the others ("They all carry the same information for now"), so
    per-vertex normals are all it can consume. Split normals would be thrown
    away.

The delta is a difference of two normals computed the same way by the same
code, so it stays accurate even where Blender's smooth vertex normal is not
exactly the split normal Unreal holds for that vertex.
"""

import os
import struct

import bpy

# Guarded on purpose. __init__.py pulls this module in at addon registration, so a bare
# `import numpy` here would take the WHOLE addon down on a Blender whose Python never had
# numpy installed - every unrelated operator gone, over an optional export feature.
#
# Blender 2.79's own Python does ship a numpy, but this addon's copy has been replaced by a
# pip install (see NumpyDependency.md), and the only other import in the tree is armature.py,
# which CLAUDE.md records as dead code. So this module is the first place numpy is actually
# CALLED, and the first place worth failing politely.
try:
    import numpy as np
    NUMPY_IMPORT_ERROR = None
except ImportError as import_error:      # pragma: no cover - depends on the install
    np = None
    NUMPY_IMPORT_ERROR = str(import_error)


MORPH_BIN_MAGIC = b'VXMB'
MORPH_BIN_VERSION = 1

MORPH_BIN_FLAG_HAS_NORMALS = 1 << 0

# Sits next to the FBX and is found by name on the Unreal side, so the two must
# agree: SKM_<name>.fbx pairs with SKM_<name>.vxmb.
MORPH_BIN_SUFFIX = '.vxmb'

# A delta smaller than this is not worth a row, as a fraction of the mesh's bounding box
# diagonal. RELATIVE, and that is the whole point.
#
# The first version used a flat 1.0e-5, reasoned about as if the mesh were in metres. It is
# not: by the time this runs, transform_apply(scale=...) has already put the body in Unreal
# units, so BelaTest measures ~177 tall, not ~1.77. A float32 coordinate of that magnitude has
# an ULP of 1.53e-05 - so the threshold sat BELOW one unit in the last place and every shape
# key "moved" every vertex it could represent. Measured on a real export: 13,909 of 18,120
# vertices flagged for all 52 morphs, the shared component running 1.0e-5 to 3.3e-5 (one to two
# ULPs of pure rounding) while the real shapes measured 0.577 on average. A 54 MB file of noise
# wrapped around the signal.
#
# Scaling it to the mesh fixes it for any unit convention, which matters because nothing here
# gets to know what the export settings did. At 1e-6 of a ~245 unit diagonal the cut lands at
# 2.4e-4: sixteen times the rounding floor, and still sixty times finer than Unreal's own
# default morph threshold (0.015), so the engine keeps the final say on what counts as movement.
DEFAULT_POSITION_THRESHOLD_RELATIVE = 1.0e-6

# Normals are unit vectors, so this one is genuinely absolute - it does not scale with the mesh.
DEFAULT_NORMAL_THRESHOLD = 1.0e-2        # unit-vector difference

DEFAULT_VERIFY_SAMPLE_COUNT = 256


def _basis_positions(mesh):
    """The base mesh vertex positions, as a flat float32 array.

    Deliberately mesh.vertices rather than the Basis shape key: that is what the
    FBX exporter writes as the mesh, so it is what Unreal will hold, and it is
    what the deltas have to be relative to. It is also what
    compute_basis_fingerprint() hashes, so the two agree by construction.
    """
    count = len(mesh.vertices)
    out = np.empty(count * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", out)
    return out


def _shapekey_positions(mesh, name):
    """One shape key's absolute positions, as a flat float32 array."""
    key_block = mesh.shape_keys.key_blocks[name]
    out = np.empty(len(key_block.data) * 3, dtype=np.float32)
    key_block.data.foreach_get("co", out)
    return out


def _vertex_normals(temp_mesh, positions):
    """Per-vertex normals for a mesh posed at `positions`.

    One scratch mesh is reused for every shape key - copying a 70k mesh a few
    hundred times would cost more than the normals are worth, and only the
    vertex coordinates differ between the passes anyway.
    """
    temp_mesh.vertices.foreach_set("co", positions)
    temp_mesh.update()
    temp_mesh.calc_normals()

    out = np.empty(len(temp_mesh.vertices) * 3, dtype=np.float32)
    temp_mesh.vertices.foreach_get("normal", out)
    return out


def _pick_verify_samples(vert_count, sample_count):
    """Vertex indices spread evenly across the mesh.

    Evenly spaced rather than random so the result is reproducible, and spread
    rather than clustered so a mapping that happens to be right for one limb
    cannot pass for the whole mesh.
    """
    if vert_count <= 0:
        return np.empty(0, dtype=np.uint32)

    count = min(sample_count, vert_count)
    step = max(1, vert_count // count)
    return np.arange(0, vert_count, step, dtype=np.uint32)[:count]


def _write_u32(handle, value):
    handle.write(struct.pack('<I', int(value)))


def _write_f32_array(handle, values):
    handle.write(np.ascontiguousarray(values, dtype='<f4').tobytes())


def _write_u32_array(handle, values):
    handle.write(np.ascontiguousarray(values, dtype='<u4').tobytes())


def export_morph_bin(filepath,
                     lod_objects,
                     sk_names,
                     fingerprint,
                     include_normals=True,
                     position_threshold_relative=DEFAULT_POSITION_THRESHOLD_RELATIVE,
                     normal_threshold=DEFAULT_NORMAL_THRESHOLD,
                     verify_sample_count=DEFAULT_VERIFY_SAMPLE_COUNT):
    """Write every shape key of every LOD to `filepath` as sparse deltas.

    lod_objects is in LOD order - the same list the FBX export builds, so
    lod_objects[0] is the hi-res mesh and lod_objects[1] the base one. Every LOD
    is expected to carry the same shape key NAMES; the vertex counts differ and
    that is the whole reason each LOD gets its own block.

    Returns the number of bytes written, or None when there was nothing to do.
    """
    if np is None:
        raise RuntimeError(
            "[VXMB] numpy is required for the morph side-car but could not be imported ({}). "
            "See NumpyDependency.md in this addon for how to install it into Blender 2.79's "
            "Python, or untick 'Morph Side-Car (.vxmb)' to export without it."
            .format(NUMPY_IMPORT_ERROR))

    if not lod_objects or not sk_names:
        print("[VXMB] Nothing to export (no LODs or no shape keys)")
        return None

    flags = MORPH_BIN_FLAG_HAS_NORMALS if include_normals else 0

    normal_threshold_sq = float(normal_threshold) ** 2

    with open(filepath, 'wb') as handle:
        handle.write(MORPH_BIN_MAGIC)
        _write_u32(handle, MORPH_BIN_VERSION)
        _write_u32(handle, flags)
        handle.write(fingerprint)
        _write_u32(handle, len(sk_names))
        _write_u32(handle, len(lod_objects))

        for name in sk_names:
            name_bytes = name.encode('utf-8')
            _write_u32(handle, len(name_bytes))
            handle.write(name_bytes)

        for lod_index, lod_object in enumerate(lod_objects):
            mesh = lod_object.data
            vert_count = len(mesh.vertices)

            _write_u32(handle, lod_index)
            _write_u32(handle, vert_count)

            basis = _basis_positions(mesh)

            # Per LOD, because the two meshes are the same body at different resolutions and
            # should be cut at the same physical size, not the same fraction of whatever each
            # one happens to span.
            extent = basis.reshape(-1, 3)
            diagonal = float(np.linalg.norm(extent.max(axis=0) - extent.min(axis=0)))
            position_threshold = diagonal * float(position_threshold_relative)
            position_threshold_sq = position_threshold ** 2
            print("[VXMB] LOD{} bbox diagonal {:.3f} -> position threshold {:.3e}"
                  .format(lod_index, diagonal, position_threshold))

            verify_indices = _pick_verify_samples(vert_count, verify_sample_count)
            _write_u32(handle, len(verify_indices))
            _write_u32_array(handle, verify_indices)
            verify_positions = basis.reshape(-1, 3)[verify_indices]
            _write_f32_array(handle, verify_positions.ravel())

            temp_mesh = None
            base_normals = None
            if include_normals:
                temp_mesh = mesh.copy()
                base_normals = _vertex_normals(temp_mesh, basis)

                # Cheap guard against calc_normals() not having done what we
                # think it did - a silently zeroed normal array would poison
                # every delta in the file and look like a shading bug in Unreal
                # weeks later.
                lengths_sq = (base_normals.reshape(-1, 3) ** 2).sum(axis=1)
                if not np.allclose(lengths_sq, 1.0, atol=1.0e-3):
                    raise RuntimeError(
                        "[VXMB] LOD{} base normals are not unit length (min {:.4f}, "
                        "max {:.4f}). Re-export with normals turned off."
                        .format(lod_index, float(lengths_sq.min()), float(lengths_sq.max())))

            if mesh.shape_keys is None:
                # Every morph still needs a block, otherwise the name table and
                # the per-LOD data fall out of step for every LOD after this one.
                print("[VXMB] LOD{} ('{}') has no shape keys - writing empty blocks"
                      .format(lod_index, lod_object.name))
                for _ in sk_names:
                    _write_u32(handle, 0)
                if temp_mesh is not None:
                    bpy.data.meshes.remove(temp_mesh)
                continue

            key_blocks = mesh.shape_keys.key_blocks
            for name in sk_names:
                if name not in key_blocks:
                    print("[VXMB] LOD{} is missing shape key '{}' - writing an empty block"
                          .format(lod_index, name))
                    _write_u32(handle, 0)
                    continue

                morphed = _shapekey_positions(mesh, name)
                position_deltas = (morphed - basis).reshape(-1, 3)
                moved = (position_deltas ** 2).sum(axis=1) > position_threshold_sq

                normal_deltas = None
                if base_normals is not None:
                    normal_deltas = (_vertex_normals(temp_mesh, morphed)
                                     - base_normals).reshape(-1, 3)
                    # Union, not intersection. Unreal keeps a vertex whose
                    # NORMAL changed even when its position did not - a crease
                    # forming beside a vertex that never moves is a real shading
                    # change, and dropping it would show.
                    moved = moved | ((normal_deltas ** 2).sum(axis=1) > normal_threshold_sq)

                indices = np.nonzero(moved)[0].astype(np.uint32)

                _write_u32(handle, len(indices))
                _write_u32_array(handle, indices)
                _write_f32_array(handle, position_deltas[indices].ravel())
                if normal_deltas is not None:
                    _write_f32_array(handle, normal_deltas[indices].ravel())

                print("[VXMB] LOD{} {}: {} / {} vertices"
                      .format(lod_index, name, len(indices), vert_count))

            if temp_mesh is not None:
                bpy.data.meshes.remove(temp_mesh)

    size = os.path.getsize(filepath)
    print("[VXMB] Wrote {} morphs x {} LODs ({:.1f} MB) to {}"
          .format(len(sk_names), len(lod_objects), size / (1024.0 * 1024.0), filepath))
    return size
