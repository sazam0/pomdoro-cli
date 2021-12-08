# import
import json
from pathlib import Path
from decouple import config as config_env
import pandas as pd
import time
from datetime import datetime, timedelta
import numpy as np
from pandas.tseries.offsets import DateOffset

# basic functions
def days(deck, past):
    # today/yesterday
    deck_past = deck[
        (deck["year"] == past["year"])
        & (deck["month_num"] == past["month_num"])
        & (deck["date"] == past["date"])
    ]
    tmpGrp = deck_past
    return [deck_past, tmpGrp]


def months(deck, past):
    # month
    deck_past = deck[
        (deck["year"] == past["year"]) & (deck["month_num"] == past["month_num"])
    ]
    tmpGrp = deck_past.groupby("date")
    return [deck_past, tmpGrp]


def weeks(deck, past):
    # week
    deck_past = deck[(deck["year"] == past["year"]) & (deck["week"] == past["week"])]
    tmpGrp = deck_past.groupby("day")
    return [deck_past, tmpGrp]

# init
def init(flag, df, datetimeStamp):
    # constants=dict()
    # with open('constants.json') as f:
    #     constants=json.load(f)

    x = datetime.now()
    # today={i:diff.strftime(j) for i,j in constants['datetimeStamp'].items()}

    deck = df[(df["task"] == True) & (df["type"] == "pomodoro")]

    # flag='7d'
    dateFlag = flag[-1]
    datebuffer = int(flag[:-1])
    pastDate = {
        "w": {
            i: (x - DateOffset(weeks=datebuffer)).strftime(j)
            for i, j in datetimeStamp.items()
        },
        "d": {
            i: (x - DateOffset(days=datebuffer)).strftime(j)
            for i, j in datetimeStamp.items()
        },
        "m": {
            i: (x - DateOffset(months=datebuffer)).strftime(j)
            for i, j in datetimeStamp.items()
        },
    }
    past = pastDate[dateFlag]
    past["year"] = int(past["year"])
    past["week"] = int(past["week"])
    past["month_num"] = int(past["month_num"])
    past["date"] = int(past["date"])

    selectedDf = {"w": weeks, "d": days, "m": months}

    return [past, selectedDf[dateFlag](deck, past)]


def statusData(flag, df, datetimeStamp):
    # flag='1w'
    # from pomodoro import rwData
    # with open('constants.json') as f:
    #     constants=json.load(f)
    # df=rwData("",'r',constants['fileName']['pomodoro'])
    # datetimeStamp=constants['datetimeStamp']
    past, df = init(flag, df, datetimeStamp)
    # past
    deck_past, tmpGrp = df
    # deck_past
    if deck_past.size == 0:
        historyDate = "{}/{}/{}, week: {}".format(
            past["date"], past["month_num"], past["year"], past["week"]
        )
        print("{}: Job history not found".format(historyDate))
        exit()
    # common
    # spent time on pomodoro categories
    grpTotal = deck_past.groupby("name")["worktime"].agg([np.sum]) / 60
    grpTotal.rename(columns={"sum": "pomodoro_worktime"}, inplace=True)
    # grpTotal
    # spent time on works
    total_wrkTime = deck_past.groupby("comment")["worktime"].agg([np.sum]) / 60
    total_wrkTime.rename(columns={"sum": "job_worktime"}, inplace=True)
    # total_wrkTime
    # max continuous worktime day/week/month
    max_consecutive = tmpGrp["maxContinue"].agg([np.max]) / 60
    total = tmpGrp["worktime"].agg([np.sum]) / 60
    # total
    # summury

    if flag[-1] != "d":
        max_consecutive.rename(columns={"amax": "max_consecutive"}, inplace=True)
        total.rename(columns={"sum": "total_worktime"}, inplace=True)
        summury = total["total_worktime"].agg([np.min, np.max, np.sum])
        summury.rename({"amin": "min", "amax": "max", "sum": "avg"}, inplace=True)
        if flag[-1] == "w":
            summury["avg"] = summury["avg"] / 7
        else:  # month >> wrong value: do not consider 28, 30, 31 month days
            summury["avg"] = summury["avg"] / 30

        # summury
    else:
        max_consecutive.rename({"amax": "max_consecutive"}, inplace=True)
        total.rename({"sum": "total_worktime"}, inplace=True)
        summury = pd.DataFrame()
    # total worktime day/week/month
    # total

    return [grpTotal, total_wrkTime, total, summury, max_consecutive]


# %%
