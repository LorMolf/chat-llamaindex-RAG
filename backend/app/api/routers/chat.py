from typing import List
import os

from fastapi.responses import StreamingResponse

from app.utils.json import json_to_model
from app.utils.index import get_index
from fastapi import APIRouter, Depends, HTTPException, Request, status
from llama_index import VectorStoreIndex
from llama_index.llms import MessageRole, ChatMessage

from app.utils.interface import _ChatData

from typing import Any

chat_router = r = APIRouter()

@r.post("")
async def chat(
    request: Request,
    # Note: To support clients sending a JSON object using content-type "text/plain",
    # we need to use Depends(json_to_model(_ChatData)) here
    data: _ChatData = Depends(json_to_model(_ChatData)),
    index: Any = None
):
    print(f"[data]: {data}")
    # check preconditions and get last message
    with open('log', 'w') as log_file:
        log_file.write(str(data.messages))
        log_file.write('\n\n')
        log_file.write(str(data.bot_name))
    if len(data.messages) == 0 or data.bot_name == None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No messages provided",
        )
    lastMessage = data.messages.pop()
    if lastMessage.role != MessageRole.USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Last message must be from user",
        )
    # convert messages coming from the request to type ChatMessage
    bot_name = data.bot_name
    index = get_index(bot_name=bot_name)

    messages = [
        ChatMessage(
            role=m.role,
            content=m.content,
        )
        for m in data.messages
    ]
    # query chat engine
    chat_engine = index.as_chat_engine()
    response = chat_engine.stream_chat(lastMessage.content,messages)

    # stream response
    async def event_generator():
        for token in response.response_gen:
            #print(token)
            # If client closes connection, stop sending events
            if await request.is_disconnected():
                break
            yield token

    return StreamingResponse(event_generator(), media_type="text/plain")
