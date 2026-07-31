import {
  Button,
  EmptyState,
  ErrorState,
  Input,
  Loader,
  PALETTE_AREA,
  ROUTES_AREA,
  SIDEBAR_NAV_AREA,
  host,
  useMutation,
  usePluginI18n
} from '@hermes/plugin-sdk'
import { useEffect, useRef, useState } from 'react'
import { jsx, jsxs } from 'react/jsx-runtime'

const ID = 'brave-search'
const ROUTE = '/brave-search'
const MAX_QUERY_CHARACTERS = 400
const MAX_QUERY_WORDS = 50
const QUERY_ERROR_ID = 'brave-search-query-error'

function focusQuery() {
  document.getElementById('brave-search-query')?.focus()
}

function validateQuery(value) {
  const query = typeof value === 'string' ? value.trim() : ''

  if (!query) {
    return 'Enter a search query.'
  }
  if (query.length > MAX_QUERY_CHARACTERS) {
    return 'Search queries must be 400 characters or fewer.'
  }
  if (query.split(/\s+/).length > MAX_QUERY_WORDS) {
    return 'Search queries must contain 50 words or fewer.'
  }

  return ''
}

function safeExternalUrl(value) {
  if (typeof value !== 'string') {
    return ''
  }

  try {
    const url = new URL(value.trim())

    if ((url.protocol !== 'http:' && url.protocol !== 'https:') || !url.hostname) {
      return ''
    }

    return url.toString()
  } catch {
    return ''
  }
}

function safeResults(value) {
  if (!Array.isArray(value)) {
    return []
  }

  return value
    .filter(result => result && typeof result === 'object')
    .map((result, index) => ({
      description: typeof result.description === 'string' ? result.description : '',
      position: Number.isInteger(result.position) && result.position > 0 ? result.position : index + 1,
      title: typeof result.title === 'string' && result.title ? result.title : 'Untitled result',
      url: typeof result.url === 'string' ? result.url : ''
    }))
}

function responseView(response, query) {
  if (!response || typeof response !== 'object') {
    return { kind: 'api_error', query }
  }

  if (response.outcome === 'results') {
    const results = safeResults(response.results)

    return results.length ? { kind: 'results', query, results } : { kind: 'empty', query }
  }
  if (response.outcome === 'empty') {
    return { kind: 'empty', query }
  }
  if (response.outcome === 'missing_credential' || response.outcome === 'invalid_credential') {
    return { kind: 'missing_credential', query }
  }

  return { kind: 'api_error', query }
}

function backendUnavailable(error) {
  const message = error instanceof Error ? error.message : ''

  return /404|not found|bridge|gateway|network|connection|unavailable/i.test(message)
}

function statusText(view, t) {
  if (view.kind === 'loading') {
    return t('loadingStatus')
  }
  if (view.kind === 'results') {
    return t('resultsStatus', view.results.length)
  }
  if (view.kind === 'empty') {
    return t('emptyStatus')
  }
  if (view.kind === 'missing_credential') {
    return t('credentialStatus')
  }
  if (view.kind === 'backend_unavailable') {
    return t('backendStatus')
  }
  if (view.kind === 'api_error') {
    return t('errorStatus')
  }

  return ''
}

function ResultCard({ result, t }) {
  const url = safeExternalUrl(result.url)

  return jsxs('li', {
    className:
      'min-w-0 rounded-[4px] border border-(--ui-stroke-secondary) bg-(--ui-bg-secondary) p-3 shadow-none',
    children: [
      jsxs('div', {
        className: 'flex min-w-0 flex-wrap items-baseline gap-x-2 gap-y-1',
        children: [
          jsx('span', { className: 'shrink-0 text-xs text-(--ui-text-tertiary)', children: `#${result.position}` }),
          jsx('h2', { className: 'min-w-0 break-words text-sm font-medium text-(--ui-text-primary)', children: result.title })
        ]
      }),
      result.description
        ? jsx('p', { className: 'mt-2 break-words text-sm leading-5 text-(--ui-text-secondary)', children: result.description })
        : null,
      url
        ? jsx(Button, {
            className: 'mt-2 max-w-full break-all text-left',
            onClick: () => {
              void window.hermesDesktop?.openExternal?.(url)
            },
            size: 'inline',
            type: 'button',
            variant: 'link',
            children: t('openResult')
          })
        : null
    ]
  })
}

function BraveSearchPage({ ctx }) {
  const t = usePluginI18n(ID)
  const generationRef = useRef(0)
  const [query, setQuery] = useState('')
  const [touched, setTouched] = useState(false)
  const [attempted, setAttempted] = useState(false)
  const [view, setView] = useState({ kind: 'idle' })
  const validationError = validateQuery(query)
  const showValidation = Boolean(validationError && (touched || attempted))
  const search = useMutation({
    mutationFn: query => ctx.rest('/search', { method: 'POST', body: { query } })
  })

  useEffect(() => {
    focusQuery()

    return () => {
      generationRef.current += 1
    }
  }, [])

  const runSearch = submittedQuery => {
    const generation = ++generationRef.current

    setView({ kind: 'loading', query: submittedQuery })
    search.mutate(submittedQuery, {
      onError: error => {
        if (generation !== generationRef.current) {
          return
        }

        if (backendUnavailable(error)) {
          setView({ kind: 'backend_unavailable', query: submittedQuery })
          return
        }

        setView({ kind: 'api_error', query: submittedQuery })
      },
      onSuccess: response => {
        if (generation !== generationRef.current) {
          return
        }

        setView(responseView(response, submittedQuery))
      }
    })
  }

  const submit = event => {
    event.preventDefault()
    const submittedQuery = query.trim()
    const problem = validateQuery(submittedQuery)

    setAttempted(true)
    setQuery(submittedQuery)
    if (problem) {
      focusQuery()
      return
    }

    setAttempted(false)
    runSearch(submittedQuery)
    focusQuery()
  }

  const retry = () => {
    if (!view.query) {
      return
    }

    runSearch(view.query)
    focusQuery()
  }

  const retryButton = jsx(Button, {
    onClick: retry,
    type: 'button',
    variant: 'outline',
    children: t('retry')
  })

  let content = jsx(EmptyState, {
    title: t('idleTitle'),
    description: t('idleDescription')
  })

  if (view.kind === 'loading') {
    content = jsxs('div', {
      className: 'flex min-h-48 flex-col items-center justify-center gap-3 text-sm text-(--ui-text-secondary)',
      children: [jsx(Loader, { label: t('loading'), type: 'lemniscate-bloom' }), jsx('span', { children: t('loading') })]
    })
  } else if (view.kind === 'results') {
    content = jsx('ol', {
      className: 'grid min-w-0 gap-3',
      children: view.results.map(result => jsx(ResultCard, { result, t }, `${result.position}-${result.url}-${result.title}`))
    })
  } else if (view.kind === 'empty') {
    content = jsx(EmptyState, {
      title: t('emptyTitle'),
      description: t('emptyDescription')
    })
  } else if (view.kind === 'missing_credential') {
    content = jsx(ErrorState, {
      title: t('credentialTitle'),
      description: t('credentialDescription'),
      children: retryButton
    })
  } else if (view.kind === 'backend_unavailable') {
    content = jsx(ErrorState, {
      title: t('backendTitle'),
      description: t('backendDescription'),
      children: retryButton
    })
  } else if (view.kind === 'api_error') {
    content = jsx(ErrorState, {
      title: t('errorTitle'),
      description: t('errorDescription'),
      children: retryButton
    })
  }

  return jsxs('main', {
    className: 'flex h-full min-w-0 flex-col gap-5 overflow-auto bg-(--ui-bg-primary) p-4 text-(--ui-text-primary) sm:p-6',
    children: [
      jsxs('header', {
        className: 'grid gap-1',
        children: [
          jsx('h1', { className: 'text-lg font-semibold', children: t('title') }),
          jsx('p', { className: 'text-sm text-(--ui-text-secondary)', children: t('subtitle') })
        ]
      }),
      jsxs('form', {
        className: 'grid gap-2',
        noValidate: true,
        onSubmit: submit,
        children: [
          jsx('label', { className: 'text-sm font-medium', htmlFor: 'brave-search-query', children: t('queryLabel') }),
          jsxs('div', {
            className: 'flex min-w-0 flex-col gap-2 sm:flex-row',
            children: [
              jsx(Input, {
                'aria-describedby': showValidation ? QUERY_ERROR_ID : undefined,
                'aria-invalid': showValidation,
                className: 'min-w-0 flex-1',
                id: 'brave-search-query',
                onBlur: () => setTouched(true),
                onChange: event => setQuery(event.target.value),
                placeholder: t('queryPlaceholder'),
                value: query
              }),
              jsx(Button, { type: 'submit', children: t('search') })
            ]
          }),
          showValidation
            ? jsx('p', {
                className: 'text-sm text-destructive',
                id: QUERY_ERROR_ID,
                role: 'alert',
                children: validationError
              })
            : jsx('p', { className: 'text-xs text-(--ui-text-tertiary)', children: t('queryHint') })
        ]
      }),
      jsx('div', {
        'aria-atomic': 'true',
        'aria-live': 'polite',
        className: 'sr-only',
        role: 'status',
        children: statusText(view, t)
      }),
      jsx('section', { className: 'min-w-0 flex-1', 'aria-label': t('resultsLabel'), children: content })
    ]
  })
}

export default {
  id: ID,
  name: 'Brave Search',
  defaultEnabled: false,
  register(ctx) {
    ctx.i18n.register({
      en: {
        backendDescription: 'Enable the Brave Search backend for this profile, then restart the gateway before retrying.',
        backendStatus: 'Brave Search backend is unavailable.',
        backendTitle: 'Brave Search backend unavailable',
        credentialDescription: 'Set BRAVE_SEARCH_API_KEY for this profile, then retry the search.',
        credentialStatus: 'Brave Search needs its configured credential.',
        credentialTitle: 'Brave Search needs a credential',
        emptyDescription: 'Try another search phrase.',
        emptyStatus: 'No Brave Search results found.',
        emptyTitle: 'No results found',
        errorDescription: 'Brave Search could not complete this request. Try again.',
        errorStatus: 'Brave Search could not complete this request.',
        errorTitle: 'Brave Search could not complete the request',
        idleDescription: 'Enter a web search query to get up to five results.',
        idleTitle: 'Search the web with Brave',
        loading: 'Searching Brave',
        loadingStatus: 'Searching Brave.',
        openResult: 'Open result',
        queryHint: 'Up to 400 characters and 50 words.',
        queryLabel: 'Search query',
        queryPlaceholder: 'Search the web',
        resultsLabel: 'Brave Search results',
        resultsStatus: count => `${count} Brave Search result${count === 1 ? '' : 's'} ready.`,
        retry: 'Retry search',
        search: 'Search',
        subtitle: 'Search the web without sharing your Brave credential with Desktop.',
        title: 'Brave Search'
      }
    })

    ctx.register({
      area: ROUTES_AREA,
      data: { path: ROUTE },
      id: ID,
      render: () => jsx(BraveSearchPage, { ctx }),
      title: 'Brave Search'
    })
    ctx.register({
      area: SIDEBAR_NAV_AREA,
      data: { codicon: 'search', label: 'Brave Search', path: ROUTE },
      id: 'brave-search-sidebar'
    })
    ctx.register({
      area: PALETTE_AREA,
      data: {
        id: 'brave-search.open',
        keywords: ['brave', 'search', 'web'],
        label: 'Open Brave Search',
        run: () => host.navigate(ROUTE)
      },
      id: 'brave-search-palette'
    })
  }
}
