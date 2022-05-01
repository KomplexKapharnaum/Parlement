import paho.mqtt.client as mqtt 
import liblo
import time, sys
from enum import Enum

M32_IP = "10.0.100.18:10023"
MAC_IP = "10.0.100.20:12000"

buzzersCount = 5

memSablier = 3

class States(Enum):
    INIT    = 1
    CONN    = 2
    START   = 3
    READY   = 4
    BUZZED  = 5
    CHRONO  = 6
    STOP    = 7
    BLACKOUT= 8
    OFF     = 9


state = States.INIT
leader = 0

def setState(s):
    global state
    state = s
    print("- ", s)
    


######## MQTT

mqttBroker ="127.0.0.1"

def on_connect(client, userdata, flags, rc):
    print("Connected to MQTT broker ", mqttBroker)
    client.subscribe("k32/event/#")
    client.subscribe("k32/c16/#")
    client.subscribe("k32/all/#")
    global state
    setState(States.START)
    


def on_disconnect(client, userdata, rc):
    global state
    setState(States.CONN)
    print("- State", "CONN")
    print("Disconnected from MQTT broker.. retrying")
    client.reconnect_delay_set(1,30)

def on_publish(client, userdata, mid):
    # print("Published")
    pass

def on_message(client, userdata, message):
    global leader
    print("Received message '" + str(message.payload) + "' on topic '" + message.topic + "' with QoS " + str(message.qos))
    
    # BUZZ
    if message.topic == "k32/event/buzz" and state == States.READY:
        
        # BUZZED    
        setState(States.BUZZED)
        leader = int(message.payload)
        buzz(leader, 1)
        m32_open(leader)
        client.publish("k32/l"+str(leader)+"/leds/mem", "6", qos=1)     # Leader -> white
        print("k32/l"+str(leader)+"/leds/mem", "6")
        
        for i in range(1,buzzersCount+1):
            if i != leader:
                client.publish("k32/l"+str(i)+"/leds/mem", "0", qos=1)  # Non-Leader -> blue 
                m32_mute(i)
                print("k32/l"+str(i)+"/leds/mem", "0")
                
    # UNBUZZ
    if message.topic == "k32/event/unbuzz":
        buzz(int(message.payload), 0)
                        
    # END
    if state == States.CHRONO and message.topic.startswith("k32/event/sablier"):
        print('SABLIER !')
        # client.publish("k32/all/leds/mem", "7", qos=1) # RED breath
        for i in range(1,buzzersCount+1):               
            if i != leader:
                client.publish("k32/l"+str(i)+"/leds/mem", "7", qos=1)   # RED breath
                print("k32/l"+str(i)+"/leds/mem", "7")
            else:
                client.publish("k32/l"+str(i)+"/leds/mem", "8", qos=1)   # RED breath with white panel
                print("k32/l"+str(i)+"/leds/mem", "8")
        setState(States.READY)
        
    # QUIZZ CTRL
    if message.topic == "k32/c16/leds/mem" or message.topic == "k32/all/leds/mem":
        s = int(message.payload)
        global memSablier
        if s == 0 and state != States.STOP:                  # C16 @0 = Stop
            setState(States.START)
        
        elif s > 0 and s < 6:
            memSablier = s     
            # C16 @1 = Speed 45
            # C16 @2 = Speed 30
            # C16 @3 = Speed 18
            # C16 @4 = Speed 9
            # C16 @5 = Speed 3
        
    # QUIZZ OFF
    if message.topic == "k32/c16/leds/stop":
        setState(States.STOP)
    if message.topic == "k32/all/leds/stop":
        setState(States.BLACKOUT)
        

######### OSC
try:
    m32 = liblo.Address("osc.udp://"+M32_IP+"/")
    macintosh = liblo.Address("osc.udp://"+MAC_IP+"/")
except liblo.AddressError as err:
    print(err)
    time.sleep(3)
    sys.exit()
    
def m32_mute(ch=None):
    if ch:
        liblo.send(m32, "/ch/0"+str(ch)+"/mix/on", 0)
        print('M32', M32_IP, "/ch/0"+str(ch)+"/mix/on", 0 )
    else:
        for i in range(1,buzzersCount+1):
            liblo.send(m32, "/ch/0"+str(i)+"/mix/on", 0)
            print('M32', M32_IP, "/ch/0"+str(i)+"/mix/on", 0 )
        
        
def m32_open(ch):
    liblo.send(m32, "/ch/0"+str(ch)+"/mix/on", 1)
    print('M32', M32_IP, "/ch/0"+str(ch)+"/mix/on", 1 )
    
def buzz(who, how):
    liblo.send(macintosh, "/1/push"+str(who), how)
    print('BUZZ', MAC_IP, "/1/push"+str(who), how)


######### MAIN LOOP 

while True:
    if state == States.INIT:
        client = mqtt.Client("Controller")
        client.loop_start()
        client.on_message=on_message 
        client.on_connect=on_connect 
        client.on_publish=on_publish 
        client.on_disconnect=on_disconnect 
        client.connect_async(mqttBroker)  
        setState(States.CONN)
        
    elif state == States.CONN:
        time.sleep(.5)
        
    elif state == States.START:
        m32_mute()
        client.publish("k32/all/leds/mem", "0", qos=1)
        time.sleep(1)
        setState(States.READY)
        
    elif state == States.STOP or state == States.BLACKOUT:
        m32_mute()
        if state == States.STOP: 
            client.publish("k32/all/leds/mem", "0", qos=1)
        elif state == States.BLACKOUT: 
            client.publish("k32/all/leds/stop", "", qos=1)
        time.sleep(1)
        setState(States.OFF)
    
    elif state == States.BUZZED:
        # CHRONO
        time.sleep(1)
        setState(States.CHRONO)
        client.publish("k32/c1/leds/mem", str(memSablier), qos=1)
        print("k32/c1/leds/mem", str(memSablier))
        
        
    else:
        time.sleep(.1)
