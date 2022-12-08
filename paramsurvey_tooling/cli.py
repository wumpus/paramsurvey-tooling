from argparse import ArgumentParser
import os
import os.path
import sys
from collections import defaultdict
import multiprocessing
import random
import hashlib
import socket
import time
import subprocess
import shlex
import warnings

import psutil

'''
https://hpcc.umd.edu/hpcc/help/slurmenv.html
https://slurm.schedmd.com/sbatch.html

https://opus.nci.org.au/display/Help/Useful+PBS+Environment+Variables
Appendix A: https://secure.altair.com/docs/PBSpro_UG_5_1.pdf
latest: https://help.altair.com/2022.1.0/PBS%20Professional/PBSUserGuide2022.1.pdf

https://docs.oracle.com/cd/E19957-01/820-0699/chp4-21/index.html
Univa Grid Engine appears to still use SGE_ as the prefix
'''


MAGIC_TIMEOUT_SEC = 300


# XXX stolen from paramsurvey.psmultiprocessing
def _core_count():
    try:
        # recent Linux
        return len(os.sched_getaffinity(0))
    except (AttributeError, NotImplementedError, OSError):
        try:
            # Windows, MacOS, FreeBSD
            return len(psutil.Process().cpu_affinity())
        except (AttributeError, NotImplementedError, OSError):
            # older Linux, MacOS. Can raise NotImplementedError
            return multiprocessing.cpu_count()


def _gpu_count():
    if 'CUDA_VISIBLE_DEVICES' in os.environ:
        gpus = os.environ['CUDA_VISIBLE_DEVICES'].count(',') + 1
    else:
        gpus = 0
    return gpus


def guess_batch(verbose=False):
    prefixes = ('SLURM_', 'PBS_', 'SGE_')
    counts = defaultdict(int)
    for key in os.environ:
        if key.startswith(prefixes):
            p = key.split('_', 1)[0]
            counts[p] += 1
    if verbose and len(counts) > 1:
        print('surprised to see signs of more than one batch system:', counts.keys(), file=sys.stderr)
    if verbose > 1:
        print('counts:', counts, file=sys.stderr)
    if not counts:
        return None

    return max(counts, key=counts.get)


def get_resources(cmd, batch=None, verbose=False):
    cores = _core_count()
    gpus = _gpu_count()

    if batch == 'SLURM':
        cores = int(os.environ.get('SLURM_CPUS_ON_NODE', '0')) or cores
        gpus = int(os.environ.get('SLURM_GPUS_ON_NODE', '0')) or gpus
    elif batch == 'PBS':
        # PBS_NUM_PPN -- not in the official docs
        # no mention of gpu in the official docs
        # there is an nVidia plugin that sets CUDA_VISIBLE_DEVICES
        warnings.warn('PBS support is untested')
    elif batch == 'SGE':
        warnings.warn('Grid Engine support is untested')
    else:
        raise ValueError('unknown type of batch system: '+repr(batch))

    # these override the numbers from the batch queue systems
    if cmd.num_cores:
        cores = cmd.num_cores
    if cmd.num_gpus:
        gpus = cmd.num_gpus

    if verbose:
        if cores != _core_count():
            print('surprised to see a subset of cores used:', cores, 'vs', _core_count(), file=sys.stderr)
        if gpus != _gpu_count():
            print('surprised to see a subset of gpus used:', gpus, 'vs', _gpu_count(), file=sys.stderr)

    return cores, gpus


def get_working_dir(batch=None, verbose=False):
    if batch == 'SLURM':
        return os.environ.get('SLURM_SUBMIT_DIR')
    elif batch == 'PBS':
        return os.environ.get('PBS_O_WORKDIR')
    elif batch == 'SGE':
        return os.environ.get('SGE_O_WORKDIR')
    else:
        return None


def create_magic_file():
    print('GREG create_magic_file')
    magic = os.path.expanduser('~/.ray-head-details')
    hostname = socket.gethostname()
    password = hashlib.md5(str(random.random()).encode('utf-8')).hexdigest()[:8]
    port = 6379
    with os.fdopen(os.open(magic, flags=os.O_CREAT | os.O_WRONLY, mode=0o600), 'w') as fd:
        address = hostname+':'+str(port)
        print(address, password, file=fd)

    # debug
    print('GREG os.path.isfile', os.path.isfile(magic))
    with open(magic) as f:
        print('GREG content', f.read())
    return port, password


def await_magic_file(check_network=True):
    magic = os.path.expanduser('~/.ray-head-details')
    timeout = time.time() + MAGIC_TIMEOUT_SEC
    timed_out = True

    while time.time() < timeout:
        try:
            with open(magic, 'r') as fd:
                address, password = fd.readline().rstrip().split(' ', 1)
        except FileNotFoundError:
            time.sleep(1)
            continue

        if not check_network:
            # used in testing
            timed_out = False
            break

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            host, port = address.split(':', 1)
            port = int(port)
            try:
                with s.connect((host, port)) as conn:
                    timed_out = False
                    s.close()
                    break
            except OSError:
                time.sleep(1)
    
    if timed_out:
        raise TimeoutError('connection to ray tied out')

    return address, password


def proc_complain(proc, name):
    if proc.returncode < 0:
        print(name, 'exited with signal', proc.returncode)
    if proc.returncode > 0:
        print(name, 'exited with value', proc.returncode)
    if proc.returncode != 0:
        exit(proc.returncode)


def starter(cmd, check_network=True):
    verbose = cmd.verbose
    if cmd.sif:
        warnings.warn('Singularity support is untested.')

    batch = guess_batch(verbose=verbose)

    wd = get_working_dir(batch=batch, verbose=verbose)
    if wd:
        if verbose:
            print('chdir', wd, file=sys.stderr)
        os.chdir(wd)

    cores, gpus = get_resources(cmd, batch=batch, verbose=verbose)

    cmdline2 = None
    if cmd.verb == 'head':
        port, password = create_magic_file()
        cmdline = 'ray start --head --block --port={} --redis-password={}'.format(port, password)
        if cores:
            cores -= 3
    elif cmd.verb == 'driver':
        address, password = await_magic_file(check_network=check_network)
        cmdline = 'ray start --address={} --redis-password={}'.format(address, password)
        if cmd.words[0] == 'python':
            cmd.words.pop(0)
        cmdline2 = 'python ' + ' '.join(cmd.words)
        if cores:
            cores -= 1
    elif cmd.verb == 'child':
        address, password = await_magic_file(check_network=check_network)
        cmdline = 'ray start --block --address={} --redis-password={}'.format(address, password)

    if cores and cores > 0:
        cmdline += ' --num-cpus={}'.format(cores)
    if gpus and gpus > 0:
        cmdline += ' --num-gpus={}'.format(gpus)

    if cmd.sif:
        cmdline = 'singularity exec {} '.format(cmd.sif) + cmdline

    parts = shlex.split(cmdline)
    if verbose:
        print('GREG parts is', parts)
    # try/catch for FileNotFound ?
    proc = subprocess.run(parts)  # XXX this is the hang in integration test -- ray start head
    proc_complain(proc, 'ray process')

    if not cmdline2:
        print('paramsurvey-batch-helper exiting', file=sys.stderr)
        return

    parts = shlex.split(cmdline2)
    if verbose:
        print(parts)
    # try/catch for FileNotFound ?
    proc = subprocess.run(parts)
    proc_complain(proc, 'driver process')

    print('paramsurvey-batch-helper driver exiting', file=sys.stderr)


def submitter(cmd, check_network=True):
    raise NotImplementedError('ray job submit is not working yet')
    verbose = cmd.verbose
    if cmd.sif:
        warnings.warn('Singularity support is untested.')

    address, password = await_magic_file(check_network=check_network)
    host = address.split(':', 1)[0]
    #address = host + ':' + str(6379)
    address = host + ':' + str(10001)

    if cmd.no_wait:
        no_wait = ' --no-wait'
    else:
        no_wait = ' '

    if cmd.words[0] == 'python':
        cmd.words.pop(0)

    cmdbase = 'ray job submit --address {}{}'.format(address, no_wait)
    if cmd.sif:
        cmdbase = 'singularity exec {} '.format(cmd.sif) + cmdbase
    cmdline = cmdbase + ' -- python ' + ' '.join(cmd.words)

    parts = shlex.split(cmdline)
    try:
        proc = subprocess.run(parts)
    except FileNotFoundError:
        if cmd.sif:
            print('FileNotFoundError: apparently singularity is not installed on this system', file=sys.stderr)
        else:
            print('FileNotFoundError: apparently ray is not installed on this system', file=sys.stderr)
    else:
        proc_complain(proc, 'driver script')

    if verbose:
        if cmd.no_wait:
            print('List of running jobs:')
            cmdline = cmdbase + 'list'
            subprocess.run(cmdline.split())
            print('Job is hopefully running. Use these commands to interact with it:')
            for verb in ('list', 'logs', 'status', 'stop'):
                print(' ', cmdbase, verb)
            

def builder(cmd, check_network=False):
    verbose = cmd.verbose

    if verbose:
        print('hint: on your docker build machine, do "docker save IMAGE_ID | gzip > my_docker_image.tar.gz', file=sys.stderr)
        if cmd.sandbox:
            print('hint: this container has a sandbox, so must be started with the "--writable {}" flag'.format(cmd.sandbox), file=sys.stderr)

    sandbox = ''
    if cmd.sandbox:
        sandbox = '--sandbox {} '.format(cmd.sandbox)

    cmdline = 'singularity build {} docker-archive://{}'.format(sandbox, cmd.file)
    parts = shlex.split(cmdline)
    try:
        proc = subprocess.run(parts)
    except FileNotFoundError:
        print('FileNotFoundError: apparently singularity is not installed on this system', file=sys.stderr)
        raise
    else:
        proc_complain(proc, 'singularity build command')


def main(args=None, check_network=False):
    parser = ArgumentParser(description='paramsurvey batch helper tool')
    parser.add_argument('--verbose', '-v', default=1, action='count', help='set logging level to INFO (-v) or DEBUG (-vv)')
    parser.add_argument('--num_cores', '--num_cpus', action='store', type=int, help='explicitly set the number of cores per  node, e.g. if short on memory')
    parser.add_argument('--num_gpus', action='store', type=int, help='explicitly set the number of gpus per  node, if autodetect fails')

    subparsers = parser.add_subparsers(dest='cmd')
    subparsers.required = True

    start = subparsers.add_parser('start', help='start head, child, or driver')
    start.add_argument('--sif', action='store', help='name of a Singularity container. Implies use of Singularity')
    start.add_argument('verb', help='head, child, or driver')
    start.add_argument('words', nargs='*', help='the driver script and args to run')
    start.set_defaults(func=starter)

    submit = subparsers.add_parser('submit', help='run a driver script from outside the batch job')
    submit.add_argument('--sif', action='store', help='name of a Singularity container. Implies use of Singularity')
    submit.add_argument('--no-wait', action='store_true', help='start job and then exit, leaving the job running')
    submit.add_argument('words', nargs='+', help='the driver script and args to run')
    submit.set_defaults(func=submitter)

    build = subparsers.add_parser('build', help='build a singularity container from a docker .tgz')
    build.add_argument('file', help='docker export tar')
    build.add_argument('--sandbox', action='store', help='writable directory inside the container')
    build.set_defaults(func=builder)

    cmd = parser.parse_args(args=args)
    cmd.func(cmd, check_network=check_network)


if __name__ == '__main__':
    print('calling main')
    main(args=sys.argv[1:])
