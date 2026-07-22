<!-- image -->

## PCCP

## PAPER

<!-- image -->

Cite this: Phys. Chem. Chem. Phys. , 2024, 26 , 28431

Received 11th January 2024, Accepted 14th October 2024

DOI: 10.1039/d4cp00131a

rsc.li/pccp

## 1 Introduction

Atomic layer deposition (ALD) is a thin film growth technique that delivers uniform thin films with nanoscale precision, 1-4 and has applications in diverse fields ranging from microelectronics to catalysts to optical coatings and beyond. 4 With the earliest experiments dating to the 1960s and 1970s, 5-7 interest in ALD is rapidly growing due to its unparalleled ability to coat complex threedimensional structures with a conformal film. 8 This ability stems from the use of self-terminating gas-solid reactions, and is taken advantage of, for example, in functional layers in logic and memory chips, in multiple patterning, 9 in catalysis, 10 and in energy storage. 11 Recently, uniform coating of silica aerogel structures with a highaspect-ratio (AR) of 4 60000:1 has been demonstrated. 12

Experimental studies on the conformality of ALD processes typically rely on specifically developed high-aspect-ratio (HAR)

a School of Chemical Engineering, Department of Chemical and Metallurgical Engineering, Aalto University, P.O. Box 16100, FI-00076 AALTO, Finland. E-mail: christine.gonsalves@aalto.fi, riikka.puurunen@aalto.fi

b School of Engineering, Aalto University, P.O. Box 16100, FI-00076 AALTO, Finland

† Electronic supplementary information (ESI) available. See DOI: https://doi.org/ 10.1039/d4cp00131a

<!-- image -->

<!-- image -->

View Article Online View Journal | View Issue

## Simulated conformality of atomic layer deposition in lateral channels: the impact of the Knudsen number on the saturation profile characteristics †

<!-- image -->

<!-- image -->

<!-- image -->

Christine Gonsalves, * a Jorge A. Velasco, a Jihong Yim, a Ja ¨ nis Ja ¨ rvilehto, a Ville Vuorinen b and Riikka L. Puurunen * a

Atomic layer deposition (ALD) is exceptionally suitable for coating complex three-dimensional structures with conformal thin films. Studies of ALD conformality in high-aspect-ratio (HAR) features typically assume free molecular flow conditions with Knudsen diffusion. However, the free molecular flow assumption might not be valid for real ALD processes. This work maps the evolution of the saturation profile characteristics in lateral high-aspect-ratio (LHAR) channels through simulations using a diffusionreaction model for various diffusion regimes with a wide range of Knudsen numbers (10 6 to 10 /C0 6 ), from free molecular flow (Knudsen diffusion) through the transition regime to continuum flow conditions (molecular diffusion). Simulations are run for ALD reactant partial pressures spanning several orders of magnitude with the exposure time kept constant (by varying the total exposure) and with the total exposure kept constant (by varying the exposure time). In a free molecular flow, for a constant total exposure, the saturation profile characteristics are identical regardless of the LHAR channel height and the partial pressure of the reactant. Under transition regime and continuum conditions, the penetration depth decreases and the steepness of the adsorption front increases with decreasing Knudsen number. The effect of varying individual parameters on the saturation profile characteristics in some cases depends on the diffusion regime. An empirical ''extended slope method'' is proposed to relate the sticking coefficient to the saturation profile's characteristic slope for any Knudsen number.

test structures. 8 These structures consist either of vertical features etched into silicon 8,13,14 or of lateral HAR (LHAR) structures prepared with a limiting height and controlled length. 8,15-17 Manually assembled macroscopic LHAR structures typically have a limiting channel height in the 100 m m range, 15,18 while LHAR structures made with techniques used in microelectromechanical systems (MEMS) can yield microscopic LHAR structures with a limiting channel height on the order of 100 nm. 16,17,19 In microscopic LHAR structures, the ARs can reach over 1000 : 1, making the structures demanding to coat completely, as the required exposure scales with the AR squared. 8,13 Incomplete conformality exposes the saturation profile for detailed analysis, as shown in Fig. 1. The saturation profile contains information on the surface reaction kinetics and has been used for analyzing the sticking coefficient in ALD 19-21 and the radical recombination probability in plasmaenhanced ALD. 22,23

Mass transport in HAR features takes place by diffusion. Whether this diffusion is Knudsen diffusion or molecular diffusion is determined by the dimensionless Knudsen number Kn ( /C0 ), which gives the ratio of the mean free path l (m) of the molecules in the gas to the characteristic limiting feature

<!-- image -->

Fig. 1 (a) The representative saturation profile as a function of the distance from the channel entrance. (b) The schematic geometry of the LHAR channels used to simulate ALD growth inside the channel for varying Knudsen numbers.

<!-- image -->

size D (m): 8,19,24

<!-- formula-not-decoded -->

For a single-component gas, the mean free path of a gas molecule is given by 8

<!-- formula-not-decoded -->

where k B (J K /C0 1 ) is the Boltzmann constant, T (K) is the temperature, d (m) is the hard-sphere diameter of the gas molecule, and p (Pa) is the pressure. If the mean free path is much larger than the characteristic dimension of the feature ( l c D , Kn c 1), molecules interact only with the walls, Knudsen diffusion takes place, and the gas transport is in the free molecular flow regime . 8,25 When the mean free path and characteristic feature dimension are similar ( l B D , Kn B 1), both molecule-wall and molecule-molecule interactions take place and the gas transport is in the transition regime . If the characteristic dimension of the feature is much larger than the mean free path ( l { D , Kn { 1), frequent gas-phase collisions occur, and the gas transport takes place in the continuum regime . 8,25 The Knudsen number for different feature sizes as a function of the reactant pressure is illustrated in Fig. 2. Typical thin-film ALD processes operate in the low vacuum (hPa range), and for nanometer-range features, Knudsen diffusion takes place. In atmospheric pressure reactors, e.g. , those used for spatial ALD and powders, molecular diffusion also needs to be taken into account.

Various models, such as diffusion-reaction models, ballistic transport-reaction models, and Monte Carlo models are used to simulate feature-scale ALD growth in HAR structures. 8,26

|

Fig. 2 Knudsen number as a function of pressure at 250 1 C, for features with different characteristic limiting sizes '' D '', calculated from the mean free path (eqn (1) and (2)) for a gas molecule with a hard-sphere diameter of 6 /C2 10 /C0 10 m.

<!-- image -->

Diffusion-reaction models and Monte Carlo models can be used at any Knudsen number, while ballistic transport-reaction models are limited to the Knudsen diffusion regime. Computational fluid dynamics simulations, in turn, are useful in the continuum flow regime, with convection and molecular diffusion. 27 While all models describe transport and reaction in HAR features, the detailed predictions may differ. This was recently shown in a comparison between a diffusion-reaction model and a ballistic transport-reaction model: the growth penetration was deeper in the ballistic transport-reaction model and the slope of the adsorption front inside the HAR feature was steeper in the diffusion-reaction model. 26 In addition, the ballistic transport-reaction model exhibited a ''trunk'' formed at the feature end, which was absent from the diffusion-reaction model 26 (a similar trunk has also been observed in Monte Carlo simulations 8 ). This work continues the series of simulations 17,21,26 performed with the Ylilammi et al. 19 diffusion-reaction model, 21,28 extending its use to the continuum regime (Kn { 1).

Another useful dimensionless number in addition to the Knudsen number is the Thiele modulus h T, which characterizes ALD growth in HAR features. The Thiele modulus has only recently been introduced for ALD, 29,30 but it has been in use for decades in the related field of heterogeneous catalysis. 29,31 The Thiele modulus is the ratio of the reaction rate to the diffusion rate and can be used to assess the growth-limiting factor (diffusion vs. reaction) in HAR features. 29-33 For single-site adsorption on a fresh surface, the Thiele modulus h T can be calculated 20,21,29 from:

ffiffiffiffiffiffiffiffiffiffiffiffiffiffiffi ffi

r

<!-- formula-not-decoded -->

Here, L (m) is the channel length, c ( /C0 ) is the sticking coefficient, H (m) is the channel height, D eff (m 2 s /C0 1 ) is the effective

diffusion coefficient, and /C22 n A (m s /C0 1 ) is the thermal velocity. When the reaction rate is much faster than the diffusion rate (when the Thiele modulus is greater than one), the process is diffusion limited , and inside the HAR features, an adsorption front forms. When the diffusion rate is faster than the reaction rate (the Thiele modulus is lower than one), the process is reaction limited and the thickness inside the HAR features increases uniformly with time. The exact limiting values of the Thiele modulus vary by source; according to Levenspiel, 34 in heterogeneous catalysis, h T 4 4 corresponds to severe diffusion resistance and h T o 0.4 to the absence of diffusion resistance. 8,29,30,33 For diffusion-limited growth in a free molecular flow regime, a simple slope method has been recently developed by Arts et al. 20 to extract information on the growth kinetics from the slope of the adsorption front.

The goal of this work is to analyze the effect of the Knudsen number on the evolution of conformality in narrow channels under diffusion-limited conditions using the Ylilammi et al. 19,21,28 model. Mapping is performed from the free molecular flow governed by Knudsen diffusion (Kn c 1) through the transition regime (Kn B 1) to continuum flow conditions governed by molecular diffusion (Kn { 1) by varying the channel height and pressure. The Knudsen number is varied by 13 orders of magnitude. An extended slope method analogous to the Arts et al. 20 slope method is proposed that covers all Knudsen numbers. This work further expands on the trends documented earlier 21 for the effect of varying process conditions on the penetration depth and the slope of the saturation profile at various Knudsen numbers. While the numerical results will be somewhat model-specific, the reported trends should be generic. Furthermore, through the (hole-)equivalent aspect ratio (EAR) concept, 8 the results can be scaled to HAR geometries other than the narrow channels studied in this work.

## 2 Methods

## 2.1 Description of the model

In this work, we used a one-dimensional diffusion-reaction model by Ylilammi et al. 19 to simulate the transport of a reactant gas from the channel entrance to the growth surface in a lateral high-aspect-ratio structure (LHAR). 21 The diffusionreaction model used in this work is based on Fick's law of diffusion and assumes Langmuir adsorption. The full model has been previously described in detail. 19,21,26 The key equations are written here to guide the reader through the simulations and results of this work.

The mean free path of the reactant 'A' in a system of two gases (reactant 'A' and inert carrier gas 'I') can be obtained using the equation 8,19,21,35

<!-- formula-not-decoded -->

where k B (J K /C0 1 ) is the Boltzmann constant, T (K) is the temperature, and m A and m I (kg) are the masses of the molecules of reactant A and inert gas I, respectively. Also, p A0 (Pa) is the partial pressure of reactant A and p I (Pa) is the inert gas partial pressure. The s A,A and s A,I are the collision cross sections (m 2 ) between the molecules i and j , given by 21

/C18

/C19

<!-- formula-not-decoded -->

where di (m) and dj (m) are the hard-sphere diameters of the molecules i and j , respectively.

In this model, the ALD surface reactions are described by the Langmuir adsorption model, 15,21 which assumes reversible single-site adsorption. Reversible Langmuir adsorption can be expressed by

<!-- formula-not-decoded -->

where A is the reactant molecule, * is the surface site, and A* is the molecule adsorbed on a site. The diffusion-reaction equation is Fick's second law of diffusion and has an adsorption loss term as in: 19,21

<!-- formula-not-decoded -->

Here, p A (Pa) is the partial pressure of reactant A, x (m) is the distance from the channel entrance, D eff (m 2 s /C0 1 ) is the effective diffusion coefficient, and h (m) is the hydraulic diameter of the lateral high aspect ratio structure. 19,21 The hydraulic diameter h is related to the height H and width W of the channel by

<!-- formula-not-decoded -->

In this work, the hydraulic diameter h is taken to represent the characteristic limiting feature size D in calculating the Knudsen number through eqn (1).

In Langmuir adsorption, a certain number of adsorption sites are occupied by the reactant molecules, and their ratio with respect to the total number of sites is called the surface coverage y , which has values ranging from 0 to 1. The rate of adsorption f ads is proportional to the fraction of unoccupied sites. The g in eqn (7) stands for the net adsorption rate (m /C0 2 s /C0 1 ), and it is the difference between the rate of adsorption f ads and the rate of desorption f des (m /C0 2 s /C0 1 ). 19,21 The evolution of the fractional surface coverage y ( /C0 ) with time from the Langmuir model of adsorption can be given by the rate equation:

<!-- formula-not-decoded -->

Here, q (m /C0 2 ) is the adsorption capacity, c ( /C0 ) is the sticking coefficient, and P d (s /C0 1 ) is the desorption probability. The adsorption capacity q is linked to the thickness-based growth per cycle (GPC) by the relation 4,21,36

<!-- formula-not-decoded -->

where r (kg m /C0 3 ) is the density of the ALD film material, gpcsat is the thickness-based growth per cycle (GPC), N 0 (mol /C0 1 ) is

s

.

C

e

m

y

P

h

<!-- image -->

Avogadro's constant, and M (kg mol /C0 1 ) is the molar mass of one formula unit of the ALD-grown film material.

In eqn (9), Q is the collision rate at unit pressure (m /C0 2 s /C0 1 Pa /C0 1 ), represented as 21

<!-- formula-not-decoded -->

where M A (kg mol /C0 1 ) is the molar mass of reactant A, R (J K /C0 1 mol /C0 1 ) is the universal gas constant, and T (K) is the temperature of the ALD process. The effective diffusion coefficient D eff in eqn (7) takes into account both the Knudsen diffusion coefficient D Kn (m 2 s /C0 1 ), which dominates at low pressures, and the molecular diffusion coefficient D A (m 2 s /C0 1 ). The molecular diffusion coefficient is a function of the gas phase collisions. The effective diffusion coefficient as per the Bosanquet relation 19,21,24 is

<!-- formula-not-decoded -->

The Knudsen diffusion coefficient D Kn does not depend on the partial pressure of reactant A but only its molar mass, M A (kg mol /C0 1 ), the hydraulic diameter h (m), and the temperature T ( K ), as given by ffiffiffiffiffiffiffiffiffiffiffiffi ffi

r

<!-- formula-not-decoded -->

The molecular diffusion coefficient D A takes into account the average speed of the molecules of reactant A, n A (m s /C0 1 ), and the collision frequency of molecules of reactant A in a gas mixture comprising reactant A and inert gas I given by z A (s /C0 1 ). The expression for the molecular diffusion coefficient 19,21

<!-- formula-not-decoded -->

The thermal velocity ( i.e. , the average speed) 19,21 is given by

r

ffiffiffiffiffiffiffiffiffiffiffi ffi

<!-- formula-not-decoded -->

Table 1 Parameters used in the simulations a

| Parameter                                                                                                                                                                                                                                                                                                                                | Values                                                                                                                                                                                                                                                     |
|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Initial partial pressure of the reactant gas ( p A0 ) [Pa] Partial pressure of inert gas I ( p I ) b [Pa] Channel height ( H ) [m] Time ( t ) [s] Temperature ( T ) [ 1 C] Adsorption capacity ( q ) [m /C0 2 ] Desorption probability in unit time ( P d ) [s /C0 1 ] Sticking coefficient ( c ) [ /C0 ] Number of ALD cycles N [ /C0 ] | 0.01, 0.1, 1, 10, 100, 1000, 10000 0.09, 0.9, 9, 90, 900, 90000 10 /C0 8 , 10 /C0 7 , 10 /C0 6 , 10 /C0 5 , 10 /C0 4 , 10 /C0 3 , 10 /C0 2 ; 5 /C2 10 /C0 7 0.001, 0.01, 0.1, 1, 10, 100, 1000 250 4 /C2 10 /C0 18 0.0001 0.0001, 0.001, 0.01 c , 0.1, 1 1 |

|

s

.

C

e

m

y

P

h

The collision frequency is 21

ffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffi

s

/C18

/C19

<!-- formula-not-decoded -->

To solve the partial pressure of reactant A along the channel p A( x , t ), instead of solving Fick's second law of diffusion, the Ylilammi et al. model 19,21 uses an analytical approximation to account for the reactant gas pressure p A along the channel. At the channel entrance, surface saturation is instantaneous ( g E 0). The diffusion-reaction equation (eqn (7)) is then simplified to 19

<!-- formula-not-decoded -->

which further resolves to 19

/C18

/C19

<!-- formula-not-decoded -->

Here, x s is the point where the linearly extrapolated partial pressure of reactant A becomes zero. 19 The x t is the transition point, at the adsorption front, where the linear approximation of eqn (18) is no longer valid and the pressure decay is approximated by an exponential tail. 19 It occurs at 19

s

ffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffi ffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffi

s

<!-- formula-not-decoded -->

x t ¼ 0 ; otherwise :

In the region beyond the transition point x t , the reactant A partial pressure is given by 19

/C18

/C19

<!-- formula-not-decoded -->

<!-- image -->

where p At is the partial pressure of reactant A at the transition point x t : 19

/C18

/C19

<!-- formula-not-decoded -->

The way the partial pressure of reactant A decreases with distance into the channel, also pinpointing the locations of x t and x s , has been illustrated in ref. 21 (figure reproduced as Fig. S1 of the ESI † ).

## 2.2 Simulation details

The equations of the Ylilammi et al. diffusion-reaction model 19 were solved using MATLAB s . A detailed description of the implementation of this model in MATLAB was presented previously. 21,28 A summary of the parameters used in the simulations in this work is shown in Table 1. These parameters were inspired by the trimethylaluminum and water ALD process. 8,19,21 The influence of varying parameters, such as the channel height, reactant partial pressure, and Knudsen number on the saturation profile was studied. All simulations were performed for one ALD reactant pulse, assuming it is the limiting step and represents an ALD cycle. The simulations were carried out using different reactant A partial pressure values ( p A0) varying from 10 /C0 2 to 10 4 Pa and the inert gas partial pressure ( p I) was nine times this value. Channel heights ( H ) ranging from 10 /C0 8 to 10 /C0 2 mwere used. To maintain a constant exposure of 10 Pa s ( B 7.5 /C2 10 4 Langmuirs, where 1 Pa s = 7500 Langmuirs), the time t was varied with the reactant A partial pressure p A0 in the range of 10 /C0 3 to 10 3 s. The dimensionless distance x ˜ ( /C0 ) was the ratio of the physical distance x (m) to the channel height H (m) and was used to effectively compare results for channels of varying heights. Simulated surface coverage results were also plotted both as a function of the physical distance x , as well as the dimensionless distance x ˜ . Fig. 3 shows the Knudsen number and the Thiele modulus calculated for the simulations in this work at different channel heights H and reactant A partial pressure values p A0. Unless otherwise stated, all simulation parameters and conditions are those provided in Table 1.

To follow the penetration depth at half surface coverage y = 0.5, a linear interpolation was made between the two closest discretization points of the dimensionless distance. The points were chosen such that the difference between the two was less than 1% of the whole range of the y -axis. Furthermore, these two points were used to get the value of the slope at half coverage, i.e. , | D y / D x ˜ | y =0.5 .

## 3 Results

## 3.1 Saturation profiles under increasing total exposure and pressure

A series of simulations were performed in which the reactant partial pressure was varied, keeping the pulse time constant and thus varying the total exposure. Keeping the exposure time t fixed at 0.1 s, the reactant partial pressure p A0 was varied within 10 /C0 2 to 10 4 Pa, giving reactant exposures ranging from

102

Fig. 3 The calculated values of the Knudsen number and Thiele modulus with a sticking coefficient c of 0.01, for the saturation profile simulations performed in this work using the Ylilammi et al. model. 19,21 (a) The Knudsen number as a function of the channel height H for different reactant A partial pressures p A0, (b) the Thiele modulus as a function of the channel height H for different reactant A partial pressures p A0, and (c) the Thiele modulus h T as a function of the Knudsen number for different channel heights.

<!-- image -->

10-1

Fig. 4 Saturation profiles in wide lateral channels of different heights at varying exposures (Pa s) using a constant reactant pulse time of 0.1 s. Channel heights: (a) 10 nm, (b) 100 nm, (c) 1 m m, (d) 10 m m, (e) 100 m m, (f) 1 mm, (g) 1 cm, and (h) 500 nm (the typical PillarHall t case 17,37 ). The calculated Knudsen number values are shown in Fig. 3(a). The exposure values are provided in the ESI † (S1). The initial reactant partial pressure p A0 is in the range of 10 /C0 2 to 10 4 Pa. The sticking coefficient c is 0.01. The other simulation conditions are given in Table 1.

<!-- image -->

<!-- image -->

10 /C0 3 to 10 3 Pa s. Simulations were performed for channels with heights from the nanometer to centimeter scale. The detailed process conditions are listed in Table 1. The Knudsen number ranged between 10 6 and 10 /C0 6 for this set of simulations (eqn (1) and Fig. 3). Thus, these simulations cover conditions from free molecular flow (Kn c 1) through the transition regime (Kn B 1) to the continuum regime (Kn { 1).

Fig. 4 shows the saturation profiles for different channel heights H and reactant partial pressures p A0. Moving from panel (a) to panel (g), the channel height increases each time by one order of magnitude, going from 10 /C0 8 to 10 /C0 2 (10 nm to 1 cm). The last panel (h) corresponds to a channel height H of 500 nm, which is typical for the PillarHall t test structures. 17,37 For a sufficiently large exposure (1 Pa s or larger) with a sticking coefficient c of 0.01, a well-developed saturation profile is seen with full coverage ( y E 1) at the channel entrance and decreasing coverage in an adsorption front deeper in the channel. In Fig. 4, the primary horizontal axis shows the physical distance x and the secondary horizontal axis shows the dimensionless distance x ˜ = x / H . In terms of the physical distance x , the growth penetrates deeper in larger channels. In terms of the dimensionless distance x ˜ , the opposite is observed: the growth penetrates deeper in smaller channels. These trends are as expected. 21

Fig. 5(a) shows the penetration depth at half coverage in terms of the dimensionless distance x ˜ y =0.5 extracted from the saturation profiles of Fig. 4 as a function of the channel height H . The cases that did not give a well-developed saturation profile ( p A0 r 1 Pa) have been excluded from Fig. 5. For a given reactant partial pressure p A0 (and thus a fixed exposure), as the channel height H increases, the penetration depth either decreases or stays constant (Fig. 5(a)). For a given channel height H , as the partial pressure p A0 increases (and thus the exposure increases), the penetration depth either increases or stays constant (Fig. 5(a)). It has been shown in previous literature that with increasing exposure, the penetration depth in ALD increases, 13 so the latter trend (no increase) may feel counter-intuitive. The reasons for the observed differences can be understood by examining the trends as a function of the Knudsen number.

Fig. 5(b) shows the penetration depth data of Fig. 5(a) further as a function of the Knudsen number. Comparing panels (b) and (a), one can see that the data has been mirrored with respect to the horizontal axis (high H corresponds to low Kn) and higher partial pressure data points are further shifted leftwards. As a result, the low-penetration-depth data points showing no dependence on p A0 and therefore clustered together at the right side of panel (a) are spread out for different Knudsen numbers on the left side of panel (b). With increasing Knudsen number for a given p A0, in the continuum flow (Kn { 1), the penetration depth increases with increasing Knudsen number. In the transition regime (Kn B 1), the penetration depth x ˜ y =0.5 continues to increase with increasing Knudsen number but the pace of increase is less, and on reaching free molecular flow (Kn c 1), the penetration depth has settled to a constant value (Fig. 5(b)). Thus, it seems that the increasing effect of exposure on the penetration depth appears

Fig. 5 The penetration depth in terms of the dimensionless distance at half coverage x ˜ y =0.5 extracted from the saturation profiles shown in Fig. 4 as a function of: (a) the channel height H , and (b) the Knudsen number. Hollow symbols correspond to the typical PillarHall t case 17,37 with a 500 nm channel height.

<!-- image -->

counterbalanced by the decreasing effect from the decreasing Knudsen number.

The dependence on the Knudsen number and the effect of pressure on the penetration depth can be explained by the type of diffusion taking place. The values of the diffusion coefficients are shown in Fig. 6 as a function of the Knudsen number: the molecular diffusion coefficient D A describing moleculemolecule interactions (eqn (14)) in panel (a), the Knudsen diffusion coefficient D Kn describing molecule-wall interactions (eqn (13)) in panel (b), and the effective diffusion coefficient D eff calculated from D A and D Kn through the Bosanquet equation (eqn (12)) in panel (c). The diffusion coefficients correspond to the cases of Fig. 5, while Fig. S2 and S3 in the ESI † represent the diffusion coefficients for all simulation conditions used in this work. Furthermore, in the ESI, † the diffusion coefficients are shown as a function of the partial pressure p A0 and the channel height H (Fig. S4, ESI † ). By examining the corresponding equations, one notices that the molecular diffusion coefficient D A has a first-order inverse relationship with the pressure (eqn (14) and (16)), while the Knudsen diffusion

s

.

C

e

m

y

P

h

2

6

2

8

4

3

7

Fig. 6 The diffusion coefficients (m 2 s /C0 1 ) as a function of the Knudsen number for different reactant partial pressures p A0 corresponding to Fig. 5: (a) the molecular diffusion coefficient D A, (b) the Knudsen diffusion coefficient D Kn, and (c) the effective diffusion coefficient D eff. Hollow symbols represent a 500 nm channel height and correspond to the typical PillarHall t case. 17,37 Diffusion coefficients for the whole range of p A0 are provided in the ESI † (Fig. S2 as a function of Knudsen number and Fig. S3 as function of channel height H ).

<!-- image -->

coefficient is not impacted by the pressure (eqn (13)). Thus, as the reactant partial pressure p A0 increases, the molecular

|

diffusion coefficient D A decreases (Fig. 6(a) and Fig. S2(a), ESI † ), while the change does not affect the Knudsen diffusion coefficient D Kn (Fig. 6(b) and Fig. S2(b), ESI † ) (to observe the trends with partial pressure, the hollow symbols help to guide the eye). Furthermore, the Knudsen diffusion coefficient D Kn has a linear dependence on the channel height H (eqn (13) and Fig. S2(b), ESI † ), while the channel height does not influence the molecular diffusion coefficient (eqn (14) and Fig. S2(a), ESI † ). The effective diffusion coefficient D eff merges these different trends, with its value being smaller than or equal to the smaller of the two. Hence, in the free molecular flow regime (Kn c 1), in the absence of gas-phase molecule-molecule interactions, the diffusion coefficient does not depend on the pressure, so the penetration depth increases because of the increasing total reactant exposure (Fig. 5). In a continuum flow (Kn { 1), in contrast, the diffusion coefficient D eff decreases linearly with increasing reactant pressure. Consequently, the increasing effect of the reactant partial pressure p A0 on the exposure is counterbalanced by the decreasing effect of increasing p A0 on the effective diffusion coefficient, and the net effect of the increasing partial pressure p A0 on the penetration depth is negligible.

Examining Fig. 4 further, in addition to trends in the penetration depth, one also observes systematic trends in the shape of the saturation profile. With increasing partial pressure p A0, for all but the most narrow channels, the adsorption front of the saturation profiles becomes shorter, and the slope of the saturation front becomes steeper. In some cases, the changes in shape lead even to a cross-over in the saturation profiles: the leading edge of the adsorption front reaches further for lower partial pressures than for higher pressures. The cross-over can be clearly seen in Fig. 4(f) and (g). The reasons for the change in shape and the cross-over are again differences in the Knudsen number and the effective diffusion coefficient. All cases where cross-over is observed are in the continuum flow regime. The increase in partial pressure p A0 leads to a decrease in the effective diffusion coefficient D eff , the stagnation of the penetration depth, a steeper saturation profile, and hence the cross-over.

## 3.2 Saturation profiles at a constant reactant exposure

A series of simulations were performed in which the reactant partial pressure p A0 (Pa) and the exposure time t (s) were varied in a way that preserved the total exposure (Pa s). The reactant partial pressure p A0 is directly related to the Knudsen number through the mean free path l (eqn (1) and (4)). Hence, the evolution of conformality can be studied at a constant reactant exposure for a range of Knudsen numbers, and thus different diffusion regimes. The reactant pressure was varied similarly to in the previous section from 10 /C0 2 to 10 4 Pa, while the exposure was kept constant at 10 Pa s by varying the pulse time between 10 3 and 10 /C0 3 s. Note that the shortest pulse times (10 /C0 2 -10 /C0 3 s) may be physically impractical.

Fig. 7 shows the saturation profiles at constant exposure for different partial pressures of the reactant p A0 and channel heights H . Similarly to in the previous section, the channel

Fig. 7 Saturation profiles in wide lateral high-aspect-ratio channels of various heights at a constant reactant exposure of 10 Pa s (300 1 C). Channel heights: (a) 10 nm, (b) 100 nm, (c) 1 m m, (d) 10 m m, (e) 100 m m, (f) 1 mm, (g) 1 cm, and (h) 500 nm (the typical PillarHall t case 17,37 ). The calculated Knudsen number values for the simulated points are shown in Fig. 3(a). To maintain a constant exposure of 10 Pa s, the pulse time was varied in the range of 10 /C0 3 to 10 3 s and the initial reactant partial pressure p A0 was varied in the range of 10 /C0 2 to 10 4 Pa (Section S2 in the ESI † ). The other simulation conditions are listed in Table 1.

<!-- image -->

2

6

2

8

4

3

9

<!-- image -->

heights vary from 10 nm in panel (a) to 1 cm in panel (g) of Fig. 7, with panel (h) representing the 500 nm PillarHall t case. 17,37 The saturation profiles are shown with respect to the dimensionless distance x ˜ on the primary horizontal axis and the physical distance x on the secondary horizontal axis. In terms of the dimensionless distance x ˜ , for a given value of the reactant partial pressure p A0, the ALD growth penetrates deeper in smaller channels. In terms of the physical distance x , for the same p A0, the growth is deeper in larger channels.

Fig. 8 shows the penetration depth values in terms of the dimensionless distance x ˜ extracted from the saturation profiles of Fig. 7. Fig. 8(a) shows that for a given reactant partial pressure p A0, the penetration depth at half coverage x ˜ y =0.5 either decreases or remains constant with increasing channel height. For a given channel height H , with an increase in the reactant partial pressure p A0, the penetration depth x ˜ y =0.5 either decreases or remains constant. Intuitively, since the exposure is constant, one could expect the penetration depth x ˜ y =0.5 to be constant. However, x ˜ y =0.5 decreases with increasing channel height and with increasing reactant partial pressure p A0.

<!-- image -->

## Channel height H (m)

Fig. 8 The penetration depth in terms of the dimensionless distance at half coverage x ˜ y =0.5 with respect to (a) the channel height H and (b) the Knudsen number. Data was extracted from the saturation profiles shown in Fig. 7. The hollow symbols at 500 nm represent the typical PillarHall t case. 17,37

<!-- image -->

Fig. 9 The saturation profiles as a function of the dimensionless distance for different Knudsen numbers at a constant reactant dose of 10 Pa s, collected from Fig. 7 (the data used is specified in the ESI, † Table S3). For Kn \ 10 2 , the surface coverage profiles overlap.

<!-- image -->

When the data of Fig. 8(a) is plotted as function of the Knudsen number, the data points collapse into a single curve in Fig. 8(b). In the continuum flow regime (Kn { 1), as the Knudsen number increases, the penetration depth increases irrespective of the reactant partial pressure. In the transition flow regime (Kn B 1), the increase in the penetration depth levels off. The penetration depth becomes constant with increasing Knudsen number in the free molecular flow regime (Kn c 1). The effect of the Knudsen number on the penetration depth is further illustrated in Fig. 9, where the saturation profiles obtained for various Knudsen numbers are presented together. Larger channel heights correspond to lower Knudsen numbers and hence have a lower penetration depth. Similarly, the higher reactant partial pressures correspond to lower Knudsen numbers and have a lower penetration depth. Once the Knudsen numbers are large enough to be in the free molecular flow regime (Kn c 1), the penetration depth is constant when the total exposure is the same, irrespective of the reactant partial pressure or channel height.

To further analyze the effect of the Knudsen number on the saturation profile characteristics, the penetration depth at half coverage and the absolute slope of the adsorption front extracted from the saturation profiles of Fig. 7 are shown in Fig. 10. The penetration depth is lowest in the continuum (Kn { 1), increases with increasing Knudsen number through the transition regime (Kn B 1), and settles to a constant value in the free molecular flow regime (Kn c 1). The absolute value of the slope decreases with increasing Knudsen number in the continuum regime (Kn { 1), the decrease slows down in the transition regime (Kn B 1), and the value settles to constant in the free molecular flow (Kn c 1).

## 3.3 The saturation profile characteristics at constant exposure with a varying sticking coefficient

In this section, the saturation profile characteristics are analyzed for a varied sticking coefficient while keeping the total

Fig. 10 (a) The penetration depth at half coverage x ˜ y =0.5 and (b) the absolute value of the slope at half coverage | D y / D x ˜ | y =0.5 plotted as a function of the Knudsen number for a sticking coefficient c of 0.01. The channel heights, reactant partial pressure, and saturation profiles are the same as in Fig. 7. Table 1 lists the other parameters.

<!-- image -->

Fig. 11 (a) The penetration depth at half coverage x ˜ y =0.5 and (b) the absolute value of the slope at half coverage | D y / D x ˜ | y =0.5 as a function of the Knudsen number for varying sticking coefficients: 1, 0.1, 0.01, 0.001, and 0.0001. The channel height used is 500 nm (the typical PillarHall t case 17,37 ). To obtain the last four points in the lower Knudsen number regime, a channel height of 1 mm is used, as indicated by the solid triangle symbol. The other parameters used for the simulations are provided in Table 1. The hollow symbols used for data of c = 0.0001 signify the fact that the used exposure did not yet saturate the adsorption at the channel entrance (saturation curves in Fig. S7, ESI † ).

<!-- image -->

exposure constant (10 Pa s). Fig. 11 illustrates as a function of the Knudsen number the influence of the sticking coefficient on the penetration depth at half coverage (a) and the slope of the adsorption front at half coverage (b). The corresponding saturation profiles are provided in the ESI † (Fig. S5).

For all sticking coefficient values, the lowest penetration depth values are obtained in the continuum (Kn { 1), see Fig. 11(a). The values increase with the Knudsen number in the transition regime (Kn B 1), and they settle to a constant value in the free molecular flow (Kn c 1). While the penetration depth at half coverage in general shows not much dependence on the sticking coefficient, especially in the free molecular flow regime, a slight variation in the penetration depth is seen for different sticking coefficients, with a higher sticking coefficient leading to a larger penetration depth at half coverage. The slight variation in the penetration depth at half coverage with the sticking coefficient is, to the authors' knowledge, related to the simplified approximate way of treating the reactant partial pressure in the Ylilammi et al. , 19,21 and not a general feature of all diffusion-reaction models. 20,24 Specifically, simulations made with the Ylilammi et al. model 19,21 show a pivot point for y ( x , t ) with varied sticking coefficient c at y E 0.3 (see Fig. S7, ESI † ), while the full solution of eqn (7) shows a pivot point at about y E 0.5 (see Fig. 1(b) of ref. 20). 20 Would the penetration depth be investigated at y E 0.3 for simulations made with the Ylilammi et al. model, it would be independent of the sticking coefficient. The case c = 0.0001 differs further from the series, because saturation had not fully taken place even at the channel entrance with the particular simulation parameters used (Fig. S7, ESI † ).

The slope of the adsorption front at half coverage depends systematically on the sticking coefficient c , with the specific relation depending on the diffusion regime (Fig. 11(b)). It is meaningful to examine the trends with decreasing Knudsen number. In a free molecular flow (Kn c 1), the slope does not depend on the Knudsen number but depends on the sticking

<!-- image -->

coefficient. The curves are vertically offset, so that a higher sticking coefficient corresponds to a higher absolute value of the slope. This observation was made previously and is the basis of the Arts et al. 20 slope method. In the transition regime (Kn B 1), the offset with a higher sticking coefficient corresponding to the higher absolute value of the slope remains, but the Knudsen number starts affecting the result: a lower Knudsen number corresponds to a steeper slope. In the continuum regime (Kn { 1), the offset remains, and the (logarithm of the) slope seems to depend linearly on the (logarithm of the) Knudsen number.

To conclude on the effect of the sticking coefficient on the saturation profile characteristics, the sticking coefficient barely affects the penetration depth, but it strongly affects the slope of the adsorption front at half coverage. The way the sticking coefficient affects the slope depends on the diffusion regime. Further analysis of this dependence will be provided in the Discussion section.

## 4 Discussion

## 4.1 Extended slope method for extracting the sticking coefficient from the saturation profile

In Fig. 11(b), it was seen that the slope of the adsorption front of the saturation profile depends on (i) the sticking coefficient and (ii) the Knudsen number. A slope method was previously derived by Arts et al. 20 to calculate the sticking coefficient describing the (lumped) kinetics of an ALD reaction in the free molecular flow regime (Kn c 1). In this section, we analyze the simulated trends with the goal of deriving an extended slope method to extract the sticking coefficient from the saturation profile in other regimes (Kn B 1 and Kn { 1).

First, the trends are analyzed in the free molecular flow regime (Kn c 1), where the slope of the adsorption front is independent of the Knudsen number (Fig. 11(b)). The least squares fitting of the data shows the following square root dependence of the slope of the adsorption front on the sticking coefficient:

/C12

/C12

ffiffiffi ffi

r

<!-- formula-not-decoded -->

where a value of 11.1 is found in this work ( R 2 = 0.9999) for parameter A . Calculated results from eqn (22) are presented in Fig. 12 (right side, Kn c 1) together with the data from Fig. 11(b). Predicted values using Arts et al. slope method 20 are included for comparison. Comparing this with the slope method by Arts et al. , 20 the same mathematical form is seen, with a slight difference in the value of the constant A (13.9 in their case). The slight quantitative difference originates from the different way of treating the reactant partial pressure in the Ylilammi et al. 19 model and in the full diffusion-reaction model that is the basis of the Arts et al. 20 slope method. The difference is consistent with the earlier finding that backextracting the sticking coefficient with the Arts et al. 20 slope method from data simulated with the Ylilammi model 19

|

returns sticking coefficient values 25% higher than the input value. 21

Second, a similar analysis is performed for the continuum regime (Kn { 1). The least squares fitting with two variables (the sticking coefficient c and Knudsen number Kn) leads to the following equation:

/C12

/C12

ffiffiffiffiffiffiffiffiffiffiffiffiffi

r

<!-- formula-not-decoded -->

where B is a parameter with a value of 23.3 ( R 2 = 0.9992). Calculated results from eqn (23) are presented in Fig. 12 (left side side, Kn { 1) together with the data from Fig. 11(b). Similarly, as in a free molecular flow, there is a square root dependence of the slope of the adsorption front at half coverage on the sticking coefficient. Additionally, there is an inverse square root dependence on the Knudsen number.

It would be helpful to have one empirical equation to relate the slope of the adsorption front at half coverage to the sticking coefficient for any Knudsen number. The following equation merges eqn (22) and (23) for a free molecular flow and continuum (diffusion-limited conditions), providing an approximate calculation also for the transition regime:

s

ffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffi

/C12

/C12

<!-- formula-not-decoded -->

where a and b are fitting parameters with values a = 0.25 and b = 1.5 (Fig. 12) note that eqn (24) is purely empirical: the added functions and parameters allow a smooth transition between free molecular flow (eqn (22)) and continuum (eqn (23)) but they do not have any deep physical meaning. Nevertheless, the

Fig. 12 Fitted data of the absolute value of the slope at half coverage as a function of the Knudsen number. Data points for c = 1, 0.1, 0.01, and 0.001 were obtained using the Ylilammi et al. 19 model for diffusion-limited conditions. Fitting parameters of the equations: A = 11.1 and B = 23.3.

<!-- image -->

ffi

equation is useful for allowing one to calculate the sticking coefficient on the basis of a measured saturation profile's adsorption front, as predicted by the Ylilammi model. 19 It should be possible to carry out a similar analysis for other models, for example, the full diffusion-reaction model on which the Arts et al. 20 slope method is based, as well as other models able to simulate ALD growth at all Knudsen numbers.

## 4.2 The effect of varying individual parameters on the saturation profile characteristics

In this section, we discuss the effect of varying a single parameter at a time on the characteristics of the ALD saturation profile. This analysis is carried out using the results obtained from simulations with the Ylilammi et al. diffusion-reaction model 19 for a free molecular flow with Knudsen diffusion (Kn c 1), which is the simplest reference case, for the transition regime (Kn B 1), and for a continuum with molecular diffusion (Kn { 1). A similar analysis was previously performed for the free molecular flow and transition regimes; 21 this work updates and adds to the previous analysis. As numerical measures of the ALD saturation profile characteristics, we use (i) the penetration depth at half coverage x ˜ y =0.5, expressed in terms of the dimensionless distance x ˜ , (ii) the absolute value of the slope of the adsorption front of the scaled saturation profile (the thickness divided by the number of cycles vs. the dimensionless distance), 17 and (iii) the absolute value of the slope of the adsorption front of the Type 1 normalized saturation profile (the normalized thickness vs. dimensionless distance). 17 The various ways to plot and interpret the ALD saturation profile (thickness profile) were introduced in ref. 17 and discussed further in ref. 21.

A summary of the interpreted trends is presented in Table 2. The corresponding ALD saturation profiles for the continuum flow regime are presented in the ESI † (Fig. S8). The parameter ranges used in these specific simulations are presented as footnotes in Table 2 and summarized in Table S4 of the ESI. † In the following text, we discuss the effect of varying each parameter individually.

Increasing the channel height H under the reference conditions of the free molecular flow (Kn c 1) does not influence the penetration depth (when expressed as the dimensionless distance x ˜ ) or the slope of the adsorption front (Table 2). (The penetration depth expressed as physical distance x of course increases with H .) In the transition (Kn B 1) and continuum regimes (Kn { 1), increasing the channel height does have an effect: the penetration depth decreases (more strongly so in the

Table 2 A summary of the effect of varying individual parameters a on the saturation profile characteristics, shown by the penetration depth at half coverage and the steepness of the adsorption front for the as measured, and Type 1 saturation profile in various diffusion regimes: the free molecular flow regime (Kn c 1), the transition flow regime (Kn B 1) [reproduced from Yim et al. 21 ], and the continuum flow regime (Kn { 1). Qualitative indicators: s increases slightly, ss increases markedly, sss increases strongly,-no change, r decreases slightly, rr decreases markedly, rrr decreases strongly b

|                                                           | Kn c 1 c        | Kn c 1 c                                                            | Kn c 1 c                                                            | Kn B 1 d        | Kn B 1 d                                                            | Kn B 1 d                                                        | Kn { 1 e        | Kn { 1 e                                                            | Kn { 1 e                                                            |
|-----------------------------------------------------------|-----------------|---------------------------------------------------------------------|---------------------------------------------------------------------|-----------------|---------------------------------------------------------------------|-----------------------------------------------------------------|-----------------|---------------------------------------------------------------------|---------------------------------------------------------------------|
| Simulation parameter (increases)                          | ~ x y ¼ 0 : 5 ¼ | d s N d ~ x /C12 /C12 /C12 /C12 /C12 /C12 /C12 /C12 /C12 /C12 ~ x ¼ | 0 : 5 d y d ~ x /C12 /C12 /C12 /C12 /C12 /C12 /C12 /C12 ~ x ¼ 0 : 5 | ~ x y ¼ 0 : 5 ¼ | d s N d ~ x /C12 /C12 /C12 /C12 /C12 /C12 /C12 /C12 /C12 /C12 ~ x ¼ | 5 d y d ~ x /C12 /C12 /C12 /C12 /C12 /C12 /C12 /C12 ~ x ¼ 0 : 5 | ~ x y ¼ 0 : 5 ¼ | d s N d ~ x /C12 /C12 /C12 /C12 /C12 /C12 /C12 /C12 /C12 /C12 ~ x ¼ | 0 : 5 d y d ~ x /C12 /C12 /C12 /C12 /C12 /C12 /C12 /C12 ~ x ¼ 0 : 5 |
|                                                           | ( /C0 )         | (nm)                                                                | ( /C0 )                                                             | ( /C0 )         | (nm)                                                                | ( /C0 )                                                         | ( /C0 )         | (nm)                                                                | ( /C0 )                                                             |
| Channel height ( H )                                      | -               | -                                                                   | -                                                                   | r               | s                                                                   | s                                                               | rr              | ss                                                                  | ss                                                                  |
| Initial partial pressure of the ALD reactant A ( p A0 ) f | ss              | -                                                                   | -                                                                   | ss              | - g                                                                 | - g                                                             | ss              | r g                                                                 | r g                                                                 |
| Reactant pulse time ( t 1 )                               | sss             | -                                                                   | -                                                                   | sss             | -                                                                   | -                                                               | sss             | -                                                                   | -                                                                   |
| Sticking coefficient ( c )                                | s h             | sss                                                                 | sss                                                                 | s h             | sss                                                                 | sss                                                             | s h             | sss                                                                 | sss                                                                 |
| Desorption probability ( P d )                            | -               | -                                                                   | -                                                                   | -               | -                                                                   | -                                                               | -               | -                                                                   | - i                                                                 |
| Adsorption capacity ( q )                                 | rrr             | ss                                                                  | -                                                                   | rrr             | ss                                                                  | -                                                               | rrr             | ss                                                                  | -                                                                   |
| Temperature ( T )                                         | r               | -                                                                   | -                                                                   | r               | -                                                                   | -                                                               | s               | r                                                                   | r                                                                   |
| Total pressure ( p ) j                                    | -               | -                                                                   | -                                                                   | r               | s                                                                   | s                                                               | rr              | ss                                                                  | ss                                                                  |
| Molar mass of the ALD reactant ( M A )                    | r               | -                                                                   | -                                                                   | r               | s                                                                   | s                                                               | r               | s                                                                   | s                                                                   |
| Molar mass of the carrier gas ( M I )                     | -               | -                                                                   | -                                                                   | s               | r                                                                   | r                                                               | s               | rr                                                                  | rr                                                                  |
| Size of the reactant molecule ( d A )                     | -               | -                                                                   | -                                                                   | r k             | s                                                                   | s                                                               | r               | s                                                                   | s                                                                   |
| Size of the inert carrier gas molecule ( d I )            | -               | -                                                                   | -                                                                   | r               | s                                                                   | s                                                               | r               | s                                                                   | s                                                                   |
| Density of the grown material ( r )                       | -               | r                                                                   | -                                                                   | -               | r                                                                   | -                                                               | -               | r                                                                   | -                                                                   |

<!-- image -->

continuum than in the transition flow) and the absolute value of the slope increases (again more strongly so in the continuum than in the transition flow). As discussed in Section 3.2, in the transition and continuum flow regimes, increasing the channel height corresponds to a decrease in the Knudsen number, leading to slower diffusion through more gas-phase molecule-molecule interactions. This leads to a lower penetration depth and a steeper slope of the adsorption front.

Increasing the reactant partial pressure p A0 leads to a higher exposure ( p A0 /C1 t ) and hence an increase in the penetration depth for all the diffusion regimes (free molecular flow (Kn c 1), transition (Kn B 1), continuum (Kn { 1)). (Note that in this simulation series, the inert gas pressure p I was kept constant, meaning that the total pressure increased only slightly.) The slope of the adsorption front is not affected in the free molecular flow (Kn c 1), and there is no effect in the transition regime (Kn B 1) either. In the continuum (Kn { 1), in contrast, the absolute value of the slope of the adsorption front barely noticeably decreases with increasing p A0. If the change was related to molecular diffusion coefficient, which slightly decreases, we would expect to see an increase in the absolute value of the slope, similarly as was the case in results reported in Section 3.1. The origin of the observed trend is clearly different, in this case. While this origin of this trend is currently not fully explained, we speculate that it may be related to the Ylilammi et al. model with the simplified analytic solution for p A( x , t ), and not to the full solution of the diffusion equation (eqn (7)).

Increasing the pulse time t 1 also leads to a higher exposure ( p A0 /C1 t ) and, consequently, an increase in the penetration depth for all diffusion regimes (free molecular flow (Kn c 1), transition (Kn B 1), continuum (Kn { 1)). The slope of the adsorption front remains unaffected in all cases. In real ALD growth experiments, increasing the exposure time is a typical way to increase the total exposure of a reactant and achieve deeper penetration into a HAR feature, with increasing the partial pressure of the reactant being the other alternative. 21 On the basis of this observation, it seems advisable to increase the total exposure in experimental conformality studies preferably by increasing the exposure time, because that does not risk altering the Knudsen number, the diffusion regime, or the slope of the adsorption front, and therefore makes interpretations related to the kinetic parameters more straightforward.

Increasing the sticking coefficient c strongly correlates with an increasing absolute value of the slope of the adsorption front in all three diffusion regimes (the free molecular flow (Kn c 1), transition (Kn B 1), continuum (Kn { 1)). This correlation has been discussed before 21 and for the basis of Arts et al. 20 slope method as well as the extended slope method proposed in this work. The simulations in this work show a slight positive correlation between the sticking coefficient and the penetration depth for all diffusion regimes. To our best understanding, this correlation is specific to the Ylilammi et al. 19 diffusion-reaction model used in this work (and related to the way it treats the partial pressure of the reactant in a simplified analytic way), and it is not expected for all diffusion-reaction

|

s

.

C

e

m

y

P

h

models. Indeed, recent simulations, e.g. , those by Arts et al. 20 with the Yanguas-Gil-Elam model, 38,39 showed no correlation between the sticking coefficient and the penetration depth.

The diffusion-reaction model of Ylilammi et al. 19 used in this work allows reversible reactions, in contrast to many other ALD models that only allow irreversible reactions. The reversibility is modeled through the desorption probability P d, or alternatively, the adsorption equilibrium constant K . The two are related through the equation K = cQ / qP d (eqn (20) in ref. 21 and eqn (13) in ref. 19). In the simulations carried out for this summary, varying the desorption probability does not affect the penetration depth or slope in any of the diffusion regimes. However, the values in the current simulations were chosen to be rather low, as we had P d from 0.001 to 10 s /C0 1 . For higher values ( P d Z 10), a decreasing effect on the absolute value of the slope is seen, along with a change in the shape of the saturation profile (Fig. S9, ESI † ). An example of a significant effect of the desorption probability can be seen in earlier simulations made for the TiCl4-H2O ALD process to grow TiO2. 19

Varying the adsorption capacity q , which is a direct measure of the ALD GPC and can be converted into the thickness per cycle through a simple formula (eqn (10)), strongly affects the saturation profile characteristics. The trends are the same regardless of the diffusion regime (Kn c 1, Kn B 1, and Kn { 1). With increasing adsorption capacity q (and thus an increasing GPC), the penetration depth strongly decreases. The decreasing effect of the GPC on the penetration depth was observed earlier in simulations 21 and in experimental studies. 17,40 When examining the adsorption front for the scaled saturation profile , with increasing adsorption capacity q (increasing GPC) the absolute value of the slope increases. When examining the adsorption front for the Type 1 normalized saturation profile , there is no change to observe in the absolute value of the slope. This case demonstrates how the difference in the two methods used to determine the saturation profile, introduced by Yim et al. , 17 is fundamentally important: the scaled saturation profile preserves the information of the core characteristic of the ALD (the GPC), while the Type 1 saturation profile does not show it. While the slope method 20 relies on the Type 1 normalized saturation profile, it would be unwise to examine only this normalized saturation profile; the scaled saturation profile is superior in its information content.

Increasing the temperature T of the ALD process influences the characteristics of the saturation profile, with the exact effect depending on the diffusion regime. (Diffusion coefficients are presented in the ESI † as Fig. S11.) In the reference free molecular flow conditions (Kn c 1), the penetration depth decreases slightly with increasing temperature, while the slope of the adsorption front is not affected. The transition regime (Kn B 1) shows the same effect (decrease) as a free molecular flow regime. The continuum regime (Kn { 1) shows the opposite effect: the penetration depth increases slightly with increasing temperature, and at the same time, the slope of the adsorption front gets slightly less steep. These two trends can be understood by considering two effects: (i) the effect of

<!-- image -->

temperature on the density of the gas and (ii) the effect of temperature on the molecular diffusion coefficient. The effect of temperature on the density of the gas is seen through the ideal gas law, pV = nRT . For a given partial pressure of the reactant molecules, the gas is less dense at a higher temperature; that is, the number density of the molecules in the gas (m /C0 3 ) decreases with increasing temperature ( n / V = p / RT ). Thus, while the total exposure calculated in the classic way through p A0 /C1 t is kept constant in the simulations, the exposure in terms of molecules entering the channel is not constant, because the number density is not constant (gas is less dense at a higher temperature). (Note: to be accurate, the total exposure, calculated from the partial pressure times time, needs temperature as a reference to be accurately defined.) Therefore, the number of molecules entering the channel during the simulation time decreases with temperature, leading to the penetration depth also decreasing under the reference free molecular flow conditions. More detailed analysis of the effect of temperature on the penetration depth in free molecular flow was recently published by Heikkinen et al. 41 In the continuum regime, where molecular diffusion and gas-phase interactions (collisions) dominate, the increasing effect of temperature on molecular diffusion (eqn (14)) dominates over the decreasing effect of temperature on the gas density, and the penetration depth thereby increases.

Varying the total pressure p alone has a distinctively different effect on the characteristics of the saturation profile in different diffusion regimes. Note that in this simulation series, the exposure ( p A0 /C1 t ) was kept constant by keeping p A0 constant; the total pressure was varied by varying the pressure of the inert gas p I. In the reference free molecular flow conditions (Kn c 1), the pressure does not influence the saturation profile characteristics - neither the penetration depth nor the slope of the adsorption front. In the transition regime (Kn B 1), the penetration depth slightly decreases and the slope of the adsorption front becomes slightly steeper with increasing total pressure. In the continuum regime (Kn { 1), in contrast, increasing the total pressure leads to a strong decrease in the penetration depth and a significantly steeper slope of the adsorption front. These trends are explained by the decreasing effect of pressure on the molecular diffusion coefficient and were already discussed earlier in Section 3.1.

Increasing the molar mass of reactant A M A causes a lower penetration depth in all diffusion regimes. Under the reference free molecular flow conditions (Kn c 1), increasing the molar mass has no effect on the slope of the adsorption front. In the transition (Kn B 1) and continuum regimes (Kn { 1), a slight increase in the absolute value of the slope ( i.e. , steepness) of the adsorption front is observed. The decrease in the penetration depth is explained by the slowing down of diffusion through heavier molecules moving more slowly than lighter molecules (eqn (14)-(16)).

Increasing the molar mass of the inert carrier gas molecules M I has no influence on the penetration depth or the slope of the adsorption front under the reference free molecular flow conditions (Kn c 1). Interestingly, in the transition regime (Kn B 1), the penetration depth increases and the absolute value of the slope of the adsorption front decreases with an increasing molar mass of the inert gas. The continuum (Kn { 1) shows similar trends as the transition regime, only stronger. As the molar mass of the inert carrier gas increases, the overall collision frequency decreases (eqn (14) and (16)). This, again, leads to a higher effective diffusion of the reactant gas.

Increasing the hard-sphere diameter of the reactant molecule d A and the inert carrier gas molecule d I has no effect on the characteristics of the saturation profile under the reference free molecular flow conditions (Kn c 1). When entering the transition (Kn B 1) and continuum regimes (Kn { 1), a small effect is seen, where the penetration depth decreases slightly and the steepness of the adsorption front increases slightly with increasing hard-sphere diameters of the reactant molecule and the carrier gas. With increasing hard-sphere diameters, the molecular diffusion coefficient decreases (eqn (14) and (16)). This leads to a lower penetration depth and a steeper adsorption front under the transition and continuum conditions.

The last parameter to vary individually was the density r of the material that makes up the thin film being grown by ALD. With all other parameters being constant (including the adsorption capacity q ), the density only affects the physical thickness of the film being grown and the GPC, expressed as thickness per cycle. The trends in the saturation profile characteristics are the same regardless of the diffusion regimes (Kn c 1, Kn B 1, and Kn { 1). The penetration depth remains unaffected by the change. With increasing density, the slope calculated from the scaled saturation profile decreases, while the slope calculated from the Type 1 normalized saturation profile remains unaffected. These changes with r are as expected and identical to those reported for the free molecular flow and transition regime earlier. 21

## 5 Summary and conclusion

The effect of the Knudsen number on the saturation profile in diffusion-limited ALD in narrow channels was analyzed with a diffusion-reaction model in this work. 19,21 Simulations were performed for a large range of realistic channel heights (10 /C0 8 to 10 /C0 2 m) and ALD reactant partial pressures (10 /C0 2 to 10 4 Pa). The resulting large range of Knudsen numbers (10 /C0 6 to 10 6 ) covers free molecular flow with Knudsen diffusion (moleculewall interactions, Kn c 1), the transition regime (Kn B 1), and a continuum with molecular diffusion (molecule-molecule interactions, Kn { 1). A series of simulations were performed (i) while varying the total exposure (the partial pressure of the reactant p A0 times the exposure time t ) and (ii) for a constant total exposure (10 Pa s at 523 K).

The simulation series with varying total exposure revealed different trends for the saturation profile characteristics with the channel height and partial pressure depending on the Knudsen number. In the free molecular flow (Kn c 1), the penetration depth increased with the reactant partial pressure ( i.e. , the total exposure), following the well-known square-rootof-exposure trend. In the continuum (Kn { 1), in contrast, the

2

6

2

8

4

5

penetration depth in a given channel height stagnated to a constant value with increasing reactant partial pressure. The stagnation was accompanied by a change in the shape of the saturation profile, which led to a cross-over in the simulated saturation profiles: the leading edge of the adsorption front reached further at low reactant partial pressures than at high pressures. While the observed stagnation and cross-over may at first seem counter-intuitive, as discussed in detail in the text, these trends are readily explained by changes in the type of diffusion from Knudsen diffusion (in free molecular flow) to molecular diffusion (in the continuum), and by how increasing pressure inversely affects the diffusion coefficient under continuum conditions.

The simulation series with constant total exposure revealed a constant penetration depth in terms of the dimensionless distance ( x ˜ = x / H ) in a free molecular flow (Kn c 1), irrespective of the specific value of the Knudsen number. (Note: the physical penetration depth x then scales with the channel height H .) When the Knudsen number decreased, in the transition regime (Kn B 1), the dimensionless penetration depth started to decrease, and in the continuum (Kn { 1), it decreased strongly with decreasing Knudsen number. Examining the saturation profile further, it is seen that the slope of the adsorption front has a constant value in a free molecular flow (Kn c 1), starts to increase with decreasing Knudsen number in the transition regime (Kn B 1), and continues to increase with decreasing Knudsen number in the continuum (Kn { 1). An extended slope method was proposed relating the slope of the adsorption front at half coverage to the sticking coefficient at any Knudsen number.

The trends in the saturation profile characteristics for different diffusion regimes (Kn c 1, Kn B 1, Kn { 1) were analyzed while varying individual simulation parameters, extending the earlier analysis for the free molecular flow and transition regime 21 to also cover the continuum. The responses to the changes in the individual parameters in the saturation profile characteristics - the penetration depth and slope of the adsorption front - were similar across all diffusion regimes when the following parameters were varied: the pulse time t 1, sticking coefficient c , desorption probability P d, adsorption capacity q , and material density r . In contrast, the response depended on the diffusion regime when the following parameters were varied: the channel height H , temperature T , reactant gas pressure p A0, total pressure p , reactant pressure fraction of the total pressure ( p A0/ p ), molar mass of the reactant M A, molar mass of the inert carrier gas M I , diameter of the reactant d A, and diameter of the inert carrier gas d I. Most cases in which the response seen in the saturation profile characteristics depends on the diffusion regime can be explained by the effect of the individual parameter on the diffusion coefficients (Knudsen and molecular diffusion coefficient). Because the total exposure ( p A0 /C1 t ) can be varied by either varying the partial pressure or by varying the pulse time, it is recommended that one should preferably vary the time to make sure one is not affecting the diffusion characteristics at the same time.

|

This work has shown that the saturation profile characteristics are affected by the diffusion regime, an indicator of which is the Knudsen number. It is recommended that all scientific articles published in the future in the field of ALD should report the pressure range used in the experiments and, especially if kinetic analysis is performed using saturation profiles, the Knudsen number.

## List of symbols

```
Parameter in the extended slope method (eqn (22) and
```

- A (24)) ( /C0 )

- a Parameter in the extended slope method (eqn (24)) ( /C0 ) B Parameter in the extended slope method (eqn (23) and (24)) ( /C0 ) b Parameter in the extended slope method (eqn (24)) ( /C0 ) b A Number of metal atoms in a reactant molecule ( /C0 ) b film Number of metal atoms per formula unit of film ( /C0 ) c Sticking coefficient ( /C0 ) c ext Sticking coefficient back-extracted with the slope method 20 ( /C0 ) D Characteristic feature dimension (m) D A Molecular diffusion coefficient (m 2 s /C0 1 ) D eff Effective diffusion coefficient (m 2 s /C0 1 ) D Kn Knudsen diffusion coefficient (m 2 s /C0 1 ) d A Hard-sphere diameter of a molecule (m) d A Hard-sphere diameter of molecule A (m) d I Hard-sphere diameter of the inert gas molecule (m) f ads Adsorption rate (m 2 s /C0 1 ) f des Desorption rate (m 2 s /C0 1 ) g Net adsorption rate (m 2 s /C0 1 ) gpcsat Saturation growth per cycle, thickness-based, in the Ylilammi et al. 19 model (m) h Hydraulic diameter of the channel (m) H Height of the channel (m) h T Thiele modulus ( /C0 ) k ads Adsorption rate constant (m /C0 2 s /C0 1 ) k des Desorption rate constant (m /C0 2 s /C0 1 ) Kn Knudsen number k B Boltzmann constant (m 2 kg s /C0 2 K /C0 1 ) l Mean free path (m) L Length of the channel (m) M Molar mass of the ALD grown film material (kg mol /C0 1 ) M A Molar mass of reactant A (kg mol /C0 1 ) M I Molar mass of inert gas I (kg mol /C0 1 ) M film Mass of the film (kg) N Number of ALD cycles ( /C0 ) n A Particle density of reactant A (m /C0 3 ) N 0 Avogadro's constant (mol /C0 1 ) p Total pressure p A0 + p I (Pa) p A Partial pressure of reactant A (Pa) p A0 Initial partial pressure of reactant A at the beginning of the channel (Pa) p At Partial pressure of reactant A at x t (Pa) p I Partial pressure of inert gas I (Pa)

- P d Desorption probability in unit time in the Ylilammi et al. 19 model (s /C0 1 )
- q Adsorption density of metal M atoms in the ALD growth of film of the M y Z x material (m /C0 2 ) ( i.e. , GPC expressed as areal number density)
- Q Collision rate of reactant A with the surface at unit pressure in the Ylilammi et al. 19 model (m /C0 2 s /C0 1 Pa /C0 1 )
- R Gas constant (J K /C0 1 mol /C0 1 )
- r Film mass density (kg m 3 )
- s i , j Collision cross-section between the molecules i and j (m 2 )

y

- Surface coverage of the adsorbed species ( /C0 )
- t Time (s)
- T Temperature (K)
- /C22 n A Thermal velocity of molecule A (m s /C0 1 )
- W Width of the channel (m)
- x Physical distance (m)
- x ˜ Dimensionless distance ( /C0 ). This is the ratio of the physical distance to the channel height. ( x ˜ = x / H )
- x s Distance where the extrapolated linear part of the reactant pressure is zero in the Ylilammi et al. 19 model (m)
- x t Distance of the linear part of the reactant pressure distribution in the Ylilammi et al. 19 model (m)
- x ˜ y =0.5 Penetration depth at half coverage in terms of the dimensionless distance ( /C0 )
- z ˜ A The collision frequency of reactant A with other gas molecules in a gas mixture of reactant A and inert gas I (s /C0 1 )

## Author contributions

The saturation profiles in this work were simulated by C. G. with re-implemented code 21,28 based on the Ylilammi et al. 19 model. The initial set of saturation profiles was simulated by J. A. V. The final simulation parameters were selected by C. G. and R. L. P. The simulations related to the summary table were carried out by C. G. The extended slope method was mainly derived by J. A. V. The initial version of the manuscript was composed by C. G. and R. L. P. The work was initiated and supervised by R. L. P. All authors discussed and contributed to the final manuscript.

## Data availability

We aim to publish data of this manuscript in https://Zenodo. org , DOI: 10.5281/zenodo.14016587 , to be included in the https://zenodo.org/communities/ald-saturation-profile-opendata/ community. Code used for the simulations is available in GitHub, see DReaM-ALD, https://github.com/Aalto-Puurunen/ dream-ald .

## Conflicts of interest

There are no conflicts to declare.

## Acknowledgements

This work was financially supported by the Academy of Finland (currently, Research Council of Finland): ALDI consortium (Decision No. 331082 and 333069) and the COOLCAT consortium (Decision No. 329978). Parts of this work were included in an oral presentation at the ALD 2023 conference in Bellevue, Washington, USA, 42 in a poster at the ALD 2022 conference in Ghent, Belgium, 43 and in an oral presentation at ALD Russia 2021 (online). 44 Computational resources were provided by the Aalto Science-IT services.

## References

- 1 T. Suntola, Mater. Sci. Rep. , 1989, 4 , 261-312.
- 2 R. L. Puurunen, J. Appl. Phys. , 2005, 97 , 9.
- 3 S. M. George, Chem. Rev. , 2010, 110 , 111-131.
- 4 J. R. van Ommen, A. Goulas and R. L. Puurunen, Chapter ''Atomic Layer Deposition''in ''Kirk-Othmer Encyclopedia of Chemical Technology, (Online), 2021, pp. 1-42, https:// doi.org/10.1002/0471238961.koe00059 .
- 5 A. A. Malygin, V. E. Drozd, A. A. Malkov and V. M. Smirnov, Chem. Vap. Deposition , 2015, 21 , 216-240.
- 6 R. L. Puurunen, Chem. Vap. Deposition , 2014, 20 , 332-344.
- 7 E. Ahvenniemi, A. R. Akbashev, S. Ali, M. Bechelany, M. Berdova, S. Boyadjiev, D. C. Cameron, R. Chen, M. Chubarov and V. Cremers, et al. , J. Vac. Sci. Technol., A , 2017, 35 , 010801.
- 8 V. Cremers, R. L. Puurunen and J. Dendooven, Appl. Phys. Rev. , 2019, 6 , 021302.
- 9 A. Mackus, A. Bol and W. Kessels, Nanoscale , 2014, 6 , 10941-10960.
- 10 B. J. ONeill, D. H. Jackson, J. Lee, C. Canlas, P. C. Stair, C. L. Marshall, J. W. Elam, T. F. Kuech, J. A. Dumesic and G. W. Huber, ACS Catal. , 2015, 5 , 1804-1825.
- 11 Y. Zhao, L. Zhang, J. Liu, K. Adair, F. Zhao, Y. Sun, T. Wu, X. Bi, K. Amine and J. Lu, et al. , Chem. Soc. Rev. , 2021, 50 , 3889-3956.
- 12 A. J. Gayle, Z. J. Berquist, Y. Chen, A. J. Hill, J. Y. Hoffman, A. R. Bielinski, A. Lenert and N. P. Dasgupta, Chem. Mater. , 2021, 33 , 5572-5583.
- 13 R. G. Gordon, D. Hausmann, E. Kim and J. Shepard, Chem. Vap. Deposition , 2003, 9 , 73-78.
- 14 M. Rose and J. Bartha, Appl. Surf. Sci. , 2009, 255 , 6620-6623.
- 15 J. Dendooven, D. Deduytsche, J. Musschoot, R. Vanmeirhaeghe
- and C. Detavernier, J. Electrochem. Soc. , 2009, 156 , P63.
- 16 F. Gao, S. Arpiainen and R. L. Puurunen, J. Vac. Sci. Technol., A , 2015, 33 , 010601.
- 17 J. Yim, O. M. Ylivaara, M. Ylilammi, V. Korpelainen, E. Haimi, E. Verkama, M. Utriainen and R. L. Puurunen, Phys. Chem. Chem. Phys. , 2020, 22 , 23107-23120.
- 18 A. Werbrouck, K. Van de Kerckhove, D. Depla, D. Poelman, P. F. Smet, J. Dendooven and C. Detavernier, J. Vac. Sci. Technol., A , 2021, 39 , 062402.
- 19 M. Ylilammi, O. M. Ylivaara and R. L. Puurunen, J. Appl. Phys. , 2018, 123 , 205301.

2

6

|

2

8

4

7

<!-- image -->

- 20 K. Arts, V. Vandalon, R. L. Puurunen, M. Utriainen, F. Gao, W. M. Kessels and H. C. Knoops, J. Vac. Sci. Technol., A , 2019, 37 , 030908.
- 21 J. Yim, E. Verkama, J. A. Velasco, K. Arts and R. L. Puurunen, Phys. Chem. Chem. Phys. , 2022, 24 , 8645-8660.
- 22 K. Arts, M. Utriainen, R. L. Puurunen, W. M. Kessels and H. C. Knoops, J. Phys. Chem. C , 2019, 123 , 27030-27035.
- 23 M. L. van de Poll, H. Jain, J. N. Hilfiker, M. Utriainen, P. Poodt, W. M. Kessels and B. Macco, Appl. Phys. Lett. , 2023, 123 , 182902.
- 24 A. Yanguas-Gil and J. W. Elam, Chem. Vap. Deposition , 2012, 18 , 46-52.
- 25 M. Knudsen, Ann. Phys. , 1909, 333 , 75-130.
- 26 J. Ja ¨rvilehto, J. A. Velasco, J. Yim, C. Gonsalves and R. L. Puurunen, Phys. Chem. Chem. Phys. , 2023, 25 , 22952-22964.
- 27 G. Ersavas Isitman, D. Izbassarov, R. L. Puurunen and V. Vuorinen, Chem. Eng. Sci. , 2023, 277 , 118862.
- 28 E. Verkama and R. L. Puurunen, DReaM-ALD (v1.0.0), https://github.com/Aalto-Puurunen/dream-ald , 2023, DOI: 10.5281/zenodo.7759195 .
- 29 A. Yanguas-Gil, Growth and Transport in Nanostructured Materials: Reactive Transport in PVD, CVD, and ALD , Springer Nature, Cham, 2017.
- 30 W. Szmyt, C. Guerra-Nun ˜ez, L. Huber, C. Dransfeld and I. Utke, Chem. Mater. , 2021, 34 , 203-216.
- 31 E. W. Thiele, Ind. Eng. Chem. , 1939, 31 , 916-920.
- 32 H. S. Fogler and S. H. Fogler, Elements of Chemical Reaction Engineering , Pearson Education, 1999.

|

- 33 P. Poodt, A. Mameli, J. Schulpen, W. Kessels and F. Roozeboom, J. Vac. Sci. Technol., A , 2017, 35 , 021502.
- 34 O. Levenspiel, Chemical Reaction Engineering , John Wiley &amp; Sons, 3rd edn, 1999.
- 35 S. Chapman and T. G. Cowling, The Mathematical Theory of Non-uniform Gases , Cambridge University Press, 1990.
- 36 R. L. Puurunen, Chem. Vap. Deposition , 2003, 9 , 249-257.
- 37 PillarHall s -Lateral High Aspect Ratio Test Structures , Accessed May 12, 2023, https://pillarhall.com/ .
- 38 A. Yanguas-Gil and J. W. Elam, Machball (0.2.0) , https:// github.com/aldsim/machball , 2020.
- 39 A. Yanguas-Gil and J. W. Elam, Theor. Chem. Acc. , 2014, 133 , 1-13.
- 40 M. Mattinen, J. Ha ¨ma ¨la ¨inen, F. Gao, P. Jalkanen, K. Mizohata, J. Ra ¨isa ¨nen, R. L. Puurunen, M. Ritala and M. Leskela ¨, Langmuir , 2016, 32 , 10559-10569.
- 41 N. Heikkinen, J. Lehtonen and R. L. Puurunen, Phys. Chem. Chem. Phys. , 2024, 26 , 7580-7591.
- 42 C. Gonsalves, J. A. Velasco, J. Ja ¨rvilehto, J. Yim, V. Vuorinen and R. L. Puurunen, Oral presentation at AVS 23nd International Conference on Atomic Layer Deposition , Bellevue, Washington, USA, July 23-26, 2023.
- 43 J. A. Velasco, C. Gonsalves, G. Ersavas Isitman, J. Yim, D. Izabassarov, E. Verkama, V. Vuorinen and R. L. Puurunen, Poster presentation at AVS 22nd International Conference on Atomic Layer Deposition , Ghent, Belgium, June 26-29, 2022.
- 44 J. A. Velasco, J. Yim, E. Verkama and R. L. Puurunen, Oral online presentation at ALD Russia , September 27-30, 2021.