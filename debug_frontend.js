// Debug script to check frontend configuration
console.log('Frontend Configuration Debug');
console.log('==========================');

// Check if the environment variable is being loaded
console.log('NEXT_PUBLIC_API_URL:', process.env.NEXT_PUBLIC_API_URL);

// Check what the API service is using
try {
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  console.log('API_BASE_URL:', API_BASE_URL);
} catch (e) {
  console.error('Error loading config:', e);
}

// Test if we can reach the backend
const testBackend = async () => {
  try {
    const response = await fetch('http://localhost:8001/health');
    const data = await response.json();
    console.log('Backend health check:', data);
  } catch (e) {
    console.error('Backend health check failed:', e);
  }
};

testBackend();