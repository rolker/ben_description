# Plan: Clean URDF restart — restructure link tree and fix design issues

## Issue

https://github.com/rolker/ben_description/issues/9

## Context

The BEN URDF was ported from ROS 1 / Gazebo Classic and carries structural debt that
causes failures in Gz Harmonic: buoyancy doesn't work because mass/collision live on
`motion_sensor` instead of `base_link`, the convex hull mesh crashes ODE, sensor joints
use fake revolute types, and the jetdrive macro is never instantiated. The issue
proposes a clean restructure that fixes all 8 problems in one coherent change.

### Current state (verified from source)

- **`ben_mesh.xacro`**: empty `base_link`, all content on `motion_sensor` via fixed joint with buoyancy offset hack
- **`jetdrive.xacro`**: defines `engine` macro with parent `motion_sensor`, header says "wam-v-two-engines", macro never called
- **`oem_gps.xacro`**: revolute joint with `lower="0.0" upper="0"` (fake fixed)
- **`oem_heading_sensor.xacro`**: revolute joint (fake fixed), empty link (no visual, no collision, no inertial)
- **`radar.xacro`**: visual geometry commented out (`<!-- <cylinder ...> -->`)
- **`pano_camera.xacro`**: separate rotate + translate joints via intermediate `_base` link per camera
- **Mesh files**: `BEN_convex_hull.tar.bz2`, `BEN_shell.tar.bz2` (compressed DAE archives)
- **Default branch**: `jazzy` (not `main`)

### Downstream references to `motion_sensor` (outside ben_description)

| File | Repo |
|------|------|
| `ben_gazebo/launch/gazebo.launch.py` (4 refs) | ben_gazebo |
| `ben_gazebo/urdf/sensors/posmv_mru.xacro` | ben_gazebo |
| `asv_sim/config/ben.yaml` (`mru_frame`) | unh_marine_simulation |
| `ben_project11/config/operator.rviz` | ben_project11 |
| `ben_project11/config/ben.rviz` | ben_project11 |
| `ben_description/rviz/urdf.rviz` | ben_description (this repo) |

## Approach

### Phase 1: Hull restructure (ben_mesh.xacro + jetdrive.xacro)

1. **Move hull content to `base_link`** — transfer mass (950 kg), visual (`BEN_shell.dae`),
   and inertial from `motion_sensor` to `base_link`. Remove the buoyancy offset hack.
   The CG origin stays on `base_link`'s inertial (no offset joint needed).

2. **Replace collision mesh with box primitive** — instead of `BEN_convex_hull.dae`,
   use a `<box size="4.25 1.7 0.8"/>` approximation matching the hull footprint
   (from the commented coordinates in `ben_mesh.xacro`). Position the box collision
   at the CG origin. This is sufficient for buoyancy volume and won't crash ODE.

3. **Add `motion_sensor` as a fixed-joint alias** — to avoid breaking all downstream
   references at once, keep a `motion_sensor` link as a fixed child of `base_link`
   with identity transform. This preserves the TF frame while downstream repos
   migrate. Mark it with an XML comment: `<!-- DEPRECATED: use base_link -->`.

4. **Instantiate jetdrive** — add `<xacro:include>` and `<xacro:engine>` call in
   `ben_mesh.xacro` at the stern position. Update parent link from `motion_sensor`
   to `base_link` in `jetdrive.xacro`.

5. **Fix jetdrive header** — change `name="wam-v-two-engines"` to `name="ben_jetdrive"`.

### Phase 2: Sensor fixes

6. **`oem_gps.xacro`** — change joint type from `revolute` to `fixed`, remove
   `<axis>` and `<limit>` elements. Change parent from `motion_sensor` to `base_link`.

7. **`oem_heading_sensor.xacro`** — same revolute→fixed fix. Add `<inertial>` block
   (small mass, e.g. 0.5 kg with appropriate inertia). Change parent to `base_link`.

8. **`radar.xacro`** — uncomment the visual geometry cylinder. Change parent to `base_link`.

9. **All other sensors** (`lidar.xacro`, `forward_camera.xacro`, `mbes.xacro`,
   `pano_array.xacro`) — change parent link from `motion_sensor` to `base_link`.

### Phase 3: Pano camera simplification

10. **`pano_camera.xacro`** — collapse the two-joint chain (rotate `_base` + translate)
    into a single fixed joint with combined origin. Remove intermediate `_base` link.
    Keep the `_optical` and `_optical_rviz_mesh` child links unchanged.

### Phase 4: Cleanup and rviz

11. **`rviz/urdf.rviz`** — update `motion_sensor` frame references to `base_link`.

12. **Remove `BEN_convex_hull` mesh** — delete `models/meshes/BEN_convex_hull.tar.bz2`
    and remove the corresponding `INSTALL` line from `CMakeLists.txt`.

13. **`display.launch`** — this is a ROS 1 launch file; leave as-is or remove if
    no longer needed (ask user).

### Phase 5: Verification

14. **xacro parse test** — `xacro ben_mesh.xacro` completes without errors.

15. **check_urdf** — `check_urdf <(xacro ben_mesh.xacro)` shows all links with
    inertials and no warnings.

16. **robot_state_publisher smoke test** — `ros2 launch ben_description
    publish_state_launch.py` starts cleanly.

17. **Link tree inspection** — verify the tree matches the proposed design from the issue.

## Files to Change

| File | Change |
|------|--------|
| `urdf/ben_mesh.xacro` | Move hull to base_link, add deprecated motion_sensor alias, instantiate jetdrive |
| `urdf/jetdrive.xacro` | Fix header, change parent to base_link |
| `urdf/sensors/oem_gps.xacro` | revolute→fixed, parent→base_link |
| `urdf/sensors/oem_heading_sensor.xacro` | revolute→fixed, add inertial, parent→base_link |
| `urdf/sensors/radar.xacro` | Uncomment visual, parent→base_link |
| `urdf/sensors/lidar.xacro` | parent→base_link |
| `urdf/sensors/forward_camera.xacro` | parent→base_link |
| `urdf/sensors/mbes.xacro` | parent→base_link |
| `urdf/sensors/pano_array.xacro` | parent→base_link |
| `urdf/sensors/pano_camera.xacro` | Collapse two-joint chain to single joint, remove _base link |
| `rviz/urdf.rviz` | Update motion_sensor refs to base_link |
| `CMakeLists.txt` | Remove BEN_convex_hull install line |
| `models/meshes/BEN_convex_hull.tar.bz2` | Delete file |

## Principles Self-Check

| Principle | Consideration |
|---|---|
| A change includes its consequences | rviz config and CMakeLists updated in same PR. Downstream repos (ben_gazebo, ben_project11, unh_marine_simulation) need separate PRs — mitigated by keeping `motion_sensor` as deprecated alias so nothing breaks immediately. |
| Improve incrementally | This is a large change, but the 8 problems are structurally entangled (all stem from the motion_sensor indirection). The deprecated alias approach lets downstream repos migrate incrementally. |
| Test what breaks | xacro parse, check_urdf, and robot_state_publisher smoke test cover the regressions that matter. |
| Only what's needed | Each change maps to a documented problem. No speculative additions. |

## ADR Compliance

| ADR | Triggered | How addressed |
|---|---|---|
| ADR-0002 Worktree isolation | Yes | Working in `feature/issue-9` worktree |
| ADR-0001 Adopt ADRs | No | Issue body documents design rationale sufficiently |
| ADR-0003 Project-agnostic workspace | No | Project repo change only |

## Consequences

| If we change... | Also update... | Included in plan? |
|---|---|---|
| Remove `motion_sensor` as primary link | ben_gazebo plugins, rviz configs, asv_sim config | Partially — deprecated alias preserves TF frame; downstream PRs tracked in ben_gazebo#5 |
| Remove `BEN_convex_hull.dae` | CMakeLists.txt install line | Yes |
| Collapse pano camera joint chain | Any code that references `pano_N_base` frames | Yes — those frames are internal to the URDF, not used externally |
| Change GPS/heading from revolute to fixed | `joint_state_publisher` will no longer publish states for these joints | Yes — this is the desired behavior (they shouldn't have been revolute) |

## Open Questions

1. **`display.launch`** is a ROS 1 XML launch file — should it be removed or kept for reference?
2. **Box collision dimensions** — `4.25 x 1.7 x 0.8` is estimated from the footprint comments. Should we refine these from CAD data?
3. **Deprecated `motion_sensor` alias** — how long should it be kept? Should downstream repos be updated in a coordinated batch, or is a deprecation period acceptable?
4. **Sub-PRs vs single PR** — the review comment recommended splitting (hull → sensors → jetdrive). Given the entanglement, a single PR with well-organized commits may be more practical. Preference?

## Estimated Scope

Single PR with 4-5 atomic commits (hull restructure, sensor fixes, pano simplification, jetdrive instantiation, cleanup). Could split into sub-PRs if preferred.

---
**Authored-By**: `Claude Code Agent`
**Model**: `Claude Opus 4.6`
