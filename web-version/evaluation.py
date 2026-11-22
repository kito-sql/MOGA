# -*- coding: utf-8 -*-
"""
evaluation.py – Calcul des 3 fonctions objectifs.
Adapté pour un horaire à créneaux variables par jour (N_PER_JOUR).
"""

import numpy as np
import config as C


def calculer_occupations(ind):
    occ_e = np.zeros((C.N_ENS,  C.N_SLOTS), dtype=int)
    occ_g = np.zeros((C.N_GRP,  C.N_SLOTS), dtype=int)
    occ_s = np.zeros((C.N_SAL,  C.N_SLOTS), dtype=int)
    for s in range(C.N_SEANCES):
        debut, salle = ind[s]
        creneaux = np.arange(debut, debut + C.DUREE_S[s])
        occ_e[C.ENS_S[s], creneaux] += 1
        occ_g[np.ix_(C.GROUPES_S[s], creneaux)] += 1
        occ_s[salle, creneaux] += 1
    return occ_e, occ_g, occ_s


def objectif_conflits(occ_e, occ_g, occ_s):
    """f1 : conflits enseignant, groupe, salle + indisponibilités."""
    c_ens  = int(np.maximum(occ_e - 1, 0).sum())
    c_grp  = int(np.maximum(occ_g - 1, 0).sum())
    c_sal  = int(np.maximum(occ_s - 1, 0).sum())
    c_dispo = int((occ_e * (1 - C.DISPO)).sum())
    return c_ens + c_grp + c_sal + c_dispo


def objectif_heures_creuses(occ_g):
    """
    f2 : trous dans les journées + déséquilibre de la charge.
    Gère les jours à nombre variable de créneaux (N_PER_JOUR).
    """
    trous        = 0
    desequilibre = 0.0

    # Offset du 1er créneau de chaque jour dans la liste plate
    offsets = []
    off = 0
    for n in C.N_PER_JOUR:
        offsets.append(off)
        off += n

    for g in range(C.N_GRP):
        charges = []
        for j in range(C.N_JOURS):
            start = offsets[j]
            end   = start + C.N_PER_JOUR[j]
            day_occ = (occ_g[g, start:end] > 0)
            charges.append(int(day_occ.sum()))
            indices = np.where(day_occ)[0]
            if len(indices) > 1:
                trous += int(indices[-1] - indices[0] + 1 - len(indices))
        desequilibre += float(np.std(charges))
    return float(trous + desequilibre)


def objectif_salles(ind):
    """f3 : pénalité d'inadéquation capacité/effectif."""
    total = 0.0
    for s in range(C.N_SEANCES):
        capacite = C.SAL_CAP[ind[s, 1]]
        taille   = C.TAILLE_S[s]
        if capacite >= taille:
            total += (capacite - taille) / capacite
        else:
            total += 5.0 * (taille - capacite) / taille
    return float(total)


def evaluer(ind):
    occ_e, occ_g, occ_s = calculer_occupations(ind)
    return np.array([
        objectif_conflits(occ_e, occ_g, occ_s),
        objectif_heures_creuses(occ_g),
        objectif_salles(ind),
    ])


def evaluer_population(pop):
    return np.array([evaluer(ind) for ind in pop])
