from crewai import Task
from agents import Property_Researcher

property_research_task = Task(
    name="Property Research Task",
    description = """Conduct in-depth, data-driven research on real estate opportunities and investment locations in the city of Peshawar Pakistan.
Analyze market trends, property values, rental yields, demographics, economic indicators, and risk factors.
Identify key investment opportunities, potential challenges, and overall market outlook.
Produce clear, structured, and evidence-backed findings that can guide informed investment decisions.
""",
    expected_output = """A comprehensive research report on {topic}, structured with:
- Market overview and trends
- Property valuations and investment metrics
- Rental yield and ROI analysis
- Risk assessment and mitigation insights
- Actionable recommendations for investors
All findings must be factual, verifiable, and presented in a professional, easy-to-digest format.
""",
    agent=Property_Researcher,
    output_file="property_research_report.md")
