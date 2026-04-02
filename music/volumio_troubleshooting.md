# Volumio Connection Troubleshooting Guide

*Last updated: 2026-04-02 18:52:22*

## Overview

You are seeing errors like:

    OPEN packet not returned by server
    RemoteDisconnected('Remote end closed connection without response')

This typically indicates a **Socket.IO version mismatch** or incorrect
connection method to Volumio.

------------------------------------------------------------------------

## Step 1: Verify Basic Connectivity

Run these commands from your Raspberry Pi:

``` bash
ping -c 3 frontspeakers.local
curl http://frontspeakers.local/api/v1/getState
```

If this fails: - Use the device IP instead of `.local` - Example:

``` bash
curl http://192.168.1.50/api/v1/getState
```

------------------------------------------------------------------------

## Step 2: Test Socket.IO Endpoint

``` bash
curl "http://frontspeakers.local:3000/socket.io/?EIO=3&transport=polling"
```

Expected: - Response starts with something like `96:0{...}`

If not: - Volumio may not be reachable on port 3000 - Or wrong protocol
version is being used

------------------------------------------------------------------------

## Step 3: Fix Python Socket.IO Version (IMPORTANT)

Volumio 3 uses **Socket.IO 2.x**

Install compatible Python libraries:

``` bash
pip uninstall -y python-socketio python-engineio
pip install python-socketio==4.6.0 python-engineio==3.14.2
```

------------------------------------------------------------------------

## Step 4: Use Correct Python Client

Example working client:

``` python
import socketio

sio = socketio.Client()

@sio.event
def connect():
    print("Connected")
    sio.emit("getState", "")

@sio.on("pushState")
def on_push_state(data):
    print(data.get("artist"), "-", data.get("title"))

sio.connect("http://192.168.1.50:3000")
sio.wait()
```

------------------------------------------------------------------------

## Step 5: Consider Using REST Instead (Simpler)

Your existing script already works with REST:

``` python
requests.get("http://192.168.1.50/api/v1/getState", timeout=5)
```

Advantages: - No Socket.IO issues - More stable - Easier debugging

------------------------------------------------------------------------

## Step 6: Common Issues Checklist

-   [ ] Wrong port (must be 3000 for Socket.IO)
-   [ ] Using `.local` hostname instead of IP
-   [ ] Python socketio version mismatch
-   [ ] Network instability
-   [ ] Volumio not running or API disabled

------------------------------------------------------------------------

## Step 7: Debug Logging

Enable verbose logs:

``` python
socketio.Client(logger=True, engineio_logger=True)
```

------------------------------------------------------------------------

## Notes

-   REST = best for simple display updates
-   Socket.IO = needed only for real-time push updates
-   Volumio WebSocket is actually Socket.IO (not raw WebSocket)

------------------------------------------------------------------------

## Recommendation

Start with REST API. Only move to Socket.IO if you need live updates.
