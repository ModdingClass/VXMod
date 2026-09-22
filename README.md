# TK17-Custom-Bodies-plugin
VXMod is a Blender plugin to export Daz bodies to Unreal

Current builds Requires Good Old Blender 2.79

## Requirements

| Requirement | Why | Notes |
|---|---|---|
| **Blender 2.79b** | The whole addon targets the 2.79 Python API | Newer Blender will not run it |
| **Game Mod Tiny Tools** (`io_game_mod_tiny_tools`) | Export calls `gmtt.object_strip_and_clean` to strip shape keys, vertex groups, materials and modifiers from the temporary export meshes | **Required, not optional** — export fails without it. Install and enable it alongside this addon |
| **numpy** (pinned `1.18.5`) | The sparse morph side-car (`exporter_morph_bin.py`) | Must be installed into Blender's own Python. See `NumpyDependency.md` |

`io_game_mod_tiny_tools` is a sibling addon by the same author. Only one of its 23 operators is
used here, but the export depends on it completely. `check_export_dependencies()` verifies it
before the export touches anything and stops with a message naming the addon, so a missing
install no longer surfaces as an `AttributeError` several hundred lines in.

