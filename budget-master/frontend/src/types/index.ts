export interface User {
  id: number;
  email: string;
  username: string;
  first_name: string;
  last_name: string;
  avatar?: string;
  currency?: string;
}

export interface Category {
  id: number;
  name: string;
  icon: string;
  color: string;
  type: 'income' | 'expense';
  budget_limit: number | null;
  rule_bucket: 'needs' | 'wants' | 'savings';
  spent_this_month?: number;
}

export interface Transaction {
  id: number;
  category: Category | null;
  category_detail?: Category | null;
  savings_account?: number | null;
  savings_account_detail?: SavingsAccount | null;
  amount: number;
  label: string;
  date: string;
  type: 'income' | 'expense' | 'saving';
  source: 'manual' | 'import';
  import_hash?: string;
  created_at: string;
}

export interface SavingsAccount {
  id: number;
  name: string;
  balance: number;
  target?: number | null;
  interest_rate?: number | null;
  color: string;
  icon: string;
  created_at: string;
  progress_pct?: number | null;
}

export interface SavingsRule {
  id: number;
  savings_target: number;
  needs_target: number;
  wants_target: number;
  savings_tolerance: number;
  needs_tolerance: number;
  wants_tolerance: number;
  savings_floor: number;
  needs_floor: number;
  wants_floor: number;
  compensation_order: string[];
  window_months: number;
  catchup_max_months: number;
  mode: 'strict' | 'adaptive';
  active: boolean;
}

export interface CompensationStep {
  lever: 'wants' | 'needs';
  cut: number;
  new_target: number;
  warning?: string;
  monthly_euros?: number;
}

export interface CompensationPlan {
  status?: string;
  plan?: {
    steps: CompensationStep[];
    remaining_gap: number;
    uncoverable_gap: number;
    severity: 'green' | 'yellow' | 'orange' | 'red' | 'critical';
    catchup_months: number;
    monthly_amounts: CompensationStep[];
    suggestions: Array<{ category: string; avg_monthly: number; suggestion: string }>;
  } | null;
  current_rates?: CurrentRates;
  rule?: SavingsRule;
}

export interface CurrentRates {
  savings: number;
  needs: number;
  wants: number;
  total_income?: number;
  savings_amount?: number;
  needs_amount?: number;
  wants_amount?: number;
}

export interface Goal {
  id: number;
  name: string;
  type: 'savings' | 'expense';
  target_amount: number;
  current_amount: number;
  deadline: string;
  icon: string;
  color: string;
  horizon: 'short' | 'medium' | 'long';
  savings_account?: number | null;
  progress_pct: number;
  days_remaining: number;
  created_at: string;
}

export interface Document {
  id: number;
  file: string;
  file_type: 'pdf' | 'csv';
  status: 'pending' | 'imported';
  imported_at?: string;
  transaction_count: number;
  created_at: string;
}

export interface FinancialScore {
  score: number;
  budget_respect: number;
  savings_respect: number;
  goals_progress: number;
  month: string;
}

export interface MonthlyStats {
  total_income: number;
  total_expenses: number;
  total_savings: number;
  balance: number;
  savings_rate: number;
  by_category: Array<{
    id?: number;
    category: string;
    name?: string;
    amount: number;
    percentage: number;
    color: string;
    icon?: string;
    budget_limit?: number | null;
    rule_bucket?: string;
  }>;
  trend: Array<{
    month: string;
    label?: string;
    income: number;
    expenses: number;
    savings: number;
  }>;
}

export interface Insight {
  type: 'warning' | 'success' | 'alert' | 'info';
  title: string;
  message: string;
  icon: string;
  data?: Record<string, unknown>;
  score?: number;
}

export interface SavingsSummary {
  total_balance: number;
  total_target: number;
  accounts_count: number;
  current_rates: CurrentRates;
  monthly_summary: Array<{
    month: string;
    label: string;
    income: number;
    savings: number;
    rate: number;
  }>;
  heatmap: Array<{
    date: string;
    amount: number;
  }>;
}

export interface CashFlowMonth {
  month: string;
  label: string;
  income: number;
  expenses: number;
  savings: number;
  net: number;
  balance: number;
  negative: boolean;
  goals: Array<{
    id: number;
    name: string;
    icon: string;
    color: string;
    amount: number;
    type: string;
  }>;
  goal_impact: number;
}
