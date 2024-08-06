import numpy as np
from keras.models import Sequential
from keras.layers import LSTM, Dropout, Dense, GRU
from keras.callbacks import ModelCheckpoint, EarlyStopping
import keras
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('agg')
import warnings
import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

warnings.filterwarnings('ignore')

def format(series: np.array = np.array([]), look_back: int = 5):
    """
    Create a (X, Y) feature-output dataset for ML workflow
    :param series: Numpy (1, ) array
    :param look_back: The number of previous features to be considered for forecasting
    :return: X and Y modelling parameters
    """
    X = []
    Y = []
    for n in range(len(series)):
        k = n + look_back
        if k >= len(series):
            break
        Xtn = series[n:k]
        if len(Xtn) != look_back:
            break
        Ytn = series[k]
        X.append(Xtn)
        Y.append(Ytn)
    return np.array(X), np.array(Y)

def lstm_prediction(stock_data,symbol):
    print('Training phase')
    model_filepath='lstm_model.keras'
    plot_path=os.path.join('static','images','lstm.png')
    # Calculate the mean of the 'Close' series
    mean = np.mean(stock_data['Close'].values)

    # Adjust the series by downscaling it using the mean
    adjusted_series = stock_data['Close'].values - mean

        # Define the look-back period you want to use
    look_back = 30  # This can be adjusted according to your needs

    # Format the adjusted series using the 'format' function
    X, y = format(adjusted_series, look_back=look_back)

    # Reshape the feature set (X) to be suitable for LSTM models
    Xr = X.reshape((X.shape[0], 1, X.shape[1]))

    # Create the Sequential model with a name
    model = Sequential(name="Proposed_LSTM")
    model.add(LSTM(units=512, activation='relu', input_shape=(1,look_back), return_sequences=True, name="input"))
    model.add(Dropout(0.2))
    model.add(LSTM(units=512, activation='relu', name="lstm"))
    model.add(Dropout(0.2))
    model.add(Dense(1, name="output"))
    model.compile(loss='mse', optimizer='adam')

    # Save the best model based on validation loss
    checkpoint_callback = ModelCheckpoint(
        filepath=model_filepath,
        save_best_only=True,
        monitor='val_loss',  # Metric to monitor
        mode='min',  # Minimize the monitored metric
        verbose=1  # Verbosity level
    )

    # Create an EarlyStopping callback to stop training when validation loss does not improve
    early_stopping = EarlyStopping(
        monitor='val_loss',  # Metric to monitor
        mode='min',  # Minimize the monitored metric
        patience=5,  # Number of epochs to wait before stopping if no progress
        verbose=1  # Verbosity level
    )

    # Add the callbacks to a list
    callbacks = [checkpoint_callback, early_stopping]

    # Train the model
    model.fit(Xr, y, epochs=50,  batch_size=128,  validation_split=0.2, callbacks=callbacks)

    #load model
    model=keras.models.load_model(model_filepath)

    days=30
    mean_added_pred = []
    x = Xr[-1]  # Initially take last training input for predicting its immediate next value

    for i in range(days):
      x = x.reshape((1, 1, look_back))  # Prepare the input for a tensorflow model using reshaping
      prediction = model.predict(x, verbose=False)   # Predict the immediate next value
      x = x.ravel()  # Ravel method converts the 3D array to single dimension array 
      x = np.delete(x, 0)  # Now, we delete first item of the original input
      x = np.append(x, prediction[0][0])  # and append the predicted value to use it for next predictions
      mean_added_pred.append(prediction[0][0])   # append the predicted value to 'predictions' list

    mean_added_pred+=mean
    y+=mean
    fig, ax = plt.subplots(figsize=(16, 8))

# Plot the forecasted series and the original series
    ax.plot(np.append(y[-100:], mean_added_pred), color='r', label="Forecasted series")
    ax.plot(y[-100:], color='b', label="Original series")

    # Set labels and legend
    ax.set_ylabel(f"{symbol} closing price (Rs.)")
    ax.set_xlabel("Days")
    ax.legend()

    # Set the title
    ax.set_title(f"{symbol} Next 30-days forecast using LSTM")

    # Add a grid to the plot
    ax.grid(True, color='gray', linestyle='--', linewidth=0.5)

    # Save the figure to the specified path
    fig.savefig(plot_path)

    # Close the figure
    plt.close(fig)
    return plot_path
    

def gru_prediction(stock_data,symbol):
    model_filepath='gru_model.keras'
    plot_path=os.path.join('static', 'images', 'gru.png')
    # Calculate the mean of the 'Close' series
    mean = np.mean(stock_data['Close'].values)

    # Adjust the series by downscaling it using the mean
    adjusted_series = stock_data['Close'].values - mean

        # Define the look-back period you want to use
    look_back = 30  # This can be adjusted according to your needs

    # Format the adjusted series using the 'format' function
    X, y = format(adjusted_series, look_back=look_back)

    # Reshape the feature set (X) to be suitable for LSTM models
    Xr = X.reshape((X.shape[0], 1, X.shape[1]))

    # Create the Sequential model with a name
    model = Sequential(name="Proposed_GRU")
    model.add(GRU(units=512, activation='relu', input_shape=(1,look_back), return_sequences=True, name="input"))
    model.add(Dropout(0.2))
    model.add(GRU(units=512, activation='relu', name="gru"))
    model.add(Dropout(0.2))
    model.add(Dense(1, name="output"))
    model.compile(loss='mse', optimizer='adam')

    # Save the best model based on validation loss
    checkpoint_callback = ModelCheckpoint(
        filepath=model_filepath,
        save_best_only=True,
        monitor='val_loss',  # Metric to monitor
        mode='min',  # Minimize the monitored metric
        verbose=1  # Verbosity level
    )

    # Create an EarlyStopping callback to stop training when validation loss does not improve
    early_stopping = EarlyStopping(
        monitor='val_loss',  # Metric to monitor
        mode='min',  # Minimize the monitored metric
        patience=10,  # Number of epochs to wait before stopping if no progress
        verbose=1  # Verbosity level
    )

    # Add the callbacks to a list
    callbacks = [checkpoint_callback, early_stopping]

    # Train the model
    model.fit(Xr, y, epochs=50,  batch_size=128,  validation_split=0.2, callbacks=callbacks)

    #load model
    model=keras.models.load_model(model_filepath)

    days=30
    mean_added_pred = []
    x = Xr[-1]  # Initially take last training input for predicting its immediate next value

    for i in range(days):
      x = x.reshape((1, 1, look_back))  # Prepare the input for a tensorflow model using reshaping
      prediction = model.predict(x, verbose=False)   # Predict the immediate next value
      x = x.ravel()  # Ravel method converts the 3D array to single dimension array 
      x = np.delete(x, 0)  # Now, we delete first item of the original input
      x = np.append(x, prediction[0][0])  # and append the predicted value to use it for next predictions
      mean_added_pred.append(prediction[0][0])   # append the predicted value to 'predictions' list

    mean_added_pred+=mean
    y+=mean
    fig, ax = plt.subplots(figsize=(16, 8))

# Plot the forecasted series and the original series
    ax.plot(np.append(y[-100:], mean_added_pred), color='r', label="Forecasted series")
    ax.plot(y[-100:], color='b', label="Original series")

    # Set labels and legend
    ax.set_ylabel(f"{symbol} closing price (Rs.)")
    ax.set_xlabel("Days")
    ax.legend()

    # Set the title
    ax.set_title(f"{symbol} Next 30-days forecast using GRU")

    # Add a grid to the plot
    ax.grid(True, color='gray', linestyle='--', linewidth=0.5)

    # Save the figure to the specified path
    fig.savefig(plot_path)

    # Close the figure
    plt.close(fig)
    return plot_path
    
