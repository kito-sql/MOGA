# 🌐 MOGA Timetabling — Version Interface Web (Webview)

Cette version propose une **interface graphique interactive complète** accessible directement depuis votre navigateur web. Elle permet de configurer dynamiquement tous les paramètres de l'université, de suivre l'évolution de l'algorithme génétique en direct et de visualiser les emplois du temps optimisés sous forme d'onglets ergonomiques.

---

## 🎯 Objectifs

- **Accessibilité visuelle** : Configurer facilement les groupes d'étudiants, les salles, les enseignants et les matières sans toucher au code.
- **Suivi temps réel** : Visualiser la progression génération par génération grâce au streaming Server-Sent Events (SSE).
- **Exploration interactive des résultats** : Consulter les grilles d'emplois du temps par groupe, inspecter le front de Pareto (3D et projection 2D) et télécharger les exports (CSV et images).

---

## 📅 Structure de la Semaine Universitaire

Cette version implémente l'horaire universitaire cible avec créneaux de 1h30, pause de 15 minutes entre chaque cours et pause déjeuner :

| Jours | Nombre de séances | Créneaux horaires |
| :--- | :---: | :--- |
| **Lundi, Mardi, Jeudi, Vendredi** | 4 séances / jour | • 08:30 – 10:00<br/>• 10:15 – 11:45<br/>*(Pause déjeuner 11:45 – 13:00)*<br/>• 13:00 – 14:30<br/>• 14:45 – 16:15 |
| **Mercredi, Samedi** | 3 séances consécutives | • 08:30 – 10:00<br/>• 10:15 – 11:45<br/>• 12:00 – 13:30 |

---

## 🚀 Installation et Lancement

### 1. Prérequis
Python 3.8 ou supérieur installé.

### 2. Installation des dépendances
Depuis ce dossier (`web-version`) :
```bash
pip install -r requirements.txt
```

### 3. Lancer l'application web
```bash
python app.py
```

### 4. Accéder à l'interface
Ouvrez votre navigateur web à l'adresse suivante :
👉 **[http://localhost:5000](http://localhost:5000)**

---

## 🖥️ Fonctionnalités de l'Interface

1. **Panneau de Configuration (Gauche)** :
   - **Jours actifs** : Cochez/décochez les jours ouvrés de votre établissement.
   - **Groupes** : Ajoutez ou supprimez des groupes avec leur effectif respectif (ex: `G1`, `30`).
   - **Salles** : Configurez vos salles avec leurs capacités maximales.
   - **Enseignants** : Renseignez les disponibilités par jour de chaque enseignant (ex: `Lun,Mar,Jeu`).
   - **Matières** : Indiquez l'enseignant responsable, la durée (1 ou 2 créneaux de 1h30) et le type (`CM` pour cours magistral commun, `TD/TP` pour séance par groupe).
   - **Paramètres NSGA-II** : Ajustez la taille de population, le nombre de générations, les probabilités de croisement et de mutation, ainsi que la graine aléatoire (`seed`).

2. **Panneau des Résultats (Droite)** :
   - **Barre de progression en temps réel** : Affichage fluide de la génération courante, de la meilleure valeur des objectifs et du ratio d'emplois du temps valides.
   - **Onglet Graphiques** : Front de Pareto 3D et 2D, et courbes de convergence des 3 objectifs.
   - **Onglet Emplois du temps** : Navigation par onglet entre les groupes avec coloration automatique des créneaux occupés et alerte visuelle en cas de conflit.
   - **Onglet Front de Pareto** : Tableau interactif répertoriant toutes les solutions non dominées et le meilleur compromis sélectionné.
   - **Onglet Téléchargements** : Liens directs pour récupérer les fichiers CSV et PNG produits.

---

## 🧬 Les 3 Objectifs Optimisés (NSGA-II)

1. **$f_1$ : Conflits matériels et humains (à minimiser, cible = 0)**
   - Chevauchements de salles, double réservation d'un enseignant, double cours pour un même groupe, cours assigné un jour où l'enseignant est indisponible.
2. **$f_2$ : Confort et équilibre des étudiants (à minimiser)**
   - Réduction des créneaux creux (trous dans la journée) et équilibrage de la charge hebdomadaire (faible variance de cours par jour).
3. **$f_3$ : Utilisation rationnelle des salles (à minimiser)**
   - Pénalisation des salles sous-dimensionnées (surcharge pénalisée avec un coefficient x5) et des salles surdimensionnées (gaspillage de places).
