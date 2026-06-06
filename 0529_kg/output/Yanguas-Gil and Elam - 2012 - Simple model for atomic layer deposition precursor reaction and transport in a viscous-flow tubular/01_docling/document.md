<!-- image -->

## Simple model for atomic layer deposition precursor reaction and transport in a viscous-flow tubular reactor 

Angel Yanguas-Gil; Jeffrey W. Elam

<!-- image -->

Check for updates

30, 01A159 (2012)

J. Vac. Sci. Technol. A

https://doi.org/10.1116/1.3670396

## Articles You May Be Interested In

Metallic molybdenum obtained by atomic layer deposition from Mo(CO) 6

J. Vac. Sci. Technol. A (February 2025)

Resolving self-limiting growth in silicon nitride plasma enhanced atomic layer deposition with trisdimethylamino silane precursor

J. Vac. Sci. Technol. A (October 2020)

Reactor scale simulations of ALD and ALE: Ideal and non-ideal self-limited processes in a cylindrical and a 300 mm wafer cross-flow reactor

J. Vac. Sci. Technol. A (September 2021)

<!-- image -->

<!-- image -->

<!-- image -->

<!-- image -->

## Simple model for atomic layer deposition precursor reaction and transport in a viscous-flow tubular reactor

Angel Yanguas-Gil and Jeffrey W. Elam a)

Energy Systems Division, Argonne National Laboratory, 9700 S Cass Avenue, Argonne, Illinois 60439

(Received 17 August 2011; accepted 22 November 2011; published 28 December 2011)

Precursor reaction and transport are both critical in determining the thickness uniformity and conformality of atomic layer deposition (ALD) thin films. However, it is sometimes difficult to predict how changes in conditions, such as mass flow rate or precursor reactivity, will affect the outcome of an ALD experiment. To provide some insight and guidance, we have developed a simple 1D model to describe precursor transport and reaction in a tubular viscous flow ALD reactor. After making some simplifying assumptions, we show that the transport problem depends only on three independent parameters, the Peclet number, the Damkoeler number, and the excess number, which can be easily calculated for most ALD processes. Despite its simplicity, we obtain very good agreement with experimental results for the thickness profiles of ALD Al2O3 films deposited using trimethyl aluminum and H2O. The authors have applied the model to study the impact of precursor properties and experimental conditions on the growth profiles and saturation curves obtained during ALD, including the presence of nonself-limited wall recombination. V C 2012 American Vacuum Society . [DOI: 10.1116/1.3670396]

## I. INTRODUCTION

One of the great advantages of atomic layer deposition (ALD) is that its self-limited nature allows the uniform coating of high area substrates, 1,2 thus providing an easier pathway for process scale up compared to chemical vapor deposition (CVD), where reactor gradients are a natural consequence of the process as well as an engineering concern. 3-5 However, precursor transport still plays an important role in ALD, since the fundamental requirement for growth uniformity is attaining surface saturation, which requires adequate precursor delivery.

There are many examples of nonuniform film thickness profiles in ALD: they are observed for reactants exhibiting nonsaturating wall recombination, such ozone during the growth of some transition metal oxides and atomic species in radical-enhanced and plasma-enhanced ALD. 6 Nonuniform film thickness profiles can also result from precursor depletion, which can be a concern for low vapor pressure precursors, or from self-poisoning by reaction byproducts. 7

Compared to CVD, the literature on precursor reaction modeling in ALD is scarce. Most of the works in ALD either involve complex computational flow dynamics or are extremely reactor/process dependent. 8-12 While these models can provide quantitative descriptions of well-specified ALD processes, their complexity hampers the extraction of general principals from the modeling results that can ultimately provide a more complete understanding. Two exceptions are the works of Ylilammi, who developed a general model of precursor transport in the plug-flow approximation, 13 and Knoops et al. , who carried out simulations based on the plug-flow limit to determine the impact of ozone decomposition in ALD thickness profiles. 14 In contrast, precursor transport and deposition in high aspect ratio and high

a) Author to whom correspondence should be addressed; electronic mail: jelam@anl.gov

surface area features have been extensively studied using simple kinetic Monte Carlo simulations, line of sight models, differential equations, and analytic results. 15-21 Consequently, there is a good understanding of the factors governing ALD in high aspect ratio or high surface-area substrates.

The purpose of this work is to describe a simple model of ALD precursor reaction and transport that: (1) provides good agreement with experimental data, (2) is simple enough to allow a clear identification of the links between growth conditions/precursor properties and coverage profiles, and (3) is easily extensible to more complex chemistries. We apply our model to a hot-wall tubular viscous flow reactor. This kind of ALD reactor is widely used in the ALD literature. 22 Finally, we compare the model results with experimental thickness profiles obtained for Al2O3 ALD using trimethyl aluminum (TMA) and water.

## II. EXPERIMENT

The ALD films were deposited in a custom viscous flow tubular reactor. Details of the experimental setup can be found elsewhere. 22 Ultrahigh purity nitrogen (99.999%) carrier gas was used at a mass flow rate of 300 sccm and a pressure of 1 Torr. Trimethyl aluminum (TMA) and titanium tetraisopropoxide (TTIP) were purchased from Aldrich and used as received. Aluminum oxide (Al2O3) films were deposited by ALD using alternating exposures to TMA and deionized H2O. Titanium dioxide films were grown using TTIP and deionized H2O. The ALD timing sequences can be expressed as t1-t2-t3-t4 where t1 is the TMA exposure time, t2 is the purge time following the TMA exposure, t3 is the H2O exposure time, and t4 is the purge time following the H2O exposure with all units in seconds (s). This work used the timing sequences, x-5-1-5 s.

To measure the Al2O3 reactor coverage profiles, 10 Si(100) substrates were uniformly spaced along a 45 cm long tray and placed inside of the reactor flow tube. The Al2O3

ALD was performed using 200 cycles of TMA/H2O at a deposition temperature of 200 /C14 C. These experiments used a TMA partial pressure of 10 mTorr and a H2O partial pressure of /C24 200 mTorr to ensure that the degree of TMA saturation was dictating the film thickness profiles. TiO2 profiles were determined in a similar fashion, using 300 cycles of TTIP/H2O at 200 /C14 C. The TTIP was contained in a stainless steel bubbler at a temperature of 45 /C14 C and 60 sccm of ultrahigh purity nitrogen was diverted through the bubbler during the TTIP exposures.

Ex-situ thickness measurements were carried out using a J. A. Woollam Co. Alpha-SE spectroscopic ellipsometer, with precalibrated optical models for Al2O3 and TiO2. The optical properties were kept fixed during the fitting procedures.

## III. MODELING

Our model is based on the assumption that the partial pressure of the precursor is much lower than the carrier gas. Then, we can decouple flow from mass transport and, if the carrier gas flow remains approximately constant during the dose and purge times, we can solve the flow equations for the carrier gas under steady-state conditions despite the pulsed nature of ALD. This is a good approximation of the experimental setup used in this work where the carrier gas flow is kept constant during the ALD.

The mass transport is controlled by the continuity equation for the precursor density:

<!-- formula-not-decoded -->

Here, n is the precursor density, r is the (vector) position inside the tube, D is the diffusion coefficient, and u ð r Þ is the velocity field. The precursor flow to the walls must match the losses due to surface reaction. Therefore, a general boundary condition is used:

/C12

<!-- formula-not-decoded -->

where Jwall is the flow to the walls per unit area, vth is the thermal mean velocity vth ¼ ffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffi ffi 8 kT = p M ð Þ p , and b ð r s ; t Þ is the precursor reaction probability for each wall position, r s . In atomic layer deposition b is coverage-dependent. For instance, assuming first order irreversible Langmurian behavior, we have:

<!-- formula-not-decoded -->

where h ð r s ; t Þ is the fractional coverage of available sites and b 0 is the reaction probability on a bare surface. In order to track the changes in surface coverage with time, we need a second differential equation, which implicitly depends on the surface position, r s :

<!-- formula-not-decoded -->

Here, s0 is the average area of a precursor adsorption site. In the more general case, we have a set of equations:

<!-- formula-not-decoded -->

with a more general boundary condition:

<!-- formula-not-decoded -->

where Gi ð r s ; t Þ represents a gain term for species that are generated as byproducts of surface reactions. These equations would be coupled to a set of balance equations for each adsorbed species in the surface:

<!-- formula-not-decoded -->

where f j ð h k ; ni Þ contains the gain and loss terms of the chemisorbed species k . These generalized equations could be used in cases where multiple species are required, for instance to model the influence of reaction by-products or in co-dosing experiments.

For complex reactor geometries, u ð r ; t Þ would be determined by solving the Navier-Stokes equation, coupled to an energy balance equation to account for thermal transport if thermal gradients are present. However, this picture can be simplified even further if we consider a high aspect-ratio, tubular reactor such as that described in Sec. II. Then, under a fully developed flow approximation the flow is purely axial and does not depend on the axial coordinate, so that Eq. (1) reduces to:

<!-- formula-not-decoded -->

If we now radially average Eq. (5), we end up with the following equation:

<!-- formula-not-decoded -->

where R is the reactor radius. Using the boundary condition, Eq. (2), we finally obtain:

<!-- formula-not-decoded -->

where h is the fraction of available sites. Equation (7) is coupled to the surface kinetics equation:

<!-- formula-not-decoded -->

Normalizing Eqs. (7) and (8), so that x ¼ n = n 0 , n ¼ z = L , and s ¼ tD = L 2 , where n 0 is the initial precursor density and L is the tube length, we obtain:

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

Equations (9) and (10), along with their corresponding boundary conditions x ð 0 ; s Þ , x ð n L ; s Þ and initial conditions x ð n ; 0 Þ and h ð n ; 0 Þ , represent a generalization of the plugflow approximations developed by Ylilammi 13 and Knoops et al. 14 to account for the influence of axial diffusion.

Thus, the transport depends only on three independent parameters: the Peclet number ( Pe ), the Damkoeler number ( Da ), and the excess number ( c ). These are given by:

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

The Peclet number measures the relative importance of convection to axial diffusion transport. The Damkoler number represents the ratio between transport and reaction characteristic times. 23 Finally, The excess number represents the number of precursor molecules inside the reactor tube per unit absorption site. Pe , Da , and c can be obtained from the experimental conditions and the precursor physical properties. For instance, the axial velocity, u , can be obtained from the carrier gas flow and pressure through the equation:

<!-- formula-not-decoded -->

where p , T , and u are the carrier gas pressure, growth temperature, and mass flow rate, and p 0 and T 0 correspond to atmospheric pressure and room temperature, respectively. Likewise, the diffusion coefficient can be determined using the Chapman-Engskop approximation: 23

/C20

/C18

/C19

/C21

<!-- formula-not-decoded -->

Where M and M 0 are the precursor and carrier gas molecular mass, X ð kT = e Þ /C25 1 : 12 kT = e ð Þ /C0 0 : 17 , and r 2 and e are two parameters that depend on the precursor-carrier gas interaction potential. Two representative values of these parameters are r ¼ 3 : 5 A ˚ and X /C25 0 : 5, 23 and they can be used whenever the interaction potential is not available.

Figure 1 summarizes the influence of the experimental conditions on these three parameters. Pe depends mainly on the reactor radius and mass flow rate. Da is proportional to the reaction probability and carrier gas pressure, while the excess number, c , is proportional to the precursor pressure and the reactor radius. As shown in Fig. 1, Pe numbers are around 100 under typical ALD conditions, while Da and c can vary by many orders of magnitude depending on the reaction probability and the precursor partial pressure inside the reactor tube.

In this work we have solved Eqs. (9) and (10) using a central finite difference scheme where the uniform spatial discretization step, D n , has been selected so that Pe D n &lt; 0 : 1. This minimizes the error of the central difference scheme for a convection-diffusion equation. 24 The time evolution of both Eqs. (9) and (10) is solved using a fully implicit scheme except for the nonlinear term, which is linearized by approximating the h x term by h ð s /C0 D s Þ x ð s Þ in Eq. (9). The time increment D s is chosen so that D s ¼ 0 : 2 ð D n Þ 2 .

We have used the following initial conditions:

<!-- formula-not-decoded -->

<!-- formula-not-decoded -->

We have assumed a square precursor pulse with a variable dose time, s 0, so that:

/C26

<!-- formula-not-decoded -->

and x ð1 ; s Þ ¼ 0, where infinity is taken as a distance much larger than 1. Typically, we have used n ð1Þ ¼ 10 and a discretization step of D n ¼ 0 : 002.

Figure 2 shows the comparison of the numerical results against analytic solutions that can be obtained in the pure nonself-limiting case, that is, in the CVD mode given by the convection-diffusion-reaction equation:

<!-- formula-not-decoded -->

By directly solving Eq. (16) using Laplace transforms, the following analytic solution for initial conditions x ð n ; 0 Þ ¼ 0, first order boundary condition x ð 0 ; s Þ ¼ 1 at the reactor entrance, and zero density at the infinite x ð1 ; s Þ ¼ 0 is obtained:

FIG. 1. Influence of experimental parameters on the Peclet, Excess, and Damkoeler numbers. Peclet and Excess number curves are shown for 1, 2.5, and 5 cm radius tubular reactors. Damkoler numbers are shown for carrier gas pressures of 0.5, 1, 2, and 3 Torr.

<!-- image -->

FIG. 2. Comparison of relative thickness vs relative position between numerical simulations (full curves) and analytic results (symbols) for a convection-diffusion-reaction model with a first order nonsaturating reaction term. Normalized growth times are 0.001 (circles), 0.005 (squares) and 0.1 (triangles).

<!-- image -->

<!-- formula-not-decoded -->

where erfc ð/C14Þ is the complementary error function and ffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffiffi

s

<!-- formula-not-decoded -->

Figure 2 shows excellent agreement between the numerical solution (full lines) and the analytic result (symbols) for s 0 ¼ 0.001, 0.005, and 0.1, thus validating our discretization scheme to numerically solve the partial differential equation.

## IV. RESULTS AND DISCUSSION

## A. Comparison with experimental results and influence of model parameters

By solving Eqs. (9) and (10) we can obtain relative film thickness, or coverage profiles along our tubular reactor as a function of the three normalized parameters Pe , Da , and c . Values of these parameters are related to experimental conditions through Eqs. (11)-(15) and Fig. 1. Of these, Pe is essentially a function of the experimental conditions and the reactor geometry. Da and c , on the other hand, strongly depend on the precursor properties.

In order to evaluate the simulation results, we measured the coverage profiles for ALD Al2O3 films deposited using 200 cycles of TMA and H2O with the experimental setup described above. These experiments were carried out at 200 /C14 C with a total flow of 300 sccm, a N2 carrier gas pressure of 1 Torr, a TMA partial pressure of 10 mTorr, and a H2O partial pressure of /C24 200 mTorr.

Our model requires estimates for the precursor diffusion coefficient and the reaction probability. For the diffusion coefficient, we used the Chapman-Engskop expression defined in Eq. (15). To our knowledge, r 2 and e have not been experimentally determined for for TMA/N2. Thus, we used the representative values indicated in Sec. III. For the reaction probability we used 10 /C0 2 . 16 For the conditions described above, and using our reactor geometry (R ¼ 2.5 cm, L ¼ 45cm), we obtain the values: Pe ¼ 65, Da ¼ 1550, and c ¼ 2.5.

The experimentally measured Al2O3 thickness profiles and the results from the model are presented in Fig. 3. The agreement is remarkable considering: (1) no fitting parameters were used; (2) the model does not take into account any time delay for precursor transport or precursor depletion in the reactor inlet; (3) the diffusion coefficient has been estimated using average values for the interaction potential with N2; (4) a first order Langmuirian behavior is used to model the surface kinetics; and (5) the effect of radial diffusion is neglected by the radially averaging procedure.

As a comparison, in Fig. 4 we show growth profiles for TTIP/H2O as a function of the TTIP dose time. Not only are the reactor profiles markedly different from those obtained for TMA/H2O, but also the saturation times are longer. Two parameters that differ from the TMA case are the reaction probability and the precursor partial pressure (estimated to be 5mTorr for TTIP in our system).

Our model allows us to rationalize the differences between the TMA/H2O and the TTIP/H2O coverage profiles in terms of the nondimensional parameters described above. In particular, the Da parameter is proportional to the precursor reaction probability. Figure 5 shows model coverage profiles obtained for the following dose times: s 0 ¼ 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, and 0.05. It is apparent that higher Da numbers lead to steeper coverage profiles and a distinct growth front that moves along the reactor tube, a situation similar to the TMA case. As Da decreases, the profiles become less steep and coverage saturation is reached more evenly in the reactor, but it also takes longer to achieve saturation. The profiles for Da ¼ 100 and 10 shown in Fig. 5 are closer to the TTIP/H2O measurements, suggesting that TTIP has a lower surface reaction probability than TMA at 200 /C14 C.

FIG. 3. Comparison of experimental (a) and simulated (b) thickness profiles during Al2O3 ALD using TMA and H2O at 200 /C14 C. Experimental TMA dose times are 200, 300, 500, and 1000 ms.

<!-- image -->

FIG. 4. Experimental profiles during TiO2 ALD using TTIP and H2O at 200 /C14 C. TTIP dose times are 1, 2, 5 and 8 s.

<!-- image -->

Figure 6 shows the influence of Da on the reactor coverage profiles when the excess number, c , is low. The excess number is essentially the number of precursor molecules in the reactor tube per reaction site. As c decreases, longer dose times are required to achieve saturation. More importantly, as shown in Fig. 6, when c is low, two different situations are possible depending on the value of Da : high Da numbers lead to a regime where saturation is achieved only at the front of the reactor creating a strong coverage gradient. On the other hand, lower Da numbers lead to undersaturated growth everywhere in the reactor with gentler gradients. From a practical point of view, the model results suggest that, for low vapor pressure precursors, saturation at the front of the reactor can be promoted by increasing the Damkoler number, for instance by increasing the carrier gas pressure at constant flow rate (i.e., by throttling the pumping inside the reactor).

Finally, higher Pe numbers allow for faster precursor delivery along the tube, leading to a faster propagation of the growth front. This could be achieved experimentally by hav-

FIG. 5. Influence of Damkoler number on theoretical relative thickness profiles ( Pe ¼ 50, c ¼ 10).

<!-- image -->

FIG. 6. Influence of Damkoeler number on theoretical relative thickness profiles at low excess numbers ( Pe ¼ 50).

<!-- image -->

ing a higher pumping capacity that allows higher flows for the same carrier gas and precursor pressures.

## B. Generalization to more complex reaction kinetics

As shown in the previous section, our reaction and transport model can be generalized to incorporate more complex chemistries that are sometimes encountered in ALD processes. As shown by Puurunen et al. , 2 multiple adsorption kinetics can be possible, including the presence of a reversible adsorption-desorption step that effectively incorporates a pressure-dependent bare reaction probability. Another example is growth inhibition due to the adsorption of reaction byproducts. 25,26

One situation of technological relevance is the presence of nonself-limiting deactivation processes, such as the wall recombination of ozone, hydrogen peroxide, or atomic species used in radical-enhanced and plasma-enhanced ALD. 14 In this case, Eq. (9) is modified by adding a nonself-limited loss term, so that:

<!-- formula-not-decoded -->

Where Darec is the analagous to the Da term given in Eq. (12), but for a surface recombination probability, b rec .

Figure 7 shows the influence of increasing wall recombination, Darec , on the relative thickness profiles for a high value of Da ¼ 1000. As a consequence of the wall recombination, the saturation front propagates more slowly than in the pure self-limited case. However, since high Da corresponds to a high reaction probability of the self-limited process, saturation is still reached at the front of the reactor.

The situation is different when the ALD process is characterized by a low reaction probability ( Da ¼ 10). As shown in Fig. 8, under these conditions the profiles change from being almost completely homogeneous along the reactor in the absence of losses to essentially an exponential decay in surface coverage when the wall recombination probability is high. In the later case, the growth profiles are similar to the

FIG. 7. Influence of wall recombination on the relative thickness profiles for large Damkoler numbers ( Pe ¼ 50, Da ¼ 1000, c ¼ 10).

<!-- image -->

CVD case shown in Fig. 2. Under these conditions, the saturation behavior and surface coverage is controlled by the nonself-limited wall recombination process.

## C. Discussion

The results presented in the preceding sections show that decoupling mass transport from flow dynamics is a reasonable approximation for modeling the transport-reaction process in tubular, laminar flow ALD reactors. Likewise, the agreement with the experimental results indicates that, despite their simplicity, 1D models can be useful tools for understanding ALD in tubular reactors.

FIG. 8. Influence of wall recombination on the relative thickness profiles for small Damkoler numbers ( Pe ¼ 50, Da ¼ 10, c ¼ 10).

<!-- image -->

Another consequence of the results presented above is that mass transport can greatly affect the saturation dynamics. Thus, care should be taken when extracting surface reaction kinetic information from saturation curves based on dosing studies: precursor transport can lead to saturation curves that differ greatly from the exponential function expected for first-order Langmuir behavior, and in some conditions they become strongly dependent on the axial position. Only when precursor depletion can be neglected will the saturation curves reflect the underlying surface kinetics.

While Da and c depend on precursor properties, Pe is mostly dependent on the experimental configuration. Two interesting limiting cases are static dosing ( Pe ¼ 0) and plug-flow ( Pe /C29 1) where the contribution of axial diffusion can be neglected. In the first case, the convecting term in Eq. (11) is the same, and the equations formally resemble the continuum approximation recently developed for coating nanostructured substrates. 21 The only difference is that in the nanostructured substrate case the transport is determined by Knudsen diffusion.

When the axial diffusion is neglected, the following first order differential equation is obtained:

<!-- formula-not-decoded -->

and its equivalent nondimensional version results:

<!-- formula-not-decoded -->

Here, s 0 ¼ u = L ð Þ t , and the characteristic time is the residence time of the precursor inside the reactor instead of the diffusion time for the full model. Likewise, Da 0 still represents the ratio between the characteristic transport and reaction times, with the transport time determined by the residence time L = u . This limit corresponds to the model developed by Ylilammi. 13 Also, plug-flow simulations were recently used by Knoops et al. to model ZnO growth profiles in a tubular viscous flow reactor. 14 The numerical solution of Eqs. (18) and (10) would be formally equivalent to the models developed in both works. The plug-flow approximation is valid as long as axial diffusion can be neglected when compared with axial convection. However, this approximation will break down depending on the average flow and also on the presence of steep precursor gradients inside the reactor. These gradients will amplify the role of axial diffusion and are likely to be more important at the beginning and the end of the dose pulse.

Finally, we would like to discuss the influence of radial averaging on the model coverage profiles. One of the main advantages of performing a cross sectional average of the different variables is that the resulting 1D model can be easily solved. This allows a fast exploration of the parameter space. The main consequence of this procedure is an underestimation of axial diffusion: in a full 2D picture, streams at the center of the reactor move at twice the average velocity, allowing precursor molecules to move faster and then diffuse laterally. This may be an additional source for broadening of

the axial gradients that is not considered in the 1D model. While we have shown that the agreement between the simple model for atomic layer deposition precursor reaction and transport (SMART) model and the ALD Al2O3 experiments is very good, the broader experimental profiles shown in Fig. 3 compared to the model results could be a consequence of the limitation of the 1D approximation. We expect that more computationally intensive modeling of the carrier gas flow will help us better understanding the dynamics of gas mixing and the role of diffusion in precursor transport during ALD.

## V. SUMMARYAND CONCLUSIONS

We have developed a simple 1D model that is able to describe precursor transport and reaction in a tubular viscous flow ALD reactor. Despite its simplicity, good agreement is obtained with experimental results on Al2O3 ALD using TMA and H2O. We have applied the model to study the impact of precursor properties and experimental conditions on the growth profiles and saturation curves obtained during ALD, including the presence of nonself-limited wall recombination. One of the advantages of the SMART model is that it can incorporate arbitrarily complex surface reactions. Two situations of practical interest are high surface area substrates and surface poisoning by reaction byproducts and both cases will be described in future work. Both the full model and the plug flow approximation for the SMART model are available for download from the site: http://www.es.anl.gov/ald/smart.

## ACKNOWLEDGMENTS

This work was supported in part by the U.S. Department of Energy, Office of Energy Efficiency and Renewable Energy, Industrial Technologies Program under Grant No. FWP-4902A. J.W.E. was supported by the ArgonneNorthwestern Solar Energy Research (ANSER) Center, an Energy Frontier Research Center funded by the U.S. Department of Energy, Office of Science, Office of Basic Energy Sciences, under Grant No. DE-SC0001059. Argonne is a U.S. Department of Energy Office of Science Laboratory, and is operated under Grant No. DE-AC02-06CH11357 by UChicago Argonne, LLC.

- 1 M. Leskela and M. Ritala, Thin Solid Films 409 , 138 (2002).
- 2 R. L. Puurunen, J. Appl. Phys. 97 , (2005).
- 3 W. L. Holstein, Prog. Cryst. Growth Charact. 24 , 111 (1992).
- 4 K. L. Knutson, R. W. Carr, W. H. Liu, and S. A. Campbell, J. Cryst. Growth 140 , 191 (1994).
- 5 H. Komiyama, Y. Shimogaki, and Y. Egashira, Chem. Eng. Sci. 54 , 1941 (1999).
- 6 A. B. F. Martinson, M. J. DeVries, J. A. Libera, S. T. Christensen, J. T. Hupp, M. J. Pellin, and J. W. Elam, J. Phys. Chem. C 115 , 4333 (2011).
- 7 K. E. Elers, T. Blomberg, M. Peussa, B. Aitchison, S. Haukka, and S. Marcus, Chem. Vap. Deposition 12 , 13 (2006).
- 8 R. A. Adomaitis, J. Cryst. Growth 312 , 1449 (2010).
- 9 V. Dwivedi and R. A. Adomaitis, 2009 American Control Conference (IEEE, New York, 2009), Vols. 1-9, pp. 2495-2500.
- 10 A. M. Lankhorst, B. D. Paarhuis, H. Terhorst, P. Simons, and C. R. Kleijn, Surf. Coat. Technol. 201 , 8842 (2007).
- 11 G. Prechtl, A. Kersch, G. S. Icking-Konert, W. Jacobs, T. Hecht, H. Boubekeur, and U. Schroder, 2003 IEEE International Electron Devices Meeting, Technical Digest (IEEE, New York, 2003), pp. 245-248.
- 12
- S. G. Webster, M. K. Gobbert, J. F. Remacle, and T. S. Cale, Euro-Par 2002 Parallel Processing, Proceedings , edited by B. Monien and R. Feldmann (Springer, Berlin, Germany, 2002), Vol. 2400, pp. 452-456.
- 13 M. Ylilammi, J. Electrochem. Soc. 142 , 2474 (1995).
- 14 H. C. M. Knoops, J. W. Elam, J. A. Libera, and W. M. M. Kessels, Chem. Mater. 23 , 2381 (2011).
- 15 J. Dendooven, D. Deduytsche, J. Musschoot, R. L. Vanmeirhaeghe, and
- C. Detavernier, J. Electrochem. Soc. 156 , P63 (2009).
- 16 J. W. Elam, D. Routkevitch, P. P. Mardilovich, and S. M. George, Chem. Mater. 15 , 3507 (2003).
- 17 M. K. Gobbert, V. Prasad, and T. S. Cale, J. Vac. Sci. Technol. B 20 , 1031 (2002).
- 18 R. G. Gordon, D. Hausmann, E. Kim, and J. Shepard, Chem. Vap. Deposition 9 , 73 (2003).
- 19 W. Jacobs, A. Kersch, G. Prechtl, and G. S. Icking-Konert, Simulation of Semiconductor Processes and Devices , edited by G. Wachutka and G. Schrag (Springer, Wien, Austria, 2004), pp. 137-140.
- 20 H. C. M. Knoops, E. Langereis, M. C. M. van de Sanden, and W. M. M. Kessels, J. Electrochem. Soc. 157 , G241 (2010).
- 21 A. Yanguas-Gil and J. W. Elam, 'Self-limited reaction-diffusion in nanostructured substrates: surface coverage dynamics and analytic approximations to ALD saturation times,' Chem. Vap. Deposition (to be published).
- 22 J. W. Elam, M. D. Groner, and S. M. George, Rev. Sci. Instrum. 73 , 2981 (2002).
- 23 D. E. Rosner, Transport Processes in Chemically Reacting Flow Systems (Dover New York, 2000).
- 24 C.-P. Hong, Computer Modelling of Heat and Fluid Flow in Materials Processing . (Institute of Physics, Bristol, 2004).
- 25 M. Ritala, M. Leskela, L. Niinisto, and P. Haussalo, Chem. Mater. 5 , 1174 (1993).
- 26 A. Yanguas-Gil, K. E. Peterson, and J. W. Elam, Chem. Mater. 23 , 4295 (2011).