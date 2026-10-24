# Daz HD morphs (.dhdm), level 1 -> vertex offsets for the subdivided LOD0.
#
# Plain Python (no bpy), so it can be tested outside Blender. The format and the maths are
# the ones written down (and verified against Daz Studio's own subdivision-1 export) in the
# VXMod UE project: Docs/VersaDazHDMorphs.md, sections 3-5.
#
# Use: the exported body already HAS the character's shape (e.g. a G8F character converted to
# G3F), and only the HD part of its HD morph is wanted. The frames come from the body's own
# base positions, so the morph's .dsf deltas are never applied here.
#
# A subdivided vertex is identified by WHAT it is, as a sorted tuple of base vertex indices:
# (v,) = base vertex, (a, b) = edge point, (a, b, c, d) = face point. That is the same key as
# the "base_indices" of <name>_vertex_mapping_list.json.

import gzip
import json
import math
import os
import struct

try:
    from urllib.parse import unquote
except ImportError:
    from urllib import unquote

DHDM_MAGIC = 0xd0d0d0d0


def load_dsf(path):
    raw = open(path, 'rb').read()
    if raw[:2] == b'\x1f\x8b':
        raw = gzip.decompress(raw)
    return json.loads(raw.decode('utf-8'))


def find_in_library(start_path, url):
    """A Daz URL ('/data/...#id') -> file, searched from start_path's folder upwards.

    Daz URLs are relative to a content directory; the start file lives inside one."""
    rel = unquote(url.split('#')[0]).lstrip('/')
    d = os.path.dirname(os.path.abspath(start_path))
    while True:
        cand = os.path.join(d, *rel.split('/'))
        if os.path.isfile(cand):
            return cand
        up = os.path.dirname(d)
        if up == d:
            return None
        d = up


def resolve_hd_files(path):
    """.dsf (with morph.hd_url) or .dhdm -> (dhdm path, figure .dsf path or None, morph name).

    The figure comes from the morph's 'parent' URL. A .dhdm on its own names no figure, so the
    caller falls back to G3F's own file (see find_figure)."""
    if path.lower().endswith('.dhdm'):
        return path, None, os.path.splitext(os.path.basename(path))[0]
    dsf = load_dsf(path)
    mods = [m for m in dsf.get('modifier_library', []) if m.get('morph', {}).get('hd_url')]
    if not mods:
        raise ValueError('{} has no HD part (no morph.hd_url)'.format(os.path.basename(path)))
    mod = mods[0]
    dhdm = find_in_library(path, mod['morph']['hd_url'])
    if dhdm is None:
        raise IOError('HD file not found: {}'.format(unquote(mod['morph']['hd_url'])))
    figure = None
    if mod.get('parent'):
        figure = find_in_library(path, mod['parent'])
    return dhdm, figure, mod.get('name', mod.get('id', ''))


G3F_FIGURE_URL = '/data/DAZ%203D/Genesis%203/Female/Genesis3Female.dsf'


def find_figure(hd_path, figure_path=None):
    if figure_path:
        return figure_path
    return find_in_library(hd_path, G3F_FIGURE_URL)


_FACES_CACHE = {}


def figure_faces(figure_path):
    """Corners of every base face in Daz's own order (polylist), cached per file."""
    key = (os.path.abspath(figure_path), os.path.getmtime(figure_path))
    if key not in _FACES_CACHE:
        geo = load_dsf(figure_path)['geometry_library'][0]
        faces = [tuple(f[2:]) for f in geo['polylist']['values']]
        _FACES_CACHE.clear()
        _FACES_CACHE[key] = (faces, geo['vertices']['count'])
    return _FACES_CACHE[key]


def read_dhdm(path):
    """-> (level-1 records [(face, [(subface, corner, dx, dy, dz), ...]), ...], {level: edits})."""
    d = open(path, 'rb').read()
    magic, _, _, nlevels = struct.unpack_from('<IIfI', d, 0)
    if magic != DHDM_MAGIC:
        raise ValueError('{} is not a .dhdm file'.format(os.path.basename(path)))
    p = 16
    records, counts = [], {}
    for _ in range(nlevels):
        _, level, nedits, size = struct.unpack_from('<IIII', d, p)
        p += 16
        counts[level] = nedits
        if level == 1:
            q, end = p, p + size
            while q < end:
                f, n = struct.unpack_from('<II', d, q)
                q += 8
                items = []
                for _ in range(n):
                    x, hi, tag, y, z = struct.unpack_from('<fBBff', d, q)
                    q += 14
                    if tag != 0x20:
                        raise ValueError('unexpected level-1 item tag 0x{:02x}'.format(tag))
                    idx = hi << 8
                    items.append((idx >> 14, (idx >> 12) & 3, x, y, z))
                records.append((f, items))
            if q != end:
                raise ValueError('level-1 block size mismatch in {}'.format(os.path.basename(path)))
        p += size
    return records, counts


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(a):
    l = math.sqrt(a[0] * a[0] + a[1] * a[1] + a[2] * a[2])
    if l < 1e-20:
        return (0.0, 0.0, 0.0)
    return (a[0] / l, a[1] / l, a[2] / l)


def level1_offsets(records, faces, positions, unit):
    """Level-1 HD offsets per subdivided vertex key, in the space of `positions`.

    faces      Daz corner order per base face (figure_faces)
    positions  base cage, any rotated space (frames are built from it), as (x, y, z) tuples
    unit       length of 1 cm in that space (0.01 for metres)
    -> ({key: (dx, dy, dz)}, number of records whose face is missing in `faces`)

    Child quad `subface` s of face f has the ring [v_s, edge(v_s, v_s+1), face f,
    edge(v_s-1, v_s)]; `corner` c picks ring[(c - s) mod 4]. Frame per base corner s:
    z = norm(cross(v_s+1 - v_s, v_s-1 - v_s)), x = norm(v_s-1 - v_s), y = cross(z, x);
    offset = x*dx + z*dy - y*dz. A vertex touched by several child faces gets the SUM."""
    out = {}
    missing = 0
    for f, items in records:
        if f >= len(faces):
            missing += 1
            continue
        corners = faces[f]
        n = len(corners)
        fkey = tuple(sorted(corners))
        frames = {}
        for s, c, dx, dy, dz in items:
            fr = frames.get(s)
            if fr is None:
                p0 = positions[corners[s]]
                pn = positions[corners[(s + 1) % n]]
                pp = positions[corners[(s - 1) % n]]
                ez = _norm(_cross(_sub(pn, p0), _sub(pp, p0)))
                ex = _norm(_sub(pp, p0))
                ey = _cross(ez, ex)
                fr = frames[s] = (ex, ey, ez)
            ex, ey, ez = fr
            k = (c - s) % 4
            if k == 0:
                key = (corners[s],)
            elif k == 1:
                key = tuple(sorted((corners[s], corners[(s + 1) % n])))
            elif k == 2:
                key = fkey
            else:
                key = tuple(sorted((corners[s], corners[(s - 1) % n])))
            a, b, e = dx * unit, dy * unit, -dz * unit
            o = out.get(key, (0.0, 0.0, 0.0))
            out[key] = (o[0] + ex[0] * a + ez[0] * b + ey[0] * e,
                        o[1] + ex[1] * a + ez[1] * b + ey[1] * e,
                        o[2] + ex[2] * a + ez[2] * b + ey[2] * e)
    return out, missing


def check_faces(faces, mesh_faces):
    """How many figure faces the mesh has (same corner set). mesh_faces = iterable of corner tuples."""
    have = set(tuple(sorted(f)) for f in mesh_faces)
    return sum(1 for f in faces if tuple(sorted(f)) in have)


def unit_from_edges(faces, figure_positions_cm, positions, sample=4000):
    """1 cm in the space of `positions`, from the median edge-length ratio against the figure's
    own base (cm). Robust to any import scale; a character's shape moves it by ~1%."""
    ratios = []
    step = max(1, len(faces) // sample)
    for f in faces[::step]:
        a, b = f[0], f[1]
        lc = math.sqrt(sum(x * x for x in _sub(figure_positions_cm[a], figure_positions_cm[b])))
        lm = math.sqrt(sum(x * x for x in _sub(positions[a], positions[b])))
        if lc > 1e-9:
            ratios.append(lm / lc)
    ratios.sort()
    return ratios[len(ratios) // 2] if ratios else None


def figure_positions(figure_path):
    geo = load_dsf(figure_path)['geometry_library'][0]
    return [tuple(v) for v in geo['vertices']['values']]
