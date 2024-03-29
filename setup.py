from __future__ import print_function

from os import path
import sys

from setuptools import setup


packages = [
    'paramsurvey_tooling',
]

# remember: keep requires synchronized with requirements.txt
requires = ['paramsurvey[ray]', 'psutil']

test_requirements = ['pytest', 'pytest-cov', 'coveralls', 'pyfakefs']

package_requirements = ['twine', 'setuptools', 'setuptools-scm[toml]']

extras_require = {
    'test': test_requirements,
    'package': package_requirements,
}

# if somehow we are running under python 2, which shouldn't happen,
# print a useful diagnostic instead of crashing on open(encoding=)

if sys.version_info[0] < 3:
    print('Somehow we are running under Python 2, which is not supported.')
    print('Python sys.executable:\n')
    print(sys.executable)
    exit(1)

this_directory = path.abspath(path.dirname(__file__))
with open(path.join(this_directory, 'README.md'), encoding='utf-8') as f:
    description = f.read()

setup(
    name='paramsurvey_tooling',
    description='A toolkit to make paramsurvey easy to use on clusters and cloud',
    use_scm_version=True,
    long_description=description,
    long_description_content_type='text/markdown',
    author='Greg Lindahl and others',
    author_email='lindahl@pbm.com',
    url='https://github.com/wumpus/paramsurvey-tooling',
    packages=packages,
    python_requires=">=3.6.*",
    extras_require=extras_require,
    install_requires=requires,
    entry_points='''
        [console_scripts]
        pstool = paramsurvey_tooling.cli:main
    ''',
    license='Apache 2.0',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Operating System :: POSIX :: Linux',
        'Environment :: MacOS X',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        #'Programming Language :: Python :: 3.5',  # setuptools-scm problem
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3 :: Only',
    ],
)
