# Worker Operations BI Chatbot

A business intelligence chatbot for Clipboard Health's Worker Operations team that provides data analysis and insights through natural language interactions.

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend API    │    │   Data Sources  │
│   (React/Next)  │◄──►│   (FastAPI)      │◄──►│   - Snowflake   │
│                 │    │                  │    │   - Confluence  │
│   Chat Interface│    │   AI Providers   │    │   - File Upload │
└─────────────────┘    │   - OpenAI       │    └─────────────────┘
                       │   - Claude       │
                       │   - Gemini       │
                       └──────────────────┘
                              │
                       ┌──────────────────┐
                       │   AWS Services   │
                       │   - ECS/Lambda   │
                       │   - RDS/DynamoDB │
                       │   - S3           │
                       └──────────────────┘
```

## Features

- **Multi-AI Provider Support**: Switchable between OpenAI, Claude, and Gemini
- **Data Integration**: Direct Snowflake connection for real-time queries
- **Business Context**: Confluence MCP server integration
- **File Upload**: Support for context files and documents
- **Business Intelligence**: Advanced analytics and trend analysis
- **AWS Deployment**: Scalable cloud infrastructure

## Technology Stack

- **Backend**: Python FastAPI
- **Frontend**: React/Next.js
- **Database**: Snowflake (primary), PostgreSQL (metadata)
- **AI Providers**: OpenAI, Anthropic Claude, Google Gemini
- **Infrastructure**: AWS (ECS, Lambda, RDS, S3)
- **Authentication**: AWS Cognito

## Project Structure

```
wops_ai/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   └── services/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   └── services/
│   ├── package.json
│   └── Dockerfile
├── infrastructure/
│   ├── aws/
│   └── terraform/
└── docs/
```

## Getting Started

1. Clone the repository
2. Set up backend dependencies
3. Configure environment variables
4. Set up frontend dependencies
5. Configure AI provider keys
6. Connect to Snowflake
7. Deploy to AWS

## Environment Variables

```
# AI Providers
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GOOGLE_API_KEY=

# Database
SNOWFLAKE_ACCOUNT=
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_WAREHOUSE=
SNOWFLAKE_DATABASE=

# AWS
AWS_REGION=
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=

# Confluence
CONFLUENCE_BASE_URL=
CONFLUENCE_API_TOKEN=
```