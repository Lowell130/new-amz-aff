export type QuestionType = 'single_choice' | 'multiple_choice' | 'range' | 'boolean' | 'number'

export interface OptionOut {
  value: string
  label: string
  hint?: string | null
}

export interface QuestionOut {
  id: string
  question: string
  help?: string | null
  type: QuestionType
  required: boolean
  options: OptionOut[]
  max_choices?: number | null
  min?: number | null
  max?: number | null
  step?: number | null
  unit?: string | null
  default?: unknown
}

export interface StepOut {
  session_id: string
  finder_slug: string
  done: boolean
  question: QuestionOut | null
  progress: { answered: number; total: number }
  answers: Record<string, unknown>
}

export interface Explainability {
  matched: string[]
  weak_matches: string[]
  missing_features: string[]
  penalties: string[]
  reasons: string[]
}

export interface OfferOut {
  price: number | null
  currency: string | null
  availability: string | null
  image_url: string | null
  fetched_at: string
  source: string
}

export interface ProductCard {
  id: string
  slug: string
  name: string
  brand: string
  asin: string
  is_demo: boolean
  attributes: Record<string, unknown>
  pros: string[]
  cons: string[]
  affiliate_url: string | null
  offer: OfferOut | null
}

export interface SlotOut {
  role: 'best_match' | 'cheaper' | 'premium' | 'alternative'
  label: string
  score: number
  confidence: 'alta' | 'media' | 'bassa'
  explain: Explainability
  product: ProductCard
}

export interface ResultOut {
  session_id: string
  finder_slug: string
  profile: {
    budget_max: number | null
    experience: string | null
    use_cases: string[]
    priorities: string[]
    requirements: string[]
  }
  slots: SlotOut[]
  considered: number
  excluded: number
  generated_at: string
  attribute_labels: Record<string, string>
}

export interface FinderSummary {
  slug: string
  title: string
  short_description: string
  questions: number
}

export interface FinderDetail extends FinderSummary {
  seo: {
    title: string
    description: string
    h1: string
    intro: string
    guide_sections: { title: string; body: string }[]
    faq: { q: string; a: string }[]
  }
  attribute_labels: Record<string, string>
  use_case_labels: Record<string, string>
}
