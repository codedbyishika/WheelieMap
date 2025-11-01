from flask import Flask, jsonify, render_template
import overpy
import geocoder
import requests

app = Flask(__name__)
api = overpy.Overpass()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/get_accessible_places")
def get_accessible_places():
    g = geocoder.ip('me')
    if not g.ok or not g.latlng:
        return jsonify({"error": "Unable to get location"}), 400

    lat, lon = g.latlng
    radius = 1000  

    query = f"""
    [out:json];
    node(around:{radius},{lat},{lon})["wheelchair"="yes"];
    out body;
    """

    result = api.query(query)

    places = [
        {"name": n.tags.get("name", "Unnamed"), "lat": n.lat, "lon": n.lon}
        for n in result.nodes
    ]

    return jsonify({
        "location": {"lat": lat, "lon": lon},
        "places": places
    })

if __name__ == "__main__":
    app.run(debug=True)
