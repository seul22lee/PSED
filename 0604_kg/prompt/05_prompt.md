# Paper Schema Reference

## materials

Extract material names that appear as deposited films, substrates, reactants, precursors, radicals, or growth surfaces.

Format:

{
  "name":"",
  "role":"film|substrate|precursor|reactant|radical|surface|unknown",
  "normalized_formula":"",
  "mentioned_as":[]
}

Examples:

- "Al2O3" → {"name":"Al2O3","role":"film","normalized_formula":"Al2O3","mentioned_as":["Al2O3"]}
- "DEZ" → {"name":"diethylzinc","role":"precursor","normalized_formula":"","mentioned_as":["DEZ","diethylzinc"]}
- "O atoms" → {"name":"oxygen radical","role":"radical","normalized_formula":"O","mentioned_as":["O atoms","oxygen radicals"]}

---

## processes

Extract ALD-related process types.

Format:

{
  "name":"",
  "type":"thermal_ALD|plasma_ALD|ALD|other",
  "mentioned_as":[]
}

Examples:

- "atomic layer deposition" → {"name":"atomic layer deposition","type":"ALD","mentioned_as":["ALD","atomic layer deposition"]}
- "plasma-assisted ALD" → {"name":"plasma-assisted atomic layer deposition","type":"plasma_ALD","mentioned_as":["plasma-assisted ALD","plasma ALD"]}

---

## geometry_types

Extract structure or feature classes where deposition, diffusion, penetration, or conformality is studied.

Only extract geometry types explicitly mentioned.

Do not infer categories not stated in the text.

Format:

{
  "name":"",
  "category":"lhar|trench|hole|porous|monolith|planar|high_aspect_ratio|unknown",
  "mentioned_as":[]
}

Examples:

- "lateral high-aspect-ratio structures" → {"name":"lateral high-aspect-ratio structure","category":"lhar","mentioned_as":["lateral high-aspect-ratio structures"]}
- "nanoporous alumina monolith" → {"name":"nanoporous monolith","category":"monolith","mentioned_as":["nanoporous alumina monolith"]}
- "high-AR structures" → {"name":"high-aspect-ratio structure","category":"high_aspect_ratio","mentioned_as":["high-AR structures"]}
- "narrow channels" → {"name":"narrow channel","category":"unknown","mentioned_as":["narrow channels"]}

---

## variables

Extract every scientific quantity, parameter, property, metric, coefficient, observable, predicted quantity, fitted quantity, physical mechanism, or governing phenomenon explicitly mentioned.

Do not reduce to only important variables.

Extract all scientifically meaningful entities that participate in models, methods, assumptions, or relationships.

Exclude generic narrative phrases.

Examples to exclude:

- study
- paper
- approach
- work
- analysis
- investigation

Variables may include:

- measurable quantities
- fitted parameters
- predicted quantities
- physical properties
- transport mechanisms
- reaction mechanisms
- governing phenomena

Examples:

- sticking coefficient
- equilibrium constant
- recombination probability
- effective diffusion coefficient
- film penetration depth
- aspect ratio
- plasma exposure time
- surface recombination
- Knudsen diffusion
- channel narrowing

Format:

{
  "name":"",
  "symbol":"",
  "role":"condition|measured_output|fitted_parameter|predicted_quantity|model_parameter|geometry_parameter|material_property|process_metric|mechanism|phenomenon|unknown",
  "unit":"",
  "mentioned_as":[]
}

Examples:

- "sticking coefficient" → {"name":"sticking coefficient","symbol":"","role":"fitted_parameter","unit":"","mentioned_as":["sticking coefficient"]}
- "equilibrium constant of adsorption" → {"name":"adsorption equilibrium constant","symbol":"K","role":"fitted_parameter","unit":"","mentioned_as":["equilibrium constant of adsorption"]}
- "film penetration depth" → {"name":"film penetration depth","symbol":"","role":"measured_output","unit":"","mentioned_as":["film penetration depth"]}
- "aspect ratio" → {"name":"aspect ratio","symbol":"AR","role":"geometry_parameter","unit":"","mentioned_as":["aspect ratio","AR"]}
- "minimum exposure time" → {"name":"minimum exposure time","symbol":"τ","role":"predicted_quantity","unit":"time","mentioned_as":["minimum exposure time"]}
- "surface recombination" → {"name":"surface recombination","symbol":"","role":"mechanism","unit":"","mentioned_as":["surface recombination"]}
- "Knudsen diffusion" → {"name":"Knudsen diffusion","symbol":"","role":"mechanism","unit":"","mentioned_as":["Knudsen diffusion"]}

---

## models

Extract named or described scientific models.

A model must define a mathematical, analytical, empirical, or computational representation.

Do not classify assumptions as models.

Format:

{
  "name":"",
  "model_type":"transport|reaction|geometry|coupled|empirical|analytical|unknown",
  "used_for":"",
  "mentioned_as":[]
}

Examples:

- "diffusion model" → {"name":"diffusion model","model_type":"transport","used_for":"studying propagation of ALD growth in narrow channels","mentioned_as":["diffusion model"]}
- "dynamic Langmuir adsorption model" → {"name":"dynamic Langmuir adsorption model","model_type":"reaction","used_for":"film growth","mentioned_as":["dynamic Langmuir adsorption model"]}
- "Shrinking Core Model" → {"name":"Shrinking Core Model","model_type":"coupled","used_for":"predicting minimum exposure time","mentioned_as":["SCM","shrinking core model"]}
- "Gordon's plug flow model" → {"name":"Gordon plug flow model","model_type":"transport","used_for":"comparison","mentioned_as":["Gordon's plug flow model"]}

Not models:

- Knudsen diffusion
- diffusion-limited growth
- Langmuir adsorption assumption
- irreversible adsorption

---

## methods

Extract procedures used to obtain, infer, estimate, fit, predict, quantify, or transform scientific information.

A method must transform information.

Input → Method → Output

A valid method consumes information and produces new information.

Format:

{
  "name":"",
  "method_type":"fitting|prediction|extraction|comparison|measurement|analysis|unknown",
  "input_variables":[],
  "output_variables":[],
  "mentioned_as":[]
}

Examples:

- "fitting measured thickness profile" → {"name":"thickness-profile fitting","method_type":"fitting","input_variables":["thickness profile"],"output_variables":["adsorption equilibrium constant","sticking coefficient"],"mentioned_as":["fitting the model to the measured thickness profile"]}
- "film penetration method" → {"name":"film-penetration-based recombination extraction","method_type":"extraction","input_variables":["film penetration depth"],"output_variables":["recombination probability"],"mentioned_as":["film penetration gives direct information on recombination probability"]}

Not methods:

- diffusion model
- Langmuir adsorption model
- Shrinking Core Model

---

## assumptions

Extract explicitly stated assumptions, limiting regimes, simplifications, or dominant mechanisms.

Format:

{
  "name":"",
  "assumption_type":"transport_regime|reaction_model|geometry_simplification|limiting_mechanism|other",
  "mentioned_as":[]
}

Examples:

- "limited by Knudsen diffusion" → {"name":"Knudsen diffusion limitation","assumption_type":"transport_regime","mentioned_as":["limited by Knudsen diffusion"]}
- "simple Langmuir surface reaction model" → {"name":"Langmuir surface reaction assumption","assumption_type":"reaction_model","mentioned_as":["simple Langmuir surface reaction model"]}
- "surface recombination limited" → {"name":"surface recombination limitation","assumption_type":"limiting_mechanism","mentioned_as":["limited by surface recombination"]}

---

## relationships

Extract explicit scientific relationships stated in the text.

A relationship must connect scientific entities.

Valid entities include:

- variables
- materials
- geometry types
- models
- methods

Extract only relationships explicitly stated.

Do not infer relationships from scientific background knowledge.

Do not extract metadata relationships.

Bad examples:

- diffusion model → used_for → ALD growth
- paper → studies → conformality
- authors → compare → models

Good examples:

- surface recombination → limits → film penetration depth
- material → affects → recombination probability
- exposure time → increases → penetration depth
- fitting method → extracts → sticking coefficient
- Shrinking Core Model → predicts → minimum exposure time

Format:

{
  "source":"",
  "relation":"limits|increases|decreases|depends_on|predicts|extracts|fits|compares_with|affects|determines|enables|is_limited_by|controls|governs|describes|estimates|quantifies|correlates_with|unknown",
  "target":"",
  "condition":"",
  "evidence_text":""
}

Examples:

- "surface recombination limits film penetration depth" → {"source":"surface recombination","relation":"limits","target":"film penetration depth","condition":"plasma-assisted ALD","evidence_text":"film penetration depth is generally limited by surface recombination"}

- "exponential increase in plasma exposure time is required to linearly increase the film penetration" → {"source":"plasma exposure time","relation":"increases","target":"film penetration depth","condition":"","evidence_text":"exponential increase in plasma exposure time is required to linearly increase the film penetration"}

- "film penetration gives direct quantitative information on recombination probability" → {"source":"film penetration depth","relation":"determines","target":"recombination probability","condition":"","evidence_text":"film penetration gives direct quantitative information on recombination probability"}

- "fitting the model to the measured thickness distribution gives the equilibrium constant of adsorption and the sticking coefficient" → {"source":"model fitting","relation":"extracts","target":"sticking coefficient","condition":"using thickness distribution","evidence_text":"fitting the model to the measured thickness profile"}

---

# Output JSON Template

```json
{
  "materials":[],
  "processes":[],
  "geometry_types":[],
  "variables":[],
  "models":[],
  "methods":[],
  "assumptions":[],
  "relationships":[]
}
```