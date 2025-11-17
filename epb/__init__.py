"""
Epistemic Pathology Benchmark (EPB)
The MLPerf of AI Truth Systems

EPB is a comprehensive benchmark for evaluating epistemic integrity in AI systems,
focusing on four key pathologies:
- Mirror Loop: Collapse in recursive refinement
- Confabulation: Fabrication and persistence of false information
- Violation State: Refusal contamination of benign prompts
- Echo Chamber: Synthetic drift and self-reinforcement

Version: 1.0.0 (epb_v1)
"""

__version__ = "1.0.0"
__epb_version__ = "epb_v1"

from epb.adapters.base import ModelClient, ModelConfig
from epb.runner.run_benchmark import run_benchmark
from epb.scoring.aggregate import compute_epb_truth

__all__ = [
    "__version__",
    "__epb_version__",
    "ModelClient",
    "ModelConfig",
    "run_benchmark",
    "compute_epb_truth",
]
