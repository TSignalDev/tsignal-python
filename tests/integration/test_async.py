import pytest
import asyncio
import logging

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
async def test_multiple_async_slots(sender, receiver):
    """Test multiple async slots receiving signals"""
    logger.info(f"Test starting with receiver[{receiver.id}]")
    receiver2 = receiver.__class__()
    logger.info(f"Created receiver2[{receiver2.id}]")

    logger.info(f"Connecting receiver[{receiver.id}] to signal")
    sender.value_changed.connect(receiver, receiver.on_value_changed)
    logger.info(f"Connecting receiver2[{receiver2.id}] to signal")
    sender.value_changed.connect(receiver2, receiver2.on_value_changed)

    logger.info("Emitting value 42")
    sender.emit_value(42)

    for i in range(5):
        logger.info(f"Wait iteration {i+1}")
        if receiver.received_value is not None and receiver2.received_value is not None:
            logger.info("Both receivers have received values")
            break
        await asyncio.sleep(0.1)

    logger.info(
        f"Final state - receiver1[{receiver.id}]: value={receiver.received_value}"
    )
    logger.info(
        f"Final state - receiver2[{receiver2.id}]: value={receiver2.received_value}"
    )

    assert receiver.received_value == 42
    assert receiver2.received_value == 42


@pytest.mark.asyncio
async def test_async_slot_execution(sender, receiver):
    """Test async slot execution with event loop"""
    logger.info("Starting test_async_slot_execution")
    sender.value_changed.connect(receiver, receiver.on_value_changed)

    logger.info("Emitting value")
    sender.emit_value(42)

    for _ in range(5):
        if receiver.received_value is not None:
            break
        await asyncio.sleep(0.1)

    logger.info(f"Receiver value: {receiver.received_value}")
    assert receiver.received_value == 42
