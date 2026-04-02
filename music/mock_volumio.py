#!/usr/bin/env python3
from aiohttp import web
import socketio
import asyncio

sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')
app = web.Application()
sio.attach(app)

@sio.event
async def connect(sid, environ):
    print(f"Client {sid} connected")
    await sio.emit('pushState', {
        'title': 'Test Song',
        'artist': 'Test Artist',
        'uri': 'test://song'
    }, to=sid)

@sio.event
async def getState(sid):
    print(f"getState from {sid}")
    await sio.emit('pushState', {
        'title': 'Test Song',
        'artist': 'Test Artist',
        'uri': 'test://song'
    }, to=sid)

@sio.event
async def disconnect(sid):
    print(f"Client {sid} disconnected")

if __name__ == '__main__':
    print("Mock Volumio server running on http://localhost:3000")
    web.run_app(app, port=3000)
