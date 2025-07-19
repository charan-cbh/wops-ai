// Simple test to verify API connection
const axios = require('axios');

async function testAPI() {
  try {
    console.log('Testing API connection...');
    
    // Test basic connection
    const healthResponse = await axios.get('http://localhost:8001/health');
    console.log('✅ Backend health check:', healthResponse.data);
    
    // Test chat endpoint
    const chatResponse = await axios.post('http://localhost:8001/api/v1/chat', {
      message: 'How many agents under Gian Gabrillo have above 90% adherence?',
      conversation_history: []
    });
    
    console.log('✅ Chat API working!');
    console.log('Response keys:', Object.keys(chatResponse.data));
    console.log('Success:', chatResponse.data.success);
    console.log('Query results:', chatResponse.data.query_results);
    
  } catch (error) {
    console.error('❌ API test failed:', error.message);
    if (error.response) {
      console.error('Error response:', error.response.data);
    }
  }
}

testAPI();