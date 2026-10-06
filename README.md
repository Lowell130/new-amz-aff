# Product Discovery Engine

Piattaforma che aiuta l'utente a **scegliere cosa comprare** in base a uso, esperienza, priorità e budget.
Amazon è il canale di monetizzazione (link affiliati conformi), non il cuore dell'architettura.

Stack: **Nuxt 4 + Tailwind 4** (frontend SSR) · **FastAPI + PyMongo Async** (backend) · **MongoDB**.

> Stato: Fasi 1–8 della roadmap: Product Finder, Configuratore kit e AI Advisor (vedi `docs/ROADMAP.md`).
> Funziona **senza credenziali Amazon e senza MongoDB**: catalogo demo di 195 prodotti sintetici
> (scarpe, zaini, giacche, bastoncini, frontali; marchi inventati) e prezzi simulati.

## Avvio rapido (Windows / PowerShell)

Requisiti: Python 3.11+, Node.js 20+ (opzionale: Docker per MongoDB).

### 1. Backend

```powershell
cd backend
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
copy .env.example .env
uvicorn app.main:app --reload
```

- API: http://localhost:8000 · Documentazione interattiva: http://localhost:8000/docs
- Con `DATA_BACKEND=memory` (default) i dati demo vengono caricati in memoria a ogni avvio.

### 2. Frontend (in un secondo terminale)

```powershell
cd frontend
copy .env.example .env
npm install
npm run dev
```

Apri http://localhost:3000 → "Scarpe da trekking" (Product Finder), "Kit trekking" (Configuratore)
oppure "Consulente" (AI Advisor). L'Advisor funziona anche senza chiavi LLM (estrattore a regole); per
usare OpenAI o Gemini imposta `LLM_PROVIDER`, `LLM_API_KEY` e `LLM_MODEL` in `backend/.env`.

### 3. (Opzionale) MongoDB reale

```powershell
docker compose up -d          # dalla cartella principale
# in backend\.env:  DATA_BACKEND=mongo
cd backend
python -m app.seed.run        # crea indici e carica i dati demo
uvicorn app.main:app --reload
```

### Test

```powershell
cd backend
pytest
```

I test coprono: motore di scoring (20 profili diversi, nessun vincitore fisso, motivazioni basate sui dati),
flusso del questionario (domande condizionali, modifica risposte), link affiliati, cache con scadenza 24h,
funzionamento senza provider, configuratore (budget mai superato, incompatibilità, riproducibilità,
kit diversi al variare del budget, sostituzioni), AI Advisor (estrazione, una domanda alla volta,
fallback quando l'LLM fallisce, spiegazioni con prezzi inventati scartate, nessun testo utente salvato),
API end-to-end.

## Struttura

```
backend/app
  api/            endpoint FastAPI + schemi di risposta
  core/           configurazione (.env) e composizione dipendenze
  db/             connessione PyMongo Async + indici (TTL inclusi)
  models/         modelli di dominio (prodotto, finder, eventi)
  repositories/   accesso dati: MongoDB e in-memory
  providers/      ProductProvider: Mock (attivo) e Amazon Creators (Fase 11)
  scoring/        motore di scoring, logica questionario, selezione risultati, configuratore
  services/       finder, configuratore, advisor, dati prodotto/cache, AffiliateLinkService
  ai/             LLM: interfaccia, provider OpenAI/Gemini, estrazione e spiegazioni dell'Advisor
  seed/           dataset demo trekking (finder + kit)
frontend/app
  pages/          /, /trova/[slug], /configura/[slug], /consulente, /come-scegliere/[slug], informativa
  components/     finder/*, configurator/*, advisor/*, recommendation/*, ProductPriceCta, AffiliateDisclosure
  composables/    useApi, useFinder, useConfigurator, useAdvisor, useTrack
```

## Regole di conformità già implementate

- Link Amazon costruiti **solo** da `AffiliateLinkService`, diretti ad Amazon (nessun redirect `/go/`), `rel="sponsored"`.
- Prezzo, disponibilità e link immagine vivono solo negli **snapshot con scadenza ≤ 24h** (indice TTL in MongoDB);
  l'ASIN è l'unico dato Amazon conservato in modo permanente.
- Il prezzo è mostrato solo se lo snapshot è valido, con **data e ora di aggiornamento** e l'avviso che può variare.
- Se il provider non risponde il sito funziona comunque, senza prezzi.
- Disclosure affiliato nel footer, vicino ai pulsanti e in una pagina dedicata.
- I risultati personali (`/trova/...?s=`, `/configura/...?c=`) sono `noindex`; tracking anonimo con whitelist dei campi.
- AI Advisor: i prodotti li scelgono sempre i motori deterministici; il testo dei messaggi non viene salvato.

Verifica comunque i requisiti aggiornati sulle pagine ufficiali del Programma Affiliazione Amazon prima del lancio.
