import React, { useState, useRef, useEffect } from 'react';
import Head from 'next/head';
import Link from 'next/link';

const BACKEND_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'error';
  content: string;
  resultData?: any; // For assistant messages with research results
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Compute hasResponse directly from messages (no state needed)
  const hasResponse = messages.some((m: Message) => m.role === 'assistant' || m.role === 'error');
  
  // Debug logging - log on every render
  // Using console.error for one message so it always shows even if filters are on
  if (messages.length > 0) {
    console.error('[XLR8 Debug] ⚠️ Component rendered with messages. hasResponse:', hasResponse, 'Messages:', messages);
  }
  console.log('[XLR8 Debug] Messages:', messages);
  console.log('[XLR8 Debug] hasResponse:', hasResponse);
  console.log('[XLR8 Debug] Messages with assistant role:', messages.filter(m => m.role === 'assistant'));
  console.log('[XLR8 Debug] All message roles:', messages.map(m => m.role));
  
  // Also log when messages change
  useEffect(() => {
    console.log('[XLR8 Debug] Messages changed! Count:', messages.length);
    console.log('[XLR8 Debug] hasResponse after change:', hasResponse);
    if (messages.length > 0) {
      console.log('[XLR8 Debug] Last message:', messages[messages.length - 1]);
    }
  }, [messages, hasResponse]);

  // Scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input on mount and after search
  useEffect(() => {
    if (!hasResponse) {
      inputRef.current?.focus();
    }
  }, [hasResponse]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const topic = inputValue.trim();
    
    if (!topic || isSearching) return;

    // Add user message
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: topic,
    };
    setMessages((prev: Message[]) => [...prev, userMessage]);
    setInputValue('');
    setIsSearching(true);

    try {
      const response = await fetch(`${BACKEND_BASE_URL}/research/v1`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          topics: [topic],
          window: 'week',
          k: 5,
          strict: true,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log('[XLR8 Debug] Response data:', data);
      console.log('[XLR8 Debug] Has results?', !!data.results);
      console.log('[XLR8 Debug] Results array?', Array.isArray(data.results));
      console.log('[XLR8 Debug] Results length:', data.results?.length);

      if (data.results && Array.isArray(data.results) && data.results.length > 0) {
        // Add assistant message with result data
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: '',
          resultData: data.results[0], // Use first result
        };
        console.log('[XLR8 Debug] Adding assistant message:', assistantMessage);
        console.log('[XLR8 Debug] Result data structure:', JSON.stringify(data.results[0], null, 2));
        setMessages((prev: Message[]) => {
          const newMessages = [...prev, assistantMessage];
          console.log('[XLR8 Debug] New messages array:', newMessages);
          console.log('[XLR8 Debug] Has assistant?', newMessages.some(m => m.role === 'assistant'));
          return newMessages;
        });
      } else if (data.error) {
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'error',
          content: data.error || 'An error occurred',
        };
        setMessages((prev: Message[]) => [...prev, errorMessage]);
      } else {
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'error',
          content: 'No results found. Please try a different topic.',
        };
        setMessages((prev: Message[]) => [...prev, errorMessage]);
      }
    } catch (error: any) {
      console.error('[XLR8 Debug] Fetch error:', error);
      console.error('[XLR8 Debug] Error message:', error.message);
      console.error('[XLR8 Debug] Error stack:', error.stack);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'error',
        content: error.message || 'Failed to fetch results',
      };
      setMessages((prev: Message[]) => [...prev, errorMessage]);
    } finally {
      setIsSearching(false);
      inputRef.current?.focus();
    }
  };

  return (
    <>
      <Head>
        <title>XLR8 Research - AI-Powered Research Agent</title>
      </Head>

      <div className="min-h-screen flex flex-col bg-[#f5f5f7]">
        {/* Header - Only show before first response */}
        {!hasResponse && (
          <header className="text-center py-12 px-4" key="header">
            <h1 className="text-4xl font-bold tracking-tight mb-4 text-slate-900">
              XLR8 Research
            </h1>
            <div className="mt-3">
              <Link
                href="/outreach.html"
                className="inline-block px-3.5 py-1.5 text-sm font-medium text-blue-600 hover:text-blue-700 border border-blue-200 rounded-full hover:bg-blue-50 transition-colors"
              >
                Outreach Agent
              </Link>
            </div>
          </header>
        )}

        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto px-4 md:px-6 pb-32">
          <div className="max-w-3xl mx-auto w-full py-6">
            {messages.length === 0 && !hasResponse && (
              <div className="text-center py-16">
                <h2 className="text-base font-semibold mb-6 text-slate-900">
                  Ready when you are
                </h2>
              </div>
            )}

            {messages.map((message: Message) => (
              <div
                key={message.id}
                className={`mb-6 ${
                  message.role === 'user'
                    ? 'flex justify-end'
                    : 'flex justify-start'
                }`}
              >
                {message.role === 'user' ? (
                  <div className="max-w-[85%] rounded-xl bg-blue-600 text-white px-4 py-3 text-base leading-relaxed">
                    {message.content}
                  </div>
                ) : message.role === 'error' ? (
                  <div className="max-w-full rounded-xl bg-white border border-red-200 px-4 py-3 text-base leading-relaxed text-red-600">
                    {message.content}
                  </div>
                ) : (
                  <div className="max-w-full rounded-xl bg-white border border-gray-200 shadow-sm px-5 py-4 text-base leading-relaxed">
                    {message.resultData ? (
                      <ResultCard result={message.resultData} />
                    ) : (
                      <div className="text-red-500">
                        [Debug] No resultData in message. Message: {JSON.stringify(message, null, 2)}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}

            {isSearching && (
              <div className="flex justify-start mb-6">
                <div className="max-w-full rounded-xl bg-white border border-gray-200 shadow-sm px-5 py-4">
                  <div className="flex items-center gap-2 text-slate-500">
                    <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                    <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                    <div className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                  </div>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Fixed Bottom Input */}
        <div className="fixed bottom-0 left-0 right-0 bg-[#f5f5f7] border-t border-gray-200">
          <div className="max-w-3xl mx-auto w-full px-4 md:px-6 py-3">
            <form onSubmit={handleSubmit} className="flex gap-2.5">
              <input
                ref={inputRef}
                type="text"
                value={inputValue}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setInputValue(e.target.value)}
                placeholder="Ask anything..."
                disabled={isSearching}
                className="flex-1 px-4 py-3 rounded-xl border border-gray-300 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent text-base leading-relaxed bg-white disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
              <button
                type="submit"
                disabled={!inputValue.trim() || isSearching}
                className="px-5 py-3 bg-blue-600 text-white rounded-xl font-medium hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors text-sm"
              >
                {isSearching ? 'Searching...' : 'Search'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </>
  );
}

// Result Card Component - Renders the research result
function ResultCard({ result }: { result: any }) {
  console.log('[XLR8 Debug] ResultCard rendering with result:', result);
  const headline = result.headline || result.topic;
  const bullets = result.summary || [];
  const links = result.links || [];
  const whyItMatters = result.why_it_matters;
  const tags = result.tags || {};
  const insights = result.insights;

  const companies = Array.isArray(tags.companies) ? tags.companies : tags.companies ? [tags.companies] : [];
  const regions = Array.isArray(tags.regions) ? tags.regions : tags.regions ? [tags.regions] : [];
  const themes = Array.isArray(tags.themes) ? tags.themes : tags.themes ? [tags.themes] : [];
  const allTags = [...companies, ...regions, ...themes];

  const scrollToSource = (citeNum: number) => {
    const sourceEl = document.getElementById(`source-${citeNum}`);
    if (sourceEl) {
      sourceEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      sourceEl.classList.add('highlight-source');
      setTimeout(() => {
        sourceEl.classList.remove('highlight-source');
      }, 2000);
    }
  };

  return (
    <div className="space-y-3">
      {/* Headline */}
      <h3 className="text-2xl font-semibold text-slate-900 leading-tight">
        {headline}
      </h3>

      {/* Tags */}
      {allTags.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {allTags.map((tag: string, idx: number) => (
            <span
              key={idx}
              className="px-2 py-0.5 text-sm font-medium bg-blue-50 text-blue-700 rounded-full"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      {/* Why it matters */}
      {whyItMatters && (
        <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
          <div className="inline-block px-2 py-0.5 text-sm font-medium bg-blue-50 text-blue-700 rounded-full mb-1.5">
            Why it matters
          </div>
          <p className="text-base text-slate-600 leading-relaxed">{whyItMatters}</p>
        </div>
      )}

      {/* Bullets */}
      {bullets.length > 0 && (
        <div className="space-y-2">
          <ul className="list-none space-y-2 pl-0">
            {bullets.map((bullet: any, idx: number) => {
              const text = bullet.bullet || '';
              const cites = bullet.cite || [];
              return (
                <li key={idx} className="text-base leading-relaxed">
                  <span>{text}</span>
                  {cites.map((n: number) => {
                    const link = links.find((l: any) => l.n === n);
                    return (
                      <button
                        key={n}
                        onClick={() => scrollToSource(n)}
                        className="ml-1 text-blue-600 hover:text-blue-700 hover:underline font-medium text-sm"
                        title={link?.title || ''}
                      >
                        [{n}]
                      </button>
                    );
                  })}
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {/* Insights */}
      {insights && !insights.error && (
        <InsightsSection insights={insights} links={links} />
      )}

      {/* Sources */}
      {links.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <h4 className="text-base font-semibold text-slate-900 mb-3">Sources</h4>
          <div className="space-y-2">
            {links.map((link: any) => {
              let domain = '';
              try {
                if (link.url) {
                  domain = new URL(link.url).hostname.replace('www.', '');
                }
              } catch (e) {
                // Invalid URL, use empty domain
                domain = '';
              }
              const faviconUrl = domain ? `https://www.google.com/s2/favicons?domain=${domain}&sz=16` : '';
              return (
                <div
                  key={link.n}
                  id={`source-${link.n}`}
                  className="p-2.5 bg-gray-50 border border-gray-200 rounded-lg transition-all"
                >
                  <div className="flex items-start gap-2.5">
                    {faviconUrl && (
                      <img
                        src={faviconUrl}
                        alt={domain}
                        className="w-3.5 h-3.5 mt-0.5 flex-shrink-0"
                        onError={(e: React.SyntheticEvent<HTMLImageElement, Event>) => {
                          (e.target as HTMLImageElement).style.display = 'none';
                        }}
                      />
                    )}
                    <div className="flex-1 min-w-0">
                      <a
                        href={link.url || '#'}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-base text-blue-600 hover:text-blue-700 font-medium break-words block"
                      >
                        {link.title || link.url || 'Source'}
                      </a>
                      {domain && <div className="text-sm text-slate-500 mt-0.5">{domain}</div>}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

// Insights Section Component
function InsightsSection({ insights, links }: { insights: any; links: any[] }) {
  const scrollToSource = (citeNum: number) => {
    const sourceEl = document.getElementById(`source-${citeNum}`);
    if (sourceEl) {
      sourceEl.scrollIntoView({ behavior: 'smooth', block: 'center' });
      sourceEl.classList.add('highlight-source');
      setTimeout(() => {
        sourceEl.classList.remove('highlight-source');
      }, 2000);
    }
  };

  return (
    <div className="mt-5 pt-5 border-t border-gray-200">
      <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg">
        <h4 className="text-2xl font-semibold text-slate-900 mb-3">Market Insights</h4>

        {insights.market_overview && (
          <div className="mb-3">
            <h5 className="text-sm font-semibold text-slate-900 mb-1.5">Market Overview</h5>
            <p className="text-base text-slate-600 leading-relaxed">{insights.market_overview}</p>
          </div>
        )}

        {insights.key_segments && Array.isArray(insights.key_segments) && insights.key_segments.length > 0 && (
          <div className="mb-3">
            <h5 className="text-sm font-semibold text-slate-900 mb-1.5">Key Segments</h5>
            <ul className="list-none space-y-1">
              {insights.key_segments.map((seg: any, idx: number) => (
                <li key={idx} className="text-base leading-relaxed">
                  <span className="font-medium text-slate-900">{seg.name || seg || 'Unknown'}</span>
                  {seg.note && <span className="text-slate-600"> - {seg.note}</span>}
                </li>
              ))}
            </ul>
          </div>
        )}

        {insights.key_players && Array.isArray(insights.key_players) && insights.key_players.length > 0 && (
          <div className="mb-3">
            <h5 className="text-sm font-semibold text-slate-900 mb-1.5">Key Players</h5>
            <ul className="list-none space-y-1.5">
              {insights.key_players.map((player: any, idx: number) => (
                <li key={idx} className="text-base leading-relaxed">
                  <span className="font-medium text-slate-900">{player.name || 'Unknown'}</span>
                  {player.role && <span className="text-slate-600"> - {player.role}</span>}
                  {player.signal && <span className="text-slate-600">: {player.signal}</span>}
                </li>
              ))}
            </ul>
          </div>
        )}

        {insights.opportunities && Array.isArray(insights.opportunities) && insights.opportunities.length > 0 && (
          <div className="mb-3">
            <h5 className="text-sm font-semibold text-slate-900 mb-1.5">Opportunities</h5>
            <ul className="list-none space-y-1.5">
              {insights.opportunities.map((opp: any, idx: number) => (
                <li key={idx} className="text-base leading-relaxed">
                  <span className="text-slate-900">{opp.text || opp}</span>
                  {opp.cite && Array.isArray(opp.cite) && opp.cite.map((n: number) => (
                    <button
                      key={n}
                      onClick={() => scrollToSource(n)}
                      className="ml-1 text-blue-600 hover:text-blue-700 hover:underline font-medium text-sm"
                    >
                      [{n}]
                    </button>
                  ))}
                </li>
              ))}
            </ul>
          </div>
        )}

        {insights.risks && Array.isArray(insights.risks) && insights.risks.length > 0 && (
          <div className="mb-3">
            <h5 className="text-sm font-semibold text-slate-900 mb-1.5">Risks</h5>
            <ul className="list-none space-y-1.5">
              {insights.risks.map((risk: any, idx: number) => (
                <li key={idx} className="text-base leading-relaxed">
                  <span className="text-slate-900">{risk.text || risk}</span>
                  {risk.cite && Array.isArray(risk.cite) && risk.cite.map((n: number) => (
                    <button
                      key={n}
                      onClick={() => scrollToSource(n)}
                      className="ml-1 text-blue-600 hover:text-blue-700 hover:underline font-medium text-sm"
                    >
                      [{n}]
                    </button>
                  ))}
                </li>
              ))}
            </ul>
          </div>
        )}

        {insights.recommended_plays && Array.isArray(insights.recommended_plays) && insights.recommended_plays.length > 0 && (
          <div className="mb-3">
            <h5 className="text-sm font-semibold text-slate-900 mb-1.5">Recommended Plays</h5>
            <ul className="list-none space-y-2">
              {insights.recommended_plays.map((play: any, idx: number) => (
                <li key={idx} className="text-base leading-relaxed">
                  <div className="font-medium text-slate-900 mb-1">{play.play_name || 'Play'}</div>
                  {play.channels && Array.isArray(play.channels) && (
                    <div className="flex flex-wrap gap-1.5 mb-1.5">
                      {play.channels.map((channel: string, chIdx: number) => (
                        <span key={chIdx} className="px-2 py-0.5 text-sm font-medium bg-blue-50 text-blue-700 rounded">
                          {channel}
                        </span>
                      ))}
                    </div>
                  )}
                  {play.angle && <p className="text-base text-slate-600">{play.angle}</p>}
                </li>
              ))}
            </ul>
          </div>
        )}

        {insights.trend && (
          <div>
            <h5 className="text-sm font-semibold text-slate-900 mb-1.5">Trend</h5>
            <p className="text-base text-slate-600 leading-relaxed">
              <span className="font-medium">Momentum:</span> {insights.trend.momentum || 'N/A'}
            </p>
            {insights.trend.signal_basis && (
              <p className="text-base text-slate-600 leading-relaxed mt-1">{insights.trend.signal_basis}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

