# 💻 MOGA Timetabling — Version Terminal Épurée (CLI)

Cette version propose une **interaction minimale et directe dans le terminal**. Elle est pensée pour les utilisateurs préférant une exécution rapide en ligne de commande, sans serveur web ni framework tiers, avec une saisie manuelle guidée et un rendu soigné en tableaux ASCII.

---

## 🎯 Objectifs

- **Interaction minimale et rapide** : Saisie guidée étape par étape dans la console avec propositions de valeurs par défaut intelligentes (un simple appui sur Entrée valide la valeur proposée).
- **Zéro dépendance web** : Fonctionne uniquement avec les bibliothèques scientifiques standards (`numpy`, `pandas`, `matplotlib`).
- **Rendu épuré** : Présentation claire et lisible des emplois du temps directement dans la console, sans pollution visuelle, avec détection explicite des éventuels conflits par le symbole `⚠`.

---

## 📅 Structure de la Semaine Universitaire

Cette version prend en compte l'horaire universitaire cible :

| Jours | Nombre de séances | Créneaux horaires |
| :--- | :---: | :--- |
| **Lundi, Mardi, Jeudi, Vendredi** | 4 séances / jour | • 08:30 – 10:00<br/>• 10:15 – 11:45<br/>*(Pause déjeuner 11:45 – 13:00)*<br/>• 13:00 – 14:30<br/>• 14:45 – 16:15 |
| **Mercredi, Samedi** | 3 séances consécutives | • 08:30 – 10:00<br/>• 10:15 – 11:45<br/>• 12:00 – 13:30 |

---

## 🚀 Installation et Lancement

### 1. Prérequis
Python 3.8 ou supérieur installé.

### 2. Installation des dépendances
Depuis ce dossier (`terminal-version`) :
```bash
pip install -r requirements.txt
```

### 3. Exécution
```bash
python terminal.py
```

---

## ⌨️ Déroulement de l'Exécution

Le programme vous guide à travers 5 étapes de saisie rapide :
1. **Jours de cours** : Indiquez les jours actifs (ex: `Lundi,Mardi,Mercredi,Jeudi,Vendredi,Samedi`).
2. **Groupes** : Nombre de groupes, noms et effectifs (ex: `G1: 30`, `G2: 35`).
3. **Salles** : Nombre de salles, noms et capacités (ex: `S1: 30`, `Amphi: 120`).
4. **Enseignants** : Noms et indices des jours de disponibilité.
5. **Matières** : Nom du cours, enseignant assigné, durée (1 ou 2 créneaux) et type (`c` pour CM commun, `t` pour TD par groupe).
6. **Paramètres NSGA-II** : Taille de population, nombre de générations et seed.

*💡 Astuce : Toutes les questions proposent une valeur par défaut entre crochets `[défaut]`. Appuyez directement sur **Entrée** pour accepter la valeur par défaut et tester le programme instantanément.*

---

## 📊 Exemple de Sortie Terminal

Pendant l'évolution, une barre de progression compacte sur une seule ligne vous informe de l'état :
```text
  [████████████████████] 100%  gén  400/400  f1=0  f2=2.00  f3=3.42  ✓100
```

Une fois l'optimisation terminée, le terminal affiche :
1. **Le tableau synthétique des gains** comparant la population initiale aléatoire à la solution retenue.
2. **L'emploi du temps hebdomadaire sous forme de grille ASCII** pour chaque groupe :
```text
  Groupe G1  (30 étudiants)
  ───────────────────────────────────────────────────────────────────────────────────────
  Créneau      │     Lundi      │     Mardi      │    Mercredi    │     Jeudi      │ ...
  ───────────────────────────────────────────────────────────────────────────────────────
  08:30-10:00  │Syst. exploit.  │·               │Probas (CM)     │Anglais         │ ...
  10:15-11:45  │Syst. exploit.  │·               │Maths (CM)      │Bases de données│ ...
  13:00-14:30  │Algorithmique   │Réseaux         │Maths (CM)      │Bases de données│ ...
  14:45-16:15  │Algorithmique   │Struct. données │·               │·               │ ...
  ───────────────────────────────────────────────────────────────────────────────────────
```
3. **La liste détaillée des séances** (matière, groupe, enseignant, jour, heure de début, durée, salle).
4. **La confirmation des exports générés** dans le dossier courant :
   - `front_pareto.png`
   - `evolution_objectifs.png`
   - `emploi_du_temps_final.csv`
   - `solutions_pareto.csv`
   - `historique_generations.csv`
