from flask import Flask, jsonify, request
import requests
import sqlite3

app = Flask(__name__)  
#Flask() is a class — you are creating an instance of it
#__name__ is a special Python variable that holds the name of the current file
#when app.py is run directly, __name__ equals "__main__"

API_KEY = "8b29e09386f7a17509e98bb83cf4ceb0"

# ─────────────────────────────────────────────
# DATABASE SETUP
# ─────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect("weather.db")
#creates weather.db file & open a connection to it

    cursor = conn.cursor() 
#creates a cursor from the connection   
#cursor is like a pen to write & read from the database
#cursor is needed to run SQL commands

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS favourites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT NOT NULL
        )
    """)

#conn is the connection & cursor is the tool to use through that connection

    conn.commit() #Saves the changes to the database file permanently
    conn.close()  #Closes the db connection & this should be done always

init_db()   #calls the function immediately when the server starts
            #this runs before any route is accessed
# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────
@app.route("/")
def home():
    return "Weather API is running!"
#Tells Flask when someone sends a request to '/' run the function below
#"/" is the root URL — http://127.0.0.1:5000/

@app.route("/weather")
def weather():
#Tells Flask: when someone visits /weather run the function below
    city = request.args.get("city", "Dhaka")
    #request.args is a dictionary of all query parameters in the URL
    #.get("city", "Dhaka") looks for a key called "city" in the URL
    #If URL is /weather?city=London then city = "London"
    #If no city is provided in URL then city = "Dhaka" (default value)
    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
    #OpenWeatherMap API URL
    #units=metric tells the API to return temperature in Celsius
    #Without units=metric it returns Fahrenheit by default
    response = requests.get(url)
    #sends a get request to the OpenWeatherMap
    #A real network call, it goes out to the internet and comes back
    data = response.json()
    #Converts the response body from JSON text to a Python dictionary
    if response.status_code == 200:
        result = {
            "city": data["name"],
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "weather": data["weather"][0]["description"],
            "wind_speed": data["wind"]["speed"]
        }
        return jsonify(result)
    else:
        return jsonify({"error": "City not found"}), 404

@app.route("/compare", methods=["POST"])
def compare():
    body = request.get_json()
    #Reads the JSON body from the POST request
    cities = body.get("cities")
    if not cities:
        return jsonify({"error": "Please provide a cities list"}), 400
    if len(cities) < 2:
        return jsonify({"error": "Please provide at least 2 cities"}), 400

    def get_weather(city):
    #Defines a helper function INSIDE the compare function
    #This is called a nested function in Python
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            ##Converts the response body from JSON text to a Python dictionary
            return {
                "city": data["name"],
                "temperature": data["main"]["temp"],
                "humidity": data["main"]["humidity"],
                "weather": data["weather"][0]["description"]
            }
        return None

    results = []
    not_found = []
    for city in cities:
        data = get_weather(city)
        if data:
            results.append(data)
        else:
            not_found.append(city)

    if not results:
        return jsonify({"error": "No valid cities found"}), 404

    hottest = max(results, key=lambda x: x["temperature"])
    coldest = min(results, key=lambda x: x["temperature"])

    return jsonify({
        "results": results,
        "hottest_city": hottest["city"],
        "coldest_city": coldest["city"],
        "not_found": not_found
    })

# ─────────────────────────────────────────────
# FAVOURITES — DATABASE ROUTES
# ─────────────────────────────────────────────
@app.route("/favourites", methods=["POST"])
def add_favourite():
    body = request.get_json()
    #reads the json body sent by the client
    #converts it to python dictionary

    city = body.get("city")
    #extracts the value of city from the 'Body'

    if not city:
        return jsonify({"error": "Please provide a city"}), 400
    #if city is empty the return this error, incomplete data, bad request

    conn = sqlite3.connect("weather.db")
    cursor = conn.cursor()
    #Open a new connection to the db and creates a cursor just like before but this time in a route

    cursor.execute("INSERT INTO favourites (city) VALUES (?)", (city,))
    #runs an insert SQL commands
    conn.commit()
    conn.close()
    return jsonify({"message": f"{city} added to favourites"}), 201

@app.route("/favourites", methods=["GET"])
def get_favourites():
    conn = sqlite3.connect("weather.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM favourites")
    rows = cursor.fetchall()
    #fetchall() retrieves all the rows returned by the select
    #returns a list of tuples
    #Example: [(1, "Dhaka"), (2, "London"), (3, "Tokyo")]
    #Each tuple is one row — first value is id, second is city
    conn.close()
    favourites = [{"id": row[0], "city": row[1]} for row in rows]
    #This is a list comprehension — a short way to loop and build a list
    #Result: [{"id": 1, "city": "Dhaka"}, {"id": 2, "city": "London"}]
    return jsonify(favourites)

@app.route("/favourites/<int:id>", methods=["DELETE"])
def delete_favourite(id):
    conn = sqlite3.connect("weather.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM favourites WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "City removed from favourites"}), 200

if __name__ == "__main__":
    app.run(debug=True)

#__name__ equals "__main__" only when you run python app.py directly
#debug=True does two things:
    #1. Auto restarts server when you save changes to the file
    #2. Shows detailed error messages in browser when something crashes
#Never use debug=True in production — it exposes your code internals    