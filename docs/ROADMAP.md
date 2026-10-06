# Roadmap

| Fase | Contenuto | Stato |
|---|---|---|
| 1 | Architettura, struttura repository, README, configurazione | ✅ |
| 2 | Modello dati MongoDB, indici (TTL), dataset demo 120 prodotti | ✅ |
| 3 | FastAPI, repository (Mongo + memoria), servizi | ✅ |
| 4 | MockProductProvider | ✅ |
| 5 | Motore di scoring con spiegazioni | ✅ |
| 6 | Product Finder (API + wizard Nuxt + pagine SEO) | ✅ |
| 7 | Configurator (kit completo entro budget, incompatibilità, upgrade/downgrade) | ✅ |
| 8 | AI Advisor (estrazione requisiti → motore deterministico → spiegazione LLM) | ⏳ |
| 9 | SEO engine (sitemap, pagine use-case, index/noindex per tipo) | ⏳ |
| 10 | AffiliateLinkService | ✅ (anticipata) |
| 11 | Adapter Amazon Creators API | ⏳ (stub pronto in `providers/amazon_creators.py`) |
| 12 | Analytics (funnel, dashboard) | 🟡 eventi già registrati |
| 13 | Admin dashboard | ⏳ (`/api/admin/stats` protetto da token) |
| 14 | Testing + hardening produzione | 🟡 |

## Scelte fatte rispetto al prompt originale

- **Domande del finder dentro il documento `finders`** invece che in collection separate
  (`finder_questions`, `finder_options`): vengono sempre lette insieme, quindi in MongoDB un unico
  documento è più semplice e veloce. Il risultato è salvato dentro `finder_sessions`.
- **`reference_price`**: stima editoriale usata solo per il ranking quando il prezzo Amazon non è
  disponibile; non viene mai mostrata come prezzo.
- **Backend `memory`**: permette di provare tutto senza MongoDB; in produzione usare `DATA_BACKEND=mongo`.
- Collection `products` per categoria caricata interamente in memoria per lo scoring: va bene per
  nicchie da centinaia/poche migliaia di prodotti. Oltre, prefiltrare in MongoDB (use_cases, prezzo).

## Come funziona il Configuratore (Fase 7)

- Le domande del template usano lo stesso formato del Finder e producono lo stesso `UserProfile`.
- Per ogni componente il profilo viene ritagliato: solo i requisiti pertinenti (`requirement_attrs`,
  es. "impermeabile" vale per scarpe e giacca, "coprizaino" per lo zaino) e le priorità pertinenti.
  Le priorità scelte dall'utente pesano il doppio delle priorità di qualità di base (`default_priorities`).
- Per ogni componente si tiene la frontiera prezzo/qualità, poi una ricerca branch-and-bound **esatta**
  sceglie la combinazione di valore massimo (`peso componente x punteggio`) entro il budget, rispettando
  le incompatibilità (`incompatible_with` ↔ `tags`, es. gilet da corsa ↔ bastoncini telescopici).
- **Prima l'essenziale:** gli opzionali entrano solo se gli essenziali restano almeno al 92% della qualità
  massima ottenibile con lo stesso budget (`ESSENTIALS_MIN_SHARE`).
- Il budget non viene mai superato dal sistema; può superarlo solo l'utente con una sostituzione esplicita
  (upgrade), e in quel caso viene segnalato.
- Totale e budget residuo mostrati all'utente sono calcolati **solo sui prezzi aggiornati**; se un prezzo
  manca, il residuo non viene mostrato.

Collection nuove: `configuration_templates`, `configuration_sessions` (TTL 30 giorni).
Endpoint: `GET /api/configurators`, `GET /api/configurators/{slug}`, `POST /api/configurators/{slug}/build`,
`GET /api/configuration/{id}`, `POST /api/configuration/{id}/swap`. Pagina: `/configura/kit-trekking`.

## Prompt per la prossima fase (da dare all'agente di sviluppo)

> Leggi `README.md`, `docs/ROADMAP.md` e il codice in `backend/app`. Implementa SOLO la **Fase 8 – AI Advisor**.
> Flusso obbligatorio: messaggio utente → estrazione requisiti strutturati (intent, categoria, budget, esperienza,
> use case, preferenze, vincoli, informazioni mancanti) tramite `LLMProvider` con output JSON validato da Pydantic
> → se mancano dati fondamentali, UNA domanda mirata alla volta → mappatura dei requisiti sulle risposte del
> Finder o del Configuratore esistenti → `ScoringEngine` / `ConfigurationEngine` (i prodotti li scelgono
> SEMPRE loro, mai l'LLM) → spiegazione LLM basata solo sui dati strutturati passati. Implementa un provider
> LLM reale (OpenAI o Gemini, configurabile da .env) e un `FakeLLMProvider` deterministico per test e sviluppo.
> Sessioni advisor con solo il contesto utile (nessun testo personale non necessario nei log). Endpoint
> `POST /api/advisor/session`, `POST /api/advisor/message`; pulsante "Apri nel configuratore" che porta a
> `/configura/...` già compilato. Test: budget interpretato correttamente, categoria corretta, nessun dato
> inventato (prezzi/specifiche nel testo devono provenire dai dati passati), riproducibilità con il fake.
> Frontend: `/consulente` con chat (AdvisorChat, AdvisorMessage, AdvisorInput, AdvisorQuickReply). Non procedere
> oltre la Fase 8.
