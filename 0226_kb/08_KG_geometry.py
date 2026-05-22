import json
from neo4j import GraphDatabase

driver = GraphDatabase.driver(
    "neo4j://127.0.0.1:7687",
    auth=("neo4j","password")
)

def ingest_reaction(json_file):

    with open(json_file) as f:
        data = json.load(f)

    reaction = data["reaction_model"]

    with driver.session() as session:

        session.run("""
        MERGE (r:ReactionModel {name:"ALD_surface_reaction"})
        """)

        coeffs = reaction["reaction_coefficients"]

        for key, val in coeffs.items():

            name = val["canonical_name"]

            session.run("""
            MERGE (c:Coefficient {name:$name})
            """, name=name)

            session.run("""
            MATCH (r:ReactionModel {name:"ALD_surface_reaction"})
            MATCH (c:Coefficient {name:$name})
            MERGE (r)-[:HAS_COEFFICIENT]->(c)
            """, name=name)