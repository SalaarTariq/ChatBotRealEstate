from crewai import Crew, Process
from agents import Property_Researcher, Property_Fetcher
from task import property_fetch_task, property_research_task

crew = Crew(
    name="Real Estate Research Crew",
    agents=[Property_Fetcher, Property_Researcher],
    tasks=[property_fetch_task, property_research_task],
    process=Process.sequential,
    verbose=True,
)

if __name__ == "__main__":
    topic = input("Enter a real estate query (e.g. '5-marla houses for sale in Hayatabad Peshawar under 3 crore'): ").strip()
    if not topic:
        topic = "Houses for sale in Peshawar"

    try:
        result = crew.kickoff(inputs={"topic": topic})
        print("\n===== FINAL OUTPUT =====\n")
        print(result)

    except Exception as e:
        print("\n Crew execution failed")
        print(str(e))
