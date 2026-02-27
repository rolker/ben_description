# Plan: Add ament environment hooks for GZ_SIM_RESOURCE_PATH

## Issue

https://github.com/rolker/ben_description/issues/3

## Context

`ben_gazebo` references meshes via `model://ben_description/models/meshes/...` URIs.
Gz Harmonic resolves these by searching `GZ_SIM_RESOURCE_PATH`. Currently no path
includes `ben_description`'s install share directory, so all mesh loads fail at launch.

VRX solves this with ament environment hooks — small files processed during
`source install/setup.bash` that prepend paths to `GZ_SIM_RESOURCE_PATH`. We follow
the same pattern used by `vrx_gazebo/hooks/resource_paths.{dsv.in,sh}`.

## Approach

1. **Create `hooks/resource_paths.dsv.in`** — Machine-readable hook (colcon's
   preferred format). Adds the install share root to `GZ_SIM_RESOURCE_PATH` using
   `prepend-non-duplicate`. The share root (not a package-specific subpath) is
   required because URIs start with the package name:
   `model://ben_description/models/meshes/...`.

2. **Create `hooks/resource_paths.sh`** — Shell fallback hook using
   `ament_prepend_unique_value`. Same path, alternative mechanism.

3. **Register hooks in `CMakeLists.txt`** — Add two `ament_environment_hooks()`
   calls before `ament_package()`.

4. **Verify** — Build, re-source, confirm `GZ_SIM_RESOURCE_PATH` includes the
   share directory.

## Files to Change

| File | Change |
|------|--------|
| `hooks/resource_paths.dsv.in` | New file: `prepend-non-duplicate;GZ_SIM_RESOURCE_PATH;@CMAKE_INSTALL_PREFIX@/share/` |
| `hooks/resource_paths.sh` | New file: `ament_prepend_unique_value GZ_SIM_RESOURCE_PATH "$AMENT_CURRENT_PREFIX/share"` |
| `CMakeLists.txt` | Add `ament_environment_hooks()` calls before `ament_package()` |

## Principles Self-Check

| Principle | Consideration |
|---|---|
| Only what's needed | 3 small files, no unnecessary abstraction |
| A change includes its consequences | No downstream changes required — `ben_gazebo` already uses `model://` URIs that will resolve once the path is set |
| Improve incrementally | Focused fix for a concrete launch failure |

## ADR Compliance

| ADR | Triggered | How addressed |
|---|---|---|
| 0002 — Worktree isolation | Yes | Working in `feature/issue-3` worktree |

## Consequences

| If we change... | Also update... | Included in plan? |
|---|---|---|
| `CMakeLists.txt` | No downstream references to update | N/A |

## Open Questions

None — the approach is well-defined and matches established VRX patterns.

## Estimated Scope

Single PR, single commit.
