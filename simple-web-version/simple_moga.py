# -*- coding: utf-8 -*-
"""
simple_moga.py -- Tuned-Down, Beginner-Friendly Pure NSGA-II Timetabling Solver.

What was simplified compared to terminal-version/ and web-version/:
  - Single self-contained file using only Python's standard library (no NumPy
    broadcasting tricks, no global mutable config state).
  - Uses explicit (day, period, room_idx) tuples instead of flattened 1D slot
    indices and manual day-offset arithmetic.
  - Pure textbook NSGA-II: random initialization + simple single-gene mutation
    (no 105-line MRV greedy builder, no 3-mode conflict-targeted mutation,
    no unused G-MOGA cone dominance, no Hypervolume/Schott EMO metrics).

Run directly:
    python simple_moga.py
    python simple_moga.py --seed 1 --gens 400 --pop 100
"""

from __future__ import annotations

import argparse
import csv
import math
import os
import random
import time
from dataclasses import dataclass


# ============================================================================
# 1. PROBLEM DATA (University Instance)
# ============================================================================

DAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]

SLOTS_PER_DAY = {
    "Lundi":    ["08:30-10:00", "10:15-11:45", "13:00-14:30", "14:45-16:15"],
    "Mardi":    ["08:30-10:00", "10:15-11:45", "13:00-14:30", "14:45-16:15"],
    "Mercredi": ["08:30-10:00", "10:15-11:45", "12:00-13:30"],
    "Jeudi":    ["08:30-10:00", "10:15-11:45", "13:00-14:30", "14:45-16:15"],
    "Vendredi": ["08:30-10:00", "10:15-11:45", "13:00-14:30", "14:45-16:15"],
    "Samedi":   ["08:30-10:00", "10:15-11:45", "12:00-13:30"],
}

GROUPS = {"G1": 30, "G2": 35, "G3": 25}
ROOMS = [("S1", 30), ("S2", 40), ("S3", 60), ("S4", 80), ("Amphi", 120)]

# Day indices (0=Lundi .. 5=Samedi) when each teacher is available
TEACHER_DAYS = {
    "E1": {0, 1, 2, 3},
    "E2": {0, 1, 3, 4},
    "E3": {0, 1, 2},
    "E4": {1, 3},
    "E5": {0, 1, 2, 4},
}

# (course_name, teacher, duration_in_slots, mode)
# "ensemble" = lecture for all groups together; "séparé" = one session per group
COURSES = [
    ("Maths (CM)",       "E3", 2, "ensemble"),
    ("Probas (CM)",      "E3", 1, "ensemble"),
    ("Algorithmique",    "E1", 2, "séparé"),
    ("Struct. données",  "E1", 1, "séparé"),
    ("Bases de données", "E2", 2, "séparé"),
    ("Réseaux",          "E2", 1, "séparé"),
    ("Syst. exploit.",   "E5", 2, "séparé"),
    ("Élec. numérique",  "E5", 1, "séparé"),
    ("Anglais",          "E4", 1, "séparé"),
]


# ============================================================================
# 2. DATA MODEL & CHROMOSOME SETUP
# ============================================================================

@dataclass(frozen=True)
class Session:
    """One concrete weekly class session that must be placed on the timetable."""
    name: str
    teacher: str
    duration: int
    groups: tuple[str, ...]
    size: int


# A Gene is (day_idx, start_period_idx, room_idx).
# A Timetable (chromosome) is a list of Genes, one per Session.
Gene = tuple[int, int, int]
Timetable = list[Gene]
Score = tuple[int, float, float]  # (f1_conflicts, f2_student_comfort, f3_room_fit)


def build_sessions(
    courses: list[tuple[str, str, int, str]] = COURSES,
    groups: dict[str, int] = GROUPS,
) -> list[Session]:
    """Expand high-level courses into individual schedulable Session objects."""
    all_groups = tuple(groups.keys())
    total_students = sum(groups.values())
    sessions: list[Session] = []

    for name, teacher, duration, mode in courses:
        if mode == "ensemble":
            sessions.append(Session(name, teacher, duration, all_groups, total_students))
        else:
            for g in all_groups:
                sessions.append(Session(name, teacher, duration, (g,), groups[g]))
    return sessions


def compute_valid_starts(
    sessions: list[Session],
    days: list[str] = DAYS,
    slots_per_day: dict[str, list[str]] = SLOTS_PER_DAY,
) -> list[list[tuple[int, int]]]:
    """
    For each session, list every (day_idx, start_period) where `duration`
    consecutive slots fit inside that day without spilling into the next day.
    """
    valid_starts: list[list[tuple[int, int]]] = []
    for session in sessions:
        options: list[tuple[int, int]] = []
        for day_idx, day_name in enumerate(days):
            n_slots = len(slots_per_day[day_name])
            for period in range(n_slots - session.duration + 1):
                options.append((day_idx, period))
        valid_starts.append(options)
    return valid_starts


def random_timetable(
    valid_starts: list[list[tuple[int, int]]],
    n_rooms: int,
    rng: random.Random,
) -> Timetable:
    """Create one random candidate timetable."""
    timetable: Timetable = []
    for options in valid_starts:
        day_idx, period = rng.choice(options)
        room_idx = rng.randrange(n_rooms)
        timetable.append((day_idx, period, room_idx))
    return timetable


# ============================================================================
# 3. OBJECTIVE FUNCTIONS (f1, f2, f3)
# ============================================================================

def evaluate(
    timetable: Timetable,
    sessions: list[Session],
    rooms: list[tuple[str, int]] = ROOMS,
    teacher_days: dict[str, set[int]] = TEACHER_DAYS,
    groups: dict[str, int] = GROUPS,
    n_days: int = len(DAYS),
) -> Score:
    """
    Evaluate a timetable on 3 objectives (all minimized):
      f1: Hard constraint violations (must be 0 for a valid timetable):
          - teacher taught on an unavailable day
          - teacher teaching >1 session at the same (day, period)
          - group attending >1 session at the same (day, period)
          - room hosting >1 session at the same (day, period)
      f2: Student comfort = total intra-day gaps + sum of daily-load std dev.
      f3: Room mismatch = wasted seats (or 5x penalty if room is too small).
    """
    teacher_busy: dict[tuple[str, int, int], int] = {}
    group_busy: dict[tuple[str, int, int], int] = {}
    room_busy: dict[tuple[int, int, int], int] = {}
    group_day_periods: dict[str, list[set[int]]] = {
        g: [set() for _ in range(n_days)] for g in groups
    }

    f1 = 0
    f3 = 0.0

    for session, (day_idx, start_p, room_idx) in zip(sessions, timetable):
        # 1) Teacher availability
        if day_idx not in teacher_days[session.teacher]:
            f1 += session.duration

        # 2) Double-bookings per occupied time slot
        for dt in range(session.duration):
            p = start_p + dt

            t_key = (session.teacher, day_idx, p)
            teacher_busy[t_key] = teacher_busy.get(t_key, 0) + 1
            if teacher_busy[t_key] > 1:
                f1 += 1

            r_key = (room_idx, day_idx, p)
            room_busy[r_key] = room_busy.get(r_key, 0) + 1
            if room_busy[r_key] > 1:
                f1 += 1

            for g in session.groups:
                g_key = (g, day_idx, p)
                group_busy[g_key] = group_busy.get(g_key, 0) + 1
                if group_busy[g_key] > 1:
                    f1 += 1
                group_day_periods[g][day_idx].add(p)

        # 3) Room capacity fit (soft penalty, asymmetric for under-sized rooms)
        _, cap = rooms[room_idx]
        if cap >= session.size:
            f3 += (cap - session.size) / cap
        else:
            f3 += 5.0 * (session.size - cap) / session.size

    # 4) Student gaps and daily load balance across the week
    f2 = 0.0
    for g in groups:
        daily_loads: list[int] = []
        for day_idx in range(n_days):
            periods = sorted(group_day_periods[g][day_idx])
            daily_loads.append(len(periods))
            if len(periods) > 1:
                span = periods[-1] - periods[0] + 1
                f2 += span - len(periods)  # empty slots between first and last class

        mean_load = sum(daily_loads) / n_days
        variance = sum((x - mean_load) ** 2 for x in daily_loads) / n_days
        f2 += math.sqrt(variance)

    return (f1, f2, f3)


# ============================================================================
# 4. PURE NSGA-II ENGINE (Dominance, Sorting, Crowding, Operators)
# ============================================================================

def dominates(a: Score, b: Score) -> bool:
    """
    Constrained Pareto dominance (Deb et al., 2002):
      - Any valid schedule (f1 == 0) dominates any invalid schedule (f1 > 0).
      - Between two invalid schedules, fewer conflicts (smaller f1) wins.
      - Between two valid schedules, standard Pareto dominance on (f2, f3):
        a is <= b on all objectives and strictly < b on at least one.
    """
    if (a[0] == 0) != (b[0] == 0):
        return a[0] == 0
    if a[0] > 0 and b[0] > 0:
        return a[0] < b[0]
    return (a[1] <= b[1] and a[2] <= b[2]) and (a[1] < b[1] or a[2] < b[2])


def non_dominated_sort(scores: list[Score]) -> tuple[list[list[int]], list[int]]:
    """
    Sort population indices into Pareto fronts:
      Front 0 = non-dominated solutions, Front 1 = dominated only by Front 0, etc.
    Returns (fronts, rank_of_each_individual).
    """
    n = len(scores)
    dominates_list: list[list[int]] = [[] for _ in range(n)]
    dominated_by_count = [0] * n
    rank = [0] * n
    fronts: list[list[int]] = [[]]

    for p in range(n):
        for q in range(n):
            if p == q:
                continue
            if dominates(scores[p], scores[q]):
                dominates_list[p].append(q)
            elif dominates(scores[q], scores[p]):
                dominated_by_count[p] += 1
        if dominated_by_count[p] == 0:
            rank[p] = 0
            fronts[0].append(p)

    i = 0
    while fronts[i]:
        next_front: list[int] = []
        for p in fronts[i]:
            for q in dominates_list[p]:
                dominated_by_count[q] -= 1
                if dominated_by_count[q] == 0:
                    rank[q] = i + 1
                    next_front.append(q)
        i += 1
        fronts.append(next_front)

    fronts.pop()
    return fronts, rank


def crowding_distance(scores: list[Score], front: list[int]) -> dict[int, float]:
    """
    Measure how spread out each individual is inside a single Pareto front.
    Boundary individuals receive infinity so extreme trade-offs are kept.
    """
    dist = {idx: 0.0 for idx in front}
    if len(front) <= 2:
        for idx in front:
            dist[idx] = float("inf")
        return dist

    n_obj = len(scores[0])
    for m in range(n_obj):
        ordered = sorted(front, key=lambda idx: scores[idx][m])
        dist[ordered[0]] = float("inf")
        dist[ordered[-1]] = float("inf")
        f_min = scores[ordered[0]][m]
        f_max = scores[ordered[-1]][m]
        if f_max == f_min:
            continue
        for k in range(1, len(ordered) - 1):
            gap = scores[ordered[k + 1]][m] - scores[ordered[k - 1]][m]
            dist[ordered[k]] += gap / (f_max - f_min)
    return dist


def tournament_select(
    pop: list[Timetable],
    rank: list[int],
    crowd: dict[int, float],
    rng: random.Random,
) -> Timetable:
    """Binary tournament: lower Pareto rank wins; ties break by larger crowding."""
    a, b = rng.randrange(len(pop)), rng.randrange(len(pop))
    if rank[a] != rank[b]:
        return pop[a] if rank[a] < rank[b] else pop[b]
    return pop[a] if crowd[a] >= crowd[b] else pop[b]


def crossover(
    parent1: Timetable,
    parent2: Timetable,
    rng: random.Random,
    p_cross: float = 0.90,
) -> tuple[Timetable, Timetable]:
    """Uniform crossover: for each session, randomly inherit from parent 1 or 2."""
    if rng.random() >= p_cross:
        return list(parent1), list(parent2)

    child1: Timetable = []
    child2: Timetable = []
    for g1, g2 in zip(parent1, parent2):
        if rng.random() < 0.5:
            child1.append(g1)
            child2.append(g2)
        else:
            child1.append(g2)
            child2.append(g1)
    return child1, child2


def mutate(
    timetable: Timetable,
    valid_starts: list[list[tuple[int, int]]],
    n_rooms: int,
    rng: random.Random,
    p_mut: float = 0.08,
) -> Timetable:
    """
    Simple single-gene mutation: with probability `p_mut` per session,
    randomly change either its time slot OR its room.
    """
    out = list(timetable)
    for s in range(len(out)):
        if rng.random() < p_mut:
            day_idx, period, room_idx = out[s]
            if rng.random() < 0.5:
                new_day, new_period = rng.choice(valid_starts[s])
                out[s] = (new_day, new_period, room_idx)
            else:
                out[s] = (day_idx, period, rng.randrange(n_rooms))
    return out


def remove_duplicates(
    pop: list[Timetable],
    scores: list[Score],
    target_size: int,
) -> tuple[list[Timetable], list[Score]]:
    """Keep unique chromosomes first so duplicates do not crowd out diversity."""
    seen: set[tuple[Gene, ...]] = set()
    uniq_pop: list[Timetable] = []
    uniq_scores: list[Score] = []
    dups: list[tuple[Timetable, Score]] = []

    for ind, sc in zip(pop, scores):
        key = tuple(ind)
        if key not in seen:
            seen.add(key)
            uniq_pop.append(ind)
            uniq_scores.append(sc)
        else:
            dups.append((ind, sc))

    for ind, sc in dups:
        if len(uniq_pop) >= target_size:
            break
        uniq_pop.append(ind)
        uniq_scores.append(sc)
    return uniq_pop, uniq_scores


def solve(
    pop_size: int = 100,
    n_generations: int = 400,
    seed: int = 42,
    p_cross: float = 0.90,
    p_mut: float = 0.08,
    verbose: bool = True,
    days: list[str] = DAYS,
    slots_per_day: dict[str, list[str]] = SLOTS_PER_DAY,
    groups: dict[str, int] = GROUPS,
    rooms: list[tuple[str, int]] = ROOMS,
    teacher_days: dict[str, set[int]] = TEACHER_DAYS,
    courses: list[tuple[str, str, int, str]] = COURSES,
    progress_callback=None,
    should_stop=None,
) -> tuple[list[tuple[Timetable, Score]], int, list[dict]]:
    """
    Run pure NSGA-II and return:
      - pareto_front: list of (timetable, score) on Front 0
      - best_idx: index of the best compromise solution in pareto_front
      - history: per-generation summary statistics
    """
    rng = random.Random(seed)
    sessions = build_sessions(courses=courses, groups=groups)
    valid_starts = compute_valid_starts(sessions, days=days, slots_per_day=slots_per_day)
    n_rooms = len(rooms)
    n_days = len(days)

    def eval_ind(ind: Timetable) -> Score:
        return evaluate(
            ind,
            sessions,
            rooms=rooms,
            teacher_days=teacher_days,
            groups=groups,
            n_days=n_days,
        )

    pop = [random_timetable(valid_starts, n_rooms, rng) for _ in range(pop_size)]
    scores = [eval_ind(ind) for ind in pop]
    history: list[dict] = []

    def record(gen: int, current_scores: list[Score]) -> None:
        valid_count = sum(1 for sc in current_scores if sc[0] == 0)
        f1_min = min(sc[0] for sc in current_scores)
        f2_min = min(sc[1] for sc in current_scores)
        f3_min = min(sc[2] for sc in current_scores)
        row = {
            "gen": gen,
            "valid": valid_count,
            "f1_min": f1_min,
            "f2_min": f2_min,
            "f3_min": f3_min,
        }
        history.append(row)
        if progress_callback is not None:
            progress_callback(gen, row)
        if verbose and (gen == 0 or gen == 1 or gen % 50 == 0 or gen == n_generations):
            print(
                f"  gen {gen:3d} | valid: {valid_count:3d}/{pop_size} | "
                f"best f1={f1_min} f2={f2_min:.2f} f3={f3_min:.2f}"
            )

    record(0, scores)

    for gen in range(1, n_generations + 1):
        if should_stop is not None and should_stop():
            raise InterruptedError("Optimization stopped by user.")

        # 1. Rank current population and compute crowding
        fronts, rank = non_dominated_sort(scores)
        crowd: dict[int, float] = {}
        for fr in fronts:
            crowd.update(crowding_distance(scores, fr))

        # 2. Generate offspring via tournament + crossover + mutation
        children: list[Timetable] = []
        while len(children) < pop_size:
            p1 = tournament_select(pop, rank, crowd, rng)
            p2 = tournament_select(pop, rank, crowd, rng)
            c1, c2 = crossover(p1, p2, rng, p_cross=p_cross)
            children.append(mutate(c1, valid_starts, n_rooms, rng, p_mut=p_mut))
            if len(children) < pop_size:
                children.append(mutate(c2, valid_starts, n_rooms, rng, p_mut=p_mut))

        child_scores = [eval_ind(ind) for ind in children]

        # 3. Combine parents + children (elitism) and select best `pop_size`
        combined_pop, combined_scores = remove_duplicates(
            pop + children, scores + child_scores, pop_size
        )
        fronts, _ = non_dominated_sort(combined_scores)

        kept_indices: list[int] = []
        for fr in fronts:
            if len(kept_indices) + len(fr) <= pop_size:
                kept_indices.extend(fr)
            else:
                cd = crowding_distance(combined_scores, fr)
                fr_sorted = sorted(fr, key=lambda idx: cd[idx], reverse=True)
                needed = pop_size - len(kept_indices)
                kept_indices.extend(fr_sorted[:needed])
                break

        pop = [combined_pop[i] for i in kept_indices]
        scores = [combined_scores[i] for i in kept_indices]
        record(gen, scores)

    # Extract deduplicated Pareto Front 0 and pick the ultimate compromise
    fronts, _ = non_dominated_sort(scores)
    seen_obj: set[tuple[int, float, float]] = set()
    pareto_front: list[tuple[Timetable, Score]] = []
    for idx in fronts[0]:
        sc = scores[idx]
        key = (sc[0], round(sc[1], 4), round(sc[2], 4))
        if key not in seen_obj:
            seen_obj.add(key)
            pareto_front.append((pop[idx], sc))

    pareto_front.sort(key=lambda item: item[1])
    best_idx = pick_best_compromise(pareto_front)
    return pareto_front, best_idx, history


def pick_best_compromise(pareto_front: list[tuple[Timetable, Score]]) -> int:
    """
    From Front 0, keep only conflict-free solutions (f1 == 0) if any exist,
    normalize (f2, f3) to [0, 1], and pick the closest to the ideal point (0, 0).
    """
    valid_idx = [i for i, (_, sc) in enumerate(pareto_front) if sc[0] == 0]
    candidates = valid_idx if valid_idx else list(range(len(pareto_front)))

    cols = (1, 2) if valid_idx else (0, 1, 2)
    mins = [min(pareto_front[i][1][c] for i in candidates) for c in cols]
    maxs = [max(pareto_front[i][1][c] for i in candidates) for c in cols]
    spans = [(mx - mn) or 1.0 for mn, mx in zip(mins, maxs)]

    def distance_to_utopia(i: int) -> float:
        sc = pareto_front[i][1]
        return math.sqrt(sum(((sc[c] - mn) / sp) ** 2 for c, mn, sp in zip(cols, mins, spans)))

    return min(candidates, key=distance_to_utopia)


# ============================================================================
# 5. HUMAN-READABLE TIMETABLE DISPLAY & CSV EXPORT
# ============================================================================

def print_schedule(
    timetable: Timetable,
    score: Score,
    sessions: list[Session],
    days: list[str] = DAYS,
    slots_per_day: dict[str, list[str]] = SLOTS_PER_DAY,
    groups: dict[str, int] = GROUPS,
    rooms: list[tuple[str, int]] = ROOMS,
) -> None:
    """Print the Pareto score and a weekly grid for every student group."""
    print("\n" + "=" * 78)
    print(f"ULTIMATE SOLUTION | f1(conflicts)={score[0]} | f2(comfort)={score[1]:.2f} | f3(rooms)={score[2]:.2f}")
    print("=" * 78)

    # Collect ordered unique time-slot labels chronologically across the week
    all_labels: list[str] = sorted(
        {lbl for day in days for lbl in slots_per_day[day]}
    )

    for group_name, group_size in groups.items():
        grid: dict[tuple[str, str], list[str]] = {}
        for session, (day_idx, start_p, room_idx) in zip(sessions, timetable):
            if group_name not in session.groups:
                continue
            day_name = days[day_idx]
            room_name = rooms[room_idx][0]
            for dt in range(session.duration):
                lbl = slots_per_day[day_name][start_p + dt]
                grid.setdefault((lbl, day_name), []).append(
                    f"{session.name} ({session.teacher},{room_name})"
                )

        print(f"\n--- Group {group_name} ({group_size} students) ---")
        col_w = 27
        header = f"{'Slot':<13}|" + "|".join(f"{d:^{col_w}}" for d in days) + "|"
        sep = "-" * len(header)
        print(sep)
        print(header)
        print(sep)
        for lbl in all_labels:
            cells = []
            for d in days:
                if lbl not in slots_per_day[d]:
                    cells.append(f"{'---':^{col_w}}")
                else:
                    entries = grid.get((lbl, d), [])
                    text = " / ".join(entries) if entries else "."
                    if len(text) > col_w - 1:
                        text = text[: col_w - 3] + ".."
                    cells.append(f"{text:<{col_w}}")
            print(f"{lbl:<13}|" + "|".join(cells) + "|")
        print(sep)


def export_schedule_csv(
    timetable: Timetable,
    sessions: list[Session],
    filepath: str,
    days: list[str] = DAYS,
    slots_per_day: dict[str, list[str]] = SLOTS_PER_DAY,
    rooms: list[tuple[str, int]] = ROOMS,
) -> None:
    """Write the chosen timetable as a flat session list CSV."""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Course", "Groups", "Teacher", "Day", "Start", "Duration", "Room", "Capacity", "Students"])
        for session, (day_idx, start_p, room_idx) in zip(sessions, timetable):
            day_name = days[day_idx]
            start_label = slots_per_day[day_name][start_p].split("-")[0]
            room_name, cap = rooms[room_idx]
            writer.writerow([
                session.name,
                "+".join(session.groups),
                session.teacher,
                day_name,
                start_label,
                session.duration,
                room_name,
                cap,
                session.size,
            ])


def main() -> None:
    parser = argparse.ArgumentParser(description="Tuned-down pure NSGA-II timetabling solver")
    parser.add_argument("--pop", type=int, default=100, help="Population size (default: 100)")
    parser.add_argument("--gens", type=int, default=400, help="Generations (default: 400)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument("--mut", type=float, default=0.08, help="Per-session mutation rate (default: 0.08)")
    parser.add_argument("--csv", type=str, default=None, help="Optional path to export final timetable CSV")
    args = parser.parse_args()

    print(f"Running Pure NSGA-II (pop={args.pop}, gens={args.gens}, seed={args.seed}, mut={args.mut})...")
    t0 = time.time()
    pareto_front, best_idx, _ = solve(
        pop_size=args.pop,
        n_generations=args.gens,
        seed=args.seed,
        p_mut=args.mut,
        verbose=True,
    )
    elapsed = time.time() - t0

    print(f"\nDone in {elapsed:.2f}s | Pareto front size: {len(pareto_front)}")
    for i, (_, sc) in enumerate(pareto_front):
        marker = " <-- ULTIMATE" if i == best_idx else ""
        print(f"  [{i}] f1={sc[0]}  f2={sc[1]:.3f}  f3={sc[2]:.3f}{marker}")

    best_timetable, best_score = pareto_front[best_idx]
    sessions = build_sessions()
    print_schedule(best_timetable, best_score, sessions)

    if args.csv:
        out_dir = os.path.dirname(os.path.abspath(args.csv))
        os.makedirs(out_dir, exist_ok=True)
        export_schedule_csv(best_timetable, sessions, args.csv)
        print(f"\nExported CSV to: {args.csv}")


if __name__ == "__main__":
    main()
