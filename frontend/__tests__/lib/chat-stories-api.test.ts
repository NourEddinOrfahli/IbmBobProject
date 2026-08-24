/**
 * Tests for sendChatMessage and fetchStories API functions.
 *
 * Covers:
 * - sendChatMessage: success, error, network failure
 * - fetchStories: success, error, parameters
 */

import { sendChatMessage, fetchStories, APIClientError } from '@/lib/api';

const mockFetch = jest.fn();
global.fetch = mockFetch;

beforeEach(() => mockFetch.mockReset());

// ---------------------------------------------------------------------------
// sendChatMessage
// ---------------------------------------------------------------------------

describe('sendChatMessage', () => {
  it('returns ChatResponseData on success', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        success: true,
        data: { reply: 'هذا سديم.', role: 'assistant' },
      }),
    } as Response);

    const result = await sendChatMessage([{ role: 'user', content: 'ما هذا؟' }]);
    expect(result.reply).toBe('هذا سديم.');
    expect(result.role).toBe('assistant');
  });

  it('passes messages in request body', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: { reply: 'إجابة', role: 'assistant' } }),
    } as Response);

    const messages = [{ role: 'user' as const, content: 'سؤال' }];
    await sendChatMessage(messages);

    const [, options] = mockFetch.mock.calls[0];
    const body = JSON.parse((options as RequestInit).body as string);
    expect(body.messages).toEqual(messages);
  });

  it('passes imageContext when provided', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: { reply: 'إجابة', role: 'assistant' } }),
    } as Response);

    const ctx = { title: 'سديم', summary: 'ملخص' };
    await sendChatMessage([{ role: 'user', content: 'ما هذا؟' }], ctx);

    const [, options] = mockFetch.mock.calls[0];
    const body = JSON.parse((options as RequestInit).body as string);
    expect(body.image_context).toEqual(ctx);
  });

  it('uses POST method', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: { reply: 'إجابة', role: 'assistant' } }),
    } as Response);

    await sendChatMessage([{ role: 'user', content: 'سؤال' }]);
    const [, options] = mockFetch.mock.calls[0];
    expect((options as RequestInit).method).toBe('POST');
  });

  it('uses correct endpoint', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ success: true, data: { reply: 'إجابة', role: 'assistant' } }),
    } as Response);

    await sendChatMessage([{ role: 'user', content: 'سؤال' }]);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/chat'),
      expect.any(Object),
    );
  });

  it('throws APIClientError on error response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({ success: false, error: { code: 'AI_NOT_CONFIGURED', message: 'غير مهيأ.' } }),
    } as Response);

    await expect(
      sendChatMessage([{ role: 'user', content: 'سؤال' }])
    ).rejects.toMatchObject({ code: 'AI_NOT_CONFIGURED' });
  });

  it('throws NETWORK_ERROR on fetch failure', async () => {
    mockFetch.mockRejectedValueOnce(new TypeError('network down'));
    await expect(
      sendChatMessage([{ role: 'user', content: 'سؤال' }])
    ).rejects.toMatchObject({ code: 'NETWORK_ERROR' });
  });
});

// ---------------------------------------------------------------------------
// fetchStories
// ---------------------------------------------------------------------------

describe('fetchStories', () => {
  function makeStoriesResponse() {
    return {
      success: true,
      data: {
        stories: [
          {
            id: '2024-01-15',
            date: '2024-01-15',
            title: 'Galaxy Formation',
            summary: 'A beautiful galaxy.',
            image_url: 'https://apod.nasa.gov/apod/image/test.jpg',
            hd_image_url: null,
            media_type: 'image',
            copyright: null,
            source: 'NASA APOD',
          },
        ],
        count: 1,
      },
    };
  }

  it('returns StoriesData on success', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => makeStoriesResponse(),
    } as Response);

    const result = await fetchStories();
    expect(result.stories).toHaveLength(1);
    expect(result.count).toBe(1);
  });

  it('passes count parameter', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => makeStoriesResponse(),
    } as Response);

    await fetchStories(3);
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('count=3'),
      expect.any(Object),
    );
  });

  it('passes end_date parameter', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => makeStoriesResponse(),
    } as Response);

    await fetchStories(5, '2024-01-10');
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining('end_date=2024-01-10'),
      expect.any(Object),
    );
  });

  it('throws APIClientError on error', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => ({ success: false, error: { code: 'NASA_NOT_CONFIGURED', message: 'خطأ' } }),
    } as Response);

    await expect(fetchStories()).rejects.toBeInstanceOf(APIClientError);
  });
});
