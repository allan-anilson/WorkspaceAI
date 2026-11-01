import test from 'node:test'
import assert from 'node:assert/strict'

const { uploadDocument } = await import('./api.ts')

test('uploadDocument uses upload-intent, S3 PUT, and confirm flow', async () => {
  const calls: Array<{ method: string; url: string; body?: any; headers?: Record<string, string> }> = []

  const fakeFetch = async (url: string, init?: RequestInit) => {
    calls.push({
      method: init?.method ?? 'GET',
      url,
      body: init?.body ? String(init.body) : undefined,
      headers: init?.headers as Record<string, string> | undefined,
    })

    if (url === 'http://localhost:8000/api/v1/workspaces/ws-123/documents/upload-intent') {
      return {
        ok: true,
        headers: {
          get: (name: string) => (name === 'content-type' ? 'application/json' : null),
        },
        json: async () => ({
          document_id: 'doc-123',
          upload_url: 'https://s3.example.com/upload-url',
          storage_path: 'workspaces/ws-123/file.txt',
        }),
      } as unknown as Response
    }

    if (url === 'https://s3.example.com/upload-url') {
      return { ok: true, headers: { get: () => null }, text: async () => '' } as unknown as Response
    }

    if (url === 'http://localhost:8000/api/v1/workspaces/ws-123/documents/doc-123/confirm') {
      return {
        ok: true,
        headers: {
          get: (name: string) => (name === 'content-type' ? 'application/json' : null),
        },
        json: async () => ({ id: 'doc-123', status: 'completed' }),
      } as unknown as Response
    }

    throw new Error(`Unexpected fetch: ${url}`)
  }

  globalThis.fetch = fakeFetch as typeof fetch

  const file = new File(['hello'], 'hello.txt', { type: 'text/plain' })
  const result = await uploadDocument('ws-123', file, 'token-123')

  assert.equal(calls[0]?.method, 'POST')
  assert.equal(calls[0]?.url, 'http://localhost:8000/api/v1/workspaces/ws-123/documents/upload-intent')
  assert.equal(calls[1]?.method, 'PUT')
  assert.equal(calls[1]?.url, 'https://s3.example.com/upload-url')
  assert.equal(calls[2]?.method, 'POST')
  assert.equal(calls[2]?.url, 'http://localhost:8000/api/v1/workspaces/ws-123/documents/doc-123/confirm')
  assert.deepEqual(result, { id: 'doc-123', status: 'completed' })
})
