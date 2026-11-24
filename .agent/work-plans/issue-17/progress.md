---
issue: 17
---

# Issue #17 — Check and port ben_description on ROS 2 Rolling, and add CI

## Issue Review
**Status**: complete
**When**: 2026-11-24 08:39 -05:00
**By**: Claude Code Agent (claude-sonnet-5-5)

**Issue**: #17

### Scope Assessment

**Well-scoped?** Yes. One small package (8 sensor xacros plus `ben_mesh.xacro`, `jetdrive.xacro`, 3 Python launch files, meshes, rviz config, environment hooks), one `rolling` branch, one CI workflow, backport by cherry-pick. Fits one PR.
**Right repo?** Yes. The description and its CI belong in `ben_description`.
**Serves**: none (the project states no goals or design document).
**Design picture?** No change. No project design document exists.
**Dependencies**: none blocking. Tracking issue rolker/unh_marine_autonomy#415. Consumers on Rolling: `unh_marine_simulation` (`marine_simulation`, declares `exec_depend ben_description`; `demo_boats_launch.py` runs `xacro ben_mesh.xacro namespace:=<n>` through `FindPackageShare`), and `ben_project11` (`ben_core_launch.py` includes `publish_state_launch.py`; its `.launch` files include a `load.launch` that this package does not have, ROS 1 leftovers). `ben_project11/package.xml` does not declare `ben_description`.

**State on Rolling today (checked on this machine, Rolling only; xacro 2.1.1)**
- `./build.sh --parallel-workers 4 --packages-up-to ben_description`: `Finished <<< ben_description [3.37s]`. The only stderr is the CMake warning "CMAKE_EXPORT_COMPILE_COMMANDS not used".
- `./test.sh --packages-select ben_description`: `0 tests, 0 errors, 0 failures, 0 skipped`. The package has no tests and no `ament_lint_auto` or `BUILD_TESTING` block, so a green test run proves nothing yet.
- `xacro` on every file under `urdf/`: exit 0. `ben_mesh.xacro` gives 555 lines, 32 `<link`; the 9 other files each give a 7-line empty result (macro libraries). `namespace:=ben` and the default give identical output. `check_urdf` parses it: robot `ben`, root `ben/base_link`.
- `ros2 launch ben_description {display,load,publish_state}_launch.py --show-args`: all three parse and list `namespace` (`load` also `parameter_name`). Not started for real (display needs rviz2 and a display).
- `ament_xmllint package.xml`: valid. `ament_copyright` and `ament_flake8` report problems in `launch/` (no copyright headers, style); these are not wired into any test, so they matter only if CI adds lint.
- None of the #415 causes found beyond cause 11 below. The mesh `BEN_shell.dae` is produced at configure time by `file(ARCHIVE_EXTRACT)` from `BEN_shell.tar.bz2` into the build tree and then installed; it exists in the install tree, so it works on Rolling.

**Undeclared dependencies (cause 11)**: `package.xml` has `joint_state_publisher`, `robot_state_publisher`, `xacro`, `ament_cmake_ros`. Used but not declared: `rviz2` (`display_launch.py`), `launch`, `launch_ros`, `ament_index_python` (all three launch files). `CMakeLists.txt` does `find_package(ament_cmake REQUIRED)` and declares `ament_cmake_ros` as the buildtool; this works because `ament_cmake_ros` pulls in `ament_cmake`, but `ament_cmake` is not declared. The `$(find ben_description)` and `package://ben_description` references are to the package itself.

**Same URDF on Rolling and Jazzy**: Jazzy is not installed here, so this is shown by CI. Both jobs run `xacro urdf/ben_mesh.xacro namespace:=ben` (against the install tree, so `$(find)` resolves as it does for users) and print `sha256sum` and line count of the output; a last step, or the Rolling job fetching the Jazzy job's artifact, compares them. Upload the processed URDF as an artifact from each job so a difference can be diffed. A difference means one of: a xacro version difference (xacro 2.0.x on Jazzy against 2.1.x on Rolling can differ in float formatting, whitespace or attribute order, which is cosmetic), or a real behaviour difference in how a macro or property evaluates (which would be a bug to fix in the xacro). Comparing after normalising with `check_urdf` or an XML canonicalisation (c14n) separates the two. Note Rolling's output is already identical between `namespace:=ben` and the default; the check should use one fixed argument.

### Principle Alignment

| Principle | Status | Notes |
|---|---|---|
| Only what's needed | OK | A port with no big changes; the issue names what it will not do. |
| A change includes its consequences | Action needed | Declare the undeclared dependencies in `package.xml` (`launch`, `launch_ros`, `ament_index_python`, `rviz2`, and `ament_cmake`) as part of the port, since `rosdep install` without `-r` in CI will not install what is not declared (cause 11). |
| Test what you build | Watch | The package has no tests, so "passes on Rolling and Jazzy" is vacuous unless the plan adds something. A small test (xacro processes, `check_urdf` parses, every `package://` path exists in the install tree) is the useful minimum; lint is optional and would need copyright headers and style fixes first. |

### ADR Applicability

| ADR | Triggered | Notes |
|---|---|---|
| ADR-0013 (progress.md entries) | Yes | This review is an `## Issue Review` entry. |
| ADR-0002 (worktree isolation) | Yes | Work runs in the issue worktree; the `rolling` branch exists on GitHub already (at the `jazzy` tip). |
| Others | No | Project-repo work, no workspace infrastructure change. |

### Consequences

- The CI workflow file is carried by both `rolling` and `jazzy` (one file, `if: (github.base_ref || github.ref_name) != 'jazzy'` on the Rolling job), in a commit separate from code fixes.
- `.agent/work-plans/` holds records only; keep them out of code commits.
- `ben_project11` should declare `exec_depend ben_description` (its repository, a follow-up, not this issue).

### Recommendations

- Add the missing dependency declarations to `package.xml` (`launch`, `launch_ros`, `ament_index_python`, `rviz2`; consider `ament_cmake` as buildtool) in one code commit that holds on Jazzy, then backport.
- Add a minimal test (processes with xacro, parses with `check_urdf`, `package://` and `$(find)` paths resolve), so the CI result means something; wire it so it runs under `test.sh`.
- In CI, print and compare a checksum of the processed `ben_mesh.xacro` URDF across the Jazzy and Rolling jobs, upload both as artifacts, and treat a difference as a finding to explain (xacro version formatting against a real difference) rather than an automatic failure.
- Track as a follow-up issue, not in this port: missing `load.launch` that `ben_project11`'s ROS 1 launch files include, `ben_project11` not declaring `ben_description`, `publish_state_launch.py` not passing `namespace` to xacro (so its URDF always uses `ben`), `display_launch.py` and `publish_state_launch.py` differing on that, and lint/copyright headers.

### Actions
- [ ] Declare the undeclared dependencies in `package.xml` (`launch`, `launch_ros`, `ament_index_python`, `rviz2`, and `ament_cmake`) as part of the port, since `rosdep install` without `-r` in CI will not install what is not declared (cause 11).
- [ ] Add the missing dependency declarations to `package.xml` (`launch`, `launch_ros`, `ament_index_python`, `rviz2`; consider `ament_cmake` as buildtool) in one code commit that holds on Jazzy, then backport.
- [ ] Add a minimal test (processes with xacro, parses with `check_urdf`, `package://` and `$(find)` paths resolve), so the CI result means something; wire it so it runs under `test.sh`.
- [ ] In CI, print and compare a checksum of the processed `ben_mesh.xacro` URDF across the Jazzy and Rolling jobs, upload both as artifacts, and treat a difference as a finding to explain (xacro version formatting against a real difference) rather than an automatic failure.
- [ ] Track as a follow-up issue, not in this port: missing `load.launch` that `ben_project11`'s ROS 1 launch files include, `ben_project11` not declaring `ben_description`, `publish_state_launch.py` not passing `namespace` to xacro (so its URDF always uses `ben`), `display_launch.py` and `publish_state_launch.py` differing on that, and lint/copyright headers.
