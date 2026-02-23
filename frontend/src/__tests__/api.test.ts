/**
 * Frontend unit tests for the API service layer.
 * Uses vitest + fetch mocking.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { checkHealth, getSkills, getMarketOverview } from '../services/api'

// Mock fetch globally
const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

const mockResponse = (body: unknown, ok = true, status = 200) => {
  return Promise.resolve({
    ok,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  } as Response)
}

beforeEach(() => mockFetch.mockReset())

describe('checkHealth', () => {
  it('returns health data on success', async () => {
    mockFetch.mockReturnValueOnce(
      mockResponse({ status: 'ok', model: 'gemini-2.0-flash-exp' })
    )
    const result = await checkHealth()
    expect(result.status).toBe('ok')
    expect(result.model).toBe('gemini-2.0-flash-exp')
  })

  it('throws on non-ok response', async () => {
    mockFetch.mockReturnValueOnce(mockResponse({ detail: 'error' }, false, 503))
    await expect(checkHealth()).rejects.toThrow('API 503')
  })
})

describe('getSkills', () => {
  it('returns skills manifest', async () => {
    const skills = [
      { name: 'trading_advisor', description: 'Trading skill', icon: '📈', tags: ['trading'], version: '1.0.0', tools: [] },
      { name: 'chart_generator', description: 'Chart skill', icon: '📊', tags: ['charts'], version: '1.0.0', tools: [] },
    ]
    mockFetch.mockReturnValueOnce(mockResponse({ skills }))
    const result = await getSkills()
    expect(result.skills).toHaveLength(2)
    expect(result.skills[0].name).toBe('trading_advisor')
    expect(result.skills[1].name).toBe('chart_generator')
  })
})

describe('getMarketOverview', () => {
  it('returns market indices', async () => {
    const mockOverview = {
      indices: {
        'S&P 500': { symbol: '^GSPC', price: 5000, change: 10, change_pct: 0.2 },
      },
      timestamp: '2026-02-23T12:00:00',
    }
    mockFetch.mockReturnValueOnce(mockResponse(mockOverview))
    const result = await getMarketOverview()
    expect(result.indices['S&P 500'].price).toBe(5000)
    expect(result.indices['S&P 500'].change_pct).toBe(0.2)
  })
})
