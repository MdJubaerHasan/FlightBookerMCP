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


    if not os.path.exists('../data/airports.json') or not os.path.exists('../data/flightdata.json'):
        print("JSON files not found.")
        return

    print("Connecting to Neon...")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        try:
            print("Creating tables...")
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS airports
                           (
                               iata_code TEXT PRIMARY KEY,
                               country   TEXT NOT NULL,
                               city      TEXT NOT NULL,
                               aliases   TEXT
                           )
                           ''')

            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS flights
                           (
                               flight_number  TEXT PRIMARY KEY,
                               origin         TEXT NOT NULL,
                               destination    TEXT NOT NULL,
                               date           TEXT NOT NULL,
                               price          REAL NOT NULL,
                               airline_name   TEXT NOT NULL,
                               departure_time TEXT NOT NULL,
                               arrival_time   TEXT NOT NULL,
                               FOREIGN KEY (origin) REFERENCES airports (iata_code),
                               FOREIGN KEY (destination) REFERENCES airports (iata_code)
                           )
                           ''')

            print("Loading data from JSON files...")
            with open('../data/airports.json', 'r') as f:
                airports = json.load(f)
            with open('../data/flightdata.json', 'r') as f:
                flights = json.load(f)

            airport_tuples = [(a['iata_code'], a['country'], a['city'], a['aliases']) for a in airports]
            flight_tuples = [(
                f['flight_number'], f['origin'], f['destination'], f['date'],
                f['price'], f['airline_name'], f['departure_time'], f['arrival_time']
            ) for f in flights]

            print("Populating airports...")
            # PostgreSQL syntax for "INSERT OR REPLACE"
            cursor.executemany('''
                               INSERT INTO airports (iata_code, country, city, aliases)
                               VALUES (%s, %s, %s, %s)
                               ON CONFLICT (iata_code) DO UPDATE SET country = EXCLUDED.country,
                                                                     city    = EXCLUDED.city,
                                                                     aliases = EXCLUDED.aliases;
                               ''', airport_tuples)

            print("Populating flights...")

            cursor.executemany('''
                               INSERT INTO flights (flight_number, origin, destination, date,
                                                    price, airline_name, departure_time, arrival_time)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                               ON CONFLICT (flight_number) DO UPDATE SET origin         = EXCLUDED.origin,
                                                                         destination    = EXCLUDED.destination,
                                                                         date           = EXCLUDED.date,
                                                                         price          = EXCLUDED.price,
                                                                         airline_name   = EXCLUDED.airline_name,
                                                                         departure_time = EXCLUDED.departure_time,
                                                                         arrival_time   = EXCLUDED.arrival_time;
                               ''', flight_tuples)

            print("Creating indexes...")
            cursor.execute('''
                           CREATE INDEX IF NOT EXISTS idx_flights_date
                               ON flights (date);
                           ''')

            conn.commit()
            print("Neon Database successfully populated.")

        except Exception as e:
            print(f"An unexpected error occurred: {e}")
        finally:

            if conn:
                conn.close()
                print("Database connection closed.")
    except Exception as e:
        print(f"Database Connection Error: {e}.")
        return


if __name__ == "__main__":
    setup_database()