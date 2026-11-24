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

## Checkpoint
**Status**: complete
**When**: 2026-11-24 08:39 -05:00
**By**: Claude Code Agent (claude-fable-5-2)
**Decided-by**: host (the issue review found the issue well scoped; its actions are for the planner and none changes what the work is for or its scope)
**After**: issue-actions
**Decision**: proceed

Read: the Issue Review, status complete. For the planner: (1) cause 11: `package.xml` lacks `launch`, `launch_ros`, `ament_index_python` and `rviz2`, which the launch files use, and `ament_cmake` as a build tool; one code commit that holds on Jazzy. (2) The package has no tests, so "passes" means nothing yet: the plan adds the smallest test that has teeth (xacro processes, the URDF parses, `package://` and `$(find)` paths resolve) and says what it would catch; this is within the issue's scope because its "Done when" asks for CI that passes. Linters are not added unless the plan shows they pass or the fixes are trivial (a port makes no big changes; lint failures in existing launch files go to a follow-up issue). (3) "Same URDF on Rolling as on Jazzy" is shown in CI: each job processes `ben_mesh.xacro` from the install tree and prints a checksum and line count of a canonical form; the plan says how the two are compared and that a difference is a finding to explain, not an automatic failure. The items the review lists for a follow-up issue (a `namespace` argument not passed to xacro in `publish_state_launch.py`, lint in `launch/`, and three items that belong to rolker/ben_project11) are left alone here.

## Plan Authored
**Status**: complete
**When**: 2026-11-24 08:52 -05:00
**By**: Claude Code Agent (claude-opus-5-5)
**Plan**: `.agent/work-plans/issue-17/plan.md` at `3c1ff46`

Three commits, each backported by cherry-pick: declare `ament_cmake`, `ament_index_python`, `launch`, `launch_ros`, `rviz2` (cause 11); add a pytest test that processes `ben_mesh.xacro` from the install tree (default and `namespace:=boat2`), runs `check_urdf`, resolves every mesh and `$(find)` path and loads the three launch files (each check shown to fail on a deliberate break); add a CI workflow with Jazzy and Rolling jobs and a `compare-urdf` job that diffs a C14N form of the URDF (xacro is 2.1.1 on both distros), warning rather than failing on a difference. Jazzy is verified by CI only.

## Plan Review
**Status**: complete
**When**: 2026-11-24 08:55 -05:00
**By**: Claude Code Agent (claude-opus-5-5)
**Verdict**: needs-work

**Issue**: #17 — Check and port ben_description on ROS 2 Rolling, and add CI
**Plan**: `.agent/work-plans/issue-17/plan.md` at `3c1ff46`
**Branch**: `feature/issue-17`

Owner direction received during this review (relayed by the host), recorded here. The owner asked: "So, a robot can use the description file but not use rviz. Does an exec depend get pulled in for a build? What's the cleanest way to handle this?" The host answered that `rosdep install --from-paths` installs run-time dependencies too and a released package's `exec_depend`s become hard dependencies, and decided (the owner may still change it): **the port does not declare `rviz2`**; `display_launch.py` stays as it is; `package.xml` gets a short comment that the display launch file needs `rviz2`, left undeclared on purpose so vehicles do not install a viewer; moving the display launch file and its rviz configuration into an operator-side or `_viz` package that declares `rviz2` goes on the follow-up list. `launch`, `launch_ros`, `ament_index_python` and the `ament_cmake` build tool are still declared.

### Evaluation

| Dimension | Verdict | Notes |
|---|---|---|
| Scope | Good | Three commits (package.xml, test, CI), 4 files; fits one PR and the owner's one-fix-per-commit backport rule. |
| Issue alignment | Needs work | `rviz2` must go per the host's decision (finding 1). The issue asks to *start* the launch files and fix what fails; the plan only loads them, and `load_launch.py` fails when started (finding 2). Serves: "None stated (the project has no goals or design document); the port tracked in rolker/unh_marine_autonomy#415." Acceptable: the project keeps no goals. |
| File targeting | Good | `package.xml`, `CMakeLists.txt`, `test/test_description.py`, `.github/workflows/ci.yml`. If finding 2 is fixed in the port, `launch/load_launch.py` is added in its own commit. |
| Consequences | Needs work | The `rviz2` row ("consumers' installs gain rviz2, accepted") is reversed by the host's decision; the follow-up list gains the `_viz` move. Consumers checked: `marine_simulation` declares `rviz2`, `robot_state_publisher`, `joint_state_publisher` itself; `ben_project11` declares none of them nor `ben_description`. |
| Principle alignment | Good | Test with teeth, shown to fail on breaks (three repeated here, see below); minimal route with alternatives named. |
| ADR compliance | Good | ADR-0013 (records in progress.md, out of code commits), ADR-0002 (worktree; scratch builds outside the source tree). No other ADR triggered. |
| ROS conventions | Good | Dependency kinds right (`exec_depend` for launch-time Python, `test_depend` for test tools); `ament_add_pytest_test` is the standard registration. CI detail in findings 3 and 4. |

### Checks made for this review

- **Test mechanics (Rolling, scratch workspaces, `env -i`, only `/opt/ros/rolling` sourced).** `CMAKE_INSTALL_PREFIX` is `install/` in a merged layout and `install/ben_description` in the isolated layout (the CI default); both prefixes carry `share/ament_index`, so prepending the prefix to `AMENT_PREFIX_PATH` makes xacro's `$(find ben_description)` resolve to the installed tree in both, with and without `--symlink-install`. An equivalent checker on both layouts: xacro rc 0, `check_urdf` `root Link: <ns>/base_link`, 32 links all prefixed, 5 filenames all present, for the default and `boat2`.
- **Breaks repeated** (my own checker, same checks a–d): collision-mesh typo — only (d) catches it, `check_urdf` passes; lidar parent `base_lnk` — (b) fails for both namespaces with "parent link [<ns>/base_lnk] ... not found"; lidar link and joint child hard-coded `ben/` — `check_urdf` passes, only the (c) prefix check fails, and only for `boat2`. All three agree with the plan's table. (Side note: an incremental rebuild within the same second left a stale installed xacro; the planner's clean rebuilds avoid this, and CI is always clean.)
- **`check_urdf` from `urdfdom`**: `ros-jazzy-urdfdom` 4.0.2 deb (noble index) contains `/opt/ros/jazzy/bin/check_urdf`; Rolling's has `/opt/ros/rolling/bin/check_urdf`. `rosdep resolve`: `urdfdom` → `ros-jazzy-urdfdom` (noble) / `ros-rolling-urdfdom` (resolute); every other planned key resolves on both.
- **rosdistro**: xacro `2.1.1-1` (jazzy) / `2.1.1-2` (rolling); urdfdom `4.0.2-1` / `6.0.2-1`; Python 3.12 (noble) / 3.14.4 (here). The planner's correction of the issue review holds.
- **Action versions**: latest `upload-artifact` v7.0.2, `download-artifact` v8.0.2, `checkout` v7.0.1 (v6.1.0 exists). v8 download reads v4+-style artifacts; v8's breaking changes (no unzip of non-zipped downloads, digest mismatch errors) do not affect a default zipped v7 upload.
- **Workflow against `marine_colormap`'s**: `set -u` before sourcing `setup.bash` fails here ("AMENT_TRACE_SETUP_FILES: unbound variable"); the model never sources under `-u` (its `set -euo` step does not source), so `set -eo pipefail` after the `source` matches it. The mesh archive is a plain bzip2 file (not LFS); `file(ARCHIVE_EXTRACT)` uses CMake's libarchive (linked to libbz2), so no `tar`/`bzip2` binary is needed. `needs: [jazzy, rolling]` with no `if:` is skipped when `rolling` is skipped, so `compare-urdf` does not run on `jazzy`, as the plan says.
- **Canonical form**: C14N 2.0 keeps attribute values, element order and non-blank text verbatim, so a changed number, value, order or text shows; it hides only attribute order, comments and whitespace-only text, which do not change a URDF. A false difference needs the generator to format differently (same xacro; Python's shortest float repr unchanged between 3.12 and 3.14). A `::warning::` shows as an annotation on the run page and in the job summary, not on the green tick; adequate for "a finding to explain, not a failure" as the checkpoint set.
- **Loading `display_launch.py` without `rviz2`**: a `launch_ros` `Node` with a non-existent package constructs without error, and all three launch files load with `get_launch_description_from_python_launch_file`; the package is looked up only when the node is executed. So check (f) passes in a container without rviz2.
- **Launch files started on Rolling** (`ROS_DOMAIN_ID=173`, localhost only): `publish_state_launch.py namespace:=boat2` starts both nodes; `load_launch.py` fails (finding 2).
- **Multi-vehicle simulation**: `demo_boats_launch.py` runs its own `robot_state_publisher` with `xacro ... namespace:=<n>`; no simulator launch includes `publish_state_launch.py`, `load_launch.py` or `ben_core_launch.py` (it uses its own nav2 composed launch). Only `ben_project11`'s `ben_core_launch.py` includes `publish_state_launch.py`, on a single real boat named `ben`. Leaving the namespace gap to a follow-up is consistent with the owner's no-big-changes rule.

### Findings

1. **[Issue alignment] (high)** — Per the host's decision recorded above, commit 1 must drop `<exec_depend>rviz2</exec_depend>` and add a short `package.xml` comment that `display_launch.py` needs `rviz2`, left undeclared on purpose so vehicles do not install a viewer. Follow through in the plan: the Consequences row and Open Question 1 change; the "Alternative weighed ... Rejected" text and the `urdf_tutorial` prior-art line are superseded; the CI time estimate drops the 1 to 2 min it added for rviz; the follow-up list gains "move `display_launch.py` and `rviz/urdf.rviz` into an operator-side or `_viz` package that declares `rviz2`"; the pull request's cause-11 statement says plainly that one used dependency, `rviz2`, is left undeclared and why. Check (f) is unaffected (loading needs no rviz2, checked). No other declared or planned dependency has rviz's character: `joint_state_publisher` (the non-GUI one), `robot_state_publisher` and `xacro` are what a vehicle runs to publish the description; `launch`, `launch_ros`, `ament_index_python` are launch infrastructure; `ament_cmake_pytest` and `urdfdom` are `test_depend` (and `urdfdom` already arrives through `robot_state_publisher` → `urdf`). Nothing GUI remains.
2. **[Issue alignment] (medium)** — The issue's scope says "start its launch files there; fix what fails". Started on Rolling, `load_launch.py` fails: "Caught exception in launch: Failed to convert '<?xml ...' using yaml rules". Its `ParameterValue(Command([...]))` has no `value_type=str`, so launch parses the URDF as YAML, and the comment "Source: OnShape CAD model" (added in `c5049ce`, 2026-03-02) is not valid YAML. `launch`'s `type_utils.py` and `launch_ros`'s `parameter_descriptions.py` behave the same on the `jazzy` branches (diff is type annotations only), so it fails on Jazzy too: a pre-existing defect, not a port break. No consumer in the Rolling clones uses `load_launch.py`. Check (f) cannot see it (it only loads). The plan should say it started each launch file it can (display needs a display) and either fix this (one line, `value_type=str`, its own commit, holds on Jazzy) or put it on the follow-up list; which is the host's or owner's choice.
3. **[ROS conventions] (low)** — In the container jobs, give `upload-artifact` a relative `path: ci-urdf/` (or the container path from `$GITHUB_WORKSPACE`), not `${{ github.workspace }}/ci-urdf`: in container jobs the `github.workspace` context is the host path, not the container's `/__w/...`, a known source of "No files were found".
4. **[ROS conventions] (low)** — `compare-urdf` with plain `needs:` is also skipped when either distro job fails at any later step (the test), although both artifacts were already uploaded after Build; the comparison is lost when it could explain a failure. Optional: `if: ${{ !cancelled() && needs.jazzy.result != 'skipped' && needs.rolling.result != 'skipped' }}` keeps it skipped on `jazzy` and runs it after a test failure (a build failure before upload would then fail the download step, which is visible).
5. **[Principle alignment] (low)** — The hard-coded 32-link count is worth keeping: it is the only check that catches a sensor's include and call removed together. Give the assertion a message saying to update the count when a link is added or removed on purpose, so it reads as a guard and not a trap.
6. **[Record] (low)** — The `## Plan Authored` entry's **When** is `08:52 -05:00`, but its commit `96e1d01` is at 08:47 and this review began before 08:52; correct the time in a later entry or leave a note.

### Summary

The plan is sound in its test design, comparison and CI shape: the test exercises the installed tree in merged and isolated layouts, its breaks reproduce, `check_urdf` ships on both distros under `urdfdom`, xacro is 2.1.1 on both, and the workflow matches the model. It needs two changes before implementation: drop `rviz2` with the comment and its knock-on edits (host decision), and deal with `load_launch.py` failing when started (fix or follow-up, the owner's or host's choice).

### Recommended Actions

- [ ] Commit 1: remove `rviz2`, add the `package.xml` comment; update Consequences, Open Question 1, Prior Art, CI time estimate, follow-up list (`_viz` move) and the PR's cause-11 text.
- [ ] Record a start of each launch file on Rolling; fix `load_launch.py` (`value_type=str`, own commit) or add it to the follow-up list.
- [ ] CI: relative `path: ci-urdf/` for `upload-artifact` in container jobs.
- [ ] Optional: `compare-urdf` condition that survives a test failure but stays skipped on `jazzy`.
- [ ] Test: assertion message on the 32-link count.

## Checkpoint
**Status**: complete
**When**: 2026-11-24 08:53 -05:00
**By**: Claude Code Agent (claude-fable-5-2)
**Decided-by**: host (the plan review's verdict is needs-work, but each of its six findings has a concrete, settled correction that the implementer applies and records; a second plan round would add nothing a code review does not check; none changes the issue's scope)
**After**: plan
**Decision**: proceed

Read: the Plan Review at `3c1ff46`, verdict needs-work, six findings. How each is applied, overriding the plan where they differ. (1) **`rviz2` is not declared.** The owner asked on 2026-11-24: "So, a robot can use the description file but not use rviz. Does an exec depend get pulled in for a build? What's the cleanest way to handle this?" It would be installed on every vehicle that installs the description (`rosdep install` takes run-time dependencies; a released package's `exec_depend`s are hard dependencies), so commit 1 declares `launch`, `launch_ros`, `ament_index_python` and the `ament_cmake` build tool only, and `package.xml` gets a short comment that `display_launch.py` needs `rviz2`, left undeclared on purpose so vehicles do not install a viewer. The follow-up list gains: move `display_launch.py` and `rviz/urdf.rviz` into an operator-side or `_viz` package that declares `rviz2`. The pull request says plainly that one used dependency is left undeclared and why. The owner was told this and may change it. (2) **`load_launch.py` is fixed in this port**, in a commit of its own: `value_type=str` on its `ParameterValue`, so the URDF is not parsed as YAML (it fails to start on both distros today; the issue's scope says "start its launch files there; fix what fails"); the same parameter in `publish_state_launch.py` is checked and treated the same way if it has the same form; the implementer starts each launch file it can on Rolling (the display one needs a display) and records the result. The alternative was the follow-up list. (3) `upload-artifact` gets a relative path, not `${{ github.workspace }}`. (4) `compare-urdf` runs when neither distro job was skipped, so it still runs after a test failure. (5) The 32-link assertion carries a message saying to update the count when a link is added or removed on purpose. (6) The plan entry's time is off by a few minutes; noted here, not corrected.

## Implementation
**Status**: complete
**When**: 2026-11-24 09:02 -05:00
**By**: Claude Code Agent (claude-opus-5-5)
**Branch**: feature/issue-17 at `da581b7`

Four commits, one fix each, none touching `.agent/` (each cherry-picks onto `jazzy`; `origin/jazzy` and `origin/rolling` are both at `b9edcac`, so they apply as they are). Each ends "Backport to jazzy."; 1 and 4 name rolker/unh_marine_autonomy#415.

1. `3880ba6` Declare the build tool and launch dependencies the package uses — `package.xml`: `ament_cmake` buildtool; `ament_index_python`, `launch`, `launch_ros` as `exec_depend`; an XML comment that `display_launch.py` needs `rviz2`, left undeclared on purpose so vehicles do not install a viewer. `ament_xmllint`: valid.
2. `0813adc` Pass the processed URDF from load_launch.py as a string — `value_type=str` on its `ParameterValue`. `display_launch.py` and `publish_state_launch.py` already have `value_type=str`: not changed.
3. `28fbda7` Add a test of the installed description — `test/test_description.py`, `ament_add_pytest_test` (`ENV BEN_DESCRIPTION_INSTALL_PREFIX`, `TIMEOUT 60`), `test_depend` `ament_cmake_pytest`, `urdfdom`. 15 pytest cases: xacro, `check_urdf` root, 32 links prefixed (message: update the count when a link is added or removed on purpose), mesh files installed (each for default and `boat2`); `$(find)` paths installed; each launch file loads and declares `namespace`; plus, added, every `ParameterValue` in the launch files is `value_type=str` (AST, 9 lines, no process started). `ament_flake8`, `ament_pep257` on `test/`: no problems.
4. `da581b7` Add CI building and testing on Jazzy and Rolling — `.github/workflows/ci.yml` as planned, with `upload-artifact` `path: ci-urdf/` (relative) and `compare-urdf` `if: ${{ !cancelled() && needs.jazzy.result != 'skipped' && needs.rolling.result != 'skipped' }}`; `set -eo pipefail` after the two `source`s. Nothing in the jobs needs `rviz2` (`rosdep keys` on the package: `ament_cmake ament_cmake_pytest ament_cmake_ros ament_index_python joint_state_publisher launch launch_ros robot_state_publisher urdfdom xacro`).

### Verification (Rolling only)

- Package worktree: `./build.sh --parallel-workers 4 --packages-up-to ben_description` → `Summary: 1 package finished [0.15s]`; `./test.sh --parallel-workers 4 --packages-select ben_description` → `15 passed in 0.32s`, `Summary: 16 tests, 0 errors, 0 failures, 0 skipped`.
- Scratch workspaces, `env -i`, only `/opt/ros/rolling/setup.bash`: merged (`--merge-install`), isolated, isolated `--symlink-install`: each `Summary: 16 tests, 0 errors, 0 failures, 0 skipped`.
- Launch files started (`ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST`, domains 161–163, each checked empty first and after), stopped with SIGINT:
  - before commit 2: `publish_state_launch.py namespace:=boat2` (domain 161): `/boat2/robot_state_publisher` and `/boat2/joint_state_publisher` up, `robot_description` root `ben/base_link` (namespace not passed to xacro, left alone). `load_launch.py` (161): fails, "Caught exception in launch: Failed to convert '<?xml ...' using yaml rules ... line 10, column 14: Source: OnShape CAD model". `display_launch.py namespace:=boat3` (163): started on this machine's forwarded X display (`DISPLAY=localhost:11.0`); `robot_state_publisher` root `boat3/base_link`, rviz2 reports OpenGL 4.5; rviz2 needed SIGKILL to stop (launch escalated after 15 s).
  - after commit 2: `load_launch.py` alone: rc 0, no error (it only sets a global parameter). Included from a scratch wrapper with `parameter_name:=robot_description` and a `robot_state_publisher` in `boat2` (162): the node **dies**: rcl "Couldn't parse parameter override rule: '-p robot_description:=<?xml ...'". `launch_ros` passes global parameters as `-p name:=value` (`node.py` line 431, the same on its `jazzy` branch) and rcl parses the value as YAML, so a URDF cannot reach a node through `SetParameter`. Not fixed (a redesign, not a port fix); on the follow-up list. `publish_state_launch.py` and `display_launch.py`: as before.
- Deliberate breaks, scratch copies, clean isolated builds (failure counts include the ctest):
  - commit 2 reverted: `test_launch_urdf_passed_as_string[load_launch.py]` — "load_launch.py:28: no value_type=str" (2 failures);
  - mesh typo `forward_camerra.dae`: `test_mesh_files_installed[default|boat2]` — "not installed: ['package://ben_description/models/meshes/forward_camerra.dae']" (3);
  - lidar parent `base_lnk`: `test_check_urdf_parses[default|boat2]` — "parent link [boat2/base_lnk] of joint ... not found" (3);
  - lidar link and joint child hard-coded `ben/`: `test_links_namespaced[boat2]` only — "links not prefixed boat2/: ['ben/lidar']" (2).
- Rolling job rehearsed: its `run:` blocks taken from `ci.yml` and run in order in `env -i` (`ROS_DISTRO=rolling` as the image sets it; apt and rosdep init/update skipped; `rosdep install` with `--simulate`: nothing to install, rc 0). Build, Processed URDF, Test, Test results all rc 0; "Processed URDF": `xacro 2.1.1`, `urdfdom 6.0.2`, `Python 3.14.4`; raw `ben.urdf` 555 lines, sha256 `ef1fb08f49fd8dc5dccec0bf8d2b1d93a16c0e8739708c541ad588b18f9f7b6e`; canonical `ben.c14n.urdf` 624 lines, sha256 `d893e417a1a3231ad7c55448fc52fc522876da0ede167634ff18157477c56144` (both as the plan found). Comparison step fed two copies: "Canonical URDFs are identical on Jazzy and Rolling."; with the lidar `xyz` altered to `-1.0690000000000002` in one copy: the diff in log and summary and `::warning title=URDF differs::...`, rc 0.

### Differs from the plan or checkpoint

- Commit 2 fixes the launch-level failure, but `load_launch.py` still cannot deliver a URDF to a node (global parameter via `-p`, above); the checkpoint expected the one line to make it work. Recorded and listed for follow-up.
- The test has 15 pytest cases, not 6 (parametrized by namespace and launch file), plus the `value_type=str` check.
- `publish_state_launch.py` did not need the fix (it already has `value_type=str`).

### For the pull request

- Cause 11: `ament_cmake` (build tool), `ament_index_python`, `launch`, `launch_ros` are now declared. One used dependency, `rviz2` (started by `launch/display_launch.py`), is left undeclared on purpose: a declared `exec_depend` is installed by `rosdep install` and is a hard dependency of the released package, so every vehicle that only uses the description would install a viewer. `package.xml` says so; the machine that runs the display installs `rviz2` itself.
- The test checks the installed package: xacro processes `ben_mesh.xacro` (default and `namespace:=boat2`); urdfdom's `check_urdf` parses it with root `<namespace>/base_link`; 32 links, all namespaced; every mesh and `$(find)` path is installed; each launch file loads, declares `namespace` and passes the URDF as a string. It does not start nodes, load meshes in a renderer, or run Gazebo's URDF-to-SDF conversion.
- URDF comparison: each job prints line count and sha256 of the raw xacro output and of an XML C14N form, uploads both, and `compare-urdf` diffs the canonical forms, warning (not failing) on a difference. It shows whether the two distros' xacro produce the same URDF text up to attribute order, comments and whitespace (any changed value, element order or text shows). It cannot tell how consumers read it on each distro (robot_state_publisher, rviz, Gazebo); each job's `check_urdf` passing is the parser evidence.
- `load_launch.py` now starts, but cannot yet deliver the URDF to a node (follow-up).

### Left alone (follow-up issue in this repository)

- `publish_state_launch.py` and `load_launch.py` do not pass `namespace` to xacro (frames always `ben/...`).
- `load_launch.py`: a URDF in a global parameter (`SetParameter`) reaches nodes as `-p name:=<xml>`, which rcl rejects; it needs a redesign or removal (no consumer in the Rolling clones uses it).
- Lint in `launch/` (no copyright headers; 15 flake8 findings), `file (` spacing in `CMakeLists.txt`; `load_launch.py`'s unused imports.
- `ament_cmake_ros` buildtool unused; `joint_state_publisher`, `robot_state_publisher` as `depend` where `exec_depend` would do; licence `BSD` not an SPDX name.
- `install(DIRECTORY models)` also installs the 33 MB `BEN_shell.tar.bz2` next to the extracted mesh.
- Move `display_launch.py` and `rviz/urdf.rviz` into an operator-side or `_viz` package that declares `rviz2`.

For rolker/ben_project11#30 (host relays): its `package.xml` does not declare `ben_description`; `replay_bag.launch`, `operator_mystique.launch`, `remote_operator.launch` include `$(find ben_description)/launch/load.launch`, which does not exist; `ben_core_launch.py` includes `publish_state_launch.py`, whose `namespace` does not reach the URDF.

### Unverified

Nothing has run on Jazzy (Ubuntu 26.04 here, no Jazzy, no Docker): strict rosdep on noble, the build, the test, `check_urdf` from urdfdom 4.0.2 and Python 3.12. The pull request's first CI run is the first Jazzy evidence, this repository's first CI run, and the first comparison of the two distros' URDFs. The `uses:` steps (checkout, upload, download) and the `if:` expressions were not run locally.

## Local Review (Pre-Push)
**Status**: complete
**When**: 2026-11-24 09:07 -05:00
**By**: Claude Code Agent (claude-opus-5-5)
**Verdict**: changes-requested

**Branch**: feature/issue-17 at `85d779e`
**Base**: origin/rolling
**Depth**: Deep (reason: 434 code lines (860 with records), new `.github/workflows/ci.yml`)
**Must-fix**: 1 | **Suggestions**: 4
**Round**: 1 | **Ship**: continue — round 1: 1 must-fix; first round always re-reviews after fixes (the one must-fix is mechanical)

Specialists: static analysis (xmllint `package.xml` valid; workflow YAML parses; flake8 on the test: one I100 that ament's google import style does not report), governance, plan drift, a fresh Claude adversarial reviewer, Gemini and Codex (both complete). Dropped as settled or not material: `rviz2` undeclared (Gemini 4, Codex 1; owner decision, the reviewers were given the plan's old text); the `load_launch.py` commit being outside the plan (Gemini 12; checkpoint point 2); `jazzy` having no workflow yet (Codex 5; the backport comes after merge); `.agent/` records in the diff (Codex 6; carried in the PR by decision); spaces in the install prefix splitting launch's `Command` (Codex 4; pre-existing in all three launch files); buildfarm `ctest` before install (Gemini 8; bloom builds with `BUILD_TESTING=OFF`); `file://` and bare mesh paths, nested `<link>`, `$(find)` in comments, hard-coded launch list, `ci-urdf/` in the checkout, `Test results` with `if: always()` (Gemini 3, 5, 6, 7, 9, 10; hypothetical forms the URDF does not use, CI would catch, or the same as the proven marine_colormap model).

### Checks made
- `load_launch.py` (`0813adc`): read `launch_ros` `actions/node.py` (installed Rolling, lines 423-431, and upstream `jazzy`, the same lines) and `actions/set_parameter.py` (both: appends to `global_params`): a `SetParameter` value reaches every later node as `-p name:=value`. Reproduced the rcl side on Rolling (`ROS_DOMAIN_ID=187`, empty first): `robot_state_publisher --ros-args -p "robot_description:=<xacro output>"` aborts with "failed to initialize rcl: Couldn't parse parameter override rule: '-p robot_description:=<?xml ...". The implementer's account holds. The commit should stay: `value_type=str` is needed by any later design that keeps a `ParameterValue`, it is what the test pins, and it turns a crash at launch into a file that starts; its message should say it does not make the file deliver a URDF (suggestion 4). The progress entry's PR text says so plainly.
- Test isolation: no other installed `ben_description` exists on this machine outside the worktree (searched `/home/roland/project11` and `/opt/ros`), so built one: a scratch copy with `lidar.xacro`'s parent changed to `base_lnk`, built isolated in `env -i` with only `/opt/ros/rolling`, tested with the good worktree install put first on the inherited `AMENT_PREFIX_PATH`: `test_check_urdf_parses[default]` and `[boat2]` fail ("2 failed, 13 passed"), so `$(find ben_description)` resolved to the install under test, not the good copy ahead of it.
- Runtime needs of the test: `check_urdf` in `urdfdom` (`/opt/ros/rolling/bin/check_urdf`; jazzy branch builds it); `ament_cmake_pytest` brings `python3-pytest` (buildtool_export_depend, Rolling and `jazzy` branch); `xacro`, `launch`, `launch_ros` declared. `ParameterValue`'s `value_type` is keyword-only on both distros, so the AST check cannot be dodged by a positional argument.
- Workflow: identical to marine_colormap's `rolling` workflow (last five runs green) apart from the URDF steps and `compare-urdf`; `if:` expressions right for a push to `jazzy`, a PR into `jazzy` (rolling and compare skipped) and a PR into `rolling` (all three run). `python3`, `sha256sum`, `sed` present in ros-core; `set -eo pipefail` only after the `source`s; relative upload path right in a container. `ros_core` (REP 2001 variant) already contains `ament_cmake`, `ament_cmake_pytest`, `ament_index_python`, `launch` and `launch_ros`, so CI cannot show that those declarations are needed or missing; rosdep only installs `xacro`, `urdfdom`, `robot_state_publisher`, `joint_state_publisher` and their dependencies.
- Compare step with one artifact missing (its `run:` block extracted and run under `bash -e`): exit 0, empty "jazzy ... lines, sha256" lines, `diff: ...: No such file or directory`, an empty diff block in the summary and `::warning title=URDF differs::`.
- Cherry-picks: `origin/jazzy` = `origin/rolling` = `b9edcac`. In a temporary worktree, the four code commits applied in order onto `origin/jazzy` with no conflict; `0813adc` and `da581b7` also apply alone; `28fbda7` needs `3880ba6` before it (package.xml context) and `0813adc` for its own check to pass, so keep the order.
- Rebuilt and retested in the package worktree: `Summary: 1 package finished`; `100% tests passed`, `Summary: 16 tests, 0 errors, 0 failures, 0 skipped`.
- Canonical form: drops comments, attribute order and surrounding whitespace only; values and structure show. A false difference would need different float output; the xacro files use `radians`, `pi`, `sin` and `cos`, whose last digit could in principle differ between glibc builds; that is the most likely cause of a warning, and it would be a finding to explain.
- Not verified: anything on Jazzy (none here); the `uses:` actions and `if:` expressions were read, not run.

### Findings
- [ ] (must-fix) `compare-urdf` with a missing artifact (a distro job failed before its upload) reports a false "URDF differs" warning on a green job: check both files exist and fail with a message naming the missing distro, and warn only on `diff` exit 1 (exit 2 fails); while there, separate the summary lines (they render as one paragraph) — `.github/workflows/ci.yml:255-271`
- [ ] (suggestion) `test_launch_urdf_passed_as_string` passes when a file has no `ParameterValue` call at all, e.g. `Command(...)` put straight into `parameters`, the regression it guards; assert at least one call per launch file (also match `func.attr`) — `test/test_description.py:134-142`
- [ ] (suggestion) A failure in "Processed URDF" or a transient artifact-service error in "Upload processed URDF" skips "Test", so the pytest output that would explain a xacro failure is lost; give "Test" `if: ${{ !cancelled() }}` with a condition on the build step, or move the URDF steps after "Test" with `if: always()` — `.github/workflows/ci.yml:122,220`
- [ ] (suggestion) The header says an undeclared dependency "fails here instead of being hidden by the overlay"; the test step sources `/opt/ros/<distro>` and the ros-core image already holds `ament_cmake`, `ament_cmake_pytest`, `ament_index_python`, `launch` and `launch_ros`, so only rosdep's install of the remaining keys is checked; reword the comment and say in the PR that CI does not prove the cause-11 declarations — `.github/workflows/ci.yml:7-11`
- [ ] (suggestion) `0813adc`'s message reads as a fix of `load_launch.py`; add that the file now starts but still cannot deliver the URDF to a node (`SetParameter` reaches nodes as `-p name:=<xml>`, which rcl rejects; follow-up), so the jazzy backport does not inherit a wrong impression — `launch/load_launch.py:29`
