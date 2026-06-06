import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from neo4j import GraphDatabase
# --------------------------------
# Config
# --------------------------------
from config import OUTPUT_DIR, STEP, NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
# --------------------------------
# Utils
# --------------------------------

def load_json(path: Path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
def normalize_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()
def ensure_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
def first_nonempty(data: Dict[str, Any], keys: Iterable[str], default: str = "") -> str:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
        if value is not None and not isinstance(value, (dict, list)):
            text = str(value).strip()
            if text:
                return text
    return default
def read_nested_list(data: Dict[str, Any], candidate_keys: Iterable[str]) -> List[Any]:
    for key in candidate_keys:
        value = data.get(key)
        if isinstance(value, list):
            return value
    return []
def infer_process_type(schema_path: Path) -> str:
    name = schema_path.name.lower()
    if "geometry" in name:
        return "geometry"
    if "reaction" in name:
        return "reaction"
    if "transport" in name:
        return "transport"
    return "unknown"
def infer_model_name(schema: Dict[str, Any], schema_path: Path) -> str:
    candidates = [
        "model_name",
        "name",
        "title",
        "canonical_name",
        "model",
    ]
    model_name = first_nonempty(schema, candidates)
    if model_name:
        return model_name
    # fallback
    return schema_path.stem.replace("_schema", "").strip()
def infer_paper_name(schema_path: Path) -> str:
    return schema_path.parent.name.strip()
def extract_equations(schema: Dict[str, Any]) -> List[Dict[str, str]]:
    raw = read_nested_list(
        schema,
        [
            "equations",
            "equation_list",
            "governing_equations",
            "model_equations",
        ],
    )
    results: List[Dict[str, str]] = []
    for item in raw:
        if isinstance(item, str):
            expr = item.strip()
            if expr:
                results.append(
                    {
                        "equation": expr,
                        "equation_id": "",
                        "description": "",
                    }
                )
        elif isinstance(item, dict):
            expr = first_nonempty(item, ["equation", "expr", "expression", "latex", "text"])
            eq_id = first_nonempty(item, ["equation_id", "id", "name", "label"])
            desc = first_nonempty(item, ["description", "meaning", "notes", "explanation"])
            if expr or eq_id:
                results.append(
                    {
                        "equation": expr,
                        "equation_id": eq_id,
                        "description": desc,
                    }
                )
    return results
def extract_variables(schema: Dict[str, Any]) -> List[Dict[str, str]]:
    raw = read_nested_list(
        schema,
        [
            "variables",
            "symbols",
            "state_variables",
            "model_variables",
        ],
    )
    results: List[Dict[str, str]] = []
    for item in raw:
        if isinstance(item, str):
            name = item.strip()
            if name:
                results.append(
                    {
                        "name": name,
                        "symbol": name,
                        "description": "",
                        "unit": "",
                    }
                )
        elif isinstance(item, dict):
            name = first_nonempty(item, ["name", "variable_name", "canonical_name"])
            symbol = first_nonempty(item, ["symbol", "notation", "variable", "label"], default=name)
            desc = first_nonempty(item, ["description", "meaning", "definition", "role"])
            unit = first_nonempty(item, ["unit", "units"])
            if name or symbol:
                results.append(
                    {
                        "name": name or symbol,
                        "symbol": symbol or name,
                        "description": desc,
                        "unit": unit,
                    }
                )
    return results
def extract_parameters(schema: Dict[str, Any]) -> List[Dict[str, str]]:
    raw = read_nested_list(
        schema,
        [
            "parameters",
            "constants",
            "model_parameters",
            "fitting_parameters",
        ],
    )
    results: List[Dict[str, str]] = []
    for item in raw:
        if isinstance(item, str):
            name = item.strip()
            if name:
                results.append(
                    {
                        "name": name,
                        "symbol": name,
                        "value": "",
                        "unit": "",
                        "description": "",
                    }
                )
        elif isinstance(item, dict):
            name = first_nonempty(item, ["name", "parameter_name", "canonical_name"])
            symbol = first_nonempty(item, ["symbol", "notation", "parameter", "label"], default=name)
            value = first_nonempty(item, ["value", "default_value", "estimated_value"])
            unit = first_nonempty(item, ["unit", "units"])
            desc = first_nonempty(item, ["description", "meaning", "definition", "role"])
            if name or symbol:
                results.append(
                    {
                        "name": name or symbol,
                        "symbol": symbol or name,
                        "value": value,
                        "unit": unit,
                        "description": desc,
                    }
                )
    return results
def extract_assumptions(schema: Dict[str, Any]) -> List[str]:
    raw = read_nested_list(
        schema,
        [
            "assumptions",
            "model_assumptions",
            "constraints",
            "simplifications",
        ],
    )
    results: List[str] = []
    for item in raw:
        if isinstance(item, str):
            text = item.strip()
            if text:
                results.append(text)
        elif isinstance(item, dict):
            text = first_nonempty(item, ["text", "assumption", "description", "statement"])
            if text:
                results.append(text)
    return results
def extract_materials(schema: Dict[str, Any]) -> List[str]:
    raw = read_nested_list(
        schema,
        [
            "materials",
            "species",
            "precursors",
            "reactants",
            "products",
        ],
    )
    results: List[str] = []
    for item in raw:
        if isinstance(item, str):
            text = item.strip()
            if text:
                results.append(text)
        elif isinstance(item, dict):
            text = first_nonempty(item, ["name", "material", "species", "compound"])
            if text:
                results.append(text)
    return results
# --------------------------------
# Neo4j
# --------------------------------

def create_constraints(driver) -> None:
    queries = [
        "CREATE CONSTRAINT paper_name IF NOT EXISTS FOR (n:Paper) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT model_key IF NOT EXISTS FOR (n:Model) REQUIRE n.key IS UNIQUE",
        "CREATE CONSTRAINT equation_key IF NOT EXISTS FOR (n:Equation) REQUIRE n.key IS UNIQUE",
        "CREATE CONSTRAINT variable_key IF NOT EXISTS FOR (n:Variable) REQUIRE n.key IS UNIQUE",
        "CREATE CONSTRAINT parameter_key IF NOT EXISTS FOR (n:Parameter) REQUIRE n.key IS UNIQUE",
        "CREATE CONSTRAINT assumption_key IF NOT EXISTS FOR (n:Assumption) REQUIRE n.key IS UNIQUE",
        "CREATE CONSTRAINT process_name IF NOT EXISTS FOR (n:Process) REQUIRE n.name IS UNIQUE",
        "CREATE CONSTRAINT material_name IF NOT EXISTS FOR (n:Material) REQUIRE n.name IS UNIQUE",
    ]
    with driver.session() as session:
        for query in queries:
            session.run(query)
def merge_schema_into_graph(
    tx,
    paper_name: str,
    model_name: str,
    process_type: str,
    source_path: str,
    equations: List[Dict[str, str]],
    variables: List[Dict[str, str]],
    parameters: List[Dict[str, str]],
    assumptions: List[str],
    materials: List[str],
) -> None:
    model_key = f"{paper_name}::{model_name}::{process_type}"
    tx.run(
        """
        MERGE (p:Paper {name: $paper_name})
        MERGE (pr:Process {name: $process_type})
        MERGE (m:Model {key: $model_key})
        SET m.name = $model_name,
            m.process_type = $process_type,
            m.source_path = $source_path
        MERGE (p)-[:PROPOSES]->(m)
        MERGE (m)-[:MODELS]->(pr)
        """,
        paper_name=paper_name,
        process_type=process_type,
        model_key=model_key,
        model_name=model_name,
        source_path=source_path,
    )
    for eq in equations:
        eq_expr = normalize_str(eq.get("equation"))
        eq_id = normalize_str(eq.get("equation_id"))
        eq_desc = normalize_str(eq.get("description"))
        eq_key = f"{model_key}::equation::{eq_id or eq_expr}"
        if not (eq_expr or eq_id):
            continue
        tx.run(
            """
            MERGE (e:Equation {key: $eq_key})
            SET e.expression = $eq_expr,
                e.equation_id = $eq_id,
                e.description = $eq_desc
            WITH e
            MATCH (m:Model {key: $model_key})
            MERGE (m)-[:HAS_EQUATION]->(e)
            """,
            eq_key=eq_key,
            eq_expr=eq_expr,
            eq_id=eq_id,
            eq_desc=eq_desc,
            model_key=model_key,
        )
    for var in variables:
        var_name = normalize_str(var.get("name"))
        var_symbol = normalize_str(var.get("symbol"))
        var_desc = normalize_str(var.get("description"))
        var_unit = normalize_str(var.get("unit"))
        var_key = f"{model_key}::variable::{var_symbol or var_name}"
        if not (var_name or var_symbol):
            continue
        tx.run(
            """
            MERGE (v:Variable {key: $var_key})
            SET v.name = $var_name,
                v.symbol = $var_symbol,
                v.description = $var_desc,
                v.unit = $var_unit
            WITH v
            MATCH (m:Model {key: $model_key})
            MERGE (m)-[:HAS_VARIABLE]->(v)
            """,
            var_key=var_key,
            var_name=var_name,
            var_symbol=var_symbol,
            var_desc=var_desc,
            var_unit=var_unit,
            model_key=model_key,
        )
    for param in parameters:
        param_name = normalize_str(param.get("name"))
        param_symbol = normalize_str(param.get("symbol"))
        param_value = normalize_str(param.get("value"))
        param_unit = normalize_str(param.get("unit"))
        param_desc = normalize_str(param.get("description"))
        param_key = f"{model_key}::parameter::{param_symbol or param_name}"
        if not (param_name or param_symbol):
            continue
        tx.run(
            """
            MERGE (p:Parameter {key: $param_key})
            SET p.name = $param_name,
                p.symbol = $param_symbol,
                p.value = $param_value,
                p.unit = $param_unit,
                p.description = $param_desc
            WITH p
            MATCH (m:Model {key: $model_key})
            MERGE (m)-[:HAS_PARAMETER]->(p)
            """,
            param_key=param_key,
            param_name=param_name,
            param_symbol=param_symbol,
            param_value=param_value,
            param_unit=param_unit,
            param_desc=param_desc,
            model_key=model_key,
        )
    for assumption in assumptions:
        assumption = normalize_str(assumption)
        if not assumption:
            continue
        assumption_key = f"{model_key}::assumption::{assumption}"
        tx.run(
            """
            MERGE (a:Assumption {key: $assumption_key})
            SET a.text = $assumption
            WITH a
            MATCH (m:Model {key: $model_key})
            MERGE (m)-[:ASSUMES]->(a)
            """,
            assumption_key=assumption_key,
            assumption=assumption,
            model_key=model_key,
        )
    for material in materials:
        material = normalize_str(material)
        if not material:
            continue
        tx.run(
            """
            MERGE (mat:Material {name: $material})
            WITH mat
            MATCH (m:Model {key: $model_key})
            MERGE (m)-[:INVOLVES_MATERIAL]->(mat)
            """,
            material=material,
            model_key=model_key,
        )
def ingest_one_schema(driver, schema_path: Path) -> None:
    schema = load_json(schema_path)
    paper_name = infer_paper_name(schema_path)
    process_type = infer_process_type(schema_path)
    model_name = infer_model_name(schema, schema_path)
    equations = extract_equations(schema)
    variables = extract_variables(schema)
    parameters = extract_parameters(schema)
    assumptions = extract_assumptions(schema)
    materials = extract_materials(schema)
    with driver.session() as session:
        session.execute_write(
            merge_schema_into_graph,
            paper_name,
            model_name,
            process_type,
            str(schema_path),
            equations,
            variables,
            parameters,
            assumptions,
            materials,
        )
    print(f"[OK] {schema_path}")
def main() -> None:
    schema_files = sorted(OUTPUT_DIR.rglob("*_schema.json"))
    if not schema_files:
        print("No schema files found.")
        return
    print(f"Found {len(schema_files)} schema files.")
    driver = GraphDatabase.driver(
        NEO4J_URI,
        auth=(NEO4J_USER, NEO4J_PASSWORD),
    )
    try:
        create_constraints(driver)
        for schema_path in schema_files:
            try:
                ingest_one_schema(driver, schema_path)
            except Exception as e:
                print(f"[FAIL] {schema_path}")
                print(e)
    finally:
        driver.close()
    print("Done.")
if __name__ == "__main__":
    main()