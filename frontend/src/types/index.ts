export interface User {
  id: number
  username: string
  email: string
  locale: string
  currency: string
}

export interface AuthTokens {
  access: string
  refresh: string
}

export interface Category {
  id: number
  name: string
  icon: string
  color: string
  type: 'income' | 'expense'
  budget_limit: number | null
  rule_bucket: 'needs' | 'wants' | 'savings'
  created_at: string
}

export interface Transaction {
  id: number
  category: number | null
  category_detail: Category | null
  savings_account: number | null
  amount: string
  label: string
  date: string
  type: 'income' | 'expense' | 'saving'
  source: 'manual' | 'import'
  import_hash: string | null
  created_at: string
}

export interface SavingsAccount {
  id: number
  name: string
  balance: string
  target: string | null
  interest_rate: string | null
  color: string
  icon: string
  created_at: string
}

export interface SavingsRule {
  id: number
  savings_target: string
  needs_target: string
  wants_target: string
  savings_tolerance: string
  needs_tolerance: string
  wants_tolerance: string
  savings_floor: string
  needs_floor: string
  wants_floor: string
  compensation_order: string[]
  window_months: number
  catchup_max_months: number
  mode: 'strict' | 'adaptive'
  active: boolean
  created_at: string
}

export interface CompensationStep {
  lever: 'wants' | 'needs'
  cut: number
  new_target: number
  monthly_euros?: number
  warning?: string
}

export interface CompensationPlan {
  steps: CompensationStep[]
  remaining_gap: number
  uncoverable_gap: number
  severity: 'yellow' | 'orange' | 'red' | 'critical'
  catchup_months: number
  monthly_amounts: CompensationStep[]
  suggestions: Array<{ category: string; icon: string; monthly_avg: number; suggestion: string }>
  savings_gap: number
  message: string
}

export interface CompensationResult {
  status: 'green' | 'yellow' | 'orange' | 'red' | 'critical'
  severity: string
  plan: CompensationPlan | null
  current_rates: { savings: number; needs: number; wants: number }
  targets: { savings: number; needs: number; wants: number }
}

export interface Goal {
  id: number
  savings_account: number | null
  name: string
  type: 'savings' | 'expense'
  target_amount: string
  current_amount: string
  deadline: string
  icon: string
  color: string
  horizon: 'short' | 'medium' | 'long'
  progress: number
  monthly_required: number
  created_at: string
}

export interface Document {
  id: number
  file: string
  file_type: 'pdf' | 'csv'
  status: 'pending' | 'imported' | 'error'
  imported_at: string | null
  transaction_count: number
  created_at: string
}

export interface FinancialScore {
  total: number
  budget_score: number
  savings_score: number
  goals_score: number
  month: string
}

export interface TransactionStats {
  month: string
  income: number
  expenses: number
  savings: number
  balance: number
  savings_rate: number
  rule_503020: { needs: number; wants: number; savings: number }
  by_category: Array<{
    category__id: number
    category__name: string
    category__icon: string
    category__color: string
    category__rule_bucket: string
    category__budget_limit: number | null
    total: number
  }>
  trend: Array<{ month: string; type: string; total: number }>
}

export interface SavingsSummary {
  month: string
  income: number
  saved: number
  savings_rate: number
  target_rate: number
  avg_rate_6m: number
  accounts: Array<{
    id: number
    name: string
    icon: string
    color: string
    balance: number
    target: number | null
    interest_rate: number | null
    month_contribution: number
    progress: number | null
  }>
  total_balance: number
}

export interface CashFlowMonth {
  month: string
  projected_income: number
  projected_expenses: number
  projected_savings: number
  net: number
  planned_expenses: Array<{ goal_id: number; goal_name: string; goal_icon: string; amount: number }>
  total_planned: number
  running_balance: number
  alert: boolean
}

export interface Insight {
  type: string
  severity: 'green' | 'orange' | 'red'
  message: string
  category?: string
  streak?: number
}

export interface ParsedTransaction {
  date: string
  amount: number
  label: string
  type: 'income' | 'expense'
  suggested_category: string
  confidence: number
  import_hash: string
  is_duplicate: boolean
  category?: string
}
