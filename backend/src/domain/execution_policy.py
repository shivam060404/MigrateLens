"""Product execution eligibility. Host execution must never be enabled for customers."""


class ExecutionDenied(ValueError):
    """A request is outside the only currently implemented execution scope."""


def authorize_repository(repository: str) -> None:
    if repository != "bundled:northstar-consumer":
        raise ExecutionDenied(
            "Customer and external repository access is disabled pending isolation review"
        )
