import tailwindcss from '@tailwindcss/vite'

// Valori sovrascrivibili con variabili d'ambiente:
// NUXT_API_BASE_SERVER, NUXT_PUBLIC_API_BASE, NUXT_PUBLIC_SITE_URL, NUXT_PUBLIC_SITE_NAME
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  css: ['~/assets/css/main.css'],
  vite: { plugins: [tailwindcss()] },
  runtimeConfig: {
    apiBaseServer: 'http://localhost:8000', // usato durante il rendering SSR
    public: {
      apiBase: 'http://localhost:8000', // usato dal browser
      siteUrl: 'http://localhost:3000',
      siteName: 'SceltaGiusta',
    },
  },
  app: {
    head: {
      htmlAttrs: { lang: 'it' },
      meta: [{ name: 'viewport', content: 'width=device-width, initial-scale=1' }],
      link: [
        { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: '' },
        { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap' },
      ],
    },
  },
})
