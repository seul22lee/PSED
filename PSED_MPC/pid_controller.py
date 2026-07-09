import numpy as np
import pandas as pd

# 노트북에 붙여 쓸 땐 아래 import 가 자동으로 건너뜁니다
# (channelModel, evaluate, cost_function, get_gpc 가 이미 정의돼 있으므로).
try:
    channelModel  # noqa: F821
except NameError:
    from deps import channelModel, evaluate, cost_function, get_gpc


# ============================================================
# A. 한 번만: 비용 최적 ratio 고르기
#    (dose = pA*tp 는 PID가 조절, ratio = pA/tp 는 여기서 고정)
# ============================================================
def pick_cost_optimal_ratio(model, x, l_0, pA_bounds, tp_bounds,
                            nR=120, bisect_iter=40):
    pA_min, pA_max = pA_bounds
    tp_min, tp_max = tp_bounds
    last_theta = np.zeros_like(x)

    r_min = pA_min / tp_max
    r_max = pA_max / tp_min
    r_grid = np.exp(np.linspace(np.log(r_min), np.log(r_max), nR))

    best = None
    for r in r_grid:
        D = _invert_dose(model, x, last_theta, l_0, r,
                         pA_bounds, tp_bounds, bisect_iter, saturate=False)
        if D is None:
            continue
        pA, tp = _dose_to_pa_tp(D, r)
        c = cost_function(pA, tp, pA, tp_max)
        if best is None or c < best[0]:
            best = (c, r)
    return best[1] if best is not None else np.sqrt(r_min * r_max)


# ============================================================
# B. dose <-> (pA, tp)  및  dose 역산 (feedforward)
# ============================================================
def _dose_to_pa_tp(D, r):
    return float(np.sqrt(D * r)), float(np.sqrt(D / r))


def _dose_bounds(r, pA_bounds, tp_bounds):
    pA_min, pA_max = pA_bounds
    tp_min, tp_max = tp_bounds
    D_low = max(pA_min**2 / r, tp_min**2 * r)
    D_high = min(pA_max**2 / r, tp_max**2 * r)
    return D_low, D_high


def _invert_dose(model, x, last_theta, target, r,
                 pA_bounds, tp_bounds, bisect_iter=40, saturate=True):
    """고정 ratio r 위에서 x_half(D) = target 을 만족하는 dose D 를 이분탐색.
       (x_half 는 dose 에 대해 단조증가 가정 — 기존 코드와 동일)
       saturate=True  : 최대 dose 로도 목표 미달이면 D_high 로 포화 (컨트롤러용)
       saturate=False : 도달 불가능하면 None (ratio 선택기용)"""
    D_low, D_high = _dose_bounds(r, pA_bounds, tp_bounds)
    if not (np.isfinite(D_low) and np.isfinite(D_high)) or D_low >= D_high:
        return None

    def xh(D):
        pA, tp = _dose_to_pa_tp(D, r)
        _, _, h = evaluate(pA, tp, model, x, last_theta)
        return h

    if xh(D_high) < target:          # 최대 dose 로도 목표 미달
        return D_high if saturate else None
    if xh(D_low) >= target:          # 최소 dose 로도 충족 -> 최소로
        return D_low

    lo, hi = D_low, D_high
    for _ in range(bisect_iter):
        mid = 0.5 * (lo + hi)
        if xh(mid) >= target:
            hi = mid
        else:
            lo = mid
    return hi


# ============================================================
# C. PID + feedforward 컨트롤러
# ============================================================
def run_pid(x, steps, l_0, T_fixed, pA_bounds, tp_bounds,
            Kp=0.6, Ki=0.25, Kd=0.0,
            margin=0.03,
            use_feedforward=True,
            r_star=None,
            warm=None):
    """warm : optional kb_bridge.warm_start(...) dict. If given, seeds r_star from
    its KB-grounded pA0/tp0 (skips the cost-optimal-ratio grid search) and the
    first-step GPC from its literature prior — a literature warm-start instead of a
    cold mid-range guess (Approach 5). Fully optional / non-breaking."""
    if warm:
        if r_star is None and warm.get("r_star"):
            r_star = warm["r_star"]
    """
    가정: gpc 는 '한 스텝 뒤'에 측정된다.
      -> 스텝 k 결정 시점엔 gpc_{k-1} 까지만 안다.
      -> gpc_k 는 persistence 로 예측 (g_hat = 마지막 측정값).
    구조 (2-DOF):
      feedforward : 예측 gpc 로 모델 역산해 목표 dose 계산
      feedback    : 한 스텝 늦은 x_half 오차에 PID (주로 적분) 보정
    margin : 노이즈 대비 안전 마진. 0 이면 경계에 앉아 ~절반 위반,
             0.03 이면 위반 0 (대신 cost 약간 증가).
    """
    model = channelModel()
    model.T = T_fixed
    model.pA = np.mean(pA_bounds)
    model.t_p = np.mean(tp_bounds)

    tp_max = tp_bounds[1]
    if r_star is None:
        r_star = pick_cost_optimal_ratio(model, x, l_0,
                                         pA_bounds, tp_bounds)

    target = l_0 * (1.0 + margin)        # 노이즈 대비 안전 마진
    last_theta = np.zeros_like(x)

    # PID 상태
    integ = 0.0
    e_prev = 0.0
    integ_clip = 0.5                     # anti-windup (정규화 오차 기준)

    g_meas = None                        # 마지막으로 '측정된' gpc (한 스텝 지연)
    e_norm = 0.0                         # 한 스텝 지연된 정규화 오차
    hist, total = [], 0.0

    for kk in range(steps):
        # --- 1. gpc 예측 (결정 시점엔 gpc_k 모름) ---
        if g_meas is None:
            # warm-start: first-step GPC from the KB literature prior (nm -> m to
            # match the model's SI scale), else nominal
            wg = (warm or {}).get("priors", {}).get("gpc_expected")
            g_hat = wg * 1e-9 if wg else get_gpc(0)
        else:
            g_hat = g_meas               # persistence: 마지막 측정값
        model.gpc = g_hat

        # --- 2. feedforward: 예측 gpc 로 목표 dose 역산 ---
        if use_feedforward:
            D_ff = _invert_dose(model, x, last_theta, target, r_star,
                                pA_bounds, tp_bounds)
            if D_ff is None:
                D_low, D_high = _dose_bounds(r_star, pA_bounds, tp_bounds)
                D_ff = D_high
        else:
            # 순수 PID 비교용: feedforward 없이 중앙값에서 시작
            D_low, D_high = _dose_bounds(r_star, pA_bounds, tp_bounds)
            D_ff = np.sqrt(D_low * D_high)

        # --- 3. feedback: 지연된 오차에 PID (곱셈 보정) ---
        deriv = e_norm - e_prev
        u = Kp * e_norm + Ki * integ + Kd * deriv
        D = D_ff * (1.0 + u)

        # dose -> (pA, tp), bounds 클램프
        pA, tp = _dose_to_pa_tp(max(D, 1e-12), r_star)
        pA = float(np.clip(pA, pA_bounds[0], pA_bounds[1]))
        tp = float(np.clip(tp, tp_bounds[0], tp_bounds[1]))

        # --- 4. 적용 & 실제 gpc 관측 (이게 다음 스텝 측정값) ---
        model.gpc = get_gpc(kk)          # 진짜 gpc_k
        _, last_theta, xh = evaluate(pA, tp, model, x, last_theta)
        g_meas = model.gpc               # 한 스텝 뒤 사용됨

        # --- 5. 오차 업데이트 (다음 스텝 feedback 입력) ---
        e_prev = e_norm
        e_norm = (target - xh) / l_0     # feedforward 와 같은 target 기준
        integ = float(np.clip(integ + e_norm, -integ_clip, integ_clip))

        cost = cost_function(pA, tp, pA, tp_max)
        total += cost
        hist.append({
            "step": kk, "pA": pA, "t_p": tp, "pA_tp": pA * tp,
            "gpc": model.gpc, "gpc_hat": g_hat,
            "x_half": xh, "ok": xh >= l_0,
            "e": l_0 - xh, "cost": cost, "total": total,
        })

    return pd.DataFrame(hist)


# ============================================================
# 자체 테스트
# ============================================================
if __name__ == "__main__":
    steps = 200
    x = np.linspace(0, 1e-3, 200)
    l_0 = 0.2e-3
    T_fixed = 673
    pA_bounds = (1, 200)
    tp_bounds = (0.01, 5)

    df = run_pid(x, steps, l_0, T_fixed, pA_bounds, tp_bounds)
    print("ratio* used (approx):", df["pA"].iloc[10] / df["t_p"].iloc[10])
    print("PID violations:", (~df["ok"]).sum())
    print("PID total cost :", df["total"].iloc[-1])
    print(df[["step", "gpc", "gpc_hat", "pA", "t_p",
              "x_half", "ok", "cost"]].head(8).to_string(index=False))
