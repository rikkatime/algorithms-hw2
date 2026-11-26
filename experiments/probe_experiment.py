"""6단계: 개별 체이닝의 적재율별 평균 탐색 비용 (비교한 노드 수).

칸 수를 4093으로 고정한 HashTable(max_load=None)에 무작위 URL을 넣으며
적재율 α = 0.25, 0.5, ..., 4에서 멈추고 잰다.
  성공 탐색: 넣은 키 전부를 찾을 때 비교한 노드 수의 평균      이론 ≈ 1 + α/2
  실패 탐색: 넣지 않은 URL 2000개를 찾을 때 비교한 노드 수의 평균  이론 ≈ α
시드가 다른 시행 5번을 평균한다. 외부 라이브러리를 쓰지 않는다.

    python3 experiments/probe_experiment.py
결과: experiments/results.csv, experiments/results.svg
"""
import csv
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, HERE)

from hash_table import HashTable  # noqa: E402
from svgplot import write_svg  # noqa: E402

M = 4093
ALPHAS = [0.25 * k for k in range(1, 17)]   # 0.25 ~ 4.0
TRIALS = 5
MISSES = 2000
LETTERS = "abcdefghijklmnopqrstuvwxyz0123456789"


def random_url(rng, i, host="example.com"):
    """i번째 무작위 URL. 번호 i가 들어가므로 서로 겹치지 않는다."""
    path = "".join(rng.choice(LETTERS) for _ in range(rng.randint(4, 12)))
    return "https://%s/%d/%s" % (host, i, path)


def measure(alphas, trials=TRIALS, misses=MISSES, m=M, seed=2026):
    """적재율마다 (성공 평균, 실패 평균)."""
    succ = [0.0] * len(alphas)
    fail = [0.0] * len(alphas)
    for t in range(trials):
        rng = random.Random(seed + t)
        table = HashTable(capacity=m, max_load=None)
        keys = []
        absent = [random_url(rng, j, host="absent.example.org") for j in range(misses)]
        for a_i, alpha in enumerate(alphas):
            target = round(alpha * m)
            while len(keys) < target:
                k = random_url(rng, len(keys))
                table.put(k, len(keys))
                keys.append(k)
            succ[a_i] += sum(table.probes(k) for k in keys) / len(keys)
            fail[a_i] += sum(table.probes(k) for k in absent) / len(absent)
    return [s / trials for s in succ], [f / trials for f in fail]


def main():
    succ, fail = measure(ALPHAS)
    rows = []
    print("M = %d, 시행 %d번 평균, 실패 탐색 %d회" % (M, TRIALS, MISSES))
    print("%6s %7s %10s %10s %10s %10s" % ("α", "n", "성공(실험)", "성공(이론)", "실패(실험)", "실패(이론)"))
    for a, s, f in zip(ALPHAS, succ, fail):
        row = [a, round(a * M), round(s, 4), round(1 + a / 2, 4), round(f, 4), round(a, 4)]
        rows.append(row)
        print("%6.2f %7d %10.3f %10.3f %10.3f %10.3f" % tuple(row))

    with open(os.path.join(HERE, "results.csv"), "w", newline="", encoding="utf-8") as fp:
        w = csv.writer(fp)
        w.writerow(["alpha", "n", "success_experiment", "success_theory",
                    "fail_experiment", "fail_theory"])
        w.writerows(rows)

    xs = [i / 20 for i in range(0, 81)]
    blue, orange = "#257de0", "#f47230"
    series = [
        {"name": "성공 · 이론 1 + α/2", "color": blue, "points": [(x, 1 + x / 2) for x in xs]},
        {"name": "성공 · 실험", "color": blue, "markers": True, "points": list(zip(ALPHAS, succ))},
        {"name": "실패 · 이론 α", "color": orange, "dashed": True, "points": [(x, x) for x in xs]},
        {"name": "실패 · 실험", "color": orange, "markers": True, "points": list(zip(ALPHAS, fail))},
    ]
    panel = {"title": "개별 체이닝 · M = 4093", "xlabel": "적재율 α = n / M",
             "ylabel": "평균 비교 노드 수", "xmax": 4, "ymax": 4.5, "xstep": 0.5,
             "series": series}
    write_svg(os.path.join(HERE, "results.svg"), [panel], series)
    print("저장: experiments/results.csv, experiments/results.svg")


if __name__ == "__main__":
    main()
