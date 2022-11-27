import pytest
from unittest import mock
from unittest.mock import patch
import subprocess
import os

from paramsurvey_tooling import cli


_save_subprocess_run = subprocess.run


def test_starter(fs):
    return
    subprocess.run = _save_subprocess_run
    home = os.path.expanduser('~')
    os.makedirs(home)

    with patch.dict(os.environ, {'SLURM_SUBMIT_DIR': '/'}, clear=True):
        cp = mock.MagicMock()
        cp.returncode = 0
        subprocess.run = mock.MagicMock(return_value=cp)

        args = 'start head'.split(' ')
        cli.main(args)
        assert os.path.isfile(os.path.expanduser('~/.ray-head-details'))
        call_args = subprocess.run.call_args()
        assert call_args[:3] == ['ray', 'start', '--head', '--block']
        subprocess.run.reset_mock()

        # driver
        # should read the magic file
        # should run the expected subprocess
        args = 'start driver foo.py a b c'.split(' ')
        cli.main(args)
        call_args = subprocess.run.call_args()
        assert call_args[:1] == ['ray', 'start']
        assert call_args[4:8] == ['foo.py', 'a', 'b', 'c']
        subprocess.run.reset_mock()

        # child
        # should read the magic file
        # should run the expected subprocess
        args = 'start child'.split(' ')
        cli.main(args)
        call_args = subprocess.run.call_args()
        assert call_args[:3] == ['ray' 'start', '--block']


def test_submitter(fs):
    subprocess.run = _save_subprocess_run
    home = os.path.expanduser('~')
    os.makedirs(home)

    port, password = cli.create_magic_file()
    address2, password2 = cli.await_magic_file(check_network=False)

    cp = mock.MagicMock()
    cp.returncode = 0
    subprocess.run = mock.MagicMock(return_value=cp)

    args = 'submit foo.py a b c'.split()
    cli.main(args)

    assert 'RAY_ADDRESS' in os.environ
    assert os.environ['RAY_ADDRESS'] == address2
    assert subprocess.run.called
    args = ['ray', 'job', 'submit', '--', 'python', *args[1:]]
    subprocess.run.assert_called_with(args)


def test_builder(fs):
    subprocess.run = _save_subprocess_run
    args = 'build foo'.split()
    with pytest.raises(SystemExit):
        # this ought to be a FileNotFoundError ?! but is getting SystemExit 255
        cli.main(args)

    cp = mock.MagicMock()
    cp.returncode = 0
    subprocess.run = mock.MagicMock(return_value=cp)
    cli.main(args)
    subprocess.run.assert_called_with(['singularity', 'build', 'docker-archive://foo'])

    args = 'build --sandbox bar foo'.split()
    cli.main(args)
    subprocess.run.assert_called_with(['singularity', 'build', '--sandbox', 'bar', 'docker-archive://foo'])