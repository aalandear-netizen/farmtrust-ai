import { useQuery } from '@tanstack/react-query';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import Head from 'next/head';
import Link from 'next/link';
import { api } from '../../services/api';

const GRADE_COLORS: Record<string, string> = {
  AAA: '#16a34a', AA: '#22c55e', A: '#84cc16',
  BBB: '#eab308', BB: '#f97316', B: '#ef4444', C: '#dc2626', D: '#7f1d1d',
};

// ─── Mock summary data (replace with real API calls) ─────────────────────────
const mockStats = {
  totalFarmers: 12_847,
  avgTrustScore: 68.4,
  activeLoans: 3_412,
  totalDisbursed: 842_000_000,
  loanDefaultRate: 2.3,
  insurancePolicies: 8_921,
};

const gradeDistribution = [
  { grade: 'AAA', count: 1203 },
  { grade: 'AA', count: 2841 },
  { grade: 'A', count: 3210 },
  { grade: 'BBB', count: 2104 },
  { grade: 'BB', count: 1893 },
  { grade: 'B', count: 1012 },
  { grade: 'C', count: 451 },
  { grade: 'D', count: 133 },
];

const monthlyScoreTrend = Array.from({ length: 12 }, (_, i) => ({
  month: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][i],
  avgScore: 60 + Math.sin(i / 2) * 8 + i * 0.5,
}));

export default function DashboardPage() {
  return (
    <>
      <Head>
        <title>FarmTrust AI – Bank Dashboard</title>
        <meta name="description" content="Agricultural trust scoring dashboard for financial institutions" />
      </Head>

      <div className="min-h-screen bg-gray-50">
        {/* Sidebar */}
        <aside className="fixed inset-y-0 left-0 w-64 bg-primary-800 text-white flex flex-col">
          <div className="px-6 py-5 border-b border-primary-700">
            <h1 className="text-xl font-bold">🌾 FarmTrust AI</h1>
            <p className="text-xs text-primary-200 mt-1">Bank Portal</p>
          </div>
          <nav className="flex-1 px-4 py-6 space-y-1">
            {[
              { href: '/dashboard', label: '📊 Dashboard', active: true },
              { href: '/farmers', label: '👩‍🌾 Farmers' },
              { href: '/loans', label: '💰 Loans' },
              { href: '/insurance', label: '🛡️ Insurance' },
              { href: '/market', label: '🏪 Market' },
              { href: '/reports', label: '📈 Reports' },
              { href: '/audit', label: '🔍 Audit Logs' },
            ].map((item) => (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  item.active
                    ? 'bg-primary-600 text-white'
                    : 'text-primary-100 hover:bg-primary-700'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </aside>

        {/* Main Content */}
        <main className="ml-64 p-8">
          <div className="mb-8">
            <h2 className="text-2xl font-bold text-gray-900">Dashboard Overview</h2>
            <p className="text-gray-500 mt-1">AI-powered agricultural credit intelligence</p>
          </div>

          {/* Stats Grid */}
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
            <StatCard label="Total Farmers" value={mockStats.totalFarmers.toLocaleString()} icon="👩‍🌾" color="green" />
            <StatCard label="Avg Trust Score" value={`${mockStats.avgTrustScore.toFixed(1)}/100`} icon="⭐" color="blue" />
            <StatCard label="Active Loans" value={mockStats.activeLoans.toLocaleString()} icon="💰" color="purple" />
            <StatCard label="Total Disbursed" value={`₹${(mockStats.totalDisbursed / 1e7).toFixed(1)} Cr`} icon="🏦" color="yellow" />
            <StatCard label="Default Rate" value={`${mockStats.loanDefaultRate}%`} icon="⚠️" color="red" />
            <StatCard label="Insurance Policies" value={mockStats.insurancePolicies.toLocaleString()} icon="🛡️" color="teal" />
          </div>

          {/* Charts Row */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {/* Grade Distribution */}
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Trust Grade Distribution</h3>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={gradeDistribution}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="grade" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                    {gradeDistribution.map((entry) => (
                      <Cell key={entry.grade} fill={GRADE_COLORS[entry.grade]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Monthly Score Trend */}
            <div className="card">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Average Trust Score Trend</h3>
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={monthlyScoreTrend}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                  <XAxis dataKey="month" />
                  <YAxis domain={[50, 85]} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="avgScore"
                    stroke="#16a34a"
                    strokeWidth={2}
                    dot={{ fill: '#16a34a', r: 4 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Recent Farmers Table */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">High-Risk Alerts</h3>
              <Link href="/farmers" className="text-sm text-primary-600 hover:underline">View all →</Link>
            </div>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-gray-500 border-b border-gray-100">
                  <th className="pb-3 font-medium">Farmer</th>
                  <th className="pb-3 font-medium">State</th>
                  <th className="pb-3 font-medium">Trust Score</th>
                  <th className="pb-3 font-medium">Grade</th>
                  <th className="pb-3 font-medium">Active Loans</th>
                  <th className="pb-3 font-medium">Action</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { name: 'Ramesh Kumar', state: 'Maharashtra', score: 28, grade: 'D', loans: 2 },
                  { name: 'Sunita Devi', state: 'UP', score: 35, grade: 'C', loans: 1 },
                  { name: 'Mohan Singh', state: 'Punjab', score: 41, grade: 'B', loans: 3 },
                ].map((farmer) => (
                  <tr key={farmer.name} className="border-b border-gray-50 hover:bg-gray-50">
                    <td className="py-3 font-medium text-gray-900">{farmer.name}</td>
                    <td className="py-3 text-gray-600">{farmer.state}</td>
                    <td className="py-3">
                      <span className="font-semibold" style={{ color: GRADE_COLORS[farmer.grade] }}>
                        {farmer.score}
                      </span>
                    </td>
                    <td className="py-3">
                      <span className={`badge-grade-${farmer.grade.toLowerCase()}`}>{farmer.grade}</span>
                    </td>
                    <td className="py-3 text-gray-600">{farmer.loans}</td>
                    <td className="py-3">
                      <button className="text-xs text-primary-600 hover:underline font-medium">
                        Review
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </main>
      </div>
    </>
  );
}

function StatCard({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: string;
  icon: string;
  color: string;
}) {
  const colorMap: Record<string, string> = {
    green: 'bg-green-50 text-green-700',
    blue: 'bg-blue-50 text-blue-700',
    purple: 'bg-purple-50 text-purple-700',
    yellow: 'bg-yellow-50 text-yellow-700',
    red: 'bg-red-50 text-red-700',
    teal: 'bg-teal-50 text-teal-700',
  };
  return (
    <div className="card flex items-center gap-4">
      <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-2xl ${colorMap[color]}`}>
        {icon}
      </div>
      <div>
        <p className="text-sm text-gray-500">{label}</p>
        <p className="text-2xl font-bold text-gray-900">{value}</p>
      </div>
    </div>
  );
}
