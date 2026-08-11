# Material

**Required**: material belongs to the case/result context. `2.067203jes` contains SiO2
deposition, an independently ALD-deposited Al2O3 capping layer, and SiO2/Al2O3 stacks.

**Ontology**: `Material` plus subclasses (`DopedFilm`, `TwoDMaterial`, `HybridMaterial`).
No distinct classes/roles for substrate, support, template, electrode or stack component.

**Resolver**: `material_scope_level` already records how a material was scoped
(`paper_single_material`, `figure_caption`, `series_legend`, `panel_caption_clause`,
`unresolved`) - a genuine and useful field. But `2.067203jes` resolves all 38 entities to
`SiO2`; Al2O3 gets no experiment, and Fig 11/12 stack measurements are labelled SiO2.

**Status**: KEEP_BUT_MOVE_LEVEL (material) + MISSING (material *role*: deposited vs
substrate vs support vs stack component). Severity HIGH.
