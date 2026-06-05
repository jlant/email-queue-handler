import pytest

from python_service_template.service import Service
from python_service_template.settings import Settings


def test_service_start_run_stop() -> None:
    settings = Settings(run_seconds=0)
    service = Service(settings)

    assert service.started is False

    service.start()
    assert service.started is True

    service.run()

    service.stop()
    assert service.started is False


def test_service_run_raises_if_not_started() -> None:
    """Service.run() should raise RuntimeError if start() was never called."""
    settings = Settings(run_seconds=0)
    service = Service(settings)
    with pytest.raises(RuntimeError, match="must be started"):
        service.run()
