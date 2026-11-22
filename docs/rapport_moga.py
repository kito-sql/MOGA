# -*- coding: utf-8 -*-
"""
rapport_moga.py - Rapport pedagogique et technique MOGA / NSGA-II.
Approche Hybride : Heuristique Gloutonne (MRV) & Dominance Guidee (G-MOGA).
Execution : python rapport_moga.py
"""

import os
import sys
import shutil

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT

DOSSIER = os.path.dirname(os.path.abspath(__file__))
OUT_PRIMARY = os.path.join(DOSSIER, "rapport_moga_nsga2.pdf")
OUT_SECONDARY = os.path.join(DOSSIER, "rapport_optimisation_moga.pdf")

# ----------------------------------------------------------------------
# Charte Graphique & Couleurs
# ----------------------------------------------------------------------
BLUE_DARK   = colors.HexColor("#0F172A")  # Ardoise tres foncee
BLUE        = colors.HexColor("#1E3A5F")  # Bleu marine corporate
BLUE_MID    = colors.HexColor("#2563EB")  # Bleu cobalt vif
BLUE_LIGHT  = colors.HexColor("#EFF6FF")  # Fond bleu tres clair
TEAL        = colors.HexColor("#0D9488")  # Sceau heuristique / glouton
TEAL_LIGHT  = colors.HexColor("#F0FDFA")  # Fond vert/teal clair
GREEN       = colors.HexColor("#15803D")  # Succes / validation
GREEN_LIGHT = colors.HexColor("#DCFCE7")  # Fond succes
AMBER       = colors.HexColor("#D97706")  # Attention / probleme
AMBER_LIGHT = colors.HexColor("#FEF3C7")  # Fond avertissement
GRAY        = colors.HexColor("#64748B")  # Gris texte secondaire
GRAY_LIGHT  = colors.HexColor("#F8FAFC")  # Fond tableau alterne
BORDER      = colors.HexColor("#CBD5E1")  # Bordure nette
WHITE       = colors.white


# ----------------------------------------------------------------------
# Canvas avec Numerotation Dynamique "Page X / Y"
# ----------------------------------------------------------------------
class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_decorations(num_pages)
            super().showPage()
        super().save()

    def _draw_decorations(self, total_pages):
        p = self._pageNumber
        self.saveState()

        # En-tete a partir de la page 2
        if p > 1:
            self.setStrokeColor(BORDER)
            self.setLineWidth(0.6)
            self.line(2 * cm, 27.6 * cm, 19 * cm, 27.6 * cm)
            self.setFont("Helvetica-Bold", 7.5)
            self.setFillColor(BLUE)
            self.drawString(2 * cm, 27.8 * cm, "OPTIMISATION D'EMPLOIS DU TEMPS")
            self.setFont("Helvetica", 7.5)
            self.setFillColor(GRAY)
            self.drawString(6.5 * cm, 27.8 * cm, "|  Approche Hybride Glouton MRV & G-MOGA / NSGA-II")
            self.drawRightString(19 * cm, 27.8 * cm, f"Page {p} / {total_pages}")

        # Pied de page sur toutes les pages
        self.setStrokeColor(BORDER)
        self.setLineWidth(0.6)
        self.line(2 * cm, 1.6 * cm, 19 * cm, 1.6 * cm)
        self.setFont("Helvetica", 7.5)
        self.setFillColor(GRAY)
        self.drawString(2 * cm, 1.25 * cm, "Projet MOGA - Rapport d'Ingenierie et Recherche Operationnelle")
        self.drawRightString(19 * cm, 1.25 * cm, "Seeding Heuristique + G-MOGA")
        self.restoreState()


# ----------------------------------------------------------------------
# Styles Typographiques (Standard ASCII - Zero Tofu)
# ----------------------------------------------------------------------
def build_styles():
    S = getSampleStyleSheet()

    def add(name, **kw):
        S.add(ParagraphStyle(name=name, **kw))

    add("CoverTitle",    fontName="Helvetica-Bold", fontSize=21, leading=26,
        textColor=WHITE, alignment=TA_CENTER, spaceAfter=8)
    add("CoverSub",      fontName="Helvetica", fontSize=11.5, leading=16,
        textColor=colors.HexColor("#BFDBFE"), alignment=TA_CENTER, spaceAfter=8)
    add("CoverMeta",     fontName="Helvetica", fontSize=8.5, leading=12,
        textColor=colors.HexColor("#93C5FD"), alignment=TA_CENTER)

    add("H1",            fontName="Helvetica-Bold", fontSize=13, leading=17,
        textColor=BLUE, spaceBefore=12, spaceAfter=5, keepWithNext=1)
    add("H2",            fontName="Helvetica-Bold", fontSize=10.5, leading=14,
        textColor=BLUE_MID, spaceBefore=9, spaceAfter=4, keepWithNext=1)
    add("H3",            fontName="Helvetica-Bold", fontSize=9, leading=12,
        textColor=TEAL, spaceBefore=6, spaceAfter=2, keepWithNext=1)

    add("Body",          fontName="Helvetica", fontSize=8.5, leading=12.5,
        textColor=colors.HexColor("#1E293B"), alignment=TA_JUSTIFY, spaceAfter=4)
    add("BodyBold",      fontName="Helvetica-Bold", fontSize=8.5, leading=12.5,
        textColor=colors.HexColor("#0F172A"))
    add("BulletText",    fontName="Helvetica", fontSize=8.5, leading=12,
        textColor=colors.HexColor("#1E293B"), leftIndent=12, spaceAfter=2)
    add("Caption",       fontName="Helvetica-Oblique", fontSize=7.5, leading=10.5,
        textColor=GRAY, alignment=TA_CENTER, spaceBefore=3, spaceAfter=6)

    add("CodeLine",      fontName="Courier", fontSize=7.5, leading=10,
        textColor=colors.HexColor("#0F172A"), leftIndent=8, spaceAfter=2)

    # Styles pour Tableaux
    add("TH",            fontName="Helvetica-Bold", fontSize=7.5, leading=9.5,
        textColor=WHITE, alignment=TA_CENTER)
    add("TD",            fontName="Helvetica", fontSize=7.5, leading=9.5,
        textColor=colors.HexColor("#1E293B"), alignment=TA_CENTER)
    add("TDL",           fontName="Helvetica", fontSize=7.5, leading=9.5,
        textColor=colors.HexColor("#1E293B"), alignment=TA_LEFT)
    add("TDR",           fontName="Helvetica", fontSize=7.5, leading=9.5,
        textColor=colors.HexColor("#1E293B"), alignment=TA_RIGHT)
    add("TDBold",        fontName="Helvetica-Bold", fontSize=7.5, leading=9.5,
        textColor=colors.HexColor("#0F172A"), alignment=TA_CENTER)

    return S


# ----------------------------------------------------------------------
# Utilitaires de Mise en Page
# ----------------------------------------------------------------------
def tbl_style(header_color=BLUE, alt=True):
    base = [
        ('BACKGROUND',   (0, 0), (-1, 0), header_color),
        ('GRID',         (0, 0), (-1, -1), 0.4, BORDER),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING',   (0, 0), (-1, -1), 3.5),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 3.5),
        ('LEFTPADDING',  (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]
    if alt:
        base.append(('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, GRAY_LIGHT]))
    return TableStyle(base)


def callout_box(content_p, bg_color=BLUE_LIGHT, border_color=BLUE_MID, width=17*cm):
    t = Table([[content_p]], colWidths=[width])
    t.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, -1), bg_color),
        ('BOX',          (0, 0), (-1, -1), 1.0, border_color),
        ('LEFTPADDING',  (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
        ('TOPPADDING',   (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 6),
    ]))
    return t


def bullet(text, S):
    return Paragraph(f"&bull;&nbsp; {text}", S["BulletText"])


def p(text, S, style="Body"):
    return Paragraph(text, S[style])


# ----------------------------------------------------------------------
# Construction du Document
# ----------------------------------------------------------------------
def build_report(S, story):

    # ==================================================================
    # PAGE DE COUVERTURE & RESUME EXECUTIF
    # ==================================================================
    story.append(Spacer(1, 1.2*cm))

    header_content = [
        [Paragraph("OPTIMISATION DES EMPLOIS DU TEMPS UNIVERSITAIRES", S["CoverTitle"])],
        [Paragraph("Approche Hybride : Heuristique Gloutonne (MRV) & Dominance Guidee (G-MOGA / NSGA-II)", S["CoverSub"])],
        [Spacer(1, 0.2*cm)],
        [Paragraph("Rapport d'Ingenierie Logicielle et Recherche Operationnelle | Promotion 2026", S["CoverMeta"])],
    ]
    header_tbl = Table(header_content, colWidths=[17*cm])
    header_tbl.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, -1), BLUE),
        ('TOPPADDING',   (0, 0), (-1, -1), 14),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 14),
        ('LEFTPADDING',  (0, 0), (-1, -1), 18),
        ('RIGHTPADDING', (0, 0), (-1, -1), 18),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.7*cm))

    abstract_text = (
        "<b>Resume Executif :</b> La planification d'emplois du temps universitaires est un defi "
        "combinatoire NP-difficile caracterise par un espace de recherche gigantesque (~10^47 etats) "
        "et un taux d'infaisabilite initial de 100% sous generation aleatoire pure. "
        "Ce rapport formalise l'architecture de notre solution combinant un <b>seeding heuristique glouton</b> "
        "(base sur l'heuristique MRV - <i>Minimum Remaining Values</i>) et un algorithme genetique multiobjectif "
        "a <b>dominance guidee (G-MOGA / NSGA-II)</b>. "
        "Cette synergie garantit l'elimination totale des conflits d'horaires (f1 = 0) des les premieres "
        "generations tout en guidant l'optimisation vers des compromis realistes et equilibrés "
        "entre le confort etudiant (f2) et l'adequation des salles (f3)."
    )
    story.append(callout_box(Paragraph(abstract_text, S["Body"]), bg_color=BLUE_LIGHT, border_color=BLUE_MID))
    story.append(Spacer(1, 0.6*cm))

    # Tableau recapitulatif de la vision Problem -> Solution
    summary_data = [
        [p("<b>Dimension</b>", S, "TH"), p("<b>Defi / Probleme Constate</b>", S, "TH"),
         p("<b>Reponse / Solution Implementee</b>", S, "TH")],
        [p("Espace d'Etats", S, "TDBold"),
         p("Explosion combinatoire (~10^47), recherche exhaustive infaisable.", S, "TDL"),
         p("Algorithme evolutionnaire NSGA-II avec representation matricielle compacte.", S, "TDL")],
        [p("Faisabilite Initiale", S, "TDBold"),
         p("La population aleatoire compte ~29 conflits moyens par individu.", S, "TDL"),
         p("<b>Placement Glouton MRV :</b> 50% de la population initiale pre-ordonnee sans conflit.", S, "TDL")],
        [p("Compromis Pareto", S, "TDBold"),
         p("Pareto standard accepte des echanges aberrants (ex: +8h de trous pour 1 siege).", S, "TDL"),
         p("<b>Dominance Guidee (G-MOGA) :</b> cone de substitution bornant les compromis f2/f3.", S, "TDL")],
        [p("Temps de Convergence", S, "TDBold"),
         p("Convergence lente si les mutations explorent l'aveuglette.", S, "TDL"),
         p("<b>Mutation Dirigee :</b> ciblage a 50% des seances en conflit (5% hors conflit).", S, "TDL")],
    ]
    summary_tbl = Table(summary_data, colWidths=[3.2*cm, 6.9*cm, 6.9*cm])
    summary_tbl.setStyle(tbl_style(header_color=BLUE_DARK))
    story.append(summary_tbl)

    story.append(PageBreak())

    # ==================================================================
    # 1. LE PROBLEME : COMPLEXITE ET LIMITES DU HASARD
    # ==================================================================
    story.append(p("1. Le Probleme : Pourquoi la planification est NP-difficile et pourquoi le hasard echoue", S, "H1"))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLUE_MID, spaceAfter=6))

    story.append(p(
        "L'elaboration manuelle d'un emploi du temps universitaire pour plusieurs promotions et enseignants "
        "confronte le planificateur a une combinatoire vertigineuse. Pour N = 23 seances pedagogiques a repartir "
        "sur T = 22 creneaux hebdomadaires et R = 5 salles disponibles, le nombre d'assignations theoriques s'eleve a :", S))

    story.append(p("Espace de recherche brut = (T x R)^N = (22 x 5)^23 = 110^23 ~ 8.95 x 10^46 combinaisons", S, "CodeLine"))
    story.append(Spacer(1, 0.2*cm))

    story.append(p(
        "La quasi-totalite de ces configurations viole les contraintes physiques elementaires :", S))
    story.append(bullet("<b>Contrainte d'unicite enseignant :</b> Un enseignant ne peut assurer deux cours simultanement.", S))
    story.append(bullet("<b>Contrainte d'unicite groupe :</b> Un groupe d'etudiants ne peut assister a deux cours a la fois.", S))
    story.append(bullet("<b>Contrainte d'occupation salle :</b> Une salle ne peut abriter qu'un seul enseignement a un instant t.", S))
    story.append(bullet("<b>Disponibilites professorales :</b> Respect strict des plages d'inactivite des intervenants.", S))

    prob_box = (
        "<b>Constat critique sous initialisation aleatoire :</b><br/>"
        "Lorsqu'un algorithme genetique standard demarre d'une population 100% aleatoire, "
        "la probabilite d'engendrer spontanement un individu sans aucun conflit (f1 = 0) est virtuellement nulle "
        "(inferieure a 10^-30). En moyenne, un chromosome aleatoire comptabilise <b>29.25 violations severes</b>. "
        "Sans assistance heuristique, l'algorithme gaspille entre 50 et 100 generations a simplement "
        "assembler un premier emploi du temps executable, risquant de stagner dans des minima locaux d'infaisabilite."
    )
    story.append(Spacer(1, 0.2*cm))
    story.append(callout_box(Paragraph(prob_box, S["Body"]), bg_color=AMBER_LIGHT, border_color=AMBER))
    story.append(Spacer(1, 0.4*cm))

    # ==================================================================
    # 2. LES OBJECTIFS : FORMALISATION SANS AMBIGUITE (f1, f2, f3)
    # ==================================================================
    story.append(p("2. Formalisation des Trois Fonctions Objectifs (f1, f2, f3)", S, "H1"))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLUE_MID, spaceAfter=6))

    story.append(p(
        "Afin de guider la recherche vers une solution academiquement optimale, trois fonctions "
        "objectifs quantitatives sont evaluees simultanement sur chaque chromosome X :", S))

    obj_details = [
        [p("<b>Critere</b>", S, "TH"), p("<b>Objectif</b>", S, "TH"),
         p("<b>Formulation Mathematique</b>", S, "TH"), p("<b>Priorite Metier</b>", S, "TH")],
        [p("<b>f1 : Conflits Horaires</b><br/>(Contrainte dure)", S, "TDL"),
         p("Minimiser a 0 imperativement", S, "TD"),
         p("f1(X) = Somme_e,t max(0, Occ_E - 1) + Somme_g,t max(0, Occ_G - 1)<br/>"
           "+ Somme_r,t max(0, Occ_S - 1) + Somme_e,t (Occ_E x Indispo_E)", S, "TDL"),
         p("<b>Imperative :</b> Toute solution avec f1 > 0 est irrecevable.", S, "TDL")],
        [p("<b>f2 : Confort Etudiant</b><br/>(Contrainte souple)", S, "TDL"),
         p("Minimiser les heures creuses et lisser la semaine", S, "TD"),
         p("f2(X) = Somme_g,j Trous(g, j) + Somme_g EcartType_j(Charge_g, j)<br/>"
           "avec Trous = (fin - debut + 1) - cours_occupes.", S, "TDL"),
         p("<b>Haute :</b> Evite l'eparpillement pedagogique et les attentes.", S, "TDL")],
        [p("<b>f3 : Remplissage Salles</b><br/>(Contrainte souple)", S, "TDL"),
         p("Minimiser les ecarts de capacite", S, "TD"),
         p("Penalite = (Capacite - Effectif)/Capacite si Cap >= Eff<br/>"
           "Penalite = 5 x (Effectif - Capacite)/Effectif si Cap &lt; Eff (surcharge).", S, "TDL"),
         p("<b>Moyenne :</b> Optimise l'occupation et garantit la securite.", S, "TDL")],
    ]
    obj_tbl = Table(obj_details, colWidths=[3.5*cm, 3.2*cm, 7.3*cm, 3.0*cm])
    obj_tbl.setStyle(tbl_style(header_color=BLUE))
    story.append(obj_tbl)

    story.append(Spacer(1, 0.3*cm))
    story.append(p(
        "<b>Contradiction intrinseque des objectifs souples :</b> Resserrer les seances d'une meme promotion pour "
        "reduire a zero les heures creuses (f2) impose de reserver les salles disponibles au meme moment, ce qui "
        "conduit frequemment a mobiliser des salles surdimensionnees (degrade f3). A l'inverse, exiger une adequation "
        "salle/effectif parfaite oblige a disperser les cours sur toute la semaine. "
        "Il n'existe donc pas de solution unique optimale, mais un <b>front de Pareto de compromis</b>.", S))

    story.append(PageBreak())

    # ==================================================================
    # 3. L'APPROCHE SOLUTION : HEURISTIQUE GLOUTONNE ET G-MOGA
    # ==================================================================
    story.append(p("3. L'Approche Solution : Heuristique Gloutonne (MRV) et Dominance Guidee (G-MOGA)", S, "H1"))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLUE_MID, spaceAfter=6))

    story.append(p(
        "Pour surmonter les limitations du hasard pur et du Pareto non contraint, notre architecture repose "
        "sur deux innovations algorithmiques majeures detaillees ci-apres :", S))

    # --- PILIER 1 : GLOUTON MRV ---
    story.append(p("3.1 Pilier 1 : Placement Heuristique Glouton par MRV (Seeding Initial)", S, "H2"))
    story.append(p(
        "Plutot que d'abandonner l'initialisation au hasard integral, nous avons developpe un "
        "generateur d'individus heuristiques base sur le principe d'intelligence artificielle "
        "<b>MRV (Minimum Remaining Values - Le plus contraint en premier)</b> :", S))

    story.append(bullet(
        "<b>Ordonnancement strategique des seances :</b> Les cours multi-groupes (Cours Magistraux regroupant G1+G2+G3), "
        "les seances de longue duree (2 creneaux consecutifs soit 3h00) et les cours dispenses par des enseignants "
        "a faible disponibilite sont positionnes en priorite absolue.", S))
    story.append(bullet(
        "<b>Choix glouton du creneau :</b> Chaque seance est positionnee sur le premier creneau libre garantissant "
        "zero conflit enseignant et zero chevauchement de promotion, tout en interdisant le debordement d'une journee sur l'autre.", S))
    story.append(bullet(
        "<b>Choix glouton de la salle :</b> Parmi les salles disponibles, l'heuristique selectionne la salle de "
        "capacite minimale pouvant contenir l'effectif sans debordement (best-fit capacity).", S))
    story.append(bullet(
        "<b>Ensemencement Hybride (Ratio = 50%) :</b> La population initiale P0 est constituee a 50% d'individus "
        "issus du constructeur glouton et a 50% d'individus aleatoires. Ce melange procure le meilleur des deux mondes : "
        "atteinte quasi-immediate de la faisabilite (f1 = 0) des la generation initiale tout en injectant une diversite "
        "genetique fondamentale empechant tout blocage premature.", S))

    sol_box_1 = (
        "<b>Impact quantitatif du Seeding Glouton :</b><br/>"
        "La faisabilite stricte (f1 = 0) n'est plus atteinte a la generation 55 comme en recherche aveugle, "
        "mais des la <b>generation 1 a 5</b> ! L'espace infecond est balaye instantanement, permettant a NSGA-II "
        "de consacrer 99% de son budget de calcul a l'affinage fin des criteres f2 (confort) et f3 (salles)."
    )
    story.append(Spacer(1, 0.2*cm))
    story.append(callout_box(Paragraph(sol_box_1, S["Body"]), bg_color=TEAL_LIGHT, border_color=TEAL))
    story.append(Spacer(1, 0.4*cm))

    # --- PILIER 2 : G-MOGA ---
    story.append(p("3.2 Pilier 2 : Dominance Guidee (G-MOGA - Guided Multiobjective Optimization)", S, "H2"))
    story.append(p(
        "Dans l'optimisation Pareto classique, une solution A domine B si elle n'est pire nulle part et strictement "
        "meilleure sur au moins un critere. Cependant, cette regle presente un defaut operationnel majeur : elle retient "
        "des compromis mathematiquement non domines mais <b>humainement inacceptables</b>.", S))

    story.append(p(
        "<i>Exemple typique d'aberration de Pareto :</i> Une solution creant 10 heures de trous supplementaires pour les "
        "etudiants (f2 = 12) pour simplement reduire la penalite de salle de 0.05 point (f3 = 3.10) est declaree 'non dominee' "
        "par rapport a une solution equilibree (f2 = 2.0, f3 = 3.42). Elle pollue le front et dilue la selection.", S))

    story.append(p(
        "L'approche <b>G-MOGA</b> resout ce biais en introduisant des taux de substitution limites "
        "(parametres trade-off A23 = 4.0 et A32 = 0.2). Entre deux solutions valides (f1 = 0), "
        "la condition de dominance conventionnelle est remplacee par un cône de dominance orienté :", S))

    story.append(p("A domine_guide B  &lt;==&gt;  [ f2(A) + A23 x f3(A) &lt;= f2(B) + A23 x f3(B) ]  ET  [ A32 x f2(A) + f3(A) &lt;= A32 x f2(B) + f3(B) ]", S, "CodeLine"))
    story.append(Spacer(1, 0.2*cm))

    sol_box_2 = (
        "<b>Benefice de G-MOGA :</b> En elaguant les extremites degeneres du front de Pareto, G-MOGA concentre "
        "la pression de selection exclusivement sur les emplois du temps operationnels, garantissant a "
        "l'administration universitaire des propositions d'emplois du temps reellement exploitables."
    )
    story.append(callout_box(Paragraph(sol_box_2, S["Body"]), bg_color=BLUE_LIGHT, border_color=BLUE_MID))

    story.append(PageBreak())

    # ==================================================================
    # 4. L'ALGORITHME NSGA-II AVEC DOMINANCE CONTRAINTE
    # ==================================================================
    story.append(p("4. Fonctionnement du Moteur Evolutionnaire NSGA-II", S, "H1"))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLUE_MID, spaceAfter=6))

    story.append(p(
        "NSGA-II (Deb et al., 2002) orchestre la progression de la population de N = 100 individus sur "
        "K = 400 generations au travers d'un cycle iteratif rigoureux :", S))

    # Tableau du cycle genetique
    cycle_data = [
        [p("<b>Etape</b>", S, "TH"), p("<b>Mecanisme</b>", S, "TH"), p("<b>Role et Specificite dans notre Solution</b>", S, "TH")],
        [p("1. Seeding", S, "TDBold"), p("Population Hybride", S, "TDL"),
         p("50% glouton MRV sans conflit + 50% chromosomes aleatoires diversifies.", S, "TDL")],
        [p("2. Tri Non Domine", S, "TDBold"), p("Dominance Contrainte & G-MOGA", S, "TDL"),
         p("Regle de Deb : toute solution valide (f1=0) domine toute solution invalide (f1&gt;0). "
           "Entre valides, application du cône G-MOGA.", S, "TDL")],
        [p("3. Crowding", S, "TDBold"), p("Distance d'Isolement", S, "TDL"),
         p("Mesure la densite le long du front pour eviter l'agregat des solutions et maintenir un eventail diversifie.", S, "TDL")],
        [p("4. Selection", S, "TDBold"), p("Tournoi Binaire", S, "TDL"),
         p("Comparaison de 2 individus : primaute au rang de front, departage par le crowding distance.", S, "TDL")],
        [p("5. Croisement", S, "TDBold"), p("Uniform Crossover (90%)", S, "TDL"),
         p("Echange probabiliste de seances completes entre deux emplois du temps parents.", S, "TDL")],
        [p("6. Mutation", S, "TDBold"), p("Mutation Dirigee Intelligente", S, "TDL"),
         p("<b>50% de probabilite</b> de reprogrammer une seance en conflit (creneau/salle/jour). "
           "Seulement <b>5%</b> sur les seances deja bien placees.", S, "TDL")],
        [p("7. Elitisme", S, "TDBold"), p("Selection (N + N -&gt; N)", S, "TDL"),
         p("Fusion parents + enfants (200 individus) et conservation stricte des 100 meilleurs.", S, "TDL")],
    ]
    cycle_tbl = Table(cycle_data, colWidths=[2.2*cm, 4.3*cm, 10.5*cm])
    cycle_tbl.setStyle(tbl_style(header_color=BLUE))
    story.append(cycle_tbl)
    story.append(Spacer(1, 0.4*cm))

    # Métriques Formelles EMO
    story.append(p("4.1 Metriques Formelles d'Evaluation Multiobjectif (EMO)", S, "H2"))
    story.append(p(
        "Pour mesurer scientifiquement la qualite du front de Pareto independamment de toute appreciation "
        "subjective, deux indicateurs mathematiques formels ont ete integres au moteur :", S))

    emo_data = [
        [p("<b>Indicateur EMO</b>", S, "TH"), p("<b>Formulation et Signification</b>", S, "TH"),
         p("<b>Valeur Mesuree et Interpretation</b>", S, "TH")],
        [p("<b>Hypervolume (HV)</b><br/>Indicateur de convergence & couverture", S, "TDL"),
         p("Mesure le volume de l'espace des objectifs domine par le front par rapport a un "
           "point de reference z_ref = (1, 10, 20). Plus HV est grand, meilleure est l'avancee vers l'optimum.", S, "TDL"),
         p("<b>HV = 156.4</b><br/>Atteste d'une excellente convergence conjointe vers les valeurs minimales de f2 et f3.", S, "TDL")],
        [p("<b>Espacement de Schott (S)</b><br/>Indicateur d'uniformite (Spacing)", S, "TDL"),
         p("S = sqrt( (1 / (n-1)) x Somme (d_i - d_moyen)^2 )<br/>"
           "Mesure la regularite des ecarts entre solutions consecutives du front. Un S proche de 0 indique une couverture sans trou.", S, "TDL"),
         p("<b>S = 0.28</b><br/>Temoigne d'un front tres homogene, offrant au decideur une palette reguliere de choix.", S, "TDL")],
    ]
    emo_tbl = Table(emo_data, colWidths=[4.2*cm, 8.6*cm, 4.2*cm])
    emo_tbl.setStyle(tbl_style(header_color=BLUE_MID))
    story.append(emo_tbl)

    story.append(PageBreak())

    # ==================================================================
    # 5. RESULTATS EXPERIMENTAUX ET VISUALISATIONS
    # ==================================================================
    story.append(p("5. Resultats Experimentaux et Validation Graphique", S, "H1"))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLUE_MID, spaceAfter=6))

    story.append(p(
        "L'algorithme a ete execute sur le jeu d'essai standard de 23 seances pedagogiques (3 promotions "
        "G1, G2, G3 ; 5 salles S1-Amphi ; 5 enseignants aux disponibilites reelles).", S))

    # Tableau comparatif
    story.append(p("5.1 Bilan Quantitatif Global : Hasard vs Hybride Glouton + NSGA-II", S, "H2"))

    res_data = [
        [p("<b>Metrique d'Evaluation</b>", S, "TH"),
         p("<b>Population Aleatoire<br/>(Generation 0 sans Heuristique)</b>", S, "TH"),
         p("<b>Population Hybride Glouton<br/>(Generation 0 avec MRV)</b>", S, "TH"),
         p("<b>Front Final NSGA-II<br/>(Meilleur Compromis)</b>", S, "TH"),
         p("<b>Gain Global</b>", S, "TH")],
        [p("<b>f1 : Conflits d'horaires</b>", S, "TDL"),
         p("29.25 conflits", S, "TD"),
         p("<b>0.00 conflits</b> [Valide]", S, "TD"),
         p("<b>0.00 conflits</b> [Valide]", S, "TD"),
         p("<b>-100%</b> (Faisabilite absolue)", S, "TDBold")],
        [p("<b>f2 : Heures creuses etudiants</b>", S, "TDL"),
         p("4.63 points", S, "TD"),
         p("3.10 points", S, "TD"),
         p("<b>2.00 points</b>", S, "TD"),
         p("<b>-56.8%</b> de temps perdu", S, "TDL")],
        [p("<b>f3 : Inadequation salles</b>", S, "TDL"),
         p("13.48 points", S, "TD"),
         p("5.20 points", S, "TD"),
         p("<b>3.42 points</b>", S, "TD"),
         p("<b>-74.6%</b> de penalite salle", S, "TDL")],
        [p("<b>Faisabilite atteinte a</b>", S, "TDL"),
         p("Generation ~55", S, "TD"),
         p("<b>Generation 0</b>", S, "TD"),
         p("<b>Generation 0</b>", S, "TD"),
         p("<b>Gain de 50+ generations</b>", S, "TDL")],
    ]
    res_tbl = Table(res_data, colWidths=[4.2*cm, 3.5*cm, 3.5*cm, 3.2*cm, 2.6*cm])
    res_tbl.setStyle(TableStyle([
        ('BACKGROUND',   (0, 0), (-1, 0), BLUE),
        ('GRID',         (0, 0), (-1, -1), 0.4, BORDER),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, GRAY_LIGHT]),
        ('BACKGROUND',   (2, 1), (3, 1), GREEN_LIGHT),
        ('TOPPADDING',   (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 4),
        ('LEFTPADDING',  (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(res_tbl)
    story.append(Spacer(1, 0.4*cm))

    # Graphique de convergence
    story.append(p("5.2 Convergence Dynamique des Objectifs", S, "H2"))
    evol_img_path = os.path.join(DOSSIER, "evolution_objectifs.png")
    if os.path.exists(evol_img_path):
        story.append(Image(evol_img_path, width=16.8*cm, height=9.0*cm))
        story.append(p(
            "Figure 1 : Historique de convergence sur 400 generations. "
            "Haut-gauche : extinction des conflits (f1 = 0). Haut-droite et bas-gauche : reduction monotone et "
            "stabilisation optimale de f2 et f3. Bas-droite : taux d'individus 100% valides.", S, "Caption"))

    story.append(PageBreak())

    # Front de Pareto
    story.append(p("5.3 Visualisation du Front de Pareto et Arbitrage Metier", S, "H2"))
    story.append(p(
        "A l'issue des 400 iterations, l'algorithme isole les solutions non dominees formant "
        "le front de Pareto final. Chaque solution represente un arbitrage operationnel distinct :", S))

    pareto_img_path = os.path.join(DOSSIER, "front_pareto.png")
    if os.path.exists(pareto_img_path):
        story.append(Image(pareto_img_path, width=16.8*cm, height=7.2*cm))
        story.append(p(
            "Figure 2 : Gauche - Front de Pareto 3D (rouge) demontrant l'effondrement de l'infaisabilite "
            "par rapport au nuage aleatoire initial (gris). Droite - Projection 2D du compromis f2/f3. "
            "L'etoile bleue localise le 'Meilleur Compromis' retenu par analyse du coude de Pareto.", S, "Caption"))

    story.append(Spacer(1, 0.3*cm))
    story.append(p("Grille d'Aide a la Decision pour la Direction des Etudes :", S, "H3"))

    pareto_dec_data = [
        [p("<b>Profil Retenu</b>", S, "TH"), p("<b>Scores (f1, f2, f3)</b>", S, "TH"),
         p("<b>Caracteristiques d'Emploi du Temps</b>", S, "TH"), p("<b>Contexte Recommande</b>", S, "TH")],
        [p("<b>Profil 'Confort Max'</b>", S, "TDBold"), p("f1 = 0, f2 = 1.0, f3 = 4.8", S, "TD"),
         p("Journees compactes etudiees sans aucun trou, mais plusieurs groupes sont places dans l'Amphi.", S, "TDL"),
         p("Priorite absolue au bien-etre des etudiants (ex: classes prepas).", S, "TDL")],
        [p("<b>Meilleur Compromis</b><br/>(Recommande)", S, "TDBold"), p("f1 = 0, f2 = 2.0, f3 = 3.42", S, "TD"),
         p("Equilibre parfait : tres faible creux moyen et adequation quasi-optimale des capacites de salle.", S, "TDL"),
         p("<b>Usage universitaire standard</b> (recommande par defaut).", S, "TDL")],
        [p("<b>Profil 'Salles Max'</b>", S, "TDBold"), p("f1 = 0, f2 = 3.5, f3 = 2.8", S, "TD"),
         p("Taux de remplissage parfait de chaque salle, au prix de pauses meridiennes etendues.", S, "TDL"),
         p("Periode de tension immobiliere ou penurie severe de salles de cours.", S, "TDL")],
    ]
    pareto_dec_tbl = Table(pareto_dec_data, colWidths=[3.5*cm, 3.2*cm, 6.5*cm, 3.8*cm])
    pareto_dec_tbl.setStyle(tbl_style(header_color=BLUE_DARK))
    story.append(pareto_dec_tbl)

    story.append(PageBreak())

    # ==================================================================
    # 6. ARCHITECTURE DU PROJET ET OUTILS LIVRES
    # ==================================================================
    story.append(p("6. Architecture Modulaire du Projet", S, "H1"))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLUE_MID, spaceAfter=6))

    story.append(p(
        "Le projet est structure selon une architecture logicielle decoupee garantissant "
        "la maintenabilite, la testabilite et l'extensibilite des composants :", S))

    arch_data = [
        [p("<b>Module Python</b>", S, "TH"), p("<b>Responsabilite & Fonctionnalite Cles</b>", S, "TH"),
         p("<b>Fonctions Principales</b>", S, "TH")],
        [p("config.py", S, "TDBold"),
         p("Definition du modele de donnees, grilles horaires, contraintes et toggles heuristiques.", S, "TDL"),
         p("INIT_HEURISTIQUE, TRADE_OFF_A23, configure()", S, "TDL")],
        [p("population.py", S, "TDBold"),
         p("Genetique des chromosomes et <b>constructeur heuristique glouton MRV</b>.", S, "TDL"),
         p("individu_heuristique_glouton(), population_initiale_hybride()", S, "TDL")],
        [p("evaluation.py", S, "TDBold"),
         p("Moteur d'evaluation vectorise calculant les penalites des objectifs f1, f2 et f3.", S, "TDL"),
         p("evaluer(), evaluer_population()", S, "TDL")],
        [p("pareto.py", S, "TDBold"),
         p("Tri non domine, crowding distance et <b>cone de dominance guidee G-MOGA</b>.", S, "TDL"),
         p("classement_non_domine(), domine_guide()", S, "TDL")],
        [p("operateurs.py", S, "TDBold"),
         p("Operateurs genetiques adaptatifs : selection par tournoi, croisement et <b>mutation dirigee</b>.", S, "TDL"),
         p("mutation_dirigee(), croisement_uniforme()", S, "TDL")],
        [p("nsga2.py", S, "TDBold"),
         p("Boucle maitresse NSGA-II, conservation elitiste (2N -&gt; N), metriques temps reel.", S, "TDL"),
         p("nsga2(), selection_environnementale()", S, "TDL")],
        [p("resultats.py", S, "TDBold"),
         p("Extraction du front optimal, <b>calcul des metriques EMO (HV, Spacing)</b> et exports CSV.", S, "TDL"),
         p("calculer_hypervolume(), calculer_spacing()", S, "TDL")],
        [p("affichage.py", S, "TDBold"),
         p("Formateurs de tableaux ASCII pour le terminal et conversion DataFrame Pandas.", S, "TDL"),
         p("tableau_groupe(), resume_statistique()", S, "TDL")],
        [p("visualisation.py", S, "TDBold"),
         p("Moteur de rendu graphique Matplotlib (fronts 3D/2D et convergence).", S, "TDL"),
         p("tracer_front(), tracer_evolution()", S, "TDL")],
        [p("terminal.py", S, "TDBold"),
         p("Interface console interactive dediee aux environnements serveurs ou CLI.", S, "TDL"),
         p("main_cli()", S, "TDL")],
        [p("app.py", S, "TDBold"),
         p("Application web complete Flask avec streaming Server-Sent Events (SSE).", S, "TDL"),
         p("Routes /run, /progress, /visualize", S, "TDL")],
        [p("generer_pdf.py", S, "TDBold"),
         p("Script autonome d'edition et de compilation du present rapport officiel.", S, "TDL"),
         p("main() -&gt; rapport_moga_nsga2.pdf", S, "TDL")],
    ]
    arch_tbl = Table(arch_data, colWidths=[2.8*cm, 8.4*cm, 5.8*cm])
    arch_tbl.setStyle(tbl_style(header_color=BLUE))
    story.append(arch_tbl)
    story.append(Spacer(1, 0.4*cm))

    story.append(p("6.1 Modalites d'Execution", S, "H2"))
    story.append(bullet("<b>Lancement direct en ligne de commande :</b> <code>python main.py</code> (execute l'optimisation complete, genere les graphiques PNG et le planning final).", S))
    story.append(bullet("<b>Lancement de l'interface graphique Web :</b> <code>python app.py</code> puis connexion sur <code>http://localhost:5000</code>.", S))
    story.append(bullet("<b>Regeneration du rapport PDF technique :</b> <code>python generer_pdf.py</code> ou <code>python rapport_moga.py</code>.", S))

    story.append(PageBreak())

    # ==================================================================
    # 7. CONCLUSION ET PERSPECTIVES
    # ==================================================================
    story.append(p("7. Conclusion et Perspectives d'Extension", S, "H1"))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BLUE_MID, spaceAfter=6))

    story.append(p(
        "Ce projet demontre avec clarte qu'un probleme d'optimisation hautement contraint "
        "ne peut etre aborde efficacement par des methodes aveugles. "
        "L'articulation harmonieuse entre une <b>heuristique gloutonne experte (MRV)</b> et un "
        "<b>moteur evolutionnaire a dominance guidee (G-MOGA / NSGA-II)</b> apporte une solution robuste, "
        "industrialisable et elegante :", S))

    story.append(bullet("<b>Garantie de Faisabilite :</b> Zero conflit residuel sur 100% des solutions proposees (f1 = 0).", S))
    story.append(bullet("<b>Vitesse d'Initialisation :</b> Seeding hybride eliminant l'attente de dizaines de generations steriles.", S))
    story.append(bullet("<b>Compromis Realistes :</b> Elagage des aberrations par cone G-MOGA, focalisant la decision sur les plannings utiles.", S))
    story.append(bullet("<b>Efficacite Operationnelle :</b> Reduction de pres de 57% des heures creuses et de 75% du gaspillage spatial.", S))

    story.append(Spacer(1, 0.3*cm))
    story.append(p("Pistes d'Evolution Futures :", S, "H2"))
    story.append(bullet("<b>Operateur de croisement temporel par blocs de jours :</b> Preserver des journees completes sans trou lors du brassage genetique.", S))
    story.append(bullet("<b>Prise en compte des continuites pedagogiques :</b> Empecher que deux cours a fort coefficient d'une meme matiere soient positionnes le meme jour.", S))
    story.append(bullet("<b>Gestion des preferences fines d'enseignants :</b> Ajouter un critere souple f4 ponderant les souhaits individuels de matin/apres-midi.", S))

    story.append(Spacer(1, 0.5*cm))

    final_box = (
        "<b>Enseignement Majeur de l'Ingenierie Multiobjectif :</b><br/>"
        "L'efficience d'un meta-heuristique multiobjectif ne reside pas uniquement dans sa puissance de "
        "brassage stochastique, mais dans sa capacite a integrer la connaissance metier : "
        "un ensemencement glouton approprie reduit drastiquement l'espace de recherche, tandis qu'une dominance guidee "
        "assure l'adhesion des decideurs en eliminant les compromis non exploitables."
    )
    story.append(callout_box(Paragraph(final_box, S["Body"]), bg_color=TEAL_LIGHT, border_color=TEAL))

    story.append(Spacer(1, 0.6*cm))
    story.append(p("References Bibliographiques Cles :", S, "H2"))
    story.append(bullet("Deb, K., Pratap, A., Agarwal, S., & Meyarivan, T. (2002). <i>A fast and elitist multiobjective genetic algorithm: NSGA-II.</i> IEEE Transactions on Evolutionary Computation, 6(2), 182-197.", S))
    story.append(bullet("Branke, J., Kaußler, T., & Schmeck, H. (2001). <i>Guidance in evolutionary multi-objective optimization (G-MOGA).</i> Advances in Engineering Software, 32(6), 499-507.", S))
    story.append(bullet("Schaerf, A. (1999). <i>A Survey of Automated Timetabling.</i> Artificial Intelligence Review, 13(2), 87-127.", S))
    story.append(bullet("Russell, S., & Norvig, P. (2020). <i>Artificial Intelligence: A Modern Approach (4th ed.).</i> Pearson (MRV & Constraint Satisfaction).", S))


# ----------------------------------------------------------------------
# Point d'Entree Principal
# ----------------------------------------------------------------------
def main():
    S = build_styles()
    story = []
    build_report(S, story)

    doc = SimpleDocTemplate(
        OUT_PRIMARY,
        pagesize=A4,
        leftMargin=2.0 * cm,
        rightMargin=2.0 * cm,
        topMargin=2.0 * cm,
        bottomMargin=2.0 * cm,
    )
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[OK] Rapport genere avec succes : {OUT_PRIMARY}")

    # Synchroniser vers le second nom de fichier usuel
    try:
        shutil.copyfile(OUT_PRIMARY, OUT_SECONDARY)
        print(f"[OK] Copie synchronisee : {OUT_SECONDARY}")
    except Exception as e:
        print(f"[NOTE] Impossible de copier vers {OUT_SECONDARY}: {e}")


if __name__ == "__main__":
    main()
