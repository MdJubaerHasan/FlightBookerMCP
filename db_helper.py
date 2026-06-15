import os
import json
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def setup_database():
    if not DATABASE_URL:
        print('Error: DATABASE_URL environment variable is not set.')
        return
    print("Connecting to Neon...")
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()

    print("Creating table...")
    cursor.execute(''' CREATE TABLE IF NOT EXISTS flights
                       (
                            flight_id SERIAL PRIMARY KEY,
                            flight_number VARCHAR(50),
                            origin VARCHAR(10),
                            destination VARCHAR(10),
                            date DATE,
                            price NUMERIC,
                            airline VARCHAR(100),
                            departure_time TIME,
                            arrival_time TIME
                       )
                   ''')

    print("Populating data from flightdata.json...")
    with open('flightdata.json') as f:
        flights = json.load(f)

        for flight in flights:
            cursor.execute('''
                           INSERT INTO flights (flight_number, origin, destination, date,
                                                price, airline, departure_time, arrival_time)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                           ''', (
                               flight['flight_number'],
                               flight['origin'],
                               flight['destination'],
                               flight['date'],
                               flight['price'],
                               flight['airline'],
                               flight['departure_time'],
                               flight['arrival_time']
                           ))

        print("db populated")

    conn.commit()
    cursor.close()
    conn.close()
    print("Neon Database successfully populated")

if __name__ == "__main__":
    setup_database()
