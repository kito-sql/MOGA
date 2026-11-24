# 🎓 MOGA — Multi-Objective Genetic Algorithm for University Timetabling

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![Algorithm](https://img.shields.io/badge/Algorithm-NSGA--II%20(from%20scratch)-green.svg)]()
[![License](https://img.shields.io/badge/License-Academic-orange.svg)]()

Ce projet implémente l'algorithme génétique multiobjectif **NSGA-II** (*Non-dominated Sorting Genetic Algorithm II*, Deb et al., 2002) **entièrement à partir de zéro** (sans DEAP ni pymoo) pour résoudre le problème combinatoire NP-difficile de la planification des emplois du temps universitaires.

Le projet est structuré en **deux versions indépendantes** partageant le même moteur algorithmique optimisé.

---

## 📁 Structure du Dépôt

```
MOGA/
├── README.md                      # Présentation globale du projet (ce fichier)
├── .gitignore
├── docs/
│   ├── rapport_moga_nsga2.pdf     # 📄 Rapport pédagogique complet (PDF 9 pages en français)
│   ├── rapport_moga.py            # Script générateur du rapport PDF
│   ├── front_pareto.png           # Visualisation du front de Pareto (3D et projection 2D)
│   └── evolution_objectifs.png    # Graphiques de convergence sur 400 générations
│
├── web-version/                   # 🌐 Version 1 : Interface Web Interactive (Flask)
│   ├── app.py                     # Serveur Flask avec streaming temps réel SSE
│   ├── requirements.txt           # Dépendances (flask, numpy, pandas, matplotlib)
│   ├── README.md                  # Instructions détaillées de la version Web
│   └── [modules algorithmiques]
│
├── terminal-version/              # 💻 Version 2 : Version Terminal Épurée (CLI)
│   ├── terminal.py                # Interface console interactive avec grilles ASCII
│   ├── requirements.txt           # Dépendances (numpy, pandas, matplotlib)
│   ├── README.md                  # Instructions détaillées de la version Terminal
│   └── [modules algorithmiques]
│
├── simple-web-version/            # ✨ Version Web Simplifiée (Pure NSGA-II, stdlib + Flask)
│   ├── simple_moga.py             # Moteur Pure NSGA-II autonome (sans NumPy/MRV/G-MOGA)
│   ├── app.py                     # Serveur Flask léger + SSE + graphique SVG
│   ├── requirements.txt           # Dépendance unique (flask)
│   └── test_web.py                # Tests d'intégration Flask
│
└── simple-terminal-version/       # ✨ Version Terminal Simplifiée (Pure NSGA-II, stdlib)
    ├── simple_moga.py             # Moteur Pure NSGA-II autonome (sans NumPy/MRV/G-MOGA)
    ├── terminal.py                # Assistant terminal interactif (--defaults disponible)
    └── test_terminal.py           # Tests de la version terminal
```

---

## ⚡ Comparatif des Deux Versions

| Caractéristique | 🌐 Version Web (`web-version`) | 💻 Version Terminal (`terminal-version`) |
| :--- | :--- | :--- |
| **Point d'entrée** | `python app.py` | `python terminal.py` |
| **Interface** | Navigateur web ([http://localhost:5000](http://localhost:5000)) | Console / Terminal classique |
| **Saisie des données** | Formulaire graphique avec ajout dynamique de lignes | Saisie interactive guidée avec valeurs par défaut `[Entrée]` |
| **Suivi d'exécution** | Streaming temps réel SSE avec barre de progression | Barre de progression compacte sur une seule ligne |
| **Visualisation** | Onglets interactifs : graphiques, grilles, front | Tableaux ASCII formatés, métriques et liste des séances |
| **Dépendances** | `flask`, `numpy`, `pandas`, `matplotlib` | `numpy`, `pandas`, `matplotlib` |

Consultez les fichiers [`web-version/README.md`](web-version/README.md) et [`terminal-version/README.md`](terminal-version/README.md) pour les guides de lancement pas à pas de chaque version.

---

## 🧬 Principes Algorithmiques (NSGA-II)

Le problème consiste à affecter chaque cours à un **créneau horaire** et une **salle** en minimisant simultanément trois fonctions objectifs contradictoires :

$$\min_{X} \; [f_1(X), \; f_2(X), \; f_3(X)]$$

### 1. Les Trois Fonctions Objectifs
- **$f_1$ : Conflits d'horaires et contraintes dures (cible = 0)**
  - Pas de salle occupée par deux cours simultanés.
  - Pas d'enseignant assigné à deux cours au même moment.
  - Pas de groupe d'étudiants ayant deux cours simultanés.
  - Respect strict des indisponibilités déclarées par les enseignants.
- **$f_2$ : Confort et équilibre des étudiants**
  - Minimisation des « trous » (heures creuses isolées entre deux cours).
  - Équilibrage de la charge journalière de cours sur la semaine (écart-type minimal).
- **$f_3$ : Utilisation efficace des salles**
  - Minimisation du gaspillage de places pour les salles surdimensionnées.
  - Forte pénalisation (facteur $\times 5$) des salles sous-dimensionnées par rapport à l'effectif.

### 2. Spécificités de l'Implémentation
1. **Dominance Contrainte (Deb et al., 2002)** : Une solution sans conflit ($f_1=0$) domine systématiquement toute solution présentant des conflits, garantissant que la population converge vers des emplois du temps 100 % valides dès la 60ᵉ génération.
2. **Mutation Dirigée** : Les séances impliquées dans un conflit ont une probabilité de mutation élevée (50 %) pour réparer l'emploi du temps, tandis que les séances saines mutent à un taux faible (5 %) pour préserver les blocs stables.
3. **Gestion d'Horaires Variables** : Le moteur s'adapte automatiquement aux semaines universitaires asymétriques (ex: 4 créneaux de 1h30 le Lundi, Mardi, Jeudi, Vendredi avec pause déjeuner ; 3 créneaux le Mercredi et Samedi).

---

## 📈 Résultats et Performance Réelle (Run Loggé)

Sur un problème de référence comportant 3 groupes (80 étudiants), 5 enseignants avec contraintes, 5 salles et 23 séances hebdomadaires (données exactes issues de `historique_generations.csv`) :

| Critère | Population Initiale (Moyenne gén. 0) | Solution Optimale NSGA-II | Évolution Réelle |
| :--- | :---: | :---: | :---: |
| **$f_1$ : Conflits d'horaires** | 29.69 | **0 [Valide]** | **-100% (Faisabilité intégrale à gén. 60)** |
| **$f_2$ : Confort étudiant** | 4.43 | **3.48** | **-21.4% vs moyenne initiale** |
| **$f_3$ : Inadéquation salles** | 13.48 | **3.75** | **-72.2% vs moyenne initiale** |

---

## 📄 Rapport Pédagogique PDF

Un rapport complet en français, structuré pour un public découvrant l'algorithmique avancée, mathématiquement rigoureux et intégrant les figures réelles de convergence et du front de Pareto, est disponible dans le dossier `docs/` :
👉 **[`docs/rapport_moga_nsga2.pdf`](docs/rapport_moga_nsga2.pdf)**

---

## 👥 Auteur et Contexte
Projet universitaire d'optimisation combinatoire et d'algorithmes évolutionnaires multiobjectifs.
