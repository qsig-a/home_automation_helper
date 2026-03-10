import timeit

def original(kwargs):
    transition_keys = ['strategy', 'step_interval_ms', 'step_size']
    return any(k in kwargs and kwargs[k] is not None for k in transition_keys)

def optimized(kwargs):
    return (kwargs.get('strategy') is not None or
            kwargs.get('step_interval_ms') is not None or
            kwargs.get('step_size') is not None)

kwargs_empty = {}
kwargs_one = {'strategy': 'random'}
kwargs_all = {'strategy': 'random', 'step_interval_ms': 100, 'step_size': 1}
kwargs_other = {'other': 123, 'more': 'test'}

print("Empty kwargs:")
print("Original:", timeit.timeit(lambda: original(kwargs_empty), number=1000000))
print("Optimized:", timeit.timeit(lambda: optimized(kwargs_empty), number=1000000))

print("One kwarg:")
print("Original:", timeit.timeit(lambda: original(kwargs_one), number=1000000))
print("Optimized:", timeit.timeit(lambda: optimized(kwargs_one), number=1000000))

print("All kwargs:")
print("Original:", timeit.timeit(lambda: original(kwargs_all), number=1000000))
print("Optimized:", timeit.timeit(lambda: optimized(kwargs_all), number=1000000))

print("Other kwargs:")
print("Original:", timeit.timeit(lambda: original(kwargs_other), number=1000000))
print("Optimized:", timeit.timeit(lambda: optimized(kwargs_other), number=1000000))
