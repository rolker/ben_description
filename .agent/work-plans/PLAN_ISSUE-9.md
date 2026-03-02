# Plan: Clean URDF restart — restructure link tree and fix design issues

## Issue

https://github.com/rolker/ben_description/issues/9

## Context

The BEN URDF was ported from ROS 1 / Gazebo Classic and carries structural debt that
causes failures in Gz Harmonic: buoyancy doesn't work because mass/collision live on
`motion_sensor` instead of `base_link`, the convex hull mesh crashes ODE, sensor joints
use fake revolute types, and the jetdrive macro is never instantiated. The issue
proposes a clean restructure that fixes all 8 problems in one coherent change.

### Key design constraint (from maintainer)

`motion_sensor` is **not a legacy artifact** — it is the physical reference frame for
the POSMV MRU. GPS and heading sensor positions are defined relative to this frame and
must stay parented to it. In previous Gazebo versions, water level for buoyancy was
assumed to be at `base_link`, so `base_link` should remain at its current origin
(waterline reference) with `motion_sensor` as a child at the MRU's physical offset.

### Current state (verified from source)

- **`ben_mesh.xacro`**: empty `base_link` at waterline origin; all content on
  `motion_sensor` via fixed joint offset `(0.911, 0.018, 0.532)` — the offset combines
  negative CG coordinates with a 0.35 m buoyancy offset
- **`jetdrive.xacro`**: defines `engine` macro with parent `motion_sensor`, header
  says "wam-v-two-engines", macro never called from `ben_mesh.xacro`
- **`oem_gps.xacro`**: revolute joint with `lower="0.0" upper="0"` (fake fixed)
- **`oem_heading_sensor.xacro`**: revolute joint (fake fixed), empty link (no visual,
  no collision, no inertial)
- **`radar.xacro`**: visual geometry commented out
- **`pano_camera.xacro`**: separate rotate + translate joints via intermediate `_base`
  link per camera
- **Mesh files**: `BEN_convex_hull.tar.bz2`, `BEN_shell.tar.bz2` (compressed DAE archives)
- **`display.launch`**: ROS 1 XML launch file — needs porting to ROS 2 Python
- **Default branch**: `jazzy` (not `main`)

### Proposed link tree

```
base_link (hull: mass, visual=BEN_shell.dae, collision=low-poly shell)
├── motion_sensor (fixed, physical POSMV MRU offset — NOT deprecated)
│   ├── gps (fixed)
│   └── heading (fixed, with inertial)
├── lidar (fixed)
├── radar (fixed, with visible geometry)
├── pano (fixed, camera enclosure housing)
│   ├── pano_1 (fixed, single joint)
│   │   ├── pano_1_optical (fixed)
│   │   └── pano_1_optical_rviz_mesh (fixed)
│   ├── pano_2 … pano_6 (same pattern)
├── forward_camera (fixed)
│   └── forward_camera_optical (fixed)
├── mbes (fixed)
└── engine_link (revolute about Z for steering)
    └── propeller_link (continuous about X)
```

GPS and heading stay under `motion_sensor` (POSMV reference frame).
All other sensors parent to `base_link` (hull-mounted).

## Approach

### Phase 1: Survey offsets section + hull restructure (ben_mesh.xacro)

0. **Add a survey offsets block** at the top of `ben_mesh.xacro` — a clearly labeled
   section with named xacro properties for every physical measurement that would
   change after a resurvey. Each property gets a comment stating what it is, what
   frame it's relative to, and where the value came from. This makes resurvey updates
   a one-section edit instead of a scavenger hunt across files.

   ```xml
   <!-- ============================================================
        Survey offsets — UPDATE THIS SECTION AFTER RESURVEY
        All positions in meters.
        Source: OnShape CAD model / field survey YYYY-MM-DD
        ============================================================ -->

   <!-- Hull properties (from OnShape) -->
   <xacro:property name="hull_mass" value="950" />
   <xacro:property name="cg_x" value="-0.911" />  <!-- CG relative to mesh origin -->
   ...

   <!-- POSMV MRU location (relative to base_link) -->
   <xacro:property name="mru_x" value="0.911" />
   <xacro:property name="mru_y" value="0.018" />
   <xacro:property name="mru_z" value="0.532" />

   <!-- Sensor positions relative to base_link (hull-mounted) -->
   <xacro:property name="lidar_x" value="-1.98" />
   <xacro:property name="lidar_y" value="0.0" />
   <xacro:property name="lidar_z" value="1.403" />
   ...

   <!-- Sensor positions relative to motion_sensor (POSMV-mounted) -->
   <xacro:property name="gps_x" value="-0.953" />
   <xacro:property name="gps_y" value="0.103" />
   <xacro:property name="gps_z" value="0.628" />
   ...
   ```

   Currently, offsets are scattered: some are inline macro args in `ben_mesh.xacro`,
   some are defaults buried in individual sensor xacro files (e.g. `mbes.xacro`
   defaults `z=-1.0`), and `heading` has no position at all (silently at
   motion_sensor origin). After this change, all survey-dependent values live in
   one block with the macro calls referencing these properties.

1. **Move hull content to `base_link`** — transfer mass, visual (`BEN_shell.dae`),
   inertial, and collision from `motion_sensor` to `base_link`. Keep `base_link` at
   its current origin (waterline reference for buoyancy). Use properties from the
   survey offsets block for CG and inertia values.

2. **Create low-polygon collision mesh** — use a mesh simplification tool (e.g.
   `meshlab` with quadric edge collapse decimation, or `blender` decimate modifier)
   to create `BEN_shell_collision.dae` from `BEN_shell.dae` — targeting ~200-500
   faces, watertight, with normals. This replaces the degenerate 8578-vertex convex
   hull that crashes ODE.

3. **Simplify `motion_sensor` link** — remove visual/collision/inertial from
   `motion_sensor` (now on `base_link`), but keep the link and fixed joint using the
   `mru_x/y/z` survey properties. `motion_sensor` becomes a lightweight reference
   frame for POSMV sensors. Add a small inertial (e.g. sensor mass) so it isn't
   dropped during URDF→SDF conversion.

### Phase 2: Sensor fixes

4. **`oem_gps.xacro`** — change joint type from `revolute` to `fixed`, remove
   `<axis>` and `<limit>` elements. **Keep parent as `motion_sensor`** (GPS is
   physically relative to the POSMV).

5. **`oem_heading_sensor.xacro`** — same revolute→fixed fix. Add `<inertial>` block
   (small mass). **Keep parent as `motion_sensor`**.

6. **`radar.xacro`** — uncomment the visual geometry cylinder. Change parent from
   `motion_sensor` to `base_link` (hull-mounted sensor).

7. **All other hull-mounted sensors** (`lidar.xacro`, `forward_camera.xacro`,
   `mbes.xacro`, `pano_array.xacro`) — change parent from `motion_sensor` to
   `base_link`. Remove default position values from macro definitions; positions
   come from the survey offsets block in `ben_mesh.xacro` via macro args.

### Phase 3: Pano camera simplification

8. **`pano_camera.xacro`** — collapse the two-joint chain (rotate `_base` + translate)
   into a single fixed joint with combined origin. Remove intermediate `_base` link.
   Keep `_optical` and `_optical_rviz_mesh` child links unchanged.

### Phase 4: Jetdrive

9. **Instantiate jetdrive** — add `<xacro:include>` and `<xacro:engine>` call in
   `ben_mesh.xacro` at the stern position. Update parent link from `motion_sensor`
   to `base_link` in `jetdrive.xacro`.

10. **Fix jetdrive header** — change `name="wam-v-two-engines"` to
    `name="ben_jetdrive"`.

### Phase 5: Launch file + cleanup

11. **Port `display.launch` to `display_launch.py`** — ROS 2 Python launch file that
    starts `robot_state_publisher`, `joint_state_publisher`, and rviz with the
    existing `rviz/urdf.rviz` config. Remove the old `display.launch`.

12. **`rviz/urdf.rviz`** — no changes needed; `motion_sensor` frame still exists in
    the tree so existing references remain valid.

13. **Replace `BEN_convex_hull` with low-poly mesh** — delete
    `models/meshes/BEN_convex_hull.tar.bz2`, add `BEN_shell_collision.dae` (or
    `.tar.bz2`). Update `CMakeLists.txt` install lines accordingly.

### Phase 6: Verification

14. **xacro parse test** — `xacro ben_mesh.xacro` completes without errors.

15. **check_urdf** — `check_urdf <(xacro ben_mesh.xacro)` shows all links with
    inertials and no warnings.

16. **robot_state_publisher smoke test** — `ros2 launch ben_description
    publish_state_launch.py` starts cleanly.

17. **display_launch.py smoke test** — `ros2 launch ben_description
    display_launch.py` opens rviz with the model visible.

18. **Link tree inspection** — verify the tree matches the proposed design.

## Files to Change

| File | Change |
|------|--------|
| `urdf/ben_mesh.xacro` | Add survey offsets block, move hull to base_link, simplify motion_sensor to reference frame, instantiate jetdrive |
| `urdf/jetdrive.xacro` | Fix header, change parent to base_link |
| `urdf/sensors/oem_gps.xacro` | revolute→fixed (keep parent=motion_sensor) |
| `urdf/sensors/oem_heading_sensor.xacro` | revolute→fixed, add inertial (keep parent=motion_sensor) |
| `urdf/sensors/radar.xacro` | Uncomment visual, parent→base_link |
| `urdf/sensors/lidar.xacro` | parent→base_link |
| `urdf/sensors/forward_camera.xacro` | parent→base_link |
| `urdf/sensors/mbes.xacro` | parent→base_link |
| `urdf/sensors/pano_array.xacro` | parent→base_link |
| `urdf/sensors/pano_camera.xacro` | Collapse two-joint chain to single joint, remove _base link |
| `launch/display_launch.py` | New: ROS 2 port of display.launch |
| `launch/display.launch` | Delete (replaced by display_launch.py) |
| `CMakeLists.txt` | Update mesh install lines (remove convex hull, add collision mesh) |
| `models/meshes/BEN_convex_hull.tar.bz2` | Delete |
| `models/meshes/BEN_shell_collision.dae` | New: low-polygon collision mesh |

## Principles Self-Check

| Principle | Consideration |
|---|---|
| A change includes its consequences | rviz config still valid (motion_sensor frame preserved). CMakeLists updated. Launch file ported. Downstream repos unaffected — motion_sensor frame unchanged. |
| Improve incrementally | Single coherent PR; problems are structurally entangled but the change is well-scoped to one package. |
| Test what breaks | xacro parse, check_urdf, robot_state_publisher, and rviz display tests cover the regressions that matter. |
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
| Move hull content from motion_sensor to base_link | ben_gazebo plugins that target base_link for buoyancy/hydrodynamics | ben_gazebo#5 tracks this; motion_sensor frame is preserved so sensor plugins are unaffected |
| Replace BEN_convex_hull.dae with low-poly mesh | CMakeLists.txt install lines | Yes |
| Collapse pano camera joint chain | Any code referencing `pano_N_base` frames | Yes — internal frames, not used externally |
| Change GPS/heading from revolute to fixed | joint_state_publisher no longer publishes states for these joints | Yes — desired behavior |
| Port display.launch to display_launch.py | Any scripts referencing the old launch file | Yes — old file removed |

## Open Questions

1. **Collision mesh origin** — `BEN_shell.dae` was rendered relative to
   `motion_sensor`; after moving it to `base_link`, the mesh origin may need an
   `<origin>` offset on the visual/collision geometry. Need to inspect the DAE to
   determine where its internal origin sits relative to the hull.
2. **Heading sensor position** — currently has no xyz offset (defaults to
   motion_sensor origin). Is that correct, or does it need a survey offset?

## Estimated Scope

Single PR with atomic commits: hull restructure → sensor fixes → pano simplification
→ jetdrive → launch port + cleanup.

---
**Authored-By**: `Claude Code Agent`
**Model**: `Claude Opus 4.6`
