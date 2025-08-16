from langgraph.graph import StateGraph, END, START
from langgraph.types import Send
from typing import TypedDict, List
import operator
import os
from langchain_openai import ChatOpenAI
from langchain_community.document_loaders import WikipediaLoader
from dotenv import load_dotenv
from langchain_community.tools.tavily_search import TavilySearchResults
from typing import Annotated
from search_tool import search_agent,search_state
from langgraph.checkpoint.memory import MemorySaver
import uuid
from rich.console import Console
from rich.markdown import Markdown
# Load .env file from the current directory
load_dotenv()
# --- LANGSMITH CONFIG ---
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
# os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = "research-agent-movius"

# --- STATE ---
class ResearchState(TypedDict):
    query: str
    valid: bool
    angles: List[str]
    context: Annotated[list, operator.add]
    report: str
    action: str
    # angle: str  # for parallel search nodes

# --- LLM & TOOLS ---
llm = ChatOpenAI(model="gpt-5-nano", temperature=0)
# llm2 = ChatOpenAI(model="gpt-5-nano", temperature=0)

def decide_new_or_edit(state: ResearchState):
    """
    Use LLM to decide if the user query is asking to edit an existing report or to start new research.
    """
    if state.get("report"):
        prompt = f"""
        The user has provided the following query:
        {state['query']}

        If the user is asking to make edits, revisions, or updates to an existing report, answer with REVISE.
        If the user is asking a new research question, answer with NEW.
        Respond only with REVISE or NEW.
        """
        result = llm.invoke(prompt).content.strip().upper()
        state["action"] = "revise" if "REVISE" in result else "new"
    else:
        state["action"] = "new"
    return state

def new_or_edit(state: ResearchState):
    if state["action"] == "new":
        return "validator"
    else:
        return "revise"

# --- NODES ---
def validate_question(state: ResearchState):
    prompt = f"""
    Determine if the following is a legitimate academic/research question.
    Question: {state['query']}
    Respond only with 'YES' or 'NO' and one-line reasoning.
    """
    result = llm.invoke(prompt).content
    state["valid"] = result.strip().startswith("YES")
    return state
def Valid_condition(state: ResearchState):
    if state["valid"]:
        return "create_angles"
    else:
        print("Invalid question. Please ask legitimate academic/research question.")
        return END


def generate_angles(state: ResearchState):
    prompt = f"""
    Given this research question: "{state['query']}", list 3-5 distinct angles or perspectives to explore.
    Important:Do not exceed 5 perspectives. Let each perspective be one single line
    Give me the perspectives in a list format.
    Format:
    - Perspective 1
    - Perspective 2
    - Perspective 3
    - Perspective 4
    - Perspective 5
    """
    angles_text = llm.invoke(prompt).content
    # print(angles_text)
    state["angles"] = [a.strip("- ") for a in angles_text.split("\n") if a.strip()]
    return state

def search_angles(state: ResearchState):
    # print(state["angles"])
    return [Send("search_one_angle", {"perspective": angle, "question": state["query"], "answer":"", "context":[]}) for angle in state["angles"]]

# def search_one_angle(state: ResearchState):
#     travily_result = tavily_search.run(state["angle"])
#     wiki_result = wikipedia_tool.run(state["angle"])
#     combined_result = f"### {state['angle']}\nTravily: {travily_result}\nWikipedia: {wiki_result}"
#     return {"search_result": state.get("search_result", []) + [combined_result]}
# def collect_results(state: dict) -> dict:
#     # Merge subagent’s context into parent’s context
#     return {"context": state["context"]}


def write_report(state: ResearchState):
#     prompt = f"""
#     Your task is to create a short, easily digestible section of a report based on a set of source documents.
# - Introduction
# - Sections for each angle: 
# - Conclusion
# - Sources
# Based on these findings:
# {state['context']}
            
# Instructions:
# 1. Analyze the content of the source documents: 
# - The name of each source document is at the start of the document, with the <Document tag.
        
# 2. Create a report structure using markdown formatting:
# - Use ## for the section title
# - Use ### for sub-section headers
        
# 3. Write the report following this structure:
# a. Title (## header)
# b. Sections for each perspective (### header)
# c. Conclusion (### header)
# d. Sources (### header)

# 4. Make your title engaging

# 5. For the "Sections for each perspective" section:
# - Set up summary with general background / context related to the angle
# - Give a title to each perspective within the "Sections for each perspective" section
# - Do not metion Angle 1, Angle 2 etc. Just use the angle name as the section title and then write the section.
# - Emphasize what is novel, interesting, or surprising about insights gathered.
# - Create a numbered list of source documents, as you use them
# - Aim for approximately 500 words maximum
# - IMPORTANT:Use numbered sources in your report (e.g., [1], [2]) based on information from source documents. 
# - The list of sources should be present in the Sources section as per the instructions given.
# - IMPORTANT:These numbers should match the source link in the Sources section.
        
# 6. In the Sources section:
# - Include all sources used in your report
# - DO not explain the sources. Just add the link or document name.
# - Always make sure that there is only one numbered list of sources. 
# - The numbers should be the same as the numbers mentioned in the summary section. 
# - Provide full links to relevant websites or specific document paths
# - Separate each source by a newline. Use two spaces at the end of each line to create a newline in Markdown.
# - It will look like:

# ### Sources
# [1] Link or Document name
# [2] Link or Document name

# - Be sure to combine sources. For example this is not correct:

# [3] https://ai.meta.com/blog/meta-llama-3-1/
# [4] https://ai.meta.com/blog/meta-llama-3-1/

# There should be no redundant sources. It should simply be:

# [3] https://ai.meta.com/blog/meta-llama-3-1/

# - Be concise when listing sources(less than 15 words per source).

# 7. Final review:
# - Ensure the report follows the required structure
# - Include no preamble before the title of the report
# - Check that all guidelines have been followed
#     """

    prompt = f"""
    You are a technical writer creating a report on this overall topic: 

{state['query']}

1. You are given documents that explore the below perspective of the topic:
{state['angles']}

2. You are to write a report based on the context/memos provided.

Your task: 

1. You will be given a collection of memos.
2. Think carefully about the insights from each memo.
3. Consolidate these into a crisp overall summary that ties together the central ideas from all of the memos. 
4. Summarize the central points in each memo into a cohesive single narrative.

To format your report:
 
1. Use markdown formatting. 
2. Make your title for the complete report engaging. Use # <Title> format.
3. Include an introduction for the report.
4. Use sub-heading for each perspective. 
5. After introduction, start your report with a single title header: ## Insights
6. IMPORTANT:Preserve any citations in the memos, which will be annotated in brackets, for example [1] or [2].
7. Mention the list of sources after every perspective with the number intact. For example:

# Perspective 1
<passage 1> [1] 
<passage 2> [2][3]

### Sources:
[1] Source 1
[2] Source 2
[3] Source 3

Here are the memos to build your report from: 

{state['context']}

"""
    state["report"] = llm.invoke(prompt).content
    return state

def revise_report(state: ResearchState):
    if state["action"] == "revise":
        prompt = f""" You are an expert in academic writing. You are to revise the report based on the feedback.
    Current report:
    {state['report']}

    Revise according to this feedback:
    {state['query']}

    Instructions:
    - Do not change anything about the format, structure, sources, etc. unless it is specifically asked in the query.
    - Make sure any revision is in line with the original report. 
    - Make sure the report is still in markdown format inline with the original report.
    - The structure of the report must not be changed unless it is specifically asked in the query.
    - If additional sections are asked, add them to the summary section. If required rewrite the introduction and conclusion sections.
    - Do not remove any sections from the report unless it is specifically asked in the query.
    """
        state["report"] = llm.invoke(prompt).content
    return state

# --- GRAPH ---
graph = StateGraph(ResearchState)
graph.add_node("decide", decide_new_or_edit)
graph.add_node("validator", validate_question)
graph.add_node("create_angles", generate_angles)
graph.add_node("search_one_angle", search_agent)
graph.add_node("report", write_report)
graph.add_node("revise", revise_report)

graph.add_edge(START, "decide")
graph.add_conditional_edges("decide", new_or_edit, ["validator", "revise"])
graph.add_conditional_edges("validator",Valid_condition, ["create_angles", END])
graph.add_conditional_edges("create_angles", search_angles)
graph.add_edge("search_one_angle", "report")
graph.add_edge("report", END)
graph.add_edge("revise", END)


memory = MemorySaver()
research_agent = graph.compile(checkpointer=memory)

# --- RUN ---
# thread_id = str(uuid.uuid4())
# config = {"configurable": {"thread_id": thread_id}}
# # First run — full research process
# research_agent.invoke(
#     {"query": "Impact of microplastics on marine biodiversity"},
#     config=config
# )

# console = Console()
# final_state = research_agent.get_state(config)
# report = final_state.values.get('report')
# console.print(Markdown(report))

# # # Second run — same thread, user gives revision request
# research_agent.invoke(
#     {"query": "Can you make the introduction shorter and exciting?"},
#     config=config
# )

# # Continue
# # for event in graph.stream({"query": "Impact of microplastics on marine biodiversity"}, thread, stream_mode="values"):
# #     print("--Node--")
# #     report = event.get('report', '')
# #     print(report)

# final_state = research_agent.get_state(config)
# report = final_state.values.get('report')
# console.print(Markdown(report))
