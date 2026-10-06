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
| 8 | AI Advisor (estrazione requisiti → motore deterministico → spiegazione LLM) | ✅ |
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

## Come funziona l'AI Advisor (Fase 8)

1. **Estrazione**: il messaggio viene trasformato nelle risposte alle domande dei Finder/Configuratori
   esistenti. Lo schema JSON per l'LLM è **generato dalle domande stesse** (nessun campo inventato);
   ogni valore viene poi rivalidato e quelli non ammessi vengono scartati.
   Senza LLM (`LLM_PROVIDER=none`) o se l'LLM fallisce, si usa l'**estrattore a regole**: parole chiave
   editoriali definite sulle opzioni (`keywords`) e regex per il budget.
2. **Strumento**: Finder o Configuratore, scelto dall'LLM/regole o dedotto dalle risposte (es. "ramponi"
   esiste solo nel Finder). Se non è chiaro, si chiede con risposte rapide.
3. **Domande**: si chiedono solo le domande indispensabili (`advisor_key_questions`, di default uso e
   budget), **una alla volta**, con risposte rapide. Tutto ciò che l'utente ha già detto viene riusato.
4. **Scelta prodotti**: sempre `ScoringEngine` / `ConfigurationEngine`. Se il budget non basta per il kit,
   l'advisor dice quanto serve e propone budget alternativi.
5. **Spiegazione**: l'LLM riceve solo i dati strutturati del risultato. Il testo viene **verificato**:
   se cita importi in euro che non esistono nei dati, viene scartato e si usa il testo a modello.
6. **Privacy**: il testo dei messaggi non viene salvato (né in sessione né nei log); la sessione
   (`advisor_sessions`, TTL 30 giorni) contiene solo lo stato strutturato.

Configurazione LLM in `backend/.env`: `LLM_PROVIDER=openai|gemini`, `LLM_API_KEY`, `LLM_MODEL`
(nome del modello obbligatorio: va preso dalla documentazione del provider). I provider reali sono
implementati via HTTP in `app/ai/providers.py` ma **non sono ancora stati provati con chiavi reali**.

Endpoint: `POST /api/advisor/session`, `POST /api/advisor/message`. Pagina: `/consulente`.
Dall'advisor si apre il risultato nel Finder (`/trova/...?s=`) o nel Configuratore già compilato
(`/configura/...?c=`).

## Prompt per la prossima fase (da dare all'agente di sviluppo)

> Leggi `README.md`, `docs/ROADMAP.md` e il codice. Implementa SOLO la **Fase 9 – SEO engine**.
> Obiettivi: `sitemap.xml` dinamica (solo pagine indicizzabili: home, /trova/*, /configura/*, /come-scegliere/*,
> /consulente e le nuove pagine use-case), regole index/noindex centralizzate per tipo di pagina (mai i risultati
> personali `?s=`/`?c=`), nuove pagine use-case generate SOLO quando esiste un intento reale con dati
> differenziati (es. `/migliori/scarpe-trekking/principianti`, `/migliori/scarpe-trekking/sotto-100-euro`):
> ogni pagina deve avere testo introduttivo editoriale, selezione calcolata dallo ScoringEngine con un profilo
> fisso, FAQ, dati strutturati (ItemList, BreadcrumbList, FAQPage), internal linking verso finder/configuratore e
> guide; soglia minima di prodotti e controllo anti-duplicazione (se due pagine darebbero la stessa selezione, se
> ne pubblica una sola). Definisci le pagine in una collection `seo_pages` (con stato draft/published) invece che
> nel codice. Test: nessuna pagina con meno di N prodotti, nessun duplicato, sitemap senza URL noindex.
> Non procedere oltre la Fase 9.
