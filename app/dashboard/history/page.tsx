import { createClient } from '@/lib/supabase/server';
import Link from 'next/link';

export default async function HistoryPage() {
  const supabase = await createClient();

  // 1. Fetch authenticated user profile data from session cookie
  const { data: { user } } = await supabase.auth.getUser();

  // 2. Fetch valuations tied to this specific user (Enforced by Row Level Security)
  const { data: valuations, error } = await supabase
    .from('valuations')
    .select('id, registration_plate, make, model, year_built, final_market_value, created_at')
    .order('created_at', { ascending: false });

  if (error) {
    return <div className="p-6 text-red-600">Failed to load platform data rows.</div>;
  }

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-black text-gray-900">Valuation Reports Log</h1>
          <p className="text-sm text-gray-500">Your secure legal history dashboard profile</p>
        </div>
        <Link 
          href="/valuation/new" 
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-bold px-4 py-2 rounded-lg transition-colors"
        >
          + New Valuation
        </Link>
      </div>

      {valuations && valuations.length === 0 ? (
        <div className="border border-dashed rounded-xl p-12 text-center text-gray-400">
          No vehicle valuations found. Click "+ New Valuation" to calculate your first vehicle report.
        </div>
      ) : (
        <div className="bg-white border rounded-xl shadow-sm overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-gray-50 border-b text-xs font-semibold text-gray-500 uppercase tracking-wider">
                <th className="p-4">Date Generated</th>
                <th className="p-4">Plate No.</th>
                <th className="p-4">Vehicle Description</th>
                <th className="p-4">Market Value Assessed</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y text-sm text-gray-700">
              {valuations?.map((item) => (
                <tr key={item.id} className="hover:bg-gray-50 transition-colors">
                  <td className="p-4 whitespace-nowrap">
                    {new Date(item.created_at).toLocaleDateString('en-KE')}
                  </td>
                  <td className="p-4 font-mono font-bold text-blue-600 uppercase">
                    {item.registration_plate}
                  </td>
                  <td className="p-4 font-medium">
                    {item.year_built} {item.make} {item.model}
                  </td>
                  <td className="p-4 font-bold text-gray-900">
                    KES {Number(item.final_market_value).toLocaleString()}
                  </td>
                  <td className="p-4 text-right">
                    <Link
                      href={`/valuation/${item.id}`}
                      className="inline-flex items-center text-xs font-bold border rounded px-2.5 py-1.5 hover:bg-gray-100 transition-colors"
                    >
                      View Certificate
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
