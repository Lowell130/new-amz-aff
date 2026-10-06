# Roadmap

| Fase | Contenuto | Stato |
|---|---|---|
| 1 | Architettura, struttura repository, README, configurazione | ✅ |
| 2 | Modello dati MongoDB, indici (TTL), dataset demo 120 prodotti | ✅ |
| 3 | FastAPI, repository (Mongo + memoria), servizi | ✅ |
| 4 | MockProductProvider | ✅ |
| 5 | Motore di scoring con spiegazioni | ✅ |
| 6 | Product Finder (API + wizard Nuxt + pagine SEO) | ✅ |
| 7 | Configurator (setup completo entro budget, compatibilità) | ⏳ |
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

## Prompt per la prossima fase (da dare all'agente di sviluppo)

> Leggi `README.md`, `docs/ROADMAP.md` e il codice in `backend/app`. Implementa SOLO la **Fase 7 – Configurator**,
> riusando `ScoringEngine`, `ProductDataService` e `AffiliateLinkService` senza duplicarli.
> Aggiungi: modello `ConfigurationTemplate` (categorie obbligatorie/opzionali, vincoli, dipendenze, pesi),
> sessioni di configurazione, algoritmo che sceglie un prodotto per categoria massimizzando il punteggio
> entro il budget (mai oltre, salvo richiesta), alternative upgrade/downgrade per ogni componente, totale e
> budget residuo calcolati solo su prezzi validi. Estendi il seed con un template "Kit trekking" (scarpe,
> zaino, bastoncini, giacca, frontale) e ~80 prodotti demo per le nuove categorie. Aggiungi test che
> verifichino: rispetto del budget, incompatibilità, riproducibilità, configurazioni diverse al variare del
> budget. Frontend: pagina `/configura/[slug]` con riepilogo budget. Non procedere oltre la Fase 7.
