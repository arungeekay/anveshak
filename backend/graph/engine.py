"""CrimeGraph: knowledge graph over people/cases + canned multi-hop queries.

Nodes: persons (PersonRegistry) and cases. Edges: accused_in (person->case),
co_accused (person-person, vw_coaccusal_edges), same_address (shared home H3),
mule_account (fraud hub linked to every case sharing a mule phone parsed from the
narrative). Communities via Louvain; canned queries return GraphResult
(contracts.md §6). NoSQL persistence is deferred to the Catalyst integration.
"""
from __future__ import annotations

import re
from collections import defaultdict

import networkx as nx
from networkx.algorithms.community import louvain_communities

PHONE_RE = re.compile(r"\b\d{4,5}-\d[\dX]{3,}\b")


def build_graph(con) -> nx.Graph:
    g = nx.Graph()
    persons = con.execute("SELECT person_key, full_name, home_h3 FROM PersonRegistry").fetchall()
    for pk, name, home in persons:
        g.add_node(pk, kind="person", label=name, meta={"home_h3": home})

    def ensure_case(cid, crimeno=None, sub=None, dist=None):
        node = f"C-{cid}"
        if not g.has_node(node):
            g.add_node(node, kind="case", label=crimeno or f"C-{cid}",
                       meta={"case_id": int(cid), "sub_head": sub, "district": dist})
        return node

    for pk, cid, crimeno, sub, dist in con.execute("""
        SELECT m.person_key, a.CaseMasterID, c.CrimeNo, c.crime_sub_head, c.district
        FROM Accused a JOIN AccusedPersonMap m ON m.AccusedMasterID = a.AccusedMasterID
        JOIN vw_case_360 c ON c.CaseMasterID = a.CaseMasterID
    """).fetchall():
        if g.has_node(pk):
            g.add_edge(pk, ensure_case(cid, crimeno, sub, dist), kind="accused_in")

    for a, b, _cid in con.execute(
        "SELECT person_a, person_b, CaseMasterID FROM vw_coaccusal_edges"
    ).fetchall():
        if g.has_node(a) and g.has_node(b):
            g.add_edge(a, b, kind="co_accused")

    by_home: dict[str, list[str]] = defaultdict(list)
    for pk, _name, home in persons:
        if home:
            by_home[home].append(pk)
    for grp in by_home.values():
        if 2 <= len(grp) <= 4:  # cap to avoid dense background cliques
            for i in range(len(grp)):
                for j in range(i + 1, len(grp)):
                    g.add_edge(grp[i], grp[j], kind="same_address")

    # Mule-account hub: connect the dominant accused to every case sharing a phone.
    phone_cases: dict[str, set[int]] = defaultdict(set)
    for cid, brief in con.execute("SELECT CaseMasterID, BriefFacts FROM CaseMaster").fetchall():
        for ph in PHONE_RE.findall(brief or ""):
            phone_cases[ph].add(int(cid))
    for _ph, cids in phone_cases.items():
        if len(cids) < 3:
            continue
        counts: dict[str, int] = defaultdict(int)
        for cid in cids:
            node = f"C-{cid}"
            if g.has_node(node):
                for nb in g.neighbors(node):
                    if g.nodes[nb]["kind"] == "person":
                        counts[nb] += 1
        if not counts:
            continue
        hub = max(counts, key=counts.get)
        for cid in cids:
            r = con.execute("SELECT CrimeNo, crime_sub_head, district FROM vw_case_360 "
                            "WHERE CaseMasterID = ?", [cid]).fetchone()
            node = ensure_case(cid, *(r or (None, None, None)))
            if not g.has_edge(hub, node):
                g.add_edge(hub, node, kind="mule_account")
    return g


def _person_graph(g: nx.Graph) -> nx.Graph:
    p = nx.Graph()
    for n, d in g.nodes(data=True):
        if d["kind"] == "person":
            p.add_node(n, label=d["label"])
    for cnode, d in g.nodes(data=True):
        if d["kind"] != "case":
            continue
        people = [nb for nb in g.neighbors(cnode) if g.nodes[nb]["kind"] == "person"]
        for i in range(len(people)):
            for j in range(i + 1, len(people)):
                p.add_edge(people[i], people[j])
    for a, b, d in g.edges(data=True):
        if d["kind"] == "same_address":
            p.add_edge(a, b)
    return p


class GraphCache:
    def __init__(self) -> None:
        self.g: nx.Graph | None = None
        self.comms: list[set] | None = None
        self._comm_of: dict[str, int] = {}
        self.centrality: dict[str, float] = {}

    def ensure(self, con) -> None:
        if self.g is None:
            self.rebuild(con)

    def rebuild(self, con) -> None:
        self.g = build_graph(con)
        p = _person_graph(self.g)
        self.comms = louvain_communities(p, seed=42) if p.number_of_nodes() else []
        self._comm_of = {}
        for i, c in enumerate(self.comms):
            for pk in c:
                self._comm_of[pk] = i
        if p.number_of_nodes():
            k = min(p.number_of_nodes(), 200)  # sample for speed on large graphs
            raw = nx.betweenness_centrality(p, k=k, seed=42, normalized=True)
            mx = max(raw.values()) or 1.0
            self.centrality = {n: v / mx for n, v in raw.items()}  # scale to [0,1]
        else:
            self.centrality = {}

    def community_index(self, person_key: str) -> int | None:
        return self._comm_of.get(person_key)


cache = GraphCache()


# --------------------------- GraphResult builders ---------------------------
def _node_dict(g: nx.Graph, node: str) -> dict:
    d = g.nodes[node]
    return {"id": node, "kind": d["kind"], "label": d.get("label", node), "meta": d.get("meta", {})}


def _result(g: nx.Graph, nodes: list[str], *, highlight_path=None,
            communities=None, narrative="") -> dict:
    nodeset = set(nodes)
    edges = []
    for a, b, d in g.subgraph(nodeset).edges(data=True):
        edges.append({"a": a, "b": b, "kind": d.get("kind", "linked"), "meta": {}})
    return {
        "nodes": [_node_dict(g, n) for n in nodeset],
        "edges": edges,
        "highlight_path": highlight_path or [],
        "communities": communities or [],
        "narrative": narrative,
    }


def ego_network(con, person_key: str, depth: int = 2) -> dict:
    cache.ensure(con)
    g = cache.g
    if not g.has_node(person_key):
        return _result(g, [], narrative=f"No graph node for {person_key}.")
    ego = nx.ego_graph(g, person_key, radius=depth)
    case_spokes = [n for n in ego.nodes if g.nodes[n]["kind"] == "case"]
    label = g.nodes[person_key]["label"]
    narrative = (f"{label} ({person_key}) is directly linked to {len(case_spokes)} cases "
                 f"within {depth} hop(s), forming a hub of {ego.number_of_nodes()} nodes.")
    return _result(g, list(ego.nodes), narrative=narrative)


def path_between(con, person_a: str, person_b: str) -> dict:
    cache.ensure(con)
    g = cache.g
    if not (g.has_node(person_a) and g.has_node(person_b)):
        return _result(g, [], narrative="One or both persons are not in the graph.")
    try:
        path = nx.shortest_path(g, person_a, person_b)
    except nx.NetworkXNoPath:
        return _result(g, [person_a, person_b], narrative="No connecting path found.")
    narrative = (f"{g.nodes[person_a]['label']} and {g.nodes[person_b]['label']} are connected "
                 f"through {len(path) - 1} link(s).")
    return _result(g, path, highlight_path=path, narrative=narrative)


def community_of(con, case_id: int) -> dict:
    cache.ensure(con)
    g = cache.g
    node = f"C-{int(case_id)}"
    if not g.has_node(node):
        return _result(g, [], narrative=f"Case {case_id} has no linked persons.")
    people = [nb for nb in g.neighbors(node) if g.nodes[nb]["kind"] == "person"]
    if not people:
        return _result(g, [node], narrative=f"Case {case_id} has no named accused.")
    idx = cache.community_index(people[0])
    members = sorted(cache.comms[idx]) if idx is not None else people
    nodes = set(members)
    for pk in members:  # include each member's cases
        nodes.update(nb for nb in g.neighbors(pk) if g.nodes[nb]["kind"] == "case")
    communities = [{"community_id": idx if idx is not None else 0,
                    "person_keys": members, "label": "candidate ring/network"}]
    narrative = (f"Case {case_id} belongs to a network of {len(members)} linked individuals "
                 f"(e.g. {', '.join(g.nodes[m]['label'] for m in members[:3])}).")
    return _result(g, list(nodes), communities=communities, narrative=narrative)


def query(con, qtype: str, params: dict) -> dict:
    if qtype == "ego_network":
        return ego_network(con, params["person_key"], params.get("depth", 2))
    if qtype == "path_between":
        return path_between(con, params["person_a"], params["person_b"])
    if qtype == "community_of":
        return community_of(con, params["case_id"])
    raise ValueError(f"unknown graph query type: {qtype}")
