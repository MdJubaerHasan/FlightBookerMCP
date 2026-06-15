import os
import psycopg2
from dotenv import load_dotenv
import stripe
import webbrowser
from mcp.server.fastmcp import FastMCP
from psycopg2.extras import RealDictCursor


load_dotenv()

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
    description="Searches the cloud database for available flights matching strict origin, destination, date, and price constraints."
)
def search_flight_tool(origin: str, destination: str, date: str, max_price: float | int):
    """Searches the Neon database for available flights based on user criteria.

        Args:
            origin: The 3-letter departure airport code (e.g., 'JFK', 'LHR').
            destination: The 3-letter arrival airport code (e.g., 'CDG', 'DXB').
            date: Departure date formatted as YYYY-MM-DD (e.g., '2026-08-12').
            max_price: The maximum budget for the ticket price.
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
            webbrowser.open(session.url)
            return f"Success: Displaying Stripe checkout screen for {flight_number} at ${price:.2f}."
    except Exception as e:
        return f"Stripe Gateway Error: {str(e)}"


if __name__ == "__main__":
    if __name__ == "__main__":
        port = int(os.environ.get("PORT", 8000))
        mcp.run(transport="sse", host="0.0.0.0", port=port)