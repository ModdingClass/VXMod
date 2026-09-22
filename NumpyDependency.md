# numpy in Blender 2.79b

Why this addon needs numpy, what is actually installed on this machine, and how to put it back
on a Blender that does not have it.

Written 2026-09-22, from the install at
`E:\devtools\3D\blender-2.79b-windows64\2.79\python`.

---

## The short version

```bat
cd /d "E:\devtools\3D\blender-2.79b-windows64\2.79\python\bin"
python.exe get-pip.py
python.exe -m pip install "numpy==1.18.5"
```

Run it against **Blender's** `python.exe`, never a system Python. Pin the version — the
current numpy will not install here.

---

## What depends on it

| Module | Uses numpy | Live? |
|---|---|---|
| `exporter_morph_bin.py` | Yes — the whole sparse delta computation | **Yes** |
| `armature.py` | `import numpy as np` at line 4 | **No** — `CLAUDE.md` records it as confirmed dead code, imported by `__init__.py:42` but never called |

So numpy is already a **load-time** requirement today, because `__init__.py` imports
`armature.py` unconditionally. But nothing has ever *called* it. `exporter_morph_bin.py` is
the first module that does real work with it.

That distinction matters for one reason: `CLAUDE.md` recommends deleting `armature.py`. Doing
so is still correct, but afterwards numpy stops being incidental and becomes a dependency this
addon genuinely has. Do not treat "numpy imports fine" as evidence that it is unused.

### The failure is contained, deliberately

`exporter_morph_bin.py` wraps its import in a `try`/`except` and only raises when the export is
actually run. A bare `import numpy` there would take the **entire addon** down at registration
on a Blender without it — every unrelated operator and panel gone, because of one optional
export feature. `armature.py` does not guard its import, which is a second, quieter reason to
delete it.

If numpy is missing you get a readable error naming this file, and everything else in the addon
keeps working. Untick **Morphs to Side-Car, not FBX (.vxmb)** and the export runs as it always did.

---

## What is installed here, and how it got there

`2.79/python/lib/site-packages`:

| Package | Version | Installed |
|---|---|---|
| pip | 20.3.4 | 2023-08-10 10:43 |
| setuptools | 50.3.2 | 2023-08-10 10:43 |
| wheel | 0.37.1 | 2023-08-10 10:43 |
| scipy | 1.4.1 | 2023-08-10 10:47 |
| numpy | 1.18.5 | 2023-08-10 10:51 |
| requests | — | 2021-06-04 (separate, earlier) |

This is **not** the stock Blender bundle. The evidence:

- `numpy-1.18.5.dist-info/INSTALLER` contains the single word `pip`.
- `2.79/python/bin/get-pip.py` is still sitting there, 1.9 MB, dated 2023-08-10 10:43. Its
  header says *"an entire copy of pip (version 20.3.4)"*.
- Stock Blender 2.79b (2018) ships neither pip, setuptools, wheel, nor scipy.

Blender 2.79 *does* bundle a numpy of its own. This one has been replaced.

---

## Why the versions are pinned

Blender 2.79b embeds **CPython 3.5**, 64-bit (`2.79/python/bin/python35.dll`). Every installed
wheel is tagged for it — e.g. `numpy/core/_multiarray_umath.cp35-win_amd64.pyd`.

Python 3.5 went end-of-life in September 2020, and the versions on disk are, in each case, the
**last release that still published a cp35 wheel**:

| Package | Pin | Why |
|---|---|---|
| pip | `20.3.4` | Last pip supporting Python 3.5 |
| numpy | `1.18.5` | Last numpy series with cp35 wheels (`Requires-Python: >=3.5`) |
| scipy | `1.4.1` | Same (`Requires-Python: >=3.5`) |
| setuptools | `50.3.2` | Last supporting Python 3.5 |

A plain `pip install numpy` will either refuse outright, or — worse on an older pip — try to
build from source and leave a half-installed package behind. **Always pin.**

scipy is not needed by this addon and is listed only so nobody assumes it is load-bearing.

---

## Bootstrapping a Blender that does not have it

### 1. Find Blender's own Python

```
<blender>\2.79\python\bin\python.exe
```

Never the system Python, never `py -3`. Blender only ever looks in its own
`2.79/python/lib/site-packages`, and a module installed into a system 3.5 will not be found —
or worse, a module built for a different minor version will be found and crash on import.

Confirm you have the right one:

```bat
python.exe -c "import sys; print(sys.version); print(sys.executable)"
```

It must say `3.5.x` and a path inside the Blender folder.

### 2. Get pip in

`get-pip.py` is already present in this install. If it is missing elsewhere, the Python 3.5
build is pinned and archived:

```
https://bootstrap.pypa.io/pip/3.5/get-pip.py
```

The version-less `https://bootstrap.pypa.io/get-pip.py` installs a **modern** pip that will not
run on 3.5. Use the `/pip/3.5/` path.

```bat
cd /d "<blender>\2.79\python\bin"
python.exe get-pip.py
```

### 3. Install numpy

```bat
python.exe -m pip install "numpy==1.18.5"
```

If the machine has no compiler and pip tries to build from source, force a wheel:

```bat
python.exe -m pip install --only-binary=:all: "numpy==1.18.5"
```

### 4. Verify from inside Blender

The only check that counts. Blender's Python console:

```python
import numpy
print(numpy.__version__, numpy.__file__)
```

Expect `1.18.5` and a path under `2.79/python/lib/site-packages`. If the version is right but
the path points outside Blender, something else is on `sys.path` and it will break the moment
that folder moves.

Then confirm the addon agrees:

```python
from io_vxmod_workflow import exporter_morph_bin
print(exporter_morph_bin.NUMPY_IMPORT_ERROR)   # None when numpy imported cleanly
```

---

## Permissions

Blender under `Program Files` needs an **elevated** command prompt for any of the above, or pip
fails with `Access is denied` part-way through and can leave `site-packages` in a mixed state.
This install lives under `E:\devtools\`, so it does not.

---

## If numpy cannot be installed

The morph side-car is the only feature that needs it, and it is optional. Untick **Morph
Side-Car (.vxmb)** in the export panel and the FBX export behaves exactly as it did before —
shape keys go into the FBX as blend shapes, and Unreal imports them the slow way.

A pure-Python fallback is possible but has not been written, and would not be pleasant: the
delta scan is roughly (vertex count × shape key count) iterations — around 29 million for a
71.5k hi-res mesh with 400 keys, per LOD. numpy does that in milliseconds; a Python loop takes
tens of seconds to minutes. If it is ever needed, the three functions to rewrite are
`_basis_positions`, `_shapekey_positions` and the delta/threshold block inside
`export_morph_bin` — everything else in that module is plain Python already.

---

## The other dependency

numpy is not the only thing this addon needs from outside itself. It also requires the sibling
addon **`io_game_mod_tiny_tools`** ("Game Mod Tiny Tools", operator prefix `gmtt`) for
`bpy.ops.gmtt.object_strip_and_clean`, which the export uses to strip shape keys, vertex groups,
materials and modifiers from its temporary meshes.

Both are now caught up front by `check_export_dependencies()`, which runs before the export
touches anything, but they differ in scope:

- **numpy missing** - only the morph side-car is affected. The export is refused only when that
  checkbox is ticked; untick it and everything else works, because the import is guarded and
  the rest of the addon never needed numpy.
- **gmtt missing** - no export at all. Seven call sites depend on it and there is no substitute
  for what it does.

See `README.md` for the full requirements table.

## Related

- `exporter_morph_bin.py` — the module, with the format documented in its docstring
- `CLAUDE.md` — environment notes, and the `armature.py` dead-code finding
- `Plugins/VersaMap/` in the Unreal project — the other half of this pipeline, which reads the
  `.vxmb` and injects the morphs after the FBX import
