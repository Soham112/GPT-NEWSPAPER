# XLR8 Research

Welcome to the XLR8 Research project, an innovative autonomous agent designed to create personalized newspapers tailored to user preferences. XLR8 Research revolutionizes the way we consume news by leveraging the power of AI to curate, write, design, and edit content based on individual tastes and interests.

## 🔍 Overview

XLR8 Research consists of six specialized sub-agents in LangChain's new [LangGraph Library](https://github.com/langchain-ai/langgraph):

1. **Search Agent**: Scours the web for the latest and most relevant news.
2. **Curator Agent**: Filters and selects news based on user-defined preferences and interests.
3. **Writer Agent**: Crafts engaging and reader-friendly articles.
4. **Critique Agent** Provide feedback to the writer until article is approved.
5. **Designer Agent**: Layouts and designs the articles for an aesthetically pleasing reading experience.
6. **Editor Agent**: Constructs the newspaper based on produced articles.
7. **Publisher Agent** Publishes the newspaper to the frontend or desired service

Each agent plays a critical role in delivering a unique and personalized newspaper experience.

<div align="center">
<img align="center" height="500" src="https://tavily-media.s3.amazonaws.com/gpt-newspaper-architecture.png">
</div>


## Demo
https://github.com/assafelovic/gpt-newspaper/assets/91344214/7f265369-1293-4d95-9be5-02070f12c67e


## 🌟 Features

- **Personalized Content**: Get news that aligns with your interests and preferences.
- **Diverse Sources**: Aggregates content from a wide range of reputable news sources.
- **Engaging Design**: Enjoy a visually appealing layout and design.
- **Quality Assurance**: Rigorous editing ensures reliable and accurate news reporting.
- **User-Friendly Interface**: Easy-to-use platform for setting preferences and receiving your newspaper.
- **Outreach Agent**: Chat-like interface for outreach analytics powered by Amazon Bedrock Agent (LinkedIn, Email, Calls, HubSpot).

## 🛠️ How It Works

1. **Setting Preferences**: Users input their interests, preferred topics, and news sources.
2. **Automated Curation**: The Search and Curator Agents find and select news stories.
3. **Content Creation**: The Writer Agent drafts articles, which are then designed by the Designer Agent.
4. **Newspaper Design**: The Editor Agent reviews and finalizes the content.
5. **Delivery**: Users receive their personalized newspaper to their mailbox.

## 🚀 Getting Started

### Prerequisites

- Tavily API Key - [Sign Up](https://tavily.com/)
- Groq API Key - [Sign Up](https://console.groq.com/) (for XLR8 Research)
- AWS Account with Bedrock Access (for Outreach Agent)
  - Bedrock Agent ID and Alias ID
  - IAM permissions (see IAM Requirements below)

### Installation

1. Clone the repo
   ```sh
   git clone https://github.com/rotemweiss57/gpt-newspaper.git
    ```
2. Create `.env` file (copy from `.env.example`):
   ```sh
   cp .env.example .env
   ```
   
   Edit `.env` and add your API keys:
   ```sh
   GROQ_API_KEY=your_groq_api_key
   TAVILY_API_KEY=your_tavily_api_key
   AWS_REGION=us-east-1
   BEDROCK_OUTREACH_AGENT_ID=your_agent_id
   BEDROCK_OUTREACH_ALIAS=your_alias_id
   USE_STREAMING=false
   ```
3. Install Requirements
   ```sh
   pip install -r requirements.txt
   ```
4. Run the app
   ```sh
    python app.py
    ```
5. Open the app in your browser
   ```sh
    http://localhost:3000/
    ```
6. Enjoy!

## 📊 Outreach Agent

The Outreach Agent provides a chat-like interface for analyzing outreach metrics across LinkedIn, Email, Calls, and HubSpot activities. It's powered by Amazon Bedrock Agent and provides real-time insights with KPI tracking.

### Features

- **Chat Interface**: Natural language queries about outreach performance
- **KPI Dashboard**: Real-time tracking of LinkedIn Outreach, Email Campaigns, Calls Placed, and HubSpot Activities
- **Source Citations**: Transparent source references for all insights
- **Session Management**: Maintains conversation context across queries

### Access

Navigate to the Outreach Agent from the main page by clicking the "Outreach Agent" button, or visit `/outreach.html` directly.

### API Endpoints

- `POST /api/outreach/ask` - Non-streaming query endpoint
- `POST /api/outreach/ask/stream` - Streaming query endpoint (requires `USE_STREAMING=true`)
- `GET /api/outreach/healthz` - Health check endpoint

### IAM Requirements

The AWS IAM role/user running the application needs the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeAgent"
      ],
      "Resource": "arn:aws:bedrock:*:*:agent/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel"
      ],
      "Resource": "arn:aws:bedrock:*:*:foundation-model/*"
    }
  ]
}
```

**Note**: The Bedrock Agent itself may have additional permissions configured (e.g., S3 access for knowledge base) through its execution role. These are managed separately in the Bedrock Agent configuration.

### Response Format

The Outreach Agent follows a structured response format:

1. **Insights**: 3-6 bullet points with key findings
2. **KPIs Line** (optional): `KPIs: LinkedIn: <n> | Email: <n> | Calls: <n> | HubSpot: <n>`
3. **Sources Line**: `Sources: <id1>, <id2>, <id3>`

The frontend automatically parses and displays KPIs in the dashboard and sources as chips.
