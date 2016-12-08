
# This file is part of the exercise code repository accompanying
# the book: Neuronal Dynamics (see http://neuronaldynamics.epfl.ch)
# located at http://github.com/EPFL-LCN/neuronaldynamics-exercises.

# This free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License 2.0 as published by the
# Free Software Foundation. You should have received a copy of the
# GNU General Public License along with the repository. If not,
# see http://www.gnu.org/licenses/.

# Should you reuse and publish the code for your own purposes,
# please cite the book or point to the webpage http://neuronaldynamics.epfl.ch.

# Wulfram Gerstner, Werner M. Kistler, Richard Naud, and Liam Paninski.
# Neuronal Dynamics: From Single Neurons to Networks and Models of Cognition.
# Cambridge University Press, 2014.

import matplotlib.pyplot as plt
import brian2 as b2
import numpy


def plot_voltage_and_current_traces(voltage_monitor, current, title=None, firing_threshold=None,
                                    do_show_plot=True, legend_location=1):
    """plots voltage and current .

    Args:
        voltage_monitor (StateMonitor): recorded voltage
        current (TimedArray): injected current
        title (string, optional): title of the figure
        firing_threshold (Quantity, optional): if set to a value, the firing threshold is plotted.
        do_show_plot (bool): optional, default=True. Set it to False to suppress the blocking pyplot.show() call.
    """

    assert isinstance(voltage_monitor, b2.StateMonitor), "voltage_monitor is not of type StateMonitor"
    assert isinstance(current, b2.TimedArray), "current is not of type TimedArray"

    time_values_ms = voltage_monitor.t / b2.ms

    # current
    axis_c = plt.subplot(211)
    c = current(voltage_monitor.t, 0)
    max_current = max(current(voltage_monitor.t, 0))
    min_current = min(current(voltage_monitor.t, 0))
    margin = 1.05 * (max_current - min_current)
    # plot the input current time-aligned with the voltage monitor
    plt.plot(voltage_monitor.t / b2.ms, c, "r", lw=2)
    if margin > 0.:
        plt.ylim((min_current - margin) / b2.amp, (max_current + margin) / b2.amp)
    # plt.xlabel("t [ms]")
    plt.ylabel("Input current [A] \n min: {0} \nmax: {1}".format(min_current, max_current))
    plt.grid()
    axis_v = plt.subplot(212)
    plt.plot(time_values_ms, voltage_monitor[0].v / b2.mV, lw=2)
    if firing_threshold is not None:
        plt.plot(
            (voltage_monitor.t / b2.ms)[[0, -1]],
            [firing_threshold / b2.mV, firing_threshold / b2.mV],
            "r--", lw=2
        )
    max_val = max(voltage_monitor[0].v)
    if firing_threshold is not None:
        max_val = max(max_val, firing_threshold)
    min_val = min(voltage_monitor[0].v)
    margin = 0.05 * (max_val - min_val)
    plt.ylim((min_val - margin) / b2.mV, (max_val + margin) / b2.mV)
    plt.xlabel("t [ms]")
    plt.ylabel("membrane voltage [mV]\n min: {0}\n max: {1}".format(min_val, max_val))
    plt.grid()

    if firing_threshold is not None:
        plt.legend(["vm", "firing threshold"], fontsize=12, loc=legend_location)

    if title is not None:
        plt.suptitle(title)
    if do_show_plot:
        plt.show()


def plot_network_activity(rate_monitor, spike_monitor, voltage_monitor=None, spike_train_idx_list=None,
                          t_min=None, t_max=None, N_highlighted_spiketrains=3):
    """
    Visualizes the results of a network simulation: spike-train, population activity and voltage-traces.

    Args:
        rate_monitor (PopulationRateMonitor): rate of the population
        spike_monitor (SpikeMonitor): spike trains of individual neurons
        voltage_monitor (StateMonitor): optional. voltage traces of some (same as in spike_train_idx_list) neurons
        spike_train_idx_list (list): optional. A list of neuron indices whose spike-train is plotted.
            If no list is provided, all (up to 500) spike-trains in the spike_monitor are plotted.
        t_min (Quantity): optional. lower bound of the plotted time interval.
            if t_min is None, it is set to the larger of [0ms, (t_max - 100ms)]
        t_max (Quantity): optional. upper bound of the plotted time interval.
            if t_max is None, it is set to the timestamp of the last spike in
        N_highlighted_spiketrains (int): optional. Number of spike trains visually highlighted, defaults to 3
            If N_highlighted_spiketrains==0 and voltage_monitor is not None, then all voltage traces of
            the voltage_monitor are plotted. Otherwise N_highlighted_spiketrains voltage traces are plotted.

    Returns:
        Figure: The whole figure
        Axes: Top panel, Raster plot
        Axes: Middle panel, population activity
        Axes: Bottom panel, voltage traces. None if no voltage monitor is provided.
    """

    assert isinstance(rate_monitor, b2.PopulationRateMonitor), \
        "rate_monitor  is not of type PopulationRateMonitor"
    assert isinstance(spike_monitor, b2.SpikeMonitor), \
        "spike_monitor is not of type SpikeMonitor"
    assert (voltage_monitor is None) or (isinstance(voltage_monitor, b2.StateMonitor)), \
        "voltage_monitor is not of type StateMonitor"
    assert (spike_train_idx_list is None) or (isinstance(spike_train_idx_list, list)), \
        "spike_train_idx_list is not of type list"

    all_spike_trains = spike_monitor.spike_trains()
    if spike_train_idx_list is None:
        if voltage_monitor is not None:
            # if no index list is provided use the one from the voltage monitor
            spike_train_idx_list = numpy.sort(voltage_monitor.record)
        else:
            # no index list AND no voltage monitor: plot all spike trains
            spike_train_idx_list = numpy.sort(all_spike_trains.keys())
        if len(spike_train_idx_list) > 500:
            # avoid slow plotting of a large set
            spike_train_idx_list = spike_train_idx_list[:500]

    # get a reasonable default interval
    if t_max is None:
        t_max = max(rate_monitor.t/b2.ms)
    else:
        t_max = t_max/b2.ms
    if t_min is None:
        t_min = max(0., t_max-100.)  # if none, plot at most the last 100ms
    else:
        t_min = t_min / b2.ms

    fig = None
    ax_raster = None
    ax_rate = None
    ax_voltage = None
    if voltage_monitor is None:
        fig, (ax_raster, ax_rate) = plt.subplots(2, 1, sharex=True)
    else:
        fig, (ax_raster, ax_rate, ax_voltage) = plt.subplots(3, 1, sharex=True)

    # nested helpers to plot the parts, note that they use parameters defined outside.
    def get_spike_train_ts_indices(spike_train):
        """
        Helper. Extracts the spikes within the time window from the spike train
        """
        ts = spike_train/b2.ms
        spike_within_time_window = (ts >= t_min) & (ts <= t_max)
        idx_spikes = numpy.where(spike_within_time_window)
        ts_spikes = ts[idx_spikes]
        return idx_spikes, ts_spikes

    def plot_raster():
        """
        Helper. Plots the spike trains of the spikes in spike_train_idx_list
        """
        neuron_counter = 0
        for neuron_index in spike_train_idx_list:
            idx_spikes, ts_spikes = get_spike_train_ts_indices(all_spike_trains[neuron_index])
            ax_raster.scatter(ts_spikes, neuron_counter * numpy.ones(ts_spikes.shape),
                              marker=".", c="k", s=15, lw=0)
            neuron_counter += 1
        ax_raster.set_ylim([0, neuron_counter])

    def highlight_raster(neuron_idxs):
        """
        Helper. Highlights three spike trains
        """
        for i in range(len(neuron_idxs)):
            color = "r" if i == 0 else "k"
            raster_plot_index = neuron_idxs[i]
            population_index = spike_train_idx_list[raster_plot_index]
            idx_spikes, ts_spikes = get_spike_train_ts_indices(all_spike_trains[population_index])
            ax_raster.axhline(y=raster_plot_index, linewidth=.5, linestyle="-", color=[.9, .9, .9])
            ax_raster.scatter(
                ts_spikes, raster_plot_index * numpy.ones(ts_spikes.shape),
                marker=".", c=color, s=144, lw=0)
        ax_raster.set_ylabel("neuron #")
        ax_raster.set_title("Raster Plot (random subset)", fontsize=10)

    def plot_population_activity():
        """
        Helper. Plots the population rate and a mean
        """
        ts = rate_monitor.t / b2.ms
        idx_rate = (ts >= t_min) & (ts <= t_max)
        # ax_rate.plot(ts[idx_rate],rate_monitor.rate[idx_rate]/b2.Hz, ".k", markersize=2)
        smoothed_rates = rate_monitor.smooth_rate(window="flat", width=0.5*b2.ms)/b2.Hz
        ax_rate.plot(ts[idx_rate], smoothed_rates[idx_rate])
        ax_rate.set_ylabel("A(t) [Hz]")
        ax_rate.set_title("Population Activity", fontsize=10)

    def plot_voltage_traces(voltage_traces_i):
        """
        Helper. Plots three voltage traces
        """
        ts = voltage_monitor.t/b2.ms
        idx_voltage = (ts >= t_min) & (ts <= t_max)
        for i in range(len(voltage_traces_i)):
            color = "r" if i == 0 else ".7"
            raster_plot_index = voltage_traces_i[i]
            population_index = spike_train_idx_list[raster_plot_index]
            ax_voltage.plot(
                ts[idx_voltage], voltage_monitor[population_index].v[idx_voltage]/b2.mV,
                c=color, lw=1.)
            ax_voltage.set_ylabel("V(t) [mV]")
            ax_voltage.set_title("Voltage Traces", fontsize=10)

    plot_raster()
    plot_population_activity()
    nr_neurons = len(spike_train_idx_list)
    highlighted_neurons_i = []  # default to an empty list.
    if N_highlighted_spiketrains > 0:
        fract = numpy.linspace(0, 1, N_highlighted_spiketrains+2)[1:-1]
        highlighted_neurons_i = [int(nr_neurons * v) for v in fract]
        highlight_raster(highlighted_neurons_i)

    if voltage_monitor is not None:
        if N_highlighted_spiketrains == 0:
            traces_i = range(nr_neurons)
        else:
            traces_i = highlighted_neurons_i
        plot_voltage_traces(traces_i)

    plt.xlabel("t [ms]")
    return fig, ax_raster, ax_rate, ax_voltage


def plot_ISI_distribution(spike_monitor, hist_nr_bins=50, hist_max_ISI=100.*b2.ms):
    """
    Computes the ISI distribution of the given spike_monitor and displays the distribution in a histogram

    Args:
        spike_monitor (SpikeMonitor): spikes
        hist_nr_bins: Number of histrogram bins.
        hist_max_ISI: the plot is cut off at this ISI. Note: the CV shown in the figure
            title is computed using ALL spikes in the given monitor.

    """
    from neurodynex.tools import spike_tools
    stats = spike_tools.get_spike_train_stats(spike_monitor)
    isi_ms = stats.all_ISI/b2.ms
    filtered_is = isi_ms <= (hist_max_ISI/b2.ms)
    idx_isi = numpy.where(filtered_is)
    isi_ms = isi_ms[idx_isi]
    plt.figure()
    plt.hist(isi_ms, bins=hist_nr_bins)
    plt.title("ISI histogram, CV={}".format(stats.CV))
    plt.xlabel("ISI [ms]")
