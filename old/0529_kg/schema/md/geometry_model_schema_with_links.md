# ALD Conformality Modeling Knowledge Graph

## Geometry Model Schema (v1.0)

This document defines the **Geometry Model Schema** used for structured
extraction of knowledge from ALD conformality modeling literature.

The schema is designed to support:

- Literature comparison of geometry assumptions and feature definitions
- Structured data extraction using LLMs
- Knowledge graph construction
- Model alignment across publications

The geometry model is one of three primary components of ALD conformality models:

    ALD Conformality Model
        =
    Transport Model
    + Reaction Model
    + Geometry Model

This document defines the **complete schema for the Geometry Model component**.

------------------------------------------------------------------------

# Canonical Variable Design Principle

Scientific papers often use **different symbols for the same geometric
quantity**.

Example:

  Physical Concept            Paper Symbols
  --------------------------  ----------------
  feature height              H, h
  feature width               W
  feature depth               L, D
  pore radius                 r, R
  aspect ratio                AR
  hydraulic diameter          h, d_h
  surface area                A
  characteristic length       H, W, d_h

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
  equation_context  equation or section where the variable appears

This separation enables **notation-independent comparison across papers**.


### Annotation Metadata

Each extracted canonical variable should include provenance metadata.

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


------------------------------------------------------------------------

# Geometry Canonical Variable Set (v1)

The following canonical variables are the core geometry concepts that
appear across ALD HAR modeling literature.

  canonical_name             Meaning
  -------------------------  -----------------------------------------------
  feature_height             opening height
  feature_width              trench or channel width
  feature_depth              trench or channel depth
  pore_radius                pore radius
  feature_length             axial length
  aspect_ratio               depth / width
  equivalent_aspect_ratio    effective AR
  hydraulic_diameter         characteristic diffusion length
  surface_area               internal surface area
  cross_section_area         feature cross-section
  feature_volume             volume of feature
  active_surface_area        reactive surface area
  characteristic_length      length scale for Kn
  diffusion_length           transport distance
  perimeter                  boundary length

------------------------------------------------------------------------

# 1. Geometry Model -- Top-Level Schema

JSON_PATH: geometry_model

    geometry_model {
        feature_definition
        geometry_parameters
        derived_parameters
        geometry_evolution
        coordinate_system
        geometry_assumptions
        transport_interface
        reaction_interface
    }

------------------------------------------------------------------------

# 2. Feature Definition

JSON_PATH: geometry_model.feature_definition

Defines what type of structure is modeled.

    feature_definition {
        feature_type
        dimensionality
    }

### feature_type

  value
  -----------------
  trench
  hole
  LHAR_channel
  porous_particle
  planar_surface

### dimensionality

  value
  ------
  1D
  2D
  3D

------------------------------------------------------------------------

# 3. Geometry Parameters

JSON_PATH: geometry_model.geometry_parameters

This section stores the primary feature-scale geometry variables.

    geometry_parameters {
        feature_height
        feature_width
        feature_depth
        pore_radius
        feature_length
    }

Each variable follows the canonical variable structure:

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

### Example

    feature_height {
        canonical_name: feature_height
        paper_symbol: H
        physical_meaning: height of feature opening
        units: m
        definition: vertical dimension of trench or channel
        equation_context: geometry_parameters
    }

    feature_width {
        canonical_name: feature_width
        paper_symbol: W
    }

    pore_radius {
        canonical_name: pore_radius
        paper_symbol: r
    }

------------------------------------------------------------------------

# 4. Derived Parameters

JSON_PATH: geometry_model.derived_parameters

These are geometry-related quantities derived from the primary geometry parameters.

    derived_parameters {
        aspect_ratio
        equivalent_aspect_ratio
        hydraulic_diameter
        surface_area
        cross_section_area
        feature_volume
    }

### Example

    aspect_ratio {
        canonical_name: aspect_ratio
        paper_symbol: AR
        physical_meaning: ratio of depth to width
        definition: feature_depth / feature_width
    }

    hydraulic_diameter {
        canonical_name: hydraulic_diameter
        paper_symbol: h
    }

------------------------------------------------------------------------

# 5. Geometry Evolution

JSON_PATH: geometry_model.geometry_evolution

Defines whether geometry changes during deposition.

    geometry_evolution {
        evolving_geometry
        evolution_equation
    }

### evolving_geometry

  value
  ------
  true
  false

### Example

    evolving_geometry: false

or

    evolution_equation:
    dH/dt = -2 * growth_rate

or

    dR/dt = -G

------------------------------------------------------------------------

# 6. Coordinate System

JSON_PATH: geometry_model.coordinate_system

Defines the coordinate system used to describe geometry.

    coordinate_system {
        coordinate_type
        spatial_variable
    }

### coordinate_type

  value
  -----------
  cartesian
  cylindrical
  radial

### Example

    spatial_variable {
        canonical_name: spatial_coordinate
        paper_symbol: x
    }

------------------------------------------------------------------------

# 7. Geometry Assumptions

JSON_PATH: geometry_model.geometry_assumptions

Stores geometry-related assumptions.

    geometry_assumptions {
        constant_geometry
        symmetric_geometry
        uniform_cross_section
    }

### Example

    constant_geometry = true

------------------------------------------------------------------------

# 8. Transport Interface

JSON_PATH: geometry_model.transport_interface

Defines how geometry provides characteristic length scales to the transport model.

    transport_interface {
        characteristic_length
        diffusion_length
    }

### Example

    characteristic_length {
        canonical_name: characteristic_length
        paper_symbol: H
    }

This value may be used in transport expressions such as:

    Kn = λ / characteristic_length

------------------------------------------------------------------------

# 9. Reaction Interface

JSON_PATH: geometry_model.reaction_interface

Defines how geometry connects to the reaction model.

    reaction_interface {
        surface_area
        active_surface_area
    }

### Example

    surface_area {
        canonical_name: surface_area
        paper_symbol: A
    }

------------------------------------------------------------------------

# 10. Example Geometry Model

JSON_PATH: geometry_model

Example in the style of **Ylilammi et al. (2018)**

    geometry_model {

    feature_definition {
        feature_type: LHAR_channel
        dimensionality: 1D
    }

    geometry_parameters {

        feature_height {
            canonical_name: feature_height
            paper_symbol: H
        }

        feature_width {
            canonical_name: feature_width
            paper_symbol: W
        }

    }

    derived_parameters {

        aspect_ratio {
            canonical_name: aspect_ratio
            paper_symbol: AR
        }

    }

    geometry_evolution {
        evolving_geometry: false
    }

    coordinate_system {
        coordinate_type: cartesian

        spatial_variable {
            canonical_name: spatial_coordinate
            paper_symbol: x
        }
    }

    geometry_assumptions {
        constant_geometry: true
    }

    }

------------------------------------------------------------------------

# 11. Knowledge Graph Mapping

When converted to a knowledge graph:

    Paper
       └ HAS_GEOMETRY_MODEL
              ├ feature_definition
              ├ geometry_parameters
              ├ derived_parameters
              └ geometry_assumptions

Transport connection:

    geometry.characteristic_length
          ↓
    transport.knudsen_number

Reaction connection:

    geometry.surface_area
          ↓
    reaction.growth_rate

------------------------------------------------------------------------

# 12. Full ALD Model Integration

The complete ALD model structure becomes:

    ALD_model

     ├ transport_model
     │     └ diffusion_model
     │
     ├ reaction_model
     │     └ adsorption_model
     │
     └ geometry_model
           └ feature_definition

And all variables across all three schemas use the same normalization pattern:

    canonical_name
    paper_symbol
    definition
    units
    equation_context

------------------------------------------------------------------------

# 13. Core Fields (Most Important)

For reliable geometry-model extraction, the following fields are the most
critical:

    feature_definition
    geometry_parameters
    derived_parameters
    geometry_assumptions

These fields capture most geometry-model differences across ALD conformality literature.

------------------------------------------------------------------------

# End of Schema
