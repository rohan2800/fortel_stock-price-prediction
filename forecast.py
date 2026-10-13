"""
LSTM / GRU 30-day close-price forecasting for the Fortel app.

- Prices are scaled to [0, 1] with a scaler fitted on the training slice only.
- Each window is a sequence of 30 timesteps with 1 feature (look_back is the
  time axis, not a feature list), which is what LSTM/GRU expect.
- The forecast is seeded with the most recent 30 closes, so the first predicted
  value is the day after the last known close.
- EarlyStopping restores the best weights, so no checkpoint file is written.
- Charts are returned as PNG bytes, so concurrent requests never share files.
"""
import io
import os
import warnings

os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'
warnings.filterwarnings('ignore')

import numpy as np
from sklearn.preprocessing import MinMaxScaler
from keras.models import Sequential
from keras.layers import LSTM, GRU, Dropout, Dense
from keras.callbacks import EarlyStopping
from matplotlib.figure import Figure

LOOK_BACK = 30          # days of history per training window
FORECAST_DAYS = 30      # days predicted ahead
MIN_HISTORY = LOOK_BACK + 50
TRAIN_FRACTION = 0.8    # share of history used to fit the scaler
EPOCHS = 50
BATCH_SIZE = 128
UNITS = 512
PLOT_HISTORY = 100      # historical points shown on the chart


def make_windows(series, look_back=LOOK_BACK):
    """X[i] holds series[i:i+look_back]; y[i] is the value right after it."""
    X, y = [], []
    for i in range(len(series) - look_back):
        X.append(series[i:i + look_back])
        y.append(series[i + look_back])
    return np.array(X), np.array(y)


def build_model(cell, look_back=None, units=None):
    look_back = look_back or LOOK_BACK
    units = units or UNITS  # read at call time so the settings can be overridden
    Layer = LSTM if cell == 'LSTM' else GRU
    model = Sequential(name=f'Proposed_{cell}')
    model.add(Layer(units, activation='tanh', input_shape=(look_back, 1), return_sequences=True))
    model.add(Dropout(0.2))
    model.add(Layer(units, activation='tanh'))
    model.add(Dropout(0.2))
    model.add(Dense(1))
    model.compile(loss='mse', optimizer='adam')
    return model


def _forecast(model, scaled, look_back, days):
    """Roll the model forward, feeding each prediction back in as the newest step."""
    window = scaled[-look_back:].reshape(1, look_back, 1)
    preds = []
    for _ in range(days):
        p = float(model.predict(window, verbose=0)[0, 0])
        preds.append(p)
        window = np.append(window[:, 1:, :], [[[p]]], axis=1)
    return np.array(preds)


def _plot(history, future, symbol, cell):
    x_hist = np.arange(len(history))
    x_fut = np.arange(len(history) - 1, len(history) + len(future))  # starts at last actual close
    fut_vals = np.concatenate([[history[-1]], future])

    # Figure (not pyplot) keeps state per call, so threads don't share a current figure
    fig = Figure(figsize=(16, 8))
    ax = fig.subplots()
    ax.plot(x_hist, history, color='b', label='Original series')
    ax.plot(x_fut, fut_vals, color='r', label='Forecasted series')
    ax.set_ylabel(f"{symbol} closing price (Rs.)")
    ax.set_xlabel("Days")
    ax.legend()
    ax.set_title(f"{symbol} Next {FORECAST_DAYS}-days forecast using {cell}")
    ax.grid(True, color='gray', linestyle='--', linewidth=0.5)

    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    return buf.getvalue()


def _run(stock_data, symbol, cell, patience):
    close = np.asarray(stock_data['Close'], dtype=float).ravel()
    if len(close) < MIN_HISTORY:
        raise ValueError(
            f"Not enough price history for {symbol}: got {len(close)} days, need {MIN_HISTORY}."
        )

    split = int(len(close) * TRAIN_FRACTION)
    scaler = MinMaxScaler()
    scaler.fit(close[:split].reshape(-1, 1))  # fit on training slice only
    scaled = scaler.transform(close.reshape(-1, 1)).ravel()

    X, y = make_windows(scaled)
    X = X.reshape(-1, LOOK_BACK, 1)

    model = build_model(cell)
    early_stopping = EarlyStopping(
        monitor='val_loss', mode='min', patience=patience,
        restore_best_weights=True, verbose=0,
    )
    model.fit(X, y, epochs=EPOCHS, batch_size=BATCH_SIZE,
              validation_split=0.2, callbacks=[early_stopping], verbose=0)

    future_scaled = _forecast(model, scaled, LOOK_BACK, FORECAST_DAYS)
    future = scaler.inverse_transform(future_scaled.reshape(-1, 1)).ravel()

    png = _plot(close[-PLOT_HISTORY:], future, symbol, cell)
    return png, future


def lstm_prediction(stock_data, symbol):
    """Train an LSTM on the close prices; return the forecast chart as PNG bytes."""
    png, _ = _run(stock_data, symbol, 'LSTM', patience=5)
    return png


def gru_prediction(stock_data, symbol):
    """Train a GRU on the close prices; return the forecast chart as PNG bytes."""
    png, _ = _run(stock_data, symbol, 'GRU', patience=10)
    return png
