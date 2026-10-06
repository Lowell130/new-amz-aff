const eur = new Intl.NumberFormat('it-IT', { style: 'currency', currency: 'EUR' })
const dt = new Intl.DateTimeFormat('it-IT', { dateStyle: 'short', timeStyle: 'short', timeZone: 'Europe/Rome' })

export function formatPrice(amount: number, currency = 'EUR') {
  return currency === 'EUR' ? eur.format(amount) : `${amount.toFixed(2)} ${currency}`
}

export function formatDateTime(iso: string) {
  return dt.format(new Date(iso))
}

const VALUE_LABELS: Record<string, Record<string, string>> = {
  cut: { low: 'Basso', mid: 'Medio', high: 'Alto' },
  crampon: { none: 'No', semi: 'Semi-automatici', auto: 'Automatici' },
}

export function formatAttr(key: string, value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'boolean') return value ? 'Sì' : 'No'
  const mapped = VALUE_LABELS[key]?.[String(value)]
  if (mapped) return mapped
  if (['grip', 'comfort', 'durability'].includes(key)) return `${value}/5`
  return String(value)
}
