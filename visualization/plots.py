import numpy as np
import plotly.graph_objects as go

from core.fourier.series import evaluate_series


def create_fourier_plot(
    function,
    L,
    a0,
    an,
    bn,
    points=1000
):
    """
    Create an interactive Plotly graph comparing
    the original function with its Fourier approximation.
    """

    x = np.linspace(-L, L, points)

    original = np.array([
        function(value)
        for value in x
    ])

    approximation = np.array([
        evaluate_series(
            value,
            L,
            a0,
            an,
            bn
        )
        for value in x
    ])

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=x,
            y=original,
            mode="lines",
            name="Original Function"
        )
    )

    figure.add_trace(
        go.Scatter(
            x=x,
            y=approximation,
            mode="lines",
            name="Fourier Approximation"
        )
    )

    figure.update_layout(
        title="Fourier Series Approximation",
        xaxis_title="x",
        yaxis_title="f(x)",
        hovermode="x unified",
        template="plotly_white"
    )

    return figure