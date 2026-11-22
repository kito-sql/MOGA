# -*- coding: utf-8 -*-
"""
operateurs.py – Sélection, croisement, mutation.
La mutation respecte les limites de journée pour l'horaire à créneaux variables.
"""

import numpy as np
import config as C
from evaluation import calculer_occupations


def tournoi_binaire(rang, crowd):
    a, b = C.RNG.integers(0, len(rang), size=2)
    if rang[a] != rang[b]:
        return a if rang[a] < rang[b] else b
    return a if crowd[a] >= crowd[b] else b


def croisement(parent1, parent2):
    enfant1, enfant2 = parent1.copy(), parent2.copy()
    if C.RNG.random() < C.PROBA_CROISEMENT:
        masque = C.RNG.random(C.N_SEANCES) < 0.5
        enfant1[masque], enfant2[masque] = parent2[masque].copy(), parent1[masque].copy()
    return enfant1, enfant2


def seances_en_conflit(ind):
    occ_e, occ_g, occ_s = calculer_occupations(ind)
    en_conflit = np.zeros(C.N_SEANCES, dtype=bool)
    for s in range(C.N_SEANCES):
        debut, salle = ind[s]
        creneaux = np.arange(debut, debut + C.DUREE_S[s])
        en_conflit[s] = (
            (occ_e[C.ENS_S[s], creneaux] > 1).any()
            or (occ_g[np.ix_(C.GROUPES_S[s], creneaux)] > 1).any()
            or (occ_s[salle, creneaux] > 1).any()
            or (C.DISPO[C.ENS_S[s], creneaux] == 0).any()
        )
    return en_conflit


def mutation(ind):
    en_conflit = seances_en_conflit(ind)
    ind = ind.copy()
    for s in range(C.N_SEANCES):
        proba = C.PROBA_MUTATION_CONFLIT if en_conflit[s] else C.PROBA_MUTATION_GENE
        if C.RNG.random() < proba:
            valides = C.STARTS_VALIDES[s]
            if len(valides) == 0:
                continue
            r = C.RNG.random()
            if r < 0.4:
                # Nouveau créneau de départ aléatoire valide
                ind[s, 0] = C.RNG.choice(valides)
            elif r < 0.7:
                # Nouvelle salle
                ind[s, 1] = int(C.RNG.integers(0, C.N_SAL))
            else:
                # Même période dans la journée, autre jour valide
                p_actuelle = C.SLOT_PERIODE[ind[s, 0]]
                # Créneau de début de chaque jour dans la liste plate
                offsets = []
                off = 0
                for n in C.N_PER_JOUR:
                    offsets.append(off)
                    off += n
                # Jours où la période p_actuelle + duree tient entièrement
                candidats = []
                for j in range(C.N_JOURS):
                    if p_actuelle + C.DUREE_S[s] <= C.N_PER_JOUR[j]:
                        t = offsets[j] + p_actuelle
                        if t in valides:
                            candidats.append(t)
                if candidats:
                    ind[s, 0] = int(C.RNG.choice(candidats))
    return ind
