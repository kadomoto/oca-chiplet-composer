"""Analytic system model: geometry DRC, UCIe link budgets, routing, power, cost.

Fast (milliseconds) so the GUI can re-evaluate on every edit. It is the
"early exploration" tier; the harness-vp engine is the "run real firmware" tier.
"""
from __future__ import annotations

import heapq
import math

from catalog import DEFAULT_LINK, DEFAULT_PROCESS, PACKAGES

INTRA_DIE_HOP_NS = 5.0   # SMN traversal inside an intermediate chiplet (illustrative)
ESCAPE_MM = {"standard": 1.0, "advanced": 0.3}


# --------------------------------------------------------------------------- geometry
def _rect(c):
    return c["x_mm"], c["y_mm"], c["x_mm"] + c["w_mm"], c["y_mm"] + c["h_mm"]


def edge_gap_mm(a, b) -> float:
    ax0, ay0, ax1, ay1 = _rect(a)
    bx0, by0, bx1, by1 = _rect(b)
    dx = max(bx0 - ax1, ax0 - bx1, 0.0)
    dy = max(by0 - ay1, ay0 - by1, 0.0)
    return math.hypot(dx, dy)


def overlaps(a, b, gap: float) -> bool:
    ax0, ay0, ax1, ay1 = _rect(a)
    bx0, by0, bx1, by1 = _rect(b)
    return ax0 < bx1 + gap and bx0 < ax1 + gap and ay0 < by1 + gap and by0 < ay1 + gap


# --------------------------------------------------------------------------- PHY placement
PHY_DEPTH_MM = {"standard": 0.8, "advanced": 0.6}


def shoreline_mm(link, pkg) -> float:
    """Die-edge length one link's UCIe PHY occupies (bumps*pitch / bump rows)."""
    lanes = pkg["lanes_per_module"] * (link.get("modules") or 1)
    bumps = int(lanes * 2 * 1.2)          # Tx+Rx data + ~20% sideband/clock/valid
    rows = 10 if pkg["ucie_flavor"] == "advanced" else 4
    return math.ceil(bumps / rows) * pkg["bump_pitch_um"] / 1000.0


def _facing(a, b):
    """Edge of `a` that faces `b`, the wanted position along it, and whether they face."""
    ax0, ay0, ax1, ay1 = _rect(a)
    bx0, by0, bx1, by1 = _rect(b)
    ov_y = (max(ay0, by0), min(ay1, by1))
    ov_x = (max(ax0, bx0), min(ax1, bx1))
    if ov_y[1] - ov_y[0] > 0 and (bx0 >= ax1 or bx1 <= ax0):
        return ("E" if bx0 >= ax1 else "W"), (ov_y[0] + ov_y[1]) / 2, True
    if ov_x[1] - ov_x[0] > 0 and (by0 >= ay1 or by1 <= ay0):
        return ("S" if by0 >= ay1 else "N"), (ov_x[0] + ov_x[1]) / 2, True
    acx, acy = (ax0 + ax1) / 2, (ay0 + ay1) / 2
    bcx, bcy = (bx0 + bx1) / 2, (by0 + by1) / 2
    if abs(bcx - acx) >= abs(bcy - acy):
        return ("E" if bcx > acx else "W"), min(max(bcy, ay0), ay1), False
    return ("S" if bcy > acy else "N"), min(max(bcx, ax0), ax1), False


def _edge_span(c, edge):
    x0, y0, x1, y1 = _rect(c)
    return (y0, y1) if edge in "EW" else (x0, x1)


def _phy_rect(c, edge, start, length, depth):
    x0, y0, x1, y1 = _rect(c)
    if edge == "E":
        return x1 - depth, start, depth, length
    if edge == "W":
        return x0, start, depth, length
    if edge == "S":
        return start, y1 - depth, length, depth
    return start, y0, length, depth


def place_phys(design, pkg, chips):
    """Assign each link a PHY on each die's facing edge; pack PHYs sharing an edge.

    Returns ({link_id: {"a": phy, "b": phy, "facing": bool}}, issues).
    A phy is {chip, edge, x, y, w, h, cx, cy} in substrate mm (cx, cy = pad-edge midpoint).
    """
    depth = PHY_DEPTH_MM[pkg["ucie_flavor"]]
    want: dict[tuple, list] = {}
    facing: dict[str, bool] = {}
    for l in design["links"]:
        if l["a"] not in chips or l["b"] not in chips or l["a"] == l["b"]:
            continue
        sl = shoreline_mm(l, pkg)
        for end, me, other in (("a", l["a"], l["b"]), ("b", l["b"], l["a"])):
            edge, pos, ok = _facing(chips[me], chips[other])
            facing[l["id"]] = facing.get(l["id"], True) and ok
            want.setdefault((me, edge), []).append((pos, sl, l["id"], end))

    out: dict[str, dict] = {lid: {"facing": f} for lid, f in facing.items()}
    issues = []
    for (cid, edge), items in want.items():
        lo, hi = _edge_span(chips[cid], edge)
        total = sum(i[1] for i in items)
        if total > hi - lo + 1e-9:
            issues.append({"severity": "error", "ref": cid,
                           "message": f"{chips[cid]['name']} {edge} edge: UCIe PHYs need "
                                      f"{total:.2f} mm of shoreline, edge is {hi - lo:.2f} mm"})
        items.sort()
        starts, cur = [], lo
        for pos, sl, _, _ in items:                      # greedy left-to-right
            st = max(pos - sl / 2, cur, lo)
            starts.append(st)
            cur = st + sl
        if cur > hi:                                      # pull back inside the edge
            nxt = hi
            for k in range(len(starts) - 1, -1, -1):
                starts[k] = max(lo, min(starts[k], nxt - items[k][1]))
                nxt = starts[k]
        for st, (pos, sl, lid, end) in zip(starts, items):
            x, y, w, h = _phy_rect(chips[cid], edge, st, sl, depth)
            if edge in "EW":
                cx, cy = (x + w if edge == "E" else x), y + h / 2
            else:
                cx, cy = x + w / 2, (y + h if edge == "S" else y)
            out[lid][end] = {"chip": cid, "edge": edge, "x": round(x, 3), "y": round(y, 3),
                             "w": round(w, 3), "h": round(h, 3),
                             "cx": round(cx, 3), "cy": round(cy, 3)}
    for lid, ph in out.items():
        if not ph["facing"]:
            l = next(x for x in design["links"] if x["id"] == lid)
            issues.append({"severity": "warning", "ref": lid,
                           "message": f"{chips[l['a']]['name']}↔{chips[l['b']]['name']}: dies do not "
                                      "face each other; the channel routes around a corner"})
    return out, issues


# --------------------------------------------------------------------------- links
def link_metrics(link, a, b, pkg, ph=None) -> dict:
    p = {**DEFAULT_LINK, **{k: v for k, v in link.items() if v is not None}}
    gap = edge_gap_mm(a, b)
    if ph and "a" in ph and "b" in ph:     # PHY-to-PHY, Manhattan (substrate routing)
        route = abs(ph["a"]["cx"] - ph["b"]["cx"]) + abs(ph["a"]["cy"] - ph["b"]["cy"])
    else:
        route = gap
    channel = route + 2 * ESCAPE_MM[pkg["ucie_flavor"]]
    lanes = pkg["lanes_per_module"] * p["modules"]
    bw_gbs = lanes * p["data_rate_gtps"] / 8.0                       # GB/s per direction
    flight_ns = channel * pkg["flight_ps_per_mm"] / 1000.0
    latency_ns = p["aou_fixed_ns"] + p["phy_ns"] + flight_ns
    return {
        "id": link["id"],
        "a": link["a"], "b": link["b"],
        "edge_gap_mm": round(gap, 3),
        "channel_mm": round(channel, 3),
        "lanes": lanes,
        "bw_gbs_per_dir": round(bw_gbs, 1),
        "latency_ns": round(latency_ns, 3),
        "flight_ns": round(flight_ns, 3),
        "shoreline_mm": round(shoreline_mm(link, pkg), 2),
        "reach_ok": channel <= pkg["max_reach_mm"],
        # what the harness-vp engine injects into dut.aou.bridge_delay_ns
        "aou_bridge_delay_ns": round(latency_ns, 3),
    }


# --------------------------------------------------------------------------- validation
def validate(design: dict) -> list[dict]:
    issues: list[dict] = []
    pkg = PACKAGES[design["package"]["tech"]]
    chips = {c["id"]: c for c in design["chiplets"]}
    W, H = design["package"]["w_mm"], design["package"]["h_mm"]

    def add(sev, msg, ref=None):
        issues.append({"severity": sev, "message": msg, "ref": ref})

    ids = list(chips)
    for i, a in enumerate(ids):
        ca = chips[a]
        x0, y0, x1, y1 = _rect(ca)
        if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
            add("error", f"{ca['name']} extends outside the {W}x{H} mm substrate", a)
        for b in ids[i + 1:]:
            if overlaps(ca, chips[b], pkg["min_die_gap_mm"]):
                add("error", f"{ca['name']} and {chips[b]['name']} violate min die gap "
                             f"{pkg['min_die_gap_mm']} mm", a)

    phys, phy_issues = place_phys(design, pkg, chips)
    issues.extend(phy_issues)
    ports_used = {c: 0 for c in chips}
    for l in design["links"]:
        if l["a"] not in chips or l["b"] not in chips:
            add("error", f"link {l['id']} references a missing chiplet", l["id"])
            continue
        if l["a"] == l["b"]:
            add("error", f"link {l['id']} is a self-loop", l["id"])
            continue
        ports_used[l["a"]] += l.get("modules", 1)
        ports_used[l["b"]] += l.get("modules", 1)
        m = link_metrics(l, chips[l["a"]], chips[l["b"]], pkg, phys.get(l["id"]))
        if not m["reach_ok"]:
            add("error", f"{chips[l['a']]['name']}↔{chips[l['b']]['name']}: channel "
                         f"{m['channel_mm']} mm exceeds {pkg['ucie_flavor']} reach "
                         f"{pkg['max_reach_mm']} mm", l["id"])
    for cid, used in ports_used.items():
        if used > chips[cid]["ucie_ports"]:
            add("error", f"{chips[cid]['name']} uses {used} UCIe modules but has "
                         f"{chips[cid]['ucie_ports']}", cid)

    adj = _adjacency(design, pkg, chips, phys)
    if chips:
        seen, stack = set(), [ids[0]]
        while stack:
            n = stack.pop()
            if n in seen:
                continue
            seen.add(n)
            stack.extend(v for v, _, _ in adj.get(n, []))
        for cid in chips:
            if cid not in seen:
                add("warning", f"{chips[cid]['name']} is not reachable from "
                               f"{chips[ids[0]]['name']}", cid)
    return issues


# --------------------------------------------------------------------------- routing
def _adjacency(design, pkg, chips, phys):
    adj: dict[str, list] = {}
    for l in design["links"]:
        if l["a"] in chips and l["b"] in chips and l["a"] != l["b"]:
            m = link_metrics(l, chips[l["a"]], chips[l["b"]], pkg, phys.get(l["id"]))
            adj.setdefault(l["a"], []).append((l["b"], l["id"], m))
            adj.setdefault(l["b"], []).append((l["a"], l["id"], m))
    return adj


def _shortest(adj, src, dst):
    pq, best = [(0.0, src, [])], {}
    while pq:
        d, n, path = heapq.heappop(pq)
        if n == dst:
            return d, path
        if best.get(n, 1e18) <= d:
            continue
        best[n] = d
        for v, lid, m in adj.get(n, []):
            hop = m["latency_ns"] + (INTRA_DIE_HOP_NS if path else 0.0)
            heapq.heappush(pq, (d + hop, v, path + [(n, v, lid)]))
    return None, None


# --------------------------------------------------------------------------- cost
def die_cost(area_mm2, proc):
    d = proc["wafer_diameter_mm"]
    dpw = math.pi * (d / 2) ** 2 / area_mm2 - math.pi * d / math.sqrt(2 * area_mm2)
    ad = area_mm2 / 100.0 * proc["defect_density_per_cm2"]
    yld = ((1 - math.exp(-ad)) / ad) ** 2 if ad > 0 else 1.0
    return proc["wafer_cost_usd"] / max(dpw * yld, 1e-9), yld


# --------------------------------------------------------------------------- run
def run(design: dict, log=print) -> dict:
    pkg = PACKAGES[design["package"]["tech"]]
    proc = {**DEFAULT_PROCESS, **design.get("process", {})}
    chips = {c["id"]: c for c in design["chiplets"]}
    issues = validate(design)
    phys, _ = place_phys(design, pkg, chips)
    log(f"[analytic] {len(chips)} chiplets, {len(design['links'])} links, package={pkg['label']}")
    for i in issues:
        log(f"[analytic] {i['severity'].upper()}: {i['message']}")

    links = {}
    for l in design["links"]:
        if l["a"] in chips and l["b"] in chips and l["a"] != l["b"]:
            links[l["id"]] = link_metrics(l, chips[l["a"]], chips[l["b"]], pkg, phys.get(l["id"]))
            links[l["id"]]["load_gbs"] = {"fwd": 0.0, "rev": 0.0}
    adj = _adjacency(design, pkg, chips, phys)

    flows_out = []
    total_bits_hops = 0.0
    for f in design.get("flows", []):
        lat, path = _shortest(adj, f["src"], f["dst"])
        if path is None:
            flows_out.append({**f, "routable": False})
            log(f"[analytic] flow {f['src']}->{f['dst']}: UNROUTABLE")
            continue
        for (u, v, lid) in path:
            dirn = "fwd" if design_link(design, lid)["a"] == u else "rev"
            links[lid]["load_gbs"][dirn] += f["gbs"]
        total_bits_hops += f["gbs"] * 8e9 * len(path)
        flows_out.append({**f, "routable": True, "hops": len(path),
                          "path": [path[0][0]] + [p[1] for p in path],
                          "link_ids": [p[2] for p in path],
                          "zero_load_latency_ns": round(lat, 2)})

    # utilisation + loaded latency (M/M/1-style inflation per hop)
    for m in links.values():
        u = max(m["load_gbs"]["fwd"], m["load_gbs"]["rev"]) / m["bw_gbs_per_dir"]
        m["utilization"] = round(u, 3)
        m["saturated"] = u >= 1.0
    for f in flows_out:
        if not f.get("routable"):
            continue
        loaded = 0.0
        for i, lid in enumerate(f["link_ids"]):
            rho = min(links[lid]["utilization"], 0.99)
            loaded += links[lid]["latency_ns"] / (1 - rho) + (INTRA_DIE_HOP_NS if i else 0.0)
        f["loaded_latency_ns"] = round(loaded, 2)
        f["saturated"] = any(links[lid]["saturated"] for lid in f["link_ids"])

    d2d_power_w = total_bits_hops * pkg["energy_pj_per_bit"] * 1e-12
    die_power_w = sum(c.get("power_w", 0) for c in chips.values())

    die_rows, silicon_cost = [], 0.0
    for c in chips.values():
        area = c["w_mm"] * c["h_mm"]
        cost, yld = die_cost(area, proc)
        silicon_cost += cost
        die_rows.append({"id": c["id"], "name": c["name"], "area_mm2": round(area, 1),
                         "yield": round(yld, 3), "cost_usd": round(cost, 2)})
    pkg_area = design["package"]["w_mm"] * design["package"]["h_mm"]
    pkg_cost = pkg_area * pkg["cost_per_mm2"] * 10   # x10: substrate+assembly lump
    total_die_area = sum(r["area_mm2"] for r in die_rows)

    summary = {
        "chiplets": len(chips),
        "links": len(links),
        "errors": sum(i["severity"] == "error" for i in issues),
        "warnings": sum(i["severity"] == "warning" for i in issues),
        "total_die_area_mm2": round(total_die_area, 1),
        "package_area_mm2": round(pkg_area, 1),
        "area_utilization": round(total_die_area / pkg_area, 3) if pkg_area else 0,
        "die_power_w": round(die_power_w, 1),
        "d2d_power_w": round(d2d_power_w, 2),
        "power_density_w_per_mm2": round((die_power_w + d2d_power_w) / pkg_area, 3) if pkg_area else 0,
        "silicon_cost_usd": round(silicon_cost, 2),
        "package_cost_usd": round(pkg_cost, 2),
        "max_link_utilization": max((m["utilization"] for m in links.values()), default=0),
    }
    log(f"[analytic] done: D2D power {summary['d2d_power_w']} W, "
        f"max link util {summary['max_link_utilization']:.0%}")
    phy_list = [{**ph[end], "link": lid, "end": end}
                for lid, ph in phys.items() for end in ("a", "b") if end in ph]
    return {"summary": summary, "issues": issues, "links": list(links.values()), "phys": phy_list,
            "flows": flows_out, "dies": die_rows}


def design_link(design, lid):
    return next(l for l in design["links"] if l["id"] == lid)
