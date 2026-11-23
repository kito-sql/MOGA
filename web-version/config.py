# -*- coding: utf-8 -*-
"""
config.py – ÉTAPE 1 : DONNÉES DU PROBLÈME ET PARAMÈTRES DE L'ALGORITHME

L'horaire universitaire cible :
  Lundi / Mardi / Jeudi / Vendredi : 4 séances
    08:30-10:00 | 10:15-11:45 | 13:00-14:30 | 14:45-16:15
  Mercredi / Samedi              : 3 séances
    08:30-10:00 | 10:15-11:45 | 12:00-13:30

Toutes les données peuvent être rechargées à chaud via configure().
"""

import numpy as np

# ============================================================================
# PARAMÈTRES ALGORITHME
# ============================================================================
SEED               = 42
TAILLE_POPULATION  = 100
N_GENERATIONS      = 400
PROBA_CROISEMENT   = 0.90
PROBA_MUTATION_GENE     = 0.05
PROBA_MUTATION_CONFLIT  = 0.50
DOMINANCE_CONTRAINTE    = True

# Paramètres Heuristiques & G-MOGA (activés pour initialisation hybride MRV et métriques EMO)
INIT_HEURISTIQUE       = True
RATIO_HEURISTIQUE      = 0.5
DOMINANCE_GUIDEE       = False
TRADE_OFF_A23          = 4.0
TRADE_OFF_A32          = 0.2
CALCUL_METRIQUES_EMO   = True

RNG = np.random.default_rng(SEED)

# ============================================================================
# HORAIRE UNIVERSITE
# Chaque jour peut avoir un nombre différent de créneaux.
# CRENEAUX_PAR_JOUR : liste de listes de chaînes "HH:MM-HH:MM"
# ============================================================================
JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]

# Créneau par jour (respecte pause déjeuner 11:45-13:00)
CRENEAUX_PAR_JOUR = {
    "Lundi":    ["08:30-10:00", "10:15-11:45", "13:00-14:30", "14:45-16:15"],
    "Mardi":    ["08:30-10:00", "10:15-11:45", "13:00-14:30", "14:45-16:15"],
    "Mercredi": ["08:30-10:00", "10:15-11:45", "12:00-13:30"],
    "Jeudi":    ["08:30-10:00", "10:15-11:45", "13:00-14:30", "14:45-16:15"],
    "Vendredi": ["08:30-10:00", "10:15-11:45", "13:00-14:30", "14:45-16:15"],
    "Samedi":   ["08:30-10:00", "10:15-11:45", "12:00-13:30"],
}

# ============================================================================
# DONNEES PAR DEFAUT (remplacées par configure() au lancement de l'app)
# ============================================================================
GROUPES    = {"G1": 30, "G2": 35, "G3": 25}
SALLES     = {"S1": 30, "S2": 40, "S3": 60, "S4": 80, "Amphi": 120}
ENSEIGNANTS = ["E1", "E2", "E3", "E4", "E5"]
JOURS_DISPO = {
    "E1": [0, 1, 2, 3],
    "E2": [0, 1, 3, 4],
    "E3": [0, 1, 2],
    "E4": [1, 3],
    "E5": [0, 1, 2, 4],
}
MATIERES = [
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
# VARIABLES DÉRIVÉES — initialisées par _build() et configure()
# ============================================================================
GRP_NOMS   = []
GRP_TAILLES = None
N_GRP      = 0
SAL_NOMS   = []
SAL_CAP    = None
N_SAL      = 0
N_ENS      = 0

# Représentation plate de l'horaire :
#   SLOT_JOUR[t]    = indice du jour du créneau global t
#   SLOT_PERIODE[t] = indice de la période dans la journée
#   N_SLOTS         = nombre total de créneaux
#   N_PER_JOUR[j]   = nombre de créneaux le jour j
SLOT_JOUR    = []
SLOT_PERIODE = []
N_SLOTS      = 0
N_JOURS      = 0
N_PER_JOUR   = []
# Pour compatibilité avec l'ancien code (période max = max des jours pleins)
N_PER        = 0

DISPO  = None
NOM_S  = []
ENS_S  = None
DUREE_S = None
GROUPES_S = []
TAILLE_S   = None
N_SEANCES  = 0
STARTS_VALIDES = []


def _build():
    """Reconstruit toutes les variables dérivées à partir des données globales."""
    global GRP_NOMS, GRP_TAILLES, N_GRP
    global SAL_NOMS, SAL_CAP, N_SAL
    global N_ENS
    global SLOT_JOUR, SLOT_PERIODE, N_SLOTS, N_JOURS, N_PER_JOUR, N_PER
    global DISPO
    global NOM_S, ENS_S, DUREE_S, GROUPES_S, TAILLE_S, N_SEANCES, STARTS_VALIDES

    # Groupes
    GRP_NOMS    = list(GROUPES)
    GRP_TAILLES = np.array(list(GROUPES.values()))
    N_GRP       = len(GRP_NOMS)

    # Salles
    SAL_NOMS = list(SALLES)
    SAL_CAP  = np.array(list(SALLES.values()))
    N_SAL    = len(SAL_NOMS)

    # Enseignants
    N_ENS = len(ENSEIGNANTS)
    N_JOURS = len(JOURS)

    # Horaire variable : on bâtit la liste plate des créneaux
    slot_jour_list = []
    slot_periode_list = []
    n_per_jour = []
    for j, jour in enumerate(JOURS):
        periodes = CRENEAUX_PAR_JOUR.get(jour, [])
        n_per_jour.append(len(periodes))
        for p in range(len(periodes)):
            slot_jour_list.append(j)
            slot_periode_list.append(p)
    SLOT_JOUR    = slot_jour_list
    SLOT_PERIODE = slot_periode_list
    N_SLOTS      = len(slot_jour_list)
    N_PER_JOUR   = n_per_jour
    N_PER        = max(n_per_jour) if n_per_jour else 0

    # Décalage (offset) du 1er créneau de chaque jour dans la liste plate
    offsets = []
    off = 0
    for n in n_per_jour:
        offsets.append(off)
        off += n

    # Disponibilités : DISPO[e, t] = 1 si l'enseignant e est disponible au créneau global t
    DISPO = np.zeros((N_ENS, N_SLOTS), dtype=int)
    for e, nom in enumerate(ENSEIGNANTS):
        jours_ok = JOURS_DISPO.get(nom, list(range(N_JOURS)))
        for j in jours_ok:
            if j < N_JOURS:
                start = offsets[j]
                end   = offsets[j] + n_per_jour[j]
                DISPO[e, start:end] = 1

    # Séances
    _nom_s, _ens_s, _duree_s, _grp_s, _tail_s = [], [], [], [], []
    for nom, ens, duree, mode in MATIERES:
        ens_idx = ENSEIGNANTS.index(ens) if ens in ENSEIGNANTS else 0
        if mode == "ensemble":
            _nom_s.append(nom)
            _ens_s.append(ens_idx)
            _duree_s.append(duree)
            _grp_s.append(list(range(N_GRP)))
            _tail_s.append(int(GRP_TAILLES.sum()))
        else:
            for g in range(N_GRP):
                _nom_s.append(nom)
                _ens_s.append(ens_idx)
                _duree_s.append(duree)
                _grp_s.append([g])
                _tail_s.append(int(GRP_TAILLES[g]))

    NOM_S     = _nom_s
    ENS_S     = np.array(_ens_s)
    DUREE_S   = np.array(_duree_s)
    GROUPES_S = _grp_s
    TAILLE_S  = np.array(_tail_s)
    N_SEANCES = len(_nom_s)

    # Créneaux de départ valides pour chaque séance :
    # une séance de durée d ne peut pas commencer sur un créneau tel que
    # les d créneaux consécutifs débordent sur le lendemain.
    starts = []
    for s in range(N_SEANCES):
        d = int(DUREE_S[s])
        valides = []
        for t in range(N_SLOTS):
            j = SLOT_JOUR[t]
            p = SLOT_PERIODE[t]
            # Les d créneaux t, t+1, … t+d-1 doivent tous appartenir au même jour
            if p + d <= n_per_jour[j]:
                valides.append(t)
        starts.append(np.array(valides))
    STARTS_VALIDES = starts


def configure(groupes=None, salles=None, enseignants=None, jours_dispo=None,
              matieres=None, jours=None, creneaux_par_jour=None,
              taille_pop=None, n_gen=None, seed=None,
              dominance_contrainte=None,
              init_heuristique=None, ratio_heuristique=None,
              dominance_guidee=None, trade_off_a23=None, trade_off_a32=None,
              calcul_metriques_emo=None):
    """
    Met à jour les données globales et reconstruit toutes les variables dérivées.
    Appelez cette fonction depuis l'interface web avant de lancer NSGA-II.
    """
    global GROUPES, SALLES, ENSEIGNANTS, JOURS_DISPO, MATIERES
    global JOURS, CRENEAUX_PAR_JOUR
    global TAILLE_POPULATION, N_GENERATIONS, SEED, RNG, DOMINANCE_CONTRAINTE
    global INIT_HEURISTIQUE, RATIO_HEURISTIQUE, DOMINANCE_GUIDEE
    global TRADE_OFF_A23, TRADE_OFF_A32, CALCUL_METRIQUES_EMO

    if groupes          is not None: GROUPES          = groupes
    if salles           is not None: SALLES           = salles
    if enseignants      is not None: ENSEIGNANTS      = enseignants
    if jours_dispo      is not None: JOURS_DISPO      = jours_dispo
    if matieres         is not None: MATIERES         = matieres
    if jours            is not None: JOURS            = jours
    if creneaux_par_jour is not None: CRENEAUX_PAR_JOUR = creneaux_par_jour
    if taille_pop       is not None: TAILLE_POPULATION = taille_pop
    if n_gen            is not None: N_GENERATIONS    = n_gen
    if seed             is not None:
        SEED = seed
        RNG  = np.random.default_rng(SEED)
    if dominance_contrainte is not None: DOMINANCE_CONTRAINTE = dominance_contrainte
    if init_heuristique   is not None: INIT_HEURISTIQUE   = init_heuristique
    if ratio_heuristique  is not None: RATIO_HEURISTIQUE  = ratio_heuristique
    if dominance_guidee   is not None: DOMINANCE_GUIDEE   = dominance_guidee
    if trade_off_a23      is not None: TRADE_OFF_A23      = trade_off_a23
    if trade_off_a32      is not None: TRADE_OFF_A32      = trade_off_a32
    if calcul_metriques_emo is not None: CALCUL_METRIQUES_EMO = calcul_metriques_emo

    _build()


# Initialisation au chargement du module
_build()
