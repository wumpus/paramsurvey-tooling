import pytest
from unittest import mock
from unittest.mock import patch
import subprocess
import os
import sys

from paramsurvey_tooling import cli


_save_subprocess_run = subprocess.run


def test_starter(fs):
    subprocess.run = _save_subprocess_run
    home = os.path.expanduser('~')
    os.makedirs(home)

    with patch.dict(os.environ, {'SLURM_SUBMIT_DIR': '/'}, clear=True):
        cp = mock.MagicMock()
        cp.returncode = 0
        subprocess.run = mock.MagicMock(return_value=cp)

        assert not os.path.isfile(os.path.expanduser('~/.ray-head-details'))

        args = 'start head'.split(' ')
        cli.main(args)

        call_args = subprocess.run.call_args
        assert call_args.args[0][:4] == ['ray', 'start', '--head', '--block']
        assert os.path.isfile(os.path.expanduser('~/.ray-head-details'))
        subprocess.run.reset_mock()

        args = 'start driver foo.py a b c'.split(' ')
        cli.main(args)
        call_args = subprocess.run.call_args
        # I'm not sure why it needs [0][0] at this point
        assert call_args[0][0][:5] == ['python', 'foo.py', 'a', 'b', 'c']
        subprocess.run.reset_mock()

        args = 'start child'.split(' ')
        cli.main(args)
        call_args = subprocess.run.call_args
        assert call_args[0][0][:3] == ['ray', 'start', '--block']


@pytest.mark.skip(reason='not working yet')
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

    assert subprocess.run.called
    args = ['ray', 'job', 'submit', '--address', 'x', '--', 'python', *args[1:]]
    # fish out the value of address in the call
    address_value = subprocess.run.call_args.args[0][4]
    args[4] = address_value
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
