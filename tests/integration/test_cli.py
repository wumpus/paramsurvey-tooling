import subprocess

import paramsurvey_tooling.cli as cli


def test_debug():
    # crash testing only
    subprocess.run(['pstool', 'debug'], check=True)
