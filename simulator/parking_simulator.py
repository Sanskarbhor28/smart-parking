"""Parking sensor simulator - plays the role of IoT sensors at the gate.

Every "tick" (default 2 seconds) it randomly:
  * lets a new vehicle arrive   -> POST /parking/entry
  * lets parked vehicles leave  -> POST /parking/exit
The API stores each event as a sensor reading too. Use --seed for reproducible runs.

Examples:
  python -m simulator.parking_simulator
  python -m simulator.parking_simulator --interval 0.5 --arrival-prob 0.7 --departure-prob 0.1 --seed 1
"""
import argparse
import random
import time

import requests

from backend import config


def make_plates(rng: random.Random, n: int = 400) -> list[str]:
    plates = {f"MH12{rng.choice('ABCDEFGH')}{rng.choice('ABCDEFGH')}{rng.randint(1000, 9999)}" for _ in range(n)}
    return sorted(plates)


def get_parked(api: str) -> dict[str, str]:
    """Vehicles currently parked according to the API {plate: slot}."""
    slots = requests.get(f"{api}/parking/slots", timeout=10).json()
    return {s["vehicle_number"]: s["slot_number"] for s in slots if s["vehicle_number"]}


def run(api: str, interval: float, arrival_prob: float, departure_prob: float,
        seed: int | None, ticks: int) -> None:
    rng = random.Random(seed)
    plates = make_plates(rng)
    parked = get_parked(api)
    print(f"Simulator started -> {api} | interval={interval}s arrival={arrival_prob} "
          f"departure={departure_prob} seed={seed} | already parked: {len(parked)}")
    tick = 0
    while ticks == 0 or tick < ticks:
        tick += 1
        # 1) vehicles leaving
        for plate in list(parked):
            if rng.random() < departure_prob:
                r = requests.post(f"{api}/parking/exit", json={"vehicle_number": plate}, timeout=10)
                if r.ok:
                    print(f"[{tick}] EXIT   {plate} left {parked.pop(plate)} after {r.json()['duration_minutes']} min")
                else:
                    parked.pop(plate, None)
        # 2) new arrival
        if rng.random() < arrival_prob:
            free_plates = [p for p in plates if p not in parked]
            plate = rng.choice(free_plates)
            r = requests.post(f"{api}/parking/entry", timeout=10, json={
                "vehicle_number": plate, "vehicle_type": rng.choices(["car", "bike", "truck"], [0.65, 0.3, 0.05])[0]})
            if r.status_code == 201:
                parked[plate] = r.json()["slot_number"]
                print(f"[{tick}] ENTRY  {plate} -> {parked[plate]}  (parked now: {len(parked)})")
            else:
                print(f"[{tick}] ENTRY refused for {plate}: {r.json().get('detail')}")
        time.sleep(interval)


def main() -> None:
    ap = argparse.ArgumentParser(description="Smart parking sensor simulator")
    ap.add_argument("--api", default=config.API_URL)
    ap.add_argument("--interval", type=float, default=2.0, help="seconds between ticks (simulation speed)")
    ap.add_argument("--arrival-prob", type=float, default=0.5, help="chance of an arrival each tick (0-1)")
    ap.add_argument("--departure-prob", type=float, default=0.05, help="chance each parked vehicle leaves per tick (0-1)")
    ap.add_argument("--seed", type=int, default=None, help="set for reproducible behaviour")
    ap.add_argument("--ticks", type=int, default=0, help="stop after N ticks (0 = run forever)")
    a = ap.parse_args()
    try:
        run(a.api.rstrip("/"), a.interval, a.arrival_prob, a.departure_prob, a.seed, a.ticks)
    except requests.ConnectionError:
        print(f"Cannot reach the API at {a.api}. Start it first:  uvicorn backend.main:app --reload")
    except KeyboardInterrupt:
        print("\nSimulator stopped.")


if __name__ == "__main__":
    main()
