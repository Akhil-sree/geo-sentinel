"""Temporal risk model — Mamba / selective state-space.

Interface (TemporalRiskModel) allows MambaTemporalModel (PyTorch) and
MockTemporalModel (dev fallback). Torch is NOT silently replaced: the
fallback is explicit via model_backend() and surfaced in /model/status.

Mamba reference: Gu & Dao (2023). Use here: regional, sensor-free,
zone-level early-warning CLASSIFICATION over environmental sequences —
not displacement forecasting of instrumented slopes.
"""
import os, json, math

try:
    import torch
    import torch.nn as nn
    TORCH = True
except ImportError:
    TORCH = False

SEQ_LEN = 48
D_IN, D_STATE = 7, 8
VERSION = "mamba_2026_01"

class TemporalRiskModel:
    def predict(self, sequence): raise NotImplementedError
    def backend(self): raise NotImplementedError

if TORCH:
    class SelectiveSSMCell(nn.Module):
        """Selective SSM recurrence: input-dependent gate Δ (the Mamba
        property — parameters are functions of the input, unlike LTI S4)."""
        def __init__(self, d_in=D_IN, d_state=D_STATE):
            super().__init__()
            self.delta_proj = nn.Linear(d_in, d_state)
            self.b_proj = nn.Linear(d_in, d_state)
            self.c_proj = nn.Linear(d_state, d_state)
            self.a_log = nn.Parameter(torch.linspace(math.log(0.85), math.log(0.65), d_state))
            self.out = nn.Linear(d_state, 1)

        def forward(self, x):
            B, T, _ = x.shape
            h = torch.zeros(B, self.a_log.shape[0], device=x.device)
            A = -torch.exp(self.a_log)
            for t in range(T):
                xt = x[:, t, :]
                delta = torch.sigmoid(self.delta_proj(xt))       # selective gate
                b = self.b_proj(xt)
                h = h * torch.exp(A * delta) + delta * b         # state update
            return torch.sigmoid(self.out(h * self.c_proj.weight @ torch.eye(h.shape[-1]))).squeeze(-1) \
                if False else torch.sigmoid(self.out(h)).squeeze(-1)  # (B,)

    class MambaTemporalModel(TemporalRiskModel):
        def __init__(self, weights_path=None):
            self.cell = SelectiveSSMCell()
            self.version = VERSION
            if weights_path:
                self.cell.load_state_dict(torch.load(weights_path, map_location="cpu"))

        def predict(self, sequence):
            x = torch.tensor([sequence], dtype=torch.float32)     # (1, T, D)
            with torch.no_grad():
                s = float(self.cell(x)[0])
            return {"dynamic_score": min(1.0, max(0.0, s)), "version": self.version,
                    "backend": "pytorch_selective_ssm"}

        def backend(self): return "pytorch_selective_ssm"


class MockTemporalModel(TemporalRiskModel):
    """Explicit fallback — an interpretable saturation heuristic. Flagged in
    /model/status so it is never mistaken for trained Mamba inference."""
    def __init__(self): self.version = VERSION + "_mock"

    def predict(self, sequence):
        if not sequence: return {"dynamic_score": 0.1, "version": self.version, "backend": "mock"}
        r72 = sequence[-1][2]; soil = sequence[-1][4]; schange = sequence[-1][5]
        base = 0.10 + 1.6 * r72 + 1.2 * max(0.0, schange)
        score = 1 / (1 + math.exp(-(base - 1.05) * 4))
        return {"dynamic_score": round(score, 4), "version": self.version,
                "backend": "mock_heuristic_fallback"}

    def backend(self): return "mock_heuristic"


def get_temporal_model():
    if TORCH:
        return MambaTemporalModel()
    return MockTemporalModel()
