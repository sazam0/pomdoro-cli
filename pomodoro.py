#!/usr/bin/env python3

# %%
import time
import sys
import argparse, argcomplete
from decouple import config
from collections import namedtuple
import subprocess
import tqdm
import pandas as pd
import datetime
from pathlib import Path
from pydub import AudioSegment
from pydub.playback import play
import io
import contextlib

# from playsound import playsound

# %%
def readPomodoroIndex(pomodoro):
    txt = "choose one of the pomodoro from index =>\n"
    txt += "{:<8s}{:<10s}{:11s}{:<11s}{:<11s}{:<12s}\n".format(
        "index", "name", "pomodoro", "s_break", "l_break", "interval"
    )
    txt += "".join(["-" for i in range(59)]) + "\n"
    for _, j in pomodoro.items():
        txt += "{:<7s} {:<9s}{:^11d}{:^11d}{:^11d}{:^11d}\n".format(
            # i[0],
            j.index,
            j.name,
            j.pomodoro,
            j.shortbreak,
            j.longbreak,
            j.interval,
        )

    print(txt)
    return ""


# %%
def writeData(df, mode, write_file):
    pathDir = "/".join([str(Path.home()), "Nextcloud", ".pomodoro"])
    fileName = {"pomodoro": "pomodoro.csv"}
    with open("{a}/{b}".format(a=pathDir, b=fileName[write_file]), mode) as f:
        df.to_csv(f, sep=",", index=False, header=False, index_label="index")
    # df.to_csv("{a}/{b}".format(a=pathDir, b=fileName[write_file]), mode=mode,
    #         sep=",",index=False,header=False,index_label="index")
    return 0


# %%
def genData(dateTime, data):
    x = dateTime
    timeParams = {
        "year": x.strftime("%Y"),
        "month": x.strftime("%b"),
        "month_num": x.strftime("%m"),
        "date": x.strftime("%d"),
        "week": x.strftime("%W"),
        "day": x.strftime("%a"),
        "hour": x.strftime("%H"),
        "minute": x.strftime("%M"),
        "day_night": x.strftime("%p"),
    }
    data = {"index": x.strftime("%Y%m%d%W%H%M%S"), **timeParams, **data}
    df = pd.DataFrame([data])

    writeData(df, "a", "pomodoro")
    return 0


def playSound(flag):
    try:
        if flag == "p":
            play(AudioSegment.from_wav("sound/after_pomodoro.wav"))
            # playsound("after_pomodoro.wav")
        elif flag == "l":
            play(AudioSegment.from_wav("sound/after_long_break.wav"))
            # playsound("after_long_break.wav")
        elif flag == "s":
            play(AudioSegment.from_wav("sound/after_short_break.wav"))
            # playSound("after_short_break.wav")
        else:
            print("unknown flag in playSound")
            exit()
    except KeyboardInterrupt:
        exit()
    if sys.platform in ("linux", "osx"):
        subprocess.call("clear", shell=True)
    elif sys.platform in ("nt", "dos", "ce"):
        subprocess.call("cls", shell=True)
    else:
        pass
    # sys.stdout.flush()

    return 0


# %%
def currentStatus(
    progress, desc, minuteBar, currentBar, interval, pomodoroFlag, metaData
):
    # pomodoroFlag = desc == "pomodoro"
    x = datetime.datetime.now()
    data = {
        "type": desc,
        "pomodoro": progress,
        "consecutiveInterval": interval,
        "completed": False,
        "worktime": 0,
        **metaData,
    }

    currentBar.total = progress
    currentBar.desc = desc
    minuteFactor = 1
    tic = time.perf_counter()

    currentBar.refresh()
    for _ in range(currentBar.total):
        for _ in range(int(minuteBar.total / minuteFactor)):
            try:
                time.sleep(minuteFactor)
            except KeyboardInterrupt:
                toc = time.perf_counter()
                if pomodoroFlag:
                    interruptedInterval = round(
                        (toc - tic) / 60, 4
                    )  # convert to minute
                    data["worktime"] = (
                        interruptedInterval if interruptedInterval > 1.0 else 0.0
                    )
                    genData(x, data)
                # intervalBar.close()
                currentBar.close()
                minuteBar.close()
                exit()
            minuteBar.update(minuteFactor)
        currentBar.update(1)
        minuteBar.reset()
    currentBar.reset()

    data["completed"] = True
    data["worktime"] = progress
    genData(x, data)
    return 0


# %%
def countdown(chosenOne, metaData):
    pomodoro = chosenOne.pomodoro
    shortBreak = chosenOne.shortbreak
    longBreak = chosenOne.longbreak
    interval = chosenOne.interval

    intervalCounter = 1
    # intervalCounter

    intervalBar = tqdm.tqdm(total=interval, desc="interval", position=0)
    currentBar = tqdm.tqdm(position=1)
    minuteBar = tqdm.tqdm(total=60, desc="minute", position=2)
    # minuteBar = ""

    while True:
        # sys.stdout.flush()
        for i in range(interval):
            # time.sleep(2)
            currentStatus(
                pomodoro,
                "pomodoro",
                minuteBar,
                currentBar,
                intervalCounter,
                True,
                metaData,
            )
            intervalBar.update(1)
            intervalCounter += 1
            playSound("p")
            intervalBar.refresh()
            if i + 1 == interval:
                currentStatus(
                    longBreak, "long break", minuteBar, currentBar, -1, False, metaData
                )
                playSound("l")
                intervalBar.refresh()
            else:
                currentStatus(
                    shortBreak, "short break", minuteBar, currentBar, 0, False, metaData
                )
                playSound("s")
                intervalBar.refresh()
        intervalBar.reset()

    return 0


# %%
def parseArgs(pomodoro):
    help_txt = programStructure()

    parser = argparse.ArgumentParser()
    parser.add_argument("--task", "-t", action="store_true", default=False)
    parser.add_argument(
        "--comment",
        "-c",
        type=str,
        default="",
        choices=help_txt["commentList"],
        metavar="str",
        help=help_txt["commentList_h"],
    )
    parser.add_argument(
        "--pomodoro",
        "-p",
        type=str,
        default="",
        metavar="str",
        help=help_txt["pomodoro_h"] + readPomodoroIndex(pomodoro),
    )
    argcomplete.autocomplete(parser)
    return parser.parse_args()


# %%
def confirmPomodoro(inputs, pomodoro, pomodoroInputIndex, commentList):
    # TODO implement proper checking protocol
    txt = ""
    chosenOne = ""
    pomodoros = inputs.pomodoro
    if inputs.pomodoro in pomodoroInputIndex.keys():
        chosenOne = pomodoroInputIndex[pomodoros]
        txt += "starting pomodoro '{input}'".format(input=chosenOne)
    else:
        print(
            "-p flag option '{input}' not know, check: 'pomodoro.py -h'".format(
                input=pomodoros
            )
        )
        exit()

    comments = inputs.comment
    if comments in commentList or comments[0] == ":":
        txt += " => '{cmnt}'".format(cmnt=comments)
    else:
        print(
            "-c flag option '{input}' not know, check: 'pomodoro.py -h'".format(
                input=comments
            )
        )
        exit()
    print(txt)
    return pomodoro[chosenOne]


# %%
def programStructure():
    struc = {
        "pomodoro": list(),
        "pomodoro_h": "",
        "commentList": ["exercise", "morning", "cook", "food", "clean", "media", ""],
        "commentList_h": "",
    }

    pomodoroStructure = namedtuple(
        "Pomodoro", ["name", "index", "pomodoro", "shortbreak", "longbreak", "interval"]
    )

    pomodoroIndex = {
        1: "common",
        2: "moderate",
        3: "longer",
        4: "marathon",
        5: "exercise",
    }

    pomodoro = {
        # pomodoroIndex[1]: pomodoroStructure(pomodoroIndex[1], 3, 2, 4, 2),
        pomodoroIndex[1]: pomodoroStructure(pomodoroIndex[1], "c", 25, 5, 30, 4),
        pomodoroIndex[2]: pomodoroStructure(pomodoroIndex[2], "m", 45, 15, 30, 4),
        pomodoroIndex[3]: pomodoroStructure(pomodoroIndex[3], "l", 55, 20, 30, 3),
        pomodoroIndex[4]: pomodoroStructure(pomodoroIndex[4], "M", 90, 30, 45, 3),
        pomodoroIndex[5]: pomodoroStructure(pomodoroIndex[5], "e", 2, 1, 5, 5),
    }

    pomodoroInputIndex = {j.index: j.name for _, j in pomodoro.items()}

    tmp = [
        "{arg1}: {arg2}".format(arg1=j.index, arg2=j.name) for _, j in pomodoro.items()
    ]
    struc["pomodoro_h"] = ", ".join(tmp)
    struc["pomodoro_c"] = [j.index for _, j in pomodoro.items()]

    struc["pomodoro"].extend([pomodoroIndex, pomodoroInputIndex, pomodoro])

    struc["commentList_h"] = ", ".join(struc["commentList"]) + '""'

    return struc


# %%
def main():

    programStr = programStructure()
    pomodoroIndex, pomodoroInputIndex, pomodoro = programStr["pomodoro"]

    inputs = parseArgs(pomodoro)
    chosenOne = confirmPomodoro(
        inputs, pomodoro, pomodoroInputIndex, programStr["commentList"]
    )
    metaData = {"task": inputs.task, "comment": inputs.comment}
    # print(inputs.comment)
    countdown(chosenOne, metaData)
    # print(chosenOne.shortbreak)
    # readPomodoroIndex(pomodoroIndex)

    return 0


# %%
if __name__ == "__main__":
    # print("hello")
    main()
