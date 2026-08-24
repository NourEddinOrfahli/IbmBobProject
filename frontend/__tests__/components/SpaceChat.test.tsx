/**
 * Tests for SpaceChat component.
 *
 * Covers:
 * - Initial render (empty state, input, send button)
 * - Sending a message
 * - AI response display
 * - Loading state
 * - Error display
 * - Clear conversation
 * - Image context badge
 * - Suggestion chips
 */

import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import SpaceChat from '@/components/chat/SpaceChat';
import { sendChatMessage, APIClientError } from '@/lib/api';

jest.mock('@/lib/api', () => ({
  sendChatMessage: jest.fn(),
  APIClientError: class APIClientError extends Error {
    code: string;
    constructor(code: string, message: string) {
      super(message);
      this.code = code;
      this.name = 'APIClientError';
    }
  },
}));

const mockSend = sendChatMessage as jest.MockedFunction<typeof sendChatMessage>;

describe('SpaceChat', () => {
  beforeEach(() => jest.clearAllMocks());

  it('renders the component title', () => {
    render(<SpaceChat />);
    expect(screen.getByText(/محادثة الفضاء/)).toBeInTheDocument();
  });

  it('renders the chat input', () => {
    render(<SpaceChat />);
    expect(screen.getByTestId('chat-input')).toBeInTheDocument();
  });

  it('renders the send button', () => {
    render(<SpaceChat />);
    expect(screen.getByTestId('chat-send')).toBeInTheDocument();
  });

  it('shows empty state initially', () => {
    render(<SpaceChat />);
    expect(screen.getByText(/ابدأ محادثة عن الفضاء/)).toBeInTheDocument();
  });

  it('shows image context badge when imageContext is provided', () => {
    const ctx = {
      title: 'سديم',
      summary: 'ملخص',
      observations: [],
      scientific_explanation: 'تفسير',
      confidence: 'high' as const,
      story: '',
      question_answer: '',
      is_space_related: true,
    };
    render(<SpaceChat imageContext={ctx} />);
    expect(screen.getByText(/صورة مرتبطة/)).toBeInTheDocument();
  });

  it('does not show badge without imageContext', () => {
    render(<SpaceChat />);
    expect(screen.queryByText(/صورة مرتبطة/)).not.toBeInTheDocument();
  });

  it('accepts text in the chat input', async () => {
    render(<SpaceChat />);
    const input = screen.getByTestId('chat-input') as HTMLTextAreaElement;
    await act(async () => {
      fireEvent.change(input, { target: { value: 'ما هو المريخ؟' } });
    });
    expect(input.value).toBe('ما هو المريخ؟');
  });

  it('sends message on send button click', async () => {
    mockSend.mockResolvedValueOnce({ reply: 'المريخ كوكب أحمر.', role: 'assistant' });

    render(<SpaceChat />);
    const input = screen.getByTestId('chat-input') as HTMLTextAreaElement;
    const sendBtn = screen.getByTestId('chat-send');

    await act(async () => {
      fireEvent.change(input, { target: { value: 'ما هو المريخ؟' } });
    });

    await act(async () => {
      fireEvent.click(sendBtn);
    });

    await waitFor(() => {
      expect(screen.getByText('المريخ كوكب أحمر.')).toBeInTheDocument();
    });
  });

  it('shows loading indicator while waiting', async () => {
    let resolve!: (v: { reply: string; role: string }) => void;
    mockSend.mockImplementationOnce(() => new Promise((r) => { resolve = r; }));

    render(<SpaceChat />);
    const input = screen.getByTestId('chat-input');
    const sendBtn = screen.getByTestId('chat-send');

    await act(async () => {
      fireEvent.change(input, { target: { value: 'سؤال' } });
    });

    await act(async () => {
      fireEvent.click(sendBtn);
    });

    expect(screen.getByTestId('chat-loading')).toBeInTheDocument();

    act(() => resolve({ reply: 'إجابة', role: 'assistant' }));
  });

  it('shows error on API failure', async () => {
    mockSend.mockRejectedValueOnce(
      new (class extends Error {
        code = 'AI_TIMEOUT';
        constructor() { super('انتهت المهلة.'); }
      })()
    );

    render(<SpaceChat />);
    const input = screen.getByTestId('chat-input');
    const sendBtn = screen.getByTestId('chat-send');

    await act(async () => {
      fireEvent.change(input, { target: { value: 'سؤال' } });
    });

    await act(async () => {
      fireEvent.click(sendBtn);
    });

    await waitFor(() => {
      expect(screen.getByTestId('chat-error')).toBeInTheDocument();
    });
  });

  it('clears messages on clear button click', async () => {
    mockSend.mockResolvedValueOnce({ reply: 'إجابة', role: 'assistant' });

    render(<SpaceChat />);
    const input = screen.getByTestId('chat-input');
    const sendBtn = screen.getByTestId('chat-send');

    await act(async () => {
      fireEvent.change(input, { target: { value: 'سؤال' } });
      fireEvent.click(sendBtn);
    });

    await waitFor(() => screen.getByText('إجابة'));

    const clearBtn = screen.getByText('مسح');
    await act(async () => {
      fireEvent.click(clearBtn);
    });

    expect(screen.queryByText('إجابة')).not.toBeInTheDocument();
    expect(screen.getByText(/ابدأ محادثة/)).toBeInTheDocument();
  });

  it('clears input after sending', async () => {
    mockSend.mockResolvedValueOnce({ reply: 'إجابة', role: 'assistant' });

    render(<SpaceChat />);
    const input = screen.getByTestId('chat-input') as HTMLTextAreaElement;
    const sendBtn = screen.getByTestId('chat-send');

    await act(async () => {
      fireEvent.change(input, { target: { value: 'ما هو الثقب الأسود؟' } });
      fireEvent.click(sendBtn);
    });

    await waitFor(() => screen.getByText('إجابة'));

    expect(input.value).toBe('');
  });
});
