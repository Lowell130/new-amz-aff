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

// ------------------------------------------------------------------ configuratore
export interface ComponentOut {
  key: string
  label: string
  required: boolean
  why?: string | null
  attribute_labels: Record<string, string>
}

export interface ConfiguratorSummary {
  slug: string
  title: string
  short_description: string
  components: number
}

export interface ConfiguratorDetail {
  slug: string
  title: string
  short_description: string
  seo: { title: string; description: string; h1: string; intro: string }
  inputs: QuestionOut[]
  components: ComponentOut[]
}

export interface AlternativeOut {
  product: ProductCard
  score: number
  price_delta: number | null
  price_is_estimate: boolean
}

export interface ConfigItemOut {
  component_key: string
  label: string
  required: boolean
  why: string | null
  score: number
  confidence: 'alta' | 'media' | 'bassa'
  explain: Explainability
  product: ProductCard
  upgrade: AlternativeOut | null
  downgrade: AlternativeOut | null
}

export interface ConfigurationOut {
  session_id: string
  template_slug: string
  budget: number
  profile: ResultOut['profile']
  items: ConfigItemOut[]
  skipped: { component_key: string; label: string; reason: string }[]
  total_valid: number
  missing_prices: number
  residual: number | null
  over_budget: boolean
  generated_at: string
  answers: Record<string, unknown>
  include_optional: string[] | null
}

// ---------------------------------------------------------------------- advisor
export interface QuickReply {
  question_id: string
  value: unknown
  label: string
}

export interface AdvisorReply {
  session_id: string
  text: string
  text_source: 'llm' | 'template'
  quick_replies: QuickReply[]
  understood: string[]
  target: { kind: 'finder' | 'configurator'; slug: string; title: string } | null
  finder_result: ResultOut | null
  configuration: ConfigurationOut | null
  open_url: string | null
  open_label: string | null
}
