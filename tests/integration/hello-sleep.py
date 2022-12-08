#!/usr/bin/env python

import time
import paramsurvey


def sleep_worker(pset, system_kwargs, user_kwargs):
    print('hello from pset', pset['i'])
    time.sleep(pset['duration'])
    return {'slept': pset['duration']}


def main():
    paramsurvey.init(backend='ray')

    psets = [{'duration': 0.1}] * 15

    # this awkwardness is caused by psets being a list of references to the same dict
    new = []
    for pset, r in zip(psets, range(len(psets))):
        pset = pset.copy()
        pset['i'] = r
        new.append(pset)
    psets = new

    results = paramsurvey.map(sleep_worker, psets)


if __name__ == '__main__':
    main()
