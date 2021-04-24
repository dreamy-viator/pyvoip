import websockets
import asyncio
import json
import aioice

STUN_SERVER = ("stun.l.google.com", 19302)


connected = set()


async def handler():
    connection = aioice.Connection(
        ice_controlling=True, components=1, stun_server=STUN_SERVER
    )
    websocket = await websockets.connect('ws://localhost:8765')
    joinCmd = json.dumps({
        "cmd": "joinRoom",
        "roomId": "1"
    })
    await websocket.send(joinCmd)
    print("> {}".format(joinCmd))

    response = await websocket.recv()
    print("< {}".format(response))

    resp = json.loads(response)

    respCmd = resp["cmd"]
    if respCmd == "playStream":
        print('playstream')
        await connection.gather_candidates()
        await websocket.send(
            json.dumps(
                {
                    "cmd" : "candidate",
                    "candidates": [c.to_sdp() for c in connection.local_candidates],
                    "password": connection.local_password,
                    "username": connection.local_username,
                }
            )
        )
        response = await websocket.recv()
        print("< {}".format(response))

        resp = json.loads(response)
        for c in resp["candidates"]:
            await connection.add_remote_candidate(aioice.Candidate.from_sdp(c))

        await connection.add_remote_candidate(None)
        connection.remote_username = resp["username"]
        connection.remote_password = resp["password"]


        await connection.connect()
        print("connected")
        # echo data back
        data, component = await connection.recvfrom()
        print("echoing %s on component %d" % (repr(data), component))
        await connection.sendto(data, component)

    elif respCmd == "candidate":
        print('candidate')
        print(resp)
        for c in resp["candidates"]:
            await connection.add_remote_candidate(aioice.Candidate.from_sdp(c))

        await connection.add_remote_candidate(None)
        connection.remote_username = resp["username"]
        connection.remote_password = resp["password"]

        await connection.gather_candidates()
        await websocket.send(
            json.dumps(
                {
                    "cmd": "candidate",
                    "candidates": [c.to_sdp() for c in connection.local_candidates],
                    "password": connection.local_password,
                    "username": connection.local_username,
                }
            )
        )
        await connection.connect()
        print("connected")
        data = b"hello"
        component = 1
        print("sending %s on component %d" % (repr(data), component))
        await connection.sendto(data, component)
        data, component = await connection.recvfrom()
        print("received %s on component %d" % (repr(data), component))

    elif respCmd == "description":
        print('description')
        print(resp)

asyncio.get_event_loop().run_until_complete(handler())