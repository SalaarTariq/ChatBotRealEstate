from crewai import Task
from agents import Property_Researcher, Property_Fetcher

property_fetch_task = Task(
    name="Property Fetch Task",
    description="""The user query is: {topic}

Step 1: Parse the query to extract structured filters:
  - city (default 'peshawar' if unspecified)
  - purpose ('buy' or 'rent', default 'buy')
  - property_type ('homes', 'plots', or 'commercial', default 'homes')
  - area / neighborhood (optional, e.g. 'Hayatabad', 'DHA', 'Bahria')
  - min_price / max_price in PKR. Convert Pakistani price units:
      1 lakh = 100,000 PKR; 1 crore = 10,000,000 PKR.
      e.g. "under 3 crore" -> max_price=30000000.

Step 2: Call the zameen_property_search tool ONCE with those filters and limit=10.

Step 3: From the tool output, build a ranked shortlist of the 5 best matches for the user's
intent. Briefly justify the ranking (location fit, price fit, size).

Do NOT invent listings. If the tool returns no results, report that honestly and suggest
relaxing the filters.
""",
    expected_output="""A markdown report with two parts:
1. A table of up to 5 recommended listings: Title | Price | Location | Beds | Baths | Area | URL.
2. A 2-3 sentence summary explaining which listing best fits the query and why.
Every listing must include a working Zameen.com URL from the tool output.
""",
    agent=Property_Fetcher,
    output_file="property_listings.md",
)

property_research_task = Task(
    name="Property Research Task",
    description="""Conduct in-depth, data-driven research on real estate opportunities and investment locations in the city of Peshawar Pakistan.
Analyze market trends, property values, rental yields, demographics, economic indicators, and risk factors.
Identify key investment opportunities, potential challenges, and overall market outlook.
Produce clear, structured, and evidence-backed findings that can guide informed investment decisions.
""",
    expected_output="""A comprehensive research report on {topic}, structured with:
- Market overview and trends
- Property valuations and investment metrics
- Rental yield and ROI analysis
- Risk assessment and mitigation insights
- Actionable recommendations for investors
All findings must be factual, verifiable, and presented in a professional, easy-to-digest format.
""",
    agent=Property_Researcher,
    output_file="property_research_report.md",
)
