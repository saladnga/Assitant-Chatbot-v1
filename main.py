from openai import OpenAI
from fastapi import FastAPI, Form, Request, WebSocket, WebSocketDisconnect
from typing import Annotated
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import os
from dotenv import load_dotenv
import uuid


load_dotenv()


openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


app = FastAPI()


templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")


chat_sessions = {}


@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse(
        "home.html", {"request": request, "chat_responses": []}
    )


@app.websocket("/ws")
async def chat(websocket: WebSocket):
    await websocket.accept()

    session_id = str(uuid.uuid4())
    chat_sessions[session_id] = {
        "responses": [],
        "messages": [
            {
                "role": "system",
                "content": "You are a versatile AI assistant designed to provide accurate and reliable information, assist with learning, problem-solving, and creative tasks, and adapt to user preferences. You break down complex topics into simple explanations, offer personalized solutions, and maintain a friendly, professional tone. Upholding ethical standards, you ensure safe and respectful interactions while empowering users with knowledge and inspiration",
            }
        ],
    }

    try:
        while True:
            user_input = await websocket.receive_text()

            chat_sessions[session_id]["messages"].append(
                {"role": "user", "content": user_input}
            )

            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=chat_sessions[session_id]["messages"],
                temperature=0.6,
                stream=True,
            )

            ai_response = ""

            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    ai_response += chunk.choices[0].delta.content
                    await websocket.send_text(chunk.choices[0].delta.content)

            if ai_response:
                chat_sessions[session_id]["messages"].append(
                    {"role": "assistant", "content": ai_response}
                )
                chat_sessions[session_id]["responses"].append(ai_response)

    except WebSocketDisconnect:
        if session_id in chat_sessions:
            del chat_sessions[session_id]
        await websocket.close()

    except Exception as e:
        await websocket.send_text(f"Error: {str(e)}")


@app.post("/", response_class=HTMLResponse)
async def chat(request: Request, user_input: Annotated[str, Form()]):
    session_id = str(uuid.uuid4())
    chat_sessions[session_id] = {
        "responses": [],
        "messages": [
            {
                "role": "system",
                "content": "You are a versatile AI assistant designed to provide accurate and reliable information, assist with learning, problem-solving, and creative tasks, and adapt to user preferences. You break down complex topics into simple explanations, offer personalized solutions, and maintain a friendly, professional tone. Upholding ethical standards, you ensure safe and respectful interactions while empowering users with knowledge and inspiration",
            }
        ],
    }
    chat_sessions[session_id]["messages"].append(
        {"role": "assistant", "content": user_input}
    )

    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=chat_sessions[session_id]["messages"],
        temperature=0.6,
    )

    bot_response = response.choices[0].message.content
    chat_sessions[session_id]["messages"].append(
        {"role": "assistant", "content": bot_response}
    )

    return templates.TemplateResponse(
        "home.html", {"request": request, "chat_responses": [bot_response]}
    )


@app.get("/image", response_class=HTMLResponse)
async def image_page(request: Request):
    return templates.TemplateResponse("image.html", {"request": request})


@app.post("/image", response_class=HTMLResponse)
async def create_image(request: Request, user_input: Annotated[str, Form()]):
    response = openai.images.generate(prompt=user_input, n=1, size="1024x1024")
    image_url = response.data[0].url
    return templates.TemplateResponse(
        "image.html", {"request": request, "image_url": image_url}
    )
