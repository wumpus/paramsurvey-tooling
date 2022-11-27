import pytest
from unittest.mock import patch
from unittest import mock
import os
import socket
import sys

from paramsurvey_tooling import cli


def test_gpu_count():
    assert cli._gpu_count() == 0
    with patch.dict(os.environ, {'CUDA_VISIBLE_DEVICES': '0,1,3'}, clear=True):
        assert cli._gpu_count() == 3


def test_guess_batch():
    d = {}
    with patch.dict(os.environ, d, clear=True):
        assert cli.guess_batch() is None, 'no env, no batch'
    d['SLURM_FOO'] = '1'
    with patch.dict(os.environ, d, clear=True):
        assert cli.guess_batch(verbose=2) == 'SLURM'
    d['PBS_1'] = '1'
    d['PBS_2'] = '1'
    with patch.dict(os.environ, d, clear=True):
        assert cli.guess_batch() == 'PBS'
    d['SGE_1'] = '1'
    d['SGE_2'] = '1'
    d['SGE_3'] = '1'
    with patch.dict(os.environ, d, clear=True):
        assert cli.guess_batch(verbose=2) == 'SGE'


def test_create_magic_file(fs):
    home = os.path.expanduser('~')
    os.makedirs(home)

    cli.MAGIC_TIMEOUT_SEC = 1
    with pytest.raises(TimeoutError):
        # times out on file creation
        address2, password2 = cli.await_magic_file()

    port, password = cli.create_magic_file()
    address2, password2 = cli.await_magic_file(check_network=False)

    host2, port2 = address2.rstrip().split(':')

    assert port == int(port2)
    assert password == password2
    assert host2
