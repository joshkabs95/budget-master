from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .engine import ForecastEngine
from .budget_projector import BudgetProjector


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def budget_forecast(request):
    horizon = min(int(request.query_params.get('months', 6)), 12)
    engine = ForecastEngine(request.user)
    projector = BudgetProjector(request.user, engine)

    # Real history (chronological)
    raw_history = engine.monthly_history(6)
    history_out = []
    for h in reversed(raw_history):
        income = h['income']
        savings = h['savings']
        history_out.append({
            'month': h['month'],
            'is_forecast': False,
            'income': income,
            'expenses': h['expenses'],
            'savings': savings,
            'net': h['net'],
            'savings_pct': round(savings / income * 100 if income else 0, 1),
        })

    data = projector.project_buckets(horizon)

    return Response({
        'history': history_out,
        **data,
    })
