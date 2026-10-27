"""Roofline ceiling on serving throughput, from GPU spec sheets and model configs.

For a workload of `conc` concurrent requests, each with `isl` input and `osl`
output tokens, on `n_gpu` GPUs (tensor parallel), the fastest possible cycle is:

  prefill:  every request's prompt, compute-bound at dense peak FLOPS
  decode:   osl steps; each step is bound by the slower of
            - memory: weights touched + KV cache read, at HBM bandwidth
            - compute: 2 x active params + attention FLOPs per token, at peak

  output tokens/s/GPU <= conc * osl / (T_prefill + osl * T_step) / n_gpu

Nothing real reaches this: kernels don't hit peak bandwidth or FLOPS, and
scheduling, communication and sampling all add time. Results above it mean an
error in the measurement or in this model.

MoE routing sets how many experts a decode step must read. Two cases:
  "min"      every token in the batch picks the same k experts (hard ceiling)
  "uniform"  tokens route independently and uniformly (typical estimate)
A measurement between the two is plausible (skewed routing); one above "min"
is not.

Parameter counts are derived from config.json and checked against the
published totals in tests.
"""

import json
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIGS = ROOT / "data" / "roofline" / "configs"

MXFP4_BYTES = 4.25 / 8  # 4-bit values plus one 8-bit scale per 32
DTYPE_BYTES = {"bf16": 2.0, "fp8": 1.0, "mxfp4": MXFP4_BYTES}


@dataclass
class Model:
    name: str
    layers: int
    experts: int            # routed experts per MoE layer (0 = dense)
    top_k: int
    moe_layers: int
    expert_params: float    # per routed expert
    always_params: float    # params read every step: attention, dense FFN, shared experts, router, lm_head
    active_params: float    # params used per token (for FLOPs)
    expert_dtype: str
    other_dtype: str
    kv_bytes_per_token_full: float  # per token, summed over full-attention layers
    kv_sliding_layers_bytes: float  # per token, summed over sliding-window layers
    sliding_window: int
    attn_flops_per_ctx_token: float  # decode attention FLOPs per (token, context token)
    kv_replicated_under_tp: bool     # MLA latent KV is not split across TP ranks


def gpt_oss(cfg, kv_dtype="bf16"):
    h, L = cfg["hidden_size"], cfg["num_hidden_layers"]
    heads, kvh, hd = cfg["num_attention_heads"], cfg["num_key_value_heads"], cfg["head_dim"]
    E, k, inter = cfg["num_local_experts"], cfg["num_experts_per_tok"], cfg["intermediate_size"]
    attn = h * heads * hd * 2 + h * kvh * hd * 2          # q, o + k, v
    expert = 3 * h * inter                                # gate, up, down
    router = h * E
    lm_head = cfg["vocab_size"] * h
    types = cfg["layer_types"]
    full, sliding = types.count("full_attention"), types.count("sliding_attention")
    kv_layer = 2 * kvh * hd * DTYPE_BYTES[kv_dtype]
    return Model(
        name="gpt-oss-120b", layers=L, experts=E, top_k=k, moe_layers=L,
        expert_params=expert, always_params=L * (attn + router) + lm_head,
        active_params=L * (attn + router + k * expert) + lm_head,
        expert_dtype="mxfp4", other_dtype="bf16",
        kv_bytes_per_token_full=full * kv_layer, kv_sliding_layers_bytes=sliding * kv_layer,
        sliding_window=cfg["sliding_window"],
        attn_flops_per_ctx_token=4 * heads * hd,  # QK and AV, 2 FLOPs each, per layer
        kv_replicated_under_tp=False,
    )


def deepseek_v3(cfg, kv_dtype="bf16"):
    h, L = cfg["hidden_size"], cfg["num_hidden_layers"]
    heads = cfg["num_attention_heads"]
    qr, kvr = cfg["q_lora_rank"], cfg["kv_lora_rank"]
    nope, rope, vh = cfg["qk_nope_head_dim"], cfg["qk_rope_head_dim"], cfg["v_head_dim"]
    attn = (h * qr + qr * heads * (nope + rope)               # q down/up
            + h * (kvr + rope) + kvr * heads * (nope + vh)    # kv down/up
            + heads * vh * h)                                 # o
    dense_layers = cfg["first_k_dense_replace"]
    moe_layers = L - dense_layers
    dense_ffn = 3 * h * cfg["intermediate_size"]
    expert = 3 * h * cfg["moe_intermediate_size"]
    shared = cfg["n_shared_experts"] * expert
    E, k = cfg["n_routed_experts"], cfg["num_experts_per_tok"]
    router = h * E
    lm_head = cfg["vocab_size"] * h
    always = L * attn + dense_layers * dense_ffn + moe_layers * (shared + router) + lm_head
    return Model(
        name="DeepSeek-R1-0528", layers=L, experts=E, top_k=k, moe_layers=moe_layers,
        expert_params=expert, always_params=always,
        active_params=always + moe_layers * k * expert,
        expert_dtype="fp8", other_dtype="fp8",
        kv_bytes_per_token_full=L * (kvr + rope) * DTYPE_BYTES[kv_dtype],
        kv_sliding_layers_bytes=0.0, sliding_window=0,
        # Absorbed MLA decode: scores over (kv_lora + rope), values over kv_lora
        attn_flops_per_ctx_token=2 * heads * ((kvr + rope) + kvr),
        kv_replicated_under_tp=True,
    )


ARCHS = {"GptOssForCausalLM": gpt_oss, "DeepseekV3ForCausalLM": deepseek_v3}


def load_model(config_file, kv_dtype="bf16"):
    cfg = json.loads(Path(config_file).read_text(encoding="utf-8"))
    return ARCHS[cfg["architectures"][0]](cfg, kv_dtype)


def total_params(m):
    return m.always_params + m.moe_layers * m.experts * m.expert_params


def experts_touched(m, batch, routing):
    if m.experts == 0:
        return 0.0
    if routing == "min":
        return float(m.top_k)
    return m.experts * (1 - (1 - m.top_k / m.experts) ** batch)


def kv_read_bytes(m, ctx):
    """KV bytes read to decode one token at context length ctx."""
    return m.kv_bytes_per_token_full * ctx + m.kv_sliding_layers_bytes * min(ctx, m.sliding_window)


def attn_flops(m, ctx):
    full_frac = m.kv_bytes_per_token_full / (m.kv_bytes_per_token_full + m.kv_sliding_layers_bytes)
    eff_ctx = full_frac * ctx + (1 - full_frac) * min(ctx, m.sliding_window or ctx)
    return m.layers * m.attn_flops_per_ctx_token * eff_ctx


def ceiling(m, gpu, n_gpu, isl, osl, conc, compute_dtype, routing="min"):
    """Upper bound on output tokens/s per GPU, and per-user decode tokens/s."""
    bw = gpu["hbm_tb_s"] * 1e12
    peak = gpu[f"{compute_dtype}_dense_tflops"] * 1e12
    # Prefill: dense compute; causal attention averages isl/2 context per token
    prefill_flops = isl * (2 * m.active_params + attn_flops(m, isl / 2))
    t_prefill = conc * prefill_flops / (n_gpu * peak)
    # Decode: KV and attention are linear in context, so the mean context is exact
    ctx = isl + (osl + 1) / 2
    weight_bytes = (m.always_params * DTYPE_BYTES[m.other_dtype]
                    + m.moe_layers * experts_touched(m, conc, routing) * m.expert_params
                    * DTYPE_BYTES[m.expert_dtype])
    kv_bytes = conc * kv_read_bytes(m, ctx)
    per_gpu_bytes = weight_bytes / n_gpu + (kv_bytes if m.kv_replicated_under_tp else kv_bytes / n_gpu)
    t_mem = per_gpu_bytes / bw
    t_cmp = conc * (2 * m.active_params + attn_flops(m, ctx)) / (n_gpu * peak)
    t_step = max(t_mem, t_cmp)
    cycle = t_prefill + osl * t_step
    return {
        "output_tput_per_gpu": conc * osl / cycle / n_gpu,
        "interactivity_tok_s_user": 1 / t_step,
        "decode_bound": "memory" if t_mem >= t_cmp else "compute",
        "prefill_share": t_prefill / cycle,
    }
