import asyncio
import websockets
import json


connected = set()
rooms = dict()

async def handler(websocket, path):
    global connected
    global rooms
    # register
    connected.add(websocket)
    try:
        async for message in websocket:
            m = json.loads(message)
            if m["cmd"] == "joinRoom":
                roomId = m['roomId']
                print('roomId :', roomId)
                if roomId not in rooms.keys():
                    rooms[roomId] = 1
                elif rooms[roomId] >= 2:
                    websocket.send(json.dumps({
                            "cmd": "err",
                            "reason" : "roomFull"
                    }))
                else:
                    rooms[roomId] += 1
                    await websocket.send(json.dumps({
                        "cmd": "playStream"
                    }))

            elif m["cmd"] == "description":
                for c in connected:
                    if c != websocket:
                        await c.send(message)

            elif m["cmd"] == "candidate":
                for c in connected:
                    if c != websocket:
                        await c.send(message)
    except websockets.ConnectionClosed:
        print('clear all rooms')
        rooms.clear()


    finally:
        # Unregister.
        connected.remove(websocket)

start_server = websockets.serve(handler, 'localhost', 8765)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()