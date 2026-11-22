# -*- coding: utf-8 -*-
"""
nsga2.py – Boucle principale NSGA-II.
Communique la progression via un callback optionnel (pour le streaming SSE).
"""

import numpy as np
import pandas as pd
import config as C
from population import population_initiale, population_initiale_hybride
from evaluation import evaluer_population
from pareto import classement_non_domine, crowding_distance, crowding_population
from operateurs import tournoi_binaire, croisement, mutation
from resultats import calculer_espacement_schott, calculer_hypervolume


def creer_enfants(pop, F):
    fronts, rang = classement_non_domine(F)
    crowd = crowding_population(F, fronts)
    enfants = []
    while len(enfants) < len(pop):
        p1 = pop[tournoi_binaire(rang, crowd)]
        p2 = pop[tournoi_binaire(rang, crowd)]
        e1, e2 = croisement(p1, p2)
        enfants += [mutation(e1), mutation(e2)]
    return enfants[:len(pop)]


def supprimer_doublons(pop, F, N):
    vus, uniques, doublons = set(), [], []
    for i, ind in enumerate(pop):
        cle = ind.tobytes()
        if cle in vus:
            doublons.append(i)
        else:
            vus.add(cle)
            uniques.append(i)
    if len(uniques) < N:
        uniques += doublons[:N - len(uniques)]
    return [pop[i] for i in uniques], F[uniques]


def selection_environnementale(pop_totale, F_totale, N):
    pop_totale, F_totale = supprimer_doublons(pop_totale, F_totale, N)
    fronts, _ = classement_non_domine(F_totale)
    gardes = []
    for front in fronts:
        if len(gardes) + len(front) <= N:
            gardes += front
        else:
            crowd = crowding_distance(F_totale, front)
            ordre = np.argsort(-crowd)
            reste = N - len(gardes)
            gardes += [front[k] for k in ordre[:reste]]
            break
    return [pop_totale[i] for i in gardes], F_totale[gardes]


def nsga2(taille_pop=None, n_generations=None, pop_init=None, verbose=True,
          progress_callback=None):
    """
    Algorithme NSGA-II complet.
    progress_callback(gen, hist_row) est appelé à chaque génération
    (utile pour le streaming SSE vers le navigateur).
    """
    if taille_pop    is None: taille_pop    = C.TAILLE_POPULATION
    if n_generations is None: n_generations = C.N_GENERATIONS

    if pop_init is not None:
        pop = pop_init
    elif getattr(C, "INIT_HEURISTIQUE", True):
        ratio = getattr(C, "RATIO_HEURISTIQUE", 0.5)
        pop = population_initiale_hybride(taille_pop, ratio_heuristique=ratio)
    else:
        pop = population_initiale(taille_pop)

    F   = evaluer_population(pop)
    historique = []

    def snapshot(gen):
        fronts, _ = classement_non_domine(F)
        faisables = F[:, 0] == 0
        row = {
            "génération":           gen,
            "taille front 0":       len(fronts[0]),
            "solutions sans conflit": int(faisables.sum()),
            "f1 min":  float(F[:, 0].min()),
            "f1 moyen": float(F[:, 0].mean()),
            "f2 min":  float(F[:, 1].min()),
            "f2 moyen": float(F[:, 1].mean()),
            "f3 min":  float(F[:, 2].min()),
            "f3 moyen": float(F[:, 2].mean()),
            "f2 min (sans conflit)": float(F[faisables, 1].min()) if faisables.any() else float("nan"),
            "f3 min (sans conflit)": float(F[faisables, 2].min()) if faisables.any() else float("nan"),
        }
        if getattr(C, "CALCUL_METRIQUES_EMO", True):
            front0_F = F[fronts[0]]
            valides = front0_F[front0_F[:, 0] == 0]
            if len(valides) > 0:
                row["espacement_schott"] = calculer_espacement_schott(valides[:, 1:3])
                row["hypervolume"] = calculer_hypervolume(valides[:, 1:3], ref_point=(40.0, 30.0))
            else:
                row["espacement_schott"] = calculer_espacement_schott(front0_F)
                row["hypervolume"] = calculer_hypervolume(front0_F, ref_point=(50.0, 40.0, 30.0))

        historique.append(row)
        if progress_callback:
            progress_callback(gen, row)
        return row

    snapshot(0)
    for gen in range(1, n_generations + 1):
        enfants   = creer_enfants(pop, F)
        F_enfants = evaluer_population(enfants)
        pop_tot   = pop + enfants
        F_tot     = np.vstack([F, F_enfants])
        pop, F    = selection_environnementale(pop_tot, F_tot, taille_pop)
        row = snapshot(gen)
        if verbose and (gen % 10 == 0 or gen == 1):
            extra = ""
            if "hypervolume" in row and "espacement_schott" in row:
                extra = f" | HV={row['hypervolume']:.1f} S={row['espacement_schott']:.2f}"
            print(f"  gén {gen:3d} | front 0: {row['taille front 0']:3d} | "
                  f"sans conflit: {row['solutions sans conflit']:3d}/{taille_pop} | "
                  f"f1={row['f1 min']:.0f} f2={row['f2 min']:.2f} f3={row['f3 min']:.2f}{extra}")

    return pop, F, pd.DataFrame(historique)
