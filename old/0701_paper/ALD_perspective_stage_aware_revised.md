# AI for Atomic Layer Deposition: From Fragmented Process Knowledge to Stage-Aware Digital Twins

## Central Thesis

AI for ALD should not be framed as a universal recipe generator or a single reactor model.

We propose a stage-aware framework for AI-enabled ALD digital twins in which model-aware knowledge bases reduce structural uncertainty during design, analytic and surrogate models reduce parametric uncertainty during development, and data assimilation with feedback control manages state uncertainty under aleatoric noise during operation.

Such twins combine model-aware knowledge bases, analytic and surrogate models, LLM/agentic systems, parameter inference, in situ sensing, and closed-loop control. The core difficulty is not only data scarcity but fragmentation: ALD knowledge is scattered across materials, precursors, reactor types, thermal/plasma chemistries, geometries, and process conditions — and across figures, captions, tables, and text.

---

## 1. Introduction and Motivation

### 1.1 Atomic layer deposition as a heterogeneous process space

Atomic layer deposition is based on sequential, self-limiting surface
reactions. It enables atomic-scale thickness control, excellent
uniformity, and conformal coating of complex three-dimensional
structures.

These capabilities make ALD central to many fields:

| Application areas |
|---|
| Microelectronics; energy devices; catalysis; protective coatings; quantum materials; superconducting films; display technologies; sensors |

However, ALD is not defined by a single recipe variable. ALD outcomes
depend on a high-dimensional process space:

| Category | Examples |
|---|---|
| **Chemistry** | precursor, co-reactant, ligand family, plasma species |
| **Material system** | oxide, nitride, metal, sulfide, ternary, doped film |
| **Surface** | substrate, surface termination, nucleation behavior |
| **Reactor** | cross-flow, showerhead, batch, spatial, direct plasma, remote plasma |
| **Cycle design** | AB, ABC, ABCD, supercycle |
| **Conditions** | temperature, pressure, pulse time, purge time, flow, plasma power |
| **Geometry** | planar wafer, trench, via, porous media, particles |
| **Measurement** | ellipsometry, QCM, XPS, XRR, SEM/TEM, resistivity |
| **Target output** | GPC, conformality, composition, crystallinity, impurity, functional property |

Because these variables are strongly coupled, AI for ALD cannot be
reduced to simple recipe optimization.

---

### 1.2 The key bottleneck: fragmentation, not only data scarcity

The ALD community produces a large amount of useful knowledge, but this
knowledge is not organized in a form that digital twins can directly use.

ALD knowledge is distributed across:

| Sources |
|---|
| Papers; reviews; ALD process databases; figures; captions; methods sections; tables; supplementary information; reactor logs; in situ sensor streams |

Broad ALD primers and reviews are essential because they organize the
human understanding of ALD. They define the conceptual vocabulary of
the field: precursors, co-reactants, reactors, ALD cycles, saturation
curves, temperature windows, non-idealities, reproducibility, and
applications.

A digital twin requires a different representation. It must know not
only **what** ALD concepts exist, but also **how** they constrain:

| Digital-twin needs |
|---|
| model selection; parameter inference; uncertainty estimation; experiment planning; process transfer; real-time control |

Thus, the key bottleneck is not only that ALD data are limited. The
larger issue is that ALD knowledge is fragmented, heterogeneous, and
not yet machine-actionable.

---

### 1.3 Why model-aware knowledge bases are needed

FAIR data, ontologies, and standardized reporting are necessary, but not
sufficient.

ALD also needs **model-aware knowledge bases**: structured
representations that connect process metadata not only to measured
outcomes, but also to equations, assumptions, parameter priors,
uncertainty, and provenance.

| Human-readable review | Model-aware knowledge base |
|---|---|
| Explains ALD concepts | Encodes entities and relations |
| Summarizes precursors and reactors | Links chemistry to process regimes |
| Shows saturation curves | Uses curves for parameter inference |
| Discusses non-idealities | Maps non-idealities to model assumptions |
| Describes reproducibility | Stores transferability and uncertainty |
| Static literature synthesis | Dynamic knowledge-accumulation system |

The purpose of the knowledge base is not to replace reviews. Its purpose
is to operationalize them.

---

### 1.4 Current fragmentation in AI for ALD

Recent AI/ML studies in ALD show promise, but they remain fragmented.

| Area | Current capability | Missing link |
|---|---|---|
| **Modeling** | Mechanistic models and simulations explain ALD phenomena | Assumptions and validity are rarely machine-actionable |
| **Surrogates** | Fast prediction and optimization for specific regimes | Limited transferability and uncertainty handling |
| **LLMs** | Can answer ALD questions and extract text | Need grounding and provenance |
| **Agents** | Can interface with tools and propose actions | Need reliable process knowledge and safety logic |
| **Control** | Can regulate selected process variables | Needs calibrated models and state estimates |

What is missing is an architecture that connects:

| Missing architecture |
|---|
| fragmented knowledge → model selection → parameter inference → surrogate modeling → real-time control → post-run knowledge update |

---

## 2. Current AI/ML for ALD: Fragmented Capabilities

This section reviews current AI/ML efforts in ALD by capability rather
than by stage. This avoids forcing existing studies into design,
development, or control categories before proposing the integrated
framework.

---

### 2.1 Modeling and simulation for ALD

#### Scope

ALD modeling spans multiple scales:

| Scale | Examples |
|---|---|
| **Atomistic** | DFT, reaction energetics, precursor adsorption |
| **Surface** | ligand exchange, nucleation, surface coverage |
| **Feature** | reaction–diffusion, conformality, HAR transport |
| **Reactor** | CFD, depletion, flow, residence time |
| **Process** | cycle design, supercycles, composition control |
| **Property** | crystallinity, impurity, resistivity, superconducting properties |

Traditional ALD modeling relies on physics-based methods such as:

| Modeling tools |
|---|
| DFT; force fields; kinetic Monte Carlo; reaction–diffusion models; transport models; CFD; reduced-order models |

More recently, ML has been used to accelerate simulations through:

| ML-enabled modeling |
|---|
| ML interatomic potentials; Δ-ML; transfer learning; CFD surrogates; learned descriptors; foundation models for atomistic simulation |

#### Key message

Physics-based and computational models provide mechanistic
understanding. They can identify surface reactions, explain saturation
behavior, predict transport limitations, and guide precursor or process
design.

#### Gap

Most models are still:

| Limitations |
|---|
| system-specific; expensive to calibrate; difficult to transfer; disconnected from literature-scale process knowledge; not linked to machine-readable assumptions or validity regimes |

For AI-enabled ALD digital twins, models must become part of a reusable
model hierarchy.

---

### 2.2 Surrogate modeling, optimization, and control

#### Scope

Surrogate models and optimization algorithms have been applied to:

| Tasks |
|---|
| dose-time optimization; saturation-time prediction; HAR conformality prediction; PEALD exposure optimization; Bayesian optimization; sparse experiment planning; active learning; in situ metrology interpretation |

These methods are attractive because ALD experiments can be slow,
expensive, and highly process-specific.

#### Key message

Surrogate models can reduce the number of experiments needed to optimize
ALD processes. They are especially useful when partial measurements
contain enough information to infer hidden process quantities.

Examples include:

| Example surrogate roles |
|---|
| predicting saturation time from undersaturated profiles; classifying reaction-limited vs recombination-limited regimes; accelerating CFD or transport simulations; suggesting next experiments |

#### Gap

Current surrogate models are often tied to narrow domains:

| Common restrictions |
|---|
| one material; one reactor; one geometry; one process regime; one simulation model; one output metric |

They need:

| Needed capabilities |
|---|
| regime awareness; uncertainty quantification; model-selection logic; links to prior knowledge; links to experimental provenance; validation across reactors and geometries |

Surrogates should therefore be embedded in a broader digital-twin
architecture rather than treated as standalone predictors.

---

### 2.3 Knowledge, language models, and agents

#### Scope

LLMs and agentic systems are beginning to appear in ALD research.

Relevant directions include:

| Direction | Role |
|---|---|
| **LLM benchmarks** | Evaluate ALD knowledge and hallucination |
| **Literature extraction** | Convert papers into structured records |
| **Knowledge graphs** | Store entities, relations, and provenance |
| **RAG systems** | Ground LLM outputs in retrieved evidence |
| **Agents** | Orchestrate tools, recipes, models, and experiments |
| **Reactor interfaces** | Translate high-level instructions into tool actions |

#### Key message

LLMs and agents are useful for reasoning, workflow orchestration, human
interaction, and literature-scale knowledge access.

They can help with:

| LLM/agent capabilities |
|---|
| extracting process information; filling schemas; retrieving relevant papers; suggesting experiments; explaining model assumptions; querying databases; launching simulations; interacting with reactor software |

#### Gap

LLMs are not reliable standalone sources of ALD truth.

They require:

| Required grounding |
|---|
| curated knowledge bases; provenance tracking; structured schemas; model-aware retrieval; uncertainty checks; validated models; safety-aware tool interfaces |

The role of LLMs and agents should be to orchestrate knowledge and
models, not to replace mechanistic models or real-time controllers.

---

### 2.4 Summary of the current landscape

Existing studies provide important pieces of the AI-for-ALD ecosystem:

| Component | What it provides |
|---|---|
| **Mechanistic models** | physical explanation and extrapolation |
| **Surrogate models** | fast prediction and inverse mapping |
| **Optimization algorithms** | experiment reduction |
| **LLMs** | language interface and extraction |
| **Knowledge graphs** | grounding and memory |
| **Agents** | tool orchestration |
| **Controllers** | real-time decisions |

However, these pieces are not yet integrated into a coherent framework.

This motivates a stage-aware ALD digital twin.

---

## 3. Proposed Framework: Stage-Aware ALD Digital Twins

### 3.1 Overview

We propose organizing AI-enabled ALD digital twins around three stages:

| Stage | Purpose | Dominant uncertainty |
|---|---|---|
| **Design** | Select chemistry, process route, and model family | Structural / epistemic |
| **Develop** | Calibrate model parameters and validate assumptions | Parametric |
| **Control** | Estimate state and act under noise and constraints | State / aleatoric |

Each stage has a different question, data source, and toolset.

---

### 3.2 Figure 1: Stage-aware ALD digital twin

```text
ALD lifecycle

┌─────────────────────┬─────────────────────┬─────────────────────┐
│ DESIGN              │ DEVELOP             │ CONTROL             │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ What chemistry,     │ What parameters     │ What should the     │
│ regime, and model   │ and validity?       │ reactor do now?     │
│ apply?              │                     │                     │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ Structural /        │ Parametric          │ State / aleatoric   │
│ epistemic           │ uncertainty         │ uncertainty         │
│ uncertainty         │                     │                     │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ Literature, ALD     │ Sparse experiments, │ In situ metrology,  │
│ databases, figures, │ digitized plots,    │ reactor logs,       │
│ captions, tables    │ simulations         │ sensor streams      │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ KG, ontology, RAG,  │ Analytic models,    │ Soft sensors,       │
│ LLM extraction,     │ Bayesian fitting,   │ data assimilation,  │
│ agents              │ surrogate models    │ feedback / MPC      │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ Candidate process,  │ Calibrated model,   │ Next-cycle action,  │
│ model family,       │ coefficient priors, │ constraints,        │
│ initial priors      │ uncertainty         │ safety decisions    │
└─────────────────────┴─────────────────────┴─────────────────────┘

Post-run data, fitted parameters, failures, and uncertainty
feed back into the knowledge base.
```

#### Message of Figure 1

| Stage | What the twin reduces |
|---|---|
| **Design** | structural uncertainty through knowledge |
| **Develop** | parameter uncertainty through calibration |
| **Control** | state uncertainty through sensing and feedback |

Every completed run should update the knowledge base.

---

### 3.3 Design: reducing structural and epistemic uncertainty

#### Question

What material, chemistry, reactor condition, process regime, and model
family should be used?

#### Dominant uncertainty

At the design stage, the system may not know:

| Unknowns |
|---|
| feasible precursor/co-reactant combinations; thermal vs plasma route; applicable reactor type; planar vs HAR regime; nucleation vs steady growth; transport vs recombination limitation; decomposition or CVD-like risk; relevant literature records; appropriate model family |

#### Main tools

| Tools |
|---|
| model-aware knowledge bases; LLM/RAG systems; knowledge graphs; ontologies; literature mining; agentic planning; ALD process databases |

#### Output

| Design outputs |
|---|
| candidate process routes; applicable model family; initial parameter priors; expected failure modes; first experiment plan |

#### Key point

This is not yet a mature research category. It is a missing capability
that can be enabled by model-aware knowledge bases.

---

### 3.4 Develop: reducing parametric uncertainty

#### Question

Given a selected model family, what are the process-specific parameters
and validity limits?

#### Dominant uncertainty

The model form may be known, but its coefficients may be unknown:

| Unknown parameters |
|---|
| GPC; saturation dose; sticking probability; recombination probability; nucleation rate; reaction coefficient; diffusion parameter; adsorption constant; incubation behavior; temperature-window limits |

#### Main tools

| Tools |
|---|
| analytic model fitting; Bayesian inference; Gaussian process regression; neural surrogates; active learning; plot-to-experiment extraction; digitized literature data; sparse calibration experiments; simulation-generated datasets |

#### Output

| Development outputs |
|---|
| calibrated model; parameter estimates; uncertainty bounds; model-validity assessment; next-experiment recommendation |

---

### 3.5 Control: managing state and aleatoric uncertainty

#### Question

What should the reactor do now?

#### Dominant uncertainty

The system must act despite:

| Uncertainties |
|---|
| unmeasured internal states; noisy in situ measurements; reactor drift; precursor-delivery variation; plasma instability; disturbances; actuator constraints |

#### Main tools

| Tools |
|---|
| reduced-order models; soft sensors; data assimilation; feedback control; model predictive control; stochastic constraints; real-time in situ metrology; agentic supervision |

#### Output

| Control outputs |
|---|
| next-cycle pulse time; pressure or dose update; purge adjustment; plasma exposure; stop/go decision; safety-aware process action |

#### Key point

Real-time control does not always require a large AI model. It requires
the right low-latency model, the right state estimate, and the right
constraint formulation.

---

## 4. Enabling Layer I: Model-Aware Knowledge Bases

### 4.1 Why a knowledge base is needed

FAIR data and ontologies can standardize names, units, and metadata.
However, digital twins need more than standardized metadata.

They need a knowledge layer that connects:

| Knowledge-base links |
|---|
| process metadata; measured outcomes; governing equations; model assumptions; parameter priors; validity ranges; uncertainty; provenance |

A knowledge base should answer:

| Questions |
|---|
| Which model applies? Which assumptions are valid? Which parameters are known? Which parameters transfer? Which data should be used for calibration? Which experiment should be done next? |

---

### 4.2 From literature to experiment records

Much of the useful ALD data is hidden in unstructured or semi-structured
forms:

| Literature sources |
|---|
| body text; methods sections; captions; tables; plots; supplementary information; figure panels |

A model-aware extraction pipeline should recover:

| Extracted record fields |
|---|
| material; precursor; co-reactant; substrate; reactor; geometry; process conditions; measurement method; measured outcome; digitized curve; uncertainty; provenance |

The key point is not only to digitize curves, but to connect each curve
to its experimental context.

---

### 4.3 From experiment records to model priors

Recovered experiment records should be converted into model-ready
quantities:

| Model priors |
|---|
| saturation-time priors; GPC priors; sticking estimates; recombination estimates; nucleation parameters; transport coefficients; temperature-window limits; failure-mode evidence |

These priors can initialize a digital twin before new experiments are
performed.

---

### 4.4 From knowledge base to digital twin initialization

Given a target requirement, the knowledge base should provide:

| Target requirement | Knowledge-base output |
|---|---|
| Target material | candidate precursor/co-reactant routes |
| Target geometry | applicable transport or conformality model |
| Thermal budget | feasible temperature window |
| Reactor type | transferable recipes and expected deviations |
| Required property | relevant process–structure–property data |
| Unknown coefficient | prior distribution and calibration experiment |

This transforms literature knowledge into a design-stage digital twin.

---

### 4.5 From completed runs back to the knowledge base

Each ALD run should write back:

| Post-run knowledge |
|---|
| process conditions; reactor configuration; in situ data; measured outcomes; fitted parameters; model errors; failed conditions; uncertainty estimates; transferability notes; updated validity ranges |

This write-back mechanism turns the digital twin into a
knowledge-accumulation system.

---

## 5. Enabling Layer II: Regime-Aware Model Hierarchies

### 5.1 Why a model hierarchy is needed

There is no universal ALD model.

Different ALD regimes require different model families:

| Regimes |
|---|
| planar thermal ALD; nucleation-limited growth; high-aspect-ratio thermal ALD; PEALD with recombination; multicomponent ALD; reactor-scale ALD; property-driven ALD |

The purpose of the knowledge base is not only to store data, but also
to route each ALD problem to the appropriate model hierarchy.

---

### 5.2 Analytic models

Analytic models provide:

| Strengths |
|---|
| mechanistic interpretability; transferable structure; physically meaningful parameters; extrapolation beyond observed data; constraints for control |

Examples include:

| Analytic model examples |
|---|
| self-limited saturation kinetics; nucleation and coverage models; reaction–diffusion transport; conformality models; supercycle composition models; reduced-order reactor models |

Analytic models are especially useful when the dominant physics is
known and the main uncertainty is parametric.

---

### 5.3 Surrogate and data-driven models

Surrogate models provide:

| Strengths |
|---|
| fast prediction; inverse design; uncertainty-aware optimization; diagnostic classification; model acceleration; real-time feasibility |

Examples include:

| Surrogate examples |
|---|
| neural surrogates for saturation time; classifiers for recombination-limited regimes; Gaussian process models for Bayesian optimization; CFD surrogates; property predictors |

Surrogates are especially useful when full simulations or experiments
are expensive, but representative data or physics-generated datasets
are available.

---

### 5.4 Hybrid models

Hybrid models combine:

| Hybrid ingredients |
|---|
| analytic structure; data-driven correction; uncertainty quantification; sparse experimental calibration |

They are useful when:

| Use cases |
|---|
| physics is partially known; data are sparse; reactor-specific effects matter; process regimes shift; model assumptions fail |

Hybrid models can serve as the bridge between physical interpretability
and data-driven adaptability.

---

### 5.5 Regime-aware model table

| ALD regime | Dominant physics | Analytic model role | Surrogate / data-driven role | Digital-twin role |
|---|---|---|---|---|
| Planar thermal ALD | Self-limited adsorption | Saturation kinetics, GPC model | Dose optimization, anomaly detection | Recipe initialization |
| Nucleation-limited ALD | Substrate-dependent growth | Nucleation / coverage model | Fit early-cycle behavior | Surface-state estimation |
| HAR thermal ALD | Reaction–diffusion transport | Feature-scale transport model | Saturation-time prediction | Conformality prediction |
| PEALD HAR | Radical transport and recombination | Plasma–surface model | Recombination classifier, exposure predictor | Diagnostic twin |
| Multicomponent ALD | Supercycles and composition coupling | Cycle / supercycle balance | Composition optimization | Material design |
| Reactor-scale ALD | Depletion and nonuniformity | CFD / multiscale model | Reduced-order CFD surrogate | Scale-up and transfer |
| Functional ALD | Process–structure–property relation | Physical constraints | Property prediction | Application-aware twin |

---

## 6. Roles of LLMs, Agents, KGs, and Controllers

### 6.1 LLMs as extraction and reasoning interfaces

LLMs can help with:

| LLM roles |
|---|
| extracting literature information; filling schemas; summarizing process knowledge; reasoning over process routes; explaining model assumptions; interacting with users |

However, LLMs require grounding and provenance. They should not be
treated as reliable standalone sources of ALD truth.

---

### 6.2 Knowledge graphs as grounding and memory

Knowledge graphs provide:

| KG roles |
|---|
| provenance tracking; entity resolution; links between experiments and models; retrieval of prior parameters; model-validity evidence; long-term memory across ALD runs |

KGs are the memory layer of the ALD digital twin.

---

### 6.3 Agents as orchestration layers

Agents can:

| Agent roles |
|---|
| query knowledge bases; select candidate models; launch simulations; propose experiments; monitor uncertainty; check reactor compatibility; escalate uncertain cases to humans |

Agents are most useful when they coordinate tools, models, and human
decision-making.

---

### 6.4 Controllers as low-latency decision layers

Real-time ALD control should rely on:

| Controller roles |
|---|
| physically constrained reduced-order models; soft sensors; feedback algorithms; uncertainty-aware constraints; safety logic |

Controllers should make low-latency, safety-critical process decisions.

---

### 6.5 Division of labor

| Component | Primary role |
|---|---|
| **LLMs** | extraction, explanation, reasoning interface |
| **KGs** | grounding, provenance, memory |
| **Agents** | orchestration and workflow management |
| **Analytic models** | physical structure and interpretability |
| **Surrogate models** | fast prediction and inverse mapping |
| **Controllers** | real-time state estimation and safe action |

LLMs and agents should orchestrate knowledge, models, and workflows.
Knowledge graphs should ground and accumulate process knowledge.
Control models should make low-latency, safety-critical decisions.

---

## 7. Outlook: From Single-Reactor Twins to Accumulating ALD Intelligence

### 7.1 The final goal

The goal is not to build one universal ALD model or a one-off twin of a
single reactor.

The goal is an accumulating ALD intelligence system.

---

### 7.2 What accumulates?

A mature ALD digital twin should accumulate:

| Accumulated knowledge |
|---|
| process recipes; successful conditions; failed conditions; fitted parameters; model errors; uncertainty estimates; reactor-specific corrections; geometry-specific deviations; transferability evidence; updated model-validity ranges |

This knowledge should improve future design, development, and control.

---

### 7.3 Closing loop

Each experiment should:

| Feedback role |
|---|
| update the knowledge base; refine parameter priors; improve model selection; reduce future calibration effort; identify failed assumptions; guide the next experiment |

A digital twin is therefore not only a model of the current reactor.
It is a mechanism for learning across experiments, reactors, materials,
and geometries.

---

### 7.4 Final perspective

The goal is not to build one universal ALD model.

The goal is to build an **accumulating ALD intelligence system** that
learns:

| What the system learns |
|---|
| which models apply; how parameters transfer; when assumptions fail; which experiments reduce uncertainty; how completed runs improve future design, development, and control |
