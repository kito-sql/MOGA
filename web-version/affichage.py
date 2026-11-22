# -*- coding: utf-8 -*-
"""
affichage.py – Tableaux console + helpers utilisés par l'interface web.
Adapté pour l'horaire variable (N_PER_JOUR).
"""

import pandas as pd
import config as C

pd.set_option("display.width", 260)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_colwidth", 50)


def titre(texte):
    print("\n" + "=" * 78)
    print(texte)
    print("=" * 78)


def afficher_donnees():
    print("Groupes  :", C.GROUPES)
    print("Salles   :", C.SALLES)
    total = sum(C.N_PER_JOUR)
    print(f"Créneaux : {C.N_JOURS} jours, {total} créneaux au total")
    for j, jour in enumerate(C.JOURS):
        periodes = C.CRENEAUX_PAR_JOUR.get(jour, [])
        print(f"  {jour:12s}: {periodes}")
    dispo = pd.DataFrame(
        {e: [", ".join(C.JOURS[j][:3] for j in C.JOURS_DISPO.get(e, []))]
         for e in C.ENSEIGNANTS},
        index=["Jours disponibles"]
    ).T
    print("\nDisponibilités :\n", dispo)
    mat = pd.DataFrame(C.MATIERES, columns=["Matière", "Enseignant", "Durée", "Public"])
    print("\nMatières :\n", mat.to_string(index=False))
    print(f"\n=> {C.N_SEANCES} séances à placer")


def afficher_population_initiale(pop0, F0):
    tab = pd.DataFrame(F0, columns=["f1 conflits", "f2 heures creuses", "f3 salles"])
    tab.index.name = "individu"
    print("Chromosome individu 0 :")
    print(pop0[0])
    print("\nObjectifs des 8 premiers individus :\n", tab.head(8).round(2))
    print("\nStatistiques initiales :\n", tab.describe().loc[["mean","min","max"]].round(2))
    print(f"\nSans conflit dans pop initiale : {(F0[:, 0]==0).sum()}/{len(F0)}")


def afficher_historique(hist):
    n = len(hist)
    lignes = sorted({i for i in [0,1,2,5,10,25,50,100,150,200,n-1] if i < n})
    cols = ["génération","taille front 0","solutions sans conflit","f1 min","f2 min","f3 min"]
    print(hist.iloc[lignes][cols].round(2).to_string(index=False))


def _get_slot_label(t):
    """Retourne la chaîne de créneau (ex. '08:30-10:00') pour le créneau global t."""
    j = C.SLOT_JOUR[t]
    p = C.SLOT_PERIODE[t]
    jour = C.JOURS[j]
    periodes = C.CRENEAUX_PAR_JOUR.get(jour, [])
    if p < len(periodes):
        return periodes[p]
    return f"slot{t}"


def tableau_groupe(ind, g):
    """Grille Pandas (période × jour) pour le groupe g."""
    # Collect all unique slot labels (row labels) in time order
    all_labels = []
    for j, jour in enumerate(C.JOURS):
        for label in C.CRENEAUX_PAR_JOUR.get(jour, []):
            if label not in all_labels:
                all_labels.append(label)

    grille = pd.DataFrame("", index=all_labels, columns=C.JOURS)

    for s in range(C.N_SEANCES):
        if g not in C.GROUPES_S[s]:
            continue
        debut, salle = ind[s]
        for dt in range(C.DUREE_S[s]):
            t = debut + dt
            label = _get_slot_label(t)
            j     = C.SLOT_JOUR[t]
            texte = f"{C.NOM_S[s]} ({C.ENSEIGNANTS[C.ENS_S[s]]}, {C.SAL_NOMS[salle]})"
            ancien = grille.iat[grille.index.get_loc(label), j]
            grille.iat[grille.index.get_loc(label), j] = (
                texte if ancien == "" else ancien + " / " + texte
            )
    return grille


def afficher_emploi_du_temps(ind, titre_texte):
    print(f"\n{'='*20} {titre_texte} {'='*20}")
    for g in range(C.N_GRP):
        print(f"\n--- Groupe {C.GRP_NOMS[g]} ({C.GRP_TAILLES[g]} étudiants) ---")
        print(tableau_groupe(ind, g).to_string())


def liste_seances(ind):
    lignes = []
    for s in range(C.N_SEANCES):
        debut, salle = ind[s]
        j = C.SLOT_JOUR[debut]
        p = C.SLOT_PERIODE[debut]
        periodes = C.CRENEAUX_PAR_JOUR.get(C.JOURS[j], [])
        debut_str = periodes[p][:5] if p < len(periodes) else "?"
        lignes.append({
            "Matière":    C.NOM_S[s],
            "Groupes":    "+".join(C.GRP_NOMS[gi] for gi in C.GROUPES_S[s]),
            "Enseignant": C.ENSEIGNANTS[C.ENS_S[s]],
            "Jour":       C.JOURS[j],
            "Début":      debut_str,
            "Durée":      C.DUREE_S[s],
            "Salle":      C.SAL_NOMS[salle],
        })
    return pd.DataFrame(lignes)
