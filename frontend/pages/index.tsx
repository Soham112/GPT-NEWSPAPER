import Head from 'next/head';
import Link from 'next/link';
import PlatformHeader from '@/components/PlatformHeader';

const featureTiles = [
  {
    title: 'Research Agent',
    description: 'Deep research with grounded citations, insights, and market signals.',
    href: '/research',
    icon: '🔍',
    accent: 'bg-blue-100 text-blue-700',
  },
  {
    title: 'Outreach Agent',
    description: 'Client dashboards, KPIs, outreach insights & progress tracking.',
    href: '/outreach.html',
    icon: '🗂️',
    accent: 'bg-orange-100 text-orange-700',
  },
  {
    title: 'Integrations',
    description: 'Connect LinkedIn, Apollo, HubSpot. Sync data automatically.',
    href: '/integrations',
    icon: '🔌',
    accent: 'bg-purple-100 text-purple-700',
  },
  {
    title: 'Settings',
    description: 'Profile, account, API keys, workspace preferences.',
    href: '/settings',
    icon: '⚙️',
    accent: 'bg-slate-100 text-slate-700',
  },
];

const recentActivity = [
  { label: 'Research', detail: 'Property tech market shifts', time: '2 hours ago' },
  { label: 'Outreach', detail: 'Reviewed VoltGrid dashboard', time: 'Yesterday' },
  { label: 'Insights', detail: 'AI compliance trends summary', time: '2 days ago' },
  { label: 'Integration', detail: 'Connected HubSpot workspace', time: '3 days ago' },
  { label: 'Research', detail: 'Solar financing opportunities', time: 'Last week' },
];

export default function LandingPage() {
  return (
    <>
      <Head>
        <title>XLR8 Platform - AI Research & Outreach Workspace</title>
      </Head>
      <div className="min-h-screen bg-[#f5f5f7] flex flex-col">
        <PlatformHeader />
        <main className="flex-1">
          <section className="text-center py-16 px-6">
            <p className="text-sm font-semibold text-blue-600 uppercase tracking-[0.2em] mb-3">
              Welcome to XLR8
            </p>
            <h1 className="text-4xl md:text-5xl font-bold text-slate-900 tracking-tight mb-4">
              Your AI Research & Outreach Workspace
            </h1>
            <p className="text-base md:text-lg text-slate-600 max-w-2xl mx-auto">
              Pick a tool to begin. Seamlessly switch between deep research, client outreach, integrations, and workspace settings.
            </p>
          </section>

          <section className="max-w-5xl mx-auto px-6 mb-16">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {featureTiles.map((tile) => (
                <Link
                  key={tile.title}
                  href={tile.href}
                  className="group rounded-2xl bg-white border border-gray-200 p-6 shadow-sm hover:shadow-md transition-shadow"
                >
                  <div className={`h-12 w-12 rounded-xl flex items-center justify-center text-xl font-semibold mb-4 ${tile.accent}`}>
                    {tile.icon}
                  </div>
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="text-2xl font-semibold text-slate-900">{tile.title}</h3>
                    <span className="text-sm text-slate-500 group-hover:text-slate-700">
                      Explore →
                    </span>
                  </div>
                  <p className="text-base text-slate-600 leading-relaxed">{tile.description}</p>
                </Link>
              ))}
            </div>
          </section>

          <section className="max-w-5xl mx-auto px-6 pb-16">
            <div className="rounded-2xl bg-white border border-gray-200 p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <p className="text-sm font-semibold text-blue-600 uppercase tracking-wide">Recent Activity</p>
                  <h2 className="text-2xl font-semibold text-slate-900">Jump back in</h2>
                </div>
                <Link href="/research" className="text-sm font-medium text-blue-600 hover:text-blue-700">
                  View all →
                </Link>
              </div>
              <div className="grid md:grid-cols-2 gap-4">
                {recentActivity.map((activity, idx) => (
                  <div key={`${activity.label}-${idx}`} className="p-4 rounded-xl border border-gray-100 bg-slate-50">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-500 mb-1">{activity.label}</p>
                    <p className="text-base font-medium text-slate-900 mb-1">{activity.detail}</p>
                    <p className="text-sm text-slate-500">{activity.time}</p>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </main>
      </div>
    </>
  );
}
