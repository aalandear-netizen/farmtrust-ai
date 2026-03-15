import Head from 'next/head';
import Link from 'next/link';

export default function Home() {
  return (
    <>
      <Head>
        <title>FarmTrust AI – Agricultural Credit Intelligence</title>
        <meta name="description" content="AI-powered trust scoring for agricultural financial inclusion" />
      </Head>
      <main className="min-h-screen bg-gradient-to-br from-primary-800 to-primary-600 flex flex-col items-center justify-center text-white px-4">
        <div className="text-center max-w-3xl">
          <h1 className="text-5xl font-bold mb-4">🌾 FarmTrust AI</h1>
          <p className="text-xl text-primary-100 mb-8">
            AI-powered agricultural trust scoring for financial inclusion.
            Empowering farmers with access to credit, insurance, and government schemes.
          </p>
          <div className="flex gap-4 justify-center">
            <Link href="/dashboard" className="btn-primary bg-white text-primary-700 hover:bg-primary-50">
              Bank Dashboard →
            </Link>
            <a
              href="/docs"
              className="border border-white text-white hover:bg-white hover:text-primary-700 font-semibold py-2 px-4 rounded-lg transition-colors"
            >
              Documentation
            </a>
          </div>
          <div className="mt-16 grid grid-cols-3 gap-8 text-center">
            {[
              { stat: '12,000+', label: 'Farmers Onboarded' },
              { stat: '₹84 Cr', label: 'Loans Disbursed' },
              { stat: '97.7%', label: 'Repayment Rate' },
            ].map((item) => (
              <div key={item.label}>
                <p className="text-3xl font-bold">{item.stat}</p>
                <p className="text-primary-200 text-sm mt-1">{item.label}</p>
              </div>
            ))}
          </div>
        </div>
      </main>
    </>
  );
}
