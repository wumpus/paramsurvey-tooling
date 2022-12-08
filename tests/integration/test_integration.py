import subprocess
import time
import os
import os.path
import pytest
import sys
import signal

import paramsurvey_tooling.cli as cli


def expand_tests():
    tests = [
#        {
#            'name': 'head submit',
#            'head_background': True,
#            'ray_job_submit_foreground': True,
#        },
#        {
#            'name': 'head submit no_wait',
#            'head_background': True,
#            'ray_job_submit_background_no_wait': True,
#        },
        {
            'name': 'head driver',
            'head_background': True,
            'driver_foreground': True,
        },
    ]

    sing = []
    for t in tests:
        t_copy = t.copy()
        t_copy['singularity'] = True
        t_copy['name'] += ' singularity'
        sing.append(t_copy)
    tests.extend(sing)
    child = []
    for t in tests:
        t_copy = t.copy()
        t_copy['child_background'] = True
        t_copy['name'] += ' child'
        child.append(t_copy)
    tests.extend(child)

    return tests


def test_integration():
    tests = expand_tests()
    os.environ['SLURM_SUBMIT_DIR'] = '.'

    background_kwargs = {
        # not using capture_output=True because we want to support older pythons (<=3.6)
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE,
        'encoding': 'utf-8',
    }
    foreground_kwargs = {
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE,
        'encoding': 'utf-8',
    }

    for t in tests:
        if 'singularity' in t:
            #pytest.skip('need to make a singularity container')  # this skips the entire test
            continue
            # XXX when this is implemented, test that we're really inside a container
            # XXX feature to warn user if they aren't consistantly using singularity

        name = t['name']

        if 'head_background' in t:
            # XXX eventually need to be able to set the name of the magic file to avoid collisions
            try:
                os.remove(os.path.expanduser('~/.ray-head-details'))
            except FileNotFoundError:
                pass
            args = 'pstool start head'.split()
            # the ray head is 10 processes, so put them in a group
            h_proc = subprocess.Popen(args, start_new_session=True, **background_kwargs)
            h_group = os.getpgid(h_proc.pid)
            print('GREG h_group is', h_group)
        if 'child_background' in t:
            args = 'pstool start child'.split()
            c_proc = subprocess.Popen(args, start_new_session=True, **background_kwargs)
            c_group = os.getpgid(c_proc.pid)
        else:
            c_proc = None

        assert h_proc.poll() is None, 'head is still alive, '+name
        ret = cli.await_magic_file(check_network=False)
        # XXX should I check ret?

        prefix = os.path.dirname(cli.__file__) + '/../tests/integration/'
        hello_world = prefix + 'hello-sleep.py'

        '''
        CompletedProcess -- returned by .run()
        returncode
        stdout, stderr
        Popen
        poll, returns None if still running
        Popen.communicate
        (stdout, stderr)
        '''

        if 'ray_job_submit_foreground' in t:
            os.environ['RAY_ADDRESS'] = 'http://localhost:8265'
            args = 'pstool submit {}'.format(hello_world).split()
            s_proc = subprocess.run(args, **foreground_kwargs)
            # XXX test hello output
            print('GREG submit foreground stdout', s_proc.stdout)
            print('GREG submit foreground stderr', s_proc.stderr)
            assert s_proc.returncode == 0
        if 'ray_job_submit_background_no_wait' in t:
            args = 'pstool submit --no-wait {}'.format(hello_world).split()
            s_proc = subprocess.run(args, **foreground_kwargs)
            # XXX cli runs ray job list already
            # XXX test more: ray job list, logs, status, stop etc.
            assert s_proc.returncode == 0
            # XXX test hello output
        if 'driver_foreground' in t:
            args = 'pstool start driver {}'.format(hello_world).split()
            d_proc = subprocess.run(args, **foreground_kwargs)
            assert d_proc.returncode == 0
            stdout_lines = d_proc.stdout.splitlines()
            count = len(set([l for l in stdout_lines if 'hello from pset ' in l]))
            assert count == 15, 'saw 15 psets'

        assert h_proc.poll() is None, 'head is still alive, '+name

        os.killpg(h_group, signal.SIGTERM)
        h_out, h_err = h_proc.communicate(timeout=30)
        print('TEST DEBUG h_out', h_out)
        print('TEST DEBUG h_err', h_err)
        
        assert h_proc.poll() == -signal.SIGTERM, 'head exited SIGTERM'

        # XXX more asserts on h_out, h_err

        if c_proc:
            os.killpg(c_group, signal.SIGTERM)
            c_out, c_err = c_proc.communicate(timeout=30)
            print('TEST DEBUG c_out', c_out)
            print('TEST DEBUG c_err', c_err)

            assert c_proc.poll() is not None
            assert c_proc.returncode in (-signal.SIGTERM, 1)  # with less verbosity, it gets 1
            # XXX more asserts on c_out and c_err
