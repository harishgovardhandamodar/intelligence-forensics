"""Insider-recon framework (modular P14 build).

Models a malicious insider at an LLM provider that keeps residual data
despite advertising "stateless inference", and quantifies reconstruction of
synthetic sensitive values per surface, cumulatively, and via amplification.

Single-source-of-truth rule: retention logic, generators, and scoring live
in `iforensics/sim/{reconstruction,sensitive,harvest}.py`. Everything here
is an adapter, policy card, staged module, mitigation, doc, or test over
that engine — never a second copy of it.
"""
__version__ = "1.0.0"
__all__ = ["__version__"]
