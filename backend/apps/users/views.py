import json
from datetime import date
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.http import HttpResponse
from .serializers import RegisterSerializer, UserSerializer
from django.contrib.auth import get_user_model

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

class ProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        current = request.data.get('current_password', '')
        new_pw  = request.data.get('new_password', '')
        if not current or not new_pw:
            return Response({'error': 'Champs requis.'}, status=status.HTTP_400_BAD_REQUEST)
        if not request.user.check_password(current):
            return Response({'error': 'Mot de passe actuel incorrect.'}, status=status.HTTP_400_BAD_REQUEST)
        if len(new_pw) < 8:
            return Response({'error': 'Le nouveau mot de passe doit faire au moins 8 caractères.'}, status=status.HTTP_400_BAD_REQUEST)
        request.user.set_password(new_pw)
        request.user.save()
        return Response({'status': 'ok'})


class CompleteOnboardingView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        """
        Accepts: { monthly_income, needs_pct, wants_pct, savings_pct, first_category }
        Creates a SavingsRule + optionally a Category, marks onboarding done.
        """
        from apps.savings.models import SavingsRule
        from apps.categories.models import Category

        user = request.user
        data = request.data

        # Save 50/30/20 rule
        needs   = float(data.get('needs_pct',   50))
        wants   = float(data.get('wants_pct',   30))
        savings = float(data.get('savings_pct', 20))
        SavingsRule.objects.update_or_create(
            user=user,
            defaults={
                'needs_target':      needs,
                'wants_target':      wants,
                'savings_target':    savings,
                'needs_tolerance':   5,
                'wants_tolerance':   5,
                'savings_tolerance': 5,
                'mode':              'adaptive',
                'window_months':     3,
                'catchup_max_months': 3,
            }
        )

        # Create first category if provided
        cat_name = data.get('first_category', '').strip()
        if cat_name:
            Category.objects.get_or_create(
                user=user,
                name=cat_name,
                defaults={'icon': '📦', 'color': '#60A5FA', 'type': 'expense', 'rule_bucket': 'needs'}
            )

        user.onboarding_done = True
        user.save(update_fields=['onboarding_done'])

        return Response({'status': 'ok'})


class ExportBackupView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.transactions.models import Transaction
        from apps.categories.models import Category
        from apps.savings.models import SavingsAccount, SavingsRule
        from apps.goals.models import Goal

        user = request.user

        transactions = list(Transaction.objects.filter(user=user).values(
            'id', 'label', 'amount', 'type', 'date', 'notes',
            'category__name', 'is_recurring', 'recurrence_frequency'
        ))

        categories = list(Category.objects.filter(user=user).values(
            'id', 'name', 'icon', 'color', 'type', 'rule_bucket', 'budget_limit'
        ))

        savings = list(SavingsAccount.objects.filter(user=user).values(
            'id', 'name', 'balance', 'target_amount', 'color', 'icon'
        ))

        goals = list(Goal.objects.filter(user=user).values(
            'id', 'name', 'type', 'target_amount', 'current_amount',
            'deadline', 'icon', 'color'
        ))

        payload = {
            'exported_at': date.today().isoformat(),
            'username': user.username,
            'transactions': transactions,
            'categories': categories,
            'savings_accounts': savings,
            'goals': goals,
        }

        content = json.dumps(payload, indent=2, default=str)
        filename = f"budget_backup_{date.today().isoformat()}.json"
        response = HttpResponse(content, content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
