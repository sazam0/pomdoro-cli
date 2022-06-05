# %%
# import
import json
from pathlib import Path
from decouple import config as config_env
import pandas as pd
import time
from datetime import datetime, timedelta
import numpy as np
from matplotlib import pyplot as plt
from pandas.tseries.offsets import DateOffset
import sys

# from sys import exit

# %%
def month(deck, past):
    # month
    deck_past = deck[
        (deck["year"] == past["year"]) & (deck["month_num"] == past["month_num"])
    ]
    tmpGrp = deck_past.groupby("date")
    return [deck_past, tmpGrp]

# %%
def months(deck, past):
    # month
    deck_past = deck[deck["year"] == past["year"]]
    tmpGrp = deck_past.groupby("month")
    return [deck_past, tmpGrp]

# %%
def weeks(deck, past):
    # week
    deck_past = deck[(deck["year"] == past["year"]) & (deck["week"] == past["week"])]
    tmpGrp = deck_past.groupby("day")
    return [deck_past, tmpGrp]

# %%
# init
def init(flag, df, datetimeStamp):
    x = datetime.now()
    deck = df[(df["task"] == True) & (df["type"] == "pomodoro")]

    # flag='7d'
    dateFlag = flag[-1]
    datebuffer = int(flag[:-1])
    # default
    pastDate={
        "m":x,
        "M":x
    }
    # pastDate={
    #     "m":datetime.strptime("01-{month}-{year}"
    #                           .format(month=datebuffer,year=x.year),"%d-%m-%Y"),
    #     "M":datetime.strptime("01-01-{year}"
    #         .format(year=(x-DateOffset(years=datebuffer)).strftime("%Y")),"%d-%m-%Y"),
    # }
    if(dateFlag == 'm'):
        pastDate[dateFlag]=datetime.strptime("01-{month}-{year}"
                    .format(month=datebuffer,year=x.year),"%d-%m-%Y")
    if(dateFlag == 'M'):
        pastDate[dateFlag]=datetime.strptime("01-01-{year}"
            .format(year=(x-DateOffset(years=datebuffer)).strftime("%Y")),"%d-%m-%Y")

    pastDate_dict = {
        "w": {
            i: (x - DateOffset(weeks=datebuffer)).strftime(j)
            for i, j in datetimeStamp.items()
        },
        # "d": {
        #     i: (x - DateOffset(days=datebuffer)).strftime(j)
        #     for i, j in datetimeStamp.items()
        # },
        "m": {
            # i: (x - DateOffset(months=datebuffer)).strftime(j)
            # for i, j in datetimeStamp.items()
            i:pastDate['m'].strftime(j) for i,j in datetimeStamp.items()
        },
        "M":{
            i:pastDate['M'].strftime(j) for i,j in datetimeStamp.items()
        },
    }

    past = pastDate_dict[dateFlag]
    past["year"] = int(past["year"])
    past["week"] = int(past["week"])
    past["month_num"] = int(past["month_num"])
    past["date"] = int(past["date"])

    # selectedDf = {"w": weeks, "d": days, "m": month, "M": months}
    selectedDf = {"w": weeks, "m": month, "M": months}
    return [past, selectedDf[dateFlag](deck, past)]

# %%
def statusData(flag, df, datetimeStamp):
    # flag='0M'
    # from pomodoro import rwData
    # with open('constants.json') as f:
    #     constants=json.load(f)
    # df=rwData("",'r',constants['fileName']['pomodoro'])
    # datetimeStamp=constants['datetimeStamp']

    past, df = init(flag, df, datetimeStamp)
    # past
    deck_past, tmpGrp = df
    # tmpGrp
    # deck_past
    if deck_past.size == 0:
        historyDate = "{}/{}/{}, week: {}".format(
            past["date"], past["month_num"], past["year"], past["week"]
        )
        print("{}: Job history not found".format(historyDate))
        # exit()
        sys.exit()
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
    max_consecutive.rename(columns={"amax": "max_consecutive"}, inplace=True)

    total = tmpGrp["worktime"].agg([np.sum]) / 60
    total.rename(columns={"sum": "total_worktime"}, inplace=True)
    # total
    genPlot(total,flag[-1],past)
    # summury

    # if flag[-1] != "d":
    summury = total["total_worktime"].agg([np.min, np.max, np.sum])
    summury.rename({"amin": "min", "amax": "max", "sum": "avg"}, inplace=True)
    if flag[-1] == "w":
        summury["avg"] = summury["avg"] / 7
    elif flag[-1] == "M":
        summury["avg"] = summury["avg"] / 12
    # month >> wrong value: do not consider 28, 30, 31 month days
    elif flag[-1] == "m":
        summury["avg"] = summury["avg"] / 30
    else:
        pass
        # summury
    # else:
    #     summury = pd.DataFrame()
    # total worktime day/week/month
    # total

    return [grpTotal, total_wrkTime, total, summury, max_consecutive]


#%%
def genPlot(df,time_flag,past):
    # time_flag='M'
    title={
        "w":"date: {date}, week: {week}".format(date=past['date_'],week=past['week']),
        "m":"date: {date}, month: {month}".format(date=past['date_'],month=past['month']),
        "M":"date: {date}, year: {year}".format(date=past['date_'],year=past['year']),
        "y":"date: {date}, year: {year}".format(date=past['date_'],year=past['year']),
    }
    sorter_w = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    sorter_M = ['','Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug',
        'Sep', 'Oct', 'Nov', 'Dec']
    # sorter_w_Index = dict(zip(sorter_w,range(len(sorter_w))))
    # sorter_M
    # df=total
    # df
    df['id']=df.index
    if(time_flag == 'w'):
        df['id']=df['id'].map(dict(zip(sorter_w,range(len(sorter_w)))))
    elif(time_flag == 'm'):
        pass
    elif(time_flag == 'M'):
        df['id']=df['id'].map(dict(zip(sorter_M,range(len(sorter_M)))))
    else:
        pass

    df.sort_values('id',inplace=True)
    df=df.reset_index()
    df.set_index('id',inplace=True)
    # df
    if(time_flag == 'm'):
        df.drop(columns=['date'],inplace=True)
    # elif(time_flag == 'M'):
    #     df.drop(columns=['month'],inplace=True)
    else:
        pass
    # fig=plt.figure(facecolor='#94F008')
    fig, ax = plt.subplots(figsize=(8,4), facecolor='#94F008')
    # ax=fig.add_axes([0,0,1,1])
    # ax.bar(df.id,df.sum)
    if(time_flag == 'w'):
        df.plot(kind='bar',ax=ax)
        ax.set_xticklabels(df.day)
    elif(time_flag == 'M'):
        df.plot(kind='bar',ax=ax)
        ax.set_xticklabels(df.month)
    else: # 'm'
        # df.plot(style='o-',kind='line',ax=ax)
        df.plot(kind='bar')
    plt.title(title[time_flag])
    plt.grid()
    plt.ylabel("hours")
    plt.xlabel("days")
    plt.xticks(rotation=0, horizontalalignment="center")
    plt.savefig("/tmp/pomodoro.png", bbox_inches='tight')
    plt.close()

    return 0

#%%
