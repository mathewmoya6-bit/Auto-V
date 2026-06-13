import Link from 'next/link';

export default function LandingPage() {
  return (
    <div className="bg-slate-50 min-h-screen font-sans">
      {/* 1. Navigation Bar Header */}
      <header className="bg-white border-b border-slate-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <span className="text-2xl font-black text-blue-600 tracking-wider">AUTO-V</span>
            <span className="bg-blue-100 text-blue-800 text-xs px-2 py-0.5 rounded-full font-bold">KENYA</span>
          </div>
          <nav className="hidden md:flex space-x-8 text-sm font-medium text-slate-600">
            <a href="#features" className="hover:text-blue-600 transition-colors">Features</a>
            <a href="#parameters" className="hover:text-blue-600 transition-colors">100+ Parameters</a>
            <a href="#security" className="hover:text-blue-600 transition-colors">Bank Security</a>
          </nav>
          <div className="flex items-center space-x-4">
            <Link href="/login" className="text-sm font-medium text-slate-600 hover:text-blue-600 transition-colors">
              Sign In
            </Link>
            <Link href="/login" className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold px-4 py-2 rounded-lg transition-colors shadow-sm">
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* 2. Hero Section */}
      <main>
        <section className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-16 text-center lg:text-left lg:flex lg:items-center lg:space-x-12">
          <div className="lg:w-1/2 space-y-6">
            <div className="inline-flex items-center space-x-2 bg-blue-50 border border-blue-100 px-3 py-1 rounded-full text-xs font-semibold text-blue-700">
              <span>🚀 Premium 2026 Algorithmic Upgrades Active</span>
            </div>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-black text-slate-900 tracking-tight leading-none">
              Bank-Grade Vehicle <span className="text-blue-600">Valuations</span> in Seconds.
            </h1>
            <p className="text-lg text-slate-600 max-w-xl mx-auto lg:mx-0">
              An advanced automated assessment matrix built for the Kenyan automotive market. Process 100+ live parameters including condition, local demand index, and service trends instantly.
            </p>
            <div className="pt-4 flex flex-col sm:flex-row justify-center lg:justify-start gap-4">
              <Link href="/login" className="bg-blue-600 hover:bg-blue-700 text-white text-base font-bold px-8 py-4 rounded-xl transition-all shadow-md hover:shadow-lg text-center">
                Evaluate Your Vehicle Now
              </Link>
              <a href="#features" className="bg-white border border-slate-300 hover:bg-slate-50 text-slate-700 text-base font-bold px-8 py-4 rounded-xl transition-all text-center">
                Explore Parameters
              </a>
            </div>
          </div>
          <div className="mt-12 lg:mt-0 lg:w-1/2 flex justify-center">
            {/* Visual Mockup Container replacing raw static images */}
            <div className="w-full max-w-md bg-white border border-slate-200 p-6 rounded-2xl shadow-xl space-y-6 transform lg:rotate-2">
              <div className="flex justify-between items-center border-b pb-4">
                <span className="font-mono text-sm font-bold bg-slate-100 px-2.5 py-1 rounded tracking-wide text-slate-700">KDK 123A</span>
                <span className="text-emerald-600 text-xs font-black bg-emerald-50 border border-emerald-100 px-2 py-0.5 rounded-full">VERIFIED</span>
              </div>
              <div className="space-y-2">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Asset Valuation Certificate</span>
                <p className="text-3xl font-black text-slate-900">KES 2,450,000</p>
              </div>
              <div className="grid grid-cols-2 gap-3 pt-2">
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <span className="text-[10px] font-bold text-slate-400 uppercase">Insurance Cush.</span>
                  <p className="text-sm font-bold text-slate-800">KES 2.69M</p>
                </div>
                <div className="bg-slate-50 p-3 rounded-lg border border-slate-100">
                  <span className="text-[10px] font-bold text-slate-400 uppercase">Forced Sale</span>
                  <p className="text-sm font-bold text-slate-800">KES 1.83M</p>
                </div>
              </div>
              <div className="bg-blue-50 border border-blue-100 p-3 rounded-lg flex items-center space-x-3">
                <div className="w-2 h-2 rounded-full bg-blue-600 animate-pulse"></div>
                <span className="text-xs font-medium text-blue-800">12 Document Vault Integrity Scores Safe</span>
              </div>
            </div>
          </div>
        </section>

        {/* 3. Feature Highlights Section */}
        <section id="features" className="bg-white border-t border-b border-slate-200 py-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center max-w-3xl mx-auto space-y-3 mb-12">
              <h2 className="text-3xl font-extrabold text-slate-900 tracking-tight">Engineered for absolute accuracy</h2>
              <p className="text-slate-600">Our machine infrastructure evaluates standard configurations against regional volatility indicators across Kenya.</p>
            </div>
            
            <div className="grid md:grid-cols-3 gap-8">
              <div className="p-6 border border-slate-100 rounded-xl bg-slate-50 space-y-3">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center font-bold text-blue-600">📊</div>
                <h3 className="text-lg font-bold text-slate-900">100+ Dynamic Metrics</h3>
                <p className="text-sm text-slate-600">Goes far beyond mileage. Tracks age degradation factors, compliance, and specific engine CC profiles effortlessly.</p>
              </div>
              <div className="p-6 border border-slate-100 rounded-xl bg-slate-50 space-y-3">
                <div className="w-10 h-10 bg-emerald-100 rounded-lg flex items-center justify-center font-bold text-emerald-600">🔒</div>
                <h3 className="text-lg font-bold text-slate-900">Legal Vault Security</h3>
                <p className="text-sm text-slate-600">All uploaded logbooks and asset receipts pass immediately into insulated private storage with Supabase Row Level Security guards.</p>
              </div>
              <div className="p-6 border border-slate-100 rounded-xl bg-slate-50 space-y-3">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center font-bold text-purple-600">🏛️</div>
                <h3 className="text-lg font-bold text-slate-900">Bank & Insurance Ready</h3>
                <p className="text-sm text-slate-600">Instantly structuralizes evaluations into matching forced-sale variables acceptable by premier local lending houses.</p>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* 4. Footer Wrapper */}
      <footer className="bg-slate-900 text-slate-400 py-8 border-t border-slate-800 text-center text-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <p>© {new Date().getFullYear()} AUTO-V Premium Assessment Systems. Powered by Next.js & Supabase Engine.</p>
        </div>
      </footer>
    </div>
  );
}
