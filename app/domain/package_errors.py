"""Expected errors cross boundaries without SDK, SQL or interface dependencies."""


class StudioError(ValueError):
    pass


class ContractError(StudioError):
    def __init__(self, file: str, field: str, problem: str):
        self.file, self.field, self.problem = file, field, problem
        super().__init__(f'{file} · {field}: {problem}')


class NeedsReview(StudioError):
    pass


class StorageError(StudioError):
    pass


class Canceled(StudioError):
    pass


class LeaseLost(StudioError):
    pass


class Paused(StudioError):
    """Pausa cooperativa solicitada en un checkpoint durable."""
