from langgraph.graph import StateGraph, END, START
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
from langchain_community.document_loaders import WikipediaLoader
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_openai import ChatOpenAI
from typing import TypedDict, Annotated
from pydantic import BaseModel, Field
import operator
import os

# Load .env file from the current directory
load_dotenv()
# --- LANGSMITH CONFIG ---
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
os.environ["TAVILY_API_KEY"] = os.getenv("TAVILY_API_KEY")
os.environ["LANGSMITH_TRACING"] = "true"
os.environ["LANGSMITH_PROJECT"] = "research-agent-movius"

llm = ChatOpenAI(model="gpt-5-nano", temperature=0)
# tavily_search = TavilySearchResults(max_results=3)

class search_state(TypedDict):
    question: str
    perspective: str
    answer: str
    search_result: Annotated[list, operator.add]
    context: Annotated[list, operator.add]
class SearchQuery(BaseModel):
    search_query: str = Field(None, description="Search query for retrieval.")

search_instructions = SystemMessage(content=f"""You will be given a question and the angle related to the question. 

Your goal is to generate a well-structured query for use in web-search related to the angle for the topic.
        
First, analyze the topic.

Pay particular attention to the angle.

Convert this final question into a well-structured web search query based on the perspective
The search query should be a single line of text and should be concise(less than 20 words)
""")

def search_web(state: search_state):
    
    """ Retrieve docs from web search """
    # print(state)
    
    tavily_search = TavilySearchResults(max_results=3)
    # Search query
    structured_llm = llm.with_structured_output(SearchQuery)
    search_query = structured_llm.invoke([search_instructions]+[state['question']] + [state['perspective']])
    
    # Search
    search_docs = tavily_search.invoke(search_query.search_query)
    # print('search_query:',search_query.search_query)
    # print('search_docs:',search_docs)
     # Format
    formatted_search_docs = "\n\n---\n\n".join(
        [
            f'<Document href="{doc["url"]}"/>\n{doc["content"]}\n</Document>'
            for doc in search_docs
        ]
    )
    # print('search done')
    return {"search_result": [formatted_search_docs]} 

def search_wikipedia(state: search_state):
    
    """ Retrieve docs from wikipedia """

    # Search query
    structured_llm = llm.with_structured_output(SearchQuery)
    search_query = structured_llm.invoke([search_instructions]+[state['question']] + [state['perspective']])
    
    # Search
    search_docs = WikipediaLoader(query=search_query.search_query, 
                                  load_max_docs=2).load()

     # Format
    formatted_search_docs = "\n\n---\n\n".join(
        [
            f'<Document source="{doc.metadata["source"]}" page="{doc.metadata.get("page", "")}"/>\n{doc.page_content}\n</Document>'
            for doc in search_docs
        ]
    )
    # print('wikipedia search done')
    return {"search_result": [formatted_search_docs]} 

def generate_answer(state: search_state):
    
    """ Node to answer a question """

    answer_instructions = f"""You are an expert research analyst.
        
Your goal is to research and answer {state['question']} from the perspective {state['perspective']}.

To answer question, use this context:
        
{state['search_result']}

When answering questions, follow these guidelines:
        
1. Use only the information provided in the context. 
        
2. Do not introduce external information or make assumptions beyond what is explicitly stated in the context.

3. The context contain sources at the topic of each individual document.

4. Include these sources your answer next to any relevant statements. For example, for source # 1 use [1]. 

5. List your sources in order at the bottom of your answer. [1] Source 1, [2] Source 2, etc. Be consise when listing sources(less than 15 words per source).
        
6. If the source is: <Document source="assistant/docs/llama3_1.pdf" page="7"/>' then just list: 
        
[1] assistant/docs/llama3_1.pdf, page 7 
        
And skip the addition of the brackets as well as the Document source preamble in your citation."""

    # Get state
    # messages = state["messages"]
    # context = state["context"]

    # Answer question
    system_message = answer_instructions
    answer = llm.invoke([HumanMessage(content=system_message)])
            
    # Name the message as coming from the expert
    # answer.name = "expert"
    
    # Append it to state
    # print('answer done')
    # print("aaaa",answer.content)
    # print("type a",type(answer.content))
    # print("bbbb",state["context"])
    # print("type b",type(state["context"]))
    # print('answer done')
    return {"context": state["context"] + [answer.content]}

# section_writer_instructions = """You are an expert technical writer. 
            
# Your task is to create a short, easily digestible section of a report based on a set of source documents.

# 1. Analyze the content of the source documents: 
# - The name of each source document is at the start of the document, with the <Document tag.
        
# 2. Create a report structure using markdown formatting:
# - Use ## for the section title
# - Use ### for sub-section headers
        
# 3. Write the report following this structure:
# a. Title (## header)
# b. Summary (### header)
# c. Sources (### header)

# 4. Make your title engaging based upon the focus area of the analyst: 
# {angle}

# 5. For the summary section:
# - Set up summary with general background / context related to the focus area of the analyst
# - Emphasize what is novel, interesting, or surprising about insights gathered.
# - Create a numbered list of source documents, as you use them
# - Do not mention the names of interviewers or experts
# - Aim for approximately 400 words maximum
# - Use numbered sources in your report (e.g., [1], [2]) based on information from source documents
        
# 6. In the Sources section:
# - Include all sources used in your report
# - Provide full links to relevant websites or specific document paths
# - Separate each source by a newline. Use two spaces at the end of each line to create a newline in Markdown.
# - It will look like:

# ### Sources
# [1] Link or Document name
# [2] Link or Document name

# 7. Be sure to combine sources. For example this is not correct:

# [3] https://ai.meta.com/blog/meta-llama-3-1/
# [4] https://ai.meta.com/blog/meta-llama-3-1/

# There should be no redundant sources. It should simply be:

# [3] https://ai.meta.com/blog/meta-llama-3-1/
        
# 8. Final review:
# - Ensure the report follows the required structure
# - Include no preamble before the title of the report
# - Check that all guidelines have been followed"""

# def write_section(state: InterviewState):

#     """ Node to answer a question """

#     # Get state
#     context = state["context"]
#     angle = state["angle"]
   
#     # Write section using either the gathered source docs from interview (context) or the interview itself (interview)
#     system_message = section_writer_instructions.format(angle=angle)
#     section = llm.invoke([SystemMessage(content=system_message)]+[HumanMessage(content=f"Use this source to write your section: {context}")]) 
                
#     # Append it to state
#     return {"sections": [section.content]}

# Add nodes
search_builder = StateGraph(search_state)

# Initialize each node with node_secret 
search_builder.add_node("search_web",search_web)
search_builder.add_node("search_wikipedia", search_wikipedia)
search_builder.add_node("generate_answer", generate_answer)

# Flow
search_builder.add_edge(START, "search_wikipedia")
search_builder.add_edge(START, "search_web")
search_builder.add_edge("search_wikipedia", "generate_answer")
search_builder.add_edge("search_web", "generate_answer")
search_builder.add_edge("generate_answer", END)

memory = MemorySaver()


search_agent = search_builder.compile(checkpointer=memory)

# search_agent.invoke({"question": "What is the impact of microplastics on marine biodiversity?",
# "perspective": "Trophic transfer and food-web effects: how microplastics move through feeding interactions from plankton to larger predators, potentially altering feeding efficiency, energy transfer, and predator–prey dynamics."
# })
