#!/usr/bin/env python
import subprocess
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.dates import YearLocator, MonthLocator, DayLocator, WeekdayLocator, DateFormatter, MONDAY
import datetime
from datetime import datetime as datet
from dateutil.relativedelta import relativedelta
import numpy as np
import pylab
import argparse
import os


######################
###### Parser ########
######################
parser = argparse.ArgumentParser()
parser.add_argument("-d", help="Number of past days, starting from today, from which to start gathering data (Default: 90)",
                    type=int, default=90)
parser.add_argument("-D", help="Plot only number of days defined by '-d'",
                    action="store_true", default=0)
parser.add_argument("-f", help="Name of datafile/figure (Default: CPUsage.txt/eps)",
                    type=str, default='CPUsage')
parser.add_argument("-g", help="Show grid",
                    action="store_true", default=0)
parser.add_argument("-p", help="Show cumulative usage in percent",
                    action="store_true", default=0)
parser.add_argument("-s", help="Use ssh. Write full command (ssh -flags xxx@yyy.zzz)",
                    type=str, default='')
args = parser.parse_args()



############################
###### Cluster List ########
############################
# <cluster name>: <Allocated core hours/month>
clusterList = {'abisko': 300000, 'triolith': 100000}



##################################
###### Set up dateobjects ########
##################################
months = MonthLocator()
days = DayLocator()

today = datetime.date.today()
oneDay = datetime.timedelta(days=1)
oneMonth = relativedelta(months=+1)

yearsFmt = DateFormatter("%d %b '%y")

dateFormat = "%Y-%m-%d"

#########################
###### THE Class ########
#########################
class CPUsageData(object):

    def __init__(self):
        self.clusterName = ''

        self.dates = []
        self.usage = {}
        self.users = []
        self.nDates = 0

        self.cumUsage = {}
        self.expandedDates = []

    def __repr__(self):
        string = 'Cluster:\t' + self.clusterName + '\n'
        string += 'Dates:'
        for element in self.dates:
            string += '\t' + str(element)
        for user in self.usage:
            string += '\n' + user + ':'
            for value in self.usage[user]:
                string += '\t' + str(value)
        return string

    def printData(self):
        print self.clusterName
        print self.dates
        print self.usage
        print self.users

    def importData(self,filename,dateFormat):
        if os.path.isfile(filename):
            lines = open(filename, 'r').read().splitlines()
            tmpData = [line.split('\t') for line in lines]
            for i in range(len(tmpData)):
                if tmpData[i][0] == 'Cluster':
                    self.clusterName = tmpData[i][1]
                elif tmpData[i][0] == 'Date' or tmpData[i][0] == 'Dates':
                    self.dates = [datet.strptime(ts, dateFormat).date() for ts in tmpData[i][1:]]
                    self.nDates = len(self.dates)
                else:
                    self.usage[tmpData[i][0]] = map(int,tmpData[i][1:])
                    self.users.append(tmpData[i][0])

    def exportData(self,filename):
        f = open(filename, 'w')
        f.write('Cluster\t' + self.clusterName + '\n')
        f.write('Dates')
        for element in self.dates:
            f.write('\t' + str(element))
        for user in self.usage:
            f.write('\n' + user)
            for value in self.usage[user]:
                f.write('\t' + str(value))
        f.close()

    def addUsage(self,cluster,newUsage,newDate):
        if not self.clusterName:
            self.clusterName = cluster
        if cluster == self.clusterName or not cluster:
            self.dates.append(newDate)
            self.nDates += 1
            for user in self.users:
                if user not in newUsage:
                    self.usage[user].append(0)
            for user in newUsage:
                try:
                    self.usage[user].append(newUsage[user])
                except KeyError:
                    self.usage[user] = self.nDates*[0]
                    self.usage[user][self.nDates-1] = newUsage[user]
                    self.users.append(user)
        else:
            print 'Cluster != clusterName.'

    def overwriteUsage(self,cluster,newUsage,newDate):
        if not self.clusterName:
            self.clusterName = cluster
        if cluster == self.clusterName or not cluster:
            if self.dateExists(newDate):
                index = self.getDateIndex(newDate)
                for user in newUsage:
                    try:
                        self.usage[user][index] = newUsage[user]
                    except KeyError:
                        self.usage[user] = self.nDates*[0]
                        self.usage[user][index] = newUsage[user]
                        self.users.append(user)
            else:
                print 'Error: Can not overwrite a nonexisting date.'
        else:
            print 'Cluster != clusterName.'

    def getLatestDate(self):
        if not self.isSorted():
            self.sort()
        return self.dates[-1]

    def isLatestDate(self,testDate):
        return self.getLatestDate() == testDate

    def dateExists(self,testDate):
        return testDate in self.dates

    def getDateIndex(self,testDate):
        return self.dates.index(testDate)

    def isSorted(self):
        notSorted = 0
        for i in range(self.nDates-1):
            notSorted += not self.dates[i] < self.dates[i+1]
        return not notSorted

    def sort(self):
        if not self.isSorted():
            sortindex = np.argsort(np.array(self.dates))
            for key in self.usage:
                self.usage[key] = [self.usage[key][index] for index in sortindex]
            self.dates = [self.dates[index] for index in sortindex]

    def isConsecutive(self):
        for i in range(self.nDates-1):
            if self.dates[i]+oneDay != self.dates[i+1]:
                return False
        return True

    def dataCheck(self):
        somethingWrong = False
        if self.nDates != len(self.dates):
            somethingWrong = True
            print 'nDates != number of dates.'
        for user in self.users:
            if self.nDates != len(self.usage[user]):
                somethingWrong = True
                print "nDates != number of data points for user '" + user + "'."
        for user in self.users:
            if user not in self.usage:
                somethingWrong = True
                print "user '" + user + "' missing from usage."
        for user in self.usage:
            if user not in self.users:
                somethingWrong = True
                print "user '" + user + "' missing from users."
        return somethingWrong

    def calcCumulativeUsage(self):
        self.sort()
        if self.isConsecutive():
            startDate = self.dates[0]
            endDate = self.dates[-1]
            expandedStartDate = startDate - oneMonth
            expandedEndDate = endDate + oneMonth
            startDays = startDate - expandedStartDate
            endDays = expandedEndDate - endDate

            self.expandedDates = [startDate + i*oneDay for i in range(self.nDates+endDays.days)]
            for user in self.users:
                tmpUsage = np.array((startDays.days+self.nDates+endDays.days)*[0])
                tmpUsage[startDays.days:startDays.days+self.nDates] = self.usage[user]

                self.cumUsage[user] = np.array((self.nDates+endDays.days)*[0])
                for i in range(self.nDates+endDays.days):
                    currentDate = startDate + i*oneDay
                    minusOneMonthDate = currentDate - oneMonth
                    daysInBetween = (currentDate-minusOneMonthDate).days

                    self.cumUsage[user][i] = sum(tmpUsage[startDays.days + i - daysInBetween:startDays.days + i+1])

    def plot(self,filename):
        if self.usage:
            if not self.cumUsage:
                self.calcCumulativeUsage()

            fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True,figsize=(16, 9))

            startIteration = 0
            if args.D:
                startIteration = max(self.nDates-args.d,0)

            if args.p:
                try:
                    factor = 100.0/clusterList[self.clusterName]
                    yLabel = 'Rolling Cumulative Usage (%)'
                except KeyError:
                    print 'Unrecognized resource named ' + self.clusterName + ', disregarding the -p flag'
                    factor = 1
                    yLabel = 'Rolling Cumulative Usage (ch)'
            else:
                factor = 1
                yLabel = 'Rolling Cumulative Usage (ch)'

            colors = {}
            barColor = [0.4,0.4,0.4]
            for user in self.users:
                if user == 'Total':
                    colors[user] = barColor
                else:
                    colors[user] = next(ax1._get_lines.color_cycle)

            ##### Subplot 1 ######
            for i in range(startIteration,self.nDates):
                currentUsage = [self.usage[user][i] for user in self.users]
                indices = np.argsort(currentUsage)[::-1]
                if self.users[indices[0]] != 'Total':
                    indices[0], indices[1] = indices[1], indices[0]
                for idx in indices:
                    ax1.bar(self.dates[i],currentUsage[idx]/60.0,color=colors[self.users[idx]],label=getFirstName(self.users[idx]) if i==startIteration else '',align='center')

            ##### Subplot 2 ######
            for user in self.users:
                if user != 'Total':
                    ax2.plot_date(self.expandedDates[startIteration:self.nDates],factor*self.cumUsage[user][startIteration:self.nDates]/60.0,'-'+colors[user],label=getFirstName(user))
                    ax2.plot_date(self.expandedDates[self.nDates-1:],factor*self.cumUsage[user][self.nDates-1:]/60.0,'--'+colors[user])
                else:
                    ax2.plot_date(self.expandedDates[startIteration:self.nDates],factor*self.cumUsage[user][startIteration:self.nDates]/60.0,'-',color=colors[user],label=getFirstName(user),linewidth=2)
                    ax2.plot_date(self.expandedDates[self.nDates-1:],factor*self.cumUsage[user][self.nDates-1:]/60.0,'--',color=colors[user],linewidth=2)

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

            ax1.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc=3,ncol=len(self.users), mode="expand", borderaxespad=0.,numpoints = 1)
            ax1.set_ylabel('Daily Usage (ch)')
            ax2.set_ylabel(yLabel)

            ##### Save figure ######
            pylab.savefig(filename, bbox_inches='tight', dpi=300)
            #plt.show()


#########################
###### Functions ########
#########################
def parseOutput(out):
    nCols = 0
    usage = {}
    cluster = ''
    if out:
        outArray = out.split('|')
        for index, element in enumerate(outArray):
            if "\n" in element and not nCols:
                nCols = index
        cluster = outArray[0]
        for j in range(len(outArray)/nCols):
            if outArray[3+nCols*j] == '':
                outArray[3+nCols*j] = 'Total'
            usage[outArray[3+nCols*j]] = int(outArray[4+nCols*j])
    return cluster, usage

def getFirstName(string):
    if type(string) == str:
        splitString = string.split(" ")
        return splitString[0]



###########################
###### Main script ########
###########################
nDays = args.d
dataFileName = args.f + '.txt'
figureFileName = args.f + '.png'

srepCommand = 'sreport -np cluster AccountUtilizationByUser Account=snic2015-10-21 format=Cluster,Accounts,Login,Proper,Used'
if args.s:
    command = args.s + ' ' + srepCommand
else:
    command = srepCommand

CPUsageData = CPUsageData()

print "Importing data from '%s'." % dataFileName
CPUsageData.importData(dataFileName,dateFormat)

print "Fetching data from cluster."
for i in range(nDays)[::-1]:
    currentDate = today-i*oneDay
    if not CPUsageData.dateExists(currentDate):
        out, err = subprocess.Popen(command.split(' ')+['start='+str(currentDate)]+['end='+str(currentDate+oneDay)], stdout=subprocess.PIPE).communicate()

        cluster, usage = parseOutput(out)
        CPUsageData.addUsage(cluster,usage,currentDate)
    elif CPUsageData.isLatestDate(currentDate):
        out, err = subprocess.Popen(command.split(' ')+['start='+str(currentDate)]+['end='+str(currentDate+oneDay)], stdout=subprocess.PIPE).communicate()

        cluster, usage = parseOutput(out)
        CPUsageData.overwriteUsage(cluster,usage,currentDate)
    print '\r',
    print '%.1f' % (100*(1-float(i)/nDays))+'%',
    #CPUsageData.dataCheck()
print ''
CPUsageData.sort()
print "Exporting data to '%s'." % dataFileName
CPUsageData.exportData(dataFileName)
print "Generating figure named '%s'." % figureFileName
CPUsageData.plot(figureFileName)
print 'Done!'
