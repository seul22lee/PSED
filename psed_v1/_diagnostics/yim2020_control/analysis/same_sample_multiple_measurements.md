# Sample 11 — one sample, three characterisation modes

## Verified statements
> Fig. 5 "(a) SEM image of **sample 11** surface (top view) with an overlayer of
> corresponding Al-Ka X-ray count map in red. 1000 growth cycles were used on the LHAR
> channels with a design height of 500 nm ... (b) SEM-EDS line scans of elemental profiles
> for Al, Si, and O **in the same sample**."

> Experimental C: "Elemental X-ray mapping of the sample surface was performed first.
> Subsequently, line scans of elemental profiles were measured. The length of the line was
> 500 mm with measurement points at 1 mm intervals."

## Identity
* Sample 11: Al2O3, 300 C, 0.1-4.0-0.1-4.0, **1000 cycles**, H = 500 nm, layout v1b.
* Identity level: **SAME_PHYSICAL_SPECIMEN** - the paper says "the same sample", and the
  map and line scan are sequential acquisitions on that one specimen.
* Sample 11 is also the 1000-cycle member of **Series D**, so it additionally carries a
  reflectometry saturation profile in Fig. 9d-f.

Sample 11 therefore supports at least four measurements: SEM image, Al-Ka map, EDS line
scan (Al, Si, O), and reflectometry.

## Answer to the PSED question
No - these should not produce multiple *deposition* Experiments. One deposition act
produced sample 11; everything else characterises that one specimen. The paper states the
grouping explicitly, so it is recoverable rather than inferred.

## Observed PSED behaviour (read-only)
`Fig 5 panel b` yields **3 Experiments** - one per elemental profile (Al, Si, O) of a
single EDS line scan on a single specimen.
