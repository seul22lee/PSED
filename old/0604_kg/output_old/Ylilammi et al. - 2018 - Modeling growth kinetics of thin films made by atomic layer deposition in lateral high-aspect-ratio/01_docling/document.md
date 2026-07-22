<!-- image -->

<!-- image -->

RESEARCH ARTICLE |  MAY 22 2018

## Modeling growth kinetics of thin films made by atomic layer deposition in lateral high-aspect-ratio structures 

Markku Ylilammi; Oili M. E. Ylivaara ; Riikka L. Puurunen iD iD

<!-- image -->

## Articles You May Be Interested In

Microscopic silicon-based lateral high-aspect-ratio structures for thin film conformality analysis

J. Vac. Sci. Technol. A (December 2014)

Atomic layer deposition of zinc oxide films on lateral high-aspect-ratio test structures using diethylzinc and water as precursors

J. Vac. Sci. Technol. A (March 2026)

Conformality in atomic layer deposition: Current status overview of analysis and modelling

Appl. Phys. Rev. (April 2019)

<!-- image -->

<!-- image -->

<!-- image -->

<!-- image -->

<!-- image -->

<!-- image -->

## Modeling growth kinetics of thin films made by atomic layer deposition in lateral high-aspect-ratio structures

Markku Ylilammi, 1,a) Oili M. E. Ylivaara, 1 and Riikka L. Puurunen 1,2

1 VTT Technical Research Centre of Finland, P.O. Box 1000, FI-02044 VTT, Finland

2 Aalto University School of Chemical Engineering, P.O. Box 16100, FI-00076 Aalto, Finland

(Received 8 March 2018; accepted 5 May 2018; published online 22 May 2018)

The conformality of thin films grown by atomic layer deposition (ALD) is studied using all-silicon test structures with long narrow lateral channels. A diffusion model, developed in this work, is used for studying the propagation of ALD growth in narrow channels. The diffusion model takes into account the gas transportation at low pressures, the dynamic Langmuir adsorption model for the film growth and the effect of channel narrowing due to film growth. The film growth is calculated by solving the diffusion equation with surface reactions. An efficient analytic approximate solution of the diffusion equation is developed for fitting the model to the measured thickness profile. The fitting gives the equilibrium constant of adsorption and the sticking coefficient. This model and Gordon's plug flow model are compared. The simulations predict the experimental measurement results quite well for Al2O3 and TiO2 ALD processes. Published by AIP Publishing. https://doi.org/10.1063/1.5028178

## NOMENCLATURE

- a Aspect ratio
- b Number of metal atoms in a molecule
- c Lumped sticking coefficient
- C Penetration depth parameter in the Gordon model (1/s)
- D Apparent longitudinal diffusion coefficient (m 2 /s)
- d A Diameter of molecule A (m)
- D A Gas-phase diffusion coefficient of molecules A (m 2 /s)
- D eff Effective diffusion coefficient (m 2 /s)
- D Kn Knudsen diffusion coefficient (m 2 /s)
- F Gas flow of the reactant (mol/s)
- f ads Adsorption rate (m /C0 2 s /C0 1 )
- g Net adsorption rate (m /C0 2 s /C0 1 )
- f des Desorption rate (m /C0 2 s /C0 1 )
- gpc Film growth per cycle (m)
- gpc sat Saturation growth in cycle (m)
- h Hydraulic diameter of the channel (m)
- H Height of the channel (m)
- K Adsorption equilibrium constant (1/Pa)
- L Length of the channel (m)
- M Molar mass of the deposited film (kg/mol)
- M A Molar mass of reactant A (kg/mol)
- N Total number of adsorbed molecules; number of ALD cycles
- n A Amount of reactant A (mol)
- N0 Avogadro constant (1/mol)
- p A Partial pressure of reactant A (Pa)
- p A0 Input partial pressure of reactant A (Pa)
- P d Desorption probability in unit time (1/s)
- q Adsorption density of molecules in saturation (1/m 2 )
- Q Collision rate at unit pressure (m /C0 2 s /C0 1 Pa /C0 1 )
- R Gas constant (J K /C0 1 mol /C0 1 )

a) Electronic mail: markku.ylilammi@vtt.fi

- s Film thickness (m)
- t Time (s)
- T Temperature (K)
- t p Length of the reactant pulse (s)
- v Velocity of gas front (m/s)
- v A Average speed of molecules A (m/s)
- W Width of the channel (m)
- x Distance from the beginning of the channel (m)
- x p Half-thickness penetration depth (m)
- x s Distance where the linear part of the reactant pressure is zero (m)
- x t Length of the linear part of the pressure distribution (m)
- z A Collision rate of molecule A (1/s)
- D s Error in thickness measurement (m)
- g Viscosity of gas (Pa s)
- h Surface coverage
- h eq Equilibrium surface coverage in the Langmuir model
- q Density of the condensed phase (kg/m 3 )
- s Time constant of adsorption

## I. INTRODUCTION

The downscaling of future semiconductor devices with increasing three-dimensionality-e.g., through-silicon-vias, FinFETS, 3D-NAND flash memories-sets new requirements for the aspect ratios which thin film processes have to conformably reach. Atomic layer deposition (ALD), based on the use of repeated, self-terminating reactions of typically at least two compatible reactants on a solid substrate (Puurunen, 2005 and George, 2010), is a technique that can often meet the conformality requirements. Conformal films made by ALD are also needed in other fields, with intrinsic three-dimensionality requirements, such as microelectromechanical systems (MEMS), energy applications, and highsurface-area catalysts. Despite its importance, experimental

data on conformality has been infrequently reported in scientific articles on ALD, likely due to the absence of available and easy-to-use analysis structures and methods. Notable exceptions are Dendooven (2010), Rose and Bartha (2009), Schwille (2017), and Yanguas-Gil (2017).

This work continues the earlier work (Gao, 2015), where microscopic lateral high-aspect-ratio structure (LHAR) prototypes were designed and fabricated. The LHAR structures consist of a long, narrow lateral gap of typically 500 nm in height (analogous to a vertical trench but rotated 90 /C14 ) in a polysilicon membrane, supported by pillars. The first LHAR prototypes have been used for conformality analysis of the ALD Al2O3-, TiO2and Ir-based thin films (Gao, 2015; Mattinen, 2016; and Puurunen and Gao, 2016). This work uses LHAR (PillarHall V R ) prototypes with a new all-silicon design made by a fabrication process resembling that previously reported (Gao, 2015). The length of the fabricated channels varied from 1 l m to 5 mm, so that for a typical gap height of 500 nm, the gap length vs. height gives the aspect ratio in the range from 2:1 to 10 000:1. It turned out that the penetration depth does not depend on the length of the channel when it is long enough. The structure of the LHAR test device is schematically illustrated in Fig. 1.

The goal of this work is to develop a model to calculate the thickness profile of ALD growth in high-aspect-ratio trenches. Using this model, the measured ALD film thickness profiles can be used to extract kinetic growth information. The derived model and its analytical simplification are compared with the Gordon model (Gordon, 2003). The frequently used trimethylaluminum-water (TMA) process for Al2O3 and the chloride process for TiO2 have been used to verify the model.

## II. GAS DIFFUSION IN NARROW CHANNELS

The hard-sphere model of molecules (Levine, 1978) can satisfactorily explain the diffusion properties of bulk gas mixtures. If the partial pressures of molecules A and B are p A and p B, their molar masses M A and M B and diameters d A and d B, respectively, the collision rate of A molecules in a gas mixture A þ B at temperature T is given by

FIG. 1. Schematic cross-section of the LHAR test device (not in scale). The gas front propagates in the x-direction. The penetration depth of the ALD film growth is x p . The width of the channel in the z-direction is W . The length in the x-direction is L .

<!-- image -->

where

<!-- formula-not-decoded -->

is the hydraulic diameter of a rectangular channel of height H and width W .

The diffusion resistance is the sum of bulk diffusion in gas and wall collisions. The combined diffusion constant in a narrow channel at low pressures follows the Bosanquet relation (Poodt, 2017)

<!-- formula-not-decoded -->

Calculation of the diffusion constant D A requires a value for the diameter d A of the molecule. For common gases, this can be calculated, e.g., from the gas phase viscosity g (Levine, 1978)

s

ffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffi ffi

r

ffiffiffiffiffiffiffiffiffiffiffiffi ffi

<!-- formula-not-decoded -->

The viscosity of water vapor at 100 /C14 C is g ¼ 12.55 l Pa s (Weast, 1977), which gives a molecular diameter d A ¼ 418pm. For nitrogen at 11 /C14 C, g ¼ 17.07 l Pa s and d B ¼ 374pm. For most reactants in ALD, the gas phase viscosity is not measured. The molecular diameter can be calculated from a molecular dynamics simulation, but because the Knudsen diffusion is the major limiting factor in the mass transport in narrow channels, a rough estimate of the molecular diameter is sufficient. We obtain it from the density q of the liquid or solid phase of the material

/C20

/C18

/C19

/C21

<!-- formula-not-decoded -->

where the latter term is the rate of A-A collisions. R ¼ k B N 0 is the gas constant where k B is the Boltzmann constant and N 0 the Avogadro constant. The average speed of A molecules is

/C18

/C19

<!-- formula-not-decoded -->

The gas-phase diffusion constant of A molecules is

<!-- formula-not-decoded -->

The diffusion model of mass transport in narrow channels can be extended to the transition flow regime if the effect of walls is incorporated into the model. The diffusion constant in a molecular (Knudsen) flow is (Poodt, 2017)

/C18

/C19

<!-- formula-not-decoded -->

/C18

/C19

<!-- formula-not-decoded -->

Trimethylaluminum (TMA, Al(CH3)3) exists at low temperatures in a dimeric form, but above 215 /C14 C, more than 96% is in the monomeric form (Almenningen, 1971). Therefore, the diffusion constant of the monomer is used. The molecular diameters of metal precursors used here are d TMA ¼ 591 pm and d TiCl4 ¼ 703.9 pm.

For the modeling of the mass transport in ALD, we need to quantify the amount of material that chemisorbs on the surface in one reaction cycle. This depends on the adsorption density q of the reactant molecules. If the experimental saturation growth per cycle is gpc sat (layer thickness per cycle at saturation reactant exposure) is available, we can calculate the adsorption density q from the film mass density q

<!-- formula-not-decoded -->

Here, b film is the number of metal atoms in the formula unit of the deposited film and bA the number of metal atoms in one reactant molecule. M is the molar mass of a formula unit of the film. For TMA and Al2O3, these are b film ¼ 2 and b A ¼ 1, and for TiCl4 and TiO2, b film ¼ 1 and b A ¼ 1.

Because the weight and the size of water molecules are smaller than those of the metal reactants they diffuse much more rapidly than the metal compounds and the growthlimiting factor is assumed to be the diffusion of metal precursors.

## III. MODELING THE FILM GROWTH

The coordinate system used in the high-aspect-ratio lateral channel is defined in Fig. 1. The gas enters from the left and propagates along the x-axis by diffusion. In the ydirection (height), the time constant for concentration equilibration by diffusion is H 2 / D eff /C25 10 ns, where the channel height H ¼ 1 l m and the effective diffusion coefficient D eff is typically about 1 cm 2 /s. Therefore, we may assume well that there are no concentration gradients in the y-direction in the millisecond time scale of the ALD process. In the z-direction, the channel is very wide ( W /C29 H ), and therefore the concentration is assumed constant in that direction.

We can now simplify the problem by using the fact that the gas concentration is constant in the y and z directions. The one-dimensional diffusion equation for partial pressure p A is

<!-- formula-not-decoded -->

where the gas adsorption rate to the walls is g (1/m 2 s). This equation can be solved numerically, but when the number of reactant pulses in an ALD process can be several thousands the computational task is impractically heavy.

Although the surface reactions may be very complicated, we use the Langmuir adsorption model for the chemisorption process. With sticking probability c the rate of adsorption (1/m 2 s) (Levine, 1978) is

<!-- formula-not-decoded -->

and the rate of desorption is

<!-- formula-not-decoded -->

where h is the surface coverage, q the saturation adsorption density, and P d the desorption probability in unit time. Here, c must be understood as a lumped sticking coefficient which combines the effects of all sequential and parallel surface processes.

In equilibrium, these are equal and we can define the adsorption equilibrium constant K using the collision rate at unit pressure Q (Levine, 1978)

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

The net adsorption rate g (1/m 2 s) of gas A is

<!-- formula-not-decoded -->

and the rate of change in the surface coverage h is

<!-- formula-not-decoded -->

During the reactant pulse, the net adsorption rate is always positive so that the question whether the adsorption is reversible or irreversible is not important for this model. Both cases are covered by the Langmuir model; in the latter case, P d ¼ 0. Experiments show that better fit, especially in the case of TiO2 is obtained if P d &gt; 0. Although the Langmuir model is used in this analysis, the actual reaction mechanism may be much more complicated.

## IV. APPROXIMATE SOLUTION TO THE DIFFUSION EQUATION

We need a simple approximate model for the reactant gas partial pressure p A as a function of location x and time t , so that we do not need to find a numerical solution of the diffusion equation in fitting the model to the measured results. In the beginning of the channel, the surfaces are immediately saturated and no gas is used in adsorption g ( x ¼ 0 ) /C25 0. The gas flow is in the steady state ( @ p A / @ t /C25 0) and the diffusion equation is simplified to

<!-- formula-not-decoded -->

Its solution is

/C18

/C19

<!-- formula-not-decoded -->

where the boundary conditions p A(0, t ) ¼ p A0 and p A( x s , t ) /C25 0 have been used. x t is the limit beyond which the approximation g /C25 0 is not valid and x s describes how far the reactant front has propagated at time t . It is the location where the linear part of the pressure distribution would go to zero.

Because the gas propagates by diffusion, a reasonable approximation is that the growth distance is proportional to the diffusion length (Yanguas-Gil, 2017) or ffiffiffiffi ffi

<!-- formula-not-decoded -->

Here, D is a parameter (apparent longitudinal diffusion constant) describing the velocity of the gas front. In the region on linear pressure distribution ( x &lt; x t) and when the surfaces are saturated, the diffusion gas flow (molecules/s)

<!-- formula-not-decoded -->

The total number of molecules adsorbed onto the surfaces at distance x is

/C18

/C19

<!-- formula-not-decoded -->

When we neglect the small amount n A /C25 p A0 WHx p /(2 RT ) of yet unused reactant in the gas phase, this must be equal to the integrated gas flow at time t

ð

<!-- formula-not-decoded -->

From this, we can solve the apparent longitudinal diffusion constant which is needed to calculate x s in (19)

<!-- formula-not-decoded -->

In the constant-slope region x &lt; x t, the pressure is approximated by the linear model (18). Beyond point x t (in the tail region), we approximate the partial pressure by an exponential tail and we use the following model to describe the reactant pressure

/C18

/C19

<!-- formula-not-decoded -->

The point x t is chosen, so that the pressure is continuous. In the tail region ( x &gt; x t ),

/C18

/C19

<!-- formula-not-decoded -->

When these are inserted in the diffusion equation, Eq. (10), we get

/C18

/C19

<!-- formula-not-decoded -->

In the tail region, the surface coverage is low. When h /C25 0, we have

<!-- formula-not-decoded -->

Now, we choose x t , so that this equation is true at location x ¼ x t , but x t must not be negative

s

ffiffiffiffiffiffiffiffiffiffiffiffiffiffiffi ffiffiffiffiffiffiffiffiffiffiffiffiffiffiffi

s

<!-- formula-not-decoded -->

In Fig. 2, this approximate model is compared with the numerical solution of the diffusion equation and the fit looks quite good.

Next, we need a solution for the surface coverage h at point x at time t . If the gas pressure changes slowly compared to the rate of adsorption, we may assume that the adsorption is in equilibrium and the surface coverage at location x would be

<!-- formula-not-decoded -->

At constant p A, the surface coverage h approaches exponentially the equilibrium coverage and the time constant of this process when h eq ¼ 0.5 is

<!-- formula-not-decoded -->

The equilibrium model is sufficiently accurate if s is much smaller than the pulse length t p. However, in real ALD processes, the adsorption can be far from equilibrium, and thus this assumption is not useful.

The surface coverage h (x,t) in the Langmuir model can always be found by solving

/C18

/C19

<!-- formula-not-decoded -->

The analytical solution is (integrations from 0 to t )

Ð

/C0

/C1

ð

Ð

/C0

/C1

<!-- formula-not-decoded -->

Because typically we need to solve Eq. (31) more than 10 000 times in fitting the result of one growth experiment, it is the major time consuming step in the analysis. Numerical integration of Eq. (32) is too slow. In this work, Eq. (31) is solved by the 4th order Runge-Kutta method (Arfken, 1970). It is self-initiated and easily stable. Often, 100 time points (time step, e.g., 1 ms) are enough for accurate results. However, sometimes this does not guarantee convergence and then we need to increase the number of time points.

In Figs. 2 and 3, this approximate model is compared with the numerical solution of the differential equations. Both models give practically identical results.

## V. THICKNESS PROFILE AND THE PENETRATION DEPTH

In an ALD growth experiment, N cycles of reactant pulses consisting of the first reactant (e.g., TMA) and the second reactant (H2O) are fed into the channel, and the resulting thickness profile s ( x ) is measured. When the penetration depth x p is determined by measuring the film thickness s , the error in it is

<!-- formula-not-decoded -->

where D s is the error in film thickness and ds/dx is the slope of the film thickness vs. location at the point of measurement. The maximum value of the slope is at the point of half film thickness and determining x p at this point gives the best

FIG. 2. Comparison of the development of reactant pressure distributions in time. Lines indicate the approximate model and circles the fully numerical solution of the growth equations. Parameter values used: H ¼ 0.5 l m , W ¼ 0.1 mm, p A0 ¼ 100Pa, M A ¼ 0.0749 kg/mol, d A ¼ 591pm, M B ¼ 0.028 kg/ mol, d B ¼ 374pm, p B ¼ 300Pa, q ¼ 5 /C2 10 18 m /C0 2 , T ¼ 500K, K ¼ 100Pa /C0 1 , c ¼ 0.01, and gpc sat ¼ 106pm. The locations of points x t and x s of the 0.1 s pulse are marked.

<!-- image -->

FIG. 3. Development of the surface coverage with time. Circles represent the fully numerical solution of differential equations and lines the result of the approximate model. Parameter values used: H ¼ 0.5 l m , W ¼ 0.1 mm, p A0 ¼ 100Pa, M A ¼ 0.0749 kg/mol, d A ¼ 591pm, M B ¼ 0.028 kg/mol, d B ¼ 374 pm, p B ¼ 300Pa, q ¼ 5 /C2 10 18 m /C0 2 , T ¼ 500 K, K ¼ 100Pa /C0 1 , c ¼ 0.01, and gpc sat ¼ 106pm.

<!-- image -->

accuracy. Therefore, we define the half-thickness penetration x p of the film growth, so that the film thickness is 50% of thickness s (0) at the beginning of the channel, or by solving x p in the equation

<!-- formula-not-decoded -->

The film grows on both the top and bottom surfaces of the channel. If the thickness growth of the film in one complete growth cycle is gpc , the free height of the channel after N cycles is

<!-- formula-not-decoded -->

Because the film growth thickness depends on location x , the channel height also varies with location. This complicates the analysis because the diffusion constant now depends on location. This problem is circumvented by assuming that the channel height is constant in the whole channel and it is updated to the value in the beginning of the channel after each pulse. Thus, in the model, the channel in the tail region is narrower than in reality, so the model predicts slightly too steep thinning of the film. However, this is a good assumption when the film is thin compared to the gap height H and when the film does not grow much beyond the point x p .

In the last step, we add the contributions h i in the surface coverage of all the N cycles and compute the final thickness distribution s ( x )

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

The resulting film thickness distributions with different channel height values are shown in Fig. 4.

FIG. 4. Film thickness profiles after 1000 cycles calculated by the approximate model when the original channel heights are H ¼ 2, 1, 0.5, or 0.2 l m. Reactant pulse length t p ¼ 0.1 s. In the last case, the channel entrance is completely plugged up. Parameter values used: H ¼ 0.5 l m , W ¼ 0.1 mm, p A0 ¼ 100Pa, M A ¼ 0.0749 kg/mol, d A ¼ 591pm, M B ¼ 0.028 kg/mol, d B ¼ 374pm, p B ¼ 300Pa, q ¼ 5 /C2 10 18 m /C0 2 , T ¼ 500K, K ¼ 100Pa /C0 1 , c ¼ 0.01, and gpc sat ¼ 106pm.

<!-- image -->

## VI. COMPARISON WITH THE GORDON MODEL

In the Gordon model for ALD conformality, it is assumed that the gas enters the rectangular channel (height H /C28 width W ) as a front with a constant concentration without any gas diffusion in the propagation direction (x-axis). This is called the Gordon model (Gordon, 2003). Gas is adsorbed onto the two walls. When q is the saturation areal density ( m /C0 2 ) of the adsorbed molecules, the number of adsorbed molecules at distance dx in a channel with width W is

<!-- formula-not-decoded -->

On the other hand, the number of molecules is equal to the flow F (1/s) of incoming gas in time dt

<!-- formula-not-decoded -->

When the surface is saturated, there is no absorption and this location x propagates with velocity v

<!-- formula-not-decoded -->

The flow through a channel of length x and area WH in a molecular flow is approximated by Gordon (2003)

<!-- formula-not-decoded -->

where p A0 is the partial pressure of molecules A in the beginning of the channel. Now, the location x of the saturation border propagates with velocity

<!-- formula-not-decoded -->

This can be separated and integrated as

/C18

/C19

<!-- formula-not-decoded -->

In the Gordon model, the aspect ratio a ¼ x/H is independent of height H of the channel. If we denote

<!-- formula-not-decoded -->

we get the penetration depth at pulse length t p, when W /C29 H

r

ffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffi

<!-- formula-not-decoded -->

This is plotted in Fig. 5 for one ALD cycle and compared with the present diffusion models. Although the Gordon model in this case gives a good description of the film penetration depth, it does not give the thickness profile and it does not enable modeling of the film growth kinetics.

## VII. EXPERIMENTAL

To test the growth model, ALD Al2O3 and TiO2 films were grown on LHAR structures. The ALD reactor was a Picosun R-150 with four reactant lines. Al2O3 was grown with the same process as in Gao (2015) from trimethylaluminum (TMA) and water (H2O) at 300 /C14 C and TiO2 from titanium tetrachloride (TiCl4) and H2O at 110 /C14 C. Nitrogen was

FIG. 5. Comparison of the penetration depth given by different models in one reactant pulse. Circles represent the fully numerical solution, the solid line the analytical approximate solution and the dashed line the Gordon model. Parameter values used: H ¼ 0.5 l m , W ¼ 0.1 mm, p A0 ¼ 100Pa, M A ¼ 0.0749 kg/mol, d A ¼ 591pm, M B ¼ 0.028 kg/mol, d B ¼ 374pm, p B ¼ 300 Pa, q ¼ 5 /C2 10 18 m /C0 2 , T ¼ 500K, K ¼ 100Pa /C0 1 , c ¼ 0.01, t p ¼ 0.1 s, and gpc sat ¼ 106 pm. In the Gordon model, only the Knudsen diffusion is considered which is slightly faster than the diffusion given by the effective diffusion coefficient in Eq. (6).

<!-- image -->

FIG. 6. The measured (circles) and calculated (line) thickness profiles of a 500cycle deposition process of Al2O3 from Al(CH3)3 and H2O in PillarHall V R prototype 3 with a nominal channel gap height of 0.5 l m. The length L of the channel was 1 mm which gives a structural aspect ratio of 2000.

<!-- image -->

used both as a purging gas and as a carrier gas for the reactants. The LHAR chips (PillarHall V R 3rd generation prototypes by VTT) were thermalized in the ALD chamber at the deposition temperature for 10 min before starting the growth process. For Al2O3 growth, the AlMe3 pulse and purge times were 0.1 and 4.0 s, respectively, followed by 0.1 and 4.0 s H2O pulse and purge steps. This reaction sequence was repeated for 500 cycles, leading approximately to 50 nm film. Nitrogen flow rates were 150 sccm through each reactant line. In the TiO2 growth, the reactant pulse and purge times were also 0.1 and 4.0 s, respectively. In the TiO2 deposition, the number of pulse sequences was 1000 resulting in approximately 50 nm film thickness. Chamber pressures for both Al2O3 and TiO2 during the runs were appr. 300 Pa.

The LHAR structures were inspected optically after the ALD before and after removing the membrane. The film growth depth was determined by spectroscopic reflectometry measurements using SCI FilmTek 2000M equipment, and the samples were measured using a 100-point line scan. The measurement started at the beginning of the lateral cavity proceeding in 2 l m steps towards the cavity end; thus, the total scan length was 200 l m. In the measurement, a 50 /C2 objective lens was used, giving roughly 5 l m spot size. The precision of the film thickness measurement is limited by the roughness of the channel surface and we estimate it to be about 3 nm.

## VIII. RESULTS

The measured and calculated thickness profiles of Al2O3 and TiO2 films are given in Figs. 6 and 7. The extracted

FIG. 7. The measured (circles) and calculated (line) thickness profiles of a 1000cycle deposition process of TiO2 from TiCl4 and H2O. The nominal channel gap height is 0.5 l m. The length L of the channel was 1 mm which gives a structural aspect ratio of 2000.

<!-- image -->

growth parameters are in Table I. The saturation growth in one cycle gpc sat is the equilibrium thickness of layer growth at saturation or high reactant exposure or

<!-- formula-not-decoded -->

where gpc is the observed growth per cycle at reactant pressure p A and K is the equilibrium constant in the Langmuir model. The thickness error is the rms difference between the measured and calculated thicknesses and describes how well the modeling describes the measured result.

The ALD thickness profiles of Al2O3 and TiO2 films are quite different. Aluminum oxide film exhibits constant thickness from the beginning to close to the penetration depth. Titanium oxide thickness is nowhere constant but the film thickness gradually decreases when the gas enters deeper into the channel. In the Langmuir model, this results in quite different values for the sticking coefficient c and the equilibrium constant K . The root cause probably is that the deposition of TiO2 produces very reactive HCl (Knapas and Ritala, 2013), while the Al2O3 deposition produces relatively passive CH4 (Puurunen, 2005). If we knew the reaction mechanism, it could be used to replace the Langmuir adsorption equation, Eq. (31), and the present fitting procedure could be then used to find out the model parameters.

## IX. CONCLUSIONS

The model presented here describes quite well the thickness distribution of ALD growth in narrow channels. This

TABLE I. Parameters extracted from the measured film thickness profiles. The measured and calculated thickness profiles are in Figs. 6 and 7. Thickness error is the rms value of the difference between the measured and fitted thickness values.

| Material   |   Cycles |   H (nm) |   p A0 (Pa) |       c |   K (Pa /C0 1 ) |   gpc sat (pm) |   rms thickness error (nm) |
|------------|----------|----------|-------------|---------|-----------------|----------------|----------------------------|
| Al 2 O 3   |      500 |      500 |       147   | 0.00572 |         219     |          105.6 |                      0.974 |
| TiO 2      |     1000 |      500 |        25.7 | 0.1     |           0.252 |           54.4 |                      1.525 |

model can be used to design and optimize a deposition process for a new device. By fitting the model to the measured thickness distribution, one obtains parameters of the growth reaction model used. Here, only the simple Langmuir surface reaction model is applied, but it can be replaced by any model by changing Eq. (31). More elaborate models require more numerous parameters and their determination requires a more extensive set of measured data.

## ACKNOWLEDGMENTS

This work received funding from the Academy of Finland through the Finnish Centre of Excellence in Atomic Layer Deposition and from Tekes (since 2018 Business Finland) through the PillarHall TUTL Project. The samples were fabricated at the Micronova Clean Room Facilities of VTT, Espoo.

- Almenningen, A., Halvorsen, S., and Haaland, A., 'A gas phase electron diffraction investigation of the molecular structures of trimethylaluminium monomer and dimer,' Acta Chem. Scand. 25 , 1937-1945 (1971).
- Arfken, G., Mathematical Methods for Physicists (Academic Press, London, 1970).
- CRC Handbook of Chemistry and Physics 58th ed., edited by R. C. Weast (CRC Press, 1977).
- Dendooven, J., Deduytsche, D., Musschoot, J., Vanmeirhaeghe, R. L., and Detavernier, C., 'Conformality of Al2O3 and AlN deposited by plasmaenhanced atomic layer deposition,' J. Electrochem. Soc 157 (4), G111-G116 (2010).
- Gao, F., Arpiainen, S., and Puurunen, R. L., 'Microscopic silicon-based lateral high-aspect-ratio structures for thin film conformality analysis,' J. Vac. Sci. Technol. A 33 , 010601 (2015).
- George, S. M., 'Atomic layer deposition: An overview,' Chem. Rev. 110 , 111-113 (2010).
- Gordon, R. G., 'A kinetic model for step coverage by atomic layer deposition in narrow holes and trenches,' Chem. Vap. Deposition 9 , 73-78 (2003).
- Knapas, K. and Ritala, M., 'In situ studies on reaction mechanisms in atomic layer deposition,' Crit. Rev. Solid State Mat. Sci. 38 , 167-202 (2013).
- Levine, I. R., Physical Chemistry (McGraw-Hill, 1978).
- Mattinen, M., H € am € al € ainen, J., Gao, F., Jalkanen, P., Mizohata, K., R € ais € anen, J., Puurunen, R. L., Ritala, M., and Leskel € a, M., 'Nucleation and conformality of iridium and iridium oxide thin films grown by atomic layer deposition,' Langmuir 32 , 10559-10569 (2016).
- Poodt, P., Mameli, A., Schulpen, J., Kessels, W. M. M., and Roozeboom, F., 'Effect of reactor pressure on the conformal coating inside porous substrates by atomic layer deposition,' J. Vac. Sci. Technol. A 35 (2), 021502 (2017).
- Puurunen, R. L., 'Surface chemistry of atomic layer deposition: A case study for the trimethylaluminum/water process,' J. Appl. Phys. 97 , 121301 (2005).
- Puurunen, R. L. and Gao, F., 'Influence of ALD temperature on thin film conformality: Investigation with microscopic lateral high-aspect-ratio structures,' in 2016 14th International Baltic Conference on Atomic Layer Deposition (BALD) , St. Petersburg (IEEE, 2016), pp. 20-24.
- Rose, M. and Bartha, J. W., 'Method to determine the sticking coefficient of precursor molecules in atomic layer deposition,' Appl. Surf. Sci. 255 , 6620-6623 (2009).
- Schwille, M. C., Sch € ossler, T., Barth, J., Knaut, M., Sch € on, F., H € ochst, A., Oettel, M., and Bartha, J. W., 'Experimental and simulation approach for process optimization of atomic layer deposited thin films in high aspect ratio 3D structures,' J. Vac. Sci. Technol. A 35 , 01B118 (2017).
- Yanguas-Gil, A., Growth and Transport in Nanostructured Materials; Reactive Transport in PVD, CVD, and ALD (Springer, 2017).