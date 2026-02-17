#!/usr/bin/env python3
"""Benchmark sensitive-word matching strategies under concurrent load.

Compare three approaches on the same dataset:
1) naive substring scan (`word in text` over full dictionary)
2) regex alternation (`re.compile('w1|w2|...')`)
3) Aho-Corasick automaton (`pyahocorasick`)

Example:
  cd server && source .venv/bin/activate
  python scripts/benchmark_sensitive_match.py \
    --words 12000 --texts 4000 --text-len 180 \
    --concurrency 1,8,32,64 --repeat 2
"""

from __future__ import annotations

import argparse
import random
import re
import string
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from statistics import median
from typing import Callable

try:
    import ahocorasick  # type: ignore
except Exception:  # pragma: no cover
    ahocorasick = None


@dataclass
class AlgoRuntime:
    name: str
    prepare_ms: float
    fn: Callable[[str], bool]


@dataclass
class BenchRow:
    algo: str
    concurrency: int
    requests: int
    prepare_ms: float
    elapsed_s: float
    throughput_rps: float
    p50_ms: float
    p95_ms: float
    hit_count: int


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    values_sorted = sorted(values)
    idx = int((len(values_sorted) - 1) * p)
    return values_sorted[idx]


def generate_keywords(count: int, seed: int) -> list[str]:
    rnd = random.Random(seed)
    keywords: set[str] = set()
    while len(keywords) < count:
        token = "kw_" + "".join(rnd.choices(string.ascii_lowercase + string.digits, k=8))
        keywords.add(token)
    return list(keywords)


def generate_texts(
    count: int,
    text_len: int,
    keywords: list[str],
    hit_rate: float,
    seed: int,
) -> list[str]:
    rnd = random.Random(seed + 1)
    alphabet = string.ascii_lowercase + string.digits + " "
    texts: list[str] = []
    for _ in range(count):
        base = "".join(rnd.choices(alphabet, k=text_len))
        if rnd.random() < hit_rate:
            kw = rnd.choice(keywords)
            pos = rnd.randint(0, max(0, text_len - len(kw)))
            base = base[:pos] + kw + base[pos + len(kw):]
        texts.append(base)
    return texts


def build_naive(words: list[str]) -> AlgoRuntime:
    t0 = time.perf_counter()
    words_lower = [w.lower() for w in words]

    def match(text: str) -> bool:
        text_lower = text.lower()
        for word in words_lower:
            if word in text_lower:
                return True
        return False

    return AlgoRuntime("naive_contains", (time.perf_counter() - t0) * 1000.0, match)


def build_regex(words: list[str]) -> AlgoRuntime:
    t0 = time.perf_counter()
    pattern = re.compile("|".join(re.escape(w) for w in words), re.IGNORECASE)

    def match(text: str) -> bool:
        return pattern.search(text) is not None

    return AlgoRuntime("regex_union", (time.perf_counter() - t0) * 1000.0, match)


def build_aho(words: list[str]) -> AlgoRuntime | None:
    if ahocorasick is None:
        return None

    t0 = time.perf_counter()
    auto = ahocorasick.Automaton()
    for w in words:
        lw = w.lower()
        auto.add_word(lw, lw)
    auto.make_automaton()

    def match(text: str) -> bool:
        for _ in auto.iter(text.lower()):
            return True
        return False

    return AlgoRuntime("aho_corasick", (time.perf_counter() - t0) * 1000.0, match)


def run_one(algo: AlgoRuntime, payloads: list[str], concurrency: int) -> BenchRow:
    latencies_ms: list[float] = []
    hit_count = 0

    def worker(text: str) -> tuple[float, bool]:
        t0 = time.perf_counter()
        hit = algo.fn(text)
        dt = (time.perf_counter() - t0) * 1000.0
        return dt, hit

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [ex.submit(worker, text) for text in payloads]
        for fut in as_completed(futures):
            dt, hit = fut.result()
            latencies_ms.append(dt)
            if hit:
                hit_count += 1
    elapsed = time.perf_counter() - start

    requests = len(payloads)
    throughput = requests / elapsed if elapsed > 0 else 0.0
    return BenchRow(
        algo=algo.name,
        concurrency=concurrency,
        requests=requests,
        prepare_ms=algo.prepare_ms,
        elapsed_s=elapsed,
        throughput_rps=throughput,
        p50_ms=median(latencies_ms) if latencies_ms else 0.0,
        p95_ms=percentile(latencies_ms, 0.95),
        hit_count=hit_count,
    )


def print_rows(rows: list[BenchRow]) -> None:
    header = (
        f"{'algo':<16} {'conc':>5} {'req':>8} {'prep(ms)':>10} "
        f"{'elapsed(s)':>10} {'rps':>10} {'p50(ms)':>10} {'p95(ms)':>10} {'hits':>8}"
    )
    print("\n" + header)
    print("-" * len(header))
    for r in rows:
        print(
            f"{r.algo:<16} {r.concurrency:>5} {r.requests:>8} {r.prepare_ms:>10.1f} "
            f"{r.elapsed_s:>10.3f} {r.throughput_rps:>10.1f} {r.p50_ms:>10.3f} "
            f"{r.p95_ms:>10.3f} {r.hit_count:>8}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Concurrent benchmark for sensitive-word matching strategies")
    parser.add_argument("--words", type=int, default=10000, help="number of keywords")
    parser.add_argument("--texts", type=int, default=3000, help="number of request texts")
    parser.add_argument("--text-len", type=int, default=180, help="text length")
    parser.add_argument("--hit-rate", type=float, default=0.35, help="fraction of texts that contain a keyword")
    parser.add_argument("--concurrency", type=str, default="1,8,32,64", help="comma-separated concurrency levels")
    parser.add_argument("--repeat", type=int, default=2, help="repeat payload set N times")
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    args = parser.parse_args()

    conc_levels = [int(x.strip()) for x in args.concurrency.split(",") if x.strip()]

    print("Generating dataset...")
    keywords = generate_keywords(args.words, args.seed)
    texts = generate_texts(args.texts, args.text_len, keywords, args.hit_rate, args.seed)
    payloads = texts * max(1, args.repeat)

    runtimes: list[AlgoRuntime] = [build_naive(keywords), build_regex(keywords)]
    aho_runtime = build_aho(keywords)
    if aho_runtime:
        runtimes.append(aho_runtime)
    else:
        print("[WARN] pyahocorasick not available; skipping aho_corasick")

    print(
        f"Dataset ready: words={len(keywords)}, texts={len(texts)}, requests={len(payloads)}, "
        f"hit_rate={args.hit_rate}, conc={conc_levels}"
    )

    all_rows: list[BenchRow] = []
    for runtime in runtimes:
        for c in conc_levels:
            row = run_one(runtime, payloads, c)
            all_rows.append(row)
            print(
                f"done: algo={runtime.name}, conc={c}, rps={row.throughput_rps:.1f}, "
                f"p95={row.p95_ms:.3f}ms"
            )

    print_rows(all_rows)


if __name__ == "__main__":
    main()
