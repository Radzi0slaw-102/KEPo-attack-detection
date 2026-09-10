import networkx as nx

WORKING_DIR = "./storage"
graph = nx.read_graphml(f"{WORKING_DIR}/graph_chunk_entity_relation.graphml")

print(f"Total nodes: {graph.number_of_nodes()}")
print(f"Total edges: {graph.number_of_edges()}")

print("\n--- All node names ---")
for node in graph.nodes():
    print(f"  {node!r}")

print("\n--- All edges names ---")
for u, v, data in graph.edges(data=True):
    print(f"  EDGE: {u!r} -> {v!r} | data={data}")