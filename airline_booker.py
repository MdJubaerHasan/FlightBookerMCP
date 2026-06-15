import os
import sqlite3
import tempfile
import webbrowser
from string import Template

from mcp.server.fastmcp import FastMCP
from pypdf import PdfReader


mcp = FastMCP(
    "AirlineBookingServer",
    instructions=(
        "You are an expert, proactive AI travel coordinator. "
        "CRITICAL CONVERSATIONAL PROTOCOLS: "
        "1. The search_flight_tool strictly requires FOUR parameters: origin, destination, date (YYYY-MM-DD), and max_price. "
        "2. If the user omits the 'date' or their 'budget/price' from their request, you MUST NOT guess, assume, or read raw workspace files. You must immediately reply to the user and ask them to clarify the missing information. "
        "3. IMMEDIATELY after displaying search results: If multiple flights are found, explicitly ask the user which flight number they prefer and if they want to launch the payment_gateway to book it. If only one flight is found, ask them directly if they want to launch the payment_gateway to book it right away. "
        "4. Only display flights that are returned directly as output from the search_flight_tool. Do not invent alternative options."
    )
)


@mcp.tool(
    name="search_flight_tool",
    description="Searches the local database for available flights matching strict origin, destination, date, and price constraints."
)
def search_flight_tool(origin: str, destination: str, date: str, max_price: float | int):
    """Searches the database for available flights based on user criteria.

    Args:
        origin: The 3-letter departure airport code (e.g., 'JFK', 'LHR').
        destination: The 3-letter arrival airport code (e.g., 'CDG', 'DXB').
        date: Departure date formatted as YYYY-MM-DD (e.g., '2026-08-12').
        max_price: The maximum budget for the ticket price.
    """
    origin = origin.upper()
    destination = destination.upper()

    project_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(project_dir, 'flights')
    conn = sqlite3.connect(db_path)

    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(''' SELECT *
                       FROM flights
                       WHERE origin = ?
                         AND destination = ?
                         AND date = ?
                         AND price <= ?''', (origin, destination, date, max_price))

    rows = cursor.fetchall()
    flight_list = [dict(row) for row in rows]
    conn.close()
    return flight_list


@mcp.resource("passport://{file_path}")
def extract_passport_text(file_path: str):
    """ Extracts the information as text from PDF files"""
    reader = PdfReader(file_path)
    page = reader.pages[0]
    return page.extract_text()


@mcp.tool(
    name="payment_gateway",
    description="Launches a secure local mockup browser interface to process client checkout for a specific flight number and price."
)
def payment_gateway(flight_number: str, price: float | int):
    """Tool for the LLM to render the external checkout page template.

    Args:
        flight_number: Passed by the LLM
        price: Passed by the LLM
    """
    template_path = os.path.join(
        str(os.path.dirname(__file__)), "payment_page.html"
    )

    if not os.path.exists(template_path):
        return "Error: payment_page.html template file was not found."

    # 1. Read the static HTML file
    with open(template_path, "r", encoding="utf-8") as file:
        html_template = file.read()

    template = Template(html_template)
    formatted_price = f"{price:.2f}"

    # Note: Double check that your payment_page.html uses exactly $flight_number and $price
    rendered_html = template.substitute(
        flight_number=flight_number, price=formatted_price
    )

    with tempfile.NamedTemporaryFile(
            "w", delete=False, suffix=".html", encoding="utf-8"
    ) as temp_file:
        temp_file.write(rendered_html)
        temp_file_path = temp_file.name

    webbrowser.open(f"file://{os.path.abspath(temp_file_path)}")

    return f"Success: Displaying payment screen for {flight_number}."


if __name__ == "__main__":
    mcp.run()