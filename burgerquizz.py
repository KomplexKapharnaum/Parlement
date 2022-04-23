import paho.mqtt.client as mqtt 
import liblo
import time, sys
from enum import Enum

M32_IP = "10.0.100.18"

buzzersCount = 5

memSablier = 2

class States(Enum):
    INIT    = 1
    CONN    = 2
    START   = 3
    READY   = 4
    BUZZED  = 5
    CHRONO  = 6
    STOP    = 7
    OFF     = 8


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
    print("Received message '" + str(message.payload) + "' on topic '" + message.topic + "' with QoS " + str(message.qos))
    
    # BUZZ
    if message.topic == "k32/event/buzz" and state == States.READY:
        
        # BUZZED    
        setState(States.BUZZED)
        leader = int(message.payload)
        m32_open(leader)
        client.publish("k32/l"+str(leader)+"/leds/mem", "1", qos=1)
        print("k32/l"+str(leader)+"/leds/mem", "1")
        
        for i in range(1,buzzersCount+1):
            if i != leader:
                client.publish("k32/l"+str(i)+"/leds/mem", "0", qos=1)
                m32_mute(i)
                print("k32/l"+str(i)+"/leds/mem", "0")
                        
    # END
    if message.topic.startswith("k32/event/sablier") and state == States.CHRONO:
        setState(States.READY)
        
    # QUIZZ CTRL
    if message.topic == "k32/c16/leds/mem":
        s = int(message.payload)
        global memSablier
        if s == 0:                  # C16 @0 = Stop
            setState(States.START)
            
        if s == 1: memSablier = 2   # C16 @1 = Speed 45
        if s == 2: memSablier = 4   # C16 @2 = Speed 30
        if s == 3: memSablier = 5   # C16 @3 = Speed 18
        if s == 4: memSablier = 6   # C16 @3 = Speed 9
        if s == 5: memSablier = 7   # C16 @3 = Speed 3
        
    # QUIZZ OFF
    if message.topic == "k32/c16/leds/stop":
        setState(States.STOP)
        

######### OSC
try:
    m32 = liblo.Address("osc.udp://"+M32_IP+":10023/")
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
        
    elif state == States.STOP:
        m32_mute()
        client.publish("k32/all/leds/mem", "0", qos=1)
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
