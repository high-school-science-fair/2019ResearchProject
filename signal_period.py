"""
This is where a signal's period is calculated from radial
velocity data using Keplerian physics.
"""
import sys

sys.path.insert(0, '/Users/Shefali_Prabhakar/Desktop/radvel')

import radvel.plot.mcmc_plots
import pylab as pl

import radvel
import astropy.stats
import scipy
from pylab import *
import numpy as np
import data_handling
import collections

import sympy
import pandas
import itertools
import signal
import sys, traceback

matplotlib.rcParams['font.size'] = 14


def ti(t, num):
    """
    outlines time-length.
    :param num:
    :param t: list of times
    :return: list of times with range given in t, with even intervals.
    """
    time_space = np.linspace(t[0] - 5, t[-1] + 5, int(num))

    return time_space


def frequency2period(frequencies):
    """
    f = 1/p. p=1/f
    :param frequencies: list of frequencies
    :return: list of periods
    """
    pperiods = []
    for ffrequency in frequencies:
        period = 1 / ffrequency

        pperiods.append(period)

    return pperiods


class RadvelAnalysis:
    def __init__(self, t, y, err):
        self.t = t
        self.y = y
        self.err = err

    def lomb_scargle_periods(self):
        """
        finds lomb scargle periodogram periods
        :return: frequency, powers, false alarm probability
        """
        frequencys, powerslist = astropy.stats.LombScargle(self.t, self.y, self.err).autopower()
        max_freq = frequencys[np.argmax(powerslist)]

        frequencys = list(frequencys)
        powerslist = list(powerslist)

        falseap = []
        falseap = list(falseap)

        for powe in powerslist:
            false_alarm_prob = astropy.stats.LombScargle(t=self.t, y=self.y). \
                false_alarm_probability(power=powe, maximum_frequency=max_freq)

            falseap.append(false_alarm_prob)

        return frequencys, powerslist, falseap


def initialize_model(period, period2):
    params = radvel.Parameters(1, basis='per tc secosw sesinw logk')  # number of planets = 1
    params['per1'] = radvel.Parameter(value=float(period))
    # params['tc1'] = radvel.Parameter(value=random.uniform(self.period, self.period + 100))
    params['tc1'] = radvel.Parameter(value=float(period + 53))
    params['secosw1'] = radvel.Parameter(value=0.01)
    params['sesinw1'] = radvel.Parameter(value=0.01)
    params['logk1'] = radvel.Parameter(value=1.1)  # 1
    params['per2'] = radvel.Parameter(value=float(period2))
    params['tc2'] = radvel.Parameter(value=float(period + 53))
    params['secosw2'] = radvel.Parameter(value=0.01)
    params['sesinw2'] = radvel.Parameter(value=0.01)
    params['logk2'] = radvel.Parameter(value=1.1)
    return params


class RadvelModels:

    def __init__(self, period, t, y, err, period2):
        """

        :param period: list
        :param t: list
        :param y: list
        :param err: list
        """
        self.period = period
        self.t = t
        self.y = y
        self.err = err
        self.time_base = 2420
        self.period2 = period2

    def initialize_like(self, nmod):
        like = radvel.likelihood.RVLikelihood(nmod, self.t, self.y, self.err)

        return like

    def radvel_analysis(self):
        mods = initialize_model(self.period, self.period2)
        dmod = radvel.RVModel(mods, time_base=self.time_base)
        # These values are centered around results by Shen and Turke (2018):
        dmod.params['sesinw1'] = radvel.Parameter(value=0.1)
        dmod.params['secosw1'] = radvel.Parameter(value=0.1)
        dmod.params['sesinw2'] = radvel.Parameter(value=0.1)
        dmod.params['secosw2'] = radvel.Parameter(value=0.1)

        like = RadvelModels.initialize_like(self, nmod=dmod)
        like.params['gamma'] = radvel.Parameter(value=0.1)
        like.params['jit'] = radvel.Parameter(value=1.0)

        like.params['per1'].vary = True
        like.params['per2'].vary = True
        like.params['tc1'].vary = True
        like.params['tc2'].vary = True

        like.params['secosw1'].vary = True
        like.params['sesinw1'].vary = True
        like.params['secosw2'].vary = True
        like.params['sesinw2'].vary = True

        post = radvel.posterior.Posterior(like)
        post.priors += [radvel.prior.EccentricityPrior(2)]

        def plot_results(llike):
            yerr = llike.yerr.tolist()

            ttime = self.t
            ttime = ti(t=ttime, num=len(llike.x))
            # fig = pl.figure(figsize=(12, 4))
            fig = pl.gcf()
            fig.set_tight_layout(True)
            pl.errorbar(
                llike.x, llike.model(ttime),  # llike.residuals(),  # + llike.residuals(),
                yerr=float(data_handling.average(yerr)), fmt='o'
            )
            pl.plot(ttime, llike.model(ttime))
            pl.xlabel('Time')
            pl.ylabel('RV')
            pl.draw()

        print("LIKE:: ")
        print(like)

        res = scipy.optimize.minimize(
            post.neglogprob_array,  # objective function is negative log likelihood
            post.get_vary_params(),  # initial variable parameters
            method='Nelder-Mead',  # Nelder-Mead also works
        )


        print("POST:: ")
        print(post)

        return post


def period2params(period, t, y):
    """
    computes amplitude and orbital phase from periods using a sin best fit.

    :param period: float
    :param t: list
    :param y: list
    :return:amplitude, orbital phase of signal
    """
    ampl = []
    orb_phase = []

    thefrequency = 1. / period

    def func(amplitude, orbital_phase, x):
        sinfunc = amplitude * math.sin(thefrequency * x + orbital_phase)
        return sinfunc

    popt, pcov = scipy.optimize.curve_fit(func, t, y)

    ampl.append(popt[0])
    orb_phase.append(popt[1])

    return popt[0], popt[1]


# def eccentricity(secosw, sesinw):
#     """
#     Finds eccentricity from radvel data
#     :param secosw: float
#     :param sesinw: float
#     :return: eccentricity, as a float
#     """
#
#     omega = math.atan(sesinw / secosw)
#     print("Omega:: ")
#     print(omega)
#     # omega = sympy.acot(secosw / sesinw)
#     eccen = (secosw * math.cos(omega))
#     print("eccen:: ")
#     print(eccen)
#     eccentric = eccen ** 2
#
#     return eccentric

def eccentricity(secosw, sesinw):
    """
    Finds eccentricity from radvel data
    :param secosw: float
    :param sesinw: float
    :return: eccentricity, as a float
    """

    eccen = secosw**2 + sesinw**2
    print(eccen)

    return eccen


def kepler_params(target_name, t, y, err, outputfile):
    """
    compiles all above functions into one, based exculsively on time, radial velocity, and err of radial velocity.
    Automatically initiates radvel analysis
    :param outputfile:
    :param target_name: string
    :param t: list
    :param y: radial velocity, list
    :param err: error of radial velocity, list
    :return: dataframe with all keplerian elements.
    """

    if len(t) < 4:

        print("Too less data to make conclusions, moving on...")


    else:
        frequencies, thepowers, thefap = RadvelAnalysis(t, y, err).lomb_scargle_periods()

        theperiods = frequency2period(frequencies)

        eccen = []
        amp = []
        orbp = []
        host_name = []
        pperiods = []
        ppowers = []
        pfap = []


        for num, (per, f) in enumerate(itertools.zip_longest(theperiods, thefap), start=0):

            if f > 7.00:

                del frequencies[num]
                del thepowers[num]
                del thefap[num]

                break

            else:

                # post = RadvelModels(per[num], t, y, err, per[num+1]).post
                post = RadvelModels(err=err, t=t, y=y, period=theperiods[num],
                                    period2=theperiods[num]).radvel_analysis()

                # post = dict(post)
                pperiods.append(per)
                ppowers.append(thepowers[num])
                pfap.append(thefap[num])

                post = post.params
                secosw = str(post['secosw1'])
                sesinw = str(post['sesinw1'])

                secosw = str(secosw.split()[4].split()[0])
                secosw = float(secosw.split(sep=",")[0])

                sesinw = str(sesinw.split()[4].split()[0])
                sesinw = float(sesinw.split(sep=",")[0])

                ecc = eccentricity(secosw, sesinw)

                eccen.append(ecc)

                amplitude, orbital_phase = period2params(per, t, y)

                amp.append(amplitude)

                orbp.append(orbital_phase)
                host_name.append(str(target_name))

                def keyboardInterruptHandler(ssignals, frame):
                    print("KeyboardInterrupt (ID: {}) has been caught. Cleaning up...".format(ssignals))

                    kep_lerian_info = collections.OrderedDict(
                        {"Star": host_name, "Period": pperiods, "Power": ppowers, "FAP": pfap,
                         "Eccentricity": eccen, "Orbital Phase": orbp, "Amplitude": amp})

                    print(len(host_name), len(theperiods), len(thepowers), len(thefap), len(eccen), len(orbp), len(amp))

                    kepl_df = pandas.DataFrame.from_dict(kep_lerian_info)
                    pandas.DataFrame(dict([(k, pandas.Series(v)) for k, v in kepl_df.items()]))

                    print("\nDone! This dataframe has been returned. It is not saved to an output file(do that yourself)")
                    print(kepl_df)
                    exit(0)

                    return kepl_df

                signal.signal(signal.SIGINT, keyboardInterruptHandler)

                while False:
                    pass



    # keplerian_info = {'Star Name': host_name, 'Period': theperiods, 'Power': thepowers, 'FAP': thefap,
    #                   'Eccentricity': eccen, 'Orbital Phase': orbp}


    keplerian_info = collections.OrderedDict({"Star": host_name, "Period": pperiods, "Power": ppowers, "FAP": pfap,
                                              "Eccentricity": eccen, "Orbital Phase": orbp, "Amplitude": amp})

    print(len(host_name), len(theperiods), len(thepowers), len(thefap), len(eccen), len(orbp), len(amp))

    kep_df = pandas.DataFrame.from_dict(keplerian_info)
    pandas.DataFrame(dict([(k, pandas.Series(v)) for k, v in kep_df.items()]))

    kep_df.to_csv(outputfile)

    print("\nDone! The dataframe has been saved in the output file: " + str(outputfile))

    return kep_df


def main():
    """
    Adopted functionality for making directories at https://realpython.com/working-with-files-in-python/
    """
    filenames = os.listdir("keck_vels/")
    planets = pd.read_csv("HiRESdetections.csv")["Name"].values.tolist()
    planets = [s + "_KECK.txt" for s in planets]
    print(planets)
    df = pd.DataFrame({"Stellar Type": [], "Star Mass": [], "Star Radius": [], "Effective Temperature": [],
                       "H Alpha: Average": [], "H Alpha: Variance": [], "H Alpha: STDEV": [],
                       "S-Value: Average": [], "S-Value: Variance": [], "S-value: STDEV": [],
                       "RV: Average": [], "RV: Variance": [], "RV: STDEV": [],
                       "RV Error: Average": [], "RV Error: Variance": [], "RV Error: STDEV": []})
    for x in planets[20:23]:
        file = x

        path = "DATA_real/"
        print(path)
        try:
            os.mkdir(path)
        except OSError:
            print("Creation of the directory %s failed" % path)
            path = ""
        else:
            print("Successfully created the directory %s " % path)
            path = str(path + "/")

        path = "DATA_real/" + os.path.splitext(file)[0]
        print("Analyzing the stellar system ", path, " for basic statistics...")
        file = "keck_vels/" + file
        print(path)
        try:
            os.mkdir(path)
        except OSError:
            print("Creation of the directory %s failed" % path)
            path = ""
        else:
            print("Successfully created the directory %s " % path)
            path = str(path + "/")

        stardf = star_stats(Reader.read(file))
        df = pd.concat([df, stardf], ignore_index=True)

        time_series = Reader.read(Reader.read(file))
        time = list(time_series.iloc[:, 0])
        ravel = list(time_series.iloc[:, 1])
        error = list(time_series.iloc[:, 2])
        frequency, powers, fap = RadvelAnalysis(t=time, y=ravel, err=error).lomb_scargle_periods()

        print("Frequencies:: " + str(len(frequency)))
        # print(frequency)

        print("Powers:: " + str(len(powers)))
        # print(powers)

        print("False Alarm Probability:: " + str(len(fap)))
        # print(fap)

        periods = frequency2period(frequency)

        print("Periods:: " + str(len(periods)))

        first_period = periods[0]
        second_period = periods[1]

        print(RadvelModels(err=error, t=time, y=ravel, period=first_period, period2=second_period).radvel_analysis())
        print(kepler_params(str(i), t=time, y=ravel, err=error,
                            outputfile="DATA/kepparams"+x+".csv"))


        print(detect(file, savedir=path))




filenames = os.listdir("keck_vels/")
planets = pd.read_csv("HiRESdetections.csv")["Name"].values.tolist()
planets = [s + "_KECK.txt" for s in planets]
print(planets)
df = pd.DataFrame({"Stellar Type": [], "Star Mass": [], "Star Radius": [], "Effective Temperature": [],
               "H Alpha: Average": [], "H Alpha: Variance": [], "H Alpha: STDEV": [],
               "S-Value: Average": [], "S-Value: Variance": [], "S-value: STDEV": [],
               "RV: Average": [], "RV: Variance": [], "RV: STDEV": [],
               "RV Error: Average": [], "RV Error: Variance": [], "RV Error: STDEV": []})
for x in planets[20:23]:


    path = "DATA_real/"
    print(path)
    try:
        os.mkdir(path)
    except OSError:
        print("Creation of the directory %s failed" % path)
        path = ""
    else:
        print("Successfully created the directory %s " % path)
        path = str(path + "/")

    path = "DATA_real/" + os.path.splitext(file)[0]
    print("Analyzing the stellar system ", path, " for basic statistics...")
    file = "keck_vels/" + file
    print(path)
    try:
        os.mkdir(path)
    except OSError:
        print("Creation of the directory %s failed" % path)
        path = ""
    else:
        print("Successfully created the directory %s " % path)
        path = str(path + "/")

    stardf = star_stats(Reader.read(file))
    df = pd.concat([df, stardf], ignore_index=True)
    print(detect(file, savedir=path))

    print("Done! Here is the final dataset: \n", df)
    df.to_csv("DATA_real/StellarSampleStats.csv")

    path = "DATA"
    try:
        os.mkdir(path)
    except OSError:
        print("Creation of the directory %s failed" % path)
        path = ""
    else:
        print("Successfully created the directory %s " % path)
        path = str(path + "/")

    for x in planets[0:20]:

        time_series = pandas.DataFrame(
            data_handling.csv2df(str(time_series_base)+str(x)+str('.text')))
        time = list(time_series.iloc[:, 0])
        ravel = list(time_series.iloc[:, 1])
        error = list(time_series.iloc[:, 2])
        frequency, powers, fap = RadvelAnalysis(t=time, y=ravel, err=error).lomb_scargle_periods()

        print("Frequencies:: " + str(len(frequency)))
        # print(frequency)





        print("Powers:: " + str(len(powers)))
        # print(powers)

        print("False Alarm Probability:: " + str(len(fap)))
        # print(fap)

        periods = frequency2period(frequency)

        print("Periods:: " + str(len(periods)))

        first_period = periods[0]
        second_period = periods[1]

        print(RadvelModels(err=error, t=time, y=ravel, period=first_period, period2=second_period).radvel_analysis())
        print(kepler_params(str(i), t=time, y=ravel, err=error,
                            outputfile="/Users/Shefali_Prabhakar/Documents/Validation_Set_GP_Science_Fair/kepparams209.csv"))

        # print(RadvelModels(err=error, t=time, y=ravel, period=first_period, period2=second_period).radvel_analysis())
        # print(kepler_params(str(i), t=time, y=ravel, err=error,
        #                     outputfile="/Volumes/SFDATA2018/Keplerianparams/dataset" + str(i)+ str(".csv")))



