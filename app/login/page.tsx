'use client';

import { useState } from 'react';
import { login, signup } from '@/lib/actions/auth';
import { useSearchParams } from 'next/navigation';

export default function LoginPage() {
  const [isSignUp, setIsSignUp] = useState(false);
  const searchParams = useSearchParams();
  const error = searchParams.get('error');
  const message = searchParams.get('message');

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4 py-12 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 bg-white p-8 rounded-xl shadow-lg border border-gray-100">
        
        {/* Header Block */}
        <div className="text-center">
          <h2 className="text-3xl font-extrabold text-gray-900 tracking-tight">
            {isSignUp ? 'Create your AUTO-V Account' : 'Sign in to AUTO-V Kenya'}
          </h2>
          <p className="mt-2 text-sm text-gray-600">
            Secure Bank & Insurance Grade Vehicle Valuation Engine
          </p>
        </div>

        {/* Dynamic System Alerts */}
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded text-sm text-center">
            {error}
          </div>
        )}
        {message && (
          <div className="bg-blue-50 border border-blue-200 text-blue-700 p-3 rounded text-sm text-center">
            {message}
          </div>
        )}

        {/* Interactive Form Processing Pipeline */}
        <form className="mt-8 space-y-4">
          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700">Email Address</label>
            <input
              id="email"
              name="email"
              type="email"
              required
              className="appearance-none rounded-lg relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-400 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
              placeholder="e.g. name@domain.co.ke"
            />
          </div>

          <div className="space-y-2">
            <label className="text-sm font-medium text-gray-700">Password</label>
            <input
              id="password"
              name="password"
              type="password"
              required
              className="appearance-none rounded-lg relative block w-full px-3 py-2 border border-gray-300 placeholder-gray-400 text-gray-900 focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
              placeholder="Minimum 6 characters"
            />
          </div>

          <div className="pt-2">
            {isSignUp ? (
              <button
                formAction={signup}
                className="w-full flex justify-center py-2.5 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 transition-colors"
              >
                Register Premium Account
              </button>
            ) : (
              <button
                formAction={login}
                className="w-full flex justify-center py-2.5 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              >
                Authenticate & Enter Dashboard
              </button>
            )}
          </div>
        </form>

        {/* Context Toggler Link */}
        <div className="text-center pt-2">
          <button
            onClick={() => setIsSignUp(!isSignUp)}
            className="text-sm font-medium text-blue-600 hover:text-blue-500 underline"
          >
            {isSignUp ? 'Already have an account? Sign In' : "Don't have an account? Register Now"}
          </button>
        </div>

      </div>
    </div>
  );
}
