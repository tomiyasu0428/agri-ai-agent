# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is an agricultural AI agent system (Agri_AI2) designed to assist ostrich farm operations through intelligent task management and decision support. The system integrates LangChain agents with MongoDB Atlas to provide natural language interfaces for farm management via LINE messaging.

## Architecture

### Core Components
- **AI Agent**: LangChain-based agent with specialized agricultural tools
- **Database**: MongoDB Atlas for NoSQL document storage
- **Interface**: LINE Messaging API for user interaction
- **Infrastructure**: Google Cloud Functions (webhooks) + Google Cloud Run (agent execution)

### Key Technologies
- **Language**: Python 3.9+
- **AI Framework**: LangChain with OpenAI GPT-4 or Anthropic Claude
- **Database**: MongoDB Atlas
- **Messaging**: LINE Messaging API
- **Cloud**: Google Cloud (Functions, Run, Secret Manager)

## Development Commands

Since this is a planning-stage project, no specific build/test commands are established yet. The project documentation indicates the following intended setup:

```bash
# Environment setup (planned)
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Dependencies (planned)
pip install langchain==0.1.0 langchain-openai==0.0.5 pymongo==4.6.1 motor==3.3.2
pip install google-cloud-functions-framework==3.5.0 google-cloud-secret-manager==2.18.1
pip install line-bot-sdk==3.5.0 python-dotenv==1.0.0 pytest==7.4.3
```

## Project Structure

This project is currently in the planning and documentation phase. The main components are:

### Documentation (`docs/`)
- **農業管理AIエージェント 要件定義書**: Complete requirements specification including technical architecture, functional requirements, and implementation phases
- **アグリエージェント_ペルソナとユーザーストーリー**: User personas and stories defining the target users and their needs
- **タスクリスト**: Detailed task breakdown for development phases
- **エージェントの精度をどうあげるか？**: Technical considerations for improving agent accuracy

### Planned Architecture
The system will be organized around three main phases:

1. **Phase 1: Foundation** - LangChain + MongoDB setup, basic agent
2. **Phase 2: Intelligence** - Agricultural-specific tools and LINE integration  
3. **Phase 3: Production** - Deployment and operational monitoring

## Key Features (Planned)

### Agricultural Tools
- Task management (`get_today_tasks`, `complete_task`)
- Field status monitoring (`get_field_status`)
- Pesticide recommendation (`recommend_pesticide`)
- Automatic scheduling (`auto_schedule_next`)
- Legacy data access for Airtable migration

### User Personas
- **新人作業員 (Novice Worker)**: Needs step-by-step guidance
- **ベテラン作業員 (Veteran Worker)**: Wants efficiency and data validation
- **農場管理者 (Farm Manager)**: Requires analytics and standardization

## Data Model (Planned)

### MongoDB Collections
- `daily_schedules`: Daily work plans and task completion
- `field_management`: Field information, crop data, pesticide history
- `worker_profiles`: User authentication and role management

### Integration Points
- LINE Messaging API for user interaction
- Weather API for agricultural recommendations
- Airtable migration for existing data

## Development Notes

- The project emphasizes natural language processing for agricultural contexts
- Focus on reducing cognitive load for farm workers
- Implements automatic task scheduling based on agricultural cycles
- Designed for 24/7 operation with high availability requirements
- Security managed through Google Secret Manager

## Current Status

This is a greenfield project in the planning phase. No code has been implemented yet, but comprehensive requirements and architecture documentation exists in Japanese.