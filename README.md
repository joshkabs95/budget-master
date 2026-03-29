# Budget Master

Application web fullstack de gestion des finances personnelles — règle 50/30/20 adaptative, enveloppes YNAB, objectifs d'épargne, projection de trésorerie et réconciliation bancaire.

---

## Stack technique

| Couche | Technologies |
|--------|-------------|
| Backend | Django 4 · Django REST Framework · JWT (SimpleJWT) · PostgreSQL |
| Frontend | React 18 · TypeScript · Vite · CSS Modules |
| Infra | Docker Compose · Nginx · Gunicorn · Prometheus · Grafana |

---

## Démarrage rapide (Docker)

```bash
git clone <repo>
cd budget-master
docker compose up -d
```

Accès : **http://localhost**
Compte de démo : `josue` / `<mot de passe>`

---

## Lancement en développement local

### Backend

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver      # http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173
```

---

## Variables d'environnement

Créer `backend/.env` :

```env
SECRET_KEY=change-me-in-production
DEBUG=True
DATABASE_URL=postgres://budgetmaster:budgetmaster@localhost:5432/budgetmaster
```

---

## Architecture

```
budget-master/
├── backend/
│   ├── config/               # settings, urls, celery, wsgi
│   └── apps/
│       ├── users/            # Auth JWT + profil utilisateur
│       ├── categories/       # Catégories + enveloppes YNAB (CategoryBudget)
│       ├── transactions/     # CRUD · stats 50/30/20 · import CSV · insights
│       ├── savings/          # Comptes épargne · règle adaptative · wants scores
│       ├── goals/            # Objectifs financiers + projection cash flow
│       ├── forecasting/      # Moteur de prévision · WantsAllocator · BudgetProjector
│       ├── notifications/    # Notifications in-app
│       └── reconciliation/   # Réconciliation bancaire 3 passes
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Dashboard/    # KPIs · répartition · projection trésorerie · insights
│       │   ├── Transactions/ # Liste · filtres · édition inline · import/export
│       │   ├── Budget/       # Règle 50/30/20 · enveloppes · priorités envies · simulation
│       │   ├── Savings/      # Comptes épargne (onglet) · Objectifs (onglet)
│       │   ├── Analytics/    # Graphiques historiques
│       │   └── Reconciliation/ # Réconciliation bancaire CSV
│       ├── components/       # TransactionRow · KPICard · ProgressBar · Modal · ForecastChart
│       ├── services/         # Axios + intercepteurs JWT auto-refresh
│       ├── context/          # AuthContext
│       ├── router/           # Routes protégées
│       └── types/            # Interfaces TypeScript
├── nginx/                    # Config reverse proxy + build frontend
├── grafana/                  # Dashboards monitoring
└── docker-compose.yml
```

---

## Fonctionnalités

### Règle 50/30/20
- Calcul automatique des ratios Besoins / Envies / Épargne sur le mois courant
- Affichage du montant en euros + pourcentage par bucket
- Barre de répartition segmentée visuelle

### Plan de compensation
- Détecte quand l'épargne est en dessous de la cible
- Calcule les réductions nécessaires sur les Envies et les Besoins
- Suggère les catégories à réduire en priorité (par montant dépensé)
- Étalement sur 1 à 3 mois selon la sévérité

### Enveloppes YNAB
- Une enveloppe par catégorie `wants` par mois
- Auto-initialisation depuis le mois précédent avec report du reliquat
- Édition inline du budget alloué
- Ajout / remboursement de dépense directement depuis la carte
- Barre de progression colorée : vert (<75%) · orange (75–100%) · rouge (>100%)
- Coaching automatique selon priorité vs consommation réelle

### Priorités Envies
- Score de priorité 1–5 par catégorie wants
- Allocation proportionnelle du budget wants selon les scores
- Messages coaching :
  - Priorité élevée + faible consommation → sous-consommation
  - Priorité basse + proche du plafond → alerte dépassement d'intention
  - Dépassement 100% → alerte systématique

### Simulation "What If"
- Réduction simulée par catégorie
- Épargne supplémentaire simulée
- Comparaison avant/après (ratios + risque)

### Projection de trésorerie
- Historique réel 6 mois + projections 6 mois
- Moteur pondéré (weighted average + tendance)
- Confiance calculée selon le nombre de mois d'historique

### Réconciliation bancaire
- Import CSV format banques françaises
- Matching 3 passes : exact → fuzzy (Jaccard) → manuel
- Session par mois, clôture possible

---

## API principale

```
POST  /api/auth/register/
POST  /api/auth/login/
POST  /api/auth/refresh/

GET/POST/PUT/DELETE  /api/categories/
GET/POST/PUT/DELETE  /api/transactions/
GET   /api/transactions/stats/       # agrégats + règle 50/30/20
GET   /api/transactions/insights/    # insights comportementaux

GET/POST/PUT/DELETE  /api/savings/accounts/
GET/POST  /api/savings/rule/
GET   /api/savings/compensation/     # plan de compensation

GET/POST/PUT/DELETE  /api/goals/
POST  /api/goals/:id/contribute/

GET   /api/envelopes/                # enveloppes YNAB du mois
POST  /api/envelopes/upsert/         # créer ou mettre à jour une enveloppe

GET   /api/forecast/budget/          # projection 6 mois
POST  /api/forecast/simulate/        # simulation what-if
GET/POST /api/forecast/wants/        # priorités envies + coaching

POST  /api/reconciliation/start/     # démarrer une session
POST  /api/reconciliation/:id/match_manual/
POST  /api/reconciliation/:id/close/
```

---

## Moteur de compensation — logique

| Écart épargne | Sévérité | Action |
|--------------|----------|--------|
| < 3% | Yellow | Réduire Envies légèrement |
| 3–8% | Orange | Réduire Envies fortement |
| > 8% | Red | Réduire Envies + Besoins |
| > 15% | Critical | Problème structurel |

**Règle fondamentale :** la cible d'épargne n'est jamais réduite. Les Envies sont compressées en premier, les Besoins en dernier recours avec avertissement "zone de vigilance".
