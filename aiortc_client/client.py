import socketio
import random
import string 
import asyncio
import smtplib, ssl

from aiortc.contrib.media import MediaPlayer
from aiortc import RTCPeerConnection,RTCSessionDescription
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


#*****************************
# GLOBAL VARIABLES
#*****************************
SERVER_URL = "https://192.168.1.115:443"
ROOM_NAME_SIZE = 4
TIMEOUT=30
TIMEOUT_BYE = TIMEOUT*3
VIDEO_SIZE = "320x240"

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 465
EMAIL_FROM = "EMAIL@gmail.com"
EMAIL_TO = "EMAIL@gmail.com"
PASSWORD = "PASSWORD"

#*****************************
# FUNCTIONS
#*****************************
def getRandomName(length):
    return ''.join(random.choice(string.ascii_lowercase) for i in range(length))

def receiver_queue(signaling, messages):
    queue = asyncio.Queue()
    for signal in messages:
        signaling.on(signal, lambda content, signal=signal: queue.put_nowait((signal, content)))
    return queue

async def bye(sio):
    await sio.emit("bye")
    del videoPlayer
    del audioPlayer
    del peerConnection    

def sendEmail(link):
    message = MIMEMultipart("alternative")
    message["Subject"] = "Doorbell"
    message["From"] = EMAIL_FROM
    message["To"] = EMAIL_TO

    html="Someone used the doorbell : <a href='"+link+"'>Click here to open</a>"
    part=MIMEText(html, "html")
    message.attach(part)
    
    with smtplib.SMTP_SSL(SMTP_SERVER, 465) as srv:
        srv.ehlo()
        srv.login(EMAIL_FROM, PASSWORD)
        srv.sendmail(EMAIL_FROM,EMAIL_TO, message.as_string())
    
async def main():
    while True:
        sio = socketio.AsyncClient(ssl_verify=False)
        messages = ["created", "joined", "full", "new_peer", "invite", "ok", "ice_candidate", "bye"]
        messagesQueue = receiver_queue(sio, messages)
        
        #Wait until keypress (to be replaced later by the pushbutton press event)
        input("Press enter to continue")
        
        #Connect to the signaling server.
        await sio.connect(SERVER_URL)
        
        #Join a conference room with a random name (send 'create' signal with room name).
        roomName = getRandomName(ROOM_NAME_SIZE)
        await sio.emit("join", roomName)
        
        #Wait for response. If response is 'joined' or 'full', stop processing and return to the loop. Go on if response is 'created'.
        response = await messagesQueue.get()
        responseMessage = response[0]
        
        if responseMessage == "full" or responseMessage == "joined":
            continue
        elif responseMessage != "created":
            print("Room not created")
            continue
        
        #Send a message (SMS, Telegram, email, ...) to the user with the room name. Or simply start by printing it on the terminal. 
        link = SERVER_URL + "?room=" + roomName
        print("Dring dring : " + link)

        sendEmail(link)
        
        videoPlayer = None
        audioPlayer = None
        peerConnection = None
        
        #Wait (with timeout) for a 'new_peer' message. If timeout, send 'bye' to signaling server and return to the loop.        
        try:
            response = await asyncio.wait_for(messagesQueue.get(), timeout=TIMEOUT)
            responseMessage = response[0]
            if responseMessage == "new_peer":
                print("new_peer")
        except asyncio.TimeoutError:
            print("Timeout 'new_peer' after " + str(TIMEOUT) + " s")
            await bye(sio)
            
        #Wait (with timeout) for an 'invite' message. If timemout, send 'bye to signaling server and return to the loop.  
        try:
            response = await asyncio.wait_for(messagesQueue.get(), timeout=TIMEOUT)
            responseMessage = response[0]
            if responseMessage == "invite":
                #Acquire the media stream from the Webcam.
                videoPlayer = MediaPlayer("/dev/video0", format="v4l2", options={"video_size": VIDEO_SIZE})
                audioPlayer = MediaPlayer("default", format="pulse")
                
                #Create the PeerConnection and add the streams from the local Webcam.
                peerConnection = RTCPeerConnection()
                peerConnection.addTrack(videoPlayer.video)
                peerConnection.addTrack(audioPlayer.audio)
                
                #Add the SDP from the 'invite' to the peer connection.
                offer = response[1]
                sdp = RTCSessionDescription(sdp = offer['sdp'], type=offer['type'])
                await peerConnection.setRemoteDescription(sdp)
                
                #Generate the local session description (answer) and send it as 'ok' to the signaling server.
                answer = await peerConnection.createAnswer()
                print(answer)
                await peerConnection.setLocalDescription(answer)
                answer = peerConnection.localDescription
                
                await sio.emit("ok", answer)
        except asyncio.TimeoutError:
            print("Timeout 'invite' after " + str(TIMEOUT) + " s")
            await bye(sio)
            continue
        
        #Wait (with timeout) for a 'bye' message.
        try:
            response = await asyncio.wait_for(messagesQueue.get(), timeout=TIMEOUT_BYE)
            responseMessage = response[0]
            if responseMessage == "bye":
                #Send a 'bye' message back and clean everything up (peerconnection, media, signaling).
                await bye(sio)
        except asyncio.TimeoutError:
            print("Timeout bye " + str(TIMEOUT_BYE) + " s")
            await sio.emit("bye", roomName)                
            continue
        
#*****************************
# MAIN PROGRAM
#*****************************
asyncio.run(main())
