import os
import io
import time
import json
import threading
from subprocess import Popen, PIPE, STDOUT
from tkinter import Tk, Frame, Button, Label, Message, StringVar, BOTH, LEFT, NW, N, E, S, W
from PIL import Image, ImageTk, ImageDraw, ImageFont
from textwrap import wrap

from dustkidtv.replays import ReplayQueue, Replay, InvalidReplay, BannedReplay
from dustkidtv.chatbot import TwitchReader, Chatbot
from dustkidtv.maps import BANNED_MAPS

THUMBNAIL_SIZE = (382, 182)
ICON_SIZE = (32, 32)
PAD = 3
MAX_TEXT_LEN = 26
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

dustkidtvThumbnail = 'dustkidtv/assets/dustkidtv-tashizuna.png'
srank = 'dustkidtv/assets/dfsrank.png'
arank = 'dustkidtv/assets/dfarank.png'
brank = 'dustkidtv/assets/dfbrank.png'
crank = 'dustkidtv/assets/dfcrank.png'
drank = 'dustkidtv/assets/dfdrank.png'
apple = 'dustkidtv/assets/dfapple.png'
star = 'dustkidtv/assets/dfstar.png'
freesans = "dustkidtv/assets/FreeSansBold.ttf"


class Window(Frame):
    dustkidImg = Image.open(dustkidtvThumbnail)
    thumbnail = dustkidImg.copy()

    font = ImageFont.truetype(freesans, 20)

    srankImg = Image.open(srank)
    arankImg = Image.open(arank)
    brankImg = Image.open(brank)
    crankImg = Image.open(crank)
    drankImg = Image.open(drank)
    appleImg = Image.open(apple)
    starImg = Image.open(star)
    scores = [drankImg, crankImg, brankImg, arankImg, srankImg]

    posLowRight2 = (THUMBNAIL_SIZE[0] - ICON_SIZE[0] - PAD, THUMBNAIL_SIZE[1] - ICON_SIZE[1] - PAD)
    posLowRight1 = (posLowRight2[0] - ICON_SIZE[0] - PAD, THUMBNAIL_SIZE[1] - ICON_SIZE[1] - PAD)
    posLowLeft1 = (PAD, THUMBNAIL_SIZE[1] - ICON_SIZE[1] - PAD)
    posLowLeft2 = (posLowLeft1[0] + PAD + ICON_SIZE[0], THUMBNAIL_SIZE[1] - ICON_SIZE[1] - PAD)

    infoText = '''    Replay ID: %i
    Timestamp: %s
    Username: %s
    Level name: %s
    Time: %.3f s
    Completion: %s
    Finesse: %s
    Est. Deaths: %i
    Real time: %.3f s

    Queue length: %i
    '''

    replayId = 0
    timestamp = ''
    username = ''
    levelname = ''
    time = 0
    completion = ''
    finesse = ''
    realTime = 0

    queueLength = 0

    tvIsActive = False
    chatbotIsActive = False

    replay_thread = None
    chatbot_thread = None

    def readConfig(self, configFile='config.json'):

        with open(configFile, 'r') as f:
            conf = json.load(f)

        self.debug = conf['debug']
        self.chatbot = conf['chatbot']  # twitch chatbot integration
        if self.chatbot:
            self.chatbot_config = conf['chatbot_config']
        self.queuePriority = {
            "PB_PRIORITY": conf["PB_PRIORITY"],
            "APPLES_PRIORITY": conf["APPLES_PRIORITY"],  # per apple hit :)
            "RANK_PRIORITY": conf["RANK_PRIORITY"],  # prioritize up to this rank
            "CONSITE_PRIORITY": conf["CONSITE_PRIORITY"]  # consite good
        }

        try:
            self.dfExePath = os.environ['DFEXE']
            self.dfPath = os.environ['DFPATH']
            self.dfDailyPath = os.environ['DFDAILYPATH']

        except KeyError:
            self.dfExePath = conf['dustmod']
            self.dfPath = conf['path']
            self.dfDailyPath = conf['user_path']

            os.environ['DFEXE'] = self.dfExePath
            os.environ['DFPATH'] = self.dfPath
            os.environ['DFDAILYPATH'] = self.dfDailyPath

    def run(self):
        self.tvIsActive = True
        self.replay_text.set('Starting Dustforce...')

        if self.debug:
            with open('dustkidtv.log', 'a', encoding='utf-8') as logfile:
                logfile.write('DustkidTV started at %s UTC\n' % (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())))

        if self.replay_thread is None:
            self.replay_thread = threading.Thread(target=self.run_thread, daemon=True)
            self.replay_thread.start()

    def stop(self):
        self.tvIsActive = False
        self.replay_text.set('Waiting for replay to end...')

        if self.debug:
            with open('dustkidtv.log', 'a', encoding='utf-8') as logfile:
                logfile.write('DustkidTV stopped at %s UTC\n' % (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())))

    def runRequests(self):
        self.chatbotIsActive = True

        if self.debug:
            with open('dustkidtv.log', 'a', encoding='utf-8') as logfile:
                logfile.write('Chatbot started at %s UTC\n' % (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())))

        if self.chatbot_thread is None:
            self.chatbot_thread = threading.Thread(target=self.run_chatbot, daemon=True)
            self.chatbot_thread.start()

    def stopRequests(self):
        self.chatbotIsActive = False

        self.handler.say('Replay requests are closed\n')

        self.reader.stop()
        self.handler.stop()

        self.reader.join()
        self.handler.join()

        if self.debug:
            with open('dustkidtv.log', 'a', encoding='utf-8') as logfile:
                logfile.write('Chatbot stopped at %s UTC\n' % (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime())))

    def run_chatbot(self):
        self.reader = TwitchReader(config_file=self.chatbot_config)
        self.handler = Chatbot()
        self.reader.handler = self.handler
        self.handler.start()
        self.reader.start()

    def run_thread(self):
        time.sleep(2)

        queue = ReplayQueue(self.debug, self.queuePriority)
        self.queueLength = queue.length

        while self.tvIsActive:

            # get next replay on the list
            if self.chatbotIsActive:

                # check chat requests
                foundValidRequest = False
                while (self.handler.replayRequestsCounter > 0):
                    # get next chat request
                    id = self.handler.replayRequests.pop(0)
                    self.handler.replayRequestsCounter -= 1
                    try:
                        rep = Replay(replayId = id)

                        # check if the request is a banned map
                        for map in BANNED_MAPS:
                            if rep.level == map:
                                raise BannedReplay

                        self.handler.setReplay(rep)
                        foundValidRequest = True
                        break
                    except InvalidReplay:
                        self.handler.say(f'Requested replay {id} is invalid, skipping\n')
                        continue
                    except BannedReplay:
                        self.handler.say(f'Requested replay {id} is banned, skipping\n')
                        continue

                # if no requests or invalid requests, continue with main queue
                if not foundValidRequest:
                    rep = queue.next()
                    self.handler.setReplay(rep)
            else:
                rep = queue.next()

            self.replayId = rep.replayId
            self.timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(rep.timestamp))
            self.username = rep.username
            self.levelname = rep.levelname
            self.time = rep.time / 1000.
            self.completion = rep.completion
            self.finesse = rep.finesse
            self.deaths = rep.deaths
            self.realTime = rep.realTime

            # update thumbnail
            if rep.thumbnail:
                img = Image.open(io.BytesIO(rep.thumbnail))
            else:
                img = self.dustkidImg.copy()
            rankCompletionImg = self.scores[rep.completionNum - 1]
            rankFinesseImg = self.scores[rep.finesseNum - 1]

            img.paste(rankCompletionImg, self.posLowRight1, rankCompletionImg)
            img.paste(rankFinesseImg, self.posLowRight2, rankFinesseImg)
            if rep.apple and rep.isPB:
                img.paste(self.starImg, self.posLowLeft1, self.starImg)
                img.paste(self.appleImg, self.posLowLeft2, self.appleImg)
            elif rep.isPB:
                img.paste(self.starImg, self.posLowLeft1, self.starImg)
            elif rep.apple:
                img.paste(self.appleImg, self.posLowLeft1, self.appleImg)

            draw = ImageDraw.Draw(img)
            text = '\n'.join(wrap(rep.levelname, MAX_TEXT_LEN))
            draw.multiline_text((PAD - 1, PAD), text, font=self.font, fill=BLACK)
            draw.multiline_text((PAD + 1, PAD), text, font=self.font, fill=BLACK)
            draw.multiline_text((PAD, PAD - 1), text, font=self.font, fill=BLACK)
            draw.multiline_text((PAD, PAD + 1), text, font=self.font, fill=BLACK)
            draw.multiline_text((PAD, PAD), text, font=self.font, fill=WHITE)

            self.thumbnail = img

            photoTk = ImageTk.PhotoImage(self.thumbnail)
            self.image_label.configure(image=photoTk)
            self.image_label.image = photoTk

            # update replay info
            self.replay_text.set(self.infoText % (
                self.replayId, self.timestamp, self.username, self.levelname, self.time, self.completion, self.finesse,
                self.deaths, self.realTime, self.queueLength))

            # show replay
            rep.openReplay(rep.replayPath)
            while not rep.skip.is_set() and rep.skip.wait(rep.realTime):
                continue

            # update queues
            queue.update(rep.replayId)
            self.queueLength = queue.length

        self.replay_text.set('Thread Stopped')
        self.replay_thread = None

    def __init__(self, master):
        self.readConfig()

        Frame.__init__(self, master)
        self.master = master

        self.master.title('Dustkid TV')
        self.master.resizable(False, False)
        self.pack(fill=BOTH, expand=1)

        left = Frame(self)
        left.grid(row=0, column=0, sticky=(N, E, S, W))

        photoTk = ImageTk.PhotoImage(self.thumbnail)
        self.image_label = Label(left, image=photoTk)
        self.image_label.image = photoTk
        self.image_label.pack(anchor=NW)

        self.replay_text = StringVar()
        self.replay_text.set('Press Start')
        self.message = Message(left, textvariable=self.replay_text, justify=LEFT, width=THUMBNAIL_SIZE[0])
        self.message.pack(anchor=NW)

        self.button = Button(left, text='Start', command=lambda: self.run())
        self.button.pack(anchor=NW)

        self.button = Button(left, text='Stop', command=lambda: self.stop())
        self.button.pack(anchor=NW)

        if self.chatbot:
            self.button = Button(left, text='Start requests', command=lambda: self.runRequests())
            self.button.pack(anchor=NW)

            self.button = Button(left, text='Stop requests', command=lambda: self.stopRequests())
            self.button.pack(anchor=NW)


def main():
    root = Tk()

    window = Window(root)

    root.mainloop()
