import Head from 'next/head';
import PlatformHeader from '@/components/PlatformHeader';

const integrations = [
  {
    name: 'LinkedIn',
    description: 'Sync conversations, outreach sequences, and prospect replies.',
    status: 'Connected',
  },
  {
    name: 'Apollo.io',
    description: 'Pull account lists, personas, and signal-based targeting.',
    status: 'Connect',
  },
  {
    name: 'HubSpot',
    description: 'Two-way sync for contacts, deals, and engagement data.',
    status: 'Connect',
  },
];

export default function IntegrationsPage() {
  return (
    <>
      <Head>
        <title>Integrations - XLR8 Platform</title>
      </Head>
      <div className="min-h-screen bg-[#f5f5f7] flex flex-col">
        <PlatformHeader />
        <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-12 space-y-8">
          <div>
            <p className="text-sm font-semibold text-blue-600 uppercase tracking-wide mb-2">Integrations</p>
            <h1 className="text-4xl font-bold text-slate-900 mb-3">Connect your tooling</h1>
            <p className="text-base text-slate-600 max-w-2xl">
              Bring your GTM data into one workspace. Connect CRMs, enrichment tools, and outreach platforms for live context inside Research and Outreach agents.
            </p>
          </div>

          <div className="space-y-4">
            {integrations.map((integration) => (
              <div key={integration.name} className="rounded-2xl bg-white border border-gray-200 p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4 shadow-sm">
                <div>
                  <h2 className="text-2xl font-semibold text-slate-900">{integration.name}</h2>
                  <p className="text-base text-slate-600 mt-1">{integration.description}</p>
                </div>
                <button
                  className={`px-5 py-2.5 rounded-xl text-sm font-semibold transition-colors ${
                    integration.status === 'Connected'
                      ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      : 'bg-slate-900 text-white hover:bg-slate-800'
                  }`}
                >
                  {integration.status === 'Connected' ? 'Connected' : 'Connect'}
                </button>
              </div>
            ))}
          </div>
        </main>
      </div>
    </>
  );
}
