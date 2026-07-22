You are analyzing a scientific paper on **Atomic Layer Deposition (ALD)
conformality modeling**.

Your task is to determine whether each segment contains information
relevant to the **Geometry Model** of the ALD conformality model.

Segments may be sentences or equations.

Return JSON only in the following format:

{
  "results": [
    {
      "segment_id": "S00010",
      "geometry_relevant": true
    }
  ]
}

------------------------------------------------------------
ALD Conformality Model Structure
------------------------------------------------------------

ALD Conformality Model

    = Transport Model
    + Reaction Model
    + Geometry Model

This task focuses ONLY on the **Geometry Model**.

------------------------------------------------------------
Geometry Model Definition
------------------------------------------------------------

The geometry model describes the **structure and dimensions of the
features where ALD deposition occurs**.

Examples include trenches, holes, channels, and porous particles.

Geometry information defines the **spatial structure used by transport
and reaction models**.

------------------------------------------------------------
Relevant Geometry Concepts
------------------------------------------------------------

A segment is relevant to the **geometry_model** if it describes any of
the following.

------------------------------------------------------------
1. Feature Definition
------------------------------------------------------------

Statements describing the **type of structure being modeled**.

Examples

• trench  
• hole  
• LHAR channel  
• porous particle  
• planar surface  

Also include statements describing **model dimensionality**

• 1D model  
• 2D model  
• 3D model  

------------------------------------------------------------
2. Geometry Parameters
------------------------------------------------------------

Statements describing the **physical dimensions of the feature**.

Examples

• feature height  
• feature width  
• feature depth  
• pore radius  
• feature length  

Example sentences

"The trench width W is 100 nm."

"The feature depth is denoted by H."

"The pore radius r is used to compute Knudsen diffusion."

------------------------------------------------------------
3. Derived Geometry Parameters
------------------------------------------------------------

Statements describing geometry-derived quantities.

Examples

• aspect ratio (AR)  
• equivalent aspect ratio  
• hydraulic diameter  
• characteristic length  
• diffusion length  

Example sentences

"The aspect ratio AR = H / W."

"The hydraulic diameter is used as the diffusion length scale."

------------------------------------------------------------
4. Geometry Evolution
------------------------------------------------------------

Statements describing whether geometry changes during deposition.

Examples

• constant geometry assumption  
• evolving geometry during deposition  
• feature closure  
• shrinking radius  

Example sentences

"The geometry is assumed constant during the ALD cycle."

"The pore radius decreases during deposition."

------------------------------------------------------------
5. Coordinate System
------------------------------------------------------------

Statements defining the coordinate system used to describe geometry.

Examples

• Cartesian coordinates  
• cylindrical coordinates  
• radial coordinate  

Example sentences

"The spatial coordinate x represents the position along the channel."

"The model uses cylindrical symmetry."

------------------------------------------------------------
6. Geometry Assumptions
------------------------------------------------------------

Statements describing assumptions about geometry.

Examples

• constant geometry  
• symmetric geometry  
• uniform cross-section  

Example sentences

"The feature is assumed to have a uniform cross-section."

------------------------------------------------------------
7. Geometry Interfaces
------------------------------------------------------------

Statements linking geometry to other model components.

Examples

Geometry → Transport

• characteristic length  
• diffusion length  

Example

"Knudsen number is defined as Kn = λ / H."

Geometry → Reaction

• surface area  
• active surface area  

Example

"The internal surface area determines the total adsorption rate."

------------------------------------------------------------
Equation Segments
------------------------------------------------------------

If the segment is an equation, classify it based on whether it defines
a **geometric quantity or relation**.

Examples

Aspect ratio definition

AR = H / W

Surface area

A = 2πrL

These should be classified as geometry_model.

------------------------------------------------------------
Classification Rule
------------------------------------------------------------

Return TRUE if the segment contains **any geometry information**.

Return FALSE if the segment only discusses:

• diffusion physics  
• reaction kinetics  
• adsorption models  
• surface coverage equations  

These belong to other model components.

------------------------------------------------------------
Output Format

Return JSON only in the following format:

{
  "results": [
    {
      "segment_id": "S00015",
      "geometry_relevant": true
    },
    {
      "segment_id": "S00016",
      "geometry_relevant": false
    }
  ]
}