# NOC Dashboard : Automatisation et Sécurisation Réseau IT/OT

Ce dépôt contient le code source d'une plateforme d'automatisation et de supervision réseau, développée dans le cadre d'un projet de fin d'études (BUT Réseaux & Télécommunications, Spécialité Cybersécurité) réalisé au sein du complexe industriel OCP de Jorf Lasfar.

## 📋 Contexte et Objectifs

Ce projet propose une implémentation concrète de l'**Infrastructure as Code (IaC)** et des méthodologies **DevSecOps** appliquées aux environnements critiques. Il vise à résoudre deux problématiques majeures :
1. **Automatisation :** Substituer aux configurations manuelles (CLI) un déploiement dynamique, asynchrone et standardisé, piloté par la donnée.
2. **Cybersécurité :** Sécuriser la convergence entre les réseaux bureautiques (IT) et les réseaux de production (OT) par un cloisonnement strict basé sur le **Modèle Purdue**.

## ⚙️ Fonctionnalités Principales

*   **Approche Data-Driven :** L'intégralité du déploiement est pilotée par des fichiers plats au format CSV (`inventaire.csv`, `vlans.csv`, etc.). La logique algorithmique est strictement séparée des variables d'infrastructure.
*   **Zero-Touch Provisioning :** Configuration automatisée d'équipements Cisco IOS (VLANs Data/Voice, liaisons Trunk, ports d'accès, routage inter-VLAN et services DHCP).
*   **Haute Disponibilité :** Déploiement et supervision de clusters de redondance HSRP sur la couche cœur.
*   **Architecture Asynchrone :** Interface web intégrant un gestionnaire de file d'attente (Queue System) permettant de traiter les connexions SSH en arrière-plan sans figer le navigateur.
*   **Diagnostics Proactifs :** Tests de connectivité ICMP globaux (franchissement de pare-feu), détection des interfaces physiques défaillantes (DOWN) et génération automatisée d'audits de conformité.
*   **Sauvegardes Centralisées :** Extraction et archivage de la `running-config` de l'ensemble du parc matériel.

## 🛠️ Stack Technique et Architecture

*   **Développement & Automatisation :** Python 3, librairie `netmiko` (connexions SSH chiffrées), `asyncio`.
*   **Interface Utilisateur (UI) :** Framework `nicegui` (basé sur Vue.js et FastAPI).
*   **Infrastructure & Virtualisation (GNS3) :** 
    *   Couches hiérarchiques Cisco (Accès, Distribution, Cœur).
    *   Pare-feu pfSense (Désactivation du NAT sortant et règles strictes *Deny All* vers l'OT).
    *   Client industriel sous Alpine Linux.

## 🗂️ Structure du Dépôt

```text
📁 noc-dashboard-automation
├── 📄 app.py                 # Point d'entrée : Interface graphique et gestionnaire asynchrone
├── 📄 deploy_network.py      # Moteur métier : Fonctions Netmiko de déploiement et de diagnostic
├── 📄 inventaire.csv         # Source de vérité (Matériel, adresses IP, identifiants)
├── 📄 vlans.csv              # Plan de segmentation logique (Data et Voice)
├── 📄 trunks.csv             # Matrice des interconnexions de couche 2
├── 📄 access.csv             # Affectation des ports d'accès
├── 📄 hsrp_config.csv        # Paramètres de haute disponibilité (Passerelles virtuelles, priorités)
├── 📄 requirements.txt       # Liste des dépendances Python
└── 📄 README.md              # Documentation technique
```

## 🚀 Installation et Utilisation

1. **Clonage du projet :**
   ```bash
   git clone https://github.com/elasraouidev-ops/noc-dashboard-automation.git
   cd noc-dashboard-automation
   ```

2. **Installation des dépendances :**
   Il est recommandé d'utiliser un environnement virtuel (`venv`).
   ```bash
   pip install -r requirements.txt
   ```

3. **Configuration de l'environnement :**
   Éditez les fichiers CSV fournis pour adapter le plan d'adressage IP et les identifiants SSH à votre propre architecture (maquette GNS3 ou environnement physique).

4. **Exécution du serveur :**
   ```bash
   python3 app.py
   ```
   L'application sera accessible via votre navigateur à l'adresse `http://localhost:8282`.

## 🔒 Notes de Sécurité et Tolérance
*   **Anonymisation :** Les adresses IP publiques et les mots de passe présents dans les fichiers `.csv` de ce dépôt sont des valeurs génériques à des fins de démonstration.
*   **Latence de virtualisation :** Les scripts intègrent un paramètre de tolérance ajusté (`global_delay_factor: 4` sous Netmiko) spécifiquement conçu pour absorber les latences de calcul inhérentes à l'émulateur GNS3 lors de la génération des clés RSA ou du routage.
