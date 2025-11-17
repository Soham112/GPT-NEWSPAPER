import Head from 'next/head';
import PlatformHeader from '@/components/PlatformHeader';

export default function SettingsPage() {
  return (
    <>
      <Head>
        <title>Settings - XLR8 Platform</title>
      </Head>
      <div className="min-h-screen bg-[#f5f5f7] flex flex-col">
        <PlatformHeader />
        <main className="flex-1 max-w-4xl mx-auto w-full px-6 py-12 space-y-8">
          <div>
            <p className="text-sm font-semibold text-blue-600 uppercase tracking-wide mb-2">Settings</p>
            <h1 className="text-4xl font-bold text-slate-900 mb-3">Workspace preferences</h1>
            <p className="text-base text-slate-600 max-w-2xl">
              Manage your profile, API keys, notification preferences, and workspace defaults.
            </p>
          </div>

          <div className="grid lg:grid-cols-2 gap-4">
            <div className="rounded-2xl bg-white border border-gray-200 p-6 shadow-sm">
              <h2 className="text-xl font-semibold text-slate-900 mb-3">Profile</h2>
              <div className="flex flex-col gap-3 text-sm text-slate-600">
                <label className="font-semibold text-slate-900">Name</label>
                <input type="text" defaultValue="Soham Patil" className="rounded-xl border border-gray-200 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
                <label className="font-semibold text-slate-900">Email</label>
                <input type="email" defaultValue="soham@xlr8.ai" className="rounded-xl border border-gray-200 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
            </div>

            <div className="rounded-2xl bg-white border border-gray-200 p-6 shadow-sm">
              <h2 className="text-xl font-semibold text-slate-900 mb-3">API Keys</h2>
              <p className="text-sm text-slate-600 mb-4">Securely manage access for XLR8 integrations and automations.</p>
              <button className="px-4 py-2 rounded-xl bg-slate-900 text-white text-sm font-semibold hover:bg-slate-800">Generate new key</button>
            </div>
          </div>
        </main>
      </div>
    </>
  );
}
