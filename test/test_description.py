"""Check the installed description: xacro, the URDF parser, paths and launch files."""

import ast
import os
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

import pytest

PACKAGE = 'ben_description'

# Number of links in the processed ben_mesh.xacro. Update it when a link is
# added or removed on purpose; otherwise a change here means a sensor's
# include or macro call went missing.
EXPECTED_LINK_COUNT = 32

# None: no argument, as load_launch.py and publish_state_launch.py run xacro.
# 'boat2': namespace:=<name>, as display_launch.py and simulations run it.
NAMESPACES = [None, 'boat2']
LAUNCH_FILES = ['display_launch.py', 'load_launch.py', 'publish_state_launch.py']


def _prefix():
    prefix = os.environ.get('BEN_DESCRIPTION_INSTALL_PREFIX')
    if not prefix:
        pytest.fail('BEN_DESCRIPTION_INSTALL_PREFIX is not set; run through colcon test')
    return Path(prefix)


def _share():
    return _prefix() / 'share' / PACKAGE


def _env():
    # colcon test gives a package its dependencies' environment, not its own
    # install: prepend that, so $(find ben_description) resolves to this
    # install and not to another ben_description further along the path.
    env = dict(os.environ)
    paths = [str(_prefix())] + [p for p in env.get('AMENT_PREFIX_PATH', '').split(os.pathsep)
                                if p]
    env['AMENT_PREFIX_PATH'] = os.pathsep.join(paths)
    return env


def _ns_id(namespace):
    return namespace or 'default'


@pytest.fixture(scope='module', params=NAMESPACES, ids=_ns_id)
def processed(request):
    namespace = request.param
    cmd = ['xacro', str(_share() / 'urdf' / 'ben_mesh.xacro')]
    if namespace:
        cmd.append(f'namespace:={namespace}')
    result = subprocess.run(cmd, capture_output=True, text=True, env=_env(), timeout=30)
    return namespace or 'ben', result


def test_xacro_processes(processed):
    _, result = processed
    assert result.returncode == 0, result.stderr


def test_check_urdf_parses(processed, tmp_path):
    namespace, result = processed
    assert result.returncode == 0, result.stderr
    urdf = tmp_path / 'ben.urdf'
    urdf.write_text(result.stdout)
    check = subprocess.run(['check_urdf', str(urdf)], capture_output=True, text=True,
                           timeout=30)
    assert check.returncode == 0, check.stdout + check.stderr
    assert f'root Link: {namespace}/base_link' in check.stdout, check.stdout


def test_links_namespaced(processed):
    namespace, result = processed
    assert result.returncode == 0, result.stderr
    links = [link.get('name') for link in ET.fromstring(result.stdout).iter('link')]
    assert len(links) == EXPECTED_LINK_COUNT, (
        f'{len(links)} links, expected {EXPECTED_LINK_COUNT}; update EXPECTED_LINK_COUNT '
        'if a link was added or removed on purpose')
    wrong = [name for name in links if not name.startswith(f'{namespace}/')]
    assert not wrong, f'links not prefixed {namespace}/: {wrong}'


def _resolve(uri):
    if uri.startswith('package://'):
        package, _, rest = uri[len('package://'):].partition('/')
        assert package == PACKAGE, f'{uri}: only {PACKAGE} paths are expected'
        return _share() / rest
    if uri.startswith('file://'):
        return Path(uri[len('file://'):])
    return Path(uri)


def test_mesh_files_installed(processed):
    _, result = processed
    assert result.returncode == 0, result.stderr
    uris = [e.get('filename') for e in ET.fromstring(result.stdout).iter()
            if e.get('filename')]
    assert len(uris) >= 5, uris
    missing = [uri for uri in uris if not _resolve(uri).is_file()]
    assert not missing, f'not installed: {missing}'


def test_find_paths_installed():
    found = re.compile(r'\$\(find ([\w-]+)\)/([^"\'\s<>]+)')
    files = sorted((_share() / 'urdf').rglob('*.xacro'))
    assert files
    missing = []
    for xacro in files:
        for package, rest in found.findall(xacro.read_text()):
            assert package == PACKAGE, f'{xacro.name}: $(find {package}) not expected'
            if not (_share() / rest).is_file():
                missing.append(f'{xacro.name}: $(find {package})/{rest}')
    assert not missing, missing


@pytest.mark.parametrize('name', LAUNCH_FILES)
def test_launch_file_loads(name, monkeypatch):
    from launch.actions import DeclareLaunchArgument
    from launch.launch_description_sources import (
        get_launch_description_from_python_launch_file)

    monkeypatch.setenv('AMENT_PREFIX_PATH', _env()['AMENT_PREFIX_PATH'])
    description = get_launch_description_from_python_launch_file(
        str(_share() / 'launch' / name))
    arguments = [e.name for e in description.entities if isinstance(e, DeclareLaunchArgument)]
    assert 'namespace' in arguments, arguments


@pytest.mark.parametrize('name', LAUNCH_FILES)
def test_launch_urdf_passed_as_string(name):
    # Without value_type=str, launch parses the URDF as YAML and fails. Each
    # launch file passes a robot description, so each must wrap it in a
    # ParameterValue: a bare Command(...) in parameters is the same failure.
    tree = ast.parse((_share() / 'launch' / name).read_text())
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and (getattr(n.func, 'id', None) == 'ParameterValue'
                  or getattr(n.func, 'attr', None) == 'ParameterValue')]
    assert calls, f'{name}: no ParameterValue call; the URDF must be passed as one'
    for call in calls:
        kinds = {k.arg: getattr(k.value, 'id', None) for k in call.keywords}
        assert kinds.get('value_type') == 'str', f'{name}:{call.lineno}: no value_type=str'
