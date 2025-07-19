import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import { CheckCircleIcon, XCircleIcon, EnvelopeIcon } from '@heroicons/react/24/outline';
import { APIService } from '../services/api';

export default function EmailVerificationPage() {
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('');
  const router = useRouter();

  const { email, token } = router.query;

  useEffect(() => {
    if (email && token) {
      verifyEmail();
    }
  }, [email, token]);

  const verifyEmail = async () => {
    try {
      const result = await APIService.verifyEmail(email as string, token as string);
      setStatus('success');
      setMessage(result.message || 'Email verified successfully!');
      
      // Redirect to set password after 3 seconds
      setTimeout(() => {
        router.push(`/set-password?email=${encodeURIComponent(email as string)}&token=${encodeURIComponent(token as string)}`);
      }, 3000);
    } catch (err: any) {
      setStatus('error');
      setMessage(err.response?.data?.detail || err.message || 'Email verification failed');
    }
  };

  const handleContinue = () => {
    if (status === 'success') {
      router.push(`/set-password?email=${encodeURIComponent(email as string)}&token=${encodeURIComponent(token as string)}`);
    } else {
      router.push('/');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl p-8 max-w-md w-full shadow-2xl">
        <div className="text-center">
          {status === 'loading' && (
            <>
              <div className="animate-spin rounded-full h-16 w-16 border-4 border-blue-200 border-t-blue-600 mx-auto mb-4"></div>
              <h1 className="text-2xl font-bold text-gray-900 mb-2">Verifying Email</h1>
              <p className="text-gray-600">
                Please wait while we verify your email address...
              </p>
            </>
          )}

          {status === 'success' && (
            <>
              <CheckCircleIcon className="h-16 w-16 text-green-500 mx-auto mb-4" />
              <h1 className="text-2xl font-bold text-gray-900 mb-2">Email Verified!</h1>
              <p className="text-gray-600 mb-6">
                {message}
              </p>
              <p className="text-sm text-gray-500 mb-6">
                You'll be redirected to set your password in a moment, or click the button below to continue.
              </p>
              <button
                onClick={handleContinue}
                className="bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 px-6 rounded-lg font-medium hover:from-blue-700 hover:to-purple-700 transition-all duration-200"
              >
                Set Password Now
              </button>
            </>
          )}

          {status === 'error' && (
            <>
              <XCircleIcon className="h-16 w-16 text-red-500 mx-auto mb-4" />
              <h1 className="text-2xl font-bold text-gray-900 mb-2">Verification Failed</h1>
              <p className="text-gray-600 mb-6">
                {message}
              </p>
              <div className="space-y-3">
                <button
                  onClick={handleContinue}
                  className="w-full bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 px-4 rounded-lg font-medium hover:from-blue-700 hover:to-purple-700 transition-all duration-200"
                >
                  Back to Home
                </button>
                <p className="text-sm text-gray-500">
                  If you're having trouble, please contact support or try registering again.
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}