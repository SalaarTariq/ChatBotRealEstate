from crewai import Crew
from agents import Property_Researcher
from task import property_research_task
from langchain_groq import ChatGroq

# Initialize Groq LLM explicitly
llm = ChatGroq(
    model="llama-3.1-8b-instant",
    temperature=0.3
)

# IMPORTANT: agents must be INSTANCES, not classes
crew = Crew(
    name="Real Estate Research Crew",
    agents=[Property_Researcher],
    tasks=[property_research_task],
    verbose=True,
    llm=llm
)

if __name__ == "__main__":
    try:
        result = crew.kickoff()
        print("\n===== FINAL OUTPUT =====\n")
        print(result)

    except Exception as e:
        print("\n❌ Crew execution failed")
        print(str(e))
