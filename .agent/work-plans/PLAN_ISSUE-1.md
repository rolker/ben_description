# Plan: Replace wamv_description mesh references with simple geometry in jetdrive.xacro

## Issue

https://github.com/rolker/ben_description/issues/1

## Context

`urdf/jetdrive.xacro` references two mesh files from the `wamv_description` package
(part of VRX) for the engine and propeller visuals. The `package.xml` never listed
`wamv_description` as a dependency, so these are already broken references unless VRX
happens to be installed. Replacing them with primitive geometry makes `ben_description`
standalone — required for the `ben_gazebo` ROS 2 Jazzy port
([ben_gazebo#1](https://github.com/rolker/ben_gazebo/issues/1)).

## Approach

1. **Replace engine visual mesh with a box** — Change line 8 from
   `<mesh filename="package://wamv_description/models/engine/mesh/engine.dae"/>` to
   `<box size="0.2 0.15 0.6"/>`. Use the issue's proposed dimensions (0.2 x 0.15 x 0.6)
   which approximate the engine's visual profile. Add an `<origin>` to center the box
   roughly where the mesh was, using the existing collision origin as a reference
   (`xyz="-0.16 0 -0.24"`).

2. **Replace propeller visual mesh with a cylinder** — Change line 32 from
   `<mesh filename="package://wamv_description/models/propeller/mesh/propeller.dae"/>` to
   `<cylinder radius="0.1" length="0.05"/>`. Use the issue's proposed dimensions. Add an
   `<origin>` matching the collision origin (`xyz="-0.08 0 0" rpy="0 1.57 0"`).

3. **Verify xacro processes cleanly** — Run
   `xacro urdf/jetdrive.xacro namespace:=test prefix:=left_` and confirm no errors.

## Files to Change

| File | Change |
|------|--------|
| `urdf/jetdrive.xacro` | Replace 2 `<mesh>` elements with `<box>` and `<cylinder>` primitives, adding `<origin>` elements |

## Principles Self-Check

| Principle | Consideration |
|---|---|
| Only what's needed | Two visual elements changed, nothing else touched |
| A change includes its consequences | Collision and inertial properties unchanged. `ben_gazebo` uses this xacro but its port is a separate issue. Xacro validation confirms no breakage |
| Improve incrementally | Single focused change removing one external dependency |

## ADR Compliance

| ADR | Triggered | How addressed |
|---|---|---|
| 0002 — Worktree isolation | Yes | Working in `feature/issue-1` worktree, PR targets `jazzy` |

## Consequences

| If we change... | Also update... | Included in plan? |
|---|---|---|
| `jetdrive.xacro` visuals | Downstream users (`ben_gazebo/urdf/ben_thruster.xacro`) | No — `ben_gazebo` is a separate repo with its own port issue; the visual change doesn't affect how the macro is called |

## Open Questions

- **Engine visual origin**: Should the box visual use the same origin as the primary
  collision box (`xyz="-0.16 0 -0.24"`) or be centered at the link origin? Using the
  collision origin keeps visual and collision roughly aligned. Defaulting to collision
  origin unless directed otherwise.

## Estimated Scope

Single PR, single commit.
