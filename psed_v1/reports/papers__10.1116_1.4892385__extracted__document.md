<!-- image -->

RESEARCH ARTICLE |  AUGUST 08 2014

## Modeling precursor diffusion and reaction of atomic layer deposition in porous structures

Thomas Keuter; Norbert Heribert Menzler; Georg Mauer; Frank Vondahlen; Robert Vaßen; Hans Peter Buchkremer

<!-- image -->

J. Vac. Sci. Technol. A 33, 01A104 (2015)

https://doi.org/10.1116/1.4892385

## Articles You May Be Interested In

Atomic layer deposition of hafnium and zirconium oxyfluoride thin films

J. Vac. Sci. Technol. A (January 2021)

Surface reaction mechanisms during atomic layer deposition of zirconium oxide using water, ethanol, and water-ethanol mixture as the oxygen sources

J. Vac. Sci. Technol. A (December 2019)

TEMAZ/O 3  atomic layer deposition process with doubled growth rate and optimized interface properties in metal-insulator-metal capacitors

J. Vac. Sci. Technol. A (November 2012)

<!-- image -->

## Precision Quadrupole Mass Spectrometers

for Vacuum, Gas, Plasma &amp; Surface Science

FindSolutionsforYourResearch

<!-- image -->

<!-- image -->

09 July 2026 16:13:34

<!-- image -->

## Modeling precursor diffusion and reaction of atomic layer deposition in porous structures

Thomas Keuter, a) Norbert Heribert Menzler, Georg Mauer, Frank Vondahlen, Robert Vaßen, and Hans Peter Buchkremer

Forschungszentrum J € ulich, Institute of Energy and Climate Research (IEK-1), 52425 J € ulich, Germany

(Received 9 May 2014; accepted 23 July 2014; published 8 August 2014)

Atomic layer deposition (ALD) is a technique for depositing thin films of materials with a precise thickness control and uniformity using the self-limitation of the underlying reactions. Usually, it is difficult to predict the result of the ALD process for given external parameters, e.g., the precursor exposure time or the size of the precursor molecules. Therefore, a deeper insight into ALD by modeling the process is needed to improve process control and to achieve more economical coatings. In this paper, a detailed, microscopic approach based on the model developed by YanguasGil and Elam is presented and additionally compared with the experiment. Precursor diffusion and second-order reaction kinetics are combined to identify the influence of the porous substrate's microstructural parameters and the influence of precursor properties on the coating. The thickness of the deposited film is calculated for different depths inside the porous structure in relation to the precursor exposure time, the precursor vapor pressure, and other parameters. Good agreement with experimental results was obtained for ALD zirconiumdioxide (ZrO2) films using the precursors tetrakis(ethylmethylamido)zirconium and O2. The derivation can be adjusted to describe other features of ALD processes, e.g., precursor and reactive site losses, different growth modes, pore size reduction, and surface diffusion. V C 2014 Author(s). All article content, except where otherwise noted, is licensed under a Creative Commons Attribution 3.0 Unported License . [http://dx.doi.org/10.1116/1.4892385]

## I. INTRODUCTION

Atomic layer deposition (ALD) is a vacuum-based technique to deposit thin films of certain materials with a precise thickness control in the order of less than one nanometer. 1-7 ALD starts with two gaseous chemicals known as precursors. The solid surface of the substrate is exposed to an alternating sequence of the precursors, separated by purging steps using an inert gas. The first precursor reacts with the surface in a self-limiting manner forming one monolayer (ML). The nonchemisorbed gaseous precursor and the gaseous reaction byproducts are removed in a purging and/or an evacuation step. The second precursor also reacts with the surface in a selflimiting manner and thereby re-activates the surface for the first precursor. After a second purging and/or an evacuation step, the surface can be re-exposed to the first precursor. By repeating the cycle of exposition and purging, a thin film is deposited. Due to the self-limitation of the reactions, a maximum of one monolayer of the target material is deposited with each cycle, allowing the thickness of the thin film to be precisely controlled. In consequence of steric hindrance effects or a low density of reactive sites, even less than one monolayer is usually deposited. In this way, inner surfaces of porous structures can also be coated with a low risk of blocking pores.

A wide range of applications exists for ALD, e.g., highj oxides for CMOS and DRAM technology, 8,9 solar cell manufacturing, 10 catalysts, 11 and others. 12-17 In order to improve the control of the deposition process, several models for ALD have been published in recent years. Some of the

a) Author to whom correspondence should be addressed; electronic mail: t.keuter@fz-juelich.de

models use Monte Carlo simulations to describe the ALD process, 18-21 other models are designed only for high-aspect-ratio structures, 22,23 partly very complex 24 and partly simplified. 25 Some studies focus only on single parts of ALD, like the sticking coefficient, 26-28 the growth mode, or the growth per cycle (GPC). 29-33

A highly useful and practical model, however, was developed by Yanguas-Gil and Elam describing ALD in viscousflow tubular ALD reactors 34 as well as in porous materials. 35,36 In their work, transport by viscous flow and diffusion are coupled to surface reactions with first-order irreversible Langmuir behavior. Due to the model's simplicity, all parameters can be calculated, and the coating result can be predicted for a wide range of precursors and experimental conditions. However, the publication has two disadvantages. The published derivation of the basic differential equations is not comprehensive and elaborated, and an experimental verification of the model for porous materials is missing. 35,36 In order to overcome these shortcomings, a more detailed, microscopic derivation, based on second-order reaction kinetics, and an experimental comparison with a coated porous substrate is presented in this work. This detailed derivation allows a flexible application of the model to various experimental cases. Thus, it is possible to identify the dependencies of coating results on the microscopic characteristics of the substrate and the precursors used. Additionally, the derivation can be simply adjusted to other features of ALD processes, like different growth modes, precursor depletions, decrease of pore size, and surface diffusion. In order to verify the model, a porous substrate of an anode-supported solid oxide fuel cell (SOFC) was coated and the measured thicknesses of the deposited layer were compared to the predicted coating profile. The aim of the inner

<!-- image -->

surface coating of the SOFC substrate is to protect the nickel in the substrate against oxidation. The oxidation of the nickel leads to structural changes of the substrate's porous microstructure and subsequent to stresses and crack growth in the electrolyte resulting in a complete failure of the SOFC. 37,38 Thus, the inner surface coating can improve the reoxidation tolerance of anode-supported SOFCs. The study of the influence of ALD coatings on the oxidation tolerance will be presented in another paper.

## II. EXPERIMENTAL PROCEDURES

Substrates of anode-supported SOFCs were used as porous structures for the ALD coatings. The substrates were made of a nickel (Ni) and 8 mol% yttria-doped ZrO2 (8YSZ) cermet and manufactured using the tape casting method (cf. Menzler et al . 39 for a detailed description).

The ALD ZrO2 films were deposited in a cylindrical showerhead reactor with a diameter of about 33 cm and a height of about 2.5 cm (LS400C ALD-MOCVD System for Oxides, experimental system for research purposes, supplier VON ARDENNE). ZrO2 was chosen due to its similarity to 8YSZ and its well known stability in contact with Ni. Argon (Ar) with a flow rate of 500 SCCM was used as a carrier gas to provide the first precursor tetrakis(ethylmethylamido)zirconium (TEMAZ) to the substrate. Oxygen (O2) with a flow rate of 100 SCCM was used as the second precursor to deposit ZrO2 films. The temperature of the TEMAZ bubbler was set to 30 /C14 C, whereas the temperature of the O2 was the ambient room temperature (about 23 /C14 C). The pressure inside the reactor chamber was about 80 Pa during TEMAZ and O2 exposure. One cycle can be written as t1-t2-t3-t4-t5-t6-t7-t8, where t1/t5 is the TEMAZ/O2 exposure time (10 s/10 s), t2/t6 is the evacuation time after TEMAZ/O2 exposure (10 s/10 s), t3/t7 is the purging time (150 SCCM of Ar) after TEMAZ/O2 exposure (8s/5 s), and t4/t8 is the evacuation time after the purging (2 s/2 s). Due to the mass transfer limitations generated by the porous substrate, long precursor exposures were used. Equally long evacuation steps after precursor exposures ensured the complete removal of nonchemisorbed precursor molecules from the porous substrate. 1135 cycles of TEMAZ/O2 were performed at a substrate temperature of 200 /C14 C in order to deposit a ZrO2 film with a thickness of 110 nm.

The ZrO2 thickness was measured ex situ on fracture surfaces using a Zeiss Ultra-55 scanning electron microscope (SEM).

## III. MODELING OF THE ALD PROCESS

## A. Assumptions

The transport of the precursor from the showerhead to the one-dimensionally described substrate was not considered, because it is usually much faster than the diffusive transport inside the substrate. The precursor was treated as an ideal gas, forming a constant precursor density above the substrate. The pores inside the substrate were not taken into account individually, but characterized by a mean porosity, mean tortuosity, mean pore size, and consequently, a mean diffusion coefficient D . Due to the substrate's small pore size of 600nm in this work, the particle transport was dominated by Knudsen diffusion and D was a Knudsen diffusion coefficient. A decrease of the pore size as a result of the coating was neglected, as was a convective precursor flow inside the pores. The precursor density inside the substrate decreased due to reactions with reactive sites on the surface following second-order reaction kinetics. It is implied by the onedimensionality of the model that this pure chemisorption was independent of the distance of the precursor molecules to the pore surface. The reactive sites were equally distributed on the surface. All had the same probability of a reaction with the precursor (random growth mode), and their density was larger than the maximum density of precursor molecules, which may adhere to the surface. No surface diffusion and no desorption took place for chemisorbed precursor molecules. The second precursor (O2) reacted with all chemisorbed firstprecursor molecules (TEMAZ) forming the target material. This assumption was justified because the O2 pressure in the reactor chamber during O2 exposure was 80 Pa (only O2 was present in the reactor chamber), whereas the TEMAZ pressure during TEMAZ exposure was much lower [maximum 1.2 Pa TEMAZ vapor pressure at a bubbler temperature of 30 /C14 C (Ref. 40)]. This means that O2 diffused deeper into the substrate than TEMAZ and the TEMAZ exposure was the limiting factor for the deposition. The by-products of the chemisorption were assumed to be chemically inert and completely removed from the gas phase during the evacuation/ purging step. The initial state of the substrate was assumed to be recovered after one cycle on the deposited layer.

## B. Derivation of the differential equations

The transport of the gaseous precursor molecules is described here as pure diffusion, assuming no additional flow inside the pores. Mathematically, the diffusion is described by Fick's second law 41

<!-- formula-not-decoded -->

where n P ( t , z ) is the volumetric precursor density ([n P] ¼ m /C0 3 ) depending on the time t and the depth z inside the porous material, and D is the diffusion coefficient. The precursor molecules in the gas phase react with reactive sites [usually functional hydroxyl groups (OH groups)] on the surface of the pores. Analogous to the TEMAZ/O3 ALD process, the stoichiometries of each half-reaction of the TEMAZ/O2 ALD process can be described as 42

TEMAZ pulse:

<!-- formula-not-decoded -->

O2 pulse:

<!-- formula-not-decoded -->

where NR1R2 is shorthand for the ligand N(CH3)(C2H5). Since this reaction depends on the precursor density, as well as on the density of reactive sites, second-order reaction kinetics is assumed. In this case, the change in n P ( t , z ) is proportional to n P ( t , z ) itself and the density of reactive sites n O ( t , z )

<!-- formula-not-decoded -->

where the proportionality constant k is the reaction rate constant.

One precursor molecule can react with m , m 2 N , reactive sites on the surface, depending on the reaction mechanism. The change in the number of surface groups N O ( t , z ) is therefore given by

<!-- formula-not-decoded -->

with N P as the number of precursor molecules. The precursor density is related to a volume V P; the density of reactive sites is related to a surface area A O

<!-- formula-not-decoded -->

The ratio of A O to V P is equal to the ratio of the active surface of the porous material and pore volume and is defined as /C22 s

<!-- formula-not-decoded -->

Combining Eqs. (4)-(7), the density change of reactive sites n O ( t , z ) can be written as

<!-- formula-not-decoded -->

Taking diffusion into account [Eq. (1)], the ALD process is then described by two coupled diffusion-reaction differential equations:

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

The fraction of available sites H ( t , z ) can be defined as

<!-- formula-not-decoded -->

where n O ( t ¼ 0, z ) is the density of reactive sites before starting the ALD process, and the degree of surface coverage can be defined as 1 /C0 H ( t , z ).

## C. Determination of the model input parameters

Physically, the change in the fraction of available sites is caused by the number of particles (precursor molecules) sticking on the surface per unit of time and area i P, normalized to the maximum density of particles, which may adhere to the surface r P 43

<!-- formula-not-decoded -->

The number of particles sticking on the surface per unit of time and area is given by the impinging flux of particles J wall times the reaction probability b 0

<!-- formula-not-decoded -->

From the kinetic theory of gases, the impingement flux of particles to the substrate's surface can generally be calculated as 41

<!-- formula-not-decoded -->

where v th , P P, and T P are the mean thermal velocity, the pressure, and the temperature of the precursor gas above the surface, respectively. m P is the mass of a precursor molecule. Inserting Eqs. (14) and (13) into (12) and comparing with (10) and (11) yields the reaction rate constant k

<!-- formula-not-decoded -->

where s 0 ¼ 1/ r P is the average surface area of an adsorption site. The temperature dependence of the reaction probability b 0 is usually assumed to be a Boltzmann factor. 28 However, in this work b 0 is constant because the corresponding reaction activation energy and the temperature of the substrate surface do not vary. The maximum density of particles which may adhere to the surface r P can be determined from density functional theory by calculating the size of the precursor molecule. 42 Usually, a precursor molecule consists of a central atom (M) and ligands (L). As schematically shown in Fig. 1, large ligands can shield some reactive sites, preventing precursor molecules from reacting, although reactive sites still exist.

The density of (available) reactive sites before the ALD process begins n O ( t ¼ 0, z ) is given by

<!-- formula-not-decoded -->

The reason for this is that only reactive sites capable of reacting with the precursor molecules have to be taken into account, but no reactive sites which are shielded by ligands. Inserting Eqs. (16), (15), and (11) into Eqs. (9) and (10) gives the two coupled diffusion-reaction differential equations, which were also reported in Ref. 35:

<!-- formula-not-decoded -->

FIG. 1. Schematic illustration of steric hindrance due to large ligands: (a) side-view and (b) top-view. The reactive sites are shown as gray circles, the precursor molecules are shown as white circles with ligands (L) and a central atom (M). Reprinted with permission from R. L. Puurunen, J. Appl. Phys. 97 , 121301 (2005). Copyright 2005 AIP Publishing LLC.

<!-- image -->

<!-- formula-not-decoded -->

For low operating pressures (e.g., 80 Pa) during the ALD process, the mean free path of the precursor molecules is much longer than the pore size of the porous material. In this case, the transport of the particles is dominated by Knudsen diffusion. 44 For a porous material with a porosity /C15 , a tortuosity s , and a mean pore radius r , the Knudsen diffusion coefficient is given by

/C18

/C19

<!-- formula-not-decoded -->

Tables I and II list all parameters required to solve the differential equations (17) and (18). The microstructural parameters of the porous material in Table I must be measured for every porous material to be coated.

The parameters in Table II are related to the precursor TEMAZ. The temperature of the precursor is assumed to be the same as the substrate temperature, since the precursor diffuses inside the substrate. The precursor density outside the porous material n P ( t , z ¼ 0) is given by the vapor pressure of the precursor inside the bubbler [1.2 Pa at 30 /C14 C (Ref. 40)]. However, since the degree of saturation of precursor vapor in the carrier gas is usually not known, the vapor pressure can be regarded as an upper limit for the precursor density. The reaction probability b 0 is a priori unknown and was determined here by fitting the calculated coating profile to experimental data.

## D. Solving the differential equations

The differential Eqs. (17) and (18) were numerically solved using the command 'pdsolve' of the computer

TABLE I. Measured microstructural parameters of the porous material to be coated. These are typical values for a tape cast substrate of a SOFC.

| Parameter                         | Value                             |
|-----------------------------------|-----------------------------------|
| Porosity /C15                     | 0.33 (Ref. 38)                    |
| Tortuosity s                      | 8.28 (Ref. 49)                    |
| Mean pore radius r                | 6 /C2 10 /C0 7 m(Refs. 49 and 50) |
| Specific active BET a surface A O | 1 : 1 m 2 = g                     |
| Specific pore volume V P          | 7 /C2 10 /C0 8 m 3 = g            |

TABLE II. Required parameters of the precursor TEMAZ.

| Parameter                                                        | Value                            |
|------------------------------------------------------------------|----------------------------------|
| Temperature of the precursor T P                                 | 200 /C14 C                       |
| Mass of one precursor molecule m P                               | 323.63 /C1 1.66 /C2 10 /C0 27 kg |
| Maximum density of particles which may adhere to the surface r P | 2.86 /C2 10 18 m /C0 2 (Ref. 42) |
| Precursor density outside the porous material n P ( t , z ¼ 0)   | 2.9 /C2 10 20 m /C0 3            |
| Reaction probability b 0                                         | 2 /C2 10 /C0 4                   |

algebra system 'Maple17' [developed by Waterloo Maple Inc. (Maplesoft)]. This command uses finite difference methods with a centered implicit scheme and discretizes time and space. The differential equations were integrated in time with a space step of 2 m m and a time step of 40 ms. For more information see the pdsolve help page of Maple17. The depth z of the porous material was limited to 500 m m, since this is the typical thickness of a tape cast substrate of a SOFC. 45 For t ¼ 0, the precursor molecules were located only outside the porous material, assuming an infinite source and therefore a constant density. In the experiments, at z ¼ 500 m m, the diffusion of precursor molecules was stopped by a heating plate that served as a substrate support. This meant that the derivative of the precursor density at this point had to be zero. Hence, the initial and boundary conditions can be summarized as

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

/C12

/C12

<!-- formula-not-decoded -->

## E. Influence of precursor density and reaction probability on the coating profile

The degree of surface coverage with TEMAZ molecules after TEMAZ exposure and before O2 exposure 1 /C0 H ( t , z ) is shown in Fig. 2 for different precursor densities outside the porous material n P ( t , z ¼ 0) (a) and different reaction probabilities b 0 (b).

Figure 2(a) shows that the porous substrate is coated deeper for higher precursor densities. Due to the reaction of the gaseous precursor with the surface, the precursor molecules are removed from the gas phase and the density decreases. Other precursor molecules have to diffuse to this point to compensate for the density gradient until the surface is saturated. For higher precursor densities, the surface is saturated quicker, resulting in a deeper coating at the same exposure time.

Figure 2(b) shows that the coating profile is steep for high reaction probabilities and becomes shallower for lower reaction probabilities. For high reaction probabilities, the reaction of the precursor with the surface is much faster than the

FIG. 2. (Color online) Surface coverage 1 /C0 H ( t , z ) for different precursor densities (here TEMAZ) n P ( t , z ¼ 0) and a fixed reaction probability b 0 ¼ 2 /C2 10 /C0 4 (a). Surface coverage 1 /C0 H ( t , z ) for different reaction probabilities b 0 and a fixed precursor density of n P ( t , z ¼ 0) ¼ 4 /C2 10 22 m /C0 3 (b). The exposure time is set to t ¼ 10 s.

<!-- image -->

<!-- image -->

diffusion and all precursor molecules will react with the surface until saturation before continuing to diffuse. For low reaction probabilities, the precursor molecules diffuse past reactive sites and react with the surface at a deeper position inside the porous substrate.

## F. Calculation of the layer thickness from the degree of surface coverage

After exposure to the first precursor (here TEMAZ), the surface was exposed to the second precursor (here O2). The oxygen molecules reacted with the ligands of the precursor molecules on the surface. The reacted ligands left into the gas phase and the central atoms with two additional oxygen atoms remained on the surface. It was assumed that all precursor molecules on the surface reacted with O2 and created ZrO2. The previously shielded reactive sites were therefore available again and the degree of surface coverage was reduced by a factor r P/ q reactive, where q reactive is the density of reactive sites if no sites are shielded.

For convenience, the ZrO2 molecules on the surface were assumed to be cubic. In this case, q reactive and the thickness of a deposited ML ZrO2 d ML -ZrO2 can be calculated from the volume density of the deposited ZrO2 layer q ZrO2

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

The thickness of the deposited ZrO2 layer d ZrO2 is then given by

/C2

/C3

<!-- formula-not-decoded -->

The factor r P/ q ZrO2 is equivalent to the GPC of the layer and can be determined experimentally or calculated if the density of the deposited ZrO2 layer q ZrO2 is known.

## IV. RESULTS AND DISCUSSION

The thickness of the deposited layer can be calculated from the degree of surface coverage 1 /C0 H ( t , z ) using Eq. (26). To compare the predicted coating profile with the experiment, a tape cast substrate of an anode-supported SOFC was coated and the fracture surface was investigated using SEM. A secondary electron SEM micrograph of the fracture surface is shown in Fig. 3 depicting the topography of the sample.

On the top of the micrograph, the outer top surface of the substrate can be seen. Above this surface, the precursor density n P ( t , z ¼ 0) was assumed to be constant and precursor molecules started to diffuse into the porous substrate. This position was defined as depth z ¼ 0; going down into the micrograph, the depth z increased. The ZrO2 coating can be

FIG. 3. (Color online) Secondary electron SEM micrograph of a fracture surface of a coated substrate. The micrograph is directly connected to Fig. 4 as indicated by the circle.

<!-- image -->

FIG. 4. (Color online) Secondary electron SEM micrograph of a fracture surface of a coated substrate. The micrograph is directly connected to Fig. 3 as indicated by the circle.

<!-- image -->

discerned by the different morphologies on the Ni/8YSZ substrate, indicated by the arrows. The red circle shows the point of connection to the next SEM micrograph (Fig. 4).

The ZrO2 coating can also be seen on the Ni/8YSZ substrate in Fig. 4, and the thickness of the ZrO2 coating can be measured with respect to the outer top surface and therefore with respect to the position z inside the porous substrate. The measured ZrO2 thicknesses are shown in Fig. 5 together with two calculated coating profiles.

Different measured ZrO2 thicknesses were found for the same position inside the substrate and vice versa. This scattering can be explained by locally different porosities,

FIG. 5. (Color online) Measured (crosses) and calculated (solid and dashed line) ZrO2 thicknesses for a precursor exposure time of t ¼ 10s and 1135 cycles. To calculate the coating profiles, a measured GPC of 0.93 A ˚ /cycle and a fitted reaction probability of b 0 ¼ 2 /C2 10 /C0 4 is used. The solid line corresponds to a precursor density of n P ( t , z ¼ 0) ¼ 2.9 /C2 10 20 m /C0 3 [TEMAZ vapor pressure of 1.2 Pa at 30 /C14 C (Ref. 40)], while the dashed line corresponds to a fitted precursor density of n P ( t , z ¼ 0) ¼ 1.0 /C2 10 20 m /C0 3 .

<!-- image -->

tortuosities, pore sizes, and therefore locally different diffusion coefficients as well as by fracturing of the ZrO2 layer, which was not parallel to the fracture surface shown. The coating profiles were calculated using a measured GPC of 0.93 A ˚ /cycle [in agreement with literature values of maximum 1A ˚ /cycle (Refs. 42 and 46)] and a reaction probability of b 0 ¼ 2 /C2 10 /C0 4 , fitted to the measured ZrO2 thicknesses. The fitted reaction probability is in the same range as reaction probabilities reported in the literature. 18,24,47,48 For a precursor density outside the porous material of n P ( t , z ¼ 0) ¼ 2.9 /C2 10 20 m /C0 3 [TEMAZ vapor pressure of 1.2 Pa at a bubbler temperature of 30 /C14 C (Ref. 40)], the calculated coating profile did not fit the measured ZrO2 thicknesses. Instead, the latter can be described by the model using a slightly lower precursor density of n P ( t , z ¼ 0) ¼ 1.0 /C2 10 20 m /C0 3 .

The reasons for this discrepancy could be, on the one hand, an incomplete saturation of precursor vapor in the Ar carrier gas flow of the bubbler, causing a lower precursor density in the reactor chamber, and on the other hand, the transport of the precursor vapor from the showerhead to the porous substrate (distance of about 2.5 cm), inducing a delayed diffusion within the substrate. In order to improve the coating profile prediction, the flow of the precursor vapor in the reactor chamber should be calculated and coupled to the presented diffusion-reaction model. The degree of saturation of precursor vapor in the carrier gas can be determined by weighing the bubbler during the deposition process. In spite of the small discrepancy between model and experiment, the agreement is remarkable considering that only the reaction probability b 0 was fitted to experimental values.

The model identifies the influence of the precursors used and of the microscopic characteristics of the substrate to be coated on the coating results. For larger precursor ligands (smaller r P), the surface of the substrate is saturated quicker and the GPC is smaller. A high precursor vapor pressure also causes a fast saturation of the surface, whereas a low vapor pressure and a large specific substrate surface makes it difficult to coat the substrate conformally and uniformly in a reasonable period of time. The derivation of the equations can be adjusted to features of any particular ALD process. A term /C0 k depletion /C1 n P ( t , z ) can be added to Eq. (4) to describe a depletion of precursor molecules 34 (e.g., recombination of atomic precursor species in plasma-supported ALD) and different growth modes can be taken into account in Eq. (11) by local, position-dependent densities of reactive sites before starting the ALD process n O ( t ¼ 0, z ). If the deposited coating thickness is significant with respect to the pore sizes, the Knudsen diffusion coefficient will become positiondependent. To take this into account, the term D @ 2 n P ð t ; z Þ =@ z 2 in Eq. (9) has to be replaced by @=@ z ð D ð z Þ @ n P ð t ; z Þ =@ z Þ and the pore size can be reduced in each cycle by the position-dependent layer thickness. A loss of reactive sites on the surface (e.g., due to adsorption of reaction by-products) can be modeled by adding a term k ads /C1 n O ( t , z ) to Eq. (10). Surface diffusion of adsorbed precursor molecules can be taken into account by a time-dependent position of reactive sites on the surface, N O ( t , z ) ¼ N O ( t , z ( t )) and a corresponding surface diffusion coefficient.

## V. CONCLUSION

A detailed, microscopic derivation of the basic differential equations of the ALD model reported by Yanguas-Gil and Elam 34-36 was presented in this work, together with an experimental verification. The thickness of the deposited film can be calculated in relation to the precursor exposure time and the position inside the porous substrate for a wide range of precursors and experimental conditions. The influence of the porous material's microstructural parameters, e.g., specific surface, porosity, and pore size, and the influence of precursor properties, e.g., ligand size and vapor pressure, on the coating profile were identified, owing to the detailed derivation of the basic equations. Additionally, examples outlined how the derivation can be modified to describe other features of ALD processes. The comparison of the predicted coating profile with the experiment showed good, but improvable, agreement.

Due to the model's flexible applicability, it is highly practical and can be used to predict ALD coating results for a wide range of applications, such as corrosion resistance, deposition of catalytic material, surface activation by depositing functional groups, and others.

Different precursors and different porous structures must be used for additional verification of the model and to identify its limitations. The model only describes an ideal ALD process without considering desorption of precursor molecules, transport mechanisms other than diffusion inside the pores, or precursor flow in the reactor chamber. Shorter purging and/or evacuation steps will neither change the predicted coating profile nor the deposited layer thickness as long as all nonchemisorbed precursor molecules are removed during these steps. However, an incomplete removal of nonchemisorbed precursor molecules is not described by the model, nor is as an incomplete reaction of O2 with TEMAZ molecules on the surface. In future work, the model should be extended accordingly and verified for systems where these aspects are important.

## ACKNOWLEDGMENTS

The authors acknowledge the contributions of colleagues in their institute: Robert M € ucke, Daniel R € ohrens, and Philipp J. Terberger for fruitful discussions, and Doris Sebold for the SEM investigations.

1 T. Suntola and J. Antson, U.S. patent no. 4,058,430 (15 November 1977).

2 T. Suntola and J. Hyvarinen, Annu. Rev. Mater. Sci. 15 , 177 (1985).

3 S. M. George, A. W. Ott, and J. W. Klaus, J. Phys. Chem. 100 , 13121 (1996).

4 S. Haukka and T. Suntola, Interface Sci. 5 , 119 (1997).

5 M. Leskel € a and M. Ritala, Thin Solid Films 409 , 138 (2002).

6 M. Ritala and M. Leskel € a, Handbook of Thin Films Materials: Deposition and Processing of Thin Films , edited by H. Nalwa (Academic, New York, 2002), Vol. 1, pp. 103-159.

7 R. L. Puurunen, J. Appl. Phys. 97 , 121301 (2005).

8 A. Jones, H. Aspinall, P. Chalker, R. Potter, T. Manning, Y. Loo, R. O'Kane, J. Gaskell, and L. Smith, Chem. Vap. Deposition 12 , 83 (2006).

- 9 J. Niinist € o, K. Kukli, M. Heikkil € a, M. Ritala, and M. Leskel € a, Adv. Eng. Mater. 11 , 223 (2009).
- 10 J. A. van Delft, D. Garcia-Alonso, and W. M. M. Kessels, Semicond. Sci. Technol. 27 , 074002 (2012).
- 11 C. Detavernier, J. Dendooven, S. Pulinthanathu Sree, K. F. Ludwig, and J. A. Martens, Chem. Soc. Rev. 40 , 5242 (2011).
- 12 F. Zaera, J. Mater. Chem. 18 , 3521 (2008).
- 13 J. R. Bakke, K. L. Pickrahn, T. P. Brennan, and S. F. Bent, Nanoscale 3 , 3482 (2011).
- 14 J. W. Elam, N. P. Dasgupta, and F. B. Prinz, MRS Bull. 36 , 899 (2011).
- 15 Q. Peng, J. S. Lewis, P. G. Hoertz, J. T. Glass, and G. N. Parsons, J. Vac. Sci. Technol., A 30 , 010803 (2012).
- 16 H. C. M. Knoops, M. E. Donders, M. C. M. van de Sanden, P. H. L. Notten, and W. M. M. Kessels, J. Vac. Sci. Technol., A 30 , 010801 (2012).
- 17 C. Wiemer, L. Lamagna, and M. Fanciulli, Semicond. Sci. Technol. 27 , 074013 (2012).
- 18 J. W. Elam, D. Routkevitch, P. P. Mardilovich, and S. M. George, Chem. Mater. 15 , 3507 (2003).
- 19 R. A. Adomaitis, J. Cryst. Growth 312 , 1449 (2010).
- 20 H. C. M. Knoops, E. Langereis, M. C. M. van de Sanden, and W. M. M. Kessels, J. Electrochem. Soc. 157 , G241 (2010).
- 21 M. Rose, Ph.D. thesis (Fakult € at Elektrotechnik und Informationstechnik der Technischen Universit € at Dresden, 2010).
- 22 J. Kim, J. Ahn, S. Kang, and J. Kim, J. Appl. Phys. 101 , 073502 (2007).
- 23 A. Lankhorst, B. Paarhuis, H. Terhorst, P. Simons, and C. Kleijn, Surf. Coat. Technol. 201 , 8842 (2007).
- 24 R. A. Adomaitis, Chem. Vap. Deposition 17 , 353 (2011).
- 25 R. G. Gordon, D. Hausmann, E. Kim, and J. Shepard, Chem. Vap. Deposition 9 , 73 (2003).
- 26 J. Dendooven, D. Deduytsche, J. Musschoot, R. L. Vanmeirhaeghe, and C. Detavernier, J. Electrochem. Soc. 156 , P63 (2009).
- 27 M. Rose and J. Bartha, Appl. Surf. Sci. 255 , 6620 (2009).
- 28 M. Rose, J. Bartha, and I. Endler, Appl. Surf. Sci. 256 , 3778 (2010).
- 29 R. Puurunen, Chem. Vap. Deposition 9 , 249 (2003).
- 30 R. Puurunen, Chem. Vap. Deposition 9 , 327 (2003).
- 31 R. Puurunen, Chem. Vap. Deposition 10 , 159 (2004).
- 32 R. L. Puurunen et al. , J. Appl. Phys. 96 , 4878 (2004).
- 33 R. L. Puurunen and W. Vandervorst, J. Appl. Phys. 96 , 7686 (2004).
- 34 A. Yanguas-Gil and J. W. Elam, J. Vac. Sci. Technol., A 30 , 01A159 (2012).
- 35 A. Yanguas-Gil and J. W. Elam, Chem. Vap. Deposition 18 , 46 (2012).
- 36 A. Yanguas-Gil and J. W. Elam, ECS Trans. 41 , 169 (2011).
- 37 J. Malzbender, E. Wessel, and R. W. Steinbrech, Solid State Ionics 176 , 2201 (2005).
- 38 M. Ettler, H. Timmermann, J. Malzbender, A. Weber, and N. Menzler, J. Power Sources 195 , 5452 (2010).
- 39 N. H. Menzler, F. Tietz, S. Uhlenbruck, H. P. Buchkremer, and D. St € over, J. Mater. Sci. 45 , 3109 (2010).
- 40 D. Monnier, I. Nuta, C. Chatillon, M. Gros-Jean, F. Volpi, and E. Blanquet, J. Electrochem. Soc. 156 , H71 (2009).
- 41 P. W. Atkins, Physikalische Chemie (Wiley-VCH, Weinheim, 2006).
- 42 W. Weinreich et al. , J. Vac. Sci. Technol., A 31 , 01A123 (2013).
- 43 T. Zilbauer, Ph.D. thesis (Universit € at der Bundeswehr M € unchen, 2009).
- 44 R. Brodkey and H. Hershey, Transport Phenomena: A Unified Approach (McGraw-Hill, New York, 1988).
- 45 W. Schafbauer, N. H. Menzler, and H. P. Buchkremer, Int. J. Appl. Ceram. Technol. 11 , 125 (2014).
- 46 D. M. Hausmann, E. Kim, J. Becker, and R. G. Gordon, Chem. Mater. 14 , 4350 (2002).
- 47 G. Prechtl, A. Kersch, G. Schulze Icking-Konert, W. Jacobs, T. Hecht, H. Boubekeur, and U. Schroder, IEEE Int. Electron Devices Meet., Tech. Dig. 2003 , 9.6.1.
- 48 A. Yanguas-Gil and J. W. Elam, J. Vac. Sci. Technol., A 32 , 031504 (2014).
- 49 B. Forreiter, Master's thesis (Karlsruher Institut f € ur Technologie, Institut f € ur Werkstoffe der Elektrotechnik, 2012).
- 50 A. Leonide, Y. Apel, and E. Ivers-Tiffee, ECS Trans. 19 , 81 (2009).