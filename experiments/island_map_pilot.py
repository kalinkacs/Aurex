"""Deterministic scoring harness for Island Map Pilot 001; no model is simulated."""
import json
from pathlib import Path

EDGES = {"D-A": 2, "A-C": 2, "C-T": 3, "D-B": 3, "B-C": 3, "B-E": 2, "E-T": 2, "A-E": 5}
CLOSED = {"E-T"}
def edge(a, b):
    return "-".join(sorted((a,b)))
WEIGHTS = {edge(*name.split("-")): value for name, value in EDGES.items()}
BLOCKED = {edge(*name.split("-")) for name in CLOSED}

def score(route):
    if not isinstance(route, list) or len(route) < 2 or route[0] != "D" or route[-1] != "T":
        return {"valid": False, "cost": None, "reason": "invalid endpoints"}
    cost = 0
    for a, b in zip(route, route[1:]):
        road = edge(a,b)
        if road not in WEIGHTS:
            return {"valid": False, "cost": None, "reason": "unlisted road: " + road}
        if road in BLOCKED:
            return {"valid": False, "cost": None, "reason": "closed road: " + road}
        cost += WEIGHTS[road]
    return {"valid": True, "cost": cost, "reason": "ok"}

def optimal():
    import heapq
    q = [(0, ("D",))]
    while q:
        cost, route = heapq.heappop(q)
        if route[-1] == "T":
            return {"route": list(route), "cost": cost}
        for road, weight in WEIGHTS.items():
            if road in BLOCKED:
                continue
            a,b = road.split("-")
            if route[-1] == a: nxt = b
            elif route[-1] == b: nxt = a
            else: continue
            if nxt not in route:
                heapq.heappush(q, (cost + weight, route + (nxt,)))
    raise ValueError("No route")

def evaluate(answer):
    result = score(answer["route"])
    best = optimal()
    result["optimal"] = result["valid"] and result["cost"] == best["cost"]
    result["excess_cost"] = result["cost"] - best["cost"] if result["valid"] else None
    return result

def main():
    reference = optimal()
    assert reference["cost"] == 7, reference
    assert score(["D","B","E","T"])["valid"] is False
    assert evaluate({"route":["D","A","C","T"]})["optimal"]
    assert not evaluate({"route":["D","B","C","T"]})["optimal"]
    print(json.dumps({"status":"harness_pass", "reference":reference, "model_invoked":False, "participants_invoked":False, "limitation":"Only validates the scorer and fixture; no agent reasoning tested."}, indent=2))
if __name__ == "__main__":
    main()
