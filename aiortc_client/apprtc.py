import socketio
import asyncio
import random
import string
import RPi.GPIO as GPIO # Import Raspberry Pi GPIO library
from time import sleep
 
TIMEOUT = 10.0
LED = True

# asyncio
sio = socketio.AsyncClient(ssl_verify=False,logger=True, engineio_logger=True)

def blink_led(times):
    for _ in range(times):
        GPIO.output(8, GPIO.HIGH)
        sleep(0.3)                  
        GPIO.output(8, GPIO.LOW)  
        sleep(0.3)

async def cleanup_restart(room_name):
    if LED:
        blink_led(3)
    await sio.emit('bye', room_name)
    await sio.disconnect()
    await sio.wait()

offer = ''
async def run():
    @sio.event
    async def created(data):
        print('ok')
        queue.put_nowait('created')

    @sio.event
    async def joined(data):
        print('not ok')
        queue.put_nowait('joined')

    @sio.event
    async def full(data):
        print('not ok')
        queue.put_nowait('full')

    @sio.event
    async def new_peer():
        print('wouw')
        queue.put_nowait('new_peer')

    @sio.event
    async def invite(data):
        print('wouw')
        queue.put_nowait('invite')
        offer = data




    while True:
        queue = asyncio.Queue() # Create a queue that we will use to store the server responses.
        #1. Wait until pushbutton press event.
        print('press button...')
        GPIO.wait_for_edge(10, GPIO.RISING)
        #print("button was pressed")

        #2. Connect to the signaling server.
        await sio.connect('https://192.168.43.240:443')
        print('my sid is', sio.sid)

        #3. Join a conference room with a random name (send 'create' signal with room name).
        room_name = ''.join(random.SystemRandom().choice(string.ascii_letters) for _ in range(10))
        print('my room is', room_name)

        while not sio.connected:
            pass
            
        await sio.emit('join', room_name)


        #4. Wait for response. If response is 'joined' or 'full', stop processing and return to the loop. Go on if response is 'created'.
        answer = await queue.get()
        print(answer)
        if answer == 'full' or answer == 'joined':
            print('wrong answer')
            await cleanup_restart(room_name)
            continue
        
        print('room created')
        #5. Send a message (SMS, Telegram, email, ...) to the user with the room name. Or simply start by printing it on the terminal.
        print('wesh connecte toi à la room', room_name)
        #6. Wait (with timeout) for a 'new_peer' message. If timeout, send 'bye' to signaling server and return to the loop.
        
        try:
            answer = await asyncio.wait_for(queue.get(), timeout=TIMEOUT)
            if answer != 'new_peer':
                raise Exception
        except (asyncio.TimeoutError, Exception):
                print('peer failed to connect on time')
                await cleanup_restart(room_name)
                continue
            
        print('peer connected \o/')

'''
        #7. Wait (with timeout) for an 'invite' message. If timemout, send 'bye' to signaling server and return to the loop. 
        try:
            answer = await asyncio.wait_for(queue.get(), timeout=TIMEOUT)
            if answer != 'invite':
                raise Exception
        except (asyncio.TimeoutError, Exception):
                print('invite not received on time')
                await cleanup_restart(room_name)
                continue

        print(offer)
'''

        #8. Acquire the media stream from the Webcam.
        #9. Create the PeerConnection and add the streams from the local Webcam.
        #10. Add the SDP from the 'invite' to the peer connection.
        #11. Generate the local session description (answer) and send it as 'ok' to the signaling server.
        #12. Wait (with timeout) for a 'bye' message.    
        #13. Send a 'bye' message back and clean everything up (peerconnection, media, signaling).
        #await sio.emit('bye', room_name)
        #print('room byed')
        #await sio.disconnect()
        print('disconnected')
        break
    

if __name__ == "__main__":   
    GPIO.setwarnings(False) # Ignore warning for now
    GPIO.setmode(GPIO.BOARD) # Use physical pin numbering
    GPIO.setup(10, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) # Set pin 10 to be an input pin and set initial value to be pulled low (off)
    if LED:
        GPIO.setup(8, GPIO.OUT, initial=GPIO.LOW)   # Set pin 8 to be an output pin and set initial value to low (off)
         


    # run event loop
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run())
    except KeyboardInterrupt:
        print("Ctrl+C pressed...")
        sys.exit(1)
    finally:
        GPIO.cleanup() # Clean up
        #a = 1
        #loop.run_until_complete(sio.disconnect())
    
