# -*- coding: utf-8 -*-
"""
terminal.py -- Interactive Terminal Version of Pure NSGA-II Timetabling.

Run with:
    python terminal.py
    python terminal.py --defaults
"""

from __future__ import annotations

import argparse
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import simple_moga as sm


def ask(prompt: str, default=None, cast=str, validate=None):
    """Read user input with a default value and validation."""
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"  {prompt}{suffix}: ").strip()
        if raw == "" and default is not None:
            raw = str(default)
        try:
            val = cast(raw)
            if validate and not validate(val):
                raise ValueError()
            return val
        except (ValueError, TypeError):
            print("  Invalid value, please try again.")


def prompt_problem_data():
    """Let the user keep default university data or enter custom data."""
    print("=" * 72)
    print("  SIMPLE MOGA TIMETABLING -- TERMINAL VERSION (Pure NSGA-II)")
    print("=" * 72)

    use_default = ask("Use default university dataset? (y/n)", default="y").lower()
    if use_default.startswith("y"):
        days = list(sm.DAYS)
        slots_per_day = dict(sm.SLOTS_PER_DAY)
        groups = dict(sm.GROUPS)
        rooms = list(sm.ROOMS)
        teacher_days = {k: set(v) for k, v in sm.TEACHER_DAYS.items()}
        courses = list(sm.COURSES)
    else:
        print("\n[1/5] Days")
        default_days = ",".join(sm.DAYS)
        days_raw = ask("Active days (comma-separated)", default=default_days)
        days = [d.strip() for d in days_raw.split(",") if d.strip()]
        slots_per_day = {
            d: sm.SLOTS_PER_DAY.get(d, ["08:30-10:00", "10:15-11:45", "13:00-14:30", "14:45-16:15"])
            for d in days
        }

        print("\n[2/5] Student Groups")
        n_grp = ask("Number of groups", default=3, cast=int, validate=lambda x: x >= 1)
        groups = {}
        for i in range(n_grp):
            name = ask(f"  Group {i + 1} name", default=f"G{i + 1}")
            size = ask(f"  Students in {name}", default=30, cast=int, validate=lambda x: x >= 1)
            groups[name] = size

        print("\n[3/5] Rooms")
        n_rooms = ask("Number of rooms", default=5, cast=int, validate=lambda x: x >= 1)
        rooms = []
        for i in range(n_rooms):
            rname = ask(f"  Room {i + 1} name", default=f"S{i + 1}")
            cap = ask(f"  Capacity of {rname}", default=40, cast=int, validate=lambda x: x >= 1)
            rooms.append((rname, cap))

        print("\n[4/5] Teachers & Available Days")
        print("  Day indices:", ", ".join(f"{i}={d[:3]}" for i, d in enumerate(days)))
        n_teach = ask("Number of teachers", default=5, cast=int, validate=lambda x: x >= 1)
        teacher_days = {}
        default_idx = ",".join(str(i) for i in range(len(days)))
        for i in range(n_teach):
            tname = ask(f"  Teacher {i + 1} name", default=f"E{i + 1}")
            raw_idx = ask(f"  Available day indices for {tname}", default=default_idx)
            parsed = {
                int(x.strip())
                for x in raw_idx.split(",")
                if x.strip().isdigit() and 0 <= int(x.strip()) < len(days)
            }
            teacher_days[tname] = parsed or set(range(len(days)))

        print("\n[5/5] Courses")
        teacher_names = list(teacher_days.keys())
        n_courses = ask("Number of courses", default=len(sm.COURSES), cast=int, validate=lambda x: x >= 1)
        courses = []
        for i in range(n_courses):
            cname = ask(f"  Course {i + 1} name", default=f"Course{i + 1}")
            tname = ask(
                f"  Teacher for {cname}",
                default=teacher_names[i % len(teacher_names)],
                validate=lambda x: x in teacher_days,
            )
            dur = ask(f"  Duration in slots (1 or 2)", default=1, cast=int, validate=lambda x: 1 <= x <= 4)
            mode_in = ask("  Mode (c=all groups together, t=separate per group)", default="t").lower()
            mode = "ensemble" if mode_in.startswith("c") else "séparé"
            courses.append((cname, tname, dur, mode))

    print("\n[Algorithm Parameters]")
    pop_size = ask("Population size", default=100, cast=int, validate=lambda x: x >= 10)
    n_generations = ask("Generations", default=400, cast=int, validate=lambda x: x >= 1)
    p_mut = ask("Mutation rate per session", default=0.08, cast=float, validate=lambda x: 0.0 <= x <= 1.0)
    seed = ask("Random seed", default=42, cast=int)

    return {
        "days": days,
        "slots_per_day": slots_per_day,
        "groups": groups,
        "rooms": rooms,
        "teacher_days": teacher_days,
        "courses": courses,
        "pop_size": pop_size,
        "n_generations": n_generations,
        "p_mut": p_mut,
        "seed": seed,
    }


def run_interactive(use_defaults: bool = False) -> None:
    if use_defaults:
        cfg = {
            "days": list(sm.DAYS),
            "slots_per_day": dict(sm.SLOTS_PER_DAY),
            "groups": dict(sm.GROUPS),
            "rooms": list(sm.ROOMS),
            "teacher_days": {k: set(v) for k, v in sm.TEACHER_DAYS.items()},
            "courses": list(sm.COURSES),
            "pop_size": 100,
            "n_generations": 400,
            "p_mut": 0.08,
            "seed": 42,
        }
    else:
        cfg = prompt_problem_data()

    n_gen = cfg["n_generations"]
    pop_size = cfg["pop_size"]
    milestones = {int(pct * n_gen / 100) for pct in range(0, 101, 10)} | {n_gen}

    def on_progress(gen: int, row: dict) -> None:
        if gen in milestones:
            pct = int(gen / n_gen * 100)
            filled = pct // 5
            bar = "#" * filled + "-" * (20 - filled)
            print(
                f"\r  [{bar}] {pct:3d}% | gen {gen:3d}/{n_gen} | "
                f"valid={row['valid']:3d}/{pop_size} | "
                f"f1={row['f1_min']} f2={row['f2_min']:.2f} f3={row['f3_min']:.2f}",
                end="",
                flush=True,
            )

    print(f"\nRunning Pure NSGA-II (pop={pop_size}, gens={n_gen}, mut={cfg['p_mut']}, seed={cfg['seed']})...")
    t0 = time.time()
    pareto_front, best_idx, _ = sm.solve(
        pop_size=pop_size,
        n_generations=n_gen,
        seed=cfg["seed"],
        p_mut=cfg["p_mut"],
        verbose=False,
        days=cfg["days"],
        slots_per_day=cfg["slots_per_day"],
        groups=cfg["groups"],
        rooms=cfg["rooms"],
        teacher_days=cfg["teacher_days"],
        courses=cfg["courses"],
        progress_callback=on_progress,
    )
    elapsed = time.time() - t0
    print(f"\n\nCompleted in {elapsed:.2f}s | Pareto front size: {len(pareto_front)}")

    for i, (_, sc) in enumerate(pareto_front):
        tag = " <-- ULTIMATE" if i == best_idx else ""
        print(f"  [{i}] f1={sc[0]}  f2={sc[1]:.3f}  f3={sc[2]:.3f}{tag}")

    sessions = sm.build_sessions(courses=cfg["courses"], groups=cfg["groups"])
    best_tt, best_sc = pareto_front[best_idx]
    sm.print_schedule(
        best_tt,
        best_sc,
        sessions,
        days=cfg["days"],
        slots_per_day=cfg["slots_per_day"],
        groups=cfg["groups"],
        rooms=cfg["rooms"],
    )

    csv_path = os.path.join(HERE, "emploi_du_temps_simple.csv")
    sm.export_schedule_csv(
        best_tt,
        sessions,
        csv_path,
        days=cfg["days"],
        slots_per_day=cfg["slots_per_day"],
        rooms=cfg["rooms"],
    )
    print(f"\nSaved timetable CSV to: {csv_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple Terminal NSGA-II Timetabling")
    parser.add_argument("--defaults", action="store_true", help="Run immediately with default settings")
    args = parser.parse_args()
    try:
        run_interactive(use_defaults=args.defaults)
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")


if __name__ == "__main__":
    main()
