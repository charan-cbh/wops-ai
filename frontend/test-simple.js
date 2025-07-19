// Simple test using regular OpenAI API
const axios = require('axios');

async function testOpenAI() {
  try {
    console.log('Testing OpenAI API directly...');
    const response = await axios.post('https://api.openai.com/v1/chat/completions', {
      model: 'gpt-4',
      messages: [
        {
          role: 'system',
          content: 'You are a helpful assistant that generates SQL queries.'
        },
        {
          role: 'user',
          content: 'Generate a SQL query to count agents under a specific supervisor with high adherence.'
        }
      ],
      max_tokens: 200,
      temperature: 0.1
    }, {
      headers: {
        'Authorization': `Bearer ${process.env.OPENAI_API_KEY}`,
        'Content-Type': 'application/json'
      },
      timeout: 30000
    });
    
    console.log('✅ OpenAI API response:', response.data.choices[0].message.content);
    
  } catch (error) {
    console.error('❌ OpenAI API error:', error.message);
    if (error.response) {
      console.error('Status:', error.response.status);
      console.error('Data:', error.response.data);
    }
  }
}

testOpenAI();