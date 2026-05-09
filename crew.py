from crewai import Crew
from agents import Property_Researcher
from task import property_research_task

crew = Crew(
    name="Real Estate Research Crew",
    agents=[Property_Researcher],
    tasks=[property_research_task],
    verbose=True,
)

if __name__ == "__main__":
    topic = input("Enter a real estate research topic: ").strip()
    if not topic:
        topic = "Real estate investment opportunities in Peshawar, Pakistan"

    try:
        result = crew.kickoff(inputs={"topic": topic})
        print("\n===== FINAL OUTPUT =====\n")
        print(result)

    except Exception as e:
        print("\n Crew execution failed")
        print(str(e))
