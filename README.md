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

### Research Agent
- **ChatGPT-Style Interface**: Modern chat-based UI with message history and dynamic layout
- **Grounded Citations**: Every research bullet cites real sources with clickable references
- **Market Insights**: Automatic generation of market overview, key segments, opportunities, and risks
- **ICP-Aware Recommendations**: Tailored marketing plays when client metadata is provided
- **Real-Time Research**: Search, curate, and generate insights from recent news (week/month timeframes)
- **Domain Filtering**: Optional filtering by specific domains or verticals
- **Quality Assurance**: Automatic citation validation and quality checks

### Outreach Agent
- **Client Dashboards**: Comprehensive KPI tracking with trend indicators
- **RAG-Powered Chat**: Natural language queries about outreach performance using custom FAISS vector store
- **Multi-Channel Analytics**: Track LinkedIn, Email, Calls, and HubSpot activities
- **Contact Management**: Full contact table with status, channels, and engagement tracking
- **Activity Timeline**: Visual timeline of outreach activities with filtering
- **S3 Data Integration**: Loads client data, metrics, and activities from S3

### Platform Features
- **Unified Navigation**: Platform header with consistent navigation across all pages
- **Landing Page**: Feature tiles for quick access to Research Agent, Outreach Agent, Integrations, and Settings
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Modern UI**: Light theme with blue accents, clean typography, and ChatGPT-inspired layouts

## 🛠️ How It Works

1. **Setting Preferences**: Users input their interests, preferred topics, and news sources.
2. **Automated Curation**: The Search and Curator Agents find and select news stories.
3. **Content Creation**: The Writer Agent drafts articles, which are then designed by the Designer Agent.
4. **Newspaper Design**: The Editor Agent reviews and finalizes the content.
5. **Delivery**: Users receive their personalized newspaper to their mailbox.

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+** and **Node.js 18+**
- **Tavily API Key** - [Sign Up](https://tavily.com/)
- **Groq API Key** - [Sign Up](https://console.groq.com/) (for XLR8 Research)
- **AWS Account** (for Outreach Agent RAG system and S3 data)
  - S3 bucket access for knowledge base and client data
  - IAM permissions for S3 read access

### Installation

1. **Clone the repository**
   ```sh
   git clone https://github.com/rotemweiss57/gpt-newspaper.git
   cd gpt-newspaper
   ```

2. **Set up Python backend**
   ```sh
   # Create virtual environment (recommended)
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install Python dependencies
   pip install -r requirements.txt
   ```

3. **Set up Next.js frontend**
   ```sh
   cd frontend
   npm install
   cd ..
   ```

4. **Configure environment variables**
   
   Create `.env` file in the root directory:
   ```sh
   cp .env.example .env
   ```
   
   Edit `.env` and add your API keys:
   ```env
   # Required for Research Agent
   GROQ_API_KEY=your_groq_api_key
   TAVILY_API_KEY=your_tavily_api_key
   
   # Required for Outreach Agent (RAG system)
   S3_BUCKET=project-xlr8
   S3_OUTREACH_PREFIX=outreach-agent/
   FAISS_PERSIST_DIR=faiss_store
   USE_STREAMING=false
   
   # Optional: Frontend backend URL (defaults to http://localhost:8000)
   NEXT_PUBLIC_BACKEND_URL=http://localhost:8000
   ```

5. **Run the application**

   **Option A: Development (Recommended)**
   
   Open two terminal windows:
   
   **Terminal 1 - Backend:**
   ```sh
   python3 run_backend.py
   ```
   Backend runs on `http://localhost:8000`
   
   **Terminal 2 - Frontend:**
   ```sh
   cd frontend
   npm run dev
   ```
   Frontend runs on `http://localhost:3000`
   
   **Option B: Legacy Flask Frontend (Alternative)**
   ```sh
   python3 app.py
   ```
   This runs both frontend (port 3000) and backend (port 8000) using multiprocessing.

6. **Open the application**
   ```sh
   http://localhost:3000/
   ```

7. **Enjoy!**

## 📊 Platform Pages

### Landing Page (`/`)
The main entry point featuring:
- **Hero Section**: Welcome message and platform overview
- **Feature Tiles**: Quick access to Research Agent, Outreach Agent, Integrations, and Settings
- **Recent Activity**: Placeholder for recent activity timeline (coming soon)

### Research Agent (`/research`)
ChatGPT-style research interface:
- **Dynamic Header**: "XLR8 Research" title and "Outreach Agent" button (hidden after first response)
- **Centered Initial Input**: Search bar centered on page initially
- **Chat Interface**: User messages (blue bubbles) and assistant responses (white cards) after first query
- **Fixed Bottom Input**: Search bar moves to bottom after first response for follow-up queries
- **Result Cards**: Full research results with headlines, tags, bullets, citations, insights, and sources
- **Typography Standards**: 
  - Page title: `text-4xl` (~36px)
  - Headlines: `text-2xl` (~22-24px)
  - Body text: `text-base` (~16px)
  - Tags/buttons: `text-sm` (~14px)

### Outreach Agent (`/outreach.html`)
Marketing campaigns dashboard:
- **Platform Header**: Consistent navigation across all pages
- **Client Selection**: Dropdown to select and switch between clients
- **KPI Tiles**: LinkedIn Outreach, Email Campaigns, Calls Placed, HubSpot Activities with trend indicators
- **Client Summary**: Snapshot of decision makers, activities, follow-ups, and engagement score
- **Contacts Table**: Full contact list with status, channels, and last contacted
- **Activity Timeline**: Visual timeline with channel, status, and time filters
- **RAG Chat Interface**: Natural language queries about outreach performance

### Integrations (`/integrations`)
Placeholder page for future integrations (LinkedIn, Apollo, HubSpot, etc.)

### Settings (`/settings`)
Placeholder page for workspace settings, profile, and API keys

## 📊 Outreach Agent Details

The Outreach Agent uses a **custom RAG system** (FAISS vector store + Groq LLM) instead of Amazon Bedrock Agent for faster, more cost-effective responses.

### RAG System Architecture

- **Knowledge Base**: JSONL files loaded from S3 (`kb_outreach_activities.jsonl`)
- **Vector Store**: FAISS index with Sentence Transformers embeddings (`all-MiniLM-L6-v2`)
- **LLM**: Groq `llama-3.1-8b-instant` for response generation
- **Persistence**: Index saved to `faiss_store/` directory for fast subsequent loads

### Features

- **Chat Interface**: Natural language queries about outreach performance
- **KPI Dashboard**: Real-time tracking with trend indicators (percentage change vs last month)
- **Client Data**: Loads from S3 CSV files (companies, metrics, activities, contacts, campaigns)
- **Source Citations**: Transparent source references for all insights
- **Session Management**: Maintains conversation context across queries

### API Endpoints

- `POST /api/outreach/ask` - Non-streaming query endpoint
- `POST /api/outreach/ask/stream` - Streaming query endpoint (requires `USE_STREAMING=true`)
- `POST /api/outreach/rebuild-index` - Rebuild FAISS index from S3 knowledge base
- `GET /api/outreach/clients` - List all clients
- `GET /api/outreach/clients/<client_id>` - Get client data with optional filters
- `GET /api/outreach/healthz` - Health check endpoint

### AWS Requirements

The application needs S3 read access for:
- Knowledge base files: `s3://<bucket>/outreach-agent/kb_outreach_activities.jsonl`
- Client data CSV files: `s3://<bucket>/outreach-agent/*.csv`

Configure AWS credentials via:
- AWS CLI: `aws configure`
- Environment variables: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
- IAM role (if running on EC2/ECS)

### Response Format

The Outreach Agent follows a structured response format:

1. **Insights**: 3-6 bullet points with key findings
2. **KPIs Line** (optional): `KPIs: LinkedIn: <n> | Email: <n> | Calls: <n> | HubSpot: <n>`
3. **Sources Line**: `Sources: <id1>, <id2>, <id3>`

The frontend automatically parses and displays KPIs in the dashboard and sources as chips.
