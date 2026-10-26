# Extracted verbatim from original/ReactionModel.ipynb (Larry), section "Coupled", cells 71, 73, 75, 77, 79, 82, 84, 86.
# Every later change is listed in CHANGELOG.md and is one git commit.

# ---- notebook cell 71 ----
import numpy as np
from scipy.constants import Boltzmann as kB
from scipy.constants import N_A, R
from scipy.integrate import solve_ivp
from scipy.sparse import lil_matrix
from scipy.linalg import solve_banded   # C10
import torch
import torch.nn as nn

# ---- notebook cell 73 ----
def torr_to_pa(p_torr):
    return p_torr * 133.322

def axial_velocity(flow_sccm, p_torr, T, R):
    """Eq. (14): u = (p0 T phi) / (p T0 pi R^2), phi in sccm."""
    p0, T0 = 101325.0, 273.15          # standard conditions for sccm
    phi = flow_sccm * 1e-6 / 60.0      # sccm -> m^3/s at STP
    p = torr_to_pa(p_torr) #p_torr * 133.322
    return p0 * T * phi / (p * T0 * np.pi * R ** 2)

def adsorption_area(b_film=2.0, rho=3990.0, gpc=106e-12, M=101.96e-3):
    return M/(b_film * rho*gpc)

def particle_velocity(M, T):
    return np.sqrt(8*kB*T/(np.pi*M))

# ---- notebook cell 75 ----
class Reactant:
    def __init__(self, vth, M):
        self.vth = vth
        self.M = M

    def diffusion_coefficient(self, M0, p, T):
        sigma, omega = 3.5, 0.5
        D = 3 / (8*np.sqrt(2*np.pi)) * (kB * T)**(3/2) * (1/self.M + 1/M0)**(1/2) / (p * (sigma * 1e-10)**2 * omega)
        self.D = D
        return self.D

class Reactor_1D:
    def __init__(self, Pe=None, D=None):


        self.x_rhs = {} #if Da is None else Da
        self.th_rhs = {} #if gamma is None else gamma

        self.D = {} if D is None else D
        self.reactants = {}

    def set_reactor_parameters(self, T, L, R, V=None):
        self.T = T
        self.L = L
        self.R = R
        self.V = V if V is not None else np.pi * R ** 2 * L

    def set_surface_parameters(self, S):
        #self.s0 = s0
        self.S = S

    def set_carrier_parameters(self, flow_sccm, M0, p=None, p_torr=None):
        self.flow_sccm = flow_sccm
        self.p = p if p is not None else torr_to_pa(p_torr)
        self.M0 = M0
        self.u = axial_velocity(self.flow_sccm, self.p / 133.322, self.T, self.R)   # R1: axial_velocity expects Torr

    def set_reactant_parameters(self, id, vth, M, s0):
        self.reactants[id] = Reactant(vth, M)
        R_i = self.reactants[id]
        self.D[id] = R_i.diffusion_coefficient(self.M0, self.p, self.T)
        self.x_rhs[id] = (self.S/self.V)*(R_i.vth)/(4)
        self.th_rhs[id] = (s0*R_i.vth)/4 / (R * self.T)   # R3: p [Pa] -> mol/m3

# ---- notebook cell 77 ----
class ReactorSetupProfile:

    def __init__(self, z=None, tau=None, x=None, theta=None):
        self.z = z
        self.tau = tau
        self.theta = {} if theta is None else theta
        self.x = {} if x is None else x

    def construct_time_profile(self, tau_end, D, dz=None, n_out=None):
        if n_out is None:
            if dz is None:
                if self.dz is None:
                    dz = 0.1
                    print('No dz found or provided.')
                else:
                    dz = self.dz
            dt = (0.2 * dz**2)/D
            t_steps = tau_end // dt
            self.dt = dt
            self.tau = dt * np.arange(0, int(t_steps) + 1)
        else:
            self.tau = np.linspace(0, tau_end, n_out)

    def construct_space_profile(self, z_max, u_D=None, n_z=None, min_z=100):
        #where u_D is u/D
        if n_z is None:
            d = 0.1/u_D
            n = int(np.ceil(z_max/d))
        else:
            n = int(n_z)
        z = np.linspace(0.0, z_max, n + 1)
        d = z[1] - z[0]

        self.z = z
        self.dz = d

    def initialize_theta(self, id, n=None, theta=None, initial_theta=0.0):
        if n is None:
            if self.z is None:
                raise ValueError("z not defined")
            else:
                n = len(self.z)
        elements = n+1 if INCLUSIVE_THETA else n-1
        if theta is None:
            self.theta[id] = np.full(elements, float(initial_theta))
        else:
            if n is not None:
                assert len(theta) == (elements)
            self.theta[id] = theta

    def initialize_x(self, id, n=None, x=None, initial_x=0.0):
        if n is None:
            if self.z is None:
                raise ValueError("xi not defined")
            else:
                n = len(self.z)

        if x is None:
            self.x[id] = np.full(n - 1, float(initial_x))
        else:
            if n is not None:
                assert len(x) == (n - 1)
            self.x[id] = x

    def flat_input_array(self):
        items = []
        for RC in self.x:
            items.append(self.x[RC])
        items.append(self.theta[0])
        return np.concatenate(items)

# ---- notebook cell 79 ----
INCLUSIVE_THETA = True
if INCLUSIVE_THETA:
    th_exc = lambda th, n: th[1:n]
    x_exc = lambda x, n: x
else:
    th_exc = lambda th, n: th
    x_exc = lambda x, n: x[1:n]

class ALD_Reactor_Model:
    def __init__(self,
                 T=200+273, L=45*1e-2, R=2.5*1e-2,
                 S=45*1e-2*2*np.pi*2.5*1e-2, V=None,
                 p_torr=1.0, flow_sccm=300, M0=28.0,
                 reactant_data={'TMA': {'M': 72.09, 'b_film': 2},
                                'H2O':{'M': 18.02, 'b_film': 3}},
                 z_max=10*45e-2, n_z=None, tau_end=0.2, tau_n=None,
                 inlet=None, outlet=None,
                 s0_func=lambda b: adsorption_area(b, rho=3990.0, gpc=106e-12, M=101.96e-3)):
        #self.ids = ids
        self.reactor = Reactor_1D()
        self.reactor.set_reactor_parameters(T=T, L=L, R=R, V=V)
        self.reactor.set_surface_parameters(S)
        self.reactor.set_carrier_parameters(p=torr_to_pa(p_torr), flow_sccm=flow_sccm,
                                            M0=M0 * 1e-3 / N_A)   # R2: g/mol -> kg per molecule

        self.Ds = []
        self.s0s = []
        self.vths = []
        self.x_rhs = []
        self.th_rhs = []

        for RC in reactant_data:
            r_data = reactant_data[RC]
            M = r_data['M'] * 1e-3 / N_A   # R2: g/mol -> kg per molecule
            vth = particle_velocity(M, T)
            self.reactor.set_reactant_parameters(RC, vth, M, s0=s0_func(r_data['b_film']))
            self.s0s.append(s0_func(r_data['b_film']))
            self.vths.append(vth)
            self.x_rhs.append(self.reactor.x_rhs[RC])
            self.th_rhs.append(self.reactor.th_rhs[RC])
            self.Ds.append(self.reactor.D[RC])

        self.x_rhs = np.array(self.x_rhs)[:, None]
        self.th_rhs = np.array(self.th_rhs)[:, None]
        self.Ds = np.array(self.Ds)[:, None]
        self.s0s = np.array(self.s0s)[:, None]
        self.vths = np.array(self.vths)[:, None]

        #Get reactor profiles
        # Spatial profile xi is normalized by L, but remember to multiply by L when displaying.
        # Cases where dz is used are scaled by L to account for us not using the 'normalized' coefficients
        self.setup = ReactorSetupProfile()
        self.setup.construct_space_profile(z_max, u_D = np.max(self.reactor.u/self.Ds), n_z=n_z, min_z=0)
        self.setup.construct_time_profile(tau_end=tau_end, D=np.max(self.Ds), dz=None, n_out=tau_n)

        #Make the profiles
        for RC in reactant_data:
            self.setup.initialize_x(RC, n=None, x=None, initial_x=0.0)
        self.setup.initialize_theta(0, n=None, theta=None, initial_theta=0.0)

        if inlet is None:
            self.inlet = lambda t: np.array([1.0, 0.0]).T
        else:
            self.inlet = inlet

        if outlet is None:
            self.outlet = lambda t: np.array([0.0, 0.0]).T
        else:
            self.outlet = outlet

        self.reset_internal_state()

    def reset_internal_state(self):
        self.y0 = self.setup.flat_input_array()
        self.old_inlet = np.zeros((2, 1), dtype='float')
        self.old_t = 0.0

    def run_model(self, outlet_type="dirichlet", epsilon=1.0,
                  rtol=1e-4, atol=1e-7, method="BDF",
                  betas = [0.001, 0.001],
                  perturbation = lambda x: x, t_offset=0, t_r = 0.22,
                  return_profile=False,   # C9: True also returns the whole time history (t, x, theta)
                  wall_reservoir=None):   # C11: {'k_ads': [a_TMA, a_H2O], 'k_des': [d_TMA, d_H2O]} [1/s]; reversible wall uptake (physisorption)
    # unknowns: x_1..x_{n-1} (interior), theta_0..theta_n

        n = len(self.setup.z)
        d = self.setup.dz # * self.reactor.L
        nx = n - 1

        co_adv = -self.reactor.u / (2.0 * d)
        co_lap = self.Ds / (d ** 2)

        tau_end = self.setup.tau[-1]
        # C11: optional linear wall reservoir s (gas-equivalent Pa) per reactant: ds/dt = k_ads x - k_des s, dx/dt -= same
        use_res = wall_reservoir is not None
        if use_res:
            k_ads = np.asarray(wall_reservoir['k_ads'], float)[:, None]; k_des = np.asarray(wall_reservoir['k_des'], float)[:, None]
            base = len(self.y0) if len(self.y0) == 2*nx + n + (1 if INCLUSIVE_THETA else -1) else None
            s0_res = getattr(self, 's_res', np.zeros(2*nx))
            y_start = np.concatenate((self.y0[:2*nx + n + (1 if INCLUSIVE_THETA else -1)], s0_res))
        else:
            y_start = self.y0
        n_core = 2*nx + n + (1 if INCLUSIVE_THETA else -1)
        inlet = self.inlet
        outlet= self.outlet

        def rhs(t, y):
            xi_x1 = y[:nx]
            xi_x2 = y[nx:2*nx]
            th = y[2*nx:n_core]   # C11: reservoir states (if any) follow theta

            x1_full = np.empty(n + 1)
            x1_full[1:n] = xi_x1
            x2_full = np.empty(n + 1)
            x2_full[1:n] = xi_x2

            x_full = np.stack((x1_full, x2_full))


            I0, O0 = inlet(t+t_offset), outlet(t+t_offset)

            for i in range(len(x_full)):
                OI = self.old_inlet[i]
                if I0[i] is None:
                    x_full[i, 0] = OI * np.exp(-np.abs(dt/t_r)) #+ dt*0.5 * (co_lap[i] * 2 * (x_full[i, 1] - OI))
                else:
                    #x_full[i, 0] = I0[i]-(dt/0.1)*(I0[i] - OI)
                    x_full[i, 0] = I0[i] #inlet(t+t_offset)

                x_full[i, n] = x_full[i, n - 1] if outlet_type == "noflux" else O0[i]
            x_full = perturbation(x_full)
            co_diff = -np.stack((self.x_rhs[0] * betas[0] * (1-th_exc(th,n)),
                              self.x_rhs[1] * betas[1] * (th_exc(th,n))))


            lap = co_lap * (x_full[:, :-2] - 2.0 * x_full[:, 1:-1] + x_full[:, 2:])
            adv = co_adv * (x_full[:, 2:] - x_full[:, :-2])
            diff = co_diff * x_full[:, 1:n]

            dx = (lap + adv + diff)/epsilon
            if use_res:   # C11
                sres = y[n_core:].reshape(2, nx); exch = k_ads * x_full[:, 1:n] - k_des * sres
                dx = dx - exch/epsilon

            dth = self.th_rhs[0] * betas[0] * (1-th) * x_exc(x_full[0], n) - \
                  self.th_rhs[1] * betas[1] * (th) * x_exc(x_full[1], n)

            res = np.concatenate((dx.ravel(), dth) + ((exch.ravel(),) if use_res else ()))   # C11

            self.old_inlet = x_full[:, 0]

            return res #np.concatenate((dx.ravel(), dth))

        dn_th = 1 if INCLUSIVE_THETA else -1
        boo_th = 1 if INCLUSIVE_THETA else 0
        jac_len = 2*nx + n + dn_th + (2*nx if use_res else 0)   # C11
        jac = lil_matrix((jac_len, jac_len), dtype=int)
        r = np.arange(nx)

        for c in range(2):
            jac[c*nx + r, c*nx + r] = 1
            jac[c*nx + r[:-1], c*nx + r[:-1] + 1] = 1
            jac[c*nx + r[1:], c*nx + r[1:] - 1] = 1

            jac[c*nx + r, 2*nx + boo_th + r] = 1              # x_i  <- theta_i
            jac[2*nx + boo_th + r, c*nx + r] = 1              # theta_i <- x_i
            if outlet_type == "noflux":
                jac[2*nx + n - 1 + dn_th, c*nx + nx - 1] = 1

        rt = np.arange(n + dn_th)
        jac[2*nx + rt, 2*nx + rt] = 1
        if use_res:   # C11: x_i <-> s_i at the same node
            for c in range(2):
                jac[n_core + c*nx + r, n_core + c*nx + r] = 1; jac[n_core + c*nx + r, c*nx + r] = 1; jac[c*nx + r, n_core + c*nx + r] = 1

        t_eval = self.setup.tau

        sol = solve_ivp(rhs, (0.0, tau_end), y_start, method=method, t_eval=t_eval,
                        jac_sparsity=jac.tocsr(), rtol=rtol, atol=atol)

        if not sol.success:
            raise RuntimeError("integration failed: %s" % sol.message)

        #self.y0 = sol.y[:, -1]
        x = np.empty((sol.t.size, 2, n + 1))
        x[:, :, 0] = [inlet(t+t_offset) for t in sol.t]
        x[:, 0, 1:n] = sol.y[:nx].T
        x[:, 1, 1:n] = sol.y[nx:2*nx].T
        theta = sol.y[2*nx:n_core].T
        if use_res: self.s_res = sol.y[n_core:, -1].copy()   # C11

        if (np.sum(x[-1, 0, 1:n])/(n-2) < 0.01) and (x[-1, 0, 1:n].max() < 0.01):
            x[-1, 0, 1:n] = 0.0
        if (np.sum(x[-1, 1, 1:n])/(n-2) < 0.2) and (x[-1, 1, 1:n].max() < 0.2):
            x[-1, 1, 1:n] = 0.0
        if (np.sum(theta[-1])/(theta.shape[1]) < 0.01) and (theta[-1].min() < 0.01):
            theta[-1, :] = 0.0

        x[:, :, n] = x[:, :, n - 1] if outlet == "noflux" else [outlet(t+t_offset) for t in sol.t]
        x[x < 0] = 0

        self.y0 = np.concatenate((x[-1, :, 1:n].ravel(), theta[-1].ravel()))



        #np.clip(sol.y[2*nx:].T, 0.0, 1.0), causes instability
        #return ReactorProfile(self.setup.xi*self.reactor.L, sol.t, x, theta)
        if return_profile:   # C9
            return x[-1], theta[-1], (sol.t + t_offset, x, theta)
        return x[-1], theta[-1]


# ---- notebook cell 82 ----
class FlatModel(nn.Module):
    def __init__(self, s0, vth, dt, xpos, logbetas=[np.log(0.001), np.log(0.001)], initial_theta=0, device="cpu", T=373.0):
        super().__init__()
        self.xpos = xpos #torch.tensor(xpos, device=device)
        self.device = device
        self.log_beta = nn.Parameter(torch.tensor(np.array(logbetas)))
        #self.log_beta = logbetas
        self.coeff = torch.tensor((1/4) * s0 * vth * dt / (R * T), device=device)   # F1: p [Pa] -> mol/m3
        #(1/4) * s0 * vth * dt #torch.tensor((1/4) * s0 * vth * dt, device=device)
        self.initial_theta = torch.tensor(initial_theta, device=device)

    def get_betas(self):
        return np.exp(self.log_beta.detach().cpu().numpy())   # G2: detach the trainable parameter

    def next_theta_deriv(self, x, last_theta):
        dtheta = (1-last_theta)*self.coeff * x[0] * torch.exp(self.log_beta[0]) - \
                 last_theta * self.coeff[1] * x[1] * torch.exp(self.log_beta[1])
        return last_theta + dtheta

    def next_theta(self, x, last_theta):
        dtheta = (1-last_theta) * (1-torch.exp(-self.coeff[0] * x[0] * torch.exp(self.log_beta[0])))
        dtheta -= last_theta * (1-torch.exp(-self.coeff[1] * x[1] * torch.exp(self.log_beta[1])))
        return last_theta + dtheta

    def get_theta_step(self, x_full):
        x = np.mean(x_full[:, self.xpos], axis=-1)
        x = torch.tensor(x, device=self.device)
        #initial_theta = torch.tensor(theta, device=self.device)
        next_theta = self.next_theta(x, self.initial_theta)
        self.initial_theta = next_theta
        return next_theta.numpy(force=True).copy()#, p

    def eval_step(self, x_full, gpc=106e-12):
        if x_full.ndim != 2:
            print('concentration profile has nonstandard dimensions, may not work as expected')
        with torch.no_grad():
            last_theta = self.initial_theta.numpy(force=True).copy()
            result = self.get_theta_step(x_full).item()
            return result
            #theta_change = np.abs(result - last_theta)
            #return theta_change * gpc
            #return result.cpu().numpy()
            #return result[0].cpu().numpy(), result[1].cpu().numpy()

# ---- notebook cell 84 ----
class ChannelModel(nn.Module):
    def __init__(self, s0, vth, dt, xpos, W, H, T, L, carrier_pressure,
                 logbetas=[np.log(0.001), np.log(0.001)], device="cpu",
                 points = 50, reactants={'TMA': {'M': 72.09, 'd_r': 5.91e-10},
                                         'H2O':{'M': 18.02, 'd_r': 2.7e-10}},
                 carrier = {'M': 28.0, 'd_r': 3.64e-10}, n_sub=1, K=None):
        super().__init__()
        self.K = K   # C6: adsorption equilibrium constant of reactant 0 [1/Pa]; None = irreversible
        self.n_sub = n_sub   # C5: sub-steps per call of step()
        self.W0 = W
        self.W = W
        self.H0 = H
        self.H = H
        self.xpos = xpos #torch.tensor(xpos, device=device)
        self.device = device
        self.log_beta = nn.Parameter(torch.tensor(np.array(logbetas)))
        #self.log_beta = logbetas
        self.dt = dt
        #self.coeff = torch.tensor((1/4) * s0 * vth * dt, device=device)
        #(1/4) * s0 * vth * dt #torch.tensor((1/4) * s0 * vth * dt, device=device)
        self.theta = self.initialize_profile(points, components=1) #torch.tensor(initial_theta, device=device)
        self.x = self.initialize_profile(points, components=2) #torch.tensor(initial_x, device=device)
        self.L = L
        self.dz = self.L/points
        self.T = T
        self.carrier_pressure = carrier_pressure
        self.za_funcs = []
        self.vths = vth
        self.s0s = s0

        for i, RC in enumerate(reactants):
            RI = reactants[RC]
            #Note that we want to use the !Molar Mass!, not the normalized molecular weight
            #Since the expressions use the gas constant and I don't want to work out where a N_A needs to be added
            self.za_funcs.append(lambda pA, RI=RI: self.calc_za(pA, self.carrier_pressure,   # C1: bind RI now
                                                         RI['M'], carrier['M'],
                                                         RI['d_r'], carrier['d_r']))

            #Function uses molecular & boltzmann
            #self.vths.append(particle_velocity(reactants[RC]['M']/N_A, T))

    def initialize_profile(self, points, components):
        return torch.zeros((components, points), device=self.device)

    def get_betas(self):
        return np.exp(self.log_beta.detach().cpu().numpy())   # G2: detach the trainable parameter
    # -------------------------
    # Physics helpers
    # -------------------------
    def hydro_diameter(self):
        return 2 / (1/self.H + 1/self.W)

    def calc_za(self, pA, pB, MA, MB, da, db):
        MA, MB = MA * 1e-3, MB * 1e-3   # C2: g/mol -> kg/mol (R in J/mol/K)
        term1 = (np.pi/4 * (da+db)**2 * \
                 np.sqrt(8*R*self.T/np.pi * (1/MA + 1/MB)) * pB)

        term2 = (np.pi * da**2 *
                 np.sqrt(16*R*self.T/(torch.pi*MA)) * pA)

        return (term1 + term2) / (R*self.T) * N_A   # C2: mol/s -> collisions/s (Ylilammi Eq. 1)

    def calc_Deff(self, va, za):
        #self.gas_velocity()
        #va = self.gas_velocity() #torch.sqrt(8*self.R*self.T/(torch.pi*self.MA))
        Da = 3*torch.pi/16 * va**2 / za

        h = self.hydro_diameter()
        #Dkn = h * torch.sqrt(8*self.R*self.T/(9*torch.pi*self.MA))
        Dkn = h * va / 3

        return 1 / (1/Da + 1/Dkn)

    def _implicit_diffusion(self, x_int, x_left, Deff, dt, k_wall=None):
        # C5: backward Euler for dx/dt = Deff d2x/dz2 on the interior nodes;
        #     x[0] = inlet value (Dirichlet), x[-1] = x[-2] (closed end, as in Larry's boundary rows)
        m = x_int.shape[0]; r = float(Deff) * dt / self.dz**2
        if not torch.is_grad_enabled():   # C10: same tridiagonal system, banded solve (O(m)) when no gradient is needed
            main = np.full(m, 1 + 2*r); main[-1] = 1 + r
            if k_wall is not None: main = main + (k_wall * dt).detach().cpu().numpy()
            ab = np.zeros((3, m)); ab[0, 1:] = -r; ab[1] = main; ab[2, :-1] = -r
            b = x_int.detach().cpu().numpy().astype(float).copy(); b[0] += r * float(x_left)
            return torch.from_numpy(solve_banded((1, 1), ab, b)).to(x_int.dtype)
        A = (torch.diag(torch.full((m,), 1 + 2*r, dtype=x_int.dtype))
             - r*torch.diag(torch.ones(m-1, dtype=x_int.dtype), 1) - r*torch.diag(torch.ones(m-1, dtype=x_int.dtype), -1))
        A[-1, -1] = 1 + r
        if k_wall is not None:   # C5b: wall loss in the same implicit solve
            A = A + torch.diag((k_wall * dt).to(x_int.dtype))
        b = x_int.clone(); b[0] = b[0] + r * x_left
        return torch.linalg.solve(A, b)

    def step(self, x0):
        # C5: pressure and coverage solved separately in each sub-step (the decoupling Larry proposed):
        #     wall loss exact over dt, diffusion implicit (stable for any dt), coverage exact over dt.
        h = self.hydro_diameter()
        n_sub = getattr(self, 'n_sub', 1); dt = self.dt / n_sub
        for _ in range(n_sub):
            for i in range(2):
                za = self.za_funcs[i](x0[i])
                va = self.vths[i].item()
                Deff = self.calc_Deff(va, za)
                beta = torch.exp(self.log_beta[i])
                x_old = self.x[i, 1:-1].clone().to(torch.float64)
                th_old = self.theta[0, 1:-1].clone().to(torch.float64)
                ka = self.s0s[i].item() * va * beta / (4 * R * self.T)   # adsorption rate per Pa
                Pd = ka / self.K if (i == 0 and self.K is not None) else 0.0   # C6
                lam = 4/h * R * self.T / self.s0s[i].item()             # Pa per unit coverage (lam*ka = 4/h * v/4 * beta)
                def relax(th, p):   # coverage after dt at constant p (exact); C4: reactant 1 resets sites
                    k = ka * p
                    if i == 0:
                        th_eq = k / (k + Pd) if self.K is not None else 1.0   # C6
                        return th_eq - (th_eq - th) * torch.exp(-(k + Pd) * dt)
                    return th * torch.exp(-k * dt)
                # C6b predictor-corrector: coverage predicted with the old pressure; gas solved with the
                #      mid-step coverage (loss and desorption source); coverage corrected with the mid-step pressure
                th_mid = 0.5 * (th_old + relax(th_old, x_old))
                cover = (1 - th_mid) if i == 0 else th_mid
                src = lam * Pd * th_mid if (i == 0 and self.K is not None) else 0.0   # C6: desorbed molecules
                x_new = self._implicit_diffusion(x_old + dt * src, x0[i], Deff, dt, lam * ka * cover)   # C5b
                th_new = relax(th_old, 0.5 * (x_old + x_new))
                self.x[i, 1:-1] = x_new.to(self.x.dtype)
                self.x[i,0] = x0[i]
                self.x[i,-1] = self.x[i,-2]
                self.theta[0, 1:-1] = th_new.to(self.theta.dtype)
                self.theta[0,0] = self.theta[0,1]
                self.theta[0,-1] = self.theta[0,-2]

        return self.x, self.theta

    # -------------------------
    # Forward simulation
    # -------------------------
    def forward(self, x_full, steps, gpc):
        x0 = np.mean(x_full[:, self.xpos], axis=-1)
        x0 = torch.tensor(x0, device=self.device)

        theta_history = [self.theta.numpy(force=True).copy()]

        for _ in range(steps):
            x, theta = self.step(x0)
            theta = theta.numpy(force=True).copy()
            entry_theta_change = max(theta[0,0] - theta_history[-1][0,0], 0.0)   # G1: count the fill only
            # update geometry (still differentiable)
            self.H = np.clip(self.H - 2*entry_theta_change*gpc, min=1e-12)   # C7: two walls
            theta_history.append(theta)

        return np.stack(theta_history)

    def eval_step(self, x_full, gpc=106e-12, steps=1):
        if x_full.ndim != 2:
            print('concentration profile has nonstandard dimensions, may not work as expected')
        with torch.no_grad():
            result = self.forward(x_full, steps=steps, gpc=gpc)
            theta_change = np.clip(result[1:] - result[:-1], 0, None)   # G1: count the fill only
            return theta_change.sum(axis=1) * gpc
            #return result.cpu().numpy(
            #return result
            #return result[0].cpu().numpy(), result[1].cpu().numpy()

# ---- notebook cell 86 ----
tma_n0 = torr_to_pa(150e-3)
h2o_n0 = torr_to_pa(80e-3)

#print(tma_n0/(R*373),  h2o_n0/(R*373))

OFF_STATE = 0

class ModelCoupling:
    def __init__(self, model=None, t_step=0.005,
                 recipe = [{'t': 0.1, 'p': [tma_n0, OFF_STATE]},
                            {'t': 60, 'p': [OFF_STATE, OFF_STATE]},
                            {'t': 1.0, 'p': [OFF_STATE, h2o_n0]},
                            {'t': 60, 'p': [OFF_STATE, OFF_STATE]}],
                 sample_betas=None,   # P1: [beta_A, beta_B] for the sample models; None = class defaults
                 **kwargs):

        self.t_step = t_step
        self.sample_betas = sample_betas   # P1

        if model is None:
            self.model_init(t_step=t_step, **kwargs)
        else:
            self.model = model
        self.coupling_init()

        #self.sample_model_init()
        self.set_recipe(recipe)

    def set_recipe(self, recipe, t_r=0.02):
        #recipe.t/2 > t_r > t_step
        #Assumes the padding offstate pressure is also the case for the last state pressure
        self.recipe = recipe
        self.cycle_time = np.sum([stage['t'] for stage in recipe])

        conc = np.zeros((round((self.cycle_time) / self.t_step)+1, 2), dtype='float')
        cstate = np.array([0, 0])[...,None].T
        ct = 0 #pad
        edge_length = round(t_r/self.t_step)
        interp = np.linspace(0, 1, edge_length)[...,None]

        for stage in recipe:
            #conc.append(stage['p']*int(stage['t']//t_step+1))
            center_point = round(ct/self.t_step)
            stage_p = np.array(stage['p'])[...,None].T
            #print(cstate, stage_p)
            #conc[center_point-edge_length:center_point+edge_length+1, :] = interp*stage_p + (1-interp)*cstate
            conc[center_point:center_point+edge_length, :] = interp*stage_p + (1-interp)*cstate
            conc[center_point+edge_length:,:] = stage_p
            cstate = stage_p
            ct += stage['t']

        #Clamp off relevant conc section
        start_index = np.argmax(np.sum(conc != 0, axis=1)!=0)
        #print(start_index + round(self.cycle_time/self.t_step))
        conc = conc[start_index-1: start_index + round(self.cycle_time/self.t_step), :]
        conc = conc #/(R*self.model.reactor.T) #pressure to concentration conversion
        self.conc = conc

    def model_init(self, t_step, T=373,
                   z_max=64*1e-2, L = 64*1e-2,
                   R = 1.75*1e-2, S=64*1e-2*2*np.pi*R,
                   p_torr=1.0, flow_sccm=120, M0=28.0,
                   n_z = 501, tau_n = 2,
                   reactant_data = {'TMA': {'M': 72.09, 'b_film': 2},
                                    'H2O': {'M': 18.02, 'b_film': 3}}):

        self.model = ALD_Reactor_Model(T=T, L=L, R=R, S=S,
                                        p_torr=p_torr, flow_sccm=flow_sccm, M0=M0,
                                        reactant_data=reactant_data,
                                        z_max=z_max, n_z=n_z,
                                        tau_end=t_step, tau_n=tau_n,
                                        inlet=self.I_by_time, outlet=None)

    def coupling_init(self, position_range = (31*1e-2, 35*1e-2)):
        z = self.model.setup.z #* self.model.reactor.L
        zpos = np.where(np.logical_and(z>=position_range[0], z<=position_range[1]))[0]
        sb = getattr(self, 'sample_betas', None)   # P1
        beta_kw = {} if sb is None else {'logbetas': [float(np.log(b)) for b in sb]}
        self.flat_model = FlatModel(s0 = self.model.s0s,
                                    vth = self.model.vths,
                                    dt = self.t_step,
                                    xpos = zpos,
                                    T = self.model.reactor.T,   # F1
                                    **beta_kw)   # P1

        self.har_model = ChannelModel(s0 = self.model.s0s,
                                      vth = self.model.vths,
                                      dt = self.t_step, #If smaller than t_step, must increase number of steps used in the running stage
                                      xpos = zpos,
                                      W=0.1e-3, H=0.2e-6, T=self.model.reactor.T,
                                      L = 200e-6,
                                      carrier_pressure=self.model.reactor.p,
                                      points=100,
                                      **beta_kw)   # P1


    def I_by_time(self, t):
        t_ = t % self.cycle_time
        return self.conc[round(t_/self.t_step)]

    def run_model(self, time, log_freq=10, gpc=1):
        x_log = []
        theta_log = []
        betatheta_log = []
        tau_log = []

        tau_end = self.t_step #self.model.setup.tau[-1]
        #perturbation = self.sample_model.get_perturbation if use_perturbation else lambda x: x
        perturbation = lambda x: x #Not currently in use
        thick_log = []

        delta_channel_log = []
        sample_theta_log = []
        delta_theta_sum = 0
        last_theta = 0

        for i in range(int(time//tau_end)+1):
            t = i * tau_end

            x, theta = self.model.run_model(betas = [0.000, 0.000],
                                            perturbation = perturbation,
                                            t_offset=t, outlet_type='noflux', #outlet_type='derichlet',
                                            method = 'RK45')


            #Change gpc to 1 to
            sample_theta = self.flat_model.eval_step(x, gpc=gpc)
            #delta_channel = self.har_model(x, gpc=106e-12, steps=1) #keep steps=1 if dt = t_steps
            delta_theta_sum += gpc*max(sample_theta-last_theta, 0.0)   # G1: count the fill only
            last_theta = sample_theta

            if i % log_freq == 0:
                #delta_channel_log.append(delta_channel)
                x_log.append(x)
                theta_log.append(theta)
                tau_log.append(t)
                sample_theta_log.append(sample_theta)
                thick_log.append(delta_theta_sum)

        #np.array(delta_channel_log),
        return np.array(x_log), np.array(theta_log), np.array(thick_log), np.array(sample_theta_log), np.array(tau_log)
