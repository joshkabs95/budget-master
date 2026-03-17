import {
  ComposedChart, Line, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine, Legend, CartesianGrid,
} from 'recharts'

interface DataPoint {
  month: string
  income?: number
  expenses?: number
  income_f?: number
  expenses_f?: number
  isToday?: boolean
}

interface Props {
  history: any[]
  forecast: any[]
  height?: number
}

export default function ForecastChart({ history, forecast, height = 240 }: Props) {
  const today = new Date()
  const currentMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}`

  // Build unified dataset: real months then forecast months
  // Last real point = connection bridge (appears in both series)
  const lastReal = history[history.length - 1]

  const data: DataPoint[] = [
    ...history.map(h => ({
      month: h.month.slice(5),
      income: h.income,
      expenses: h.expenses,
      income_f: undefined,
      expenses_f: undefined,
    })),
    // Bridge: last real month also starts the dashed series
    ...(lastReal ? [{
      month: lastReal.month.slice(5),
      income: undefined,
      expenses: undefined,
      income_f: lastReal.income,
      expenses_f: lastReal.expenses,
      isToday: true,
    }] : []),
    ...forecast.map(f => ({
      month: f.month.slice(5),
      income: undefined,
      expenses: undefined,
      income_f: f.income,
      expenses_f: f.needs + f.wants,
    })),
  ]

  const todayLabel = currentMonth.slice(5)
  const tooltipStyle = {
    background: 'var(--bg-overlay)',
    border: '1px solid var(--border-hover)',
    borderRadius: 8, fontSize: 12,
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <ComposedChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" vertical={false} />
        <XAxis dataKey="month" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
        <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} width={44} />
        <Tooltip contentStyle={tooltipStyle} formatter={(v: any) => v != null ? `${Number(v).toFixed(0)} €` : '–'} />
        <Legend iconType="circle" iconSize={7} wrapperStyle={{ fontSize: '0.72rem' }} />

        {/* Real data — solid */}
        <Line name="Revenus réels"  dataKey="income"   stroke="var(--accent-green)" strokeWidth={2} dot={false} connectNulls={false} />
        <Line name="Dépenses réelles" dataKey="expenses" stroke="var(--accent-red)"   strokeWidth={2} dot={false} connectNulls={false} />

        {/* Forecast — dashed */}
        <Line name="Revenus estimés"  dataKey="income_f"   stroke="var(--accent-green)" strokeWidth={1.5} strokeDasharray="5 4" dot={false} connectNulls={false} opacity={0.55} />
        <Line name="Dépenses estimées" dataKey="expenses_f" stroke="var(--accent-red)"   strokeWidth={1.5} strokeDasharray="5 4" dot={false} connectNulls={false} opacity={0.55} />

        {/* Today reference */}
        <ReferenceLine x={todayLabel} stroke="var(--accent)" strokeDasharray="3 3" strokeWidth={1} label={{ value: 'auj.', position: 'top', fill: 'var(--accent)', fontSize: 10 }} />
      </ComposedChart>
    </ResponsiveContainer>
  )
}
