"""WebSocket endpoint for real-time channel communication.

Provides a WebSocket connection at /ws/channels/{channel_id} that lets users
send and receive messages in real-time.  Each incoming message is persisted via
CommunicationService (which handles DB write + Redis pub/sub broadcast) and the
sender's read cursor is advanced.

Session management: WebSocket connections are long-lived so we create a fresh
database session for each operation (channel validation, message send, read
cursor update) to avoid holding transactions open.  The session factory is
stored on ``app.state.session_factory`` by the application lifespan.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from botcrew.schemas.message import WebSocketSendPayload
from botcrew.services.channel_service import ChannelService
from botcrew.services.communication import CommunicationService, NativeTransport
from botcrew.services.message_service import MessageService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/channels/{channel_id}")
async def channel_websocket(
    websocket: WebSocket,
    channel_id: str,
    client_id: str = Query(...),
) -> None:
    """WebSocket endpoint for real-time channel messaging.

    Flow:
    1. Validate channel exists (close 4004 if not)
    2. Accept connection and register in ConnectionManager
    3. Send join notification as system message
    4. Enter receive loop: validate payload, persist via CommunicationService,
       update read cursor for sender
    5. On disconnect: unregister and send leave notification
    """
    connection_manager = websocket.app.state.connection_manager
    session_factory = websocket.app.state.session_factory

    # 1. Validate channel exists before accepting the connection
    async with session_factory() as db:
        channel_service = ChannelService(db)
        channel = await channel_service.get_channel(channel_id)
        if channel is None:
            await websocket.close(code=4004, reason="Channel not found")
            return

    # 2. Accept and register connection
    await connection_manager.connect(websocket, channel_id, client_id)
    logger.info(
        "WebSocket connected: channel=%s client=%s",
        channel_id,
        client_id,
    )

    # 3. Send join notification (system message)
    try:
        async with session_factory() as db:
            redis = websocket.app.state.redis
            transport = NativeTransport(redis=redis)
            msg_service = MessageService(db)
            ch_service = ChannelService(db)
            comm_service = CommunicationService(
                message_service=msg_service,
                channel_service=ch_service,
                transport=transport,
            )
            await comm_service.send_system_message(
                channel_id=channel_id,
                content=f"{client_id} joined the channel",
            )
    except Exception:
        logger.exception(
            "Failed to send join notification: channel=%s client=%s",
            channel_id,
            client_id,
        )

    # 4. Receive loop
    try:
        while True:
            data = await websocket.receive_json()

            # Validate incoming payload
            try:
                payload = WebSocketSendPayload(**data)
            except ValidationError as exc:
                await websocket.send_json(
                    {"type": "error", "detail": exc.errors()}
                )
                continue

            # Persist and broadcast via CommunicationService (fresh session)
            async with session_factory() as db:
                redis = websocket.app.state.redis
                transport = NativeTransport(redis=redis)
                msg_service = MessageService(db)
                ch_service = ChannelService(db)
                comm_service = CommunicationService(
                    message_service=msg_service,
                    channel_service=ch_service,
                    transport=transport,
                )
                msg = await comm_service.send_channel_message(
                    channel_id=channel_id,
                    content=payload.content,
                    sender_user_identifier=client_id,
                    message_type=payload.message_type,
                )

                # Update read cursor for the sender
                await msg_service.update_read_cursor(
                    channel_id=channel_id,
                    last_read_message_id=str(msg.id),
                    user_identifier=client_id,
                )

    except WebSocketDisconnect:
        logger.info(
            "WebSocket disconnected: channel=%s client=%s",
            channel_id,
            client_id,
        )
    except Exception:
        logger.exception(
            "WebSocket error: channel=%s client=%s",
            channel_id,
            client_id,
        )
    finally:
        # 5. Disconnect and send leave notification
        connection_manager.disconnect(channel_id, client_id)

        try:
            async with session_factory() as db:
                redis = websocket.app.state.redis
                transport = NativeTransport(redis=redis)
                msg_service = MessageService(db)
                ch_service = ChannelService(db)
                comm_service = CommunicationService(
                    message_service=msg_service,
                    channel_service=ch_service,
                    transport=transport,
                )
                await comm_service.send_system_message(
                    channel_id=channel_id,
                    content=f"{client_id} left the channel",
                )
        except Exception:
            logger.exception(
                "Failed to send leave notification: channel=%s client=%s",
                channel_id,
                client_id,
            )
