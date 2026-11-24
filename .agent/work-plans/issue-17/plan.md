# Plan: Check and port ben_description on ROS 2 Rolling, and add CI

## Issue

https://github.com/rolker/ben_description/issues/17 (part of rolker/unh_marine_autonomy#415)

## Context

`ben_description` builds on Rolling as it stands (issue review). Two gaps make "passes on
Rolling and Jazzy" mean nothing yet: `package.xml` does not declare what the launch files use
(cause 11), and the package has **no tests** (`0 tests`). There is no CI. Jazzy is not
installed on this machine and there is no Docker: **Jazzy is verified by CI only.**

Everything below was rehearsed on Rolling (Ubuntu 26.04) in a scratch workspace, with
`env -i` and only `/opt/ros/rolling/setup.bash` sourced, no install folder sourced for tests.

## Approach

Three commits on `feature/issue-17` (base `rolling`), each backported to `jazzy` by
`git cherry-pick -x`. No file under `.agent/` in any of them.

1. **Declare what is used (cause 11)** — `package.xml` only. Backported.
   - `<buildtool_depend>ament_cmake</buildtool_depend>` (CMake calls `find_package(ament_cmake)`;
     today it arrives only through `ament_cmake_ros`, which stays: removing it is not needed).
   - `<exec_depend>` `ament_index_python`, `launch`, `launch_ros` (all three launch files),
     `rviz2` (`display_launch.py`).
   - Kinds: `exec_depend`, since launch files and xacro run at run time. `xacro`,
     `joint_state_publisher`, `robot_state_publisher` stay `depend` as they are.
   - Every key resolves on both distros (`rosdep resolve --os=ubuntu:noble` with Jazzy,
     `ubuntu:resolute` with Rolling): checked for all of the above and the test keys below.
     `rosdep check --from-paths src --ignore-src` on Rolling: all satisfied. Element order
     keeps `ament_xmllint` valid (cause 9): checked after the edit.
   - Alternative weighed: leave `rviz2` undeclared because only the developer display uses it.
     Rejected: that is cause 11 itself. Cost: `rosdep install` pulls rviz2 (Qt, Ogre) into
     each CI job.

2. **Add the smallest test with teeth** — `test/test_description.py` (new) plus a
   `BUILD_TESTING` block in `CMakeLists.txt` and two `test_depend`s in `package.xml`. Backported.
   - Framework: `ament_add_pytest_test(test_description test/test_description.py
     ENV BEN_DESCRIPTION_INSTALL_PREFIX=${CMAKE_INSTALL_PREFIX} TIMEOUT 60)`. Chosen over
     `add_test` with a shell script: the path walk and XML parsing are a few lines of Python,
     and pytest gives one named result per case. No code package is needed for either.
   - How it finds the installed files: `colcon test` gives a package only its dependencies'
     environment, not its own install. The test reads `BEN_DESCRIPTION_INSTALL_PREFIX` and
     **prepends** it to `AMENT_PREFIX_PATH` for the `xacro` subprocess (prepend, so an older
     `ben_description` elsewhere on the path, as in this machine's layered workspaces, is not
     picked). `package://ben_description/...` is resolved against `<prefix>/share/ben_description`.
     Runs after `colcon build` (install step); not meant for bare `ctest` before install.
   - Checks (6 pytest cases, one ctest):
     a. `xacro <share>/urdf/ben_mesh.xacro` with no argument (what `load_launch.py` and
        `publish_state_launch.py` pass) and with `namespace:=boat2` (what
        `unh_marine_simulation`'s demo passes, `namespace:=<boat>`): exit 0;
     b. `check_urdf` on the result: exit 0 and `root Link: <ns>/base_link` (urdfdom is the parser
        `robot_state_publisher` uses);
     c. 32 links, every name prefixed `<ns>/`;
     d. every `filename` attribute (`package://`, `file://`, absolute; what a `$(find)` in a mesh
        path becomes) resolves to an installed file, at least 5 of them;
     e. every `$(find <pkg>)/<path>` in the installed `urdf/**/*.xacro` names an installed file;
     f. each launch file loads (`get_launch_description_from_python_launch_file`) and declares
        `namespace`. No node is started, no DDS, no display.
   - What breaking things showed (scratch copies, each rebuilt from clean):

     | Break | Caught by |
     |---|---|
     | mesh path typo `forward_camerra.dae` | (d), names the missing URI |
     | `BEN_shell.tar.bz2` extracted to `models/` not `models/meshes/` | (d), 3 failures |
     | archive extraction removed | the **build** fails (`cmake_install.cmake` error) before any test |
     | macro renamed `ben_lidar2` | (a): `unknown macro name: xacro:ben_lidar` |
     | lidar link name hard-coded `ben/` | (b) for `boat2` only: `child link [boat2/lidar] ... not found` |
     | lidar parent `base_lnk` | (b): xacro succeeds, `check_urdf` fails |
     | include path `radr.xacro` | (a) and (e) |
     | `SetParameterX` import in `load_launch.py` | (f) |

   - Test dependencies: `<test_depend>ament_cmake_pytest</test_depend>` (brings
     `python3-pytest`) and `<test_depend>urdfdom</test_depend>` for `check_urdf`. `urdfdom` is
     chosen over `liburdfdom-tools`: both resolve on both distros, but the ROS package is the
     parser the stack uses and ships `/opt/ros/<distro>/bin/check_urdf` on both (checked in the
     `ros-jazzy-urdfdom` 4.0.2 deb). `urdfdom_py` is **not** needed: the test parses with the
     standard library. `xacro`, `launch`, `ament_index_python` are already declared.
   - Rolling: 7 results (6 pytest + 1 ctest), 0 failures, about 0.3 s; passes with and without
     `--symlink-install`. The test file is written to pass `ament_flake8` and `ament_pep257`.
   - Launch files: covered by (f), above; it would catch an API removed from `launch_ros`.
   - Linters: **not added** (recommended). `ament_lint_common` today: `ament_copyright` 3 files
     without a header (all of `launch/`); `ament_flake8` 15 findings in `load_launch.py` and
     `publish_state_launch.py` (F401 x2, Q000 x4, I100, W391 x2, E261, E262, E302, E303, W293);
     `ament_lint_cmake` 1 (`file (` spacing); `ament_xmllint` and `ament_pep257` pass. Copyright
     headers need the owner's licence wording, so the fix is not trivial: follow-up.

3. **CI** — `.github/workflows/ci.yml`, modelled on `marine_colormap`'s (branch `rolling`).
   Backported unchanged.
   - Jobs `jazzy` (`ros:jazzy-ros-core`) and `rolling` (`ros:rolling-ros-core`, with
     `if: (github.base_ref || github.ref_name) != 'jazzy'`), on push and pull request to both
     branches. Steps as in the model: apt, `ros-dev-tools`, checkout, rosdep init/update,
     workspace symlink, **strict** `rosdep install --ignore-src -y --from-paths $paths` (no `-r`,
     paths from `colcon list --packages-up-to ben_description`), build, test with
     `--return-code-on-test-failure`, `colcon test-result --verbose`. The test step sources only
     `/opt/ros/<distro>/setup.bash`; the test finds the install through its CMake-set prefix.
   - New step after Build, `Processed URDF` (`shell: bash`): sources `/opt/ros/<distro>` and
     `install/setup.bash` (the step runs xacro the way a user does, it is not a test), runs
     `xacro install/ben_description/share/ben_description/urdf/ben_mesh.xacro namespace:=ben`,
     writes the raw output and a canonical form into `$GITHUB_WORKSPACE/ci-urdf/`, prints
     `xacro`'s package version, `wc -l` and `sha256sum` of both. `set -eo pipefail` goes **after**
     the `source`: with `-u` set, sourcing `setup.bash` fails (`AMENT_TRACE_SETUP_FILES: unbound
     variable`, found in the rehearsal). Upload with `actions/upload-artifact@v7` as
     `urdf-<distro>`.
   - Job `compare-urdf` (`needs: [jazzy, rolling]`, `runs-on: ubuntu-24.04`, no container,
     skipped on `jazzy` because `rolling` is): `actions/download-artifact@v8` with
     `pattern: urdf-*`, prints both checksums and line counts, `diff -u` of the canonical files
     into the log and job summary. A difference raises a `::warning::`, **not** a failure.
     Alternative: values printed in each job for a reader to compare; rejected because nobody
     compares them; the job is about 20 lines and 15 s.
   - `actions/checkout@v6` as in the working model (v7 exists; not needed for the port).

## Same URDF on Rolling as on Jazzy

- xacro is **2.1.1 on both** (rosdistro `jazzy`: `2.1.1-1`; `rolling`: `2.1.1-2`), so the
  review's "2.0.x against 2.1.x" does not hold. What differs underneath: Python 3.12 against
  3.14 (expression evaluation, float `repr`), urdfdom 4.0.2 against 6.0.2 (`check_urdf`).
- Canonical form: XML C14N 2.0 from the standard library,
  `xml.etree.ElementTree.canonicalize(with_comments=False, strip_text=True)`, then one element
  per line for a readable diff. It sorts attributes, drops comments (the generated-by header,
  which names the input path) and drops whitespace-only text. On Rolling: raw 555 lines,
  sha256 `ef1fb08f…`; canonical 624 lines, sha256 `d893e417…`.
- Expected first Jazzy run: strict rosdep passes (keys resolve on noble), build passes,
  7 results with 0 failures, and the **canonical and raw checksums equal Rolling's** (same
  xacro, same relative input path). A canonical difference is a finding to explain (Python
  evaluating a property differently), not an automatic failure; a raw-only difference is
  formatting.
- What it cannot tell: how consumers read the URDF on each distro (robot_state_publisher, rviz,
  Gazebo's URDF-to-SDF conversion); mesh files are checked to exist, not loaded. Each job's
  `check_urdf` passing is the parser evidence there is.

## #415 causes against this package

Cause 11: hit (step 1). 1 `ament_target_dependencies`, 2 `.h` includes, 3 `CPL_CVSID`,
10 GCC 15, 16 `Waitable`: none (no C++). 4 `tests_require`, 5 `logger.warn`, 15 flake8 `A005`:
none (no `setup.py`, no logger, no module named like the standard library). 6, 7, 13 Nav2,
8 geodesy, 12 GDAL, 14 tf2 listener/broadcasters: none. 9 `package.xml` order: valid before
and after. CMake below 3.10 warning: none (3.18).

## Left alone (for a follow-up issue in this repository)

- `publish_state_launch.py` and `load_launch.py` do not pass `namespace` to xacro (frames are
  always `ben/...`); `display_launch.py` does.
- Lint in `launch/` (copyright headers, 15 flake8 findings, listed above); `file (` spacing in
  `CMakeLists.txt`; `load_launch.py`'s two unused imports.
- `ament_cmake_ros` buildtool unused by the CMake; `joint_state_publisher` and
  `robot_state_publisher` as `depend` where `exec_depend` would do; licence `BSD` not SPDX.
- `install(DIRECTORY models)` also installs the 33 MB `BEN_shell.tar.bz2` next to the
  extracted mesh.

For rolker/ben_project11#30 (the host relays; not this repository): its `package.xml` does not
declare `ben_description`; three ROS 1 files (`replay_bag.launch`, `operator_mystique.launch`,
`remote_operator.launch`) include `$(find ben_description)/launch/load.launch`, which does not
exist; `ben_core_launch.py` includes `publish_state_launch.py`, whose `namespace` does not
reach the URDF (fixed here only by the follow-up above).

## Files to Change

| File | Change | Commit |
|------|--------|--------|
| `package.xml` | `ament_cmake` buildtool; 4 `exec_depend` | 1 |
| `package.xml` | `test_depend` `ament_cmake_pytest`, `urdfdom` | 2 |
| `CMakeLists.txt` | `BUILD_TESTING` block registering the pytest test | 2 |
| `test/test_description.py` | new test (above) | 2 |
| `.github/workflows/ci.yml` | new workflow (above) | 3 |

## Prior Art

`marine_colormap`'s `ci.yml` (strict rosdep, job skip on `jazzy`, no install sourced for
tests) taken as is. The issue review's test outline and comparison idea taken, corrected on the
xacro versions. `urdf_tutorial`-style packages declare `rviz2` as `exec_depend`: taken.
`urdfdom_py` parsing: rejected as an extra dependency the standard library makes unneeded.

## Serves

None stated (the project has no goals or design document); the port tracked in
rolker/unh_marine_autonomy#415.

## Design Picture

No change to the design picture; the project keeps no design document.

## Principles Self-Check

| Principle | Consideration |
|---|---|
| Only what's needed | Three small commits; no lint, no launch fixes; left-alone list above. |
| A change includes its consequences | Dependencies declared with the code that uses them; test deps with the test. |
| Test what you build | The test was shown to fail on each break it claims to catch. |

## ADR Compliance

| ADR | Triggered | How addressed |
|---|---|---|
| ADR-0013 | Yes | Plan Authored entry in `progress.md`; records kept out of code commits. |
| ADR-0002 | Yes | Work in the issue worktree; scratch builds outside the source tree. |

## Consequences

| If we change... | Also update... | Included in plan? |
|---|---|---|
| `package.xml` deps | consumers' installs gain `rviz2` | Yes (accepted) |
| new CI on `rolling` | same file on `jazzy` | Yes, cherry-pick of commit 3 |
| `ben_project11` gaps | ben_project11#30 | No, relayed to host |

## Open Questions

1. `rviz2` as `exec_depend` (heavier installs and CI). Recommend: declare it.
2. Linters now or later. Recommend: later, with the copyright wording decided.
3. Third compare job or printed values. Recommend: the third job.

## Estimated Scope

Single PR into `rolling`, then a hand backport PR into `jazzy`. CI time: about 4 to 5 min
per distro job in parallel (the model's Jazzy job took 3m45s, with 47 s of rosdep install;
`rviz2` adds an estimated 1 to 2 min), plus about 15 s for `compare-urdf`.
