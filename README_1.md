# 📚 Research Agent Movius  

An intelligent **research assistant** that generates structured reports from user queries.  
It can:  
- Validate whether a query is a legitimate research question.  
- Explore multiple perspectives (angles).  
- Search the web + Wikipedia for sources.  
- Generate a structured markdown report.  
- Revise reports based on user feedback.  

---

## 🚀 Setup Instructions  

### 1. Clone the repo & install dependencies
```bash
git clone <your-repo-url>
cd research-agent
pip install -r requirements.txt
```

### 2. Environment variables  
Create a `.env` file in the root directory with:
```env
OPENAI_API_KEY=your_openai_key
LANGSMITH_API_KEY=your_langsmith_key
TAVILY_API_KEY=your_tavily_key   # optional, for Tavily web search
```

### 3. Run the agent  
```bash
python main.py
```

---

## 🏗️ Architecture & Reasoning Flow  

The agent is built using **LangGraph**.  

### 🔹 High-level flow
1. **User query** → classify:  
   - *New research?* → validation → generate angles.  
   - *Revise existing report?* → revision node.  
2. **Angle exploration** → subgraph searches (Wikipedia + Web).  
3. **Answer generation** → context gathered per angle.  
4. **Report writing** → structured markdown report.  
5. **Optional revisions** → user provides feedback → report updated.  

### 🔹 Graph overview  

```
User Query
   │
   ▼
 [decide] ────────────────► [revise] ──► END
   │
   ▼
 [validator] → (invalid?) → END
   │
   ▼
 [create_angles]
   │
   ▼
[search_one_angle] (Wikipedia + Web)
   │
   ▼
 [report] ────────────────────────────► END
```

### 🔹 Components
- **Agent.py** → main orchestration graph.  
- **search_tool.py** → sub-agent for retrieving and summarizing sources.  
- **main.py** → interactive CLI for queries.  

---

## 💡 Sample Interactions  

### Start Query
![Start Query](Screenshot%20start%20query.png)

### Generated Response
![Generated Response](Response.png)

### Revision Example
![Revision Example](Screenshot%20revision.png)

---

## 📂 Project Structure  

```
.
├── Agent.py          # Core research workflow
├── search_tool.py    # Web + Wikipedia search subgraph
├── main.py           # CLI interface
├── requirements.txt  # Dependencies
└── .env              # API keys (not committed)
```
