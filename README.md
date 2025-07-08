# Agricultural AI Agent System

LangChain-based AI agent for farm management using MongoDB and LINE messaging.

## Overview

This system provides intelligent farm management assistance through natural language interactions via LINE messaging. It helps farm workers with task management, pesticide recommendations, and automated scheduling.

## Features

- **Natural Language Processing**: Interact with the AI agent using natural Japanese
- **Task Management**: Automatic scheduling and tracking of farm tasks
- **Pesticide Recommendations**: AI-powered suggestions based on crop and field conditions
- **LINE Integration**: Seamless communication through LINE messaging
- **MongoDB Storage**: Efficient document-based data storage

## Setup

1. Clone the repository:
```bash
git clone https://github.com/tomiyasu0428/agri-ai-agent.git
cd agri-ai-agent
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.template .env
# Edit .env with your actual configuration
```

## Project Structure

```
src/
├── agri_ai/
│   ├── core/          # Core agent logic
│   ├── tools/         # LangChain tools
│   ├── models/        # Data models
│   ├── utils/         # Utilities
│   └── api/           # API endpoints
docs/                  # Documentation
```

## Development Status

🚧 This project is currently under development.

## License

MIT License