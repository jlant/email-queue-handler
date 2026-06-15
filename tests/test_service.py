import pytest

from email_queue_handler.service import Service
from email_queue_handler.settings import Settings


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
