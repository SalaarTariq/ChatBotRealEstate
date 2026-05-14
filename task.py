import threading

from crewai import Task
from agents import Property_Researcher, Property_Fetcher

_progress_lock = threading.Lock()
_progress_callbacks: dict[int, "object"] = {}


def set_task_progress_callback_for_thread(thread_id: int, callback) -> None:
    """Register a callback keyed by the thread id that will run the crew.

    The callback receives (task_index, task_output). Pass None to clear.
    """
    with _progress_lock:
        if callback is None:
            _progress_callbacks.pop(thread_id, None)
        else:
            _progress_callbacks[thread_id] = callback


def _make_task_callback(task_index: int):
    def _cb(task_output):
        with _progress_lock:
            cb = _progress_callbacks.get(threading.get_ident())
        if cb is None:
            return
        try:
            cb(task_index, task_output)
        except Exception:
            pass
    return _cb


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
    callback=_make_task_callback(0),
)

property_research_task = Task(
    name="Property Research Task",
    description="""Conduct in-depth, data-driven research on real estate opportunities and investment locations relevant to the user's query: {topic}.
Analyze market trends, property values, rental yields, demographics, economic indicators, and risk factors for the city and area implied by the query.
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
    callback=_make_task_callback(1),
)
