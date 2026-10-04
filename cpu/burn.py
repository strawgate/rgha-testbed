"""Fixed amount of pure-Python CPU work, split over N processes.

Same total work on every runner, so wall time and CPU cost are comparable:
`python cpu/burn.py <chunks> <processes>`.
"""

import os
import resource
import sys
import time
from multiprocessing import Pool

ITERATIONS = 40_000_000  # per chunk; a few seconds per chunk on one vCPU


def chunk(seed: int) -> int:
    acc = seed
    for i in range(ITERATIONS):
        acc = (acc * 31 + i) & 0xFFFFFFFF
    return acc


if __name__ == "__main__":
    chunks, procs = int(sys.argv[1]), int(sys.argv[2])
    t0 = time.monotonic()
    with Pool(procs) as pool:
        result = sum(pool.map(chunk, range(chunks)))
    wall = time.monotonic() - t0
    ru = resource.getrusage(resource.RUSAGE_CHILDREN)
    cpu = ru.ru_utime + ru.ru_stime
    print(f"chunks={chunks} procs={procs} nproc={os.cpu_count()} wall={wall:.1f}s cpu={cpu:.1f}s "
          f"parallelism={cpu / wall:.2f} result={result}")
