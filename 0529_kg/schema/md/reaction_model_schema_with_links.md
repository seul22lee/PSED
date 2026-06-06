# ALD Conformality Modeling Knowledge Graph
## Reaction Model Schema (v1.0)

This document defines the **Reaction Model Schema** used for structured extraction of knowledge from ALD conformality modeling literature.

The schema is designed to support:

- Literature comparison of surface-reaction physics
- Structured data extraction using LLMs
- Knowledge graph construction
- Model alignment across publications

The reaction model is one of three primary components of ALD conformality models:

```text
ALD Conformality Model
    =
Transport Model
+ Reaction Model
+ Geometry Model
```

This document defines the **complete schema for the Reaction Model component**.

---

# 1. Reaction Model – Top Level Schema

JSON_PATH: reaction_model

```json
reaction_model {
  reaction_equation
  surface_species
  adsorption_model
  desorption_model
  site_balance
  reaction_coefficients
  growth_relation
  reaction_dependencies
  dimensionless_numbers
  assumptions
  reaction_regime
  boundary_coupling
  source_reference
}
```

| Field | Description |
|---|---|
| reaction_equation | Governing surface-reaction expression used in the paper |
| surface_species | Surface-state variables such as coverage or adsorbed species density |
| adsorption_model | Adsorption mechanism and adsorption-related coefficients |
| desorption_model | Desorption mechanism and desorption-related coefficients |
| site_balance | Surface site conservation and maximum occupancy information |
| reaction_coefficients | Canonical reaction coefficients used in the model |
| growth_relation | Mapping from surface reaction to growth or thickness evolution |
| reaction_dependencies | Variables on which the reaction rate depends |
| dimensionless_numbers | Dimensionless numbers used to characterize reaction regime |
| assumptions | Modeling assumptions applied to the reaction model |
| reaction_regime | Interpretation of rate-limiting behavior and coverage dependence |
| boundary_coupling | Coupling between reaction and transport, especially surface flux |
| source_reference | Provenance metadata for extraction |

---

# 2. Reaction Equation

JSON_PATH: reaction_model.reaction_equation

Defines the main kinetics expression used in the paper.

```json
reaction_equation {
  kinetics_type
  equation
  equation_terms {
    adsorption_term
    desorption_term
    surface_reaction_term
  }
}
```

## 2.1 kinetics_type

Suggested values:

| Value |
|---|
| Langmuir |
| reversible_Langmuir |
| sticking_model |
| probabilistic_adsorption |
| recombination_model |
| custom |

## 2.2 equation

Examples:

```text
dθ/dt = k_ads C (1 − θ) − k_des θ
```

```text
r = s F (1 − θ)
```

## 2.3 equation_terms

| Field | Meaning |
|---|---|
| adsorption_term | Adsorption contribution to the rate |
| desorption_term | Desorption contribution to the rate |
| surface_reaction_term | Other surface-reaction terms, if present |

---

# 3. Surface Species

JSON_PATH: reaction_model.surface_species

Defines the surface-state variables appearing in the model.

```json
surface_species {
  coverage_variable {
    canonical_name
    paper_symbol
    physical_meaning
    units
  }
  surface_density_variable {
    canonical_name
    paper_symbol
    physical_meaning
    units
  }
}
```

## 3.1 coverage_variable

Typical canonical name:

| Canonical Name |
|---|
| surface_coverage |

Example meanings:

- fraction of occupied adsorption sites
- normalized surface occupancy
- fraction of reactive sites consumed

## 3.2 surface_density_variable

Typical canonical name:

| Canonical Name |
|---|
| adsorbed_species_density |

Use this field when the paper expresses the surface state as a density rather than a dimensionless coverage.

---

# 4. Adsorption Model

JSON_PATH: reaction_model.adsorption_model

Defines the adsorption mechanism.

```json
adsorption_model {
  model_type
  adsorption_rate_expression
  sticking_coefficient {
    canonical_name
    paper_symbol
    physical_meaning
    units
    definition
    equation_context
  }
  collision_flux {
    canonical_name
    paper_symbol
    physical_meaning
    units
    definition
    equation
  }
}
```

## 4.1 model_type

Suggested values:

| Value |
|---|
| Langmuir_adsorption |
| sticking_model |
| probabilistic_adsorption |
| custom |

## 4.2 adsorption_rate_expression

Examples:

```text
k_ads C (1 − θ)
```

```text
s F (1 − θ)
```

## 4.3 sticking_coefficient

This field must capture the **canonical concept** separately from the paper symbol.

Example:

```json
{
  "canonical_name": "sticking_probability",
  "paper_symbol": "β",
  "physical_meaning": "probability that a precursor molecule adsorbs upon collision",
  "units": "dimensionless",
  "definition": "probability of adsorption upon collision",
  "equation_context": "adsorption_rate"
}
```

Important note: the same concept may appear with different symbols across papers, such as `s`, `β`, or `c`.

## 4.4 collision_flux

Used when the adsorption rate is written in terms of molecular collision flux.

Example fields:

- paper symbol: `F`
- physical meaning: collision flux of precursor molecules to the surface

---

# 5. Desorption Model

JSON_PATH: reaction_model.desorption_model

Defines whether desorption is included and how it is represented.

```json
desorption_model {
  present
  desorption_rate_expression
  desorption_rate_constant {
    canonical_name
    paper_symbol
    physical_meaning
    units
    definition
    equation_context
  }
}
```

## 5.1 present

| Value |
|---|
| true |
| false |

If `false`, the model typically assumes irreversible adsorption.

## 5.2 desorption_rate_expression

Example:

```text
k_des θ
```

---

# 6. Site Balance

JSON_PATH: reaction_model.site_balance

Defines site conservation and saturation constraints.

```json
site_balance {
  site_density {
    canonical_name
    paper_symbol
    physical_meaning
    units
    definition
    equation_context
  }
  site_balance_equation
  maximum_coverage {
    canonical_name
    paper_symbol
    physical_meaning
    value
    units
  }
}
```

Examples:

```text
θ + θ_vacant = 1
```

```text
Γ ≤ q
```

Typical site-density concept:

- adsorption site density
- active site density
- saturation site concentration

---

# 7. Reaction Coefficients

JSON_PATH: reaction_model.reaction_coefficients

Stores canonical coefficients that define the reaction model.

```json
reaction_coefficients {
  adsorption_rate_constant {
    canonical_name
    paper_symbol
    physical_meaning
    units
    definition
    equation_context
  }
  desorption_rate_constant {
    canonical_name
    paper_symbol
    physical_meaning
    units
    definition
    equation_context
  }
  sticking_probability {
    canonical_name
    paper_symbol
    physical_meaning
    units
    definition
    equation_context
  }
  reaction_probability {
    canonical_name
    paper_symbol
    physical_meaning
    units
    definition
    equation_context
  }
}
```

## Important note on coefficient symbols

Coefficient symbols vary strongly across papers. For example:

| Canonical Concept | Possible Paper Symbols |
|---|---|
| sticking_probability | `s`, `β`, `c` |
| surface_coverage | `θ`, `h`, `f` |
| site_density | `q`, `N_s` |

Therefore, schema instances must always store both:


### Annotation Metadata

All canonical variable blocks should include provenance metadata.

Structure:

    annotation {
        evidence
        confidence
        uncertainty_note
    }

Field meanings:

evidence
    location in the paper where the information was found
    (example: Eq. (4), Section 3.2)

confidence
    extraction confidence level (high / medium / low)

uncertainty_note
    optional explanation of ambiguity


- `canonical_name`
- `paper_symbol`

The **canonical concept** is the stable identifier; the symbol is metadata tied to a specific paper.

---

# 8. Growth Relation

JSON_PATH: reaction_model.growth_relation

Defines how surface reaction is linked to film growth.

```json
growth_relation {
  growth_per_cycle {
    canonical_name
    paper_symbol
    physical_meaning
    units
    definition
  }
  growth_rate_expression
  surface_growth_coupling
}
```

Examples:

```text
GPC = q θ
```

```text
growth_rate = f(coverage)
```

This section is important because it connects the reaction model to the geometry model.

---

# 9. Reaction Dependencies

JSON_PATH: reaction_model.reaction_dependencies

Stores the variables that influence reaction rate.

```json
reaction_dependencies {
  gas_phase_variable
  surface_coverage
  temperature_dependence
  pressure_dependence
}
```

Typical dependencies include:

- gas-phase precursor pressure or concentration
- coverage dependence
- temperature-dependent rate constants
- pressure dependence

---

# 10. Dimensionless Numbers

JSON_PATH: reaction_model.dimensionless_numbers

Stores reaction-related dimensionless numbers used in the paper.

```json
dimensionless_numbers {
  damkohler_number
  thiele_modulus
}
```

Use these fields when the paper explicitly introduces a dimensionless number to describe regime behavior.

---

# 11. Assumptions

JSON_PATH: reaction_model.assumptions

Stores assumptions that define the reaction model.

```json
assumptions {
  irreversible_adsorption
  single_site_adsorption
  self_limiting_reaction
  no_surface_diffusion
  uniform_surface
  coverage_independent_sticking
}
```

## Suggested meanings

| Field | Meaning |
|---|---|
| irreversible_adsorption | Desorption neglected or set to zero |
| single_site_adsorption | One-site Langmuir-type occupation assumed |
| self_limiting_reaction | Reaction saturates as sites are filled |
| no_surface_diffusion | No lateral migration on the surface |
| uniform_surface | All surface sites treated as equivalent |
| coverage_independent_sticking | Sticking treated as constant, unless stated otherwise |

These assumptions often appear in prose rather than equations, so they should be extracted from both equations and text.

---

# 12. Reaction Regime

JSON_PATH: reaction_model.reaction_regime

Provides the paper's interpretation of the kinetic regime.

```json
reaction_regime {
  rate_limiting_step
  reaction_order
  coverage_dependence
}
```

Examples:

- adsorption-limited
- transport-limited with implicit fast reaction
- first-order adsorption
- coverage-dependent sticking

---

# 13. Boundary Coupling

JSON_PATH: reaction_model.boundary_coupling

Defines how the reaction model couples back to the transport model.

```json
boundary_coupling {
  surface_flux_expression
  transport_reaction_coupling
}
```

Examples:

```text
transport sink term = reaction rate
```

```text
surface adsorption flux used as wall boundary condition
```

This is the key interface between transport and reaction models.

---

# 14. Source Reference

JSON_PATH: reaction_model.source_reference

Stores provenance information for extraction.

```json
source_reference {
  paper_title
  equation_location
  notes
}
```

Suggested contents:

- paper title
- equation number or page number
- extraction notes
- ambiguity notes

---

# 15. Example Reaction Model Instance

Example in the style of **Ylilammi et al. (2018)**:

```json
{
  "reaction_model": {
    "reaction_equation": {
      "kinetics_type": "Langmuir",
      "equation": "dθ/dt = k_ads p_A (1 − θ)",
      "equation_terms": {
        "adsorption_term": "k_ads p_A (1 − θ)",
        "desorption_term": "",
        "surface_reaction_term": ""
      }
    },
    "surface_species": {
      "coverage_variable": {
        "canonical_name": "surface_coverage",
        "paper_symbol": "θ",
        "physical_meaning": "fraction of occupied adsorption sites",
        "units": "dimensionless"
      },
      "surface_density_variable": {
        "canonical_name": "adsorbed_species_density",
        "paper_symbol": "",
        "physical_meaning": "",
        "units": ""
      }
    },
    "adsorption_model": {
      "model_type": "Langmuir_adsorption",
      "adsorption_rate_expression": "k_ads p_A (1 − θ)",
      "sticking_coefficient": {
        "canonical_name": "sticking_probability",
        "paper_symbol": "c",
        "physical_meaning": "probability that a precursor molecule adsorbs upon collision",
        "units": "dimensionless",
        "definition": "sticking probability",
        "equation_context": "adsorption_rate"
      },
      "collision_flux": {
        "canonical_name": "collision_flux",
        "paper_symbol": "",
        "physical_meaning": "",
        "units": "",
        "definition": "",
        "equation": ""
      }
    },
    "desorption_model": {
      "present": false,
      "desorption_rate_expression": "",
      "desorption_rate_constant": {
        "canonical_name": "desorption_rate_constant",
        "paper_symbol": "",
        "physical_meaning": "",
        "units": "",
        "definition": "",
        "equation_context": ""
      }
    },
    "site_balance": {
      "site_density": {
        "canonical_name": "site_density",
        "paper_symbol": "q",
        "physical_meaning": "adsorption site density",
        "units": "",
        "definition": "adsorption site density",
        "equation_context": "growth_relation"
      },
      "site_balance_equation": "",
      "maximum_coverage": {
        "canonical_name": "maximum_surface_coverage",
        "paper_symbol": "",
        "physical_meaning": "",
        "value": "",
        "units": "dimensionless"
      }
    },
    "reaction_coefficients": {
      "adsorption_rate_constant": {
        "canonical_name": "adsorption_rate_constant",
        "paper_symbol": "k_ads",
        "physical_meaning": "adsorption rate constant",
        "units": "",
        "definition": "",
        "equation_context": "reaction_equation"
      },
      "desorption_rate_constant": {
        "canonical_name": "desorption_rate_constant",
        "paper_symbol": "",
        "physical_meaning": "",
        "units": "",
        "definition": "",
        "equation_context": ""
      },
      "sticking_probability": {
        "canonical_name": "sticking_probability",
        "paper_symbol": "c",
        "physical_meaning": "sticking probability",
        "units": "dimensionless",
        "definition": "",
        "equation_context": "adsorption_model"
      },
      "reaction_probability": {
        "canonical_name": "reaction_probability",
        "paper_symbol": "",
        "physical_meaning": "",
        "units": "dimensionless",
        "definition": "",
        "equation_context": ""
      }
    },
    "growth_relation": {
      "growth_per_cycle": {
        "canonical_name": "growth_per_cycle",
        "paper_symbol": "",
        "physical_meaning": "",
        "units": "",
        "definition": ""
      },
      "growth_rate_expression": "",
      "surface_growth_coupling": ""
    },
    "reaction_dependencies": {
      "gas_phase_variable": "p_A",
      "surface_coverage": "θ",
      "temperature_dependence": "",
      "pressure_dependence": "dependent on precursor partial pressure"
    },
    "dimensionless_numbers": {
      "damkohler_number": "",
      "thiele_modulus": ""
    },
    "assumptions": {
      "irreversible_adsorption": true,
      "single_site_adsorption": true,
      "self_limiting_reaction": true,
      "no_surface_diffusion": true,
      "uniform_surface": true,
      "coverage_independent_sticking": false
    },
    "reaction_regime": {
      "rate_limiting_step": "",
      "reaction_order": "",
      "coverage_dependence": "adsorption decreases as coverage increases"
    },
    "boundary_coupling": {
      "surface_flux_expression": "",
      "transport_reaction_coupling": "transport sink term equals surface adsorption rate"
    },
    "source_reference": {
      "paper_title": "Ylilammi et al. (2018)",
      "equation_location": "",
      "notes": ""
    }
  }
}
```

---

# 16. Recommended Use

This reaction schema can be used in four ways:

1. **Documentation**  
   As the formal ontology/specification for reaction-model extraction.

2. **LLM Prompting**  
   Paste the schema into prompts and ask the model to fill the fields.

3. **Manual Annotation**  
   Use it as a structured reaction-model card for each paper.

4. **Knowledge Graph Ingestion**  
   Convert canonical fields into graph nodes and edges.

---

# 17. Most Important Fields

For reliable extraction, the most important fields are:

```text
kinetics_type
adsorption_rate_expression
coverage_variable
sticking_coefficient
assumptions
```

These fields capture most of the scientifically meaningful variation across ALD reaction models.

---

# End of Schema
