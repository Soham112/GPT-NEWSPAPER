import Link from 'next/link';
import { useRouter } from 'next/router';

const navItems = [
  { label: 'Home', href: '/' },
  { label: 'Research Agent', href: '/research' },
  { label: 'Outreach Agent', href: '/outreach.html' },
  { label: 'Integrations', href: '/integrations' },
  { label: 'Settings', href: '/settings' },
];

export default function PlatformHeader() {
  const router = useRouter();

  return (
    <header className="w-full border-b border-gray-200 bg-white/90 backdrop-blur supports-[backdrop-filter]:bg-white/80">
      <div className="max-w-6xl mx-auto px-4 md:px-6 py-4 flex items-center justify-between gap-4">
        <Link href="/" className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-blue-600 text-white font-semibold flex items-center justify-center">
            X
          </div>
          <div className="flex flex-col">
            <span className="text-base font-semibold text-slate-900">XLR8</span>
            <span className="text-xs text-slate-500">AI Workspace</span>
          </div>
        </Link>

        <nav className="flex flex-wrap lg:flex-nowrap items-center gap-4 text-sm font-medium text-slate-600">
          {navItems.map((item) => {
            const isActive =
              item.href === '/outreach.html'
                ? router.asPath.startsWith('/outreach')
                : router.asPath === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`transition-colors ${
                  isActive ? 'text-slate-900' : 'hover:text-slate-900'
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-3">
          <button className="hidden md:inline-flex items-center gap-2 rounded-full border border-gray-200 px-3 py-1.5 text-xs font-medium text-slate-600 hover:border-gray-300">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-500" />
            Live
          </button>
          <div className="h-10 w-10 rounded-full bg-slate-200 flex items-center justify-center text-sm font-semibold text-slate-600">
            SP
          </div>
        </div>
      </div>
    </header>
  );
}
