'use client';

import { useState, useRef, useEffect } from 'react';
import { sendChatMessage, APIClientError } from '@/lib/api';
import type { ChatMessage, ImageAnalysisResult } from '@/lib/types';

interface SpaceChatProps {
  /** Optional initial image context (from ImageAnalyzer) */
  imageContext?: ImageAnalysisResult | null;
  /** Show the image context indicator */
  showImageBadge?: boolean;
}

export default function SpaceChat({ imageContext, showImageBadge = true }: SpaceChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to latest message (guard for test environments without scrollIntoView)
  useEffect(() => {
    if (messagesEndRef.current && typeof messagesEndRef.current.scrollIntoView === 'function') {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  async function handleSend() {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: ChatMessage = { role: 'user', content: text };
    const updatedMessages = [...messages, userMsg];
    setMessages(updatedMessages);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const ctx = imageContext
        ? {
            title: imageContext.title,
            summary: imageContext.summary,
            observations: imageContext.observations,
            scientific_explanation: imageContext.scientific_explanation,
            confidence: imageContext.confidence,
          }
        : null;

      const data = await sendChatMessage(updatedMessages, ctx);
      const assistantMsg: ChatMessage = { role: 'assistant', content: data.reply };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const msg =
        err instanceof APIClientError
          ? err.message
          : 'حدث خطأ غير متوقع. يرجى المحاولة مجدداً.';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleClear() {
    setMessages([]);
    setError(null);
  }

  const isEmpty = messages.length === 0;

  const suggestions = imageContext
    ? ['ما هذا الجسم؟', 'هل هذا حقيقي؟', 'اشرحلي أكثر']
    : ['ما هو الثقب الأسود؟', 'كيف تولد النجوم؟', 'هل يمكن رؤية مجرة أندروميدا؟'];

  return (
    <div
      lang="ar"
      dir="rtl"
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '620px',
        background: 'rgba(255,255,255,0.025)',
        border: '1px solid var(--border)',
        borderRadius: '16px',
        overflow: 'hidden',
      }}
    >
      {/* ── Header ─────────────────────────────────────────────── */}
      <div
        style={{
          padding: '18px 24px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexShrink: 0,
          background: 'rgba(0,217,255,0.02)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {/* Pulsar AI indicator */}
          <div
            aria-hidden="true"
            style={{
              position: 'relative',
              width: '32px',
              height: '32px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <div style={{
              position: 'absolute',
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              border: '1px solid rgba(0,217,255,0.2)',
              animation: loading ? 'pulsarRing 1.2s ease-in-out infinite' : 'pulsarRing 3s ease-in-out infinite',
            }} />
            <div style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              background: loading
                ? 'linear-gradient(135deg, #00D9FF, #FF2D9A)'
                : 'linear-gradient(135deg, #00D9FF, #7A2CFF)',
              boxShadow: loading
                ? '0 0 10px rgba(0,217,255,0.9)'
                : '0 0 6px rgba(0,217,255,0.5)',
              animation: 'pulsarCore 2s ease-in-out infinite',
            }} />
          </div>
          <div>
            <h2
              style={{
                fontSize: '15px',
                fontWeight: 700,
                color: 'var(--stellar-white)',
                margin: 0,
                marginBottom: '1px',
              }}
            >
              محادثة الفضاء
            </h2>
            <p style={{ fontSize: '11px', color: 'var(--text-faint)', margin: 0 }}>
              {loading ? 'يفكر…' : 'مساعد فلكي · ذكاء اصطناعي'}
            </p>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Image context badge */}
          {showImageBadge && imageContext && (
            <span
              title={`سياق الصورة: ${imageContext.title}`}
              style={{
                fontSize: '11px',
                padding: '3px 10px',
                background: 'rgba(0,217,255,0.08)',
                border: '1px solid rgba(0,217,255,0.2)',
                borderRadius: '20px',
                color: 'var(--pulsar-blue)',
                fontWeight: 600,
              }}
            >
              صورة مرتبطة
            </span>
          )}

          {/* Clear button */}
          {!isEmpty && (
            <button
              onClick={handleClear}
              aria-label="مسح المحادثة"
              style={{
                background: 'transparent',
                border: '1px solid var(--border)',
                borderRadius: '6px',
                padding: '4px 10px',
                color: 'var(--text-faint)',
                fontSize: '11px',
                cursor: 'pointer',
                transition: 'border-color 0.15s, color 0.15s',
              }}
            >
              مسح
            </button>
          )}
        </div>
      </div>

      {/* ── Messages area ──────────────────────────────────────── */}
      <div
        role="log"
        aria-live="polite"
        aria-label="المحادثة"
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '20px 24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '14px',
        }}
      >
        {isEmpty && (
          <div
            style={{
              flex: 1,
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--text-faint)',
              fontSize: '14px',
              textAlign: 'center',
              gap: '16px',
              paddingTop: '20px',
            }}
          >
            {/* Cosmos symbol */}
            <div
              aria-hidden="true"
              style={{
                position: 'relative',
                width: '56px',
                height: '56px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <div style={{
                position: 'absolute',
                width: '56px',
                height: '56px',
                borderRadius: '50%',
                border: '1px solid rgba(0,217,255,0.12)',
                animation: 'pulsarRing 4s ease-in-out infinite',
              }} />
              <div style={{
                position: 'absolute',
                width: '38px',
                height: '38px',
                borderRadius: '50%',
                border: '1px solid rgba(122,44,255,0.12)',
                animation: 'pulsarRing 4s ease-in-out 1s infinite',
              }} />
              <span style={{ fontSize: '22px' }}>✦</span>
            </div>

            <div>
              <p style={{ margin: '0 0 6px', fontWeight: 600, fontSize: '15px', color: 'var(--text-muted)' }}>
                ابدأ محادثة عن الفضاء
              </p>
              <p style={{ margin: 0, fontSize: '12px', color: 'var(--text-faint)' }}>
                {imageContext ? 'يمكنك الآن السؤال عن الصورة أو أي موضوع فضائي' : 'اسأل عن النجوم والكواكب والمجرات والكون'}
              </p>
            </div>

            {/* Suggestion chips */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', justifyContent: 'center' }}>
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => { setInput(suggestion); inputRef.current?.focus(); }}
                  style={{
                    background: 'rgba(0,217,255,0.05)',
                    border: '1px solid rgba(0,217,255,0.15)',
                    borderRadius: '20px',
                    padding: '7px 16px',
                    color: 'var(--text-muted)',
                    fontSize: '12px',
                    cursor: 'pointer',
                    transition: 'border-color 0.15s, background 0.15s',
                    fontFamily: 'inherit',
                  }}
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              display: 'flex',
              justifyContent: msg.role === 'user' ? 'flex-start' : 'flex-end',
            }}
          >
            <div
              style={{
                maxWidth: '82%',
                padding: '11px 16px',
                borderRadius: msg.role === 'user'
                  ? '14px 14px 14px 4px'
                  : '14px 14px 4px 14px',
                background: msg.role === 'user'
                  ? 'rgba(255,255,255,0.05)'
                  : 'rgba(0,217,255,0.07)',
                border: `1px solid ${msg.role === 'user'
                  ? 'rgba(255,255,255,0.07)'
                  : 'rgba(0,217,255,0.15)'}`,
                color: 'var(--text-primary)',
                fontSize: '14px',
                lineHeight: 1.85,
                wordBreak: 'break-word',
              }}
            >
              <div style={{
                fontSize: '9px',
                color: msg.role === 'user' ? 'var(--text-faint)' : 'rgba(0,217,255,0.5)',
                marginBottom: '5px',
                fontWeight: 700,
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
              }}>
                {msg.role === 'user' ? 'أنت' : 'SPACE INTERPRETER AI'}
              </div>
              {msg.content}
            </div>
          </div>
        ))}

        {/* Pulsar thinking animation */}
        {loading && (
          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
            <div
              data-testid="chat-loading"
              style={{
                padding: '12px 18px',
                borderRadius: '14px 14px 4px 14px',
                background: 'rgba(0,217,255,0.05)',
                border: '1px solid rgba(0,217,255,0.12)',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
              }}
            >
              {[0, 0.2, 0.4].map((delay, i) => (
                <span
                  key={i}
                  style={{
                    width: '6px',
                    height: '6px',
                    borderRadius: '50%',
                    background: 'var(--pulsar-blue)',
                    display: 'inline-block',
                    animation: `dotPulse 1.4s ease-in-out ${delay}s infinite`,
                  }}
                />
              ))}
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div
            role="alert"
            data-testid="chat-error"
            style={{
              background: 'rgba(248,113,113,0.06)',
              border: '1px solid rgba(248,113,113,0.25)',
              borderRadius: '10px',
              padding: '10px 14px',
              color: 'var(--accent-red)',
              fontSize: '13px',
            }}
          >
            <span aria-hidden="true" style={{ marginLeft: '6px' }}>⚠</span>
            {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* ── Input area ─────────────────────────────────────────── */}
      <div
        style={{
          padding: '12px 16px',
          borderTop: '1px solid var(--border)',
          flexShrink: 0,
          background: 'rgba(0,0,0,0.15)',
        }}
      >
        <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-end' }}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="اسأل عن النجوم والمجرات والظواهر الكونية…"
            maxLength={800}
            rows={2}
            disabled={loading}
            data-testid="chat-input"
            style={{
              flex: 1,
              background: 'rgba(255,255,255,0.04)',
              border: `1px solid ${input.trim() ? 'rgba(0,217,255,0.25)' : 'var(--border)'}`,
              borderRadius: '12px',
              padding: '10px 14px',
              color: 'var(--text-primary)',
              fontSize: '14px',
              resize: 'none',
              outline: 'none',
              direction: 'rtl',
              lineHeight: 1.6,
              opacity: loading ? 0.6 : 1,
              fontFamily: 'inherit',
              transition: 'border-color 0.15s',
            }}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            data-testid="chat-send"
            aria-label="إرسال"
            className="btn-pulsar"
            style={{
              padding: '12px 16px',
              fontSize: '16px',
              flexShrink: 0,
              opacity: input.trim() && !loading ? 1 : 0.4,
            }}
          >
            ↑
          </button>
        </div>
        <div style={{
          fontSize: '10px',
          color: 'var(--text-faint)',
          marginTop: '6px',
          textAlign: 'left',
          letterSpacing: '0.04em',
        }}>
          Enter للإرسال · Shift+Enter لسطر جديد
        </div>
      </div>
    </div>
  );
}
