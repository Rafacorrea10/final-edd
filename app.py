
from flask import Flask, render_template, request, jsonify, send_from_directory
import os
import json
import sqlite3
from math import hypot

app = Flask(__name__, static_folder="static", template_folder="templates")
DB = "rutas.db"


def get_db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/nodes", methods=["GET", "POST"])
def nodes():
    con = get_db()
    cur = con.cursor()
    if request.method == "POST":
        data = request.get_json()
        cur.execute("INSERT INTO nodos (name, lat, lng) VALUES (?, ?, ?)",
                    (data["name"], data["lat"], data["lng"]))
        con.commit()
        return jsonify({"id": cur.lastrowid, **data}), 201
    nodos = cur.execute("SELECT * FROM nodos").fetchall()
    return jsonify([dict(n) for n in nodos])


@app.route("/nodes/<int:nid>", methods=["PUT", "DELETE"])
def node_update(nid):
    con = get_db()
    cur = con.cursor()
    if request.method == "DELETE":
        cur.execute("DELETE FROM nodos WHERE id = ?", (nid,))
        con.commit()
        return "", 204
    data = request.get_json()
    cur.execute("UPDATE nodos SET name = ?, lat = ?, lng = ? WHERE id = ?",
                (data["name"], data["lat"], data["lng"], nid))
    con.commit()
    return jsonify({"id": nid, **data})


@app.route("/connections", methods=["GET", "POST"])
def connections():
    con = get_db()
    cur = con.cursor()
    if request.method == "POST":
        data = request.get_json()
        cur.execute("INSERT INTO conexiones (from_id, to_id, weight) VALUES (?, ?, ?)",
                    (data["from"], data["to"], data["weight"]))
        con.commit()
        return jsonify({"id": cur.lastrowid, **data}), 201
    conns = cur.execute("SELECT * FROM conexiones").fetchall()
    return jsonify([dict(c) for c in conns])


@app.route("/shortest_path", methods=["POST"])
def shortest_path():
    data = request.get_json()
    con = get_db()
    nodos = {n["id"]: dict(n) for n in con.execute("SELECT * FROM nodos")}
    edges = con.execute("SELECT * FROM conexiones").fetchall()
    graph = {n: {} for n in nodos}
    for e in edges:
        graph[e["from_id"]][e["to_id"]] = e["weight"]
    origin = data["origin"]
    dest = data["dest"]
    waypoints = data.get("waypoints", [])

    def dijkstra(start, end):
        dist = {n: float("inf") for n in graph}
        prev = {}
        dist[start] = 0
        q = list(graph)
        while q:
            u = min(q, key=lambda x: dist[x])
            q.remove(u)
            if u == end:
                break
            for v in graph[u]:
                alt = dist[u] + graph[u][v]
                if alt < dist[v]:
                    dist[v] = alt
                    prev[v] = u
        path = []
        u = end
        while u in prev:
            path.insert(0, nodos[u])
            u = prev[u]
        if u == start:
            path.insert(0, nodos[u])
            return path
        return []

    full_path = []
    ids = [origin] + waypoints + [dest]
    for i in range(len(ids)-1):
        segment = dijkstra(ids[i], ids[i+1])
        if not segment:
            return jsonify({"error": "No hay ruta entre algunos puntos"}), 400
        if full_path and full_path[-1]["id"] == segment[0]["id"]:
            segment = segment[1:]
        full_path += segment
    total_dist = sum(hypot(full_path[i]["lat"] - full_path[i+1]["lat"],
                           full_path[i]["lng"] - full_path[i+1]["lng"])
                     for i in range(len(full_path)-1))
    return jsonify(path=full_path, distance=round(total_dist, 1))


@app.route("/export/nodos.csv")
def export_nodos():
    con = get_db()
    rows = con.execute("SELECT * FROM nodos").fetchall()
    csv = "id,name,lat,lng\n" + \
        "\n".join(f"{r['id']},{r['name']},{r['lat']},{r['lng']}" for r in rows)
    return csv, 200, {'Content-Type': 'text/csv'}


@app.route("/export/conexiones.csv")
def export_conexiones():
    con = get_db()
    rows = con.execute("SELECT * FROM conexiones").fetchall()
    csv = "from_id,to_id,weight\n" + \
        "\n".join(f"{r['from_id']},{r['to_id']},{r['weight']}" for r in rows)
    return csv, 200, {'Content-Type': 'text/csv'}


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
