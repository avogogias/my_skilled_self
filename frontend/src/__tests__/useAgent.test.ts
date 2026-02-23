/**
 * Tests for the useAgent hook.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useAgent } from '../hooks/useAgent'

// Mock the api module
vi.mock('../services/api', () => ({
  streamChat: vi.fn(async (_req, onEvent) => {
    onEvent({ type: 'text_chunk', content: 'Hello from agent' })
    onEvent({ type: 'text_chunk', content: '! Ready to help.' })
    onEvent({ type: 'done' })
  }),
}))

describe('useAgent', () => {
  it('starts with empty messages', () => {
    const { result } = renderHook(() => useAgent())
    expect(result.current.messages).toHaveLength(0)
    expect(result.current.isLoading).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('adds user message and assistant response on sendMessage', async () => {
    const { result } = renderHook(() => useAgent())

    await act(async () => {
      await result.current.sendMessage('Tell me about AAPL')
    })

    expect(result.current.messages).toHaveLength(2)
    expect(result.current.messages[0].role).toBe('user')
    expect(result.current.messages[1].role).toBe('assistant')

    const userPart = result.current.messages[0].parts[0]
    expect(userPart.kind).toBe('text')
    if (userPart.kind === 'text') {
      expect(userPart.content).toBe('Tell me about AAPL')
    }
  })

  it('accumulates text chunks into assistant message', async () => {
    const { result } = renderHook(() => useAgent())

    await act(async () => {
      await result.current.sendMessage('Hello')
    })

    const assistantMsg = result.current.messages[1]
    const textPart = assistantMsg.parts.find(p => p.kind === 'text')
    expect(textPart).toBeDefined()
    if (textPart && textPart.kind === 'text') {
      expect(textPart.content).toBe('Hello from agent! Ready to help.')
    }
  })

  it('clearMessages resets state', async () => {
    const { result } = renderHook(() => useAgent())

    await act(async () => {
      await result.current.sendMessage('Test')
    })

    expect(result.current.messages.length).toBeGreaterThan(0)

    act(() => {
      result.current.clearMessages()
    })

    expect(result.current.messages).toHaveLength(0)
    expect(result.current.error).toBeNull()
  })

  it('does not send empty messages', async () => {
    const { result } = renderHook(() => useAgent())

    await act(async () => {
      await result.current.sendMessage('   ')
    })

    expect(result.current.messages).toHaveLength(0)
  })
})
