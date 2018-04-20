import itertools

def flatten(ll):
    return list(itertools.chain.from_iterable(ll))
