import os
from dotenv import load_dotenv
import psycopg2
import stripe
from fastmcp import FastMCP
from psycopg2.extras import RealDictCursor

load_dotenv()

mcp = FastMCP(
    "AirlineBookingServer",
    instructions=(
        "ROLE: Expert AI travel coordinator. You MUST adhere to these strict operational protocols: "
        "1. STRICT IATA PARAMETERS: search_flight_tool requires exactly 4 parameters: origin, destination, date (YYYY-MM-DD), and max_price. Origin and destination MUST be valid 3-letter IATA codes. Convert cities or fuzzy terms to exact IATA codes internally BEFORE calling the tool. "
        "2. EXPLICIT DATA GATHERING: NEVER guess, assume, or read workspace files for missing dates or budgets. If omitted, pause and immediately prompt the user for clarification. "
        "3. ZERO HALLUCINATION: ONLY display flights directly returned by the search_flight_tool. NEVER invent, hallucinate, or alter flight options. "
        "4. POST-SEARCH WORKFLOW: If multiple flights match, explicitly ask the user for their preferred flight number and offer the payment_gateway. If exactly one flight matches, immediately offer the payment_gateway to book it. "
        "5. STRIPE LINK SECURITY: URLs returned by the payment_gateway MUST be output inside raw Markdown code blocks (```). NEVER format them as clickable hyperlinks, as this corrupts the secure checkout hash."
    )
)


@mcp.tool(
    name="search_flight_tool",
    description="Searches the cloud database for available flights matching strict origin, destination, date, and price constraints."
)
def search_flight_tool(origin: str, destination: str, date: str, max_price: float | int):
    """Searches the Neon database for available flights based on user criteria.
    
    Args:
        origin: STRICTLY a 3-letter IATA airport code (e.g., 'DUB' for Dublin, 'DXB' for Dubai, 'JFK' for New York). NEVER use full city names.
        destination: STRICTLY a 3-letter IATA airport code. NEVER use full city names.
        date: The date of the flight in YYYY-MM-DD format.
        max_price: The user's maximum budget constraint.
    """
    origin = origin.upper()
    destination = destination.upper()

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        return "Error: DATABASE_URL environment variable is not set on the server"

    try:

        conn = psycopg2.connect(database_url)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute(''' SELECT *
                           FROM  flights
                           WHERE origin = %s
                             AND destination = %s
                             AND date = %s
                             AND price <= %s''', (origin, destination, date, max_price))

        rows = cursor.fetchall()
        flight_list = [dict(row) for row in rows]
        cursor.close()
        conn.close()
        return flight_list

    except Exception as e:
        return f"Database search error: {str(e)}"


@mcp.tool(
    name="payment_gateway",
    description="Launches a secure Stripe checkout session to process client payment for a specific flight number."
)
def payment_gateway(flight_number: str, price: float | int):
    """Generates a Stripe Checkout URL and opens it in the user's browser

        Args:
            flight_number: Passed by the LLM
            price: Passed by the LLM
    """

    stripe_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe_key:
        return "Error: STRIPE_SECRET_KEY environment variable is not set"

    stripe.api_key = stripe_key

    try:
        amount_in_cents = int(float(price) * 100)
        session = stripe.checkout.Session.create(
            mode='payment',
            payment_method_types=['card'],
            line_items=[{
                'price_data':{
                    'currency': 'usd',
                    'product_data':{
                        'name': f'Flight Ticket: {flight_number}',
                        'description': 'Dream Air Secure Checkout',
                    },
                    'unit_amount': amount_in_cents,
                },
                'quantity': 1,
            }],
            success_url='https://example.com/success',
            cancel_url='https://example.com/cancel',
        )
        if session.url:
            return (
                f"Success: Payment gateway created. \n\n"
                f"CRITICAL LLM INSTRUCTION: You MUST output the URL below exactly as it appears, wrapped in triple backticks. Do NOT make it a clickable link.\n\n"
                f"```text\n{session.url}\n```"
            )
    except Exception as e:
        return f"Stripe Gateway Error: {str(e)}"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    mcp.run(transport="sse", host="0.0.0.0", port=port)
