import React, { useState, useRef, useEffect } from 'react';
import Head from 'next/head';
import PlatformHeader from '@/components/PlatformHeader';

const BACKEND_BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

// Default client metadata used ONLY when the user implicitly requests ICP strategy
// via natural-language prompts (e.g., "ICP strategy", "ideal customer profile").
// This keeps the UI simple while still satisfying the backend requirement that
// both `include_icp: true` and a `client` object must be present.
const DEFAULT_CLIENT = {
  name: 'XLR8 Default Client',
  type: 'Agency',
  focus_industry: 'Energy',
  client_industry: 'Utilities',
  target_regions: ['US', 'EU'],
  target_audience: ['CFOs', 'Heads of Sustainability'],
};

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'error';
  content: string;
  resultData?: any; // For assistant messages with research results
}

export default function ResearchPage() {
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
      // Detect natural-language intent for ICP strategy.
      // IMPORTANT: This only toggles a flag; the backend still enforces that
      // ICP strategy runs ONLY when include_icp === true AND client is present.
      const normalized = topic.toLowerCase();
      const wantsICP =
        /\bicp\b/.test(normalized) ||
        normalized.includes('ideal customer profile') ||
        normalized.includes('persona strategy') ||
        normalized.includes('icp strategy') ||
        normalized.includes('icp insights');

      // Let backend auto-detect intent (use_case, include_insights, region)
      // No need to pass these explicitly - backend will detect from query text
      const requestBody: any = {
        topics: [topic],
        window: 'week',
        k: 5,
        strict: true,
      };

      if (wantsICP) {
        requestBody.include_icp = true;
        requestBody.client = DEFAULT_CLIENT;
      }

      const response = await fetch(`${BACKEND_BASE_URL}/research/v1`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
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
        <PlatformHeader />
        <div className="flex-1 flex flex-col">

        {/* Header - Only show before first response */}
        {!hasResponse && (
          <header className="text-center py-12 px-4" key="header">
            <h1 className="text-4xl font-bold tracking-tight mb-4 text-slate-900">
              XLR8 Research
            </h1>
            <div className="mt-3">
              <a
                href="/outreach.html"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block px-3.5 py-1.5 text-sm font-medium text-blue-600 hover:text-blue-700 border border-blue-200 rounded-full hover:bg-blue-50 transition-colors"
              >
                Outreach Agent
              </a>
            </div>
          </header>
        )}

        {/* Messages Container */}
        {messages.length === 0 && !hasResponse ? (
          /* Centered Initial State */
          <div className="flex-1 flex items-center justify-center px-4 md:px-6">
            <div className="w-full max-w-2xl">
              <div className="flex flex-col items-center justify-center">
                <h2 className="text-base font-semibold mb-8 text-slate-900 text-center">
                  Ready when you are
                </h2>
                
                {/* Centered Input */}
                <form onSubmit={handleSubmit} className="w-full flex gap-2.5">
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
        ) : (
          /* Messages View */
          <div className="flex-1 overflow-y-auto px-4 md:px-6 pb-32">
            <div className="max-w-3xl mx-auto w-full py-6">

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
        )}

        {/* Fixed Bottom Input - Only show after first response */}
        {hasResponse && (
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
        )}
        </div>
      </div>
    </>
  );
}

// Helper to check if use case is ICP
const isICPUseCase = (useCase?: string | null): boolean => {
  return useCase === "icp_companies" || useCase === "icp_profiles";
};

// Result Card Component - Renders the research result
function ResultCard({ result }: { result: any }) {
  console.log('[XLR8 Debug] ResultCard rendering with result:', result);
  const headline = result.headline || result.topic;
  const bullets = result.summary || [];
  const links = result.links || [];
  const whyItMatters = result.why_it_matters;
  const tags = result.tags || {};
  const insights = result.insights;
  const icpStrategy = result.icp_strategy;
  const useCase = result.use_case as string | undefined;
  const isICP = isICPUseCase(useCase);
  const useCaseOutput = result.use_case_output;

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

      {/* ICP-specific output: Show for ICP use cases ABOVE the normal bullets/insights */}
      {isICP && useCaseOutput && (
        <ICPOutputSection useCase={useCase} useCaseOutput={useCaseOutput} />
      )}

      {/* Fallback message if ICP use case but no output */}
      {isICP && !useCaseOutput && (
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-sm text-yellow-800">
            Couldn't extract structured ICP output from the articles. Try rephrasing your question or widening the time window.
          </p>
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

      {/* Market Insights: ONLY show when not ICP use case */}
      {!isICP && insights && !insights.error && (
        <InsightsSection insights={insights} links={links} />
      )}

      {/* ICP Strategy (optional, only when backend returns icp_strategy) */}
      {icpStrategy && (
        <div className="mt-5 pt-5 border-t border-gray-200">
          <div className="p-3 bg-gray-50 border border-gray-200 rounded-lg space-y-3">
            <h4 className="text-2xl font-semibold text-slate-900 mb-2">ICP Strategy</h4>

            {/* ICP Profile */}
            {icpStrategy.icp_profile && (
              <div>
                <h5 className="text-sm font-semibold text-slate-900 mb-1.5">ICP Profile</h5>
                <p className="text-base text-slate-600 leading-relaxed">
                  {icpStrategy.icp_profile.description}
                </p>
                <p className="text-sm text-slate-500 mt-1">
                  {icpStrategy.icp_profile.industry && (
                    <>Industry: {icpStrategy.icp_profile.industry}. </>
                  )}
                  {icpStrategy.icp_profile.region && <>Region: {icpStrategy.icp_profile.region}.</>}
                </p>
              </div>
            )}

            {/* Helper to render bullet-style ICP arrays */}
            {Array.isArray(icpStrategy.icp_pains) && icpStrategy.icp_pains.length > 0 && (
              <div>
                <h5 className="text-sm font-semibold text-slate-900 mb-1.5">ICP Pains</h5>
                <ul className="list-none space-y-1">
                  {icpStrategy.icp_pains.map((item: any, idx: number) => (
                    <li key={idx} className="text-base text-slate-600 leading-relaxed">
                      {item.text}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {Array.isArray(icpStrategy.icp_triggers) && icpStrategy.icp_triggers.length > 0 && (
              <div>
                <h5 className="text-sm font-semibold text-slate-900 mb-1.5">ICP Triggers</h5>
                <ul className="list-none space-y-1">
                  {icpStrategy.icp_triggers.map((item: any, idx: number) => (
                    <li key={idx} className="text-base text-slate-600 leading-relaxed">
                      {item.text}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {Array.isArray(icpStrategy.icp_jobs_to_be_done) &&
              icpStrategy.icp_jobs_to_be_done.length > 0 && (
                <div>
                  <h5 className="text-sm font-semibold text-slate-900 mb-1.5">
                    ICP Jobs To Be Done
                  </h5>
                  <ul className="list-none space-y-1">
                    {icpStrategy.icp_jobs_to_be_done.map((item: any, idx: number) => (
                      <li key={idx} className="text-base text-slate-600 leading-relaxed">
                        {item.text}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

            {Array.isArray(icpStrategy.icp_recommendations) &&
              icpStrategy.icp_recommendations.length > 0 && (
                <div>
                  <h5 className="text-sm font-semibold text-slate-900 mb-1.5">
                    ICP Recommendations & Plays
                  </h5>
                  <ul className="list-none space-y-1">
                    {icpStrategy.icp_recommendations.map((item: any, idx: number) => (
                      <li key={idx} className="text-base text-slate-600 leading-relaxed">
                        <span className="font-medium text-slate-900">
                          {item.play_name || 'Play'}:
                        </span>{' '}
                        {item.angle}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

            {Array.isArray(icpStrategy.product_opportunities) &&
              icpStrategy.product_opportunities.length > 0 && (
                <div>
                  <h5 className="text-sm font-semibold text-slate-900 mb-1.5">
                    Product Opportunities
                  </h5>
                  <ul className="list-none space-y-1">
                    {icpStrategy.product_opportunities.map((item: any, idx: number) => (
                      <li key={idx} className="text-base text-slate-600 leading-relaxed">
                        {item.text}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

            {Array.isArray(icpStrategy.workflow_impact) &&
              icpStrategy.workflow_impact.length > 0 && (
                <div>
                  <h5 className="text-sm font-semibold text-slate-900 mb-1.5">
                    Workflow Impact
                  </h5>
                  <ul className="list-none space-y-1">
                    {icpStrategy.workflow_impact.map((item: any, idx: number) => (
                      <li key={idx} className="text-base text-slate-600 leading-relaxed">
                        {item.text}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

            {icpStrategy.decision_framework && (
              <div>
                <h5 className="text-sm font-semibold text-slate-900 mb-1.5">
                  Decision Framework
                </h5>
                <p className="text-base text-slate-600 leading-relaxed">
                  <span className="font-medium">If</span> {icpStrategy.decision_framework.if},{' '}
                  <span className="font-medium">then</span> {icpStrategy.decision_framework.then}.{' '}
                  <span className="font-medium">Because</span>{' '}
                  {icpStrategy.decision_framework.because}
                </p>
              </div>
            )}
          </div>
        </div>
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

// ICP Output Section Component - Renders ICP-specific output
function ICPOutputSection({ useCase, useCaseOutput }: { useCase: string | undefined; useCaseOutput: any }) {
  // Handle error case
  if (useCaseOutput.error) {
    return (
      <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-sm text-red-800">
          Error generating ICP output: {useCaseOutput.message || useCaseOutput.error}
        </p>
      </div>
    );
  }

  // ICP Companies rendering
  if (useCase === "icp_companies" && useCaseOutput.companies && Array.isArray(useCaseOutput.companies)) {
    return (
      <section className="mt-4 rounded-xl border bg-white p-4">
        <h3 className="text-lg font-semibold mb-3">Ideal Buyer Companies</h3>
        <div className="space-y-3">
          {useCaseOutput.companies.map((co: any, idx: number) => (
            <div key={co.name || idx} className="border rounded-lg p-3">
              <div className="flex justify-between items-center">
                <div>
                  <div className="font-medium">{co.name}</div>
                  {co.industry && (
                    <div className="text-sm text-gray-600">{co.industry}</div>
                  )}
                </div>
                {co.approx_size && (
                  <span className="text-xs rounded-full bg-gray-100 px-2 py-1">
                    {co.approx_size}
                  </span>
                )}
              </div>
              {co.location && (
                <div className="mt-1 text-xs text-gray-500">{co.location}</div>
              )}
              {co.why_target && (
                <p className="mt-2 text-sm text-gray-800">{co.why_target}</p>
              )}
              {co.source && (
                <a
                  href={co.source}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-2 inline-block text-xs text-blue-600 underline"
                >
                  Source
                </a>
              )}
            </div>
          ))}
        </div>
      </section>
    );
  }

  // ICP Profiles rendering
  if (useCase === "icp_profiles" && useCaseOutput.companies && Array.isArray(useCaseOutput.companies)) {
    return (
      <section className="mt-4 rounded-xl border bg-white p-4">
        <h3 className="text-lg font-semibold mb-3">ICP Titles & Leaders</h3>
        <div className="space-y-4">
          {useCaseOutput.companies.map((co: any, idx: number) => (
            <div key={co.name || idx} className="border rounded-lg p-3">
              <div className="font-medium">{co.name}</div>

              {co.icp_titles && Array.isArray(co.icp_titles) && co.icp_titles.length > 0 && (
                <div className="mt-2">
                  <div className="text-xs font-semibold text-gray-600">
                    ICP Titles
                  </div>
                  <ul className="mt-1 list-disc pl-5 text-sm text-gray-800">
                    {co.icp_titles.map((t: string, tIdx: number) => (
                      <li key={tIdx}>{t}</li>
                    ))}
                  </ul>
                </div>
              )}

              {co.leaders && Array.isArray(co.leaders) && co.leaders.length > 0 && (
                <div className="mt-2">
                  <div className="text-xs font-semibold text-gray-600">
                    Named Leaders
                  </div>
                  <ul className="mt-1 space-y-1 text-sm text-gray-800">
                    {co.leaders.map((l: any, lIdx: number) => (
                      <li key={`${l.name}-${l.title}-${lIdx}`}>
                        <span className="font-medium">{l.name}</span>
                        {l.title && ` – ${l.title}`}
                        {l.is_icp_title && (
                          <span className="ml-1 rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-semibold text-blue-700">
                            ICP
                          </span>
                        )}
                        {l.reason && (
                          <div className="text-xs text-gray-600">{l.reason}</div>
                        )}
                        {l.source && (
                          <a
                            href={l.source}
                            target="_blank"
                            rel="noreferrer"
                            className="text-[11px] text-blue-600 underline"
                          >
                            Source
                          </a>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
        </div>
      </section>
    );
  }

  // Fallback for unknown ICP use case or missing data
  return (
    <div className="mt-4 p-3 bg-gray-50 border border-gray-200 rounded-lg">
      <p className="text-sm text-gray-600">
        ICP output format not recognized for use case: {useCase}
      </p>
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

