# -*- coding: utf-8 -*-
"""
terminal.py – Version terminal interactive du projet MOGA Timetabling.

Lancer avec :  python terminal.py

Interaction minimale : saisie guidée des données, puis affichage propre
des résultats (emplois du temps + métriques clés) directement dans le terminal.
"""

import sys
import os

# ── Chemin vers les modules du projet ────────────────────────────────────────
DOSSIER = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DOSSIER)

import matplotlib
matplotlib.use("Agg")

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS D'AFFICHAGE
# ─────────────────────────────────────────────────────────────────────────────

WIDTH = 72

def hr(char="─"):
    print(char * WIDTH)

def banner(text, char="═"):
    print(char * WIDTH)
    print(f"  {text}")
    print(char * WIDTH)

def section(text):
    print()
    print("┌" + "─" * (WIDTH - 2) + "┐")
    print(f"│  {text:<{WIDTH-4}}│")
    print("└" + "─" * (WIDTH - 2) + "┘")

def ask(prompt, default=None, cast=str, validate=None):
    """Saisie avec valeur par défaut et validation."""
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"  {prompt}{suffix} : ").strip()
        if raw == "" and default is not None:
            raw = str(default)
        try:
            val = cast(raw)
            if validate and not validate(val):
                raise ValueError()
            return val
        except (ValueError, TypeError):
            print(f"  ✗ Valeur invalide. Réessayez.")

def ask_list(prompt, default=""):
    """Saisie d'une liste séparée par virgules."""
    raw = input(f"  {prompt} [{default}] : ").strip()
    return raw if raw else default


# ─────────────────────────────────────────────────────────────────────────────
# SAISIE DES DONNÉES
# ─────────────────────────────────────────────────────────────────────────────

def saisir_donnees():
    banner("MOGA TIMETABLING  –  Saisie des données")

    # ── Jours ─────────────────────────────────────────────────────────────────
    section("1 / 5  Jours de cours")
    print("  Jours disponibles : Lundi  Mardi  Mercredi  Jeudi  Vendredi  Samedi")
    print("  Format : noms séparés par virgule  (Mercredi et Samedi = 3 séances)")
    jours_str = ask_list(
        "Jours actifs",
        default="Lundi,Mardi,Mercredi,Jeudi,Vendredi,Samedi"
    )
    jours = [j.strip() for j in jours_str.split(",") if j.strip()]

    # ── Groupes ───────────────────────────────────────────────────────────────
    section("2 / 5  Groupes d'étudiants")
    n_grp = ask("Nombre de groupes", default=3, cast=int, validate=lambda x: x >= 1)
    groupes = {}
    for i in range(n_grp):
        nom = ask(f"  Nom du groupe {i+1}", default=f"G{i+1}")
        eff = ask(f"  Effectif de {nom}", default=30, cast=int, validate=lambda x: x >= 1)
        groupes[nom] = eff

    # ── Salles ────────────────────────────────────────────────────────────────
    section("3 / 5  Salles")
    n_sal = ask("Nombre de salles", default=5, cast=int, validate=lambda x: x >= 1)
    salles = {}
    for i in range(n_sal):
        nom = ask(f"  Nom de la salle {i+1}", default=f"S{i+1}")
        cap = ask(f"  Capacité de {nom}", default=40, cast=int, validate=lambda x: x >= 1)
        salles[nom] = cap

    # ── Enseignants ───────────────────────────────────────────────────────────
    section("4 / 5  Enseignants")
    n_ens = ask("Nombre d'enseignants", default=5, cast=int, validate=lambda x: x >= 1)
    enseignants  = []
    jours_dispo  = {}
    print(f"  Jours actifs numérotés : {', '.join(f'{i}={j[:3]}' for i,j in enumerate(jours))}")
    for i in range(n_ens):
        nom  = ask(f"  Nom enseignant {i+1}", default=f"E{i+1}")
        dstr = ask_list(f"  Jours disponibles de {nom} (indices 0-{len(jours)-1}, séparés par virgule)",
                        default=",".join(str(k) for k in range(len(jours))))
        try:
            idx = [int(x.strip()) for x in dstr.split(",") if x.strip()]
            idx = [x for x in idx if 0 <= x < len(jours)]
        except Exception:
            idx = list(range(len(jours)))
        enseignants.append(nom)
        jours_dispo[nom] = idx

    # ── Matières ──────────────────────────────────────────────────────────────
    section("5 / 5  Matières")
    print("  Durée en créneaux (1 créneau = 1h30). Mode : c=CM (tout le monde), t=TD/TP (par groupe).")
    n_mat = ask("Nombre de matières", default=9, cast=int, validate=lambda x: x >= 1)
    matieres = []
    for i in range(n_mat):
        print(f"\n  — Matière {i+1} —")
        nom  = ask("    Nom",             default=f"Matière{i+1}")
        ens  = ask("    Enseignant",       default=enseignants[i % len(enseignants)])
        dur  = ask("    Durée (créneaux)", default=1, cast=int, validate=lambda x: 1 <= x <= 4)
        mode_str = ask("    Mode (c=CM, t=TD)", default="t")
        mode = "ensemble" if mode_str.strip().lower().startswith("c") else "séparé"
        matieres.append((nom, ens, dur, mode))

    # ── Paramètres NSGA-II ────────────────────────────────────────────────────
    section("Paramètres de l'algorithme NSGA-II")
    pop_size = ask("Taille de la population", default=100, cast=int, validate=lambda x: x >= 10)
    n_gen    = ask("Nombre de générations",   default=400, cast=int, validate=lambda x: x >= 1)
    seed     = ask("Graine aléatoire (seed)", default=42,  cast=int)

    return dict(
        jours=jours, groupes=groupes, salles=salles,
        enseignants=enseignants, jours_dispo=jours_dispo, matieres=matieres,
        pop_size=pop_size, n_gen=n_gen, seed=seed,
    )


# ─────────────────────────────────────────────────────────────────────────────
# AFFICHAGE PROPRE DE L'EMPLOI DU TEMPS
# ─────────────────────────────────────────────────────────────────────────────

def afficher_grille(grille, groupe_nom, effectif):
    import config as C
    jours = C.JOURS

    # Largeur de colonne
    COL = 22
    SLOT_COL = 13

    print(f"\n  Groupe {groupe_nom}  ({effectif} étudiants)")
    print("  " + "─" * (SLOT_COL + COL * len(jours) + len(jours) + 1))

    # Header
    header = f"  {'Créneau':<{SLOT_COL}}" + "│"
    for j in jours:
        header += f"{j:^{COL}}│"
    print(header)
    print("  " + "─" * (SLOT_COL + COL * len(jours) + len(jours) + 1))

    # Rows
    all_slots = []
    for jour in jours:
        for lbl in C.CRENEAUX_PAR_JOUR.get(jour, []):
            if lbl not in all_slots:
                all_slots.append(lbl)

    for slot in all_slots:
        row = f"  {slot:<{SLOT_COL}}│"
        for jour in jours:
            cell = str(grille.loc[slot, jour]) if slot in grille.index and jour in grille.columns else ""
            # Flag conflict
            if "/" in cell:
                cell = "⚠ " + cell[:COL - 4] + ".."
            elif cell == "":
                cell = "·"
            else:
                cell = cell[:COL - 1]
            row += f"{cell:<{COL}}│"
        print(row)

    print("  " + "─" * (SLOT_COL + COL * len(jours) + len(jours) + 1))


def afficher_resultats(solutions, k_best, F0, hist):
    import config as C
    from affichage import tableau_groupe

    meilleur, f_m = solutions[k_best]

    banner("RÉSULTATS DE L'OPTIMISATION", "═")

    # ── Métriques ──────────────────────────────────────────────────────────
    section("Métriques clés du meilleur compromis")
    f1_init_moy = F0[:, 0].mean()
    f2_init_moy = F0[:, 1].mean()
    f3_init_moy = F0[:, 2].mean()

    def pct(avant, apres):
        return f"{(avant - apres)/avant*100:+.1f}%" if avant > 0 else "–"

    print(f"\n  {'Objectif':<30} {'Initial (moy)':<16} {'Optimisé':<14} {'Gain'}")
    print(f"  {'─'*30} {'─'*15} {'─'*13} {'─'*10}")
    print(f"  {'f1  Conflits (cible : 0)':<30} {f1_init_moy:<16.1f} {f_m[0]:<14.0f} {pct(f1_init_moy, f_m[0])}")
    print(f"  {'f2  Heures creuses':<30} {f2_init_moy:<16.2f} {f_m[1]:<14.2f} {pct(f2_init_moy, f_m[1])}")
    print(f"  {'f3  Adéquation salles':<30} {f3_init_moy:<16.2f} {f_m[2]:<14.2f} {pct(f3_init_moy, f_m[2])}")

    # Validité
    n_valid = sum(1 for _, f in solutions if f[0] == 0)
    print(f"\n  Solutions non dominées : {len(solutions)}  |  Sans conflit : {n_valid}")

    # ── Convergence résumé ─────────────────────────────────────────────────
    section("Convergence (extrait)")
    gen_col = hist["génération"]
    rows = [0, 10, 25, 50, 100, 200, len(hist) - 1]
    rows = sorted({r for r in rows if r < len(hist)})
    print(f"\n  {'Gén':>5}  {'f1 min':>8}  {'f2 min':>9}  {'f3 min':>9}  {'Sans conflit':>14}")
    print(f"  {'─'*5}  {'─'*8}  {'─'*9}  {'─'*9}  {'─'*14}")
    for r in rows:
        h = hist.iloc[r]
        print(f"  {int(h['génération']):>5}  {h['f1 min']:>8.0f}  {h['f2 min']:>9.2f}"
              f"  {h['f3 min']:>9.2f}  {int(h['solutions sans conflit']):>8}/{C.TAILLE_POPULATION}")

    # ── Emplois du temps ───────────────────────────────────────────────────
    section("Emplois du temps optimisés")
    for g in range(C.N_GRP):
        grille = tableau_groupe(meilleur, g)
        afficher_grille(grille, C.GRP_NOMS[g], C.GRP_TAILLES[g])

    # ── Liste des séances ──────────────────────────────────────────────────
    section("Récapitulatif des séances")
    from affichage import liste_seances
    df = liste_seances(meilleur)
    # Print clean table
    cols = ["Matière", "Groupes", "Enseignant", "Jour", "Début", "Durée", "Salle"]
    widths = [max(len(c), df[c].astype(str).str.len().max()) for c in cols]
    header = "  " + "  ".join(f"{c:<{widths[i]}}" for i, c in enumerate(cols))
    print("\n" + header)
    print("  " + "  ".join("─" * w for w in widths))
    for _, row in df.iterrows():
        print("  " + "  ".join(f"{str(row[c]):<{widths[i]}}" for i, c in enumerate(cols)))

    # ── Fichiers générés ───────────────────────────────────────────────────
    print()
    hr()
    print("  Fichiers générés :")
    for f in ["front_pareto.png", "evolution_objectifs.png",
              "historique_generations.csv", "solutions_pareto.csv", "emploi_du_temps_final.csv"]:
        print(f"    ✓  {f}")
    hr()


# ─────────────────────────────────────────────────────────────────────────────
# POINT D'ENTRÉE PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────

def main():
    try:
        data = saisir_donnees()
    except (KeyboardInterrupt, EOFError):
        print("\n\n  Annulé.")
        return

    # ── Configure le moteur ──────────────────────────────────────────────────
    import config as C
    C.configure(
        groupes=data["groupes"],
        salles=data["salles"],
        enseignants=data["enseignants"],
        jours_dispo=data["jours_dispo"],
        matieres=data["matieres"],
        jours=data["jours"],
        taille_pop=data["pop_size"],
        n_gen=data["n_gen"],
        seed=data["seed"],
    )

    from population import population_initiale
    from evaluation import evaluer_population
    from nsga2 import nsga2
    from resultats import (extraire_front, meilleur_compromis,
                           construire_tableau_front, exporter_resultats)
    from visualisation import tracer_front, tracer_evolution

    # ── Lancer l'optimisation ────────────────────────────────────────────────
    print()
    banner(f"Optimisation NSGA-II  —  {data['pop_size']} individus  ×  {data['n_gen']} générations")

    pop0 = population_initiale(data["pop_size"])
    F0   = evaluer_population(pop0)

    # Barre de progression minimaliste
    n_gen = data["n_gen"]
    milestones = set()
    for pct in range(0, 101, 10):
        milestones.add(int(pct * n_gen / 100))

    def cb(gen, row):
        if gen in milestones or gen == n_gen:
            pct  = int(gen / n_gen * 100)
            done = int(pct / 5)
            bar  = "█" * done + "░" * (20 - done)
            print(f"\r  [{bar}] {pct:3d}%  gén {gen:4d}/{n_gen}"
                  f"  f1={row['f1 min']:.0f}  f2={row['f2 min']:.2f}  f3={row['f3 min']:.2f}"
                  f"  ✓{row['solutions sans conflit']}", end="", flush=True)

    pop, F, hist = nsga2(
        pop_init=[p.copy() for p in pop0],
        verbose=False,
        progress_callback=cb,
    )
    print()  # newline after progress bar

    # ── Extraire + afficher ──────────────────────────────────────────────────
    solutions = extraire_front(pop, F)
    k_best    = meilleur_compromis(solutions)
    front_df  = construire_tableau_front(solutions, k_best)
    meilleur, f_m = solutions[k_best]

    exporter_resultats(hist, front_df, meilleur)
    tracer_front(F0, solutions, k_best)
    tracer_evolution(hist)

    afficher_resultats(solutions, k_best, F0, hist)


if __name__ == "__main__":
    main()
