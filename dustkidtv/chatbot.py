import re
import socket
import json
import threading
from emoji import demojize

DEFAULT_TWITCH_FILE = 'twitch_config.json'
MAX_REPLAY_REQUESTS = 10

def decode(message):
    message = demojize(message).replace('\r', '')
    username, channel, message = re.search(r':(.*)\!.*@.*\.tmi\.twitch\.tv PRIVMSG #(.*?) :(.*)', message).groups()
    return username, message

def parseId(id):
    if isinstance(id, int):
        return id
    numbers=re.findall('[-]?[\d]+', id)
    if len(numbers)==0:
        print('No replay ID found in ' + id)
        return None
    elif len(numbers)>1:
        print('Not sure which one is the replay ID in ' + id)
        return None
    else:
        return int(numbers[0])


class TwitchReader(threading.Thread):

    #TODO add reconnect if connection drops

    def __init__(self, name="TwitchReader", config_file=DEFAULT_TWITCH_FILE):
        threading.Thread.__init__(self)
        self.name = name

        # keep sensitive information stored in a separate config file
        self._config = {
            'server': '',
            'port': 0,
            'nickname': '',
            'token': '',
            'channel': '',
            "debug" : false
        }
        self.load_config(filename=config_file)

        self.debug = self._config["debug"]
        self.handler = None
        self.running = False

    def load_config(self, filename):
        with open(filename, 'r') as f:
            self._config = json.load(f)

    def save_config(self, filename):
        with open(filename, 'w') as f:
            json.dump(self._config, f)

    def stop(self):
        self.running = False

    def run(self):
        print('Connecting to Twitch')
        if self.debug:
            with open('dustkidtv.log', 'a', encoding='utf-8') as logfile:
                logfile.write('Connecting to Twitch\n')

        sock = socket.socket()
        if self.handler is not None:
            self.handler.socket = sock
            self.handler.channel = self._config["channel"]
            self.handler.debug = self._config["debug"]
        sock.connect((self._config['server'], self._config['port']))
        sock.send(f'PASS {self._config["token"]}\n'.encode('utf-8'))
        sock.send(f'NICK {self._config["nickname"]}\n'.encode('utf-8'))
        sock.send(f'JOIN {self._config["channel"]}\n'.encode('utf-8'))

        print('Entering Chat loop')
        if self.debug:
            with open('dustkidtv.log', 'a', encoding='utf-8') as logfile:
                logfile.write('Entering Chat loop\n')

        self.running = True
        while self.running:
            resp = sock.recv(2048).decode('utf-8')

            if resp.startswith('PING'):
                sock.send("PONG :tmi.twitch.tv2 3\n".encode('utf-8'))
            elif len(resp) > 0 and 'PRIVMSG' in resp:
                if self.handler is not None:
                    username, message = decode(resp)
                    self.handler.receive(username, message)
                    # sock.send(f'PRIVMSG {self._config["channel"]} :received message\n'.encode('utf-8'))
            if self.debug:
                print(resp)

        print('Closing socket')
        if self.debug:
            with open('dustkidtv.log', 'a', encoding='utf-8') as logfile:
                logfile.write('Closing socket\n')

        sock.close()


class Chatbot(threading.Thread):
    def __init__(self, name="Chatbot", replay=None):
        threading.Thread.__init__(self)
        self.name = name

        self.debug = False

        self.socket = None
        self.channel = None
        self.message_queue = []
        self.message_condition = threading.Condition()
        self.running = False

        self.replaySkip=False
        self.replayRequests=[]
        self.replayRequestsCounter=0

        self.currentReplay = replay

    def setReplay(self, replay):
        self.currentReplay = replay

    def receive(self, username, message):
        self.message_condition.acquire()
        self.message_queue.append((username, message))
        self.message_condition.notify()
        self.message_condition.release()

    def stop(self):
        self.message_condition.acquire()
        self.running = False
        self.message_condition.notify()
        self.message_condition.release()

    def say(self, message):
        self.socket.send(f'PRIVMSG {self.channel} :{message}'.encode('utf-8'))

    def run(self):
        print('Handler Starting!')
        if self.debug:
            with open('dustkidtv.log', 'a', encoding='utf-8') as logfile:
                logfile.write('Handler Starting!\n')

        self.running = True

        while self.running:
            self.message_condition.acquire()
            while not self.message_queue and self.running:
                self.message_condition.wait()

            for username, message in self.message_queue:

                if message.startswith('!request ') or message.startswith('!rq '):
                    if self.replayRequestsCounter > MAX_REPLAY_REQUESTS:
                        self.say(f'@{username} maximum number of replay requests reached, please try again later ({self.replayRequestsCounter} replays in queue)\n')
                    else:
                        id = parseId(message)
                        if id is not None:
                            print('adding ID %i to replay requests' % id)
                            if self.debug:
                                with open('dustkidtv.log', 'a', encoding='utf-8') as logfile:
                                    logfile.write('adding ID %i to replay requests\n' % id)
                            self.replayRequests.append(id)
                            self.replayRequestsCounter += 1
                            self.say(f'@{username} requested replay ID {id} (#{self.replayRequestsCounter} in queue)\n')
                        else:
                            self.say(f'@{username} invalid replay ID: to request a replay, use !request followed by the dustkid ID\n')

                elif message == '!skip':
                    print('skip request received')
                    if self.debug:
                        with open('dustkidtv.log', 'a', encoding='utf-8') as logfile:
                            logfile.write('skip request received\n')
                    if self.currentReplay is not None:
                        self.currentReplay.skip.set()
                        self.say(f'@{username} requested replay skip\n')

                elif message == '!info' or message == '!replay' or message == '!map' or message == '!level':
                    print('info request received')
                    if self.debug:
                        with open('dustkidtv.log', 'a', encoding='utf-8') as logfile:
                            logfile.write('info request received')
                    if self.currentReplay is not None:
                        self.say(f'@{username} the current replay is {self.currentReplay.levelname} by {self.currentReplay.username}, score {self.currentReplay.completion}{self.currentReplay.finesse}, time {self.currentReplay.time/1000.}s {self.currentReplay.getReplayPage()}\n')


            self.message_queue.clear()

            self.message_condition.release()
            # release the lock so that other messages can be queued while current ones are read

        print('Handler stopping')
        if self.debug:
            with open('dustkidtv.log', 'a', encoding='utf-8') as logfile:
                logfile.write('Handler stopping\n')
