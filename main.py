import Agent
from rich.console import Console
from rich.markdown import Markdown
import uuid

console = Console()
thread_id = str(uuid.uuid4())
config = {"configurable": {"thread_id": thread_id}}
print("Welcome to the Research Agent Movius! Type 'exit' to quit.\n")
while True:
    query = input("Query: ")

    if query == "exit":
        print("Exiting program. Bye!")
        break
    Agent.research_agent.invoke({"query": query}, config=config)
    final_state = Agent.research_agent.get_state(config)
    report = final_state.values.get('report')
    console.print(Markdown(report))


