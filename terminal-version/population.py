# -*- coding: utf-8 -*-
"""
population.py – Représentation et génération de la population initiale.
Intègre la construction heuristique / gloutonne (MRV) et l'initialisation hybride.
"""

import numpy as np
import config as C


def individu_aleatoire():
    """Génère un individu complètement aléatoire."""
    ind = np.zeros((C.N_SEANCES, 2), dtype=int)
    for s in range(C.N_SEANCES):
        valides = C.STARTS_VALIDES[s]
        ind[s, 0] = int(C.RNG.choice(valides))
        ind[s, 1] = int(C.RNG.integers(0, C.N_SAL))
    return ind


def individu_heuristique_glouton(max_retries=3):
    """
    Constructeur heuristique glouton basé sur le principe MRV (Minimum Remaining Values) :
    1. Classement des séances les plus contraintes en priorité :
       - Séances en promo complète (CM / tous groupes) et grande taille
       - Séances longues (durée = 2)
       - Enseignants à disponibilité restreinte (peu de créneaux compatibles)
    2. Placement glouton pour chaque séance sur le meilleur créneau et la meilleure salle :
       - Priorité absolue au respect des contraintes dures (0 conflit enseignant, groupe, salle, dispo)
       - Minimisation du gaspillage de capacité de salle (f3)
       - Minimisation des trous et équilibrage des journées pour les groupes (f2)
    3. Diversité stochastique : tirage aléatoire parmi les meilleurs placements équivalents.
    """
    for retry in range(max_retries):
        # 1. Ordonnancement MRV des séances
        def mrv_score(s):
            is_cm = 0 if len(C.GROUPES_S[s]) > 1 else 1
            d = C.DUREE_S[s]
            ens = C.ENS_S[s]
            # Nombre de créneaux valides où l'enseignant est totalement disponible
            n_dispo = sum(np.all(C.DISPO[ens, t:t + d] == 1) for t in C.STARTS_VALIDES[s])
            taille = C.TAILLE_S[s]
            # Légère perturbation aléatoire pour diversifier l'ordre entre individus
            jitter = float(C.RNG.uniform(0, 0.2))
            return (is_cm, -d, n_dispo + jitter, -taille, s)

        session_order = sorted(range(C.N_SEANCES), key=mrv_score)

        ind = np.zeros((C.N_SEANCES, 2), dtype=int)
        occ_e = np.zeros((C.N_ENS, C.N_SLOTS), dtype=int)
        occ_g = np.zeros((C.N_GRP, C.N_SLOTS), dtype=int)
        occ_s = np.zeros((C.N_SAL, C.N_SLOTS), dtype=int)

        offsets = []
        off = 0
        for n in C.N_PER_JOUR:
            offsets.append(off)
            off += n

        total_conflits = 0

        for s in session_order:
            ens = C.ENS_S[s]
            d = C.DUREE_S[s]
            grps = C.GROUPES_S[s]
            taille = C.TAILLE_S[s]
            valides = C.STARTS_VALIDES[s]

            candidats = []
            for t in valides:
                creneaux = np.arange(t, t + d)
                c_dispo = int((1 - C.DISPO[ens, creneaux]).sum())
                c_ens   = int(occ_e[ens, creneaux].sum())
                c_grp   = int(occ_g[np.ix_(grps, creneaux)].sum())

                # Évaluation locale f2 (trous & équilibre)
                j = C.SLOT_JOUR[t]
                p = C.SLOT_PERIODE[t]
                start_j = offsets[j]
                end_j   = start_j + C.N_PER_JOUR[j]

                pen_soft = 0.0
                for g in grps:
                    day_occ = occ_g[g, start_j:end_j] > 0
                    n_day = int(day_occ.sum())
                    pen_soft += n_day * 0.5
                    if n_day > 0:
                        occ_idx = np.where(day_occ)[0]
                        min_dist = min(abs(p - (k + 1)) if p > k else abs(k - (p + d)) for k in occ_idx)
                        pen_soft += min_dist * 1.0

                # Évaluation salles (f3 + collision)
                for r in range(C.N_SAL):
                    c_sal = int(occ_s[r, creneaux].sum())
                    conflits = c_dispo + c_ens + c_grp + c_sal

                    cap = C.SAL_CAP[r]
                    if cap >= taille:
                        pen_salle = (cap - taille) / cap
                    else:
                        pen_salle = 5.0 * (taille - cap) / taille

                    score = conflits * 10000.0 + pen_salle * 2.0 + pen_soft
                    candidats.append((score, conflits, t, r))

            # Choix glouton parmi les meilleures options
            zero_conf = [c for c in candidats if c[1] == 0]
            pool = zero_conf if zero_conf else candidats
            pool.sort(key=lambda x: x[0])
            min_score = pool[0][0]
            top = [c for c in pool if c[0] <= min_score + 0.5]
            chosen = top[int(C.RNG.integers(0, len(top)))]
            _, conf_choisi, best_t, best_r = chosen

            total_conflits += conf_choisi
            ind[s, 0] = best_t
            ind[s, 1] = best_r

            creneaux = np.arange(best_t, best_t + d)
            occ_e[ens, creneaux] += 1
            occ_g[np.ix_(grps, creneaux)] += 1
            occ_s[best_r, creneaux] += 1

        if total_conflits == 0 or retry == max_retries - 1:
            return ind

    return ind


def population_initiale_hybride(taille, ratio_heuristique=0.5):
    """
    Génère une population initiale hybride combinant des individus gloutons
    et des individus aléatoires.
    """
    n_heur = int(round(taille * ratio_heuristique))
    n_alea = max(0, taille - n_heur)
    pop = [individu_heuristique_glouton() for _ in range(n_heur)]
    pop += [individu_aleatoire() for _ in range(n_alea)]
    return pop


def population_initiale(taille):
    """
    Point d'entrée standard. Utilise l'initialisation hybride si INIT_HEURISTIQUE est activé.
    """
    if getattr(C, "INIT_HEURISTIQUE", True):
        ratio = getattr(C, "RATIO_HEURISTIQUE", 0.5)
        return population_initiale_hybride(taille, ratio_heuristique=ratio)
    return [individu_aleatoire() for _ in range(taille)]
