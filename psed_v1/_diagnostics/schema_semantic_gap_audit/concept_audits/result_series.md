# ResultSeries

**Required**: data produced by a Measurement or a ModelRun.

**Current**: represented **twice** - `PlotSeries` (1044 KG nodes) from the resolve/KG layer
and `Curve` (1042) from canonical. They denote the same scientific object at different
pipeline stages; the counts differ only by the two point-less `NoFig` entities.

**Status**: DUPLICATED (severity MEDIUM). Also KEEP - the object itself is right, and
`PlotSeries` is correctly documented "A drawn curve. NEVER an Experiment".
