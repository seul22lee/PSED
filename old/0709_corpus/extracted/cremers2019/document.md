<!-- image -->

<!-- image -->

## Conformality in atomic layer deposition: Current status overview of analysis and modelling F

Cite as: Appl. Phys. Rev. 6 , 021302 (2019); https://doi.org/10.1063/1.5060967 Submitted: 21 September 2018 . Accepted: 31 January 2019 . Published Online: 04 April 2019

<!-- image -->

Véronique Cremers, Riikka L. Puurunen

## COLLECTIONS

<!-- image -->

- This paper was selected as Featured

<!-- image -->

openoccess

View Online

Export Citation

CrossMark

<!-- image -->

<!-- image -->

<!-- image -->

<!-- image -->

<!-- image -->

, and Jolien Dendooven

<!-- image -->

## Conformality in atomic layer deposition: Current status overview of analysis and modelling

Cite as: Appl. Phys. Rev. 6

, 021302 (2019); doi: 10.1063/1.5060967

Submitted: 21 September 2018 . Accepted: 31 January 2019 .

Published Online: 4 April 2019

<!-- image -->

V /C19 eronique Cremers, 1 Riikka L. Puurunen, 2,3

and Jolien Dendooven 1,a)

## AFFILIATIONS

1 Department of Solid State Sciences, Ghent University, Krijgslaan 281/S1, B-9000 Ghent, Belgium

2 Department of Chemical and Metallurgical Engineering, Aalto University School of Chemical Engineering, P.O. Box 16100, FI-00076 AALTO, Finland

3 VTT Technical Research Centre of Finland, P.O. Box 1000, FI-02044 VTT, Finland

a) Electronic mail: Jolien.Dendooven@UGent.be

## ABSTRACT

Atomic layer deposition (ALD) relies on alternated, self-limiting reactions between gaseous reactants and an exposed solid surface to deposit highly conformal coatings with a thickness controlled at the submonolayer level. These advantages have rendered ALD a mainstream technique in microelectronics and have triggered growing interest in ALD for a variety of nanotechnology applications, including energy technologies. Often, the choice for ALD is related to the need for a conformal coating on a 3D nanostructured surface, making the conformality of ALD processes a key factor in actual applications. In this work, we aim to review the current status of knowledge about the conformality of ALD processes. We describe the basic concepts related to the conformality of ALD, including an overview of relevant gas transport regimes, definitions of exposure and sticking probability, and a distinction between different ALD growth types observed in high aspect ratio structures. In addition, aiming for a more standardized and direct comparison of reported results concerning the conformality of ALD processes, we propose a new concept, Equivalent Aspect Ratio (EAR), to describe 3D substrates and introduce standard ways to express thin film conformality. Other than the conventional aspect ratio, the EAR provides a measure for the ease of coatability by referring to a cylindrical hole as the reference structure. The different types of high aspect ratio structures and characterization approaches that have been used for quantifying the conformality of ALD processes are reviewed. The published experimental data on the conformality of thermal, plasma-enhanced, and ozone-based ALD processes are tabulated and discussed. Besides discussing the experimental results of conformality of ALD, we will also give an overview of the reported models for simulating the conformality of ALD. The different classes of models are discussed with special attention for the key assumptions typically used in the different modelling approaches. The influence of certain assumptions on simulated deposition thickness profiles is illustrated and discussed with the aim of shedding light on how deposition thickness profiles can provide insights into factors governing the surface chemistry of ALD processes. We hope that this review can serve as a starting point and reference work for new and expert researchers interested in the conformality of ALD and, at the same time, will trigger new research to further improve our understanding of this famous characteristic of ALD processes.

V C 2019 Author(s). All article content, except where otherwise noted, is licensed under a Creative Commons Attribution (CC BY) license (http:// creativecommons.org/licenses/by/4.0/) . https://doi.org/10.1063/1.5060967

| TABLE OF CONTENTS                                                                                                    |    | F. ALD growth types in high aspect ratio structures                                      |   6 |
|----------------------------------------------------------------------------------------------------------------------|----|------------------------------------------------------------------------------------------|-----|
| I. INTRODUCTION . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .                                    |  2 | G. Aspect ratio and equivalent aspect ratio. . . . . . . .                               |   6 |
| II. CONCEPTS . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .                             |  3 | H. Ways to express the level of conformality . . . . . . III. STRUCTURES TO QUANTIFY THE |   7 |
| A. ALD characteristics: Uniformity and conformality. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . |  3 | CONFORMALITY OF ALD . . . . . . . . . . . . . . . . . . . . . .                          |   8 |
| B. Gas transport: Molecular to viscous flow . . . . . . . .                                                          |  3 | A. Vertical structures. . . . . . . . . . . . . . . . . . . . . . . . . . .              |   8 |
| C. ALD reactor types. . . . . . . . . . . . . . . . . . . . . . . . . . . .                                          |  4 | B. Lateral structures. . . . . . . . . . . . . . . . . . . . . . . . . . . .             |  11 |
| D. Exposure in ALD . . . . . . . . . . . . . . . . . . . . . . . . . . . .                                           |  5 | C. Porous materials . . . . . . . . . . . . . . . . . . . . . . . . . . . .              |  12 |
| E. Reaction mechanisms and sticking probability. . . .                                                               |  5 | IV. EXPERIMENTS ON CONFORMALITY OF ALD. . . .                                            |  13 |

<!-- image -->

<!-- image -->

<!-- image -->

<!-- image -->

<!-- image -->

<!-- image -->

| A. Thermal ALD processes. . . . . . . . . . . . . . . . . . . . . .                                                                                                    |   13 |
|------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------|
| B. Ozone-based ALD processes . . . . . . . . . . . . . . . . . .                                                                                                       |   16 |
| C. PE-ALD processes. . . . . . . . . . . . . . . . . . . . . . . . . . .                                                                                               |   19 |
| V. SIMULATION MODELS ON CONFORMALITY OF ALD. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .                                     |   20 |
| A. Overview . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .                                                                                        |   20 |
| 1. Analytical models . . . . . . . . . . . . . . . . . . . . . . . .                                                                                                   |   20 |
| 2. Computational models. . . . . . . . . . . . . . . . . . . .                                                                                                         |   20 |
| B. Multiscale approach . . . . . . . . . . . . . . . . . . . . . . . . .                                                                                               |   26 |
| 1. Reactor and feature scale. . . . . . . . . . . . . . . . . .                                                                                                        |   26 |
| 2. Feature scale and molecular scale . . . . . . . . . .                                                                                                               |   26 |
| C. Key assumptions used in modelling . . . . . . . . . . .                                                                                                             |   27 |
| 1. Flow regime: Molecular or viscous flow . . . . .                                                                                                                    |   27 |
| 2. Diffusion coefficient in continuum and analytical models . . . . . . . . . . . . . . . . . . . . . . . .                                                            |   27 |
| 3. Simulation space in Monte Carlo models . . .                                                                                                                        |   27 |
| 4. Reaction mechanism . . . . . . . . . . . . . . . . . . . . .                                                                                                        |   28 |
| 5. Re-emission mechanism . . . . . . . . . . . . . . . . . .                                                                                                           |   28 |
| 6. Simulating one or multiple ALD cycles . . . . .                                                                                                                     |   28 |
| D. Model output. . . . . . . . . . . . . . . . . . . . . . . .                                                                                                         |   29 |
| . . . . . . . 1. Exposure and EAR. . . . . . . . . . . . . . . . . . . . . . .                                                                                         |   29 |
| 2. Thickness profile and sticking coefficient. . . .                                                                                                                   |   29 |
| 3. Other output . . . . . . . . . . . . . . . . . . . . . . . . . . . .                                                                                                |   30 |
| VI. INSIGHTS INTO ALD THICKNESS PROFILES BY MONTE CARLO SIMULATIONS . . . . . . . . . . . . . . . . .                                                                  |   30 |
| A. Monte Carlo simulation program . . . . . . . . . . . . .                                                                                                            |   31 |
| B. Theoretical ALD cases .                                                                                                                                             |   31 |
| . . . . . . . . . . . . . . . . . . . . . . 1. Model of Gordon et al. : Sticking probability of unity. . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . |   31 |
| 2. Irreversible Langmuirian adsorption: Influence of sticking probability on the thickness profile . . . . . . . . . . . . . . . . . . . . . . .                       |   31 |
| . . 3. Determining the initial sticking coefficient through comparing simulation with experiment. . . . . . . . . . . . . . . . . . . . . . . . . . . . . .            |   31 |
| 4. Influence of the initial sticking coefficient on the required exposure . . . . . . . . . . . . . . . . . . . .                                                      |   31 |
| 5. Influence of the bottom of the feature . . . . . .                                                                                                                  |   32 |
| C. Contribution of secondary CVD-type reactions .                                                                                                                      |   33 |
| D. Other reactions potentially influencing the thickness profile . . . . . . . . . . . . . . . . . . . . . . . . . . . .                                               |   34 |
| VII. SUMMARY AND OUTLOOK. . . . . . . . . . . . . . . . . . . .                                                                                                        |   35 |

## I. INTRODUCTION

Atomic layer deposition (ALD) is a gas phase thin film deposition technique which has been discovered and developed independently in the 1960s in the Soviet Union and in 1974 in Finland. 1-3 This technique is characterized by exposing the substrate to an alternating sequence of vapor phase reactants. Due to the selfsaturating nature of the surface reactions, the film thickness can be controlled at the atomic scale. 4-8 A typical ALD process consists of several ALD cycles with each ALD cycle comprising four characteristic steps, which are shown in Fig. 1 for the prototypic 4-6 trimethylaluminum (TMA)/H2O process:

1. Step 1: The first reactant A (TMA) reacts in a self-terminating way with the available functional groups on the OH-terminated surface.

FIG. 1. Schematic representation of one ALD cycle of the TMA/H 2 O process.

<!-- image -->

2. Step 2: The excess of reactant A (TMA) and the gaseous by-products (CH4) are purged or pumped away.
3. Step 3: The second reactant B (H2O) reacts in a self-terminating way with the adsorbed species ( A ) on the surface.
4. Step 4: The excess of reactant B (H2O) and the gaseous by-products (CH4) are purged or pumped away.

In this review, we will call steps 1 and 3 the first and second reactions of the ALD cycle, respectively. After each ALD cycle, a certain amount of material (coating) is deposited on the surface, which is called the growth per cycle (GPC). The GPC can be expressed in various units such as those of the thickness (e.g., nm), mass gain (e.g., g), and an increase in the areal density (e.g., atoms/nm 2 ).

As opposed to 'line-of-sight' deposition techniques such as physical vapor deposition (PVD), 9,10 ALD has the capability to grow uniform and conformal films in 3D structures with complex shapes and with a large depth to width ratio or in more general terms a large aspect ratio. 11-15 For deposition techniques that are flux controlled [such as chemical vapor deposition (CVD) 16 and PVD], film growth depends on the local gas flux. Because of the inherent kinetics of gas transport within narrow trenches, the flux of reactant molecules can be several orders of magnitude larger near the entrance as compared to the bottom of the structure. Therefore, the entrance region to narrow trenches tends to get clogged at the beginning of the deposition, making it difficult for reactant molecules to diffuse deeper into the structure. Various approaches exist to improve the conformality of CVD processes, e.g., inhibiting the growth, 17 using pulsed CVD, 18,19 and using surfactants to catalyze the growth. 20,21 Also during ALD deposition, the entrance region will receive a higher flux of reactant molecules. However, the self-saturating nature of the surface reactions during ALD results in surface-controlled deposition. Higher flux near the entrance region will result in faster coverage at this location, but once the surface is saturated, no further reaction can take place at this site, avoiding clogging of the trench entrance and allowing the reactant molecules to diffuse deeper into the trench and coat the entire structure.

The miniaturization of semiconductor devices leads to the introduction of more complex 3D geometries with an increasing aspect ratio, often termed high aspect ratio (HAR) structures . Due to the selflimited surface reactions, ALD is one of the most suitable deposition techniques to deposit thin coatings with an excellent control of the layer thickness onto such structures. ALD is, for example, used for the fabrication of trench capacitors in dynamic random-access memory (DRAM), 22,23 in FinFETs, 24,25 and 3D NAND structures. 26,27 Also, outside the field of semiconductor applications, 28 ALDis being considered to deposit films onto 3D substrates, e.g., for surface functionalization and protection of microelectromechanical systems (MEMSs), 29,30 and coatings for fuel cells, 31 solar cells, 32-34 batteries, 35-39 catalytic surfaces, 40-46 membranes, 47,48 textiles, 49 and pharmaceuticals. 50

In this review article, we explore the status of current understanding of the conformality of ALD processes, providing an overview of published experimental and theoretical studies focusing on this topic. First, conformality-related concepts of ALD processes will be introduced in Sec. II. In Sec. III, we discuss methods and dedicated test structures that have been used to quantify the conformality of ALD processes. An overview of experimental reports on the conformality of thermal, plasma-enhanced, and ozone-based ALD processes is presented in Sec. IV. In Sec. V, different models are discussed that have been used to simulate ALD in narrow structures. These models can be used to optimize process parameters towards improved conformality. Fitting of model parameters to experimental data can also provide insights into the ALD surface reactions, e.g., in sticking probabilities and the impact of non-ideal side-reactions during ALD. In Sec. VI, we simulate the influence of different ALD parameters on the conformality with a Monte Carlo model 51 and discuss how one can obtain relevant information on the growth mechanism from the analysis of such thickness profiles.

## II. CONCEPTS

## A. ALD characteristics: Uniformity and conformality

Due to the self-limited nature of the chemisorption and subsequent surface reactions, it is possible to grow with ALD uniform and conformal films in structures with a large depth to width ratio. Uniform films have an equal thickness and composition (and other properties) at each position along a planar substrate, e.g., along a 300 mm wafer. Conformal films have the same thickness (and properties) also inside 3D features ('around-the-corner'). Figure 2 shows a schematic representation of the coating of a 3D structured surface with a non-conformal line-of-sight technique (a) and with the typical conformality of an ALD coating (b). In the absence of the 3D feature, both films could be considered uniform.

## B. Gas transport: Molecular to viscous flow

During reactant transport, the reactant molecules penetrate into narrow structures in a certain flow regime. To distinguish the different flow regimes, Knudsen 52 introduced a dimensionless parameter, the Knudsen number Kn , which is defined as the ratio of the mean free path k (m) and the pore diameter dp (m)

<!-- formula-not-decoded -->

If the mean free path of the reactant molecules is much larger than the dimensions of the structures ( Kn /C29 1), gas transport takes place in the molecular flow regime. 52 In this regime, the transport is dominated by particle-surface interactions and inter-particle interactions can in most cases be neglected.

The mean free path k (m) of molecules is given by 53

<!-- formula-not-decoded -->

with kB (m 2 kg/(s 2 K)) being the Boltzmann constant, T (K) being the temperature, P (Pa) being the pressure, and d (m) being the diameter of the molecules. The mean free path depends strongly on pressure, while the molecule size and temperature affect the mean free path to a

FIG. 2. Schematic representation of a deposition on a 3D structured surface by a line-of-sight technique (a) and by a conformal technique such as ALD (b).

<!-- image -->

minor extent, as illustrated in Fig. 3. At sufficiently low pressure, a molecular flow regime can be obtained in structures with macroscopic (i.e., mm to cm) dimensions, while for near-atmosphere pressures, molecular flow will only be achieved in nanometer scale features.

If the mean free path of the reactant molecules is much smaller than the dimensions of the features ( Kn /C28 1), gas transport is governed by viscous flow, 52 also known as continuum flow. 54 In viscous flow, there are frequent particle-particle interactions in the gas phase. The transition flow between molecular and viscous flow takes place when Kn /C25 1 and is often termed Knudsen flow although the latter term is also used as a synonym for molecular flow. 16

When the gas phase consists of different types of molecules, e.g., when a mixture of reactant molecules (species A) and carrier gas molecules (species B) is used in ALD, one has to adapt the above formula [Eq. (2)] of the mean free path. Chapman et al. 55 derived a specific scattering length k 0, A (m) for a particle of species A taking into account the interaction with particles of species B

<!-- formula-not-decoded -->

with kB (m 2 kg/(s 2 K)) being the Boltzmann constant, T (K) being the deposition temperature, Pi (Pa) being the partial pressure, and mi (kg) being the mass of molecules of type i 2 { A , B }. The cross-section between the molecules i and j with radii r i (m) and r j (m) is represented by 55

## C. ALD reactor types

One of the distinguishing factors among the different types of ALD reactors is whether they operate in the temporal or spatial ALD mode, with the first mode being the most conventional one. During temporal ALD, the sample is stationary and the different reactants are sequentially injected and removed from the sample cell. In spatial ALD, there is a continuous supply of the reactants in isolated injection regions which are separated by an inert gas curtain, while the substrate moves between the different zones. 56-58 Suntola developed in 1974 his first ALD reactor where he applied spatial ALD. 59 The reactor comprised a carousel that rotated at several rounds per second and worked at a base pressure of 10 /C0 4 Pa. 3 In another reactor design, Suntola et al. 60 used a carrier gas to separate the different surface reaction steps from each other in a temporal deposition mode.

As discussed above, the reactant (partial) pressure is a determining factor for the gas transport regime in high aspect ratio structures, influencing in turn the process of conformal coating during ALD. Therefore, we classify the different designs of ALD reactors according to the typical pressure ranges that are applied. Following the classification by George, 4 we define pump-type and flow-type (temporal) ALD reactors. In pump-type reactors , reactants are added into the reactor chamber without the use of a carrier gas and the typical reactant

FIG. 3. Mean free path (left y-axis) as a function of pressure, calculated according to Eq. (2), for molecules with average diameters of 5, 7, and 9 A ˚ at a temperature of 100 /C14 C (a) and for a molecule with an average diameter of 7 A ˚ at temperatures of 100 /C14 C, 300 /C14 C, and 500 /C14 C (b). The working pressure regimes of the pump-type, flow-type, and atmospheric pressure (AP-type) ALD reactors are indicated in the figure. The right y-axis of the graphs shows the characteristic feature size ( dp ). Comparing dp with the mean free path, k , allows to determine the corresponding flow regime for a given pressure: molecular flow regime ( k /C29 dp ) and viscous flow regime ( k /C28 dp ).

<!-- image -->

<!-- formula-not-decoded -->

pressures are in the range of 10 /C0 3 -10 0 Pa. After the reactant exposure, the chamber is evacuated by pumping down to a base pressure in the range of 10 /C0 4 -10 /C0 3 Pa. Because of the low pressure and the corresponding molecular flow regime, the reactor design is not restricted to specific geometric constraints and can easily be adapted to accommodate plasma sources and in-situ characterization techniques. The main disadvantage of pump-type reactors concerns the long cycle times in the range of 10 1 -10 2 s, due to the slow evacuation of the reaction chamber without the use of a purge gas. In the classical flow-type reactor design, 3,60 the reactants are entrained in an inert carrier gas which flows through the reactor in a viscous flow regime. Flow-type reactors are typically operated at a pressure near 100 Pa, and cycle times are on the order of 10 0 s. 4 Next to pump-type and flow-type reactors, atmospheric pressure (AP-type) reactors in which ALD processes take place at (or near) atmospheric pressure ( /C24 10 5 Pa) form the third class of ALD reactors. Over the past few years, there has been increasing interest in spatial ALD approaches applying atmospheric pressures for high throughput ALD for a number of applications including photovoltaics. 56-58 In this way, high deposition rates can be achieved for certain processes, e.g., /C24 1nm/s for ZnO. 61

As shown in Fig. 3, different flow regimes occur during ALD within high aspect ratio structures, depending on the characteristic size of the 3D features that are present on the substrate and the absolute pressure range, linked to the type of ALD reactor used. For instance, in millimeter-sized features, reactant transport occurs in the molecular flow regime in pump-type reactors, but in flow-type and AP-type ALD reactors, it occurs in the viscous flow regime.

## D. Exposure in ALD

Pressure plays a crucial role in the ALD process, as it determines the impinging flux of reactant molecules on the substrate. At a given pressure, a certain minimum amount of time is needed before the sample surface is fully covered with adsorbed reactant molecules and saturation is reached. A useful measure for the reactant exposure is therefore given by the product of the reactant partial pressure and the pulse time. In this way, the exposure is expressed in Langmuir (1 L ¼ 10 6 Torr s ¼ 7500Pa s). As an example, Gordon et al. 62 estimated that the exposure required to saturate a flat surface with Hf(NMe2)4 molecules during ALD of HfO2 at 200 /C14 C is in the range of 3-43L. Much larger exposures are commonly required during ALD on high aspect ratio structures to compensate for diffusional limitations. To deposit a conformal coating of HfO2 into holes with a pore diameter of 0.17 l mand a depth of 7.3 l m, an exposure of 9000 L was required. 62 Applying sufficiently large exposures is one of the essential conditions to obtain a conformal coating by ALD as will be exemplified later in this review article.

## E. Reaction mechanisms and sticking probability

The surface reaction kinetics of ALD processes can be complex 5,6,63 and should not be considered as trivial as depicted in Fig. 1. For many processes, even the reaction stoichiometry during an ALD cycle is not necessarily known. 64 To cope with this complexity when modelling the conformality of ALD processes, the reaction chemistry is often simplified by using irreversible Langmuir surface kinetics. 65-67 The sticking probability s is introduced as the probability that a reactant molecule reacts upon collision with the surface and contributes to film growth. It is often assumed that the sticking probability has a first order dependence with the available surface sites 16

<!-- formula-not-decoded -->

with s 0 being the initial sticking coefficient (i.e., reaction probability with a bare surface) and h being the fraction of covered sites. This expression implies that the surface reactivity gradually decreases with the increase in the coverage and eventually becomes zero. This simple model thus reflects the self-limiting nature of the surface reactions during ALD, while the reaction kinetics (fast/slow) can be implemented via the initial sticking coefficient s 0 (high/low values).

Taking a step back and considering in the first instance reversible Langmuir adsorption, the first reaction of an ALD cycle (Reaction A ) can be represented by

<!-- formula-not-decoded -->

with Ag being the gaseous reactant A , /C3 a vacant surface site, and A /C3 the chemisorbed reactant A . A /C3 can be interpreted as a 'lumped reaction product' (and not the result of an elementary reaction), containing multiple types of surface species simultaneously.

The adsorption rate r ads is equal to the product of the adsorption rate constant kads , the partial pressure of reactant A , PA , and the fraction of uncovered surface sites, giving the overall second-order 68 surface reaction rate equation

<!-- formula-not-decoded -->

The desorption rate r des is equal to the fraction of covered sites times the desorption rate constant kdes

<!-- formula-not-decoded -->

The rate of change in the surface coverage h is obtained by subtracting the desorption rate from the adsorption rate

<!-- formula-not-decoded -->

At equilibrium, d h dt is zero. In practice, gaseous byproducts are often continuously pumped out, making reverse reactions unlikely and justifying the assumption of irreversibility. When irreversible adsorption is assumed, the second term, r des , in Eq. (9) will be ignored.

The second reaction of the ALD cycle (reaction B ) can be described, in the lumped way, assuming an 'average' reaction product AB /C3

<!-- formula-not-decoded -->

In practice, in many models, reaction B is not modelled separately, and it is only considered that the surface left behind by exposure to reactant A , saturated with h /C25 1, is rendered reactive again in reaction B .

Furthermore, it is often assumed that the total number of adsorption sites for the Langmuir adsorption model is obtained from the number of metal atoms deposited per cycle and thus growth per cycle (GPC). The current authors understand this to be a gross oversimplification, as, e.g., the number of OH groups on alumina, which act as (reactive) adsorption sites in the trimethylaluminum reaction, is known to be 7-9 per nm 2 at typical ALD Al2O3 conditions, while the number of aluminium atoms deposited per cycle is around 4.5 per nm 2 . 5 Despite the fact that this assumption is clearly oversimplified, it

is being repeatedly used as it can give modelling results with a satisfactory fit.

For radical-assisted ALD processes (e.g., plasma-enhanced or PEALD) or ozone-based ALD processes, reactant molecules that collide with the surface can undergo recombination processes. For example, an O radical can recombine with an adsorbed O atom and form molecular O2 that leaves the surface. The probability that a species recombines during a collision with the surface is usually defined as the recombination probability r . 66,69,70 Although it depends on the process, the recombined species can often no longer contribute to film growth upon subsequent collisions with the surface, e.g., when the surface is only reactive towards O radicals and not towards molecular O2. Hence, recombination processes are usually considered loss processes.

## F. ALD growth types in high aspect ratio structures

Elam et al. 65 introduced the concepts of a diffusion versus a reaction limited growth type for ALD growth in narrow features in the molecular flow regime. 71 In the diffusion limited growth type , it is the geometry of the feature that causes the main difficulty in coating. 72 During deposition, the most accessible sites will be covered first, resulting in a clear front between the accessible (covered) sites and the less accessible (uncovered) sites. During the deposition, this front will gradually penetrate deeper into the feature. In the reaction limited growth type , the difficulty of coating is mainly related to a low sticking probability of the reactant molecules. In this case, there is a less sharp front between coated and as yet uncoated parts of the feature. For plasma-enhanced ALD, Knoops et al. 66 introduced a recombination limited growth type , where saturation is not limited by the diffusion rate or the sticking probability but by the recombination loss during collisions of the radicals with the side-walls of the feature. These different growth types are illustrated in Fig. 4, which shows unsaturated thickness profiles. Note that both the aspect ratio of the feature and the sticking probability of the ALD reactants will determine the ALD growth type, as will be discussed in Sec. VI B 4 and in Fig. 23.

## G. Aspect ratio and equivalent aspect ratio

The Aspect Ratio (AR) of a structure is typically defined as

<!-- formula-not-decoded -->

with L (m) being the depth and w (m) being the width of the structure, as indicated in Fig. 5. Achieving a conformal coating in a structure

FIG. 4. Schematic representation of unsaturated thickness profiles: diffusion limited (a), reaction limited (b), and recombination limited growth type (c). Adapted with permission from H. C. M. Knoops et al. , J. Electrochem. Soc. 157 (12), G241-G249 (2010). Copyright 2010 The Electrochemical Society.

<!-- image -->

FIG. 5. Schematic representation of a cylindrical hole (a), a square hole (b), and a trench structure (c) with width w and depth L . The three structures have the same AR; however, the holes [(a) and (b)] have a different EAR than the trench structure (c).

<!-- image -->

becomes more difficult with an increase in the AR of the structure. In addition, it will be easier to coat an elongated trench with depth L and width w than a cylindrical hole with the same depth L and diameter w because the opening through which the reactant can enter will be larger for the trench which facilitates the diffusion. AR is a 2D concept, based on geometrical measures of a cross-section of a 3D object, and is therefore not expected to be sufficient as a parameter to fully describe the difficulty of precursor diffusion into 3D features. Therefore, not only the AR will be important but also the length of the feature along the third dimension will have an impact on the conformality. A schematic representation of a hole and trench structure with equal AR is given in Fig. 5.

Gordon et al. 62 proposed a generalized expression for the aspect ratio a of holes

<!-- formula-not-decoded -->

with L (m) being the depth of the hole, p (m) being its perimeter, and A (m 2 ) being the cross-sectional area. This expression takes into account the 3D nature (third dimension) of the feature. For cylindrical holes, Eq. (12) reduces to L/w which is equal to the depth to width AR interpretation from Eq. (11). For trenches, Eq. (12) reduces to L/ (2 w ), which is a factor of two smaller than the conventionally used AR of Eq. (11). Gordon et al. also showed that for large a , the required exposure for conformal coating scales with a 2 . The difference of a with a factor of two between trenches and cylinders implies that a four times larger exposure is required to conformally coat a hole in comparison with a trench with the same depth to width ratio (AR) as can be measured in a cross-sectional view. This example of trenches versus holes clearly illustrates that a depth to width ratio of a 3D feature is not a sufficient measure to estimate the difficulty in coating the 3D structure: gas flow into the real structure will depend on the full 3D geometry of the feature.

To facilitate a direct comparison between different structures and literature reports, we propose a new concept to express the aspect ratio in a structure-independent way . Analogous to the 'equivalent oxide thickness' which was introduced in the field of high-k oxides to enable a straightforward comparison between different structures and

materials by expressing their key functional properties with respect to a well-known reference material (SiO2), 73 we propose to introduce the concept of an Equivalent Aspect Ratio (EAR) by referring to simple cylindrical holes as the reference structure. 74 The EAR of a given 3D feature can then be defined as the aspect ratio of a hypothetical cylindrical hole that would require the same reactant exposure dose during an ALD reaction as the feature of interest.

In Fig. 6, the AR and EAR are compared for arrays of holes, trenches, 62 and pillars. 51 Following expressions for the (E)AR were found:

- For circular holes: AR ¼ L / w and EAR ¼ L / w .
- For square holes: AR ¼ L / w and EAR ¼ L / w .
- For (infinite) trenches, AR ¼ L / w and EAR ¼ L /(2 w ).
- For elongated holes, AR ¼ L / w and EAR ¼ ( L ( w þ z ))/(2 wz ), with z being the length of the hole as indicated in Fig. 6. ffiffi ffi p /C0 /C1
- For squares pillars, AR ¼ L / w and EAR ¼ L = 2 2 w (valid for L / w in the range of 5-50, w / wpillar ¼ 3).

Most expressions follow from Gordon's definition (12) and were further confirmed via Monte Carlo modelling. 51 For arrays of pillars, the EAR was not derived from analytical equations, but was determined from Monte Carlo simulations, assuming an initial sticking coefficient of unity (see Sec. V). Comparing holes and trenches with the same AR, the EAR of trenches is a factor of two smaller. For L/w ratios in the range of 5-50 and w / wpillar ¼ 3, we found that the EAR of an array of pillars is a factor of 2 ffiffi ffi 2 p smaller than that for holes. It should be noted that this EAR was determined for molecular flow conditions. Additional calculations would be needed to determine the

FIG. 6. The scheme in the central circle depicts the depth to width ratio (AR) as measured on a cross-section of a 3D feature. The surrounding schemes provide the Equivalent Aspect Ratio (EAR) taking into account the 3D geometry of square holes (a), trenches (b), elongated holes (c), and square pillars (valid for L / w in the range of 5-50 and w / wpillar ¼ 3) (d). The EAR in (d) was determined for molecular flow conditions.

<!-- image -->

EAR of an array of pillars for viscous flow conditions and hence confirm whether or not the EAR is a flow regime dependent parameter.

## H. Ways to express the level of conformality

The 3D uniformity of a film is often discussed either in terms of step coverage or conformality (sometimes conformity). The definition of step coverage may vary from reference to reference.

Typically, Step Coverage (SC) is used for the ratio of the film thickness at the bottom of a feature to the film thickness at the top of the feature. Alternatively, it is calculated as the ratio of the film thickness at the side wall to the film thickness at the top [Fig. 7(a)]. Step coverage is typically expressed as percentage. The term is often used for thin films made by PVD 75 or (PE)CVD. 76 In ALD, the 'steps' which may be challenging for PVD and (PE)CVD (e.g., EAR 5:1) are typically coated 100% uniformly, i.e., with 100% SC, and therefore, more demanding (e.g., lateral) test structures are needed for ALD (see Sec. III).

When analysed with vertical structures, conformality of ALD is often defined in a similar manner as step coverage: ratio of bottom-top or sidewall-top film thickness and is given as percentage.

An alternative way to express the conformality of ALD coatings is via the coated (E)AR . This approach is typically used when the ALD coating did not reach the bottom of the feature and is especially useful for lateral, highly demanding test structures (AR &gt; 50:1). If a thickness profile is experimentally obtained, one determines the penetration depth at which the film thickness equals 50% of the film thickness at the top, which we propose to call the half-thickness-penetration-depth or 50%-thickness-penetration-depth, abbreviated PD 50% . 77 From the PD 50% , one can calculate the coated (E)AR. Alternatively, one can distinguish the coated versus uncoated regions of the feature in crosssectional electron microscopy or optical images. The transition point is then used to calculate the coated (E)AR. Similar to the PD 50% , one can also define the PD 80% which stands for the penetration depth at which the film thickness is reduced to 80% of the original film

FIG. 7. (a) Schematic cross-section of a high aspect ratio structure in which the step coverage can be defined as the ratio of the film thickness at the bottom (3) to the film thickness at the top (1) or the ratio of the film thickness at the sidewalls half way into the feature (2) to the film thickness at the top (1). (b) Thickness profile of an ALD process into a high aspect ratio structure. The PD 50% and PD 80% are indicated.

<!-- image -->

thickness. The concepts of step coverage, 78-81 PD 50% and PD 80% , are illustrated in Fig. 7.

## III. STRUCTURES TO QUANTIFY THE CONFORMALITY OF ALD

When studying the conformality of a certain ALD process, it is important to use test structures in which gas diffusion occurs according to a flow regime that is relevant for the envisioned application and reactor. Most of the high aspect ratio structures on which ALD is used for applications in micro-electronics, 29 batteries, 36 fuel cells, 31 catalytic surfaces, 40 etc., exhibit micrometer- or nanometer-sized dimensions. Note that for porous materials, IUPAC classifies three pore types according to the pore size: micropores have a diameter below 2 nm, mesopores have a diameter in the range of 2 to 50 nm, and macropores have a diameter above 50 nm. 82 As shown in Fig. 3, gas diffusion into structures with a characteristic width below ca. 1 l m will be determined by molecular flow when the deposition is performed in traditional flow(low-vacuum) and pump-type (high-vacuum) ALD reactors (because the mean free path of the reactant molecules will be much larger than the structure width). Therefore, the molecular flow regime is most relevant for the majority of 3D substrates, ALD reactors, and targeted applications although viscous flow applies in some specific cases.

Table I and Fig. 8 overview different types of high aspect ratio test structures that have been used for quantifying the conformality of ALD processes, ordered according to a decreasing size. Many types of structures have been used in mml m-nm ranges of feature sizes. We classify them here as vertical structures, lateral structures, and porous materials. These structures often differ in the methods typically used to characterize the film after deposition. Table I includes some references that discuss the fabrication of the specific structures and that introduce a particular characterization approach for determining the thickness/conformality of the deposited ALD coating, as further detailed in Secs. III A-III C.

## A. Vertical structures

Large surface area substrates with vertical features such as arrays of trenches, forests of pillars, carbon nanotubes, or assemblies of pores

[e.g., anodized alumina (AAO)] have been used in combination with ALD for applications in fuel cells, 31 batteries, 35 and supercapacitors. 116 Evidently, these substrates can also be used to quantify the conformality of an ALD process. Cross-sectional imaging of the structures [e.g., by scanning electron microscopy (SEM)] allows relatively straightforward visualization of the depth up to which an ALD coating has been deposited. The film thickness can be measured point-by point; accuracy depends on the sample preparation and skills of the electron microscopy operator.

Trenches etched into silicon have most often a width in the range of 100 nm 117 to several l m and achieve an EAR of &gt; 40:1 [Fig. 8(d)]. Vertical trenches are fabricated with an anisotropic etch process which is designed so that a passivated film is deposited on the sidewalls, while the feature is being etched. 118 With the basic Bosch Deep Reactive Ion Etching (DRIE) process, developed in the MEMS industry, one alternates etching and passivation cycles. 119 During the passivation cycle, a protective fluorocarbon film is deposited on all the surfaces. This step is followed by an etching step during which an ion bombardment removes the protecting film from all the horizontal surfaces. This technique allows us to achieve trenches with EAR up to 80:1 for widths in the range of 250-800 nm. 120 To characterize coated trenches, Gluch et al. 89 introduced a TEM lamellae preparation using focused ion beam (FIB) to measure detailed thickness profiles in trenches.

AAO structures can be prepared 121 by electrochemical anodization of aluminum films in liquid electrolytes and consist typically of a high density of well-defined parallel and uniform cylindrical pores which are arranged in a hexagonal symmetry with pore diameters between 5 and 300 nm [Fig. 8(f)]. The length of the pores can be controlled from a few tens of nm to a few hundreds of microns. After deposition, cross-sectional SEM is most often used to evaluate the penetration of the ALD coating. Elam et al. 65 introduced an alternative approach, where they polished the AAO membrane under a slight angle. In this way, one can obtain cross-sections along the entire length of the pore at different locations in one plane, simplifying the SEM analysis. This measurement technique is illustrated with a thickness profile of a ZnO coating in an AAO structure in Fig. 9(a). Perez et al. 95 dissolved the AAO structures and studied the ALD formed nanotubes directly by TEM, avoiding the need for preparing cross-sectional TEM

TABLE I. Overview of test structures used to quantify the conformality of an ALD process. The labels (a)-(j) correspond to the labeled images in Fig. 8.

| Structure                        | Characterization method                 | References         |
|----------------------------------|-----------------------------------------|--------------------|
| Macroscopic lateral trenches (a) | Ellipsometry/XRR/XRF/EDX                | 67, 69, 83, and 84 |
| Capillary tubes (b)              | Optical microscope                      | 85                 |
| Microscopic lateral trenches (c) | Optical and IR microscope/reflectometry | 83 and 86-88       |
| Micron trenches (d)              | TEM                                     | 89 and 90          |
| Pillars (e)                      | SEM/EDX                                 | 91-94              |
| Anodized alumina (AAO) (f)       | EPMA/TEM                                | 65, 95, and 96     |
| Nano trenches                    | TEM                                     | 79 and 97          |
| Forests of carbon nanotubes (g)  | SEM/EDX/TEM                             | 98-100             |
| Opals (h)                        | FE-SEM/TEM                              | 101-104            |
| Mesoporous thin films (i)        | XRF/porosimetry/TEM/SIMS                | 47 and 105-108     |
| Mesoporous powders (j)           | TEM/SEM/EDX                             | 109-113            |

<!-- image -->

samples from the AAO template. They also introduced an algorithm to automatically determine the wall thickness and diameter of the nanotube as a function of the depth from the TEM images. The thickness profile of a nanotube obtained out of an AAO pore is shown in Fig. 9(b). Recently, Macak and co-workers 122 studied the conformality

FIG. 8. Overview of macro-, micro-, and nano-sized test structures to quantify the conformality of ALD processes. (a) Macroscopic lateral trenches. 114 (b) Capillary tubes. Adapted with permission from J. S. Becker et al. , Chem. Mater. 15 (15), 2969-2976 (2003). Copyright 2003 American Chemical Society. (c) Microscopic lateral trenches (LHAR). Reprinted with permission from F. Gao et al. , J. Vac. Sci. Technol. A 33 (1), 010601:1-010601:5 (2015). Copyright 2015 American Vacuum Society. (d) Trenches (Si). Reproduced with permission from M. Ladanov et al. , Nanotechnology 24 (37), 375301:1-375301:9 (2013). Copyright 2013 IOP Publishing. (e) Pillars (silicon). (f) AAO. (g) CNT. Reprinted with permission from S. Deng et al. , RSC Adv. 4 (23), 11648-11653 (2014). Copyright 2014 RSC Publishing. (h) Opals (polystyrene). (i) Mesoporous titania films. Reproduced with permission from J. Dendooven et al. , Nanoscale 6 (24), 14991-14998 (2014). Copyright 2014 The Royal Society of Chemistry. (j) Mesoporous powders (Zeotile-4). Adapted with permission from S. P. Sree et al. , Chem. Mater. 24 , 2775-2780 (2012). Copyright 2012 American Chemical Society.

of ALD processes in anodic TiO2 nanotube layers. The closely spaced nanotubes had a diameter of 110 nm and an EAR of 180:1. By depositing the TiO2 nanotube substrate on a quartz crystal that can be mounted in a quartz crystal microbalance (QCM), they were able to perform in-situ QCM measurements during the ALD process. This

<!-- image -->

enabled real-time monitoring of reactant uptake during the ALD reactions. In principle, this approach could be extended to other porous substrates.

Track-etch membranes are another type of micro- or nanoporous materials which are formed by irradiation of polymeric sheets. The diameter of the etched pores can be in the range of a few nm to mm, resulting in an EAR of 10:1-1000:1. 123 SEM and cross-sectional

FIG. 9. (a) The thickness profile of a ZnO coating (measured with electron probe micro-analysis) in an AAO structure for several pulse times, as reported by Elam et al. 65 Adapted with permission from J. W. Elam et al. , Chem. Mater. 15 (18), 3507-3517 (2003). Copyright 2003 American Chemical Society. (b) The thickness profile of a HfO 2 nanotube that was ALD deposited into an AAO pore, as reported by Perez et al. 95 Reprinted with permission from I. Perez et al. , Small 4 (8), 1223-1232 (2008). Copyright 2008 John Wiley &amp; Sons, Inc.

TEM are often used to investigate the conformality of the deposited ALD coating in the membranes. 124 Arrays of (silicon) pillars 93,125 can be either etched or grown through catalyzed chemical vapor deposition [Fig. 8(e)]. To ensure mechanical stability, the pillars often have a diameter and spacing of 1-10 l m and a typically height of 50 l m. Forests of carbon nanotubes (CNTs) can be grown by CVD. Multiwalled CNTs can have a diameter of 10-100 nm and a length up

to several micrometers 126 [Fig. 8(g)]. To quantify the conformality of an ALD process on pillars or CNTs, EDX mapping is performed on a cross-section to quantify the amount of deposited material along the wall of the pillar or nanotube. 92,100

## B. Lateral structures

Dedicated lateral test structures have been designed by several groups to enable easy and accurate quantification of the penetration depth and the composition profile of the deposited coating. Often, the goal is to avoid the need of (time-consuming) cross-sectioning and electron microscopy. In the CVD literature, Yang et al. 127 used macroscopic lateral structures to analyze the CVD growth of HfO2 thin films. More recently, Shima et al. 84 introduced parallel-plate microchannels to study CVD processes. A patterned Si wafer, fabricated by single step etching, is clamped onto a planar Si substrate. In this way, one obtains lateral trench-like features with a microscopic gap size of 1-15 l m (determined by the depth of the Si etching process) and EAR up to 1000:1. The chronological overview below discusses the most important lateral structures that have been used to characterize the conformality of ALD films.

Fused silica capillary tubes with a length of 2 mm and a diameter of 20 l m were introduced as ALD conformality test structures by Becker et al. 85 [Fig. 8(b)]. After ALD, the coating on the exterior of the tubes was burned off and the inside was filled with a liquid with a similar refracting index as fused silica. In this way, one could visually determine the penetration depth of the ALD coating on the interior of the tubes using an optical microscope.

Macroscopic lateral structures were introduced by Dendooven et al. 67 [Fig. 8(a)] and were created by cutting a rectangular shaped structure (typically 0.5 cm /C2 2cm) from a sheet of aluminum foil (thickness of 100-500 l m) and clamping the resulting foil in-between two silicon wafers [Fig. 10(a)]. Because of the design of the structure, exposed regions of the clamped Si wafer are effectively turned into the sidewalls of a lateral trench. By using aluminum foils with different thicknesses and by cutting different shapes, one can easily produce structures with EARs in the range of 1:1-100:1. After ALD deposition, the clamped structure can be disassembled, resulting in two planar Si wafers. The penetration depth of the ALD coating can often be observed with the naked eye. Since the lateral size of the structures is on the order of cm, any technique for characterization of the layer thickness or composition with an intrinsic lateral resolution of the order of 1 mm can be used for obtaining an accurate profile of the thickness and composition of the ALD coating along the sidewalls of the test structure. Quantitative thickness profiles can be obtained, e.g., by ellipsometry (SE), x-ray fluorescence (XRF), or Rutherford backscattering spectroscopy (RBS) mapping of the regions of the Si wafers that constituted the sidewalls in the clamped structure. Not only the film thickness as a function of the depth but also the change in the composition of the deposited film can be monitored. This can be particularly important for complex coatings such as, e.g., ternary oxides or LiPON for 3D battery applications. An advantage of the macroscopic lateral structures is that the small thickness of the deposited film (nms) as compared to the total width of the trench (mms) implies that the EAR of the trench remains essentially constant during deposition, which simplifies, e.g., modelling. The main disadvantage is that their use is limited to pump-type reactors working at high vacuum if the molecular-flow assumption needs to be valid.

Air wedge structures were used by Gabriel et al. 83 to quantify the conformality of optical coatings deposited by ALD. These structures consist of two square silicon wafers with a side of 7 cm. The two wafers are in contact along one edge and open at the opposite edge with an air gap of 1560 l m [Fig. 10(b)]. By using such wedge structures, one can simultaneously estimate the penetration depth for a range of EARs (38:1-1410:1).

Musschoot et al. 69 extended the method of Dendooven et al. to investigate the penetration of thermal and plasma-enhanced ALD into fibrous materials. They used a hole, made of Teflon (1 cm /C2 1cm /C2 5cm), and filled it with non-woven polyester. The hole structure was clamped between the substrate holder and a flat Teflon surface. In this way, the ALD reactants could enter the fibrous material from only one side and precursor penetration into the non-woven polyester could be studied in a systematic way.

Puurunen and co-workers 86,87 fabricated microscopic lateral high aspect ratio (LHAR) trenches, code named PillarHall structures, with a gap height of 200-1000 nm and EARs up to 12 500:1, using microfabrication techniques commonly used for MEMS [Figs. 10(c) and 8(c)]. In recent work, the gap height range was expanded to 100-2000nm. 77 The lateral structures consist of a Si wafer (as bottom surface) and a suspended polysilicon membrane that is locally supported by a network of Si or SiO2 pillars. Elongated openings are etched through the top polysilicon membrane to define the access points for the gas into the lateral structure. After ALD, the film penetration can be investigated non-destructively through the membrane using, e.g., infrared spectroscopy or in some cases using a laboratory microscope. After the removal of the membrane, e.g., by using an adhesive tape, one can measure the penetration depth by microscopy and quantify the thickness of the ALD coating deposited onto the Si wafer (i.e., onto the bottom part of the lateral test structures) by using small-spot size techniques such as reflectometry or SEM/EDX. As indicated in Fig. 3, these LHAR structures with a typical 500 nm gap can be used in flow-type ALD reactors in the molecular flow gas transport regime up to pressures of 1000 Pa.

Recently, Schwille et al. 128,129 studied the conformality of ALD in microscopic rectangular cavities with lateral dimensions of 2000 l m, a height of 4.5 l m, and a central access hole with a diameter in the range of 4-60 l m [Fig. 10(d)]. The centrosymmetric nature of the structure slightly complicates the analysis as the equations for trenches do not apply directly because of the different symmetry. These structures resemble those encountered in real MEMS processing.

To tentatively demonstrate that the conformality of an ALD process is indeed determined by the flow type and EAR and not by the absolute dimension, a test was made for this review where a macroscopic lateral test structure reported by Dendooven et al. 67 with EAR of 200:1 and LHAR structures reported by Puurunen and co-workers (Generation 1, Ref. 86) were used to compare the quantification of conformality for the same ALD process in the same ALD run. Both substrates were coated in a pump-type reactor during a TMA/H2O process to deposit an Al2O3 film. The process parameters were identical for both substrates: T ¼ 100 /C14 C, PTMA ¼ 0.28 Pa, and PH 2 O ¼ 0 : 25 Pa. During the process, 1000 ALD cycles were applied with the following pulse/pump times: TMA (20 s) - pump (60 s) - H2O (20 s) pump (60 s). The film thickness was measured with SE in the case of the macroscopic lateral structure, while the coating was visualized using an optical microscope for the microscopic LHAR substrate. For

FIG. 10. Lateral test structures to quantify the conformality of an ALD process: (a) Macroscopic trenches. Reproduced with permission from J. Dendooven et al. J. Electrochem. Soc. 156 (4), P63-P67 (2009). Copyright 2009 The Electrochemical Society. (b) Air wedges. Reprinted with permission from N. T. Gabriel and J. J. Talghader, Appl. Opt. 49 (8), 1242-1248 (2010). Copyright 2010 The Optical Society. (c) LHAR structures. Reprinted with permission from F. Gao et al. , J. Vac. Sci. Technol. A 33 (1), 010601:1-010601:5 (2015). Copyright 2015 American Vacuum Society. (d) A microscopic cavity. Reprinted with permission from M. C. Schwille et al. , J. Vac. Sci. Technol. A 35 (1), 01B118 (2017). Copyright 2017 American Vacuum Society.

<!-- image -->

both substrates, a coated EAR of roughly 100:1 was found as can be seen in Fig. 11.

## C. Porous materials

Most conformality research has focused on ALD coatings in materials with critical dimensions &gt; 30 nm, e.g., using the abovementioned Si-based trench structures, AAO, and lateral structures. Fewer studies have focused on ALD coatings in sub-30 nm pores.

George and co-workers investigated ALD of Al2O3, TiO2, and SiO2 in tubular alumina membranes with a pore diameter of 5 nm. 47 After each ALD growth reaction, the pore diameter was derived from in situ N2 conductance measurements (assuming molecular flow in the pores). The pore size was smaller after a metal reactant exposure than after the subsequent H2O exposure, in accordance with the replacement of the bulkier metal reactant ligands on the pore walls by the smaller OH groups during the H2O step. The pore diameter was successfully reduced to molecular diameters (estimated in the range of 3-10A ˚ ), demonstrating the potential of ALD in tailoring nanoporous membranes for specific gas separation purposes.

To quantify the penetration of ALD coatings into nanosized pores, Dendooven et al. 106,115 developed an approach based on mesoporous SiO2 and TiO2 films that were deposited onto silicon substrates. The mesoporous SiO2 films had randomly ordered channel- like pores with an average diameter of ca. 6.5 nm. The mesoporous titania thin films contained ink-bottle shaped pores [Fig. 8(i)], i.e., spherical cages with a diameter in the range of 4-7 nm connected to each other via smaller pore necks (3-5 nm). The amount of deposited material during the ALD process was monitored using in situ XRF 105 and the remaining porosity using in situ grazing incidence small angle x-ray scattering (GISAXS) 115 and ellipsometric porosimetry (EP). 106 Since the thickness of the deposited film was of the same order as the gap size through which the gas had to enter the pore, the equivalent aspect ratio was not constant, but was gradually increasing as the thickness of the deposited film increased. They demonstrated tuning of the pore size up to near molecular dimensions for both channellike and ink-bottle shaped mesopores, indicating that the key limiting factor in ALD deposition into nanopores is the diameter of the reactant molecules used during the process, e.g., a TDMAT molecule has a molecular diameter of about 0.7 nm. 130

Opal structures consist mostly of close-packed silica or polystyrene spheres with a diameter of several hundred nm [Fig. 8(h)]. With ALD, one can deposit a coating into the void space between the spheres. 101-104 After the deposition, the original spheres can be removed to obtain an inverse opal structure, with potential applications in photonics. The conformality of ALD in these structures can be evaluated by EDX mapping of cross-sections of the opal structure to

FIG. 11. A TMA/H2O process was performed on a macroscopic 67 (EAR 200:1 / gap 0.1 mm) (a) and microscopic LHAR 86 test structure (EAR 200:1 / gap 500 nm) (b) in a pump-type ALD reactor under equal process conditions. Thickness profiles were obtained using ellipsometry (a) and optical microscopy (b). In both cases, a coated EAR of roughly 100:1 was found.

<!-- image -->

measure the penetration depth. After the removal of the opal template, cross-sectional SEM can be used to measure the thickness and lateral uniformity of the inverse opal structure.

Besides conformality in mesoporous thin films and opal structures, ALD infiltration in mesoporous powders, including silica gel, 109 Zeotile4 111,131 [Fig. 8(j)], metal organic frameworks (MOFs), 110,132 and alumina and silica powder with a size of several hundred microns, 112,133 has also been a subject of research. ALD functionalization of porous powders is mainly explored for applications in the field of catalysis. The diffusion into the interior portions of these materials is considered to be highly challenging, not only because of the high EAR (few nm wide pores of sometimes several microns in length) but also because of the very large surface areas (up to 2500 m 2 /g) 110 that need to be covered. Because of these large surface areas, the conformality of ALD is governed not only by the diffusion of the molecules but also by the reactant supply. 109

## IV. EXPERIMENTS ON CONFORMALITY OF ALD

In this section, we aim to provide a systematic overview of experimental data on the conformality of ALD processes. This overview does not aim to include all reported ALD processes but rather concentrates on those reports in which conformality has been investigated in detail. We distinguish three types of ALD processes: thermal, ozonebased, and plasma-enhanced processes. In thermal ALD, the conformality is influenced by the molar mass and reactivity of the ALD reactants as well as by the partial pressures and exposure times. Reactant decomposition (not occurring in theoretical ALD, but sometimes occurring in real processes) and too short purge/evacuation steps may decrease the conformality. For ozone-based and plasma-enhanced

ALD, the conformality additionally depends on the recombination of radicals (or ozone) which causes the flux of radicals (ozone) to decrease inside trenches and hence leads to decreased conformality. Therefore, in general, it is expected that better conformality will be achieved for thermal ALD than for ozone-based or plasma-enhanced ALD processes.

Tables II-IV overview experimental results on the conformality of thermal, ozone-based, and plasma-enhanced ALD processes, respectively, as reported in the literature. The indicated EAR has been calculated according to the definition given in Sec. II based on the feature dimensions reported in the corresponding reference. For AAO pores that are accessible from both sides, the tabulated EAR is calculated using half of the pore length. Unless stated otherwise in the table footnotes, the given exposure corresponds to the metal reactant (reactant A) of the ALD process. The value has been calculated from the reactant partial pressures and pulse times reported in the referenced papers (where available). The coated EAR equals the EAR of the structure in the case of complete coverage or is determined by PD 50% in the case of incomplete coverage as described in Sec. II and indicated with /C3 . If the results were presented in a thickness profile (film thickness as a function of the depth of the structure), 'D' is noted after the coated EAR. Not all fields in the tables could be filled because the process parameters were not always reported. For the PE-ALD processes shown in Table IV, the type of plasma configuration is noted. The influence of the type of configuration will be discussed in Sec. IV C.

## A. Thermal ALD processes

Table II summarizes experiments on the conformality of thermal ALD processes. According to the mean free path of the molecules as

TABLE II. Overview of experimental results on the conformality of thermal ALD processes. The coated EAR equals the EAR of the structure in the case of complete coverage or is determined by PD 50% in the case of incomplete coverage and indicated with /C3 . If the results were presented in a thickness profile (film thickness as a function of the depth of the structure), 'D' is noted after the coated EAR.

|          | Film (process)                    | Substrate          | EAR      | T ( /C14 C)   | Exposure (10 3 L)   | Characterization method               | Coated EAR   | References   |
|----------|-----------------------------------|--------------------|----------|---------------|---------------------|---------------------------------------|--------------|--------------|
| Oxides   | Al 2 O 3 (TMA/H 2 O)              | Macro lateral      | 100      | 200           | 9                   | SE                                    | 50 /C3 (D)   | 67           |
|          |                                   | Trench             | 5        | 300           |                     | SEM                                   | 5            | 134          |
|          |                                   | AAO                | 8.5      | 200           | 300                 | SEM/TEM                               | 8.5          | 135          |
|          |                                   | Nanorods (ZnO) 136 |          | 300           | 560                 | TEM                                   | Conformal    | 99           |
|          |                                   | Pillars (Si) 137   |          | 125           |                     | TEM                                   | Conformal    | 93           |
|          |                                   | AAO                | 1750     | 177           |                     | SEM/TEM                               | 1750         | 96           |
|          |                                   | AAO                | 770      | 177           | 4500                | SEM                                   | 770          | 65           |
|          |                                   | LHAR               | 10-12500 | 300           |                     | Reflectometry, optical/IR microscopy, | 75 /C3 (D)   | 86           |
|          |                                   | LHAR               | 10-12500 | 300           |                     | Reflectometry                         | 130 /C3 (D)  | 77           |
|          |                                   | Trench             | 11       |               |                     | SEM                                   | 11           | 138          |
|          |                                   | Macro lateral      | 5        | 75            | 18                  | SEM/EDX                               | 2.5 /C3 (D)  | 69           |
|          |                                   | Hole               | 17       | 200           | 370                 | SEM                                   | 17           | 139          |
|          | TiO 2 (TiCl 4 /H 2 O)             | Pillars (Si) 137   |          | 110           |                     | TEM                                   | Conformal    | 93           |
|          |                                   | AAO                | 7.5      | 200           |                     | SEM/TEM                               | 7.5          | 140          |
|          |                                   | LHAR               | 10-12500 | 110           |                     | Reflectometry                         | 90 /C3 (D)   | 77           |
|          |                                   |                    |          |               |                     | IR microscopy                         |              |              |
|          |                                   | LHAR               | 10-12500 | 110           |                     | Reflectometry                         | 65 /C3 (D)   | 86           |
|          |                                   | AAO                | 7000     | 100           |                     | SEM/TEM/EDAX                          | 7000         | 96           |
|          |                                   | Opal               |          | 70            |                     | FE-SEM                                | Conformal    | 101          |
|          |                                   | Opal               |          | 80            |                     | SEM                                   |              | 141          |
|          | TiO 2 (TTIP/H 2 O)                | VACNT 142          |          | 225           |                     | SEM                                   | (D)          | 100          |
|          | V 2 O 5 (VOTP/H 2 O 2 )           | AAO                | 7000     | 100           |                     | SEM/TEM/EDAX                          | 7000         | 96           |
|          | Fe 2 O 3 [Fe 2 (O t Bu) 6 /H 2 O] | AAO                | 100      | 140           |                     | SEM/TEM                               | 100          | 143          |
|          | Fe 3 O 4 [Fe(Cp) 2 /O 2 ]         | AAO                |          | 400           |                     | SEM/TEM                               |              | 144          |
|          | ZnO (DEZ/H 2 O)                   | AAO                | 700      | 177           | 2000                | EPMA                                  | 700 (D)      | 65           |
|          |                                   | AAO                | 5000     | 177           | 6 00 000            | EPMA                                  | 5000 (D)     | 65           |
|          |                                   | Opal               |          | 85            |                     | SEM                                   |              | 102          |
|          |                                   | Trench             | 3        | 250           |                     | SEM                                   | 3            | 90           |
|          |                                   | Nanowire (CuO)     | 145      | 150           |                     | SEM/TEM                               | Conformal    | 146          |
|          | Y 2 O 3 [(CpCH 3 ) 3 Y/H 2 O]     | Trench             | 35       | 300           | 50 000              | TEM                                   | 15 /C3       | 89           |
|          | ZrO [Zr(NMe 2 ) 4 /H 2 O]         | Elliptical holes   | 36       |               | 6                   | SEM                                   | 36           | 78           |
|          | ZrO [Zr(NEtMe) 4 /H 2 O]          | Elliptical holes   | 36       |               | 6                   | SEM                                   | 36           | 78           |
|          | ZrO [Zr(NEt 2 ) 4 /H 2 O]         | Elliptical holes   | 36       |               | 6                   | SEM                                   | 36           | 78           |
|          | RuO 2 [Ru(od) 3 /O 2 ]            | CNT 147            |          | 300           |                     | SEM/TEM                               | Conformal    | 148          |
|          | SnO x (SnCl 4 /H 2 O)             | Porous silicon     | 140      | 500           |                     | TEM/SIMS                              | 140 (D)      | 107          |
|          | HfO 2 (HfCl 4 /H 2 O)             | Trench             | 35       | 300           | 2000                | TEM                                   | 22 /C3       | 89           |
|          | HfO 2 [Hf(NMe 2 ) 4 /H 2 O]       | Holes              | 36       | 150           | 9                   | SEM                                   | 36           | 62           |
|          |                                   | Elliptical holes   | 36       |               | 6                   | SEM                                   | 36           | 78           |
|          | HfO 2 [Hf(NEtMe) 4 /H 2 O]        | Elliptical holes   | 36       |               | 6                   | SEM                                   | 36           | 78           |
|          | HfO 2 [Hf(NEt 2 ) 4 /H 2 O]       | Elliptical holes   | 36       |               | 6                   | SEM                                   | 36           | 78           |
| Nitrides | BN (BBr 3 /NH 3 )                 | AAO                | 10000    | 750           |                     | SEM                                   | 20           | 149          |
|          | AlN (TMA/NH 3 )                   | Trench             | 17.5     | 420           |                     | SEM                                   | 17.5         | 150          |
|          | TiN (TiCl 4 /Zn/NH 3 )            | Trench             | 5        | 500           |                     | SEM                                   | 5            | 134          |

TABLE II. ( Continued. )

|        | Film (process)                                        | Substrate             | EAR      | T ( /C14 C)       | Exposure (10 3 L)   | Characterization method         | Coated EAR      |   References |
|--------|-------------------------------------------------------|-----------------------|----------|-------------------|---------------------|---------------------------------|-----------------|--------------|
|        | TaN (TBTDET/NH 3 ) WN[( t BuN) 2 (Me 2 N) 2 W/ NH 3 ] | Trench                | 11       |                   |                     | SEM                             | 11              |          138 |
|        |                                                       | Silica capillary tube | 1000     | 300               | 110                 | Optical microscopy              | 210             |           85 |
| Metals | Ru [( i Pr-Me- Be)Ru(CHD)/O 2 ]                       | Hole                  | 4.6      | 225, 270, and 310 |                     | TEM                             | 4.6             |          151 |
|        |                                                       | Hole                  | 25       | 270               |                     | TEM                             | 25 152          |          151 |
|        |                                                       | Hole                  | 24       | 220               |                     | XTEM                            | 24              |          153 |
|        | Ru [(EtCp)Ru(DMPD)/ O 2 ]                             | AAO                   | 20       | 280               |                     | TEM                             | 20              |          154 |
|        |                                                       | Hole                  | 17       | 250               |                     | SEM                             | 17 155          |          156 |
|        | Ru [(Et-Be)Ru(CHD)/O 2 ]                              | Trench                | 2.25     | 225               |                     | TEM                             | 2.25            |          157 |
|        | Ru [(Et-Be)Ru(Et-CHD)/ O 2 ]                          | Hole                  | 32       | 225 and 270       |                     | XTEM                            | 32              |          158 |
|        | Ru [Ru(Me-Me 2 -CHD) 2 / O 2 ]                        | AAO                   | 166      | 300               |                     | TEM                             | 100             |          159 |
|        | Ru [(EtCp)Ru(Py)/O 2 ]                                | Hole                  | 20       | 275               |                     | SEM                             | 20 /C3          |          160 |
|        |                                                       | Trench                | 11       |                   |                     | SEM                             | 11              |          138 |
|        | Ru [Ru(EtCp) 2 /O 2 ]                                 | Trench                | 4        | 270               |                     | SEM                             | 4               |          161 |
|        |                                                       | AAO                   | 10       | 300               |                     | SEM/TEM                         | 10              |          162 |
|        | Ru (RuO 4 /H 2 )                                      | Pillars (Si) 163      | 10       | 100               |                     | SEM/EDX                         | Conformal (D)   |           94 |
|        | Pd [Pd(hfac) 2 /formalin]                             | AAO                   | 1500     | 200               |                     | SEM/EDX electrical conductivity | 1500            |          164 |
|        | W(Si 2 H 6 /WF 6 )                                    | AAO                   | 1750     | 200               | 60 00 000 165       | SEM/EDX                         | 1750 (D)        |          166 |
|        | Ir [Ir(acac) 3 /O 2 /H 2 ]                            | LHAR                  | 10-12500 | 250               |                     | EDX optical microscopy          | 20 /C3 (D)      |           87 |
|        | Ir [Ir(acac) 3 /O 2 ]                                 | LHAR                  | 10-12500 | 250               |                     | EDX optical microscopy          | 15 /C3 (D)      |           87 |
|        |                                                       | Hole                  | 142      | 300               |                     |                                 | Ref. 167        |          168 |
|        |                                                       | Trench                |          | 370               |                     | SEM                             |                 |          169 |
|        | Pt (MeCpPtMe 3 /O 2 )                                 | AAO                   | 8.5      | 250               | 405                 | SEM/TEM                         | 8.5             |          135 |
|        |                                                       | AAO                   | 150      | 250               |                     | SEM/EDX/SANS                    | 110 /C3 (D) 170 |          171 |
|        |                                                       | AAO                   | 200      | 300               |                     | SEM                             | 94              |          172 |
|        |                                                       | Trench                | 6        | 300               |                     | TEM                             | 6               |           79 |
|        |                                                       | AAO                   | 200      | 300               |                     | SEM/TEM                         | 50              |          173 |
|        |                                                       | Hole                  | 90       | 300               |                     | SEM/TEM                         | 30              |          173 |
|        | PtIr alloy [MeCpPtMe 3 /                              | AAO                   | 7.1      | 300               |                     | SEM                             | 7.1             |          172 |
|        | 2 3 2                                                 | Trench                | 9.5      | 300               |                     | SEM                             | 9.5             |          174 |

discussed in Sec. II, all experiments were performed with the molecular flow regime inside the structures. To conformally coat a substrate with a large EAR, a large dose of reactant molecules is needed because of the increased coated surface area and due to the increased diffusion time of the molecules. For example, Elam et al. 65 used an exposure of 6 /C2 10 8 L for a conformal ZnO coating of an AAO structure with an EAR of 5000:1. An unusually large exposure time of 10 min, resulting in an exposure of 6 /C2 10 9 L, was used to achieve a conformal W coating on an AAO structure with an EAR of 1750:1. 166 To reduce the deposition time, one can also increase the reactant partial pressure 230 to increase the total exposure.

A majority of studies are done on oxides, nitrides, and metals. Only a few studied the conformality of sulfides, 231,232 fluorides, 233 and phosphates. 92,234 The largest coated EAR by conventional (thermal) ALD is in the range of 5000:1, 65 in an extreme case an EAR of 7000:1 is achieved. 96 All such ultra-high aspect ratio coatings published in scientific journals are oxides and have so far been made with anodic alumina (AAO) structures. The published processes 96 are TiCl4/H2O, DEZ/H2O, and VOTP/H2O2. For the commonly used TMA/H2O process, the record coating so far is EAR 1750:1. 96 As seen from Table II, the coated EAR varies greatly for the same process, e.g., 5:1 to 1750:1 for the TMA/H2O process, depending on the test structures and process conditions. Also, the purpose of coating high aspect ratio

TABLE III. Overview of the experimental results on the conformality of ozone-based ALD processes. The coated EAR equals the EAR of the structure in the case of complete coverage or is determined by PD 50% in the case of incomplete coverage and indicated with /C3 . If the results were presented in a thickness profile (film thickness as a function of the depth of the structure), 'D' is noted after the coated EAR.

|        | Film (process)                                                             | Substrate                     | EAR      | T ( /C14 C)   | Exposure (10 3 L)   | Characterization method    | Coated EAR        | References   |
|--------|----------------------------------------------------------------------------|-------------------------------|----------|---------------|---------------------|----------------------------|-------------------|--------------|
| Oxides | Al 2 O 3 (TMA/O 3 ) SiO 2 ([H 2 N(CH 2 ) 3 Si(OCH 2 CH 3 ) 3 ]/H 2 O/O 3 ) | Trench AAO                    | 400      |               |                     | SEM/TEM                    | Ref. 175 400      | 176 177      |
|        | TiO 2 (TDMAT/O 3 )                                                         | Hole CNT 179                  | 20       | 180 100       | 4500                | TEM TEM/SEM/EDX            | 20 /C3 (D)        | 178 98       |
|        | TiO 2 [Cp /C3 Ti(OMe) 3 /O 3 ] V 2 O 5 (VOTP/O 3 )                         | Hole AAO                      | 15.3 100 | 270           |                     | SEM/TEM SEM/EDX            | (D) 100           | 180 150      |
|        | Fe 2 O 3 [Fe(Cp) 2 /O 3 ]                                                  | AAO Trench                    | 185      | 170 250       |                     | SEM                        | 2                 | 181          |
|        | 2 O 3 [CpFeC 5 H 4 CHN(CH 3 ) 2                                            | Silica aerogel                | 2 150    | 250 230       |                     | SEM/TEM SEM/EDX            | 44                | 159          |
|        | Co 3 O 4 (CoCp 2 /O 3 ) NiO [Ni(CpEt) /O ]                                 | Nanowire (TiO 2 ) Anodisc 183 |          | 167 250       |                     | TEM/EDX SEM/EDX            | 150 (D) Conformal | 181 182      |
|        | Fe /O 3 ] 2 3                                                              | AAO                           | 375 70   |               |                     | TEM/SEM/EDX TEM/SEM        | 375 (D) 70        | 184 185      |
|        | NiO (NiCp 2 /O 3 )                                                         | AAO                           | 238      | 300           |                     |                            | 238               | 186          |
|        | ZnO (DEZ/O 3 )                                                             | AAO                           | 250      | 50            |                     | SEM/EDX                    | 250 (D)           | 187          |
|        | HfO (TEMAHf/O )                                                            | Hole 188 Hole                 | 2 15.3   | 85 180        |                     | SEM SEM/TEM                | 2 9.6 /C3 (D)     | 189 180      |
|        | IrO 2 [Ir(acac) 3 /O 3 ]                                                   | LHAR                          | 10-12500 | 185           |                     | EDX 190 optical microscopy | 15 /C3 (D)        | 87           |
|        | PtO (Pt(acac) /O )                                                         | Trench                        | 3.5      | 120           |                     | FE-SEM                     |                   |              |
|        | Ru [Ru(EtCp) /O ]                                                          |                               | 5        | 275           |                     | SEM                        |                   |              |
|        | x 2 3 PtO (MeCpPtMe /O )                                                   | Trench                        |          |               |                     | TEM optical microscopy     | 3.5               | 191          |
|        | x 3 3                                                                      |                               | 16       | 120           |                     |                            | 5                 | 192          |
| Metal  | 2 3 Ir [Ir(acac) /O /H ]                                                   | Hole LHAR                     | 10-12500 | 185           |                     | EDX                        | 16 193 45 /C3 (D) | 194 87       |
|        | Pt (Pt(acac) 2 /O 3 )                                                      | AAO                           | 120      | 150           |                     | SEM                        | 50                | 196          |
|        |                                                                            | Trench                        |          | 165           |                     | FE-SEM                     |                   | 192          |
|        | Pt (MeCpPtMe 3 /O 3 )                                                      | AAO                           | 150      | 150           |                     | SEM/EDX                    | 35 /C3 (D)        | 195          |

structures can be different: Rose et al. 180 wanted to determine the slope of the thickness profile, and therefore, they on purpose used an unsaturated exposure.

Besides the exposure, high reactivity (often interpreted as high sticking probability) of the reactant molecules is important to achieve a good conformality in structures with a moderate EAR. In Table V, an overview is given of sticking probabilities that have been reported for specific ALD reactants. There is a large variety in reported sticking probabilities, even in values reported for the same reactant molecule. This variety of values is likely partly caused by the large range of methods used to determine the sticking probability. One can use not only theoretical approaches such as density functional theory calculations 176 or Monte Carlo modelling 128,178 but also several experimental methods to measure the sticking probability, e.g., Auger Electron Spectroscopy 235 and QCM measurements; 78,236 and more recently, sum frequency generation 237,238 has been reported in the literature.

## B. Ozone-based ALD processes

The use of ozone in ALD processes has several advantages. Ozone is a strong oxidizer, whereby some metal reactants react with O3 and not with H2O. 5 Another advantage is that at low deposition temperatures, ozone is easier to purge away than the sticky H2O. However, it often proves difficult to achieve a good conformality for ozone-based processes.

In Table III, one observes the best conformality with an ozonebased process for a film growth up to an EAR of 400:1. This result was obtained for a SiO 2 three-steps process from H2N(CH2)3Si(OCH2CH3)3 and water and ozone as reactants. 177 Also, V2O5 has been deposited conformally in a structure with an EAR of 100:1. 78 A conformal ZnO coating was achieved in an AAO structure with EAR of 250:1. 187 In general, most of the other ozone-based ALD processes have a relatively small coated EAR in comparison with the corresponding thermal ALD process. While the largest coated EAR of the thermal Al2O3 process was 1750:1, 96 for the ozone-based Al2O3 process, the coated EAR was only equal to 20:1. 176 This difference in coated EAR between thermal and ozone-based ALD processes is caused by the fact that ozone can thermally decompose in recombination processes on surfaces. The chemical composition of the substrate and the temperature have a large influence on the recombination probability of ozone. Knoops et al. 241 studied the recombination probabilities of ozone by measuring the transmission of ozone through high aspect ratio capillaries (EAR 350:1). The recombination probabilities from different processes are shown in

TABLE IV. Overview of the experimental results on the conformality of PE-ALD processes. The plasma configuration is indicated as C (capacitive), I (inductive), R (remote), and RE (radical enhanced). The coated EAR equals the EAR of the structure in the case of complete coverage or is determined by PD 50% in the case of incomplete coverage and indicated with /C3 . If the results were presented in a thickness profile (film thickness as a function of the depth of the structure), 'D' is noted after the coated EAR.

|          | Film (process)                                                      | Substrate                     | EAR    | T ( /C14 C)   | Plasma configuration   | Exposure (10 3 L)   | Characterization method   | Coated EAR      | References   |
|----------|---------------------------------------------------------------------|-------------------------------|--------|---------------|------------------------|---------------------|---------------------------|-----------------|--------------|
| Oxides   | Al 2 O 3 ð TMA = O /C3 2 Þ                                          | Macro lateral                 | 10     | 200           | RI                     | 27                  | SE                        | 10 (D)          | 70           |
|          |                                                                     | Hole                          | 8      | 200           | RI                     |                     | SEM                       | 8               | 197          |
|          |                                                                     | Trench                        | 13.5   | 250           | RC                     |                     | SEM                       | 13.5            | 198          |
|          |                                                                     | Macro lateral 199             | 5      | 75            | RI                     | 5                   | EDX                       | 0.75 /C3 (D)    | 69           |
|          |                                                                     | Hole                          | 10     | 225           |                        | 30                  | FE-SEM                    | 10              | 200          |
|          |                                                                     | Trench                        | 2      | 250           | C                      |                     | TEM                       | 2               | 201          |
|          |                                                                     | Trench                        | 15     |               | R                      |                     | SEM                       | 15 /C3          | 202          |
|          | SiO 2 ð 3DMAS = O /C3 2 Þ                                           | Trench                        | 30     | 250           | RC                     |                     | SEM                       | 30              | 198          |
|          | SiO 2 ð H 2 Si ½ N ð C 2 H 5 Þ 2 /C138 2 = O /C3 2 Þ                | Trench                        | 15     |               | R                      |                     | SEM                       | 15              | 202          |
|          |                                                                     | Hole                          | 50     | 75            |                        |                     | TEM                       | (D)             | 203          |
|          | TiO 2 ð TTIP = O /C3 2 Þ                                            | Trench                        | 13.5   | 150           | RC                     |                     | SEM                       | 13.5            | 198          |
|          |                                                                     | Hole                          | 8.7    | 225           |                        |                     | TEM                       | 8.7 (D)         | 204          |
|          | Ti ð TiCl 4 = O /C3 2 Þ                                             | Trench                        | 4.5    | 200           | RI                     | 75                  | FE-SEM/FEI                | 4.5             | 205          |
|          | HfO 2 ð TEMAHf = O /C3 2 Þ                                          | Trench                        | 30     | 250           | RC                     |                     | SEM                       | 30              | 198          |
|          | Ta 2 O 5 (Ta(OEt) 5 /O /C3 )                                        | Trench                        | 2.5    | 150-250       | RE                     |                     | SEM                       | 2.5             | 206          |
|          |                                                                     | Trench                        | 5      | 150-250       | RE                     |                     | SEM                       | 5               | 206          |
|          | Ta 2 O 5 ð Ta ð OEt Þ 5 = O /C3 2 Þ                                 | Trench                        | 10     | 200           | RC                     |                     | SEM                       | 10              | 198          |
| Nitrides | AlN ð TMA = NH /C3 3 Þ SiN ð Si Cl = NH /C3 Þ                       | Macro lateral Trench          | 10 2.5 | 200 400       | RI                     | 40 207              | SE TEM                    | 2.5 /C3 (D) 2.5 | 70 208       |
|          | x 2 6 3 SiN x ð DTDN2-H2 = N /C3 2 Þ                                | Trench                        | 2.75   | 300           | C                      |                     | TEM                       | Ref. 209        | 81           |
|          | TiN ð TDMAT = NH /C3 3 Þ                                            | Hole                          | 10     | 250           | R                      |                     | FE-SEM/AES                | 10              | 210          |
|          | TiN ð TDMAT = NH 3 = H /C3 2 Þ                                      | Trench                        | 10     | 180           | C                      |                     | FE-SEM                    | 10              | 80           |
|          | TiN ð TDMAT = H /C3 2 Þ                                             | Hole                          | 10     | 250           | R                      |                     | FE-SEM/AES                | 10              | 210          |
|          | = /C3                                                               | Hole                          |        |               | R                      |                     |                           | 10              |              |
|          | TiN ð TDMAT N 2 Þ                                                   |                               | 10     | 250           |                        |                     | FE-SEM/AES                |                 | 210          |
|          | TiN ð TiCl = H /C3 þ N /C3 Þ                                        | AAO                           | 14     | 200           |                        |                     | FE-SEM                    | 14              | 211          |
|          | 4 2 2                                                               | Hole                          | 6      | 350           | C                      |                     | SEM                       | 6               | 201          |
|          |                                                                     | 2 Trench                      | 10.5   | 400           |                        |                     | SEM                       | 10.5            | 213          |
|          | Mo 2 N                                                              | Nanotrench                    | 2.25   | 300           | RI                     |                     | XTEM                      | Ref. 214        | 215          |
|          | ð Mo ð N t Bu Þ 2 ð S t Bu Þ 2 = H /C3 2 Þ TaN ð TBTDET = H /C3 2 Þ | Hole                          | 10     | 260           |                        |                     | SEM                       | 10              | 216          |
|          | TaN (TBTEMAT/H 2 /C3 )                                              |                               | 2      |               | C                      |                     | TEM                       | 2               |              |
|          |                                                                     | Trench                        |        |               |                        |                     |                           |                 | 97           |
|          |                                                                     | Hole                          | 7      | 250           |                        |                     |                           | 7 5             | 217 218      |
|          | TaN x (PDMAT/H 2 /C3 )                                              | Trench                        | 5      | 250           |                        |                     | TEM                       |                 |              |
| Metals   | Co ðð C 5 H 5 Þ 2 Co = NH /C3 3 Þ                                   | Trench                        | 5.5    | 300           | HW                     | 20                  | FE-SEM                    | 5.5 219         | 220          |
|          | Ni ð Ni ð Cp Þ 2 = H 2 O = H /C3 2 Þ                                | Hole (TaN)                    | 3.3    | 165           | C                      |                     | SEM                       | 3.3             | 221          |
|          | Cu ð Cu ð acac Þ = H /C3 Þ                                          | Trench (SiO 2 )               | 1.75   | 85            | C                      |                     | SEM                       | 1.75            | 222          |
|          | 2 2                                                                 |                               | 2.5    | 85            |                        |                     |                           | 2.5             | 222          |
|          |                                                                     |                               | 4.5    | 85            |                        |                     |                           | 4.5             | 222          |
|          | Ru ð Ru ð EtCp Þ 2 = NH /C3 3 Þ                                     | Trench                        | 2      | 290           |                        |                     | TEM                       | 2 223           | 97           |
|          | Ag ð Ag ð fod Þð PEt 3 Þ = H /C3 Þ                                  | Si,Si/TaN Trench (SiO 2 /TiN) | 30     | 120           | RC                     |                     | FE-SEM                    | 5 224           | 198          |
|          | 2 Ag ((Ag(O 2 C t Bu)(PEt 3 ))/H /C3 )                              | Trench                        | 4.5    | 140           | RE                     |                     | SEM                       | 4.5             | 225          |

TABLE IV. ( Continued. )

| Film (process)                  | Substrate        | EAR   |   T ( /C14 C) | Plasma configuration   | Exposure (10 3 L)   | Characterization method   | Coated EAR   |   References |
|---------------------------------|------------------|-------|---------------|------------------------|---------------------|---------------------------|--------------|--------------|
| Ir ð Ir ð acac Þ 3 = O /C3 2 Þ  | Hole (elongated) |       |           370 | I                      |                     | SEM                       |              |          226 |
|                                 | Trench           |       |           370 |                        |                     | SEM                       |              |          169 |
| Pt ð MeCpPtMe 3 = O /C3 2 Þ 227 | Trench           | 17    |           300 | I                      |                     | SEM                       | 17 (D)       |          228 |
| Ta ð TaCl 5 = H /C3 2 Þ         | Trench           | 3     |           250 | I                      |                     | SEM                       | 3            |          229 |

Table VI. There are low-loss oxides (silica and alumina), high-loss oxides (MnO2 and Ru2O3), and high-loss noble metal surfaces (Pt). Liu et al. 150 reported that during ALD of HfO2 using O3, the decomposition rate increased for increasing substrate temperature, leading to a reduction in the step coverage. This temperature effect is also shown in Table VI for the ZnO process. Besides the temperature and the chemical nature of the surface, other parameters can also influence the recombination coefficient of ozone. For Pt 242 and

Fe2O3, 243 it has been reported that humidity can decrease the decomposition rate of ozone. In these cases, a co-dosing of ozone and H2O could lead to a higher conformality, as earlier suggested by Knoops et al. 241 Also, the addition of N2 could in some cases decrease the recombination probability of ozone; however, this can also influence the growth process (increase or decrease the film thickness, depending on the ALD process) and the material properties, e.g., N impurities in the TMA/O3 process. 244

TABLE V. Sticking probabilities for several ALD reactants and the method how they were derived, as reported in the literature. Updated from H. C. M. Knoops et al. , J. Electrochem. Soc. 157 (12), G241-G249 (2010).

| Species                  | Deposited material   | Method                      | T ( /C14 C)   | Sticking probability   | References   |
|--------------------------|----------------------|-----------------------------|---------------|------------------------|--------------|
| Al(CH 3 ) 3              | Al 2 O 3             | Monte Carlo model           | 177           | 0.001                  | 65           |
|                          |                      | Ballistic model             | 225           | 0.026                  | 200          |
|                          |                      | Semi-Analytical model       | 200           | 0.1                    | 67           |
|                          |                      | DFT                         |               | 0.1-0.9                | 176          |
|                          |                      | Continuum model             | 300           | 0.00572                | 77           |
|                          |                      | Monte Carlo model           | 200           | 0.02                   | 128          |
|                          |                      | Sum-frequency generation    | 100-300       | 0.002-0.005            | 237          |
|                          |                      | Auger electron spectroscopy | 25            | 0.01                   | 235          |
| Hf(NEtMe) 4              | HfO 2                | Monte Carlo model           | 180-270       | 0.03-0.6               | 180          |
| Ti(NMe 2 ) 4             | TiO 2                | Monte Carlo model           | 180           | 0.02 6 0.005           | 178          |
| Ti(O i Pr) 4             | TiO 2                | Ballistic model             | 125-225       | 0.04-0.1               | 204          |
| Cp /C3 Ti(OMe) 3         | TiO 2                | Monte Carlo model           | 270           | 0.01                   | 180          |
| TiCl 4                   | TiN                  | QCM                         | 25-125        | 0.006 6 0.002          | 236          |
|                          |                      | Continuum model             | 110           | 0.1                    | 77           |
| ZnEt 2                   | ZnO                  | Monte Carlo model           | 177           | 0.007                  | 65           |
| SiCl 4                   | SiO 2                | Monte Carlo model           |               | 10 -8                  | 65 and 239   |
| H 2 Si[N(C 2 H 5 ) 2 ] 2 | SiO 2                | Monte Carlo model           | 300           | 3 /C2 10 -5            | 128          |
| Zr(NMe 2 ) 4             | ZrO                  | QCM                         | 200           | 0.07                   | 78           |
| Co(C 5 H 5 ) 2           | Co                   | Monte Carlo model           | 300           | 0.002                  | 220          |
| H 2 O                    | Al 2 O 3             | DFT                         |               | 0.01-0.1               | 176          |
|                          |                      | Sum-frequency generation    | 100           | 0.000001               | 238          |
|                          |                      | Sum-frequency generation    | 300           | 0.0001                 | 238          |
|                          |                      | Auger electron spectroscopy | 25            | 0.25; 0.009 240        | 235          |
| O 3                      | Al 2 O 3             | DFT                         |               | 0.001-0.01             | 176          |
| O /C3                    | Al 2 O 3             | DFT                         |               | 0.1-0.9                | 176          |
| H /C3                    | TiN                  | QCM                         | 25-125        | 0.0003 6 0.0001        | 236          |
| N /C3                    | TiN                  | QCM                         | 25-125        | 0.01 6 0.002           | 236          |

TABLE VI. Measured recombination probabilities of ozone for various surfaces at different temperatures. Reprinted with permission from H. C. M. Knoops et al. , Chem. Mater. 23 (9), 2381-2387 (2011). Copyright 2011 American Chemical Society.

| Surface   | Temperature ( /C14 C)   | Recombination probability   |
|-----------|-------------------------|-----------------------------|
| Al 2 O 3  | 100-200                 | < 10 -6                     |
| ZnO       | 100                     | < 10 -6                     |
|           | 150                     | (5 6 2) /C2 10 -5           |
|           | 200                     | > 10 -3                     |
| Pt        | 100                     | > 10 -3                     |
| MnO x     | 100                     | > 10 -3                     |

## C. PE-ALD processes

In PE-ALD processes, one uses plasma excitation during the reactant exposure step, to create reactive species, such as electrons, ions, and radicals. 245 In some cases, PE-ALD offers a higher GPC, 197,246,247 higher film density, and lower deposition temperature than those obtained with thermal ALD. A lower deposition temperature can be useful for thermally fragile samples such as biological substrates or polymers. 248,249 The main disadvantages of PE-ALD include potential plasma damage to the substrate, more challenges in batch processing for higher throughput, and a limited conformality in high aspect ratio structures due to the recombination of the radicals by collisions with the surface. Note that, during two-particle collisions in the gas phase, recombination will not occur because of preservation of energy and impulse.

When coating deep holes or trenches with PE-ALD, the reactive species undergo multiple wall collisions during which they may be lost through surface recombination before they can reach the surfaces deeper in the hole. The elimination of radicals through recombination on the sidewalls of high aspect ratio structures will inevitably limit the conformality of PE-ALD. This is clear from Table IV, where the highest achieved conformally coated EAR for PE-ALD is only equal to 30:1, 198 compared to the much higher conformally coated EAR of thermal ALD (7000:1) 96 (Table II).

Table VII lists recombination probabilities r for O, N, and H atoms on various surfaces. The r values span a large range from 0.000094 for the recombination of O atoms on Pyrex to 0.8 for the recombination of H atoms on silicon. In general, higher recombination rates are measured on metallic surfaces, which explains the lower EAR values for PE-ALD of metals listed in Table IV. The largest coated EAR for metals coated with PE-ALD is 17:1, for a Pt coating in a trench structure. 228 In contrast, the largest PE-ALD coated EAR for oxides is 30:1 (SiO2 and HfO2). 198 Hydrogen radicals have a larger recombination probability than O and N radicals. However, O radicals have larger recombination probabilities on oxide surfaces containing elements with an incomplete d-shell (transition metals, such as Mn, Fe, Co, Ni, and Cu). 250 Furthermore, the recombination coefficient will also vary during the plasma pulse, because the surface changes during the pulse, from a surface that is covered with metal reactant ligands to the oxide, nitride, or metal that is deposited. When NH3, N2, and H2 plasmas are used, the high recombination of the N and H radicals may explain why in general it is more difficult to achieve good conformality for these processes in comparison with O2 plasma-based processes.

TABLE VII. Overview of the surface recombination probabilities of O, H, and N atoms on different surfaces as reported in the literature. Updated from H. C. M. Knoops et al. , J. Electrochem. Soc. 157 (12), G241-G249 (2010).

| Atom   | Surface                  | Recombination probability r   |   References |
|--------|--------------------------|-------------------------------|--------------|
| O      | Alumina                  | 0.0021                        |          250 |
|        |                          | 0.0097 6 0.0019               |          251 |
|        | Silica                   | 0.0004                        |          252 |
|        | Titania                  | 0.014 6 0.003                 |          251 |
|        | Iron(III)oxide           | 0.0052                        |          250 |
|        | Iron(II, III)oxide       | 0.015 6 0.003                 |          251 |
|        | Cobalt oxide             | 0.0049                        |          250 |
|        |                          | 0.029 6 0.006                 |          251 |
|        | Oxidized cobalt          | 0.085 6 0.005                 |          253 |
|        | Nickel oxide             | 0.0089                        |          250 |
|        | Oxidized nickel          | 0.27 6 0.04                   |          254 |
|        | Copper (II) oxide        | 0.043                         |          250 |
|        | Oxidized copper          | 0.225                         |          253 |
|        | Zinc oxide               | 0.00044                       |          250 |
|        | Pyrex                    | 0.000045                      |          250 |
|        |                          | 0.0020 6 0.0005               |          255 |
|        | Stainless steel          | 0.0702 6 0.009                |          256 |
| N      | Aluminum                 | 0.0018                        |          257 |
|        | Silicon                  | 0.0016                        |          257 |
|        | Silica                   | 0.00021 6 0.00003             |          258 |
|        | Stainless steel          | 0.0063                        |          257 |
| H      | Aluminum                 | 0.29                          |          259 |
|        | Oxidized aluminum        | 0.0018 6 0.0003               |          260 |
|        |                          | 0.0017 6 0.0002               |          261 |
|        | Silicon                  | 0.8                           |          262 |
|        |                          | 0.66                          |          263 |
|        | Oxidized silicon         | 0.0030 6 0.0003               |          260 |
|        | Titanium                 | 0.35                          |          259 |
|        | Nickel                   | 0.25                          |          259 |
|        |                          | 0.18 6 0.03                   |          260 |
|        | Copper                   | 0.14                          |          259 |
|        | Pyrex                    | 0.0058 6 0.0018               |          259 |
|        |                          | 0.00094 6 0.0004              |          261 |
|        | Stainless steel          | 0.030 6 0.014                 |          260 |
|        | Oxidized stainless steel | 0.0022 6 0.0002               |          261 |

The conformality of a PE-ALD process depends on the recombination probability and therefore on the type of radical, on the type of material on which it collides (the deposited material), and on the process parameters, such as deposition temperature, gas pressure, and plasma configuration. Varying the gas pressure or the plasma set-up will not only affect the recombination probability but also affect the radical density which has an influence on the conformality.

Dendooven et al. 70 used macroscopic test structures to study the influence of the gas pressure, the RF power, the plasma exposure time,

and the directionality of the plasma plume on the conformality of the remote PE-ALD of Al2O3 from TMA and O2 plasma and PE-ALD of AlN from TMA and NH3 plasma. Dendooven et al. used a remote inductively coupled plasma ALD reactor where the plasma is located at approximately 50cm from the substrate. They showed that by increasing the plasma power or the plasma pulse time, the conformality could be improved. For the Al2O3 process using O2 plasma, conformal coatings in holes with an EAR of 10:1 were considered achievable by optimizing the process parameters. The conformality of the AlN process was more limited, and an EAR of 10:1 seemed already out of reach.

Kariniemi et al. 198 investigated the conformality of various PEALD processes by deposition into microscopic trenches and subsequent characterization by cross-sectional SEM. They showed good conformality of metal oxide coatings deposited in trenches with EARs considerably larger than what had generally been achieved for PEALD (up to 30:1). Kariniemi et al. used a capacitively coupled RF plasma operated at two or three orders of magnitude higher pressure configuration, enabling higher radical densities in closer proximity to the substrate. These higher radical densities lead to higher radical fluxes deeper in the trench, enhancing the conformality. In the case of the Ag-PEALD process using H2 plasma, the coating penetrated conformally up to an EAR of 5:1. The low conformality is probably related to the high recombination probability of H radicals on metal surfaces.

It is assumed that in some cases, secondary thermal ALD reactions by the gaseous by-products can lead to an apparently better conformality than could be achieved with a 'pure' plasma process. For instance, experimental film thickness profiles obtained for PE-ALD of Al2O3 by Dendooven et al. 70 and Musschoot et al. 69 could only be reproduced by Monte Carlo simulations if a superposition of two reactions was assumed, i.e., (i) combustion reactions of O radicals with adsorbed TMA molecules near the entrance of the hole resulting in CO2 and H2O as reaction products and (ii) a secondary thermal ALD reaction of these H2O molecules that are diffusing deeper into the structure and react with adsorbed TMA molecules deeper in the hole. On the other hand, Kariniemi et al. 198 concluded that the secondary H2O effect played a minor role in their depositions as good conformality was also achieved for the SiO 2 process, while the Si-reactant reacts only slowly with H2O. The minor secondary H2O effect might be explained by the difference in radical fluxes inside the high aspect ratio structures. Indeed, for sufficiently large O radical fluxes, as is also the case on planar substrates, the effect of the secondary H2O reaction should be minor as it has to compete with the combustion-like O radical reactions which are likely to occur faster. If the radical flux is low, secondary reactions with the H2O may have a relatively large impact.

## V. SIMULATION MODELS ON CONFORMALITY OF ALD

A number of models for simulating the conformality of ALD processes, based on different theoretical and numerical approaches, have been developed in recent years. In this section, we aim to provide an overview of the analytical and computational models that are available in the literature. First, a classification for the models is proposed in Sec. VA, while multiscale approaches are addressed in Sec. V B. Next, attention is given to the key assumptions that are used and to how these differ for different models. Finally, typical model output results are discussed. An overview of the reported models focusing on the conformality of ALD is given in Table VIII. In Table IX, an overview of the multiscale models is presented (see also Sec. V B). For each model, the main modelling approach, the key assumptions, simulation space, simulated structures, and the most important conclusions are listed.

## A. Overview

## 1. Analytical models

In 2003, Gordon et al. 62 introduced a kinetic model to describe the diffusion and deposition of reactant molecules into holes with aspect ratio a . Gordon et al. defined the aspect ratio as

<!-- formula-not-decoded -->

with L (m) being the length, p (m) being the perimeter, and A (m 2 ) being the cross-section of the hole.

Gordon et al. 62 obtained an analytical expression, based on conductance formulae derived for cylindrical holes, for the exposure required to conformally coat a hole with a certain aspect ratio a

/C18

/C19

<!-- formula-not-decoded -->

In this equation, Kmax is the saturated coverage of the reactant molecule per unit surface area (molecules/m 2 , in practice, calculated from the GPC value of the process), m (kg) is the mass of the reactant molecules, kB is the Boltzmann constant, and T (K) is the temperature. For large EARs, the required exposure increases approximately quadratically with a . The model assumes that reactant molecules react upon their first collision with an unsaturated part of the substrate walls, implying a sticking probability of unity. Therefore, the model is especially powerful in the diffusion limited growth type, where the exposure time strongly depends on the value of a and much less on the value of the sticking probability (see also Sec. VI B 4 and Fig. 24). Alternatively, in the reaction limited growth type, the model predicts a minimum exposure for the reactant (with a sticking probability of less than one for any real ALD reaction) to coat a structure with a certain a . The predictions of the model agreed with the experimentally determined minimum exposure for coating holes with HfO2 (EAR 36:1). 62

Inspired by the model of Gordon et al. , several analytical models on the conformality of ALD processes have been derived. Dendooven et al. 67 used a similar approach based on conductance formulae to study the effect of sticking probability on the thickness profile. Ylilammi et al. 77 used diffusion equations to study the propagation of ALD growth in narrow channels. Yazdani et al. 100 and Cremers et al. 51 extended the Gordon model for other geometries being forests of CNTs and arrays of pillars, respectively. Also in these papers, closed-formulae were obtained to calculate the required exposure for conformal coating.

## 2. Computational models

In addition to the (semi)analytical models, models that require computational effort have been introduced to simulate the conformality of ALD processes. Following the classification suggested by Yanguas-Gil et al. , 264 these models can be categorized as ballistic, continuum, and Monte Carlo models.

TABLE VIII. Overview of different modelling works describing the conformality of ALD process, listed in the chronological order.

| References     | Main modelling approach           | Key assumptions                                                                                                                                                                                                                                                                   | Simulation space   | Geometry         | Conclusion                                                                                                                                                                                |
|----------------|-----------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------|------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Gobbert 282    | Ballistic                         | Molecular flow Reversible adsorption during first ALD reaction, irreversible reaction during sec- ond ALD reaction Species fluxes constant over small time scales                                                                                                                 | 2D                 | Trench           | Predict optimal pulse durations Simulation results for both ALD reac- tions and purge steps                                                                                               |
| Gordon 62      | Analytical (conductance formulae) | Molecular flow Irreversible reactions assumed Cosine distributed re-emission direction Vapor by-products neglected No depletion effects                                                                                                                                           | 3D                 | Hole Trench      | Pt K max ffiffiffiffiffiffiffiffiffiffi 2 p mkT p ¼ 1 þ 19 4 a þ 3 2 a 2 Formula to estimate the minimum exposure required for conformal coating of a hole/trench with an aspect ratio a  |
| Elam 65        | Monte Carlo                       | Molecular flow Molecule is irreversibly adsorbed if random number < s Re-emission of the molecule over a distance of 6 d i 289 with d i the diameter of the pore at the i th position All nanopores identical and molecules are entering the pores from both ends with equal rate | 1D                 | AAO              | Predict minimum exposure for confor- mal coating s /C29 H diffusion limited growth type integrated coverage /C24 t 1 = 2 s /C28 H reaction limited growth type integrated coverage /C24 t |
| Neizvestny 274 | Monte Carlo                       | Only reactant molecules on the substrate are considered, not those in the gaseous phase By-products evaporate immediately Nucleation starts around defects (sticking centers)                                                                                                     | 3D                 | Porous substrate | Growth per cycle stabilization after 2-4 cycles due to the roughness of the sur- face which increases nucleation                                                                          |
| Kim 204        | Ballistic                         | Molecular flow Irreversible Langmuir adsorption Studied 3 re-emission mechanisms: Cosine distributed, random, and specular All reactant molecules chemisorbed on the surface are converted into a solid film Ideal gas at the hole entrance (flux                                 | 3D                 | Hole             | Study step coverage depending on the reactant injection time                                                                                                                              |

TABLE VIII. ( Continued. )

| References    | Main modelling approach                | Key assumptions                                                                                                                                                                                                               | Simulation space   | Geometry                                                         | Conclusion                                                                                                               |
|---------------|----------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------|------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------|
| Rose 178      | Monte Carlo                            | Molecular flow Adsorption if random number < s Re-emission according a random direction                                                                                                                                       | 2D                 | Hole                                                             | Predict thickness profile Method to determine s                                                                          |
| Dendooven 67  | Semi-analytical (conductance formulae) | Molecular flow Irreversible Langmuir adsorption Cosine distributed re-emission direction Surface reactions occur at a much faster time scale than gas transport into the hole Incoming flux at pore entrance constant in time | 1D                 | Cylindrical hole                                                 | Predict coverage as a function of depth Extension Gordon model: Sticking probability different from unity                |
| Lee 290       | Continuum                              | Molecular flow Sticking probability of unity 'Outer' transport of molecules is much faster than transport into the pores Only radial diffusion Concentration of reactant molecules is constant Irreversible adsorption        | 3D                 | Cylindrical, spherical, and planar monoliths with tortuous pores | Calculate minimum exposure time for conformal coating. This exposure is largely dependent on the shape of the substrate. |
| Dendooven 70  | Monte Carlo                            | Molecular flow Irreversible Langmuir adsorption Cosine distributed re-emission direction Recombination probability                                                                                                            | 3D                 | Hole                                                             | Predict coverage as a function of depth of the feature, for PE-ALD                                                       |
| Knoops 66     | Monte Carlo                            | Molecular flow s , r constant 291 Cosine distributed re-emission direction                                                                                                                                                    | 2D                 | Trench                                                           | Simulate PE-ALD Introduction of recombination limited growth type                                                        |
| Adomaitis 266 | Ballistic                              | Molecular flow Irreversible Langmuir adsorption Cosine distributed re-emission direction Reactant in - reactant out ¼ reactant consumed Steady-state fluxes                                                                   | 3D                 | Circular hole                                                    | Derive reactant transmission probabil- ity functions for intra pore feature fluxes                                       |

TABLE VIII. ( Continued. )

| References      | Main modelling approach     | Key assumptions                                                                                                                                                                                                                                                                                              | Simulation space   | Geometry                              | Conclusion                                                                                                                                                                                                                  |
|-----------------|-----------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------|---------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Musschoot 69    | Monte Carlo                 | Molecular flow Irreversible Langmuir adsorption Re-emission according inverse reflection Particles in the medium are at rest, and the moving particle is small Neglect multiple collisions in a cell Transport equations (transmission, loss, and reflection probability)                                    | 1D                 | Hole filled with non- woven polyester | Simulate thermal and PE-ALD Predict coverage as function of depth in porous/fibrous substrate                                                                                                                               |
| Yanguas-Gil 272 | Continuum                   | Molecular flow Irreversible Langmuir adsorption The surface coverage changes concur- rently with the diffusion process 292 Time-dependent reaction equation                                                                                                                                                  | 1D                 | Via                                   | Predict saturation exposure times and thickness profiles Suited for high tortuosity structures (high number of wall collisions) Can be extended for viscous flow, 3D,…                                                      |
| Shimizu 220     | Monte Carlo                 | Molecular flow Irreversible Langmuir adsorption Cosine distributed re-emission direction                                                                                                                                                                                                                     | 2D                 | Trench                                | Determine sticking probability                                                                                                                                                                                              |
| Yazdani 100     | Continuum (Semi)-analytical | Molecular flow Quick equilibrium within and outside the CNT arrays Fast distribution of carrier gas Adsorption rate /C29 diffusion rate Analytic approximation for s ¼ 1 Exclude discrete nucleation phase 293                                                                                               | 3D                 | CNT                                   | A larger precursor supply is needed with increasing film thickness due to the increasing diameter of CNTs in combination with a larger surface area, which results in a limited penetration depth and non-uniform thickness |
| Keuter 294      | Continuum                   | Based on the model by Yanguas-Gil 272 Including second-order kinetics Transport to the substrate is not considered Pores are not taken individually into account (mean porosity, tortuosity, pore size, and Knudsen diffusion coefficient) Only reaction sites which are not shielded are taken into account | 1D                 | Porous substrate                      | Predict thickness profile                                                                                                                                                                                                   |

| References   | Main modelling approach   | Key assumptions                                                                                                                               | Simulation space     | Geometry                  | Conclusion                                                                                                                                          |
|--------------|---------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|----------------------|---------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------|
| Cremers 51   | Monte Carlo Analytic      | Molecular flow Irreversible Langmuir adsorption Cosine distributed re-emission direction Molecular flow Initial sticking coefficient of unity | 3D                   | Square hole Square pillar | The required exposure for conformal coating of an array of pillars is a factor of 2-30 times smaller than an array of holes with equal surface area |
| Schwille 129 | Monte Carlo               | Molecular and viscous flow Cosine distributed/specular re-emission direction Coverage if random number < s                                    | 2D centro- symmetric | Cavity                    | Predict film thickness in 3D structures Extraction of the sticking probability of the reactant                                                      |
| Jin 295      | Monte Carlo               | Molecular and viscous flow                                                                                                                    | 3D                   | Nanoparticle agglomerates | Predict pulse time for conformal coating                                                                                                            |
| Poodt 139    | Monte Carlo               | Molecular and viscous flow Irreversible Langmuir adsorption Simplified diffuse reflection model 296                                           | 2D                   | Trench                    | Predict exposure for 95% coverage                                                                                                                   |
|              | Analytic                  | Molecular and viscous flow                                                                                                                    | 3D                   | Hole                      | Predict the saturation dose for complete coverage (only valid in the diffusion limited growth type)                                                 |
| Ylilammi 77  | Continuum                 | Molecular flow Reversible Langmuir adsorption Irreversible successive surface reaction                                                        | 1D                   | LHAR                      | Calculate the thickness profile in high- aspect ratio trenches Extract kinetic growth information                                                   |

TABLE IX. Overview of multiscale modelling works describing the conformality of ALD, listed in the chronological order.

| References        | Scale                    | Model                 | Key assumptions                                                                                                                    | Space   | Geometry                | Conclusion                                                                                                                                                                                                                |
|-------------------|--------------------------|-----------------------|------------------------------------------------------------------------------------------------------------------------------------|---------|-------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Prechtl 176       | Feature                  | Ballistic             | B3LYP gradient corrected DFT functional                                                                                            | 2D      | Trench                  | Derive the activation energy of the initial adsorption and s For low s , depletion on the reactor scale is small; filling time /C24 1/ s For high s , filling time independent of s                                       |
|                   | Reactor                  |                       | Molecular flow Viscous flow                                                                                                        | 2D      | Showerhead reactor      | Predict minimum exposure for conformal coating                                                                                                                                                                            |
| Lankhorst 230     | Feature Reactor          | Continuum Continuum   | Molecular flow Viscous flow                                                                                                        | 1D 3D   | Trench Batch reactor    | Deposition time for conformal coating of trenched wafers /C29 than for flat wafers                                                                                                                                        |
| Adomaitis 266,270 | Feature Reaction         | Continuum Monte Carlo | Molecular flow Molecular flow                                                                                                      | 1D 2D   | Nanopore                | Observe GPC, film density, and surface roughness with varying ALD cycles and reactant dose                                                                                                                                |
| Yanguas-Gil 264   | Feature Reaction         | Ballistic             | Markov chain Molecular flow Cosine distributed re-emission direction Multiple reaction channels each with a specific probability   | 3D      | Circular pores          | Track the probabilities as a function of the number of collisions General expression for the absorption, escape, and effective reaction probability of the feature Predict total exposure required to cover the substrate |
| Miyano 203        | Reactor Feature Reaction | Continuum             | Flow rate of the gas below the inlet is uniform over the plane Molecular flow Reversible physisorption, irreversible chemisorption | 2D 2D   | Showerhead reactor Hole | Predict the thickness profile in a hole Precursor partial pressure and feeding time can be estimated for a hole with a given a                                                                                            |

a. Ballistic models. The derivations for collisionless flow in cylindrical tubes made by Clausing et al. 265 in the 1930s provide the basis for the ballistic transport models that are used nowadays. Ballistic models 204,266 inherently imply particle transport in the molecular flow regime. One uses the balance of particles to compute fluxes at different locations in the high aspect ratio structure. More specifically, the flux of reactant molecules reaching section i ( / i ) is expressed as the sum of the flux of reactant molecules coming from other sections in the structure ( / j ) and the flux of molecules coming from outside ( / 0 )

X

<!-- formula-not-decoded -->

with Si being the surface area of the discrete section i and qji and q 0 i being the probabilities that the molecules coming from section j /0 (outside the trench) can reach section i . s j and r j represent the reaction and surface recombination probabilities. The ballistic transport models used in the ALD literature are based on the earlier work of Cale and co-workers on low-pressure CVD. 267,268

b. Continuum models. In continuum models, 230,269-273 one uses a diffusion equation to simulate the transport inside a high aspect ratio structure. When the transport of the precursor molecules is described as a diffusion process without an additional flow, the diffusion can be described by Fick's second law

<!-- formula-not-decoded -->

with n ( t , z ) being the precursor density, z being the axial position along the depth of the high aspect ratio feature, t being the time, D being the diffusion coefficient, and a (t, z) being a loss term representing the adsorption of precursor molecules (chemisorption). Assuming that the cross-sectional area of the pore is independent of the position, particle conservation in a section of the feature reduces Eq. (16) to

<!-- formula-not-decoded -->

with D As being the surface area per unit volume, s being the reaction probability, h being the fraction of available sites, and J wall being the reactant flux per unit area to the walls. The change in surface coverage is given by

<!-- formula-not-decoded -->

FIG. 12. Monte Carlo algorithm used by Cremers et al. 51 for the simulation of thermal ALD.

<!-- image -->

with A 0 being the average surface area of an adsorption site. One can use Eqs. (16) and (17) both in the viscous flow regime and in the molecular regime by using the corresponding diffusion coefficient valid in that regime, as explained in Sec. V C 2. This is an important advantage of continuum models. In addition, the geometry of the substrate is only incorporated via two parameters, the diffusion coefficient and the surface area per unit volume, which makes this type of model suitable for simulation of more complex substrates.

c. Monte Carlo models. In Monte Carlo models, 51,65,66,114,178,274 one particle at a time is simulated based on an algorithm, as is exemplified in the flowchart in Fig. 12. Each particle typically represents a certain number of reactant molecules. Following the path of the particle, the intersection of the path and one of the boundary walls of the substrate feature is calculated. A random number x in the range of 0-1 is generated, and a sticking probability s of the reaction is assumed. If x &lt; s , the particle will be adsorbed and another particle will be simulated. Otherwise, the particle will be re-emitted according to a certain type of re-emission mechanism. The simulation stops if a predefined number of particles are simulated or if the predefined integrated coverage of the high aspect ratio structure is achieved.

## B. Multiscale approach

By modelling the conformality of ALD, one can focus on different length scales, being the reactor, feature, and molecular scale. In Fig. 13, a schematic representation of the different scales in the simulation space is shown. Multiscale approaches aim at combining the transport and/or reactions taking place at two (or more) different length scales.

## 1. Reactor and feature scale

Several models focus on the feature scale and do not take into account transport at the reactor scale. 51,62,66,275 One assumes that the

FIG. 13. Schematic representation of the reactor scale (for a rotary reactor) (a), the feature scale (b), and the molecular scale (c).

<!-- image -->

pressure at the opening of the feature or in the reactor, in general, is constant, while, in practice, the pressure will vary during a reactant pulse. For relatively small surface area structures, it can be correct to assume a constant flux of molecules at the feature entry during the ALD reaction. However, if one simulates high surface area materials like porous powders (e.g., SBA-15 powder can have a BET value larger than 300 m 2 /g) 276 or batches of multiple trenched wafers (e.g., 100 VNAND wafers yield a surface area of 1450 m 2 in a batch reactor 133 ), saturation will no longer be limited by the diffusion of the molecules but also by the limited availability of precursor molecules in the reactor.

Lankhorst et al. 230 developed a multiscale model in which continuum reactor scale simulations and 1D feature scale simulations of trench structures were combined. They simulated the HfO2 coating of high aspect ratio trenched wafers loaded in a multi-wafer vertical batch reactor. They found that the exposure time required for saturating all trenched wafers with TEMAHf was mainly governed by the timescales corresponding to the following three processes: (1) supply time needed to saturate the gas phase with the reactant, (2) supply time needed to provide sufficient reactant molecules to achieve full coverage, and (3) deposition time needed to coat the trench structures. The latter one can be estimated using the expression of Gordon et al. , 62 yielding a value of 6 s for a trench with an EAR of 60:1 and a reactor pressure of 93Pa. However, the total required exposure time for coating all trenches was found to be a factor of 10 higher, showing that depletion effects in the batch reactor, characterized by large required supply times, have a considerable impact.

Prechtl et al. 176 derived the sticking probability by ab initio calculations of the first adsorption step and fed that data as input into a feature scale simulator, coupled with a fluid dynamics based reactor simulator. With this model, they could predict the step coverage and saturation pulse time of an Al2O3 deposition, for a given deposition temperature, ALD tool, trench geometry, and oxygen partial pressure. Prechtl et al. 176 performed TMA/H2O depositions in a trench and these experimental results confirmed the validity of their multiscale simulation model.

## 2. Feature scale and molecular scale

Besides the multiscale approach of the coupling between feature and reactor scale, one can also study the coupling between the transport in the high aspect ratio structure and detailed reaction simulations at the surface. Yanguas-Gil et al. 264 used a Markov chain approach to decouple the transport from the complex chemical surface reactions. In a Markov chain approach, 277,278 the trajectory of a molecule is represented by a series of transitions between different states. A state represents a certain geometrical position in the simulated feature.

FIG. 14. Schematic representation of a Markov chain. A molecule in state i can undergo different transitions each with a characteristic transition probability. The molecule can react via a surface reaction pathway or be re-emitted outside the feature (state 0) or re-emitted to position j . Adapted with permission from A. YanguasGil and J. W. Elam, Theor. Chem. Acc. 133 , 1465:1-1465:13 (2014). Copyright 2014 Springer.

<!-- image -->

Figure 14 shows a schematical presentation of a Markov chain. State i represents the molecule reaching the surface. The molecule can react at point i on the surface according to a certain reaction, e.g., surface reaction pathway F 1 i . If the molecule does not react, it can be reemitted to point j of the surface or it can be re-emitted while leaving the structure (transition to 0). Each transition is characterized with a specific transition probability, e.g., Pij is the probability that the molecule will be re-emitted from position i to position j .

Adomaitis et al. 270 coupled a continuum model to describe the reactant transport in a high aspect ratio nanopore and a Monte Carlo model to describe growth of the ALD film at the molecular scale. This model bridges different timescales: (1) the slower timescale of the film growth over multiple ALD cycles and the resulting evolution in pore geometry (decrease in the pore diameter as a function of pore depth) (min to h) and (2) the faster timescale of the surface reactions taking place during each exposure (ns-ps). Progressive film growth was shown to influence the reactant transport in the nanopore (open at both ends), leading to reactant depletion and reduced growth in the central region of the pore.

In addition to the references listed in Tables VIII and IX and the accompanying discussion in Secs. V A and V B, the authors want to refer the reader to the recent book of Yanguas-Gil, 16 providing a more theoretical basis for the different models included here, together with a discussion of growth and transport in the broader context of thin film deposition, also including PVD and CVD concepts. More advanced modeling approaches related to shape evolution during growth and depletion effects at the reactor scale when coating high surface area materials, briefly touched upon above, are also discussed in this book. 16

## C. Key assumptions used in modelling

## 1. Flow regime: Molecular or viscous flow

A majority of models assume a molecular flow regime where particle-particle interactions can be neglected. This is especially true for the listed ballistic 204,266 and Monte-Carlo based models. 51,65,66,69,114 As already discussed in Sec. II, one can only obtain a molecular flow regime if the mean free path of the molecules is much larger than the limiting dimensions of the studied features ( Kn /C29 1). An important characteristic of the molecular flow regime is the scale invariance of the reactive transport process. 16 The same model to simulate the transport of molecules at a reactor scale can be used to model the transport of molecules inside high aspect ratio structures. However, in the limit of very small pore sizes, i.e., micropores with pore diameter &lt; 2nm, the diffusion is, in principle, governed by molecular flow but also surface diffusion and the interaction potential between molecules and the walls will affect the reactant transport. 16

Due to the high pressure in atmospheric pressure-type reactors, there is no molecular flow but a viscous flow regime where intermolecular collisions control the diffusion. To be able to describe ALD processes in atmospheric pressure reactors and to get a better insight into the effect of the process parameters, one needs other models which assume a viscous instead of a molecular flow regime. Yanguas-Gil et al. 279 developed a continuum formulation model in which the same formulae can be applied for molecular and viscous flow as further detailed. Poodt et al. , 139 Schwille et al. , 129 and Ylilammi et al. 77 developed simulations models, which can be used in both the molecular and viscous flow regimes.

## 2. Diffusion coefficient in continuum and analytical models

The transport of reactant molecules can be described by a diffusion coefficient. In the molecular flow regime, some models use a diffusion coefficient DKn derived for a cylindrical geometry with pore diameter dp (m) 62,67

ffiffiffiffiffiffiffiffiffiffi ffi

s

<!-- formula-not-decoded -->

where kB is the Boltzmann constant, T (K) is the temperature, and mp (kg) is the mass of the reactant molecule.

Yazdani et al. 100 developed a model to simulate an ALD process on CNTs. The different geometry of the substrate required an adaptation of the diffusion coefficient, which was approximated as ffiffiffiffiffiffiffiffiffiffi ffi s

/C18

/C19

<!-- formula-not-decoded -->

with r (m) being the radius and r CNT (1/m 2 ) being the areal density of the CNTs. Other models assume an approximated diffusion coefficient for other geometries such as square holes or pillars. 51

In the continuum based model of Yanguas-Gil et al. , 272 simulations in the viscous flow regime are achieved by replacing DKn by an effective diffusion coefficient D which represents the overall resistance to molecular motion given by

<!-- formula-not-decoded -->

with DKn being the Knudsen diffusion coefficient (molecular flow contribution) and Dgas being the gas phase diffusion coefficient (viscous flow contribution) given by the Chapman-Enskog approximation. 280

## 3. Simulation space in Monte Carlo models

Monte Carlo models offer the possibility for modelling complex geometries. However, most models neglect the 3D nature of the experimentally used structures and simulate features in one or two dimensions for simplification and to reduce the computational time. One assumes that the transport of reactant molecules in the structure is

FIG. 15. Simulated hole structure using a 1D (a), 2D (b), or 3D (c) model.

<!-- image -->

largely determined by only one of the dimensions of the cross-section, implying a trench structure instead of a hole structure. Elam et al. 65 used a 1D Monte Carlo model, to simulate a TMA/H2O and DEZ/ H2O process into an AAO structure. The pores of the AAO structure were modelled as a 1D array with array elements representing the diameter of the nanopore at a specific distance of the opening of the tube. If an element of the array becomes coated, the diameter of the given segment decreased. Other models use a 2D structure. 66 However, with a 2D model one cannot distinguish between, e.g., a trench and a cylindrical hole. A 3D MC simulation model was recently developed by Cremers et al. 51 They gained insights into the required exposure for conformal coating of an array of pillars versus holes and found that the required exposure to coat an array of pillars is a factor of 2-30 times smaller than the exposure needed to coat an array of holes with equal dimensions. Figure 15 shows a schematic representation of a simulated structure by a 1D, 2D, or 3D model.

## 4. Reaction mechanism

In several models, surface dynamics are related to reactant impingement fluxes, which are computed using the kinetic theory of gases. The Langmuir adsorption kinetics are often used as a simplification to model the complex reaction chemistry as was discussed in Sec. II E. Different models 67,69,114,241,266,272,279 introduce a sticking probability s to model the conformality of ALD. In Sec. VI, we will further look into the effect of the sticking probability on the thickness profile. Gobbert et al. 281,282 combine reversible and irreversible reactions to describe an ALD cycle 283

<!-- formula-not-decoded -->

where Ag denotes the gaseous reactant A , /C3 is a vacant surface site available for adsorption, and A /C3 stands for chemisorbed reactant A . The irreversible reaction by the second reactant B is described by

<!-- formula-not-decoded -->

where Bg stands for the gaseous reactant B , A /C3 is the chemisorbed reactant A , and AB /C3 is the chemisorbed product made from reactants A and B . Equation (22) describes a reversible adsorption of A on a single site, and Eq. (23) describes the irreversible reaction of B with the adsorbed A (known as the Eley-Rideal mechanism).

Yanguas-Gil et al. 264 used a Markov chain approach to simulate ALD processes in holes as discussed in Sec. V B. One of the advantages of a Markov chain is that one can easily introduce more complex surface

FIG. 16. Three re-emission mechanisms which are often used in ALD models: (a) cosine re-emission, (b) diffuse elastic re-emission, and (c) specular re-emission mechanism. Adapted with permission from H. C. Wulu et al. , J. Electrochem. Soc. 138 (6), 1831-1840 (1991). Copyright 1991 Electrochemical Society.

<!-- image -->

kinetics by adding additional surface kinetic channels with their own transition probability, e.g., extra secondary CVD reaction pathways.

## 5. Re-emission mechanism

When a particle hits the surface but is not adsorbed, it will be reemitted (i.e., bounced back) in a certain direction. Three re-emission mechanisms are typically reported in the literature: 284 cosine reemission, specular re-emission, and diffuse elastic re-emission. The different re-emission mechanisms are illustrated in Fig. 16. In the cosine and diffuse elastic re-emission mechanisms, the particle experiences a strong interaction with the surface and loses all information of the incoming trajectory. Following the cosine re-emission mechanism, particles are re-emitted according a cosine distribution. This mechanism was first suggested by Maxwell et al. 285 and was later experimentally verified in the work of Clausing 286 and Hurlbut et al. 287 Knudsen et al. 288 used the cosine re-emission mechanism in the derivation of the diffusion coefficient for low-density gases in narrow tubes. This assumption is often used in models of ALD. 62,66,67,114,266 When the particle undergoes a diffuse elastic re-emission mechanism, the re-emission direction of colliding particles is random: the particles have an equal probability to be re-emitted in any direction above the surface. The latter mechanism was used by Rose et al. 178 in their simulation model. In the specular re-emission mechanism, the re-emission angle is equal to the angle of incidence, and the surface acts as a perfectly reflecting wall. This mechanism is often used for the modelling of CVD processes. Kim et al. 204 compared their simulation results with the experimental results of the coverage of a hole with TiO 2 to fit several parameters including the re-emission mechanism, and they concluded that the cosine reemission mechanism produced the best fit to the experimental data.

## 6. Simulating one or multiple ALD cycles

To simplify the simulations, models do not typically simulate the entire ALD cycle, but simulate the first ALD reaction, assuming the second ALD reaction to be fully saturated. A difference between the various models is including or neglecting the film growth. Some models simulate only one ALD reaction. 65,66,178,271 The simulated profile is taken as the thickness profile obtained after a multiple cycle deposition. This interpretation is correct as long as the film thickness is small in comparison with the dimensions of the high aspect ratio feature.

Otherwise, the EAR experienced by the molecules will increase with an increasing number of ALD cycles, which will have an additional effect on the thickness profile.

Several models include film growth and can simulate multiple ALD cycles. 77,100,270,282 In these models, one simulates multiple times the first ALD reaction, assuming the second ALD reaction to be saturated. The film growth is determined by the entire ALD cycle (first reaction þ second reaction) and the film thickness equals a multiple of the GPC.

During ALD in a nanoscopic hole, such as an AAO pore, the coating deposited during each ALD cycle decreases the pore diameter, while the EAR increases. This was also demonstrated by Gordon et al. 62 with a deposition of HfO2 into patterned holes. The EAR of the holes increased from 36:1 to 43:1, after the deposition. Consequently, for a fixed unsaturated exposure, the Gordon model predicts a decrease in the penetration depth with each ALD cycle deposited. Perez et al. 95 showed good agreement between the slope obtained in the thickness profiles for HfO2 ALD in AAO pores and the slope predicted by iteratively applying Gordon's model to a pore that is gradually getting narrower as the ALD process progresses. Similarly, Yazdani et al. 100 observed the influence of the film thickness on the exposure required to coat a forest of CNTs. The increasing film thickness leads to an increasing hinderance of the precursor molecules.

In some cases, an additional coating will influence not only the transport of the precursor molecules but also the surface area which has to be coated. When coating nanopores, the pores will gradually shrink, as discussed in Sec. III C. When coating nanowires or CNTs as done by Yazdani et al., 100 the effective surface area which has to be covered will, in fact, increase as the coating thickens.

## D. Model output

## 1. Exposure and EAR

Based on the simulations, one can predict the required exposure to conformally coat a structure with a certain geometry. In addition, systematic simulations can provide valuable insights into the effect of specific simulation parameters on the required exposure time, such as the effect of sticking probability, geometry, and recombination probability.

As an example, Fig. 17 shows the calculated required TMA exposure for holes, trenches, and two arrays of pillars as a function of depth to width ratio using a 3D Monte Carlo model. If we compare the L / w ratios that can be obtained for a given exposure time, for example, for the value indicated by the dashed line in the figure, the L / w ratio that can be coated in a trench is 2 times larger than in a hole, and 2 ffiffi ffi 2 p times larger in a pillar structure with w / wpillar ¼ 3. These factors of 2 and 2 ffiffi ffi 2 p are valid in the plotted range of L / w values, being 5-25. These results confirm the earlier proposed definitions of EAR for trenches and illustrate how simulations can be used to calculate the corresponding EAR of a given structure, as done here for square pillars with w / wpillar ¼ 3. Note that, for square pillars with w / wpillar ¼ 1, it is not possible to derive a general expression for the EAR as a function of L / w that is valid for a large L / w range. Instead, the EAR should be calculated for a particular L / w value. For example, for L / w ¼ 25, we find that the required exposure for an array of pillars with w / wpillar ¼ 1 is equal to

FIG. 17. Absolute TMA exposure required to conformally coat a certain structure with L / w ratio. The structure is either a square hole, a trench or an array of square pillars. L is the height of the structures, and w is the width of the hole or the trench, or is the gap between two adjacent pillars. The width of the square pillars is denoted by wpillar . The data points were obtained using the Monte Carlo model reported by Cremers et al. 51 using an initial sticking probability of s 0 ¼ 1 and an integrated coverage of 90%.

<!-- image -->

the required exposure for an array of holes with L / w ¼ 10, yielding an EARof 10 for the array of pillars with L / w ¼ 25 and w / wpillar ¼ 1.

## 2. Thickness profile and sticking coefficient

In addition to knowledge about the required exposure, which is a critical parameter in the experimental optimization of the conformality of ALD processes, fundamental insights into the ALD process can be obtained by simulating detailed thickness profiles as a function of depth in the feature. Figure 18 shows some typical thickness profiles obtained from simulations, published in the literature. 66,129,180,272 To evaluate the models, one often compares the simulated thickness profiles with the experimentally obtained thickness profiles. A distinct feature often observed in both experimental and simulated profiles is the slope near the end of the thickness profile. For nanoscopic features, this slope has been partly attributed to the evolution of the EAR of the structure as the deposited film thickness has the same order of magnitude as the width of the structure, 95 as already discussed in Sec. V C 6.

However, the slope observed, e.g., in the thickness profiles for Al2O3 ALD in macroscopic holes, 67 cannot be explained by an increasing EAR during the deposition because the deposited film thickness ( /C24 nm) is negligible compared to the width of the hole ( /C24 100 l m). In this case, the observed slope is interpreted to be related to a sticking probability which is less than one. 67 By comparing experimental and simulated thickness profiles, one can determine the initial sticking coefficient as will be explained in more detail in Sec. VI B 3. To give the reader more insights into the effect of the sticking probability on the thickness profiles and, in

FIG. 18. Thickness profiles of a feature, showing the coverage along the depth of the feature. (a) Trench structure (EAR 50:1) simulated with a MC model. Reprinted with permission from H. C. M. Knoops et al. , J. Electrochem. Soc. 157 (12), G241-G249 (2010). Copyright 2010 The Electrochemical Society. (b) Comparison of experimental and simulated (MC model) thickness profiles of HfO 2 films in a cylindrical hole with EAR of 15:1. Reprinted with permission from M. Rose et al. , Appl. Surf. Sci. 256(12), 3778-3782 (2010). Copyright 2010 Elsevier. (c) Comparison of experimental and simulated (MC model) thickness profiles of SifO 2 films in a centrosymmetric cavity with the diameter of the access hole being 10 l m. Reprinted with permission from M. C. Schwille et al. , J. Vac. Sci. Technol. A 35 (1), 01B118 (2017). Copyright 2017 American Vacuum Society. (d) Thickness profiles into a structure simulated with a continuum model. Reprinted with permission from A. Yanguas-Gil and J. W. Elam, Chem. Vap. Depos. 18(1-3), 46-52 (2012). Copyright 2012 John Wiley Sons, Inc.

<!-- image -->

turn, how an experimentally observed profile can provide information on the chemistry of the ALD process, a systematic simulation study is presented and discussed in Sec. VI.

## 3. Other output

In addition to exposure and thickness profiles, some models can also explicitly provide information on the pressure profile inside the structure during the deposition, providing information on the reactant molecule distribution and on gas diffusion within the structure. 66,114 Yanguas-Gil et al. 264 reported statistical information such as the average interaction time, the trajectory of individual reactant molecules, and the average number of wall collisions.

## VI. INSIGHTS INTO ALD THICKNESS PROFILES BY MONTECARLO SIMULATIONS

One can obtain fundamental insights into the factors governing the surface chemistry of an ALD process by simulating thickness profiles along the depth of high aspect ratio structures. A schematic figure of a typical experimental thickness profile inside a high aspect ratio feature is shown in Fig. 19. In this review paper, we will focus on the slope at a 50% thickness (PD 50% ), which we will simply call the slope of the thickness profile. In this section, the effect of the initial sticking coefficient, feature size, and contributions of possible secondary CVD-type reactions on the thickness profile will be investigated by 3D Monte Carlo simulations. The effect of recombination probability has been previously discussed by Knoops et al. 66 and will not be considered here.

FIG. 19. Schematic figure of a typical thickness profile of an ALD process in a high aspect ratio structure, showing the film thickness as a function of the depth of the structure. This profile is characterized by an initial slope and a slope at 50% film thickness (PD 50% ).

<!-- image -->

## A. Monte Carlo simulation program

The calculated deposition profiles are obtained through 3D Monte Carlo simulations 51 and describe the coverage of the ALD film along the hole wall after the first reaction of the ALD cycle. All simulations were performed for a square hole with an EAR of 50:1 (width of 10 and depth of 500 distance units). To investigate the evolution of the sidewall coverage as a function of time during the ALD process, several thickness profiles are given for different exposure doses. The exposure doses are expressed in terms of the normalized exposure which is the exposure divided by the exposure required to saturate a flat surface. In Fig. 20, an overview is presented of the thickness profiles for theoretical saturationbased ALD processes. It was chosen to plot the thickness profiles as a function of EAR as this, in principle, would allow a better comparison of the profile shape, and the slope at PD 50% ð d h d ð EAR Þ Þ with earlier published results. For each case, two profiles are shown, calculated for open-ended structures and structures terminated by a bottom surface. In both cases, the reactant molecules can only enter the structure from the top, as is illustrated in Fig. 21. The effect of the terminating bottom surface will be discussed for all cases in Sec. VI B 5.

## B. Theoretical ALD cases

## 1. Model of Gordon et al. : Sticking probability of unity

Assuming a constant sticking probability of unity, the thickness profile consists of a fully covered part and an almost uncovered part, separated by a distinct and abrupt front (a step function). Gordon et al. 62 suggested that the top part of the trench, where all active surface sites have been saturated, can be considered as a 'vacuum tube' because impinging molecules simply bounce back. The bottom part of the trench, which presents a surface covered with reactive sites, acts as a 'vacuum pump' because all impinging molecules will stick to the wall. Based on this representation of the problem as a vacuum system, Gordon et al. derived an expression to calculate the exposure required to saturate a hole with given dimension, as already discussed in Sec. VA1. For an unsaturated exposure, the Gordon model predicts complete coverage of the pore walls up to a depth l 0 1

ffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffi ffi

s

<!-- formula-not-decoded -->

Step profiles calculated with Eq. (24) are shown in Fig. 20(a).

## 2. Irreversible Langmuirian adsorption: Influence of sticking probability on the thickness profile

Thickness profiles simulated assuming Langmuir-type irreversible adsorption with different values of the initial sticking coefficient are shown in Figs. 20(b)-20(e). If one introduces Langmuir's adsorption assumption to describe the sticking probability, ( s ¼ s 0 (1 h )), still assuming the initial sticking probability to be one, one observes a more gentle slope in the thickness profile compared to the step function of Gordon et al. 62 With the decrease in s 0, the profile becomes smoother. For very low initial sticking probabilities, the unsaturated thickness profiles do not necessarily show the initial plateau as shown in Fig. 20(e). This situation corresponds to the sketch in Fig. 4(b). Similar thickness profiles were also observed in the simulations of Rose et al. , 178 Dendooven et al. , 67 and Knoops et al. 66

## 3. Determining the initial sticking coefficient through comparing simulation with experiment

By comparing simulated thickness profiles with experimentally obtained profiles, one could quantify the initial sticking coefficient of a given ALD reactant. This approach was suggested by Rose et al. 178 who obtained a value of 0.02 6 0.005 for TDMAT on TiO2. Shimizu et al. 220 obtained a sticking probability of 0.002 for a (C5H5)2Co reactant. However, one should realize that a high density of data points along the depth profile, and especially in the slope region, are needed in order to make a fair conclusion about the sticking probability, as illustrated in Fig. 22. In this respect, the recent development in experimental test structures and analysis methods to extract depth profiles, e.g., by the microscopic LHAR structures 86 or the recently introduced methods by Schwille et al. , 129 might allow for a more detailed investigation of the initial sticking coefficient. By comparing experimental and simulation results, Bartha and co-workers could extract an initial sticking coefficient of 2 /C2 10 /C0 2 for TMA and 3 /C2 10 /C0 5 for the BDEAS reactant. 128 Ylilammi et al. 77 compared experimental results, obtained using the microscopic LHAR structures, with simulation results, obtained using their diffusion model, to extract an initial sticking coefficient of 0.00572 for TMA.

## 4. Influence of the initial sticking coefficient on the required exposure

In addition to the influence of sticking probability on the thickness profile, it is of interest to understand the effect of sticking probability on the reactant exposure required for creating a conformal coating up to a certain EAR. In Fig. 23, the exposure is shown as a function of the EAR, simulated by the Monte Carlo code of Cremers et al. 51 Similar simulation results were earlier published by Knoops et al. 66 For small EAR (up to EAR 30:1), one observes an increasing exposure for decreasing s 0 in the range of 1 to 0.01. With the increase in EAR, the exposure becomes independent of s 0 . As already discussed in Sec. II, these two behaviors correspond to the reaction limited (low EAR) and diffusion limited (high EAR) growth types, respectively. The exposure required to obtain a fully covered trench with high EAR (100:1) is equal for different initial sticking coefficients, in the range of 1-0.01; however, the thickness profile for unsaturated doses differs with the initial sticking coefficient due to differences in the ALD reaction kinetics. Figure 23 shows the difference in the thickness profile for an unsaturated coating of a trench structure with EAR of 100:1 and for an initial sticking coefficient of 1 and 0.01, respectively.

<!-- image -->

## 5. Influence of the bottom of the feature

The existence of a bottom in the structure is expected to have an impact on the thickness profile for an unsaturated exposure dose. In Monte Carlo simulations, we observe that for each case listed in Fig. 20, in general, the bottom of the structure is covered faster than the

FIG. 20. Thickness profiles of a hole structure with EAR of 50:1, in the case of a theoretical ALD process, based on saturating, irreversible reactions. The schematic s -plots represent the sticking probability s as a function of the surface coverage h . The analytical derived thickness profile according to Gordon et al. 62 is shown in (a). Simulated thickness profiles are shown, assuming the irreversible Langmuir-type adsorption with varying initial sticking coefficients s 0 ¼ 1 (b), 0.1 (c), 0.01 (d), and 0.001 (e). For each case, the thickness profiles are shown for a hole structure without (middle) or with (right) a terminating bottom surface. The normalized exposure required to obtain the different thickness profiles is given by black line: 700, blue line: 1400, red line: 2100, and green line: 2800.

adjacent walls. This phenomenon of a faster coverage of the bottom of the structure has been observed in other Monte Carlo simulations 51,66 and was also reported in ballistic models 264,266 which can be explained by the contribution of the direct pore-opening to pore-bottom flux, leading to a higher coverage of the bottom in comparison with the pore walls.

FIG. 21. Schematic figure of the simulated square holes with (a) and without a bottom (b). In both cases, the reactant molecules can only enter the structure from the top, as indicated by the arrows.

<!-- image -->

## C. Contribution of secondary CVD-type reactions

In a typical flux-controlled CVD process, film growth depends on the local gas flux and lacks the characteristic self-limited behavior of ALD. To simulate the contribution of a CVD-type process, the same simulation program was used for the ALD processes, omitting the limit on the number of adsorbed reactant molecules per unit area and with an adapted sticking probability s . We reduce the chemistry of the CVD process to one parameter preaction which represents the reaction probability and which is independent of the local coverage h . In the schemes in Fig. 24, the CVD contribution is represented by the orange curve. The ALD contribution during the process is similar as in the theoretical ALD case, assuming the irreversible Langmuir adsorption (blue curve). The total probability that a reactant molecule

FIG. 22. Experimental thickness profile obtained using spectroscopic ellipsometry for Al2O3 ALD (TMA/H2O process) in a macroscopic rectangular hole with EAR of 100 and a cross-section of 0.1 mm /C2 5 mm. The deposition was done in a pumptype reactor with a partial pressure of TMA of 0.27 Pa, a TMA pulse time of 4 s, and a deposition temperature of 200 /C14 C. The simulated profiles were calculated using the MC model of Dendooven et al. 114 and scaled to the film thickness measured in the first experimental data point.

<!-- image -->

sticks on the surface (green curve) is given by the sum of the probability for ALD reaction and p reaction of the irreversible CVD process, leading to

<!-- formula-not-decoded -->

FIG. 23. Absolute exposure for a TMA/H 2 O process as a function of the EAR for a trench structure (with bottom) and s 0 ¼ 1, 0.1, and 0.01 and an integrated coverage of 90% obtained from 3D Monte Carlo simulations. The inset shows the difference for s 0 ¼ 1 and s 0 ¼ 0.01 in the thickness profile for an EAR of 100:1 and an integrated coverage of 49%.

<!-- image -->

FIG. 24. Simulated thickness profile of a hole structure with EAR of 50:1, in the case of an ALD process with a CVD contribution, based on irreversible reactions. The schematic s -plots represent the sticking probability s as a function of the surface coverage h assuming the irreversible Langmuir-type adsorption with varying initial sticking coefficients s 0 ¼ 0.1 (a) and 0.01 (b) and reaction probability of the CVD contribution preaction ¼ 0.0002. For each case, the deposition profiles are shown for a hole structure without (middle) or with (right) a terminating bottom surface. The normalized exposure required to obtain the different thickness profiles is given by black line: 700, blue line: 1400, red line: 2100, and green line: 2800.

<!-- image -->

In Fig. 24, we show two cases of an ALD reaction with a small CVD contribution described with a p reaction of 0.0002. In (a) and (b), the initial sticking probability for the ALD reaction is considered 0.1 and 0.01 so that the simulation results can be compared to the ideal ALD cases in Figs. 20(c) and 20(d), respectively. The main impact of the CVD contribution can be observed in the thickness profile near the feature opening. A coverage degree of more than 100% can be observed at the entrance of the structure, with a value of ca. 160% for the highest simulated exposure. As expected due to the flux controlled nature of the CVD contribution, the coverage degree increases with exposure time, surpassing the value of 100%, meaning that more than one saturated ALD layer is deposited. Instead of the initial plateau typically observed in the ideal ALD simulations for s 0 above 0.01 (Fig. 20), the CVD contribution gives rise to a decreasing contribution because the flux decreases inside the feature. With the increasing exposure time, the slope of this initial part of the thickness profile increases, ultimately leading to clogging of the feature mouth. This first part of the thickness profile is in agreement with the classical CVD profile. 297 Deeper in the trench, where the coverage drops below 100%, we recognize the characteristics of the typical ALD profile, with a marked slope. This slope decreases with the decrease in the initial sticking probability, as for the ideal ALD case, and the slope and its position (PD 50% ) are only slightly affected by the CVD component. The PD 50% is a bit lower because the reactant molecules that are consumed in the CVD reactions near the feature entrance are no longer available to contribute to deposition deeper in the structure.

The effect of the presence of a feature bottom is comparable to the ideal ALD case.

To the best our knowledge, simulated profiles including a CVD contribution have not been studied in detail before nor have they been compared to experimental data. A more extended study of simulations could be instructive on how even a minor CVD component can impact the conformality of an ALD process. Moreover, comparing those thickness profiles with experimental thickness profiles can potentially give a hint on the possible contribution of a CVD-like component in the ALD process. To this end, it would also be useful to extract experimental thickness profiles for processes where intentionally a CVD component is present, e.g., by selecting a deposition temperature slightly above the decomposition temperature of the metal ALD reactant.

## D. Other reactions potentially influencing the thickness profile

The position of the slope and the gradient of the slope of the simulated profiles are often in good agreement with the experimental results. 67,178 However, there are also examples of experimental data which cannot yet be explained by the simulations. For example, there are experimental profiles in which no initial plateau is observed 114 (e.g., experimental profile in Fig. 22), or which show a more gradual decrease lacking a well-defined slope, 69 or a long tail following the slope. 69 Although irreversible Langmuir adsorption can often

satisfactorily describe the thickness profile, real processes are more complex, and the assumptions of the Langmuir model likely oversimplify the reactions. Moreover, additional reactions might contribute in real ALD processes:

- The more complex real surface chemistry may also include reversible reactions, which would affect the observed thickness profile. Then, some surface groups left behind after one reaction of the ALD process may desorb during the purging/pumping step, resulting in less reaction sites for the next ALD reaction. Indeed, when coating demanding 3D structures, the purging/pumping time is typically prolonged to allow excess reactants and reaction by-products to diffuse out of the structure. This prolonged evacuation time may affect the possible desorption of surface species. 298
- Real gas-solid reactions used in ALD may involve multiple surface reaction pathways that occur simultaneously or consequently. For example, for the TMA/H2O process, the existence of multiple reaction pathways has been proposed on the basis of experimental evidence. 5 Simulations have been made 264 to illustrate possible coverage profiles with a theoretical two-site model with different reaction probabilities.
- With this Monte Carlo code, the simulations are limited to the first reactant exposure of the ALD process, assuming the second reaction to be saturated. However, in the experimental cases, it is possible that both reactions are unsaturated and both limit the conformal nature of the coating. In this case, both reactions will contribute in their own particular way to the profile, which may lead to more complex profiles.
- As already discussed in Sec. V C 6, by deposition of more cycles, the EAR of the coated structure increases and the deposited film gradually limits the diffusion on molecules. As a consequence, the steepness of the slope of the thickness profile will decrease.
- In the growth of composite films by ALD, etching reactions of one of the reactants can occur. 275 This etching effect may be dependent on the flux of one of the reactants and may therefore have an influence on the corresponding thickness profile of the ALD process.
- Metal ALD on oxide supports usually suffers from nucleation difficulties. Islands form at the start of the process, which in turn act as catalysts for the ALD reactions, speeding up the growth. However, in 3D structures, due to differences in local reactant pressure along the feature, the nucleation process will likely be delayed deeper in the trench. In that way, the catalytic enhancement of the ALD growth will be affected and as such also the conformality. Also for applications in catalysis where one is mainly interested in nanoparticles grown by ALD, the diffusional limitations may cause an uneven nucleation over a 3D porous structure.
- Gaseous by-products (e.g., HCl) may not be inert, but they can occupy the same sites as the reactant. 273 Therefore, less sites will be available for the reactant molecules, potentially leading to a decrease of the GPC deeper in the structure.

## VII. SUMMARY AND OUTLOOK

In this review, an overview was given on the analysis and modelling of the conformality of ALD processes. Vertical, lateral, and (meso)porous substrates can be used to quantify the conformality of ALD processes. In general, a higher conformality is obtained for substrates coated with thermal ALD processes than with energy-assisted processes, such as plasma-enhanced and ozone-based ALD where surface recombination inevitably leads to a decrease in the impingement flux of radical/ozone species at an increasing penetration depth. To gain more insight into the process parameters influencing the conformality of ALD, several models (classified as analytical, ballistic, continuum,

Monte Carlo) have been reported in the literature. Models can predict the exposure required to conformally coat a certain substrate and can simulate detailed thickness profiles as a function of the penetration depth. These profiles for unsaturated exposures are characterized by a slope, the steepness of which increases with the increasing initial sticking coefficient. The steepness of the slope can also be influenced by an increasing aspect ratio of the coated feature during deposition due to the comparable dimensions of the feature and the film thickness. Besides ALD, also other reactions can influence the profile. CVD type contributions lead to growth beyond the ALD GPC and clogging at the entrance of the feature. An interesting potential direction of future work concerns investigating how more complex effects, such as etching, nucleation, and undersaturation, contribute to the thickness profile.

To define the achieved conformality, in the literature, one often focuses on the conformality as percentage or on the penetration depth of the deposited film along the high aspect ratio substrate. However, also the properties of the film could change along the depth of the structure. It would be interesting to extend the work on conformality to the observation of differences in the composition, crystallinity, morphology, and functional properties (e.g., dielectric constant, electronic conductivity, or Li ion conductivity) of the deposited coating.

Experiments on the conformality of ALD films have been performed on a variety of test structures for which often the height to width ratio (AR) is reported. This diversity of substrates and the lack of a standard definition of a geometry-independent aspect ratio often complicate a direct comparison of the reported results. In this article, we propose a geometry independent equivalent aspect ratio (EAR), to facilitate comparison. For benchmarking purposes, it would be interesting to investigate a specific process with different types of conformality test structures and crosscompare the results. In the future, it might be beneficial if a consensus could grow within the ALD community on the use of standardized test structures which could be used to validate conformality across a wide range of ALD reactor types, pressure ranges, and ALD processes.

## ACKNOWLEDGMENTS

Professor Christophe Detavernier, Ghent University, and Dr. Markku Ylilammi, VTT, are thanked for the many helpful discussions. V.C. acknowledges financial support from the Strategic Initiative Materials in Flanders (SIM, SBO-FUNC project). R.L.P. acknowledges funding from the Finnish Centre of Excellence on Atomic Layer Deposition by the Academy of Finland and the PillarHall project by Tekes, currently Business Finland. J.D. acknowledges the Research Foundation Flanders (FWO-Vlaanderen) for a postdoctoral fellowship. All the authors acknowledge the HERALD COST network.

## NOMENCLATURE

- /C3 Vacant surface site
- 3DMAS Tris(dimethylamino)silane
- a Aspect ratio according to Gordon et al. 62
- a ( t , z ) Loss term representing the adsorption of precursor molecules
- A Cross-sectional area

## Applied Physics Reviews

A /C3 Chemisorbed reactant A

| A               | Chemisorbed reactant A                                                                                               |
|-----------------|----------------------------------------------------------------------------------------------------------------------|
| A               | Gaseous reactant A                                                                                                   |
| g D A s         | Specific surface area (area per unit volume)                                                                         |
| A 0             | Average surface area of an adsorption site                                                                           |
| AAO             | Anodized Aluminum Oxide                                                                                              |
| acac            | Acetylacetone                                                                                                        |
| AES             | Auger Electron Spectroscopy                                                                                          |
| ALD             | Atomic Layer Deposition                                                                                              |
| AP-type reactor | Atmospheric pressure type reactor                                                                                    |
| AR              | Aspect ratio                                                                                                         |
| B3LYP           | Becke, three-parameter, Lee-Yang-Parr                                                                                |
| Be              | Benzene                                                                                                              |
| CHD             | Cyclohexadienyl                                                                                                      |
| CNT             | Carbon Nanotube                                                                                                      |
| Cp              | Cyclopentadienyl                                                                                                     |
| CVD             | Chemical vapor deposition                                                                                            |
| d               | Molecule diameter                                                                                                    |
| d p             | Pore diameter                                                                                                        |
| D               | Diffusion coefficient                                                                                                |
| D gas           | Gas phase diffusion coefficient (viscous flow contribution)                                                          |
| D Kn            |                                                                                                                      |
|                 | Knudsen diffusion coefficient                                                                                        |
| DEZ             | Diethylzinc                                                                                                          |
| DMPD            | Dimethylpentadienyl                                                                                                  |
| DRAM            | Dynamic random-access memory                                                                                         |
| DRIE            | Deep Reactive Ion Etching                                                                                            |
| EAR             | Equivalent aspect ratio                                                                                              |
| EDX             | Energy-dispersive x-ray spectroscopy                                                                                 |
| EPMA EP         | Electron probe microanalysis Ellipsometric Porosimetry                                                               |
| /               |                                                                                                                      |
| 0               | Flux of reactant molecules coming from outside                                                                       |
| / i             | Flux of reactant molecules reaching section i                                                                        |
| (FE)-SEM        | (Field emission)-scanning electron microscope Focused Ion Beam                                                       |
| FIB fod         | 6,6,7,7,8,8,8-heptafluoro-2,2-dimethyl-3,5-                                                                          |
|                 | octanedionate                                                                                                        |
| G g GISAXS      | Gaseous reaction by-product Grazing Incidence Small Angle X-ray Scattering                                           |
| GPC             | Growth per cycle                                                                                                     |
| HAR             | High aspect ratio                                                                                                    |
| hfac            | Hexafluoroacetylacetone Infrared                                                                                     |
| IR IUPAC        | International Union of Pure and Applied                                                                              |
| wall            | Chemistry Reactant flux per unit area to the walls                                                                   |
| J k ads k B     | Adsorption rate constant Boltzmann constant Desorption rate constant Saturated coverage of the reactant molecule per |
| max             |                                                                                                                      |
| k des           |                                                                                                                      |
| K               |                                                                                                                      |
|                 | unit surface area                                                                                                    |
| Kn              | Knudsen number Mean free path                                                                                        |
| k k 0, i L      | Specific scattering length of molecules i Depth                                                                      |
| LHAR m i        | Microscopic lateral trenches 86                                                                                      |
|                 | Mass of molecules i                                                                                                  |
|                 | Microelectromechanical                                                                                               |
| MEMS            | sytems                                                                                                               |

| MOF         | Metal Organic Framework                                                                        |
|-------------|------------------------------------------------------------------------------------------------|
| n ( t , z ) | Precursor density                                                                              |
| p           | Perimeter                                                                                      |
| P i         | Partial pressure of reactant i                                                                 |
| p reaction  | Reaction probability in a CVD-contributed process                                              |
| P           | Pressure                                                                                       |
| PD 50%      | Half-thickness-penetration-depth                                                               |
| PD 80%      | Penetration depth at which the film thickness is reduced to 80% of the original film thickness |
| PDMAT       | Pentakis dimethylamino tantalum                                                                |
| Pr          | Propyl                                                                                         |
| PVD         | Physical vapor deposition                                                                      |
| Py          | Pyrrolyl                                                                                       |
| q ji        | Probability that the molecules coming from sec-                                                |
|             | tion j can reach section i                                                                     |
| QCM         | Quartz Crystal Microbalance                                                                    |
| r           | Recombination probability                                                                      |
| r ads       | Adsorption rate                                                                                |
| r des       | Desorption rate                                                                                |
| r i         | Radius of the molecule i                                                                       |
| RBS         | Rutherford Backscattering spectroscopy                                                         |
| r i , j     | Cross-section between molecules i and j                                                        |
| s           | Sticking probability                                                                           |
| s 0         | Initial sticking coefficient                                                                   |
| S i         | Surface area of the discrete section i                                                         |
| SANS        | Small Angle Neutron Scattering                                                                 |
| SC          | Step coverage                                                                                  |
| SCM         | Shrinking Core Model 299                                                                       |
| SE          | Spectroscopic ellipsometry                                                                     |
| SIMS        | Secondary Ion Mass Spectrometry                                                                |
| h           | Fraction of covered sites                                                                      |
| t           | Pulse time                                                                                     |
| T           | Temperature                                                                                    |
| TBTDET      | Tris(diethylamido)(tert-butylimido)tantalum(V)                                                 |
| TBTEMAT     | Tert-butylimino-tris-ethylmethylamino tantalum                                                 |
| TDMAT       | Tetrakis(dimethylamido)titanium(IV)                                                            |
| TEM         | Transmission electron microscopy                                                               |
| TEMAHf      | Tetrakis(ethylmethylamido)hafnium(IV)                                                          |
|             | Trimethylaluminum                                                                              |
| TMA         |                                                                                                |
| VOTP        | Vanadium(V)oxytripropoxide                                                                     |
| w           | Width                                                                                          |
| XRF         | X-ray fluorescence                                                                             |
| XRR         | X-ray reflectivity                                                                             |

## REFERENCES

1 E. Ahvenniemi, A. R. Akbashev, S. Ali, M. Bechelany, M. Berdova, S. Boyadjiev, D. C. Cameron, R. Chen, M. Chubarov, V. Cremers, A. Devi, V. Drozd, L. Elnikova, G. Gottardi, K. Grigoras, D. M. Hausmann, C. S. Hwang, S. H. Jen, T. Kallio, J. Kanervo, I. Khmelnitskiy, D. H. Kim, L. Klibanov, Y. Koshtyal, A. O. I. Krause, J. Kuhs, I. K € arkk € anen, M.-L. K € a € ari € ainen, T. K € a € ari € ainen, L. Lamagna, A. A. Łapicki, M. Leskel € a, H. Lipsanen, J. Lyytinen, A. Malkov, A. Malygin, A. Mennad, C. Militzer, J. Molarius, M. Norek, C. € Ozgit Akg € un, M. Panov, H. Pedersen, F. Piallat, G. Popov, R. L. Puurunen, G. Rampelberg, R. H. A. Ras, E. Rauwel, F. Roozeboom, T. Sajavaara, H. Salami, H. Savin, N. Schneider, T. E. Seidel, J. Sundqvist, D. B. Suyatin, T. T € orndahl, J.

- R. van Ommen, C. Wiemer, O. M. E. Ylivaara, and O. Yurkevich, 'Review Article: Recommended reading list of early publications on atomic layer deposition-Outcome of the 'Virtual Project on the History of ALD',' J. Vac. Sci. Technol. A 35 , 010801:1-010801:13 (2017).
2. 2 A. A. Malygin, V. E. Drozd, A. A. Malkov, and V. M. Smirnov, 'From V.B. Aleskovskii's 'Framework' hypothesis to the method of molecular layering/ atomic layer deposition,' Chem. Vap. Depos. 21 , 216-240 (2015).
3. 3 R. L. Puurunen, 'A short history of atomic layer deposition: Tuomo Suntola's atomic layer epitaxy,' Chem. Vap. Depos. 20 (10-12), 332-344 (2014).
4. 4 S. M. George, 'Atomic layer deposition: An overview,' Chem. Rev. 110 , 111-131 (2010).
5. 5 R. L. Puurunen, 'Surface chemistry of atomic layer deposition: A case study for the trimethylaluminum/water process,' J. Appl. Phys. 97 (12), 121301:1-121301:52 (2005).
6. 6 V. Miikkulainen, M. Leskel € a, M. Ritala, and R. L. Puurunen, 'Crystallinity of inorganic films grown by atomic layer deposition: Overview and general trends,' J. Appl. Phys. 113 (2), 021301:1-021301:101 (2013).
7. 7 R. W. Johnson, A. Hultqvist, and S. F. Bent, 'A brief review of atomic layer deposition: From fundamentals to applications,' Mater. Today 17 (5), 236-246 (2014).
8. 8 H. Van Bui, F. Grillo, and J. R. van Ommen, 'Atomic and molecular layer deposition: Off the beaten track,' Chem. Commun. 53 (1), 45-71 (2017).
9. 9 S. A. Campbell, Fabrication Engineering at the Micro and Nanoscale (Oxford University Press, 2008).
10. 10 S. M. Rossnagel, 'Thin film deposition with physical vapor deposition and related technologies,' J. Vac. Sci. Technol. A 21 , S74-S87 (2003).
11. 11 H. Kim, H. B. R. Lee, and W. J. Maeng, 'Applications of atomic layer deposition to nanofabrication and emerging nanodevices,' Thin Solid Films 517 (8), 2563-2580 (2009).
12. 12 M. Knez, K. Nielsch, and L. Niinist € o, 'Synthesis and surface engineering of complex nanostructures by atomic layer deposition,' Adv. Mater. 19 (21), 3425-3438 (2007).
13. 13 C. Marichy and N. Pinna, 'Carbon-nanostructures coated/decorated by atomic layer deposition: Growth and applications,' Coordin. Chem. Rev. 257 (23-24), 3232-3253 (2013).
14. 14 C. Detavernier, J. Dendooven, S. P. Sree, K. F. Ludwig, and J. A. Martens, 'Tailoring nanoporous materials by atomic layer deposition,' Chem. Soc. Rev. 40 (11), 5242-5253 (2011).
15. 15 M. Leskel € a and M. Ritala, 'Atomic layer deposition (ALD): From precursors to thin film structures,' Thin Solid Films 409 (1), 138-146 (2002).
16. 16 A. Yanguas-Gil, Growth and Transport in Nanostructured Materials: Reactive Transport in PVD, CVD and ALD (Springer, 2017).
17. 17 N. Kumar, A. Yanguas-Gil, S. R. Daly, G. S. Girolami, and J. R. Abelson, 'Growth inhibition to enhanced conformal coverage in thin film chemical vapor deposition,' J. Am. Chem. Soc. 130 (52), 17660-17661 (2008).
18. 18 H. Kikuchi, Y. Yamada, A. M. Ali, J. Liang, T. Fukushima, T. Tanaka, and M. Koyanagi, 'Tungsten through-silicon via technology for three-dimensional LSIs,' Jpn. J. Appl. Phys., Part 1 47 (4), 2801-2806 (2008).
19. 19 K. Kim and K. Yong, 'Highly conformal Cu thin-film growth by lowtemperature pulsed MOCVD,' Electrochem. Solid State 6 (8), C106 (2003).
20. 20 K.-C. Shim, H.-B. Lee, O.-K. Kwon, H.-S. Park, W. Koh, and S.-W. Kang, 'Bottom-up filling of submicrometer features in catalyst-enhanced chemical vapor deposition of copper,' J. Electrochem. Soc. 149 (2), G109-G113 (2002).
21. 21 D. Josell, S. Kim, D. Wheeler, T. P. Moffat, and S. G. Pyo, 'Interconnect fabrication by superconformal iodine-catalyzed chemical vapor deposition of copper,' J. Electrochem. Soc. 150 (5), C368-C373 (2003).
22. 22 O. Sneh, R. B. Clark-Phelps, A. R. Londergan, J. Winkler, and T. E. Seidel, 'Thin film atomic layer deposition equipment for semiconductor processing,' Thin Solid Films 402 (1-2), 248-261 (2002).
23. 23 W. Jeon, H.-S. Chung, D. Joo, and S.-W. Kang, 'TiO2/Al2O3/TiO2 nanolaminated thin films for DRAM capacitor deposited by plasma-enhanced atomic layer deposition,' Electrochem. Solid State 11 (2), H19-H21 (2008).
24. 24 K. Endo, Y. Ishikawa, T. Matsukawa, Y. Liu, S. I. O'Uchi, K. Sakamoto, J. Tsukada, H. Yamauchi, and M. Masahara, 'Enhancement of FinFET performance using 25-nm-thin sidewall spacer grown by atomic layer deposition,' Solid-State Electron. 74 , 13-18 (2012).
25. 25 M. P. Chudzik, S. Krishnan, M. Dai, S. Siddiqui, J. Shepard, and U. Kwon, '(Keynote) atomic layer deposition trends and challenges in high-k/metal gate and alternative channel CMOS processing,' ECS Trans. 60 (1), 513-518 (2014).
26. 26 B. Hudec, C.-W. Hsu, I.-T. Wang, W.-L. Lai, C.-C. Chang, T. Wang, K. Fr € ohlich, C.-H. Ho, C.-H. Lin, and T.-H. Hou, '3D resistive RAM cell design for high-density storage class memory-A review,' Sci. China Inform. Sci. 59 (6), 061403:1-061403:21 (2016).
27. 27 J. Oh, H. Na, S. Park, and H. Sohn, 'Characteristics of junctionless charge trap flash memory for 3D stacked NAND flash,' J. Nanosci. Nanotechnology 13 (9), 6413-6415 (2013).
28. 28 N. Biyikli and A. Haider, 'Atomic layer deposition of ZnO: A review atomic layer deposition: An enabling technology for the growth of functional nanoscale semiconductors,' Semicond. Sci. Technol.. 32 , 093002 (2017).
29. 29 T. M. Mayer, J. W. Elam, S. M. George, P. G. Kotula, and R. S. Goeke, 'Atomic-layer deposition of wear-resistant coatings for microelectromechanical devices,' Appl. Phys. Lett. 82 (17), 2883-2885 (2003).
30. 30 N. D. Hoivik, J. W. Elam, R. J. Linderman, V. M. Bright, S. M. George, and Y. C. Lee, 'Atomic layer deposited protective coatings for microelectromechanical systems,' Sens. Actuator 103 , 100-108 (2003).
31. 31 N. Cheng, Y. Shao, J. Liu, and X. Sun, 'Electrocatalysts by atomic layer deposition for fuel cell applications,' Nano Energy 29 , 220-242 (2016).
32. 32 J. A. Van Delft, D. Garcia-Alonso, and W. M. M. Kessels, 'Atomic layer deposition for photovoltaics: Applications and prospects for solar cell manufacturing,' Semicond. Sci. Technol. 27 (7), 074002:1-074002:13 (2012).
33. 33 J. R. Bakke, K. L. Pickrahn, T. P. Brennan, and S. F. Bent, 'Nanoengineering and interfacial engineering of photovoltaics by atomic layer deposition,' Nanoscale 3 (9), 3482-3508 (2011).
34. 34 G. Dingemans and W. M. M. Kessels, 'Status and prospects of Al2O3-based surface passivation schemes for silicon solar cells,' J. Vac. Sci. Technol. A 30 (4), 040802:1-040802:27 (2012).
35. 35 J. Liu, M. N. Banis, B. Xiao, Q. Sun, A. Lushington, R. Li, J. Guo, T.-K. Sham, and X. Sun, 'Atomically precise growth of sodium titanates as anode materials for high-rate and ultralong cycle-life sodium-ion batteries,' J. Mater. Chem. A 3 (48), 24281-24288 (2015).
36. 36 L. Ma, R. B. Nuwayhid, T. Wu, Y. Lei, K. Amine, and J. Lu, 'Atomic layer deposition for lithium-based batteries,' Adv. Mater. Interfaces 3 (21), 1600564:1-1600564:15 (2016).
37. 37 A. C. Kozen, C.-F. Lin, A. J. Pearse, M. A. Schroeder, X. Han, L. Hu, S.-B. Lee, G. W. Rubloff, and M. Noked, 'Next-generation lithium metal anode engineering via atomic layer deposition,' ACS Nano 9 (6), 5884-5892 (2015).
38. 38 H. C. M. Knoops, M. E. Donders, M. C. M. van de Sanden, P. H. L. Notten, and W. M. M. Kessels, 'Atomic layer deposition for nanostructured Li-ion batteries,' J. Vac. Sci. Technol. A 30 (1), 010801:1-010801:10 (2012).
39. 39 X. Meng, X.-Q. Yang, and X. Sun, 'Emerging applications of atomic layer deposition for lithium-ion battery studies,' Adv. Mater. 24 (27), 3589-3615 (2012).
40. 40 B. J. O'Neill, D. H. K. Jackson, J. Lee, C. Canlas, P. C. Stair, C. L. Marshall, J. W. Elam, T. F. Kuech, J. A. Dumesic, and G. W. Huber, 'Catalyst design with atomic layer deposition,' ACS Catal. 5 (3), 1804-1825 (2015).
41. 41 S. Haukka, E.-L. Lakomaa, and T. Suntola, 'Adsorption controlled preparation of heterogenous catalysts,' Stud. Surf. Sci. Catal. 120 , 715-750 (1999).
42. 42 J. A. Singh, N. Yang, and S. F. Bent, 'Nanoengineering heterogeneous catalysts by atomic layer deposition,' Annu. Rev. Chem. Biomol. 8 (1), 41-62 (2017). PMID: 28301732.
43. 43 T. M. Onn, R. K € ugas, P. Fornasiero, K. Huang, and R. J. Gorte, 'Atomic layer deposition on porous materials: Problems with conventional approaches to catalyst and fuel cell electrode preparation,' Inorganics 6 (1), 34 (2018).
44. 44 K. Cao, J. Cai, X. Liu, and R. Chen, 'Review article: Catalysts design and synthesis via selective atomic layer deposition,' J. Vac. Sci. Technol. A 36 (1), 010801:1-010801:12 (2018).
45. 45 J. Dendooven, 'Atomic layer deposition in nanoporous catalyst materials,' in Atomically-Precise Methods for Synthesis of Solid Catalysts (The Royal Society of Chemistry, 2015), Chap. 7, pp. 167-197.
46. 46 R. K. Ramachandran, C. Detavernier, and J. Dendooven, Atomic Layer Deposition for Catalysis (Wiley-Blackwell, 2017), pp. 335-358.

- 47 M. A. Cameron, I. P. Gartland, J. A. Smith, S. F. Diaz, and S. M. George, 'Atomic layer deposition of SiO2 and TiO2 in alumina tubular membranes: Pore reduction and effect of surface species on gas transport,' Langmuir 16 (19), 7435-7444 (2000).
- 48 F. Li, Y. Yang, Y. Fan, W. Xing, and Y. Wang, 'Modification of ceramic membranes for pore structure tailoring: The atomic layer deposition route,' J. Membr. Sci. 397-398 , 17-23 (2012).
- 49 A. H. Brozena, C. J. Oldham, and G. N. Parsons, 'Atomic layer deposition on polymer fibers and fabrics for multifunctional and electronic textiles,' J. Vac. Sci. Technol. A 34 (1), 010801:1-010801:17 (2016).
- 50 T. O. K € a € ari € ainen, M. Kemell, M. Vehkam € aki, M. L. K € a € ari € ainen, A. Correia, H. A. Santos, L. M. Bimbo, J. Hirvonen, P. Hoppu, S. M. George, D. C. Cameron, M. Ritala, and M. Leskel € a, 'Surface modification of acetaminophen particles by atomic layer deposition,' Int. J. Pharm. 525 (1), 160-174 (2017).
- 51 V. Cremers, F. Geenen, C. Detavernier, and J. Dendooven, 'Monte Carlo simulations of atomic layer deposition on 3D large surface area structures: Required precursor exposure for pillar- versus hole-type structures,' J. Vac. Sci. Technol. A 35 (1), 01B115:1-01B115:6 (2017).
- 52 M. Knudsen, 'Die Gesetze der Molekularstr € omung und der inneren Reibungsstr € omung der Gase durch R € ohren,' Ann. Phys. 333 (1), 75-130 (1909).
- 53 J. F. O'Hanlon, A User's Guide to Vacuum Technology , 3rd ed. (Wiley, New Jersey, 2004).
- 54 Y. Shi, Y. T. Lee, and A. S. Kim, 'Knudsen diffusion through cylindrical tubes of varying radii: Theory and Monte Carlo simulations,' Transp. Porous Med. 93 (3), 517-541 (2012).
- 55 S. Chapman and T. G. Cowling, The Mathematical Theory of Non-Uniform Gases: An Account of the Kinetic Theory of Viscosity, Thermal Conduction and Diffusion in Gases (Cambridge University Press, 1970).
- 56 D. Mu ~ noz-Rojas and J. MacManus-Driscoll, 'Spatial atmospheric atomic layer deposition: A new laboratory and industrial tool for low-cost photovoltaics,' Mater. Horiz. 1 (3), 314-320 (2014).
- 57 W. M. M. Kessels and M. Putkonen, 'Advanced process technologies: Plasma, direct-write, atmospheric pressure, and roll-to-roll ALD,' MRS Bull. 36 (11), 907-913 (2011).
- 58 P. Poodt, D. C. Cameron, E. Dickey, S. M. George, V. Kuznetsov, G. N. Parsons, F. Roozeboom, G. Sundaram, and A. Vermeer, 'Spatial atomic layer deposition: A route towards further industrialization of atomic layer deposition,' J. Vac. Sci. Technol. A 30 (1), 010802:1-010801:11 (2012).
- 59 T. Suntola and J. Antson, U.S. Patent No. 4,058,430 (November 1977).
- 60 T. Suntola, A. Pakkala, and S. G. Lindfors, U.S. Patent No. 4,389,973 (28 June 1983).
- 61 A. Illiberi, F. Roozeboom, and P. Poodt, 'Spatial atomic layer deposition of zinc oxide thin films,' ACS Appl. Mater. Interfaces 4 (1), 268-272 (2012).
- 62 R. G. Gordon, D. Hausmann, E. Kim, and J. Shepard, 'A kinetic model for step coverage by atomic layer deposition in narrow holes or trenches,' Chem. Vap. Depos. 9 (2), 73-78 (2003).
- 63 S. T. Barry, A. V. Teplyakov, and F. Zaera, 'The chemistry of inorganic precursors during the chemical deposition of films on solid surfaces,' Acc. Chem. Res. 51 (3), 800-809 (2018).
- 64 F. Zaera, 'The surface chemistry of atomic layer depositions of solid,' J. Phys. Chem. Lett. 3 (10), 1301-1309 (2012).
- 65 J. W. Elam, D. Routkevitch, P. P. Mardilovich, and S. M. George, 'Conformal coating on ultrahigh-aspect-ratio nanopores of anodic alumina by atomic layer deposition,' Chem. Mater. 15 (18), 3507-3517 (2003).
- 66 H. C. M. Knoops, E. Langereis, M. C. M. van de Sanden, and W. M. M. Kessels, 'Conformality of plasma-assisted ALD: Physical processes and modeling,' J. Electrochem. Soc. 157 (12), G241-G249 (2010).
- 67 J. Dendooven, D. Deduytsche, J. Musschoot, R. L. Vanmeirhaeghe, and C. Detavernier, 'Modeling the conformality of atomic layer deposition: The effect of sticking probability,' J. Electrochem. Soc. 156 (4), P63-P67 (2009).
- 68 One order with respect to pA , the other with respect to the surface sites (1 h ), resulting in an overall reaction order of two.
- 69 J. Musschoot, J. Dendooven, D. Deduytsche, J. Haemers, G. Buyle, and C. Detavernier, 'Conformality of thermal and plasma enhanced atomic layer deposition on a non-woven fibrous substrate,' Surf. Coat. Technol. 206 (22), 4511-4517 (2012).
- 70 J. Dendooven, D. Deduytsche, J. Musschoot, R. L. Vanmeirhaeghe, and C. Detavernier, 'Conformality of Al2O3 and AlN deposited by plasma-enhanced atomic layer deposition,' J. Electrochem. Soc. 157 (4), G111-G116 (2010).
- 71 Note that, in previous works, these different growth types are referred to as growth regimes. In this review, we call these growth types to indicate a clear distinction with other growth regimes defined in the context of how the GPC changes with the number of ALD reaction cycles (i.e., initial regime, transition regime, and linear, steady regime) (Ref. 5).
- 72 The term diffusion limited may cause some confusion, because the estimated time scales for diffusion in an inert tubular structure or trench are much smaller than the exposure times typically needed to conformally coat a high aspect ratio structure by ALD. However, one should realize that in the case of ALD the reactants need to diffuse in a reactive or sticky tube instead of an inert tube meaning that the surface of the high aspect ratio structure acts as an additional loss channel in particular for reactions with a high sticking probability.
- 73 R. A. McKee, F. J. Walker, and M. F. Chisholm, 'Crystalline oxides on silicon: The first five monolayers,' Phys. Rev. Lett. 81 (14), 3014-3017 (1998).
- 74 R. Puurunen and C. Detavernier, Private Communication, May 2016, Helsinki.
- 75 T. Karabacak and T.-M. Lu, 'Enhanced step coverage by oblique angle physical vapor deposition,' J. Appl. Phys. 97 (12), 124504:1-124504:5 (2005).
- 76 S. H. Baxamusa and K. K. Gleason, 'Thin polymer films with high step coverage in microtrenches by initiated CVD,' Chem. Vap. Depos. 14 (9-10), 313-318 (2008).
- 77 M. Ylilammi, O. M. E. Ylivaara, and R. L. Puurunen, 'Modeling growth kinetics of thin films made by atomic layer deposition in lateral high-aspect-ratio structures,' J. Appl. Phys. 123 , 205301:1-205301:8 (2018).
- 78 D. M. Hausmann, E. Kim, J. Becker, and R. G. Gordon, 'Atomic layer deposition of hafnium and zirconium oxides using metal amide precursors,' Chem. Mater. 14 (10), 4350-4358 (2002).
- 79 Y. Zhu, K. A. Dunn, and A. E. Kaloyeros, 'Properties of ultrathin platinum deposited by atomic layer deposition for nanoscale copper-metallization schemes,' J. Mater. Res. 22 (5), 1292-1298 (2007).
- 80 Y. J. Lee, 'Low-impurity, highly conformal atomic layer deposition of titanium nitride using NH3-Ar-H2 plasma treatment for capacitor electrodes,' Mater. Lett. 59 (6), 615-617 (2005).
- 81 J.-M. Park, S. J. Jang, L. L. Yusup, W.-J. Lee, and S.-I. Lee, 'Plasma-enhanced atomic layer deposition of silicon nitride using a novel silylamine precursor,' ACS Appl. Mater. Interfaces 8 (32), 20865-208713 (2016).
- 82 J. Rouquerol, D. Avnir, C. W. Fairbridge, D. H. Everett, J. H. Haynes, N. Pernicone, J. D. F. Ramsay, K. S. W. Sing, and K. K. Unger, 'Recommendations for the characterization of porous solids,' Pure Appl. Chem. 66 (8), 1739-1758 (1994).
- 83 N. T. Gabriel and J. J. Talghader, 'Optical coatings in microscale channels by atomic layer deposition,' Appl. Opt. 49 (8), 1242-1248 (2010).
- 84 K. Shima, Y. Funato, H. Sugiura, N. Sato, Y. Fukushima, T. Momose, and Y. Shimogaki, 'High-aspect-ratio parallel-plate microchannels applicable to kinetic analysis of chemical vapor deposition,' Adv. Mater. Interfaces 3 (16), 1600254:1-1600254:11 (2016).
- 85 J. S. Becker, S. Suh, S. Wang, and R. G. Gordon, 'Highly conformal thin films of tungsten nitride prepared by atomic layer deposition from a novel precursor,' Chem. Mater. 15 (15), 2969-2976 (2003).
- 86 F. Gao, S. Arpiainen, and R. L. Puurunen, 'Microscopic silicon-based lateral high-aspect-ratio structures for thin film conformality analysis,' J. Vac. Sci. Technol. A 33 (1), 010601:1-010601:5 (2015).
- 87 M. Mattinen, J. H € am € al € ainen, F. Gao, P. Jalkanen, K. Mizohata, J. R € ais € anen, R. L. Puurunen, M. Ritala, and M. Leskel € a, 'Nucleation and conformality of iridium and iridium oxide thin films grown by atomic layer deposition,' Langmuir 32 (41), 10559-10569 (2016).
- 88 R. L. Puurunen and F. Gao, 'Influence of ALD temperature on thin film conformality: Investigation with microscopic lateral high-aspect-ratio structures,' in Proceedings of 14th International Baltic Conference on Atomic Layer Deposition, BALD (2016), pp. 20-24.
- 89 J. Gluch, T. R € oßler, D. Schmidt, S. B. Menzel, M. Albert, and J. Eckert, 'TEM characterization of ALD layers in deep trenches using a dedicated FIB lamellae preparation method,' Thin Solid Films 518 (16), 4553-4555 (2010).

- 90 M. Ladanov, P. Algarin-Amaris, G. Matthews, M. Ram, S. Thomas, A. Kumar, and J. Wang, 'Microfluidic hydrothermal growth of ZnO nanowires over high aspect ratio microstructures,' Nanotechnology 24 (37), 375301:1-375301:9 (2013).
- 91 J. D. Caldwell, O. J. Glembocki, F. J. Bezares, M. I. Kariniemi, J. T. Niinist € o, T. T. Hatanp € a € a, R. W. Rendell, M. Ukaegbu, M. K. Ritala, S. M. Prokes, C. M. Hosten, M. A. Leskel € a, and R. Kasica, 'Large-area plasmonic hot-spot arrays: Sub-2 nm interparticle separations with plasma-enhanced atomic layer deposition of Ag on periodic arrays of Si nanopillars,' Opt. Express 19 (27), 26056-26064 (2011).
- 92 T. Dobbelaere, F. Mattelaer, J. Dendooven, P. Vereecken, and C. Detavernier, 'Plasma-enhanced atomic layer deposition of iron phosphate as a positive electrode for 3D lithium-ion microbatteries,' Chem. Mater. 28 (10), 3435-3445 (2016).
- 93 J. C. Ye, Y. H. An, T. W. Heo, M. M. Biener, R. J. Nikolic, M. Tang, H. Jiang, and Y. M. Wang, 'Enhanced lithiation and fracture behavior of silicon mesoscale pillars via atomic layer coatings and geometry design,' J. Power Sources 248 , 447-456 (2014).
- 94 M. M. Minjauw, J. Dendooven, B. Capon, M. Schaekers, and C. Detavernier, 'Atomic layer deposition of ruthenium at 100 /C14 C using the RuO4-precursor and H2,' J. Mater. Chem. C 3 (1), 132-137 (2015).
- 95 I. Perez, E. Robertson, P. Banerjee, L. Henn-Lecordier, S. J. Son, S. B. Lee, and G. W. Rubloff, 'TEM-based metrology for HfO2 layers and nanotubes formed in anodic aluminum oxide nanopore structures,' Small 4 (8), 1223-1232 (2008).
- 96 J. W. Elam, G. Xiong, C. Y. Han, H. H. Wang, J. P. Birrell, U. Welp, J. N. Hryn, M. J. Pellin, T. F. Baumann, J. F. Poco, and J. H. Satcher, Jr., 'Atomic layer deposition for the conformal coating of nanoporous materials,' J. Nanomater. 2006 , 64501:1-64501:5 (2006).
- 97 B. H. Choi, Y. H. Lim, J. H. Lee, Y. B. Kim, H.-N. Lee, and H. K. Lee, 'Preparation of Ru thin film layer on Si and TaN/Si as diffusion barrier by plasma enhanced atomic layer deposition,' Microelectron. Eng. 87 (5-8), 1391-1395 (2010).
- 98 S. Deng, S. W. Verbruggen, Z. He, D. J. Cott, P. M. Vereecken, J. A. Martens, S. Bals, S. Lenaerts, and C. Detavernier, 'Atomic layer deposition-based synthesis of photoactive TiO2 nanoparticle chains by using carbon nanotubes as sacrificial templates,' RSC Adv. 4 (23), 11648-11653 (2014).
- 99 B. Min, J. S. Lee, J. W. Hwang, K. H. Keem, M. I. Kang, K. Cho, M. Y. Sung, S. Kim, M.-S. Lee, S. O. Park, and J. T. Moon, 'Al2O3 coating of ZnO nanorods by atomic layer deposition,' J. Cryst. Growth 252 (4), 565-569 (2003).
- 100 N. Yazdani, V. Chawla, E. Edwards, V. Wood, H. G. Park, and I. Utke, 'Modeling and optimization of atomic layer deposition processes on vertically aligned carbon nanotubes,' Beilstein J. Nanotechnol. 5 (1), 234-244 (2014).
- 101 L. Liu, S. K. Karuturi, L. T. Su, and A. I. Y. Tok, 'TiO2 inverse-opal electrode fabricated by atomic layer deposition for dye-sensitized solar cell applications,' Energy Environ. Sci. 4 (1), 209-215 (2011).
- 102 M. Scharrer, X. Wu, A. Yamilov, H. Cao, and R. P. H. Chang, 'Fabrication of inverted opal ZnO photonic crystals by atomic layer deposition,' Appl. Phys. Lett. 86 (15), 151113:1-151113:3 (2005).
- 103 L. Dong, Q.-Q. Sun, Y. Shi, H. Liu, C. Wang, S.-J. Ding, and D. W. Zhang, 'Quantum chemical study of the initial surface reactions of atomic layer deposition GaAs for photonic crystal fabrication,' Appl. Phys. Lett. 92 (11), 111105:1-111105:3 (2008).
- 104 Z. A. Sechrist, R. Piestun, and S. M. George, 'Atomic layer deposition of tungsten thin films on opals in the visible region,' AIP Conf. Proc. 992 , 507-512 (2008).
- 105 J. Dendooven, S. P. Sree, K. De Keyser, D. Deduytsche, J. A. Martens, K. F. Ludwig, and C. Detavernier, ' In situ X-ray fluorescence measurements during atomic layer deposition: nucleation and growth of TiO2,' J. Phys. Chem. C 115 (14), 6605-6610 (2011).
- 106 J. Dendooven, K. Devloo-Casier, E. Levrau, R. Van Hove, S. P. Sree, M. R. Baklanov, J. A. Martens, and C. Detavernier, ' In situ monitoring of atomic layer deposition in nanoporous thin films using ellipsometric porosimetry,' Langmuir 28 (8), 3852-3859 (2012).
- 107 C. D € ucs € o, N. Q. Khanh, Z. Horvath, I. B /C19 arsony, M. Utriainen, S. Lehto, M. Nieminen, and L. Niinist € o, 'Deposition of tin oxide into porous silicon by atomic layer epitaxy,' J. Electrochem. Soc. 143 (2), 683-687 (1996).
- 108 M. Utriainen, S. Lehto, L. Niinist € o, Cs. D € ucso, N. Q. Khanh, Z. E. Horv /C19 ath, I. B /C19 arsony, and B. P /C19 ecz, 'Porous silicon host matrix for deposition by atomic layer epitaxy,' Thin Solid Films 297 (1-2), 39-42 (1997).
- 109 J. W. Elam, J. A. Libera, T. H. Huynh, H. Feng, and M. J. Pellin, 'Atomic layer deposition of aluminum oxide in mesoporous silica gel,' J. Phys. Chem. C 114 (41), 17286-17292 (2010).
- 110 J. E. Mondloch, W. Bury, D. Fairen-Jimenez, S. Kwon, E. J. DeMarco, M. H. Weston, A. A. Sarjeant, S. T. Nguyen, P. C. Stair, R. Q. Snurr, O. K. Farha, and J. T. Hupp, 'Vapor-phase metalation by atomic layer deposition in a metalorganic framework,' J. Am. Chem. Soc. 135 , 10294-10297 (2013).
- 111 S. P. Sree, J. Dendooven, J. Jammaer, K. Masschaele, D. Deduytsche, J. D'Haen, C. E. A. Kirschhock, J. A. Martens, and C. Detavernier, 'Anisotropic atomic layer deposition profiles of TiO2 in hierarchical silica material with multiple porosity,' Chem. Mater. 24 , 2775-2780 (2012).
- 112 R. L. Puurunen, A. Root, P. Sarv, M. M. Viitanen, H. H. Brongersma, M. Lindblad, and A. O. I. Krause, 'Growth of aluminum nitride on porous alumina and silica through separate saturated gas-solid reactions of trimethylaluminum and ammonia,' Chem. Mater. 14 (2), 720-729 (2002).
- 113 A. Kyt € okivi, J.-P. Jacobs, A. Hakuli, J. Meril € ainen, and H. H. Brongersma, 'Surface characteristics and activity of chromia/alumina catalysts prepared by atomic layer epitaxy,' J. Catal. 162 (2), 190-197 (1996).
- 114 J. Dendooven, 'Modeling and in situ characterization of the conformality of atomic layer deposition in high aspect ratio structures and nanoporous materials,' Ph.D. thesis (Ghent University, Belgium, 2012).
- 115 J. Dendooven, K. Devloo-Casier, M. Ide, K. Grandfield, M. Kurttepeli, K. F. Ludwig, S. Bals, P. Van Der Voort, and C. Detavernier, 'Atomic layer deposition-based tuning of the pore size in mesoporous thin films studied by in situ grazing incidence small angle X-ray scattering,' Nanoscale 6 (24), 14991-14998 (2014).
- 116 S. Boukhalfa, K. Evanoff, and G. Yushin, 'Atomic layer deposition of vanadium oxide on carbon nanotubes for high-power supercapacitor electrodes,' Energ. Environ. Sci. 5 (5), 6872 (2012).
- 117 G. C. Rosolen, T. K. S. Wong, and M. E. Welland, 'Study of reactive ion etched nanometre size trenches using a combined scanning electron microscope and scanning tunnelling microscope,' Nanotechnology 3 , 49-53 (1992).
- 118 S. Panda, R. Ranade, and G. S. Mathad, 'Etching high aspect ratio silicon trenches,' J. Electrochem. Soc. 150 (10), G612-G616 (2003).
- 119 A. A. Ay /C19 on, R. L. Bayt, and K. S. Breuer, 'Deep reactive ion etching: A promising technology for micro- and nanosatellites,' Smart Mater. Struct. 10 (6), 1135-1144 (2001).
- 120 J. Parasuraman, A. Summanwar, F. Marty, P. Basset, D. E. Angelescu, and T. Bourouina, 'Deep reactive ion etching of sub-micrometer trenches with ultra high aspect ratio,' Microelectron. Eng. 113 , 35-39 (2014).
- 121 H. Masuda and M. Satoh, 'Fabrication of gold nanodot array using anodic porous alumina as an evaporation mask,' Jpn. J. Appl. Phys., Part 2 35 , L126-L129 (1996).
- 122 R. Zazpe, M. Knaut, H. Sopha, L. Hromadko, M. Albert, J. Prikryl, V. G € artnerov /C19 a, J. W. Bartha, and J. M. Macak, 'Atomic layer deposition for coating of high aspect ratio TiO2 nanotube layers,' Langmuir 32 (41), 10551-10558 (2016).
- 123 S. K. Chakarvarti, 'Track-etch membranes enabled nano-/microtechnology: A review,' Radiat. Meas. 44 (9-10), 1085-1092 (2009).
- 124 G. Triani, P. J. Evans, D. J. Attard, K. E. Prince, J. Bartlett, S. Tan, and R. P. Burford, 'Nanostructured TiO2 membranes by atomic layer deposition,' J. Mater. Chem. 16 (14), 1355-1359 (2006).
- 125 L. Sainiemi, T. Nissil € a, V. Jokinen, T. Sikanen, T. Kotiaho, R. Kostiainen, R. A. Ketola, and S. Franssila, 'Fabrication and fluidic characterization of silicon micropillar array electrospray ionization chip,' Sens. Actuator B 132 (2), 380-387 (2008).
- 126 K. L. Stano, M. Carroll, R. Padbury, M. McCord, J. S. Jur, and P. D. Bradford, 'Conformal atomic layer deposition of alumina on millimeter tall, verticallyaligned carbon nanotube arrays,' ACS Appl. Mater. Interfaces 6 (21), 19135-19143 (2014).
- 127 Y. Yang, S. Jayaraman, D. Y. Kim, G. S. Girolami, and J. R. Abelson, 'CVD growth kinetics of HfB2 thin films from the single-source precursor Hf(BH4)4,' Chem. Mater. 18 (21), 5088-5096 (2006).

- 128 M. C. Schwille, T. Sch € ossler, J. Barth, M. Knaut, F. Sch € on, A. H € ochst, M. Oettel, and J. W. Bartha, 'Experimental and simulation approach for process optimization of atomic layer deposited thin films in high aspect ratio 3D structures,' J. Vac. Sci. Technol. A 35 (1), 01B118:1-01B118:10 (2017).
- 129 M. C. Schwille, J. Barth, T. Sch € ossler, F. Sch € on, J. W. Bartha, and M. Oettel, 'Simulation approach of atomic layer deposition in large 3D structures,' Modell. Simul. Mater. Sci. Eng. 25 , 035008:1-035008:18 (2017).
- 130 M. E. Davie, T. Foerster, S. Parsons, C. Pulham, D. W. H. Rankin, and B. A. Smart, 'The crystal structure of tetrakis(dimethylamino)titanium(IV),' Polyhedron 25 (4), 923-929 (2006).
- 131 S. P. Sree, J. Dendooven, L. Geerts, R. K. Ramachandran, E. Javon, F. Ceyssens, E. Breynaert, C. E. A. Kirschhock, R. Puers, T. Altantzis, G. Van Tendeloo, S. Bals, C. Detavernier, and J. A. Martens, '3D porous nanostructured platinum prepared using atomic layer deposition,' J. Mater. Chem. A 5 (36), 19007-19016 (2017).
- 132 K. Leus, C. Krishnaraj, L. Verhoeven, V. Cremers, J. Dendooven, R. K. Ramachandran, P. Dubruel, and P. Van Der Voort, 'Catalytic carpets: Pt@MIL-101@electrospun PCL, a surprisingly active and robust hydrogenation catalyst,' J. Catal. 360 , 81-88 (2018).
- 133 S. Haukka, 'Future applications and challenges for ALD in microelectronics,' in AVS 17th International Conference on Atomic Layer Deposition (ALD 2017), Denver, 2017. (Invited oral presentation).
- 134 M. Ritala, M. Leskel € a, J. P. Dekker, C. Mutsaers, P. J. Soininen, and J. Skarp, 'Perfectly conformal TiN and Al2O3 films deposited by atomic layer deposition,' Chem. Vap. Depos. 5 (1), 7-9 (1999).
- 135 G. Pardon, H. K. Gatty, G. Stemme, W. Van der Wijngaart, and N. Roxhed, 'Pt-Al2O3 dual layer atomic layer deposition coating in high aspect ratio nanopores,' Nanotechnology 24 (1), 015602:1-015602:11 (2013).
- 136 50-200 nm diameter, 20-30 l mheight.
- 137 2 l mdiameter, 50 l mheight, and 2 l mspacing.
- 138 M. Knaut, M. Junige, V. Neumann, H. Wojcik, T. Henke, C. Hossbach, A. Hiess, M. Albert, and J. W. Bartha, 'Atomic layer deposition for high aspect ratio through silicon vias,' Microelectron. Eng. 107 , 80-83 (2013).
- 139 P. Poodt, A. Mameli, J. Schulpen, W. M. M. Kessels, and F. Roozeboom, 'Effect of reactor pressure on the conformal coating inside porous substrates by atomic layer deposition,' J. Vac. Sci. Technol. A 35 (2), 021502:1-021502:9 (2017).
- 140 Z. Yao, C. Wang, Y. Li, and N.-Y. Kim, 'AAO-assisted synthesis of highly ordered, large-scale TiO2 nanowire arrays via sputtering and atomic layer deposition,' Nanoscale Res. Lett. 10 (1), 166 (2015).
- 141 X. Li, M. Puttaswamy, Z. Wang, C. K. Tan, A. C. Grimsdale, N. P. Kherani, and A. I. Y. Tok, 'A pressure tuned stop-flow atomic layer deposition process for MoS2 on high porous nanostructure and fabrication of TiO2/MoS2 core/ shell inverse opal structure,' Appl. Surf. Sci. 422 , 536-543 (2017).
- 142 6.3 nm diameter and 50-90 l mheight.
- 143 J. Bachmann, J. Jing, M. Knez, S. Barth, H. Shen, S. Mathur, U. G € osele, and K. Nielsch, 'Ordered iron oxide nanotube arrays of controlled geometry and tunable magnetism by atomic layer deposition,' J. Am. Chem. Soc. 129 (31), 9554-9555 (2007).
- 144 Y. Zhang, M. Liu, B. Peng, Z. Zhou, X. Chen, S.-M. Yang, Z.-D. Jiang, J. Zhang, W. Ren, and Z.-G. Ye, 'Controlled phase and tunable magnetism in ordered iron oxide nanotube arrays prepared by atomic layer deposition,' Sci. Rep. 6 , 18401:1-18401:8 (2016).
- 145 230 nm diameter and 1.2 l mheight.
- 146 W. N. Wang, F. Wu, Y. Myung, D. M. Niedzwiedzki, H. S. Im, J. Park, P. Banerjee, and P. Biswas, 'Surface engineered CuO nanowires with ZnO islands for CO2 photoreduction,' ACS Appl. Mater. Interfaces 7 (10), 5685-5692 (2015).
- 147 30-50 nm inner diameter and 70-100 nm height.
- 148 Y.-S. Min, E. J. Bae, K. S. Jeong, Y. J. Cho, J.-H. Lee, W. B. Choi, and G.-S. Park, 'Ruthenium oxide nanotube arrays fabricated by atomic layer deposition using a carbon nanotube template,' Adv. Mater. 15 (12), 1019-1022 (2003).
- 149 M. Weber, B. Koonkaew, S. Balme, I. Utke, F. Picaud, I. Iatsunskyi, E. Coy, P. Miele, and M. Bechelany, 'Boron nitride nanoporous membranes with high surface charge by atomic layer deposition,' ACS Appl. Mater. Interfaces 9 (19), 16669-16678 (2017).
- 150 X. Liu, S. Ramanathan, E. Lee, and T. E. Seidel, in Atomic Layer Deposition of Aluminum Nitride Thin Films From Trimethyl Aluminum (TMA) and Ammonia (Mater. Res. Soc. Proc., 2004), Vol. 811, pp. 1-816.
- 151 S.-H. Choi, T. Cheon, S.-H. Kim, D.-H. Kang, G.-S. Park, and S. Kim, 'Thermal atomic layer deposition (ALD) of Ru films for Cu direct plating,' J. Electrochem. Soc. 158 (6), D351-D356 (2011).
- 152 Deposition at 310 /C14 C resulted in a step coverage of 75% (bottom-top).
- 153 T.-K. Eom, W. Sari, K.-J. Choi, W.-C. Shin, J. H. Kim, D.-J. Lee, K.-B. Kim, H. Sohn, and S.-H. Kim, 'Low temperature atomic layer deposition of ruthenium thin films using isopropylmethylbenzene-cyclohexadiene-ruthenium and O2,' Electrochem. Solid State 12 (11), D85-D88 (2009).
- 154 W. H. Kim, S. J. Park, J. Y. Son, and H. Kim, 'Ru nanostructure fabrication using an anodic aluminum oxide nanotemplate and highly conformal Ru atomic layer deposition,' Nanotechnology 19 (4), 045302:1-045302:8 (2008).
- 155 By increasing the Ar gas flow rate, one observed a decrease in the step coverage.
- 156 S. K. Kim, S. Y. Lee, S. W. Lee, G. W. Hwang, C. S. Hwang, J. W. Lee, and J. Jeong, 'Atomic layer deposition of Ru thin films using 2,4(dimethylpentadienyl)(ethylcyclopentadienyl)Ru by a liquid injection system,' J. Electrochem. Soc. 154 (2), D95-D101 (2007).
- 157 S. Yeo, S.-H. Choi, J.-Y. Park, S.-H. Kim, T. Cheon, B.-Y. Lim, and S. Kim, 'Atomic layer deposition of ruthenium (Ru) thin films using ethylbenzencyclohexadiene Ru(0) as a seed layer for copper metallization,' Thin Solid Films 546 , 2-8 (2013).
- 158 T. E. Hong, S.-H. Choi, S. Yeo, J.-Y. Park, S.-H. Kim, T. Cheon, H. Kim, M.-K. Kim, and H. Kim, 'Atomic layer deposition of Ru thin films using a Ru(0) metallorganic precursor and O2,' ECS J. Solid State Sci. 2 (3), P47-P53 (2012).
- 159 C. Liu, E. I. Gillette, X. Chen, A. J. Pearse, A. C. Kozen, M. A. Schroeder, K. E. Gregorczyk, S. B. Lee, and G. W. Rubloff, 'An all-in-one nanopore battery array,' Nat. Nanotechnol. 9 (12), 1031-1039 (2014).
- 160 K. Kukli, M. Kemell, E. Puukilainen, J. Aarik, A. Aidla, T. Sajavaara, M. Laitinen, M. Tallarida, J. Sundqvist, M. Ritala, and M. Leskel € a, 'Atomic layer deposition of ruthenium films from (ethylcyclopentadienyl)(pyrrolyl)ruthenium and oxygen,' J. Electrochem. Soc. 158 (3), D158-D165 (2011).
- 161 O.-K. Kwon, J.-H. Kim, H.-S. Park, and S.-W. Kang, 'Atomic layer deposition of ruthenium thin films for copper glue layer,' J. Electrochem. Soc. 151 (2), G109-G112 (2004).
- 162 D.-J. Lee, S.-S. Yim, K.-S. Kim, S.-H. Kim, and K.-B. Kim, 'Formation of Ru nanotubes by atomic layer deposition onto an anodized aluminum oxide template,' Electrochem. Solid State 11 (6), K61-K63 (2008).
- 163 2 l mwidth, 50 l mheight, and 4 l mcenter-to-center distance.
- 164 J. W. Elam, A. Zinovev, C. Y. Han, H. H. Wang, U. Welp, J. N. Hryn, and M. J. Pellin, 'Atomic layer deposition of palladium films on Al2O3 surfaces,' Thin Solid Films 515 (4), 1664-1673 (2006).
- 165 Exposure of WF6 is the limiting factor.
- 166 J. W. Elam, J. A. Libera, M. J. Pellin, A. V. Zinovev, J. P. Greene, and J. A. Nolen, 'Atomic layer deposition of W on nanoporous carbon aerogels,' Appl. Phys. Lett. 89 (5), 053124:1-053124:3 (2006).
- 167 A step coverage of 75% was achieved, using a special flow-through approach. Ir(acac) 3 was pulsed two times in each ALD cycle. Both pulses were seperated by a purge step.
- 168 T. Pilvi, 'Atomic layer deposition for optical applications: Metal fluoride thin films and novel devices,' Ph.D. thesis (University of Helsinki, Finland, 2008).
- 169 J. Vila-Comamala, L. Romano, V. Guzenko, M. Kagias, M. Stampanoni, and K. Jefimovs, 'Towards sub-micrometer high aspect ratio X-ray gratings by atomic layer deposition of iridium,' Microelectron. Eng. 192 , 19-24 (2018).
- 170 Along the entire depth of the AAO structure, Pt was deposited. Lower or higher deposition temperatures lead to a decrease of the penetration depth.
- 171 A. Vaish, S. Krueger, M. Dimitriou, C. Majkrzak, D. J. Vanderah, L. Chen, and K. Gawrisch, 'Enhancing the platinum atomic layer deposition infiltration depth inside anodic alumina nanoporous membrane,' J. Vac. Sci. Technol. A 33 (1), 01A148 (2015).
- 172 D. J. Comstock, S. T. Christensen, J. W. Elam, M. J. Pellin, and M. C. Hersam, 'Tuning the composition and nanostructure of Pt/Ir films via anodized aluminum oxide templated atomic layer deposition,' Adv. Funct. Mater. 20 (20), 3099-3105 (2010).
- 173 D. Gu, H. Baumgart, K. Tapily, P. Shrestha, G. Namkoong, X. Ao, and F. M € uller, 'Precise control of highly ordered arrays of nested semiconductor/ metal nanotubes,' Nano Res. 4 (2), 164-170 (2011).

- 174 S. T. Christensen and J. W. Elam, 'Atomic layer deposition of Ir-Pt alloy films,' Chem. Mater. 22 (8), 2517-2525 (2010).
- 175 The step-coverage (bottom-top) increased from 75% to 100% by increasing the deposition temperature, explained by the temperature dependence of the sticking coefficient for O 3 .
- 176 G. Prechtl, A. Kersch, G. S. Icking-Konert, W. Jacobs, T. Hecht, H. Boubekeur, and U. Schroder, 'A model for Al2O3 ALD conformity and deposition rate from oxygen precursor reactivity,' Tech. Dig.-Int Electron Devices. Meet. 2003 , 9.6.1.
- 177 J. Lee, S. Farhangfar, R. Yang, R. Scholz, M. Alexe, U. G € osele, J. Lee, and K. Nielsch, 'A novel approach for fabrication of bismuth-silicon dioxide coreshell structures by atomic layer deposition,' J. Mater. Chem. 19 (38), 7050-7054 (2009).
- 178 M. Rose and J. W. Bartha, 'Applied surface science method to determine the sticking coefficient of precursor molecules in atomic layer deposition,' Appl. Surf. Sci. 255 , 6620-6623 (2009).
- 179 10 nm diameter and 6 l mlength.
- 180 M. Rose, J. W. Bartha, and I. Endler, 'Temperature dependence of the sticking coefficient in atomic layer deposition,' Appl. Surf. Sci. 256 (12), 3778-3782 (2010).
- 181 A. B. F. Martinson, M. J. DeVries, J. A. Libera, S. T. Christensen, J. T. Hupp, M. J. Pellin, and J. W. Elam, 'Atomic layer deposition of Fe2O3 using ferrocene and ozone,' J. Phys. Chem. C 115 (10), 4333-4339 (2011).
- 182 L. Steier, J. Luo, M. Schreier, M. T. Mayer, T. Sajavaara, and M. Gr € atzel, 'Lowtemperature atomic layer deposition of crystalline and photoactive ultrathin hematite films for solar water splitting,' ACS Nano 9 (12), 11775-11783 (2015).
- 183 Porous alumina membranes.
- 184 M. Diskus, O. Nilsen, and H. Fjellvag, 'Thin films of cobalt oxide deposited on high aspect ratio supports by atomic layer deposition,' Chem. Vap. Depos. 17 (4-6), 135-140 (2011).
- 185 M. K. S. Barr, L. Assaud, Y. Wu, C. Laffon, P. Parent, J. Bachmann, and L. Santinacci, 'Engineering a three-dimensional, photoelectrochemically active p-NiO/i-Sb2S3 junction by atomic layer deposition,' Electrochim. Acta 179 , 504-511 (2015).
- 186 A. Pereira, J. L. Palma, J. C. Denardin, and J. Escrig, 'Temperature-dependent magnetic properties of Ni nanotubes synthesized by atomic layer deposition,' Nanotechnology 27 (34), 345709:1-345709:6 (2016).
- 187 K. Sharma, D. Routkevitch, N. Varaksa, and S. M. George, 'Spatial atomic layer deposition on flexible porous substrates: ZnO on anodic aluminum oxide films and Al2O3 on Li ion battery electrodes,' J. Vac. Sci. Technol. A 34 (1), 01A146:1-01A146:10 (2016).
- 188 Cylindrical pores made of polystyrene.
- 189 C. H. Lin, S. Polisetty, L. O'Brien, A. Baruth, M. A. Hillmyer, C. Leighton, and W. L. Gladfelter, 'Size-tuned ZnO nanocrucible arrays for magnetic nanodot synthesis via atomic layer deposition-assisted block polymer lithography,' ACS Nano 9 (2), 1379-1387 (2015).
- 190 The film thickness was calculated as Ir because based on the optical images, one expected a change in composition to metallic iridium.
- 191 J. H € am € al € ainen, F. Munnik, M. Ritala, and M. Leskel € a, 'Atomic layer deposition of platinum oxide and metallic platinum thin films from pt(acac)2 and Ozone,' Chem. Mater. 20 (21), 6840-6846 (2008).
- 192 J. H € am € al € ainen, E. Puukilainen, M. Kemell, L. Costelle, M. Ritala, and M. Leskel € a, 'Atomic layer deposition of iridium thin films by consecutive oxidation and reduction steps,' Chem. Mater. 21 (20), 4868-4872 (2009).
- 193 Ru step coverage (bottom-top) of 80%.
- 194 J.-Y. Kim, D.-S. Kil, J.-H. Kim, S.-H. Kwon, J.-H. Ahn, J.-S. Roh, and S.-K. Park, 'Ru Films from Bis(ethylcyclopentadienyl)ruthenium using ozone as a reactant by atomic layer deposition for capacitor electrodes,' J. Electrochem. Soc. 159 (6), H560-H564 (2012).
- 195 J. Dendooven, R. K. Ramachandran, K. Devloo-Casier, G. Rampelberg, M. Filez, H. Poelman, G. B. Marin, E. Fonda, and C. Detavernier, 'Low-temperature atomic layer deposition of platinum using (methylcyclopentadienyl)trimethylplatinum and ozone,' J. Phys. Chem. C 117 (40), 20557-20561 (2013).
- 196 L. Assaud, J. Schumacher, A. Tafel, S. Bochmann, S. Christiansen, and J. Bachmann, 'Systematic increase of electrocatalytic turnover at nanoporous
- platinum surfaces prepared by atomic layer deposition,' J. Mater. Chem. A 3 (16), 8450-8458 (2015).
- 197 J. L. van Hemmen, S. B. S. Heil, J. H. Klootwijk, F. Roozeboom, C. J. Hodson, M. C. M. van de Sanden, and W. M. M. Kessels, 'Plasma and thermal ALD of Al2O3 in a commercial 200 mm ALD reactor,' J. Electrochem. Soc. 154 (7), G165-G169 (2007).
- 198 M. Kariniemi, J. Niinist € o, M. Vehkam € aki, M. Kemell, M. Ritala, M. Leskel € a, and M. Putkonen, 'Conformality of remote plasma-enhanced atomic layer deposition processes: An experimental study,' J. Vac. Sci. Technol. A 30 (1), 01A115:1-01A115:5 (2012).
- 199 Macroscopic structure was filled with non-woven fibers to investigate the penetration depth of the ALD process in fibrous material.
- 200 J.-Y. Kim, J.-H. Ahn, S.-W. Kang, and J.-H. Kim, 'Step coverage modeling of thin films in atomic layer deposition,' J. Appl. Phys. 101 (7), 073502:1-073502:7 (2007).
- 201 S.-W. Choi, C.-M. Jang, D.-Y. Kim, J.-S. Ha, H.-S. Park, W. Koh, and C.-S. Lee, 'Plasma enhanced atomic layer deposition of Al2O3 and TiN,' J. Korean Phys. Soc. 42 , S975-S979 (2003).
- 202 G. Dingemans, C. A. A. van Helvoirt, D. Pierreux, W. Keuning, and W. M. M. Kessels, 'Plasma-assisted ALD for the conformal deposition of SiO2: Process, material and electronic properties,' J. Electrochem. Soc. 159 (3), H277-H285 (2012).
- 203 Y. Miyano, R. Narasaki, T. Ichikawa, A. Fukumoto, F. Aiso, and N. Tamaoki, 'Multiscale modeling for SiO2 atomic layer deposition for high-aspect-ratio hole patterns,' Jpn. J. Appl. Phys., Part 1 57 , 06JB03:1-06JB03:4 (2018).
- 204 J.-Y. Kim, J.-H. Kim, J.-H. Ahn, P.-K. Park, and S.-W. Kang, 'Applicability of step-coverage modeling to TiO2 thin films in atomic layer deposition,' J. Electrochem. Soc. 154 (12), H1008-H1013 (2007).
- 205 N. G. Kubala, P. C. Rowlette, and C. A. Wolden, 'Plasma-Enhanced Atomic Layer Deposition of Anatase TiO2 Using TiCl4,' J. Phys. Chem. C Lett. 113 (37), 16307-16310 (2009).
- 206 A. Niskanen, U. Kreissig, M. Leskel € a, and M. Ritala, 'Radical enhanced atomic layer deposition of tantalum oxide,' Chem. Mater. 19 (9), 2316-2320 (2007).
- 207 Here, the reactant pulse time is the limiting factor. Therefore, we calculate the exposure of the reactant pulse.
- 208 R. A. Ovanesyan, D. M. Hausmann, and S. Agarwal, 'Low-temperature conformal atomic layer deposition of SiNx films using Si2Cl6 and NH3 plasma,' ACS Appl. Mater. Interfaces 7 (20), 10806-10813 (2015).
- 209 At the bottom 80% and at the sidewalls 73% of the original film thickness.
- 210 J. Y. Kim, D. Y. Kim, H. O. Park, and H. Jeon, 'Characteristics and compositional variation of TiN films deposited by remote PEALD on contact holes,' J. Electrochem. Soc. 152 (1), G29-G34 (2005).
- 211 J. Yoon, S. Kim, and K. No, 'Highly ordered and well aligned TiN nanotube arrays fabricated via template-assisted atomic layer deposition,' Mater. Lett. 87 , 124-126 (2012).
- 212 S. Farsinezhad, T. Shanavas, N. Mahdi, A. M. Askar, P. Kar, H. Sharma, and K. Shankar, 'Core-shell titanium dioxide-titanium nitride nanotube arrays with near-infrared plasmon resonances,' Nanotechnology 29 (15), 154006 (2018).
- 213 H. C. M. Knoops, 'Atomic layer deposition: From reaction mechanisms to 3D integrated micro batteries,' Ph.D. thesis (Technische Universiteit Eindhoven, Netherlands, 2011).
- 214 Mo2N step coverage (bottom-top) of 80%.
- 215 Y. Jang, J. B. Kim, T. E. Hong, S. J. Yeo, S. Lee, E. A. Jung, B. K. Park, T.-M. Chung, C. G. Kim, D.-J. Lee, H.-B.-R. Lee, and S.-H. Kim, 'Highly-conformal nanocrystalline molybdenum nitride thin films by atomic layer deposition as a diffusion barrier against Cu,' J. Alloys Compd. 663 , 651-658 (2016).
- 216 J.-S. Park, H.-S. Park, and S.-W. Kang, 'Plasma-enhanced atomic layer deposition of Ta-N thin films,' J. Electrochem. Soc. 149 (1), C28-C32 (2002).
- 217 D.-K. Kim, B.-H. Kim, H.-G. Woo, D.-H. Kim, and H. K. Shin, 'Preparation of TaN thin film by H2 plasma assisted atomic layer deposition using tertbutylimino-tris-ethylmethylamino tantalum,' J. Nanosci. Nanotechnol. 6 (11), 3392-3395 (2006).
- 218 H. Kim, C. Detavernier, O. van der Straten, S. M. Rossnagel, A. J. Kellock, and D.-G. Park, 'Robust TaNx diffusion barrier for Cu-interconnect technology

- with subnanometer thickness by metal-organic plasma-enhanced atomic layer deposition,' J. Appl. Phys. 98 , 014308:1-014308:8 (2005).
- 219 Step coverage (bottom-top) of 85%. Lower temperature resulted in worse conformality.
- 220 H. Shimizu, K. Sakoda, T. Momose, M. Koshi, and Y. Shimogaki, 'Hot-wireassisted atomic layer deposition of a high quality cobalt film using cobaltocene: Elementary reaction analysis on NHx radical formation,' J. Vac. Sci. Technol. A 30 (1), 01A144:1-01A144:7 (2012).
- 221 J. Chae, H.-S. Park, and S-w Kang, 'Atomic layer deposition of nickel by the reduction of preformed nickel oxide,' Electrochem. Solid State 5 (6), C64-C66 (2002).
- 222 L. Wu and E. Eisenbraun, 'Integration of atomic layer deposition-grown copper seed layers for Cu electroplating applications,' J. Electrochem. Soc. 156 (9), H734-H739 (2009).
- 223 Films deposited on Si/TaN covered trenches had better step coverage (bottom-top) (92%) than on Si trenches (82%).
- 224 Films deeper in the trench were formed by silver grains and formed no longer a continuous film. Films deposited on SiO2 trenches had better conformality than on TiN covered trenches.
- 225 A. Niskanen, T. Hatanp € a € a, K. Arstila, M. Leskel € a, and M. Ritala, 'Radicalenhanced atomic layer deposition of silver thin films using phosphineadducted silver carboxylates,' Chem. Vap. Depos. 13 (8), 408-413 (2007).
- 226 B. R € osner, F. Koch, F. D € oring, J. Bosgra, V. A. Guzenko, E. Kirk, M. Meyer, J. L. Ornelas, R. H. Fink, S. Stanescu, S. Swaraj, R. Belkhou, B. Watts, J. Raabe, and C. David, 'Exploiting atomic layer deposition for fabricating sub-10 nm X-ray lenses,' Microelectron. Eng. 191 , 91-96 (2018).
- 227 Depending on the oxygen plasma pulse time, one can either deposit Pt or PtO2.
- 228 I. J. M. Erkens, M. A. Verheijen, H. C. M. Knoops, W. Keuning, F. Roozeboom, and W. M. M. Kessels, 'Plasma-assisted atomic layer deposition of conformal Pt films in high aspect ratio trenches,' J. Chem. Phys. 146 , 052818:1-052818:8 (2017).
- 229 S. M. Rossnagel, A. Sherman, and F. Turner, 'Plasma-enhanced atomic layer deposition of Ta and Ti for interconnect diffusion barriers,' J. Vac. Sci. Technol. B 18 (4), 2016-2020 (2000).
- 230 A. M. Lankhorst, B. D. Paarhuis, H. J. C. M. Terhorst, P. J. P. M. Simons, and C. R. Kleijn, 'Transient ALD simulations for a multi-wafer reactor with trenched wafers,' Surf. Coat. Technol. 201 (22-23), 8842-8848 (2007).
- 231 N. P. Dasgupta, X. Meng, J. W. Elam, and A. B. F. Martinson, 'Atomic layer deposition of metal sulfide materials,' Acc. Chem. Res. 48 (2), 341-348 (2015).
- 232 A. W. Peters, Z. Li, O. K. Farha, and J. T. Hupp, 'Atomically precise growth of catalytically active cobalt sulfide on flat surfaces and within a metal-organic framework via atomic layer deposition,' ACS Nano 9 (8), 8484-8490 (2015).
- 233 M. F. J. Vos, H. C. M. Knoops, R. A. Synowicki, W. M. M. Kessels, and A. J. M. Mackus, 'Atomic layer deposition of aluminum fluoride using Al(CH3)3 and SF6 plasma,' Appl. Phys. Lett. 111 (11), 113105:1-113105:5 (2017).
- 234 T. Dobbelaere, F. Mattelaer, A. K. Roy, P. Vereecken, and C. Detavernier, 'Plasma-enhanced atomic layer deposition of titanium phosphate as an electrode for lithium-ion batteries,' J. Mater. Chem. A 5 , 330-338 (2017).
- 235 C. Soto and W. T. Tysoe, 'The reaction pathway for the growth of alumina on high surface area alumina and in ultrahigh vacuum by a reaction between trimethyl aluminum and water,' J. Vac. Sci. Technol. A 9 , 2686-2695 (1991).
- 236 F. Greer, D. Fraser, J. W. Coburn, and D. B. Graves, 'Fundamental beam studies of radical enhanced atomic layer deposition of TiN,' J. Vac. Sci. Technol. A 21 (1), 96-105 (2003).
- 237 V. Vandalon and W. M. M. Kessels, 'What is limiting low-temperature atomic layer deposition of Al2O3? A vibrational sumfrequency generation study,' Appl. Phys. Lett. 108 , 011607:1-011607:5 (2016).
- 238 V. Vandalon and W. M. M. Kessels, 'Revisiting the growth mechanism for atomic layer deposition of al 2 o3: A vibrational sum-frequency generation study,' J. Vac. Sci. Technol. A 35 , 05C313:1-05C313:14 (2017).
- 239 J. W. Klaus, A. W. Ott, J. M. Johnson, and S. M. George, 'Atomic layer controlled growth of SiO2 films using binary reaction sequence chemistry,' Appl. Phys. Lett. 70 (9), 1092-1094 (1997).
- 240 The reaction of H2O with the first CH3 group in the Al(CH3)2 surface species is found to proceed rapidly (sticking probability of 0.25) versus a ca. 30 times slower reaction with the second CH3 group (sticking probability of 0.009).
- 241 H. C. M. Knoops, J. W. Elam, J. A. Libera, and W. M. M. Kessels, 'Surface loss in ozone-based atomic layer deposition processes,' Chem. Mater. 23 (9), 2381-2387 (2011).
- 242 W. T. Tsai, C. Y. Chang, F. H. Jung, C. Y. Chiu, W. H. Huang, Y. H. Yu, H. T. Liou, Y. Ku, J. N. Chen, and C. F. Mao, 'Catalytic decomposition of ozone in the presence of water vapor,' J. Environ. Sci. Heal. A 33 (8), 1705-1717 (1998).
- 243 P. K. Mogili, P. D. Kleiber, M. A. Young, and V. H. Grassian, 'Heterogeneous uptake of ozone on reactive components of mineral dust aerosol: An environmental aerosol reaction chamber study,' J. Phys. Chem. A 110 (51), 13799-13807 (2006).
- 244 A. Delabie, M. Caymax, S. Gielis, J. W. Maes, L. Nyns, M. Popovici, J. Swerts, H. Tielens, J. Peeters, and S. Van Elshocht, 'Ozone-based metal oxide atomic layer deposition: Impact of N2/O2 supply ratio in ozone generation,' Electrochem. Solid State 13 (2), H176-H178 (2010).
- 245 H. B. Profijt, S. E. Potts, M. C. M. van de Sanden, and W. M. M. Kessels, 'Plasma-assisted atomic layer deposition: Basics, opportunities, and challenges,' J. Vac. Sci. Technol. A 29 (5), 050801:1-050801:26 (2011).
- 246 A. Niskanen, K. Arstila, M. Ritala, and M. Leskel € a, 'Low-temperature deposition of aluminum oxide by radical enhanced atomic layer deposition,' J. Electrochem. Soc. 152 (7), F90-F93 (2005).
- 247 S. Sioncke, A. Delabie, G. Brammertz, T. Conard, A. Franquet, M. Caymax, A. Urbanzcyk, M. Heyns, M. Meuris, J. L. van Hemmen, W. Keuning, and W. M. M. Kessels, 'Thermal and plasma enhanced atomic layer deposition of Al2O3 on GaAs substrates,' J. Electrochem. Soc. 156 (4), H255-H262 (2009).
- 248 E. Langereis, M. Creatore, S. B. S. Heil, M. C. M. Van De Sanden, and W. M. M. Kessels, 'Plasma-assisted atomic layer deposition of Al2O3 moisture permeation barriers on polymers,' Appl. Phys. Lett. 89 (8), 081915:1-081915:3 (2006).
- 249 G. A. Ten Eyck, S. Pimanpang, J. S. Juneja, H. Bakhru, T.-M. Lu, and G.-C. Wang, 'Plasma-enhanced atomic layer deposition of palladium on a polymer substrate,' Chem. Vap. Depos. 13 (6-7), 307-311 (2007).
- 250 J. C. Greaves and J. W. Linnett, 'The recombination of oxygen atoms at surfaces,' Trans. Faraday Soc. 54 , 1323-1330 (1958).
- 251 C. Guyon, S. Cavadias, I. Mabille, M. Moscosa-Santillan, and J. Amouroux, 'Recombination of oxygen atomic excited states produced by non-equilibrium RF plasma on different semiconductor materials: Catalytic phenomena and modelling,' Catal. Today 89 (1-2), 159-167 (2004).
- 252 G. Cartry, X. Duten, and A. Rousseau, 'Atomic oxygen surface loss probability on silica in microwave plasmas studied by a pulsed induced fluorescence technique,' Plasma Sources Sci. Technol. 15 (3), 479-488 (2006).
- 253 U. Cvelbar, M. Mozetic ˇ, and A. Ricard, 'Characterization of Oxygen Plasma With A Fiber Optic Catalytic Probe And Determination Of Recombination Coefficients,' IEEE Trans. Plasma Sci. 33 (2), 834-837 (2005).
- 254 I. /C20 Sorli and R. Roc ˇak, 'Determination of atomic oxygen density with a nickel catalytic probe,' J. Vac. Sci. Technol. A 18 (2), 338-342 (2000).
- 255 P. Macko, P. Veis, and G. Cernogora, 'Study of oxygen atom recombination on a Pyrex surface at different wall temperatures by means of time-resolved actinometry in a double pulse discharge technique,' Plasma Sources Sci. Technol. 13 (2), 251-262 (2004).
- 256 M. Mozetic ˇ and A. Zalar, 'Recombination of neutral oxygen atoms on stainless steel surface,' Appl. Surf. Sci. 158 (3-4), 263-267 (2000).
- 257 S. F. Adams and T. A. Miller, 'Surface and volume loss of atomic nitrogen in a parallel plate rf discharge reactor,' Plasma Sources Sci. Technol. 9 , 248-255 (2000).
- 258 E. Es-Sebbar, Y. Benilan, A. Jolly, and M. C. Gazeau, 'Characterization of an N2 flowing microwave post-discharge by OES spectroscopy and determination of absolute ground-state nitrogen atom densities by TALIF,' J. Phys. D: Appl. Phys. 42 (13), 135206:1-135206:11 (2009).
- 259 B. J. Wood and H. Wise, 'Kinetics of hydrogen recombination on surfaces,' J. Phys. Chem. 65 , 1976-1983 (1961).
- 260 A. D. Tserepi and T. A. Miller, 'Two-photon absorption laser-induced fluorescence of H atoms: A probe for heterogeneous processes in hydrogen plasmas,' J. Appl. Phys. 75 (11), 7231-7236 (1994).
- 261 R. K. Grubbs and S. M. George, 'Attenuation of hydrogen radicals traveling under flowing gas conditions through tubes of different materials,' J. Vac. Sci. Technol. A 24 (3), 486-496 (2006).

- 262 A. Bouchoule and P. Ranson, 'Study of volume and surface processes in low pressure radio frequency plasma reactors by pulsed excitation methods. I. Hydrogen-argon plasma,' J. Vac. Sci. Technol. A 9 (2), 317-326 (1991).
- 263 J. Abrefah and D. R. Olander, 'Reaction of atomic hydrogen with crystalline silicon,' Surf. Sci. 209 (3), 291-313 (1989).
- 264 A. Yanguas-Gil and J. W. Elam, 'A Markov chain approach to simulate atomic layer deposition chemistry and transport inside nanostructured substrates,' Theor. Chem. Acc. 133 , 1465:1-1465:13 (2014).
- 265 P. Clausing, 'Uber die Str € omung sehr verd € unnter Gase durch R € ohren von beliebiger L € ange,' Ann. Phys. 404 (8), 961-989 (1932).
- 266 R. A. Adomaitis, 'A ballistic transport and surface reaction model for simulating atomic layer deposition processes in high-aspect-ratio nanopores,' Chem. Vap. Depos. 17 (10-12), 353-365 (2011).
- 267 T. S. Cale and G. B. Raupp, 'A unified line-of-sight model of deposition in rectangular trenches,' J. Vac. Sci. Technol. B 8 (6), 1242-1248 (1990).
- 268 T. S. Cale, 'Flux distributions in low pressure deposition and etch models,' J. Vac. Sci. Technol. B 9 (5), 2551-2553 (1991).
- 269 S. Chatterjee and C. M. McConica, 'Prediction of step coverage during blanket CVD tungsten deposition in cylindrical pores,' J. Electrochem. Soc. 137 (1), 328-335 (1990).
- 270 R. A. Adomaitis, 'Development of a multiscale model for an atomic layer deposition process,' J. Cryst. Growth 312 (8), 1449-1452 (2010).
- 271 V. Dwivedi and R. A. Adomaitis, 'Multiscale simulation and optimization of an atomic layer deposition process in a nanoporous material,' ECS Trans. 25 (8), 115-122 (2009).
- 272 A. Yanguas-Gil and J. W. Elam, 'Self-limited reaction-diffusion in nanostructured substrates: Surface coverage dynamics and analytic approximations to ALD saturation times,' Chem. Vap. Depos. 18 (1-3), 46-52 (2012).
- 273 H. Siimon and J. Aarik, 'Thickness profiles of thin films caused by secondary reactions in flow-type atomic layer deposition reactors,' J. Phys. D: Appl. Phys. 30 (12), 1725-1728 (1997).
- 274 I. G. Neizvestny, N. L. Shwartz, Z. S. Yanovitskaja, and A. V. Zverev, 'Simulation of surface relief effect on ALD process,' Comput. Mater. Sci. 36 (1-2), 36-41 (2006).
- 275 J. W. Elam and S. M. George, 'Growth of ZnO/Al2O3 alloy films using atomic layer deposition techniques,' Chem. Mater. 15 (4), 1020-1028 (2003).
- 276 J. P. Thielemann, F. Girgsdies, R. Schl € ogl, and C. Hess, 'Pore structure and surface area of silica SBA-15: Influence of washing and scale-up,' Beilstein J. Nanotechnol. 2 , 110-118 (2011).
- 277 C. W. Gardiner, Handbook of Stochastic Methods for Physics, Chemistry, and the Natural Sciences (Springer, Berlin, 2004).
- 278 R. Goodman, Introduction to Stochastic Models (Mineola, New York, 1988).
- 279 A. Yanguas-Gil and J. W. Elam, 'Simple model for atomic layer deposition precursor reaction and transport in a viscous-flow tubular reactor,' J. Vac. Sci. Technol. A 30 (1), 01A159:1-01A159:7 (2012).
- 280 D. E. Rosner, Transport Processes in Chemically Reacting Flow Systems (Butterworth-Heinemann, 2013).
- 281 M. K. Gobbert, V. Prasad, and T. S. Cale, 'Modeling and simulation of atomic layer deposition at the feature scale,' J. Vac. Sci. Technol. B 20 (3), 1031 (2002).
- 282 M. K. Gobbert, V. Prasad, and T. S. Cale, 'Predective modeling of atomic layer deposition on the feature scale,' Thin Solid Films 410 (1-2), 129-141 (2002).
- 283 R. I. Masel, Principle of Adsorption and Reaction on Solid Surfaces (Wiley Series in Chemical Engineering, New York, 1996).
- 284 H. C. Wulu, K. C. Saraswat, and J. P. McVittie, 'Simulation of mass transport for deposition in via holes and trenches,' J. Electrochem. Soc. 138 (6), 1831-1840 (1991).
- 285 J. C. Maxwell, 'On stresses in rarified gases arising from inequalities in temperature,' Philos. Trans. R. Soc. London, Sect. A 170 , 231-256 (1879).
- 286 P. Clausing, 'Uber eine Messung der molekularen Geschwindigkeit und eine Pr € ufung des Kosinusgesetzes,' Ann. Phys. 399 (5), 569-578 (1930).
- 287 F. C. Hurlbut, 'Studies of molecular scattering at the solid surface,' J. Appl. Phys. 28 (8), 844-850 (1957).
- 288 R. D. Present, Kinetic Theory of Gases (McGraw-Hill, New York, 1958).
- 289 This assumption for trajectories in 1 dimension is equivalent to the cosine distributed re-emission direction in 3 dimensions.
- 290 H.-Y. Lee, C. J. An, S. J. Piao, D. Y. Ahn, M.-T. Kim, and Y.-S. Min, 'Shrinking core model for Knudsen diffusion-limited atomic layer deposition on a nanoporous monolith with an ultrahigh aspect ratio,' J. Phys. Chem. C 114 (43), 18601-18606 (2010).
- 291 In reality, r and s are not constant during the process. A surface with or without ligands can have different sticking/recombination probabilities.
- 292 In contrast to line-of-sight and kinetic Monte Carlo models, assuming that the surface coverage evolves at a much slower timescale than the average reactant chemisorption time.
- 293 One assumes that already a ceramic layer was deposited on the CNTs which normally require 50-100 ALD cycles. Therefore, for a low number of ALD cycles, this model underestimates probably the penetration depth.
- 294 T. Keuter, N. H. Menzler, G. Mauer, F. Vondahlen, R. Vaßen, and H. P. Buchkremer, 'Modeling precursor diffusion and reaction of atomic layer deposition in porous structures,' J. Vac. Sci. Technol. A 33 (1), 01A104:1-01A104:7 (2015).
- 295 W. Jin, C. R. Kleijn, and J. R. van Ommen, 'Simulation of atomic layer deposition on nanoparticle agglomerates,' J. Vac. Sci. Technol. A 35 (1), 01B116:1-01B116:7 (2017).
- 296 Reflection occurs perpendiculary or diagonally with respect to the pore surface.
- 297 W. B. Wang, N. N. Chang, T. A. Codding, G. S. Girolami, and J. R. Abelson, 'Superconformal chemical vapor deposition of thin films in deep features,' J. Vac. Sci. Technol. A 32 (5), 051512:1-051512:10 (2014).
- 298 D. Longrie, K. Devloo-Casier, D. Deduytsche, S. Van den Berghe, K. Driesen, and C. Detavernier, 'Plasma-enhanced ALD of platinum with O2, N2 and NH3 plasmas,' ECS J. Solid State Sci. Technol. 1 (6), Q123-Q129 (2012).
- 299 O. Levenspiel, Chemical Reaction Engineering , 3rd ed. (Wiley, New York, 1999).