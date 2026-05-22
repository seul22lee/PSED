import os
import json
from neo4j import GraphDatabase
from dotenv import load_dotenv

# load .env
load_dotenv()

# connect
neo4j_driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

neo4j_driver.verify_connectivity()
print("Neo4j connected")

def merge_variable(tx, label, name, props=None):
    if not name:
        return
    props = props or {}
    query = f"""
    MERGE (n:{label} {{name: $name}})
    SET n += $props
    """
    tx.run(query, name=name, props=props)


def merge_relation(tx, from_label, from_name, rel, to_label, to_name):
    if not from_name or not to_name:
        return
    query = f"""
    MATCH (a:{from_label} {{name: $from_name}})
    MATCH (b:{to_label} {{name: $to_name}})
    MERGE (a)-[r:{rel}]->(b)
    """
    tx.run(query, from_name=from_name, to_name=to_name)


def ingest_transport(json_file):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    model = data["transport_model"]

    with driver.session() as session:
        session.run("""
        MERGE (m:TransportModel {name: "transport_model"})
        """)

        # 1) Equation structure
        eq = model["equation_structure"]
        eq_name = f'{eq.get("form","")}_{eq.get("spatial_dimension","")}_{eq.get("time_dependence","")}'
        session.execute_write(
            merge_variable,
            "EquationStructure",
            eq_name,
            {
                "form": eq.get("form", ""),
                "spatial_dimension": eq.get("spatial_dimension", ""),
                "time_dependence": eq.get("time_dependence", ""),
            }
        )
        session.execute_write(
            merge_relation,
            "TransportModel", "transport_model",
            "HAS_EQUATION_STRUCTURE",
            "EquationStructure", eq_name
        )

        # reaction coupling variable
        rc = eq.get("reaction_coupling", {})
        coupling_var = rc.get("coupling_variable", {})
        cname = coupling_var.get("canonical_name", "")
        if cname:
            session.execute_write(
                merge_variable,
                "Variable",
                cname,
                {
                    "paper_symbol": coupling_var.get("paper_symbol", ""),
                    "physical_meaning": coupling_var.get("physical_meaning", ""),
                    "units": coupling_var.get("units", ""),
                    "definition": coupling_var.get("definition", ""),
                    "equation_context": coupling_var.get("equation_context", ""),
                    "evidence": coupling_var.get("annotation", {}).get("evidence", ""),
                    "confidence": coupling_var.get("annotation", {}).get("confidence", ""),
                    "uncertainty_note": coupling_var.get("annotation", {}).get("uncertainty_note", ""),
                }
            )
            session.execute_write(
                merge_relation,
                "TransportModel", "transport_model",
                "HAS_REACTION_COUPLING_VARIABLE",
                "Variable", cname
            )

        # 2) Transport variable
        tv = model["transport_variable"]
        tv_name = tv.get("canonical_name", "")
        if tv_name:
            session.execute_write(
                merge_variable,
                "Variable",
                tv_name,
                {
                    "paper_symbol": tv.get("paper_symbol", ""),
                    "physical_meaning": tv.get("physical_meaning", ""),
                    "units": tv.get("units", ""),
                    "definition": tv.get("definition", ""),
                    "equation_context": tv.get("equation_context", ""),
                    "evidence": tv.get("annotation", {}).get("evidence", ""),
                    "confidence": tv.get("annotation", {}).get("confidence", ""),
                    "uncertainty_note": tv.get("annotation", {}).get("uncertainty_note", ""),
                }
            )
            session.execute_write(
                merge_relation,
                "TransportModel", "transport_model",
                "HAS_TRANSPORT_VARIABLE",
                "Variable", tv_name
            )

        # 3) Diffusion model
        dm = model["diffusion_model"]
        dm_name = dm.get("type", "")
        if dm_name:
            session.execute_write(
                merge_variable,
                "DiffusionModel",
                dm_name,
                {
                    "equation": dm.get("equation", "")
                }
            )
            session.execute_write(
                merge_relation,
                "TransportModel", "transport_model",
                "USES_DIFFUSION_MODEL",
                "DiffusionModel", dm_name
            )

        # diffusion coefficients
        coeffs = dm.get("coefficients", {})
        for _, val in coeffs.items():
            name = val.get("canonical_name", "")
            if not name:
                continue

            session.execute_write(
                merge_variable,
                "Variable",
                name,
                {
                    "paper_symbol": val.get("paper_symbol", ""),
                    "physical_meaning": val.get("physical_meaning", ""),
                    "units": val.get("units", ""),
                    "definition": val.get("definition", ""),
                    "equation_context": val.get("equation_context", ""),
                    "evidence": val.get("annotation", {}).get("evidence", ""),
                    "confidence": val.get("annotation", {}).get("confidence", ""),
                    "uncertainty_note": val.get("annotation", {}).get("uncertainty_note", ""),
                }
            )
            session.execute_write(
                merge_relation,
                "DiffusionModel", dm_name,
                "HAS_COEFFICIENT",
                "Variable", name
            )

        # dependencies
        for dep in dm.get("dependencies", []):
            session.execute_write(
                merge_variable,
                "Variable",
                dep,
                {}
            )
            session.execute_write(
                merge_relation,
                "DiffusionModel", dm_name,
                "DEPENDS_ON",
                "Variable", dep
            )

        # 4) Related variables
        related = model.get("related_variables", {})
        for _, val in related.items():
            name = val.get("canonical_name", "")
            if not name:
                continue
            session.execute_write(
                merge_variable,
                "Variable",
                name,
                {
                    "paper_symbol": val.get("paper_symbol", ""),
                    "physical_meaning": val.get("physical_meaning", ""),
                    "units": val.get("units", ""),
                    "definition": val.get("definition", ""),
                    "equation_context": val.get("equation_context", ""),
                    "evidence": val.get("annotation", {}).get("evidence", ""),
                    "confidence": val.get("annotation", {}).get("confidence", ""),
                    "uncertainty_note": val.get("annotation", {}).get("uncertainty_note", ""),
                }
            )
            session.execute_write(
                merge_relation,
                "TransportModel", "transport_model",
                "HAS_RELATED_VARIABLE",
                "Variable", name
            )

        # 5) Regime indicators
        indicators = model.get("regime_indicators", {})
        for _, val in indicators.items():
            name = val.get("canonical_name", "")
            if not name:
                continue
            session.execute_write(
                merge_variable,
                "RegimeIndicator",
                name,
                {
                    "paper_symbol": val.get("paper_symbol", ""),
                    "physical_meaning": val.get("physical_meaning", ""),
                    "units": val.get("units", ""),
                    "definition": val.get("definition", ""),
                    "equation_context": val.get("equation_context", ""),
                    "evidence": val.get("annotation", {}).get("evidence", ""),
                    "confidence": val.get("annotation", {}).get("confidence", ""),
                    "uncertainty_note": val.get("annotation", {}).get("uncertainty_note", ""),
                }
            )
            session.execute_write(
                merge_relation,
                "TransportModel", "transport_model",
                "HAS_REGIME_INDICATOR",
                "RegimeIndicator", name
            )

        # 6) Geometry coupling
        gc = model.get("geometry_coupling", {})
        feature_type = gc.get("feature_type", "")
        if feature_type:
            session.execute_write(
                merge_variable,
                "GeometryFeature",
                feature_type,
                {}
            )
            session.execute_write(
                merge_relation,
                "TransportModel", "transport_model",
                "COUPLED_TO_GEOMETRY",
                "GeometryFeature", feature_type
            )

        for _, val in gc.get("geometry_parameters", {}).items():
            name = val.get("canonical_name", "")
            if not name:
                continue
            session.execute_write(
                merge_variable,
                "GeometryParameter",
                name,
                {
                    "paper_symbol": val.get("paper_symbol", ""),
                    "physical_meaning": val.get("physical_meaning", ""),
                    "units": val.get("units", ""),
                    "definition": val.get("definition", ""),
                    "equation_context": val.get("equation_context", ""),
                    "evidence": val.get("annotation", {}).get("evidence", ""),
                    "confidence": val.get("annotation", {}).get("confidence", ""),
                    "uncertainty_note": val.get("annotation", {}).get("uncertainty_note", ""),
                }
            )
            if feature_type:
                session.execute_write(
                    merge_relation,
                    "GeometryFeature", feature_type,
                    "HAS_PARAMETER",
                    "GeometryParameter", name
                )

        hd = gc.get("hydraulic_diameter", {})
        hd_name = hd.get("canonical_name", "")
        if hd_name:
            session.execute_write(
                merge_variable,
                "GeometryParameter",
                hd_name,
                {
                    "paper_symbol": hd.get("paper_symbol", ""),
                    "physical_meaning": hd.get("physical_meaning", ""),
                    "units": hd.get("units", ""),
                    "definition": hd.get("definition", ""),
                    "equation_context": hd.get("equation_context", ""),
                    "evidence": hd.get("annotation", {}).get("evidence", ""),
                    "confidence": hd.get("annotation", {}).get("confidence", ""),
                    "uncertainty_note": hd.get("annotation", {}).get("uncertainty_note", ""),
                }
            )
            if feature_type:
                session.execute_write(
                    merge_relation,
                    "GeometryFeature", feature_type,
                    "HAS_PARAMETER",
                    "GeometryParameter", hd_name
                )

        # 7) Boundary conditions
        bc = model.get("boundary_conditions", {})
        for key, value in bc.items():
            if not value:
                continue
            bc_name = key
            session.execute_write(
                merge_variable,
                "BoundaryCondition",
                bc_name,
                {"expression": value}
            )
            session.execute_write(
                merge_relation,
                "TransportModel", "transport_model",
                "HAS_BOUNDARY_CONDITION",
                "BoundaryCondition", bc_name
            )

        # 8) Assumptions
        assumptions = model.get("assumptions", {})
        for key, value in assumptions.items():
            session.execute_write(
                merge_variable,
                "Assumption",
                key,
                {"value": value}
            )
            session.execute_write(
                merge_relation,
                "TransportModel", "transport_model",
                "HAS_ASSUMPTION",
                "Assumption", key
            )

        # 9) Solution strategy
        ss = model.get("solution_strategy", {})
        ss_name = ss.get("type", "")
        if ss_name:
            session.execute_write(
                merge_variable,
                "SolutionStrategy",
                ss_name,
                {}
            )
            session.execute_write(
                merge_relation,
                "TransportModel", "transport_model",
                "USES_SOLUTION_STRATEGY",
                "SolutionStrategy", ss_name
            )

        # 10) Source reference
        sr = model.get("source_reference", {})
        sr_name = sr.get("equation_location", "source_reference")
        session.execute_write(
            merge_variable,
            "SourceReference",
            sr_name,
            {
                "paper_title": sr.get("paper_title", ""),
                "equation_location": sr.get("equation_location", ""),
                "notes": sr.get("notes", "")
            }
        )
        session.execute_write(
            merge_relation,
            "TransportModel", "transport_model",
            "HAS_SOURCE_REFERENCE",
            "SourceReference", sr_name
        )

    print("Transport knowledge graph ingestion completed.")


if __name__ == "__main__":
    ingest_transport(r"/home/ftk3187/github/PSED/0226_kb/extracted/Ylilammi et al. - 2018 - Modeling growth kinetics of thin films made by atomic layer deposition in lateral high-aspect-ratio/transport_schema.json")
    driver.close()