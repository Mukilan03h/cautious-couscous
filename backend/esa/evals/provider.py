from esa.evals.models import EvalProvider
from esa.evals.providers.braintrust import BraintrustEvalProvider


def get_default_provider() -> EvalProvider:
    return BraintrustEvalProvider()
