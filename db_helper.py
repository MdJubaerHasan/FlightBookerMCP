import sqlite3
import json

conn = sqlite3.connect('flights')
cursor = conn.cursor()

cursor.execute(''' CREATE TABLE IF NOT EXISTS flights
                   (
                       flight_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                       flight_number  TEXT,
                       origin         TEXT,
                       destination    TEXT,
                       date           TEXT,
                       price          REAL,
                       airline        TEXT,
                       departure_time TEXT,
                       arrival_time   TEXT
                   )
               ''')


def populate_db(
        flight_number,
        origin,
        destination,
        date,
        price,
        airline,
        departure_time,
        arrival_time):
    cursor.execute('''
                   INSERT INTO flights(flight_number,
                                       origin,
                                       destination,
                                       date,
                                       price,
                                       airline,
                                       departure_time,
                                       arrival_time)
                   VALUES (?,?,?,?,?,?,?,?)''',
                   (flight_number,
                    origin,
                    destination,
                    date,
                    price,
                    airline,
                    departure_time,
                    arrival_time))


with open('flightdata.json') as f:
    flights = json.load(f)

    for flight in flights:
        populate_db(
        flight['flight_number'],
        flight['origin'],
        flight['destination'],
        flight['date'],
        flight['price'],
        flight['airline'],
        flight['departure_time'],
        flight['arrival_time'])

    print("db populated")


conn.commit()
conn.close()
