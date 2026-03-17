# Budget Master

Application web fullstack de gestion des finances personnelles avec règle 50/30/20 adaptative, suivi multi-supports de l'épargne, objectifs financiers et projection de trésorerie.

---

## Prérequis

- Python 3.10+
- Node.js 18+
- npm ou yarn

---

## Lancement en développement

### Backend

```bash
cd backend
pip install -r requirements.txt
python3 manage.py migrate
python3 manage.py seed_data      # données de démo
python3 manage.py runserver      # http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

Compte de démo : **demo** / **demo1234**

---

## Variables d'environnement (optionnel)

Créer `backend/.env` :

```env
SECRET_KEY=change-me-in-production
DEBUG=True
```

---

## Architecture

```
budget-master/
├── backend/
│   ├── config/           # settings, urls, wsgi
│   ├── apps/
│   │   ├── users/        # Auth JWT + profil
│   │   ├── categories/   # Catégories + limites budget
│   │   ├── transactions/ # CRUD + stats + import + insights
│   │   ├── savings/      # Comptes épargne + règle adaptative
│   │   ├── goals/        # Objectifs + projection cash flow
│   │   └── documents/    # Upload + parsing PDF/CSV
│   └── manage.py
└── frontend/
    └── src/
        ├── pages/        # Dashboard, Transactions, Budget, Savings, Analytics, Goals, Auth
        ├── components/   # KPICard, ProgressBar, Modal, CompensationPlanCard, ...
        ├── services/     # Axios + intercepteurs JWT
        ├── context/      # AuthContext
        ├── router/       # Routes protégées
        └── types/        # Interfaces TypeScript
```

---

## Moteur de compensation 50/30/20

Le `AdaptiveRuleEngine` (`apps/savings/services/adaptive_rule.py`) applique une cascade de compensation lorsque le taux d'épargne réel est inférieur à la cible (20% par défaut) :

| Scénario | Épargne réelle | Gap | Action | Sévérité |
|----------|---------------|-----|--------|----------|
| A | 17% | 3% | Réduire Envies 33%→30% | Yellow |
| B | 12% | 8% | Réduire Envies 38%→30% | Orange |
| C | 8% | 12% | Réduire Envies + Besoins | Red |
| D | 2% | 18% | Problème structurel | Critical |

**Règle fondamentale :** l'épargne cible n'est jamais réduite. On compresse les Envies en premier, les Besoins en dernier recours.

En mode **adaptatif** (recommandé), l'évaluation se fait sur une fenêtre glissante de 3 mois (configurable) pour éviter les faux positifs sur un mois isolé.

---

## API

```
POST  /api/auth/register/
POST  /api/auth/login/
POST  /api/auth/refresh/

GET/POST/PUT/DELETE  /api/categories/
GET/POST/PUT/DELETE  /api/transactions/
GET  /api/transactions/stats/      # agrégats + règle 50/30/20
GET  /api/transactions/insights/   # insights comportementaux

GET/POST/PUT/DELETE  /api/savings/accounts/
GET/POST  /api/savings/rule/
GET  /api/savings/summary/
GET  /api/savings/compensation/    # plan AdaptiveRuleEngine

GET/POST/PUT/DELETE  /api/goals/
POST /api/goals/:id/contribute/
GET  /api/goals/cashflow/          # projection 24 mois

POST /api/documents/upload/
GET  /api/documents/:id/preview/
POST /api/documents/:id/import/
```

---

## Données de démo (seed_data)

- 40 transactions sur 2 mois (revenus, dépenses needs/wants, virements épargne)
- 2 comptes épargne : Livret A + PEL
- 1 règle adaptative 20% active
- 4 objectifs : 1 court / 1 moyen / 2 long terme
- **Scénario intentionnel :** épargne à ~14% → le moteur déclenche un plan Orange
