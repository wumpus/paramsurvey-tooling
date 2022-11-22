Running paramsurvey on a laptop doesn't require any software other
than your software and the paramsurvey package.

```
$ pip install paramsurvey
$ python ./my-program.py
```

By default paramsurvey will use Python's `multiprocessing module`, and
will use all of your laptop's cores.

If you're debugging, you might want to use some environment variables
to only run a small computation and get more debugging info. This is
an example:

```
$ PARAMSURVEY_VERBOSE=3 PARAMSURVEY_LIMIT=1 python ./my-program.py
```

Remember to check the hidden logfile (`ls -la`) if you would like to
see debugging information from previous runs.
