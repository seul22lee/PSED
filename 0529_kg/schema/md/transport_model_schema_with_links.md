# ALD Conformality Modeling Knowledge Graph

## Transport Model Schema (v1.1)

This document defines the **Transport Model Schema** used for structured
extraction of knowledge from ALD conformality modeling literature.\
The schema is designed to support:

-   Literature comparison of transport physics
-   Structured data extraction using LLMs
-   Knowledge graph construction
-   Model alignment across publications

The transport model is one of three primary components of ALD
conformality models:

    ALD Conformality Model
        =
    Transport Model
    + Reaction Model
    + Geometry Model

This document defines the **complete schema for the Transport Model
component**.

------------------------------------------------------------------------

# Canonical Variable Design Principle

Scientific papers often use **different symbols for the same physical
quantity**.

Example:

  Physical Concept                    Paper Symbols
  ----------------------------------  -----------------
  effective diffusion coefficient     D, D_eff, D_K
  gas-phase precursor pressure        p_A
  gas-phase precursor concentration   C_A
  surface flux                        F
  Knudsen number                      Kn

To normalize these differences, every variable or coefficient in this
schema follows the structure:

    {
      canonical_name
      paper_symbol
      physical_meaning
      units
      definition
      equation_context

      annotation {
          evidence
          confidence
          uncertainty_note
      }
    }

Where:

  Field             Meaning
  ----------------- ---------------------------------------------------------
  canonical_name    canonical physical quantity used in the knowledge graph
  paper_symbol      symbol used in the specific paper
  physical_meaning  description of the variable
  units             physical units
  definition        definition or interpretation
  equation_context  equation where the variable appears

annotation {
    evidence
    confidence
    uncertainty_note
}

evidence
    location in the paper where the information was found
    (example: Eq. (4), Section 3.2)

confidence
    extraction confidence level (high / medium / low)

uncertainty_note
    optional explanation of ambiguity


This separation enables **notation-independent comparison across
papers**.

------------------------------------------------------------------------

# 1. Transport Model -- Top Level Schema

JSON_PATH: transport_model

    transport_model {
        equation_structure
        transport_variable
        diffusion_model
        related_variables
        regime_indicators
        geometry_coupling
        boundary_conditions
        assumptions
        solution_strategy
    }

  Field                 Description
  --------------------- ---------------------------------------------------
  equation_structure    Structure of the governing transport equation
  transport_variable    Gas-phase precursor variable used in the model
  diffusion_model       Definition of the effective diffusion coefficient
  related_variables     Variables appearing in the transport equation
  regime_indicators     Parameters indicating transport regime
  geometry_coupling     Relationship between transport and geometry
  boundary_conditions   Boundary conditions for the PDE
  assumptions           Modeling assumptions
  solution_strategy     Analytical or numerical solution method

------------------------------------------------------------------------

# 2. Equation Structure

JSON_PATH: transport_model.equation_structure

    equation_structure {
        form
        spatial_dimension
        time_dependence
        reaction_coupling
        convection_term
    }

### form

  Value
  -------------------------------
  diffusion
  diffusion_reaction
  convection_diffusion
  convection_diffusion_reaction

### spatial_dimension

  Value
  --------
  1D
  2D
  3D
  radial

### time_dependence

  Value
  --------------
  transient
  steady_state

### reaction_coupling

    reaction_coupling {
        sink_term_present: true / false
        coupling_variable {
            canonical_name
            paper_symbol
            definition
        }
    }

### convection_term

    convection_term {
        present: true / false
        velocity_variable {
            canonical_name
            paper_symbol
            units
            definition
        }
    }

------------------------------------------------------------------------

# 3. Transport Variable

JSON_PATH: transport_model.transport_variable

The gas-phase reactant variable used in the transport equation.

    transport_variable {
        canonical_name
        paper_symbol
        physical_meaning
        units
        definition
        equation_context
    }

Example

    {
      canonical_name: gas_phase_pressure
      paper_symbol: p_A
      physical_meaning: precursor partial pressure
      units: Pa
      definition: gas-phase partial pressure of precursor A
      equation_context: governing transport equation
    }

Possible canonical variables

  Canonical Variable
  --------------------------
  gas_phase_pressure
  gas_phase_concentration
  gas_phase_number_density
  gas_phase_flux

------------------------------------------------------------------------

# 4. Diffusion Model

JSON_PATH: transport_model.diffusion_model

Defines how the diffusion coefficient is modeled.

    diffusion_model {
        type
        equation
        coefficients
        dependencies
    }

### diffusion_model.type

  Type
  ------------------------------
  molecular_diffusion
  knudsen_diffusion
  bosanquet_diffusion
  effective_pore_diffusion
  pressure_dependent_diffusion

### diffusion_model.equation

Example

    D_eff = (1/D_A + 1/D_K)^(-1)

or

    D_K = (2/3) r sqrt(8RT / πM)

### diffusion_model.coefficients

Each coefficient follows the canonical variable structure.

    coefficients {
        molecular_diffusion_coefficient {
            canonical_name
            paper_symbol
            physical_meaning
            units
            definition
            equation_context
        }

        knudsen_diffusion_coefficient {
            canonical_name
            paper_symbol
            physical_meaning
            units
            definition
            equation_context
        }

        effective_diffusion_coefficient {
            canonical_name
            paper_symbol
            physical_meaning
            units
            definition
            equation_context
        }
    }

Example

    effective_diffusion_coefficient {
        canonical_name: effective_diffusion_coefficient
        paper_symbol: D_eff
        physical_meaning: diffusion coefficient used in the transport equation
        units: m2/s
        definition: effective diffusion coefficient in feature-scale transport
        equation_context: diffusion_model.equation
    }

This allows the same concept to be normalized across papers even if one
paper uses `D`, another uses `D_eff`, and another uses `D_K`.

### diffusion_model.dependencies

    dependencies {
        temperature
        pressure
        pore_radius
        molecular_mass
    }

------------------------------------------------------------------------

# 5. Related Variables

JSON_PATH: transport_model.related_variables

Variables appearing in the transport equation.

    related_variables {
        spatial_coordinate
        time
        diffusion_coefficient
    }

Each variable may be represented in canonical form.

Example

    spatial_coordinate {
        canonical_name: spatial_coordinate
        paper_symbol: x
        physical_meaning: position along transport direction
        units: m
        definition: axial coordinate in feature
        equation_context: governing transport equation
    }

    time {
        canonical_name: time
        paper_symbol: t
        physical_meaning: time
        units: s
        definition: temporal coordinate
        equation_context: governing transport equation
    }

    diffusion_coefficient {
        canonical_name: effective_diffusion_coefficient
        paper_symbol: D_eff
        physical_meaning: diffusion coefficient used in equation
        units: m2/s
        definition: shorthand variable appearing in transport equation
        equation_context: governing transport equation
    }

------------------------------------------------------------------------

# 6. Regime Indicators

JSON_PATH: transport_model.regime_indicators

Parameters used to determine transport regime.

    regime_indicators {
        knudsen_number
        mean_free_path
        pressure
    }

Each indicator may be represented in canonical form.

Example

    knudsen_number {
        canonical_name: knudsen_number
        paper_symbol: Kn
        physical_meaning: ratio of mean free path to characteristic length
        units: dimensionless
        definition: Kn = λ / D
        equation_context: regime classification
    }

------------------------------------------------------------------------

# 7. Geometry Coupling

JSON_PATH: transport_model.geometry_coupling

Describes how the transport model depends on geometry.

    geometry_coupling {
        feature_type
        geometry_parameters
        hydraulic_diameter
    }

### feature_type

  Type
  -----------------
  trench
  hole
  LHAR_channel
  porous_particle

### geometry_parameters

  Parameter
  -----------
  height
  width
  depth
  radius

Each geometry-related quantity may also be stored in canonical form.

Example

    hydraulic_diameter {
        canonical_name: hydraulic_diameter
        paper_symbol: h
        physical_meaning: characteristic length scale used in transport model
        units: m
        definition: hydraulic diameter of the feature
        equation_context: geometry_coupling
    }

------------------------------------------------------------------------

# 8. Boundary Conditions

JSON_PATH: transport_model.boundary_conditions

Boundary conditions used in the transport equation.

    boundary_conditions {
        inlet_condition
        wall_condition
        symmetry_condition
    }

Example

    inlet_condition: C = C0
    wall_condition: adsorption_flux

------------------------------------------------------------------------

# 9. Assumptions

JSON_PATH: transport_model.assumptions

Modeling assumptions applied to the transport model.

    assumptions {
        dimensionality
        isothermal
        constant_diffusion
        molecular_flow
        steady_state
    }

Example

    assumptions {
        dimensionality: 1D
        isothermal: true
        constant_diffusion: true
    }

------------------------------------------------------------------------

# 10. Solution Strategy

JSON_PATH: transport_model.solution_strategy

How the transport equation is solved.

    solution_strategy {
        type
    }

  Solution Type
  ---------------
  analytical
  numerical
  reduced_model

------------------------------------------------------------------------

# 11. Example: Transport Model Instance

Example extracted from **Ylilammi et al. (2018)**

    transport_model {

    equation_structure {
        form: diffusion_reaction
        spatial_dimension: 1D
        time_dependence: transient
        reaction_coupling {
            sink_term_present: true
            coupling_variable {
                canonical_name: surface_coverage
                paper_symbol: θ
                definition: fraction of occupied sites
            }
        }
        convection_term {
            present: false
            velocity_variable {
                canonical_name: gas_velocity
                paper_symbol:
                units: m/s
                definition:
            }
        }
    }

    transport_variable {
        canonical_name: gas_phase_pressure
        paper_symbol: p_A
        physical_meaning: precursor partial pressure
        units: Pa
        definition: gas-phase partial pressure of precursor A
        equation_context: governing transport equation
    }

    diffusion_model {
        type: bosanquet_diffusion
        equation: D_eff = (1/D_A + 1/D_K)^(-1)

        coefficients {
            molecular_diffusion_coefficient {
                canonical_name: molecular_diffusion_coefficient
                paper_symbol: D_A
                physical_meaning: molecular diffusion coefficient
                units: m2/s
                definition:
                equation_context: diffusion_model.equation
            }

            knudsen_diffusion_coefficient {
                canonical_name: knudsen_diffusion_coefficient
                paper_symbol: D_K
                physical_meaning: Knudsen diffusion coefficient
                units: m2/s
                definition:
                equation_context: diffusion_model.equation
            }

            effective_diffusion_coefficient {
                canonical_name: effective_diffusion_coefficient
                paper_symbol: D_eff
                physical_meaning: effective diffusion coefficient
                units: m2/s
                definition:
                equation_context: diffusion_model.equation
            }
        }
    }

    regime_indicators {
        knudsen_number {
            canonical_name: knudsen_number
            paper_symbol: Kn
            physical_meaning: ratio of mean free path to characteristic length
            units: dimensionless
            definition:
            equation_context: regime classification
        }
    }

    geometry_coupling {
        feature_type: LHAR_channel
        hydraulic_diameter {
            canonical_name: hydraulic_diameter
            paper_symbol: h
            physical_meaning: characteristic length used in diffusion model
            units: m
            definition:
            equation_context: geometry_coupling
        }
    }

    assumptions {
        dimensionality: 1D
        isothermal: true
    }
    }

------------------------------------------------------------------------

# 12. Knowledge Graph Mapping

When converted to a knowledge graph:

    Paper
      └─HAS_TRANSPORT_MODEL
            ├ equation_structure
            ├ diffusion_model
            ├ assumptions
            └ regime_indicators

This allows comparison of transport physics across literature.

Variable normalization occurs through:

    canonical_name → symbol alias

Example:

    effective_diffusion_coefficient
       ├ symbol: D_eff (Paper A)
       ├ symbol: D (Paper B)
       └ symbol: D_K (Paper C)

------------------------------------------------------------------------

# 13. Core Fields (Most Important)

For reliable automated extraction, the following fields are the most
critical:

    equation_structure
    diffusion_model
    transport_variable
    assumptions

These four fields capture most transport-model differences across ALD
conformality literature.

------------------------------------------------------------------------

# End of Schema
