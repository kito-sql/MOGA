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
└── terminal-version/              # 💻 Version 2 : Version Terminal Épurée (CLI)
    ├── terminal.py                # Interface console interactive avec grilles ASCII
    ├── requirements.txt           # Dépendances (numpy, pandas, matplotlib)
    ├── README.md                  # Instructions détaillées de la version Terminal
    └── [modules algorithmiques]
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
1. **Dominance Contrainte (Deb et al., 2002)** : Une solution sans conflit ($f_1=0$) domine systématiquement toute solution présentant des conflits, garantissant que la population converge rapidement vers des emplois du temps 100 % valides dès la 50ᵉ génération.
2. **Mutation Dirigée** : Les séances impliquées dans un conflit ont une probabilité de mutation élevée (50 %) pour réparer l'emploi du temps, tandis que les séances saines mutent à un taux faible (5 %) pour préserver les blocs stables.
3. **Gestion d'Horaires Variables** : Le moteur s'adapte automatiquement aux semaines universitaires asymétriques (ex: 4 créneaux de 1h30 le Lundi, Mardi, Jeudi, Vendredi avec pause déjeuner ; 3 créneaux le Mercredi et Samedi).

---

## 📈 Résultats et Performance

Sur un problème de référence comportant 3 groupes (80 étudiants), 5 enseignants avec contraintes, 5 salles et 23 séances hebdomadaires :

| Critère | Population Initiale (Moyenne) | Solution Optimale NSGA-II | Amélioration |
| :--- | :---: | :---: | :---: |
| **$f_1$ : Conflits** | 29.25 | **0** | **-100% (Emploi du temps 100% valide)** |
| **$f_2$ : Heures creuses** | 4.63 | **2.00** | **-56.8% de trous étudiants** |
| **$f_3$ : Inadéquation salles** | 13.48 | **3.42** | **-74.6% d'erreur de capacité** |

---

## 📄 Rapport Pédagogique PDF

Un rapport complet de 9 pages en français, structuré pour un public découvrant l'algorithmique avancée et intégrant les figures haute résolution de convergence et du front de Pareto, est disponible dans le dossier `docs/` :
👉 **[`docs/rapport_moga_nsga2.pdf`](docs/rapport_moga_nsga2.pdf)**

---

## 👥 Auteur et Contexte
Projet universitaire d'optimisation combinatoire et d'algorithmes évolutionnaires multiobjectifs.
