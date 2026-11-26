"""과제: 개별 체이닝과 선형 탐지의 탐색 비용 비교.

같은 키를 같은 크기(M = 4093)의 두 테이블에 같은 순서로 넣고, 크기 늘리기는 끈다.
적재율 α = 0.1, 0.2, ..., 0.9에서 잰다.
  체이닝: 비교한 노드 수          성공 ≈ 1 + α/2            실패 ≈ α
  선형 탐지: 들여다본 칸 수      성공 ≈ (1 + 1/(1-α))/2     실패 ≈ (1 + 1/(1-α)²)/2
실패 탐색은 넣지 않은 URL 2000개, 시드가 다른 시행 5번 평균. 외부 라이브러리를 쓰지 않는다.

    python3 experiments/compare_experiment.py
결과: experiments/compare_results.csv, experiments/compare.svg
"""
import csv
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))
sys.path.insert(0, HERE)

from hash_table import HashTable  # noqa: E402
from linear_probing import LinearProbingHashTable  # noqa: E402
from probe_experiment import random_url  # noqa: E402
from svgplot import write_svg  # noqa: E402

M = 4093
ALPHAS = [round(0.1 * k, 1) for k in range(1, 10)]   # 0.1 ~ 0.9
TRIALS = 5
MISSES = 2000


def chain_success(a):
    return 1 + a / 2


def chain_fail(a):
    return a


def linear_success(a):
    return (1 + 1 / (1 - a)) / 2


def linear_fail(a):
    return (1 + 1 / (1 - a) ** 2) / 2


def measure(alphas=ALPHAS, trials=TRIALS, misses=MISSES, m=M, seed=2026):
    """적재율마다 [체이닝 성공, 체이닝 실패, 선형 성공, 선형 실패] 평균."""
    acc = [[0.0, 0.0, 0.0, 0.0] for _ in alphas]
    for t in range(trials):
        rng = random.Random(seed + t)
        chain = HashTable(capacity=m, max_load=None)
        linear = LinearProbingHashTable(capacity=m, max_load=None)
        keys = []
        absent = [random_url(rng, j, host="absent.example.org") for j in range(misses)]
        for a_i, alpha in enumerate(alphas):
            target = round(alpha * m)
            while len(keys) < target:
                k = random_url(rng, len(keys))
                chain.put(k, len(keys))
                linear.put(k, len(keys))   # 같은 키, 같은 순서
                keys.append(k)
            acc[a_i][0] += sum(chain.probes(k) for k in keys) / len(keys)
            acc[a_i][1] += sum(chain.probes(k) for k in absent) / len(absent)
            acc[a_i][2] += sum(linear.probes(k) for k in keys) / len(keys)
            acc[a_i][3] += sum(linear.probes(k) for k in absent) / len(absent)
    return [[v / trials for v in row] for row in acc]


def main():
    res = measure()
    header = ["alpha", "n", "chain_success", "chain_success_theory", "chain_fail",
              "chain_fail_theory", "linear_success", "linear_success_theory",
              "linear_fail", "linear_fail_theory"]
    rows = []
    print("M = %d, 시행 %d번 평균, 실패 탐색 %d회" % (M, TRIALS, MISSES))
    print("%5s | %-23s | %-23s | %-23s | %-23s" % ("α", "체이닝 성공 (실험/이론)", "체이닝 실패",
                                                 "선형 성공", "선형 실패"))
    for a, (cs, cf, ls, lf) in zip(ALPHAS, res):
        row = [a, round(a * M), cs, chain_success(a), cf, chain_fail(a),
               ls, linear_success(a), lf, linear_fail(a)]
        rows.append([row[0], row[1]] + [round(v, 4) for v in row[2:]])
        print("%5.1f | %10.3f / %-10.3f | %10.3f / %-10.3f | %10.3f / %-10.3f | %10.3f / %-10.3f"
              % (a, cs, chain_success(a), cf, chain_fail(a), ls, linear_success(a),
                 lf, linear_fail(a)))

    with open(os.path.join(HERE, "compare_results.csv"), "w", newline="", encoding="utf-8") as fp:
        w = csv.writer(fp)
        w.writerow(header)
        w.writerows(rows)

    xs = [i / 200 for i in range(0, 185)]   # 0 ~ 0.92
    blue, orange = "#257de0", "#f47230"

    def panel(title, ylabel, ymax, ystep_hint, chain_f, lin_f, ci, li):
        return {"title": title, "xlabel": "적재율 α", "ylabel": ylabel,
                "xmax": 1.0, "ymax": ymax, "xstep": 0.1,
                "series": [
                    {"name": "체이닝 이론", "color": blue, "points": [(x, chain_f(x)) for x in xs]},
                    {"name": "체이닝 실험", "color": blue, "markers": True,
                     "points": [(a, r[ci]) for a, r in zip(ALPHAS, res)]},
                    {"name": "선형 탐지 이론", "color": orange, "dashed": True,
                     "points": [(x, lin_f(x)) for x in xs]},
                    {"name": "선형 탐지 실험", "color": orange, "markers": True,
                     "points": [(a, r[li]) for a, r in zip(ALPHAS, res)]},
                ]}

    p1 = panel("성공 탐색", "평균 비용 (노드 수 / 칸 수)", 6, 1, chain_success, linear_success, 0, 2)
    p2 = panel("실패 탐색", "평균 비용 (노드 수 / 칸 수)", 55, 10, chain_fail, linear_fail, 1, 3)
    write_svg(os.path.join(HERE, "compare.svg"), [p1, p2], p1["series"],
              title="개별 체이닝 vs 선형 탐지 · M = 4093, 같은 키")
    print("저장: experiments/compare_results.csv, experiments/compare.svg")


if __name__ == "__main__":
    main()
