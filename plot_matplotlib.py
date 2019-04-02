import numpy as np

def make_plot(df, out_filename=None):
    import matplotlib
    matplotlib.use("Agg")

    import matplotlib.pyplot as plt
    fig = plt.figure(figsize=(12,5))
    ax = plt.gca()

    # Create the labels including the original datetime and a sum of the rain
    deltas_string   = [delta.strftime('%H:%M') for delta in df.columns]
    sums_string     = ['%4.2f mm' % value for value in df.sum(axis=1)*(5./60.)]
    labels          = ['start '+m+', tot. '+n for m,n in zip(deltas_string, sums_string)]
    # Since timedelta objects are not correctly handled by matplotlib
    # we need to do this converstion manually
    x = df.index.values.astype(float)/(60e9)

    ax.plot(x, df.values, '-')
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.xaxis.grid(True, ls='dashed')
    #ax.set_title("Radar forecast | Basetime "+time_radar[0].strftime("%Y%m%d %H:%M"))
    ax.set_ylabel("$P$ [mm h$^{-1}$]")
    ax.set_xlabel("Time from start [minutes]")
    ax.fill_between(x, y1=0, y2=2.5, alpha=0.4, color="paleturquoise")
    ax.fill_between(x, y1=2.5, y2=7.6, alpha=0.3, color="lightseagreen")
    ax.fill_between(x, y1=7.6, y2=ax.get_ylim()[-1], alpha=0.3, color="teal")
    ax.set_xlim(left=x[0], right=x[-1])
    ax.set_ylim(bottom=0, top=df.values.max())
    if df.values.max() > 0.5:
        ax.annotate("Light", xy=(x[-20], .1), alpha=0.6)
    if df.values.max() > 3.0 :
        ax.annotate("Moderate", xy=(x[-20], 2.6), alpha=0.6)
    if df.values.max() > 8.0 :
        ax.annotate("Heavy", xy=(x[-20], 7.7), alpha=0.5)
    plt.legend(labels, fontsize=7)

    if out_filename:
        plt.savefig(out_filename)
        print("Wrote plot to `{}`".format(out_filename))

    return fig