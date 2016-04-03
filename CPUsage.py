#!/usr/bin/env python
import subprocess
import matplotlib.pyplot as plt
from matplotlib.dates import YearLocator, MonthLocator, DayLocator, WeekdayLocator, DateFormatter, MONDAY
import datetime
from dateutil.relativedelta import relativedelta
import numpy as np
import pylab
import argparse


######################
###### Parser ########
######################
parser = argparse.ArgumentParser()
parser.add_argument("-p", help="Show cumulative usage in percent",
                    action="store_true", default=0)
parser.add_argument("-b", help="Use bar plot",
                    action="store_true", default=0)
parser.add_argument("-B", help="Use bar-marker plot",
                    action="store_true", default=0)
parser.add_argument("-g", help="Show grid",
                    action="store_true", default=0)
parser.add_argument("-d", help="Number of past days, starting from today, from which to start gathering data (Default: 90)",
                    type=int, default=90)
parser.add_argument("-f", help="Filename of output figure (Default: CPUsage.eps)",
                    type=str, default='CPUsage.eps')
args = parser.parse_args()



############################
###### Cluster List ########
############################
# <cluster name>: <Allocated core hours/month>
clusterList = {'abisko': 300000, 'triolith': 100000}


#########################
###### Functions ########
#########################
def getFirstName(string):
    if type(string) == str:
        splitString = string.split(" ")
        return splitString[0]

def getCumulative(usage,dtF,lastDate,dtL,nDays):
    tmpUsage = np.array((nDays+dtF.days+dtL.days)*[0])
    tmpUsage[dtL.days:dtL.days+nDays] = usage

    newDates = []
    cumUsage = np.array((nDays+dtL.days)*[0])
    for i in range(nDays+dtL.days):
        currentDate = lastDate-i*dt
        minusOneMonthDate = currentDate-relativedelta(months=+1)

        daysInBetween = (currentDate-minusOneMonthDate).days
        cumUsage[i] = sum(tmpUsage[i:i+daysInBetween])
        newDates.append(currentDate)
    return newDates, cumUsage


###########################
###### Gather data ########
###########################
months = MonthLocator()
days = DayLocator()
yearsFmt = DateFormatter("%d %b '%y")

today = datetime.date.today()
dt = datetime.timedelta(days=1)
nDays = args.d

srepCommand = 'sreport -np cluster AccountUtilizationByUser Account=snic2015-10-21 format=Cluster,Accounts,Login,Proper,Used'

dates = []
usage = {}
cluster = ''
nCols = []
for i in range(nDays):
    currentDate = today-i*dt

    out, err = subprocess.Popen(srepCommand.split(' ')+['start='+str(currentDate)]+['end='+str(currentDate+dt)], stdout=subprocess.PIPE).communicate()
    if out:
        outArray = out.split('|')
        for index, element in enumerate(outArray):
            if "\n" in element and not nCols:
                nCols = index
        if not cluster:
            cluster = outArray[0]
        for j in range(len(outArray)/nCols):
            try:
                usage[outArray[3+nCols*j]][i] = int(outArray[4+nCols*j])
            except KeyError:
                usage[outArray[3+nCols*j]] = np.array(nDays*[0])
                usage[outArray[3+nCols*j]][i] = int(outArray[4+nCols*j])

    dates.append(currentDate)

firstDate = dates[-1]-relativedelta(months=+1)
lastDate = dates[0]+relativedelta(months=+1)
dtF = dates[-1]-firstDate
dtL = lastDate-dates[0]

cumUsage = {}
for user in usage:
    newDates, cumUsage[user] = getCumulative(usage[user],dtF,lastDate,dtL,nDays)

if args.p:
    try:
        factor = 100.0/clusterList[cluster]
        yLabel = 'Rolling Cumulative Usage (%)'
    except KeyError:
        print 'Unrecognized resource named ' + cluster + ', disregarding the -p flag'
        factor = 1
        yLabel = 'Rolling Cumulative Usage (ch)'
else:
    factor = 1
    yLabel = 'Rolling Cumulative Usage (ch)'


######################
##### Figure 1 #######
######################
fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True,figsize=(16, 9))


users = usage.keys()
colors = {}
barColor = [0.4,0.4,0.4]
for user in users:
    if not user:
        colors[user] = barColor
    else:
        colors[user] = next(ax1._get_lines.color_cycle)

if args.b:
    for i in range(nDays):
        currentUsage = [usage[user][i] for user in users]
        indices = np.argsort(currentUsage)[::-1]
        if users[indices[0]]:
            indices[0], indices[1] = indices[1], indices[0]
        for idx in indices:
            if users[idx]:
                ax1.bar(dates[i],currentUsage[idx]/60.0,color=colors[users[idx]],label=getFirstName(users[idx]) if not i else '',align='center')
            else:
                ax1.bar(dates[i],currentUsage[idx]/60.0,color=barColor,label='Total' if not i else '',align='center')
else:
    for user in usage:
        if user:
            if args.B:
                lalala = usage[user]>np.array(len(usage[user])*[0])
                indx, = np.where(lalala)
                ax1.plot_date([dates[i] for i in indx],usage[user][lalala]/60.0,label=getFirstName(user),fmt='o'+colors[user])
            else:
                ax1.plot_date(dates,usage[user]/60.0,'-'+colors[user],label=getFirstName(user))

        else:
            if args.B:
                ax1.bar(dates,usage[user]/60.0,facecolor=barColor,alpha=0.5,label='Total',align='center')
            else:
                ax1.plot_date(dates,usage[user]/60.0,'-',color=colors[user],label='Total',linewidth=2)


##### Subplot 2 ######
for user in cumUsage:
    if user:
        ax2.plot_date(newDates[dtL.days:],factor*cumUsage[user][dtL.days:]/60.0,'-'+colors[user],label=getFirstName(user))
        ax2.plot_date(newDates[:dtL.days+1],factor*cumUsage[user][:dtL.days+1]/60.0,'--'+colors[user])
    else:
        ax2.plot_date(newDates[dtL.days:],factor*cumUsage[user][dtL.days:]/60.0,'-',color=colors[user],label='Total',linewidth=2)
        ax2.plot_date(newDates[:dtL.days+1],factor*cumUsage[user][:dtL.days+1]/60.0,'--',color=colors[user],linewidth=2)


##### axies, labels etc. ######
plt.minorticks_on()
if args.g:
    ax1.grid()
    ax2.grid()
    ax1.set_axisbelow(True)
    ax2.set_axisbelow(True)
ax1.xaxis.set_major_locator(months)
ax1.xaxis.set_major_formatter(yearsFmt)
ax1.xaxis.set_minor_locator(days)

ax1.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,ncol=len(usage), mode="expand", borderaxespad=0.,numpoints = 1)
ax1.set_ylabel('Daily Usage (ch)')
ax2.set_ylabel(yLabel)


##### Save figure ######
pylab.savefig(args.f, bbox_inches='tight')
#plt.show()
