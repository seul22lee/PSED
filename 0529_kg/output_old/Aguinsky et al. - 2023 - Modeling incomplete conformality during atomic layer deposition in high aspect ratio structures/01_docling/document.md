<!-- image -->

Contents lists available at ScienceDirect

## Solid State Electronics

journal homepage: www.elsevier.com/locate/sse

## Modeling incomplete conformality during atomic layer deposition in high aspect ratio structures ✩

Luiz Felipe Aguinsky a, ∗ , Frâncio Rodrigues a , Tobias Reiter b , Xaver Klemenschits b , Lado Filipovic b , Andreas Hössinger c , Josef Weinbub a

- a Christian Doppler Laboratory for High Performance TCAD, Institute for Microelectronics, TU Wien, Gußhausstraße 27-29, 1040, Wien, Austria
- b Institute for Microelectronics, TU Wien, Gußhausstraße 27-29, 1040, Wien, Austria
- c Silvaco Europe Ltd., Compass Point, St Ives, Cambridge, PE27 5JL, United Kingdom

## A R T I C L E I N F O

Keywords: Atomic layer deposition Thin films High aspect ratio Langmuir kinetics Topography simulation

## 1. Introduction

Atomic layer deposition (ALD) is a thin film deposition technique which enables greater control over film thickness and conformality than conventional chemical vapor deposition (CVD) [1]. ALD has become a key technology in semiconductor processing, having found application in, e.g., the deposition of technologically relevant oxides and nitrides [2]. Due to its increased control over conformality, ALD is a key enabler of high aspect ratio (HAR) structures such as dynamic random-access memory (DRAM) capacitors [3] and three-dimensional (3D) NAND flash memory [4].

In contrast to conventional CVD, ALD divides the growth process into at least two sequential, self-limiting processing steps, which repeat in cycles [2]. From the many precursor chemistries enabling ALD, the deposition of aluminum oxide (Al 2 O 3 ) from trimethylaluminum (TMA, or Al(CH 3 ) 3 ) and water (H 2 O) has emerged as a paradigmatic system [5]. Even though this process has found application in, e.g., high𝜅

✩ The review of this paper was arranged by Francisco Gamiz.

∗ Corresponding author. E-mail address: aguinsky@iue.tuwien.ac.at (L.F. Aguinsky).

https://doi.org/10.1016/j.sse.2022.108584

## A B S T R A C T

Atomic layer deposition allows for precise control over film thickness and conformality. It is a critical enabler of high aspect ratio structures, such as 3D NAND memory, since its self-limiting behavior enables higher conformality than conventional processes. However, as the aspect ratio increases, deviations from complete conformality frequently occur, requiring comprehensive modeling to aid the development of novel technologies. To that end, we present a model for surface coverage during atomic layer deposition where incomplete conformality is present. This model combines existing approaches based on Knudsen diffusion and Langmuir kinetics. Our model expands the state-of-the art by (i) incorporating gas-phase diffusivity through the Bosanquet formula as well as reaction reversibility in the modeling framework first proposed by Yanguas-Gil and Elam, and (ii) being efficiently integrated within level-set topography simulators. The model is manually calibrated to published results of the prototypical atomic layer deposition of Al 2 O 3 from TMA and H 2 O in lateral high aspect ratio structures. We investigate the temperature dependence of the H 2 O step, thus extracting an activation energy of 0 . 178 eV which is consistent with recent experiments. In the TMA step, we observe increased accuracy from the Bosanquet formula and we reproduce multiple independent experiments with the same parameter set, highlighting that the model parameters effectively capture the reactor conditions.

capacitor films for DRAM [3], its main importance stems from the nearideal aspects of the involved surface chemistry. Thus, a significant body of research has emerged for this process, and it became the de facto standard against which novel approaches are tested.

In an irreversible self-limiting reaction with fixed reactor conditions, complete conformality is theoretically achievable by adapting the step pulse time 𝑡 𝑝 to the involved HAR structure. Thus, the conformal film thickness could be straightforwardly controlled via the growth per cycle (GPC) parameter, determined by the involved reactants and reactor conditions, and the total number of cycles ( 𝑁 cycles ). However, in real-world conditions, deviations from complete conformality in HAR structures are observed [1] since (i) the true surface chemistry is not perfectly self-limiting, and (ii) reactant transport becomes severely constricted. Accordingly, as semiconductor technology advances towards ever higher aspect ratios, the challenge of understanding incomplete conformality in ALD must be addressed with a joint experimental and modeling approach.

<!-- image -->

<!-- image -->

L.F. Aguinsky et al.

To that end, first-order Langmuir models have been developed and applied to predict saturation times [6-8], to model growth kinetics [9], to derive scaling laws [10], and to estimate the clean surface sticking coefficient ( 𝛽 0 ) using either Monte Carlo methods [11,12] or simplified analytical expressions [13]. These approaches are very powerful, however, they do not evaluate the resulting thickness profiles in a manner which is compatible with level-set topography simulators. This is a requirement for the integration of ALD models with additional processing steps and for process-aware device simulation within a design-technology co-optimization (DTCO) framework [14].

In the past, we addressed this issue in the context of the ALD of titanium compounds by developing a topography simulation integrating detailed Langmuir surface models with Monte Carlo ray tracing calculations of local reactant fluxes [15]. Nevertheless, the use of Monte Carlo ray tracing as well as the calculation of the growth on a cycleby-cycle basis leads to high computational costs. Therefore, only a few deposition cycles were simulated. For a topography simulation of realistic ALD processes involving hundreds of cycles, not only the surface coverages but also the level-set velocity field must be accurately and efficiently calculated.

Here, we present a model for ALD surface coverage in HAR structures based on one-dimensional (1D) diffusive particle transport, building upon the model proposed by Yanguas-Gil and Elam [8] by combining it with physical-chemical phenomena highlighted in previous works [6,9,16]. Namely, the model now includes reversible reactions and gas-phase diffusion through the Bosanquet formula [17]. For the calculation of thickness profiles, the model is efficiently integrated with level-set based topography simulators [18-21] through the bundling of multiple cycles via the introduction of an artificial time unit. Our model is then manually calibrated to reported ALD thicknesses of Al 2 O 3 in both the H 2 Oand TMA-limited regimes, allowing for a deeper analysis of the role of temperature and geometrical parameters for this prototypical process.

## 2. Methods

## 2.1. Surface kinetics and flux modeling

As with most ALD modeling approaches [1], our model assumes that the processes are limited by the reactive transport of a single reactant species. For clarity, our discussion focuses on the H 2 O-limited regime during ALD of Al 2 O 3 . However, the same insights are valid for the TMA-limited case and to similar reactants. We employ a first-order Langmuir surface model, combined with diffusive reactant transport for the calculation of the surface coverage 𝜃 , building upon the model first proposed by Yanguas-Gil and Elam [8] by considering reversible kinetics and the impact of gas-phase diffusivity [6,9,16].

The following reaction pathways for an impinging water flux 𝛤 H2 O ( m -2 s -1 ) are considered, represented in Fig. 1: Adsorption-reflection, mediated by a 𝜃 -dependent sticking coefficient 𝛽 ( 𝜃 ) = 𝛽 0 (1 𝜃 ) , and desorption, given by an evaporation flux 𝛤 ev ( m -2 s -1 ). In the original model [8] as well as in subsequent developments [10,22,23], irreversible kinetics are assumed, i.e., 𝛤 ev = 0 . However, other works have highlighted the necessity of considering the reaction reversibility, leading to the following equation for the time evolution of 𝜃 at each surface point 𝑟 ⃗ [6,9,16]:

<!-- formula-not-decoded -->

Eq. (1) describes an empirical model with two phenomenological parameters: 𝛽 0 and 𝛤 ev . The surface site area 𝑠 0 ( m 2 ) can be estimated with a ''billiard ball'' approximation from the deposited film density 𝜌 ( kgm -3 ) and GPC (Å) [9]. In contrast to the steady-state assumption applied in, e.g., plasma etching simulations [19], we solve (1) up to

Fig. 1. Possible reaction pathways in reversible Langmuir kinetics for the H 2 O step of ALD of Al 2 O 3 .

<!-- image -->

the reactor pulse time 𝑡 𝑝 ( s ) using the forward Euler method with 𝑁𝑡 total time steps. The purge step is not considered.

A requirement for determining 𝜃 ( 𝑟 ⃗ ) is finding the distribution of the reactant flux 𝛤 H2 O ( 𝑟 ⃗ ) . This calculation is challenging given that the 𝛽 ( 𝜃 ) changes not only across the surface but also after the solution of each step of (1). Although powerful methods such as the Boltzmann transport equation [6], the lattice Boltzmann model [24], or Monte Carlo ray tracing can be used [11,15], they require substantial computational resources.

To alleviate the computational burden, we assume a preferential transport direction, i.e., that the flux is equal on all surfaces at the same 𝑧 coordinate. This allows to calculate the flux using the continuity equation assuming diffusive flow in a cylinder of diameter 𝑑 ( μm ) and length 𝐿 ( μm ), with adsorption losses, given by a 1D differential equation [8,25]:

<!-- formula-not-decoded -->

In (2), ̄ 𝑣 ( ms -1 ) is the thermal speed and 𝛤 0 ( m -2 s -1 ) is the flux of the reactant species inside the reactor, which can be calculated using the kinetic theory of gases [26] from the reactor temperature 𝑇 ( ◦ C ), reactant molar mass 𝑀𝐴 ( kgmol -1 ), and partial pressure 𝑝 𝐴 ( mTorr ). The frozen surface approximation is employed [8], that is, transport is assumed to reach equilibrium on a much faster timescale than the chemical evolution of the surface (i.e., 𝑑𝛤 H2 O ∕ 𝑑𝑡 = 0 even though 𝑑𝜃 ∕ 𝑑𝑡 ≠ 0 ). This approximation is generally accepted as valid for microscopic structures [25]. This equation is solved with a central finite differences scheme for each step of the solution of (1).

The system composed of (1) and (2) is, in essence, a re-statement of the established Yanguas-Gil and Elam model [8] with two main differences. First, the reversibility of the reactions is considered in (1). Also, the diffusivity 𝐷 ( m 2 s -1 ) is considered explicitly, which enables to combine Knudsen diffusion with gas-phase diffusion through the Bosanquet interpolation formula, which is discussed in the following paragraph. Both of these physical-chemical phenomena have been incorporated into modeling by previous studies either separately [6,12] or jointly [9,16]. However, such models, most notably the approach taken by Ylilammi et al. [9] and its subsequent expansion [16], rely on a different set of approximations for the calculation of the flux distribution inside the structure and do not compute a solution to (2). In their work, the frozen surface approximation is not employed and the partial pressure distribution, which is equivalent to the reactant flux distribution, is directly approximated as two separate regions, one linear and another exponentially decaying.

Fig. 2. Impact of model parameters in the required 𝑡 𝑝 to reach 95% saturation at the bottom of a cylindrical structure with 𝑑 = 1μm , 𝐿 = 100μm in a fictitious chemistry with 𝑠 0 = 2 × 10 -19 m 2 and 𝛤 0 = 10 24 m -2 s -1 .

<!-- image -->

As previously indicated, 𝐷 can be calculated by considering two individual contributions: One stemming from reactant-wall collisions, i.e., the Knudsen diffusivity 𝐷 Kn , and another stemming from reactantreactant collisions, i.e., the gas-phase diffusivity 𝐷𝐴 . Historically, Knudsen diffusion has been defined in terms of a long cylindrical tube [27] of diameter 𝑑 , leading to the following expression for the diffusivity [17]:

<!-- formula-not-decoded -->

Therefore, when structures other than a long cylindrical tube are considered, some kind of mapping between the involved geometry and the standard cylinder must be provided. The development of such mappings has been the source of much controversy since the inception of the theory [28], leading to many lingering misconceptions (e.g., incorrect conductance values for square tubes). A further discussion of these misconceptions is outside of the scope of the presented research, instead, the simplified hydraulic diameter approximation is employed [9]. That is, the diameter 𝑑 in (2) and (3) is replaced with 𝑑 → ℎ 𝑑 ⋅ 𝑑 , where ℎ 𝑑 is the hydraulic diameter factor and 𝑑 is a relevant physical dimension. For example, for a wide rectangular trench with opening 𝑑 (c.f. Fig. 3), ℎ 𝑑 is estimated to be 2 [1,9].

Eq. (3) is valid when reactant-wall collisions are more likely than reactant-reactant collisions (i.e., Knudsen number Kn &gt; 10 ). Should the rate of particle-particle collisions be comparable, i.e., 1 &lt; Kn &lt; 10 , 𝐷 can be approximated with the Bosanquet interpolation formula [17]:

<!-- formula-not-decoded -->

In (4), 𝐷𝐴 is the conventional Chapman-Enskog gas-phase diffusivity [26] calculated from the particle hard-sphere diameter 𝑑 𝐴 ( pm ). In this work, we assume only Knudsen diffusivity ( 𝐷𝐴 → ∞ ), except when otherwise indicated.

In Fig. 2, the impact of the parameters 𝛽 0 and 𝛤 ev in the required 𝑡 𝑝 for achieving 95% saturation is presented. We define saturation as the final state of the surface coverage in the steady state, i.e., 𝑑𝜃 sat ( 𝑟 ⃗ )∕ 𝑑𝑡 = 0 . Since this situation is only reached on the limit 𝑡 𝑝 → ∞ , we identify a relevant time as the pulse time necessary to reach 0 . 95 ⋅ 𝜃 sat . In addition, as 𝜃 sat is defined on the entire structure, the coverage value at the bottom of the structure, i.e., 𝜃 sat ( 𝑧 = 𝐿 ) , is chosen as the representative value for analysis, since it is where the impact of the flux restriction is the largest.

From Fig. 2, we observe that 𝛽 0 has the most influence on the saturation time. Instead of directly impacting 𝑡 𝑝 , 𝛤 ev greatly affects the maximum coverage achievable at the bottom of the structure. Therefore, it strictly limits the maximum aspect ratio achievable by a certain reactor configuration and must be considered in the design of novel

Fig. 3. Illustration of simulated trench after ALD with incomplete conformality.

<!-- image -->

technologies. In addition, previous work has shown that a high value of 𝛤 ev can impact the thickness profile particularly in the transition between a region with high growth to one with low growth [16].

## 2.2. Topography simulation

In order to calculate the time evolution of the thickness profiles during the fabrication process in a manner compatible with simulation of further processing steps and DTCO, we employ the established levelset method [18,19] as implemented in ViennaLS [20] and in Silvaco's Victory Process [21]. In this method, the surface is described as the zero level-set of a 3D function 𝜙 ( 𝑟 ⃗ ) which evolves in time according to the level-set equation

<!-- formula-not-decoded -->

where 𝑉 ( 𝑟 ⃗ ) is a scalar velocity field describing how the surface should evolve over time, i.e., how a material is grown or etched. An illustration of a simulated 3D trench geometry after ALD of Al 2 O 3 is shown in Fig. 3.

The methodology presented in Section 2.1 is limited to calculating 𝜃 ( 𝑟 ⃗ ) . However, it is not straightforward to map 𝜃 ( 𝑟 ⃗ ) into 𝑉 ( 𝑟 ⃗ ) . Growth rates can be calculated cycle-by-cycle by evolving the surface by the molecular layer thickness [15], however, this imposes a performance penalty since the grid resolution must be small enough to capture the individual molecular layer and 𝜃 ( 𝑟 ⃗ ) must be calculated 𝑁 cycles times. This calculation repeats even though the geometry changes minimally between sequential cycles.

In order to capture a realistic ALD process with hundreds or thousands of cycles, a more efficient approach is required, bundling multiple cycles into the surface evolution step. For this, we introduce an artificial time 𝑡 ∗ = 𝑁 cycles ∕ 𝐶 where 𝐶 is a numerical constant. It is important to note that 𝑡 ∗ is unrelated to 𝑡 𝑝 , since the latter is only required for the calculation of 𝜃 ( 𝑟 ⃗ ) . In essence, to maintain unit consistency with (5), the time variable 𝑡 ∗ represents a bundle of multiple ALD cycles. Thus, the velocity field becomes

<!-- formula-not-decoded -->

The constant 𝐶 can be chosen by considering the involved number of cycles such that 𝑡 ∗ ≈ 1 . In fact, the choice of 𝐶 plays a limited role in the determination of the bundling. Instead, in the involved level-set based topography simulators, 𝑉 ( 𝑟 ⃗ ) is assumed to be constant during each time step 𝛥𝑡 of the solution of (5). According to the CourantFriedrichs-Lewy (CFL) condition [18], the time step is limited to allow

Table 1 Model parameters for the H 2 O step of ALD of Al 2 O 3

calibrated to measurements from [13].

| Parameter                       | 150 ◦ C         | 220 ◦ C         | 310 ◦ C         |
|---------------------------------|-----------------|-----------------|-----------------|
| 𝛤 ev ( m -2 s -1 )              | 6 . 5 ⋅ 10 19   | 5 . 0 ⋅ 10 19   | 3 . 5 ⋅ 10 19   |
| 𝛽 0                             | 5 . 0 ⋅ 10 -5   | 1 . 2 ⋅ 10 -4   | 1 . 9 ⋅ 10 -4   |
| 𝛽 0 , estimated range from [13] | 1 . 4 ⋅ 10 -5 - | 0 . 8 ⋅ 10 -4 - | 0 . 9 ⋅ 10 -4 - |
| 𝛽 0 , estimated range from [13] | 2 . 3 ⋅ 10 -5   | 2 . 0 ⋅ 10 -4   | 2 . 5 ⋅ 10 -4   |

Fig. 4. Comparison of topography simulation using the combined surface coverage model with the parameters from Table 1 to H 2 O-limited thickness profiles measured by Arts et al. [13].

<!-- image -->

an evolution of at most one grid spacing 𝛥𝑥 , i.e., 𝛥𝑡 &lt; 𝛥𝑥 ∕max | 𝑉 ( 𝑟 ⃗ ) | . After each time step, the geometrical inputs of (2), namely 𝑑 and 𝐿 , are updated. Thus, for (6) to be physically meaningful, 𝛥𝑥 must be small enough such that the change in the geometry of its magnitude does not significantly impact 𝜃 ( 𝑟 ⃗ ) .

## 3. Results

## 3.1. The H 2 O step: Temperature dependence

We calibrate our model to measured thickness profiles of Al 2 O 3 in the H 2 O-limited regime. Arts et al. [13] report film thicknesses in lateral HAR trench-like structures ( 𝑑 = 0 . 5 μm , 𝐿 = 5000μm ) with an H 2 O dose of approximately 750 mTorr ⋅ s after 400 ALD cycles with a GPC of 1 . 12 Å at three calibrated substrate temperatures 𝑇 ( 150 ◦ C , 220 ◦ C , and 310 ◦ C ). We estimate 𝑡 𝑝 to be 0 . 1 s . We were unable to reproduce the reported penetration depths with realistic values of density [29] in the calculation of 𝑠 0 [9] using the ''billiard ball'' approximation. Therefore, we treat 𝑠 0 as another parameter to be estimated, for which we obtain the value of 3 . 36 ⋅ 10 -19 m 2 . The parameters for each 𝑇 were obtained by manual adjustment and visual comparison to the experimental data and are provided in Table 1. The model comparison to experimental data is given in Fig. 4. The authors of the original work also estimate 𝛽 0 from the slope at 50% height, and those values are reported in Table 1.

In Fig. 4, we note a good agreement between our topography simulations using the combined model for surface coverage and the reported experimental profiles. The estimated values of 𝛽 0 are also generally consistent with the estimated ranges from the original work, which is expected since it also relies on first-order Langmuir kinetics. However, we expect that our methodology provides a more accurate estimate, including on the discrepant value at 150 ◦ C , since we consider the entire profile and we include 𝛤 ev . Nonetheless, it is possible that we overestimate 𝛤 ev since we do not consider the purge step. The reduction in thickness and the less abrupt transition between the region with

Fig. 5. (a) Arrhenius analysis of 𝛽 0 and 𝛤 ev from Table 1. (b) After parameterization to 𝑇 , its effect is investigated in the required 𝑡 𝑝 to reach 95% of saturation, 𝜃 sat at 𝑧 = 𝐿 and SCsat .

<!-- image -->

high growth for that profile is strong evidence of the important role of reversible reactions, which is supported by other modeling studies [16].

Due to the availability of data at different substrate temperatures, we perform an indicative Arrhenius analysis, shown in Fig. 5. In Fig. 5(a), we observe that the 𝛽 0 increases and 𝛤 ev decreases with increasing 𝑇 . This suggests that the increase in temperature not only makes the reaction more efficient but also, counter-intuitively, reduces the reversibility of the reaction. This is the cause of the negative value of 𝐸𝐴 on the Arrhenius fit of 𝛤 ev , which is not itself the true activation energy of the reaction. Instead, we interpret the value of 𝐸𝐴 from the linear fit of 𝛽 0 ( 0 . 178 eV ) as that representing the energy barrier involved in the reaction, since it is the one which must be overcome on a clean surface (i.e., 𝜃 =0 ). Although this value is lower than first-principle studies suggest ( 1 . 101 eV ) [30], it is consistent with a recent experimental analysis exploring a two-stage reaction, where 𝐸𝐴 is estimated as 0 . 166 ± 0 . 02 eV [31]. This two-stage reaction is a possible cause of failure of the ''billiard ball'' approximation for 𝑠 0 .

From the fitted Arrhenius relationships, both model parameters ( 𝛽 0 and 𝛤 ev ) can be expressed as functions of the single physical variable 𝑇 . Thus, the parameter analysis from Fig. 2 can be reduced from three to two dimensions, as shown in Fig. 5(b). We observe that the saturation 𝑡 𝑝 reduces and 𝜃 sat at 𝑧 = 𝐿 increases with higher temperatures, as is expected from a more thermodynamically favorable reaction. However, in many experimental situations 𝜃 is not easily measurable. Instead, the step coverage ( SC ) is commonly measured [25]. After saturation, i.e. 𝑑𝜃 ∕ 𝑑𝑡 = 0 , we estimate the step coverage to be SCsat = 𝜃 sat ( 𝑧 = 𝐿 )∕ 𝜃 sat ( 𝑧 = 0) . Interestingly, we note that SCsat is high and

Table 2 Model parameters for the TMA step of ALD of Al 2 O 3 calibrated to multiple measurements [9,13,32].

| 𝛤 ev ( m -2 s -1 )   | 𝛽 0           | 𝛽 0 from [9]   | 𝛽 0 from [13]         | 𝛽 0 from [32]   |
|----------------------|---------------|----------------|-----------------------|-----------------|
| 3 . 0 ⋅ 10 19        | 7 . 5 ⋅ 10 -3 | 5 . 7 ⋅ 10 -3  | (0 . 5-2 . 0) ⋅ 10 -3 | 4 . 0 ⋅ 10 -3   |

450

Fig. 6. Comparison of simulation with parameters from Table 2 to TMA-limited thickness profiles reported by Ylilammi et al. [9], Arts et al. [13], and Yim and Ylivaara et al. [32].

<!-- image -->

nearly constant for the entire tested temperature range even though 𝜃 sat has a larger variation. Thus, we expect that, at low temperatures, the film quality could be low due to the presence of defects such as vacancies and voids.

## 3.2. The TMA step and geometric parameters

Similarly to Section 3.1, the model is manually calibrated to published thickness profiles of Al 2 O 3 in the TMA-limited regime. Due to the comparatively higher complexity of TMA, this step has received more research attention, therefore, we are able to simultaneously apply our model to multiple independent experiments in similar lateral HAR structures ( 𝑑 = 0 . 5 μm ) [9,13,32]. All available reactor and film parameters were taken directly from the original publications. The unavailable data was estimated as follows: For Ylilammi et al. [9] (and footnotes from [32]), we estimate 𝑝 𝐴 = 325 mTorr ; for Arts et al. [13], 𝑡 𝑝 = 0 . 4 s and 𝜌 Al 2 O3 = 3000 kg∕m 3 ; and for Yim and Ylivaara et al. [32], 𝑝 𝐴 = 160 mTorr .

Since all reported thickness profiles were obtained on a restricted range of set temperatures ( 275 ◦ C in [13], 300 ◦ C otherwise), we manually calibrate our model to all profiles with the same parameter set presented in Table 2, including the estimates of 𝛽 0 from the original works. The disparity is likely due to the effect of 𝛤 ev , which is corroborated by the most similar value being that from [9], whose approach also considers reversible kinetics.

The comparison to the published measured profiles is provided in Fig. 6, showing good agreement. This is strong evidence for the hypothesis discussed in Section 2.1 that the model parameters are determined by the reactor setup, most importantly the reactor 𝑇 . The peaks shown in the experimental data from [32] are disregarded since they are reported to be spurious interactions with the pillars sustaining the structure.

Wereproduce additional experiments by Yim and Ylivaara et al. [32] in lateral HAR structures with different initial openings 𝑑 , shown in Fig. 7. The discrepancy in the structure with 𝑑 = 0 . 1 μm is due to the limits of our model when the opening becomes fully constricted. In this situation, the approximation that the entire geometry can be represented by an evolving but single value of 𝑑 starts to fail. One

Fig. 7. Comparison of simulated structures to profiles reported by Yim and Ylivaara et al. [32] for lateral HAR structures with different initial openings 𝑑 using parameters from Table 2. ''Knudsen'' shows the model using only Knudsen diffusivity, while ''Bosanquet'' includes gas-phase diffusivity.

<!-- image -->

additional limitation is the failure of the hydraulic diameter approximation in a constricted structure, since it is not rigorously justified and has significant discrepancies with regards to established results [28]. For the structure with opening 𝑑 = 2 . 0 μm , pure Knudsen diffusivity is no longer valid, since Kn ≈ 8 . 9 . We recover accuracy by using (4) (marked ''Bosanquet'') which is calculated using the hard-sphere diameters of TMA 𝑑 TMA = 591 pm and of nitrogen (N 2 , the carrier gas) 𝑑 N2 = 374 pm [9].

## 4. Summary and outlook

In this work, we present a surface coverage model for incomplete conformality during ALD in HAR structures based on diffusive particle transport and reversible first-order Langmuir kinetics which combines insights from multiple established modeling approaches. By focusing on the evaporation flux, we achieve a good fit to experimental data and also obtain further chemical insights from the saturation behavior. Also, by approximating the diffusivity with the Bosanquet formula, we are able to capture processing conditions with lower Knudsen numbers. Finally, we present an approach for efficiently integrating our model with a level-set topography simulator by bundling multiple ALD cycles into an artificial time unit.

We manually calibrate our model to reported thickness profiles in the prototypical ALD of Al 2 O 3 from H 2 O and TMA. We study the impact of temperature in H 2 O-limited profiles, indicating the strong impact of the evaporation flux at lower temperatures and extracting an activation energy of 0 . 178 eV which is comparable with recent experimental studies. From calibrating our simulation with a single parameter set to multiple independent experiments in the TMA-limited regime, we strengthen the hypothesis that the parameters are strongly related to the reactor condition, most importantly to its temperature.

Our ALD modeling can be further improved by integrating a more accurate flux calculation methodology such as Monte Carlo ray tracing and additional physical phenomena, such as losses due to recombination, partial decomposition, and the effect of impurities. Since the evaporation flux plays such an important role, the explicit consideration of the purge step can further enhance the model. A more rigorous estimation approach would also enable estimation of the error bounds, which would improve the connections to experimental data. Finally, our robust level-set simulation approach enables the simulation of further processing steps and of process-aware device operation and could be applied to, e.g., atomic layer etching for 3D integration of novel memories.

## Declaration of competing interest

The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.

## Data availability

Data will be made available on request.

## Acknowledgments

The financial support by the Austrian Federal Ministry for Digital and Economic Affairs, the National Foundation for Research, Technology and Development, Austria and the Christian Doppler Research Association, Austria is gratefully acknowledged. This work was supported in part by the Austrian Research Promotion Agency FFG under Project 878662 PASTE-DTCO. The authors acknowledge the TU Wien Bibliothek for financial support through its Open Access Funding Program.

## References

- [1] Cremers V, Puurunen RL, Dendooven J. Conformality in atomic layer deposition: Current status overview of analysis and modelling. Appl Phys Rev 2019;6(2):021302. http://dx.doi.org/10.1063/1.5060967.
- [2] Knoops H, Potts S, Bol A, Kessels W. 27 - Atomic layer deposition. In: Kuech TF, editor. Handbook of crystal growth. 2nd ed. North-Holland; 2015, p. 1101-34. http://dx.doi.org/10.1016/B978-0-444-63304-0.00027-5.
- [3] Jakschik S, Schroeder U, Hecht T, Dollinger G, Bergmaier A, Bartha J. Physical properties of ALD-Al 2 O 3 in a DRAM-capacitor equivalent structure comparing interfaces and oxygen precursors. Mater Sci Eng B 2004;107(3):251-4. http: //dx.doi.org/10.1016/j.mseb.2003.09.044.
- [4] Fischer A, Routzahn A, Gasvoda RJ, Sims J, Lill T. Control of etch profiles in high aspect ratio holes via precise reactant dosing in thermal atomic layer etching. J Vac Sci Technol A 2022;40(2):022603. http://dx.doi.org/10.1116/6.0001691.
- [5] Puurunen RL. Surface chemistry of atomic layer deposition: A case study for the trimethylaluminum/water process. J Appl Phys 2005;97(12):9. http://dx.doi.org/ 10.1063/1.1940727.
- [6] Gobbert MK, Prasad V, Cale TS. Predictive modeling of atomic layer deposition on the feature scale. Thin Solid Films 2002;410(1-2):129-41. http://dx.doi.org/ 10.1016/S0040-6090(02)00236-5.
- [7] Gordon RG, Hausmann D, Kim E, Shepard J. A kinetic model for step coverage by atomic layer deposition in narrow holes or trenches. Chem Vap Depos 2003;9(2):73-8. http://dx.doi.org/10.1002/cvde.200390005.
- [8] Yanguas-Gil A, Elam JW. Self-limited reaction-diffusion in nanostructured substrates: Surface coverage dynamics and analytic approximations to ALD saturation times. Chem Vap Depos 2012;18(1-3):46-52. http://dx.doi.org/10. 1002/cvde.201106938.
- [9] Ylilammi M, Ylivaara OM, Puurunen RL. Modeling growth kinetics of thin films made by atomic layer deposition in lateral high-aspect-ratio structures. J Appl Phys 2018;123(20):205301. http://dx.doi.org/10.1063/1.5028178.
- [10] Szmyt W, Guerra-Nuñez C, Huber L, Dransfeld C, Utke I. Atomic layer deposition on porous substrates: From general formulation to fibrous substrates and scaling laws. Chem Mater 2021;34(1):203-16. http://dx.doi.org/10.1021/ acs.chemmater.1c03164.
- [11] Schwille MC, Schössler T, Schön F, Oettel M, Bartha JW. Temperature dependence of the sticking coefficients of bis-diethyl aminosilane and trimethylaluminum in atomic layer deposition. J Vac Sci Technol A 2017;35(1):01B119. http://dx.doi.org/10.1116/1.4971197.
- [12] Poodt P, Mameli A, Schulpen J, Kessels W, Roozeboom F. Effect of reactor pressure on the conformal coating inside porous substrates by atomic layer deposition. J Vac Sci Technol A 2017;35(2):021502. http://dx.doi.org/10.1116/ 1.4973350.
- [13] Arts K, Vandalon V, Puurunen RL, Utriainen M, Gao F, Kessels WM, et al. Sticking probabilities of H 2 O and Al(CH 3 ) 3 during atomic layer deposition of Al 2 O 3 extracted from their impact on film conformality. J Vac Sci Technol A 2019;37(3):030908. http://dx.doi.org/10.1116/1.5093620.
- [14] Klemenschits X, Selberherr S, Filipovic L. Combined process simulation and simulation of an SRAM cell of the 5nm technology node. In: Proceedings of the international conference on simulation of semiconductor processes and devices (SISPAD). 2021, p. 23-7. http://dx.doi.org/10.1109/SISPAD54002.2021. 9592605.
- [15] Filipovic L. Modeling and simulation of atomic layer deposition. In: Proceedings of the international conference on simulation of semiconductor processes and devices (SISPAD). IEEE; 2019, p. 323-6. http://dx.doi.org/10.1109/SISPAD. 2019.8870462.
- [16] Yim J, Verkama E, Velasco JA, Arts K, Puurunen RL. Conformality of atomic layer deposition in microchannels: Impact of process parameters on the simulated thickness profile. Phys Chem Chem Phys 2022;24(15):8645-60. http://dx.doi. org/10.1039/d1cp04758b.
- [17] Pollard W, Present RD. On gaseous self-diffusion in long capillary tubes. Phys Rev 1948;73(7):762. http://dx.doi.org/10.1103/PhysRev.73.762.
- [18] Sethian JA. Level set methods and fast marching methods. 2nd ed. Cambridge University Press; 1999.
- [19] Klemenschits X, Selberherr S, Filipovic L. Modeling of gate stack patterning for advanced technology nodes: A review. Micromach 2018;9(12):631. http: //dx.doi.org/10.3390/mi9120631.
- [20] ViennaLS. Available online: https://viennatools.github.io/ViennaLS [accessed 08 June 2022].
- [21] Silvaco. Victory Process. Available online: www.silvaco.com/tcad/victoryprocess-3d/ [accessed 08 June 2022].
- [22] Keuter T, Menzler NH, Mauer G, Vondahlen F, Vaßen R, Buchkremer HP. Modeling precursor diffusion and reaction of atomic layer deposition in porous structures. J Vac Sci Technol A 2015;33(1):01A104. http://dx.doi.org/10.1116/ 1.4892385.
- [23] Yanguas-Gil A, Libera JA, Elam JW. Reactor scale simulations of ALD and ALE: Ideal and non-ideal self-limited processes in a cylindrical and a 300 mm wafer cross-flow reactor. J Vac Sci Technol A 2021;39(6):062404. http://dx.doi.org/ 10.1116/6.0001212.
- [24] Fang W-Z, Tang Y-Q, Ban C, Kang Q, Qiao R, Tao W-Q. Atomic layer deposition in porous electrodes: A pore-scale modeling study. Chem Eng J 2019;378:122099. http://dx.doi.org/10.1016/j.cej.2019.122099.
- [25] Yanguas-Gil A. Growth and transport in nanostructured materials: Reactive transport in PVD, CVD, and ALD. Springer; 2016.
- [26] Chapman S, Cowling TG. The mathematical theory of non-uniform gases. 3rd ed. Cambridge University Press; 1991.
- [27] Knudsen M. Eine Revision der Gleichgewichtsbedingung der Gase. Thermische Molekularströmung. Annalen Der Physik 1909;336:205-29. http://dx.doi.org/10. 1002/ANDP.19093360110.
- [28] Steckelmacher W. Knudsen flow 75 years on: The current state of the art for flow of rarefied gases in tubes and systems. Rep Prog Phys 1986;49(10):1083. http://dx.doi.org/10.1088/0034-4885/49/10/001.
- [29] Ylivaara OM, Liu X, Kilpi L, Lyytinen J, Schneider D, Laitinen M, et al. Aluminum oxide from trimethylaluminum and water by atomic layer deposition: The temperature dependence of residual stress, elastic modulus, hardness and adhesion. Thin Solid Films 2014;552:124-35. http://dx.doi.org/10.1016/j.tsf.2013.11.112.
- [30] Seo S, Nam T, Kim H, Shong B, et al. Molecular oxidation of surface-CH 3 during atomic layer deposition of Al 2 O 3 with H 2 O, H 2 O 2 , and O 3 : A theoretical study. Appl Surf Sci 2018;457:376-80. http://dx.doi.org/10.1016/j.apsusc.2018.06.160.
- [31] Sperling BA, Kalanyan B, Maslar JE. Atomic layer deposition of Al 2 O 3 using trimethylaluminum and H 2 O: The kinetics of the H 2 O half-cycle. J Phys Chem C 2020;124(5):3410-20. http://dx.doi.org/10.1021/acs.jpcc.9b11291.
- [32] Yim J, Ylivaara OM, Ylilammi M, Korpelainen V, Haimi E, Verkama E, et al. Saturation profile based conformality analysis for atomic layer deposition: Aluminum oxide in lateral high-aspect-ratio channels. Phys Chem Chem Phys 2020;22(40):23107-20. http://dx.doi.org/10.1039/d0cp03358h.