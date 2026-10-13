from flask import Flask, render_template, request, send_file
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'

import base64
import matplotlib
matplotlib.use('agg')
from forecast import lstm_prediction, gru_prediction

# Resolve bundled files relative to this file so they work in Docker (Linux) and locally
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOCS_DIR = os.path.join(BASE_DIR, 'Documents')

def encode_png(png_bytes):
    """Base64-encode PNG bytes for an inline <img> (charts are never written to disk)."""
    return base64.b64encode(png_bytes).decode('utf-8')

def get_stock_data(stock_symbol):
    ticker = stock_symbol.upper() + '.NS'
    stock_data = yf.download(ticker, progress=False)
    if stock_data is None or stock_data.empty:
        raise ValueError(f"No price data returned for {ticker}. Please try again later.")
    # Recent yfinance returns (field, ticker) column pairs; keep just the field names
    if isinstance(stock_data.columns, pd.MultiIndex):
        stock_data.columns = stock_data.columns.get_level_values(0)
    return stock_data


def filter_stock_data(stock_data, duration):
    if duration==None:
        return stock_data
    if duration.lower() == "day":
        return stock_data.iloc[-1:]
    elif duration.lower() == "week":
        return stock_data.iloc[-5:]
    elif duration.lower() == "month":
        return stock_data.iloc[-20:]
    elif duration.lower() == "year":
        return stock_data.iloc[-252:]
    return stock_data


def calculate_ema(data, span):
    """Calculate Exponential Moving Average (EMA)"""
    return data.ewm(span=span, adjust=False).mean()

def calculate_ma(data, window):
    """Calculate Moving Average (MA)"""
    return data.rolling(window=window).mean()  

def _ensure_series(value):
    if isinstance(value, pd.DataFrame) and value.shape[1] == 1:
        return value.iloc[:, 0]
    return value

def stock_plotter(stock_data,stock_symbol):
    # Work on a copy: the indicator columns below are added to the frame
    stock_data = stock_data.copy()

    close_col = _ensure_series(stock_data.loc[:,('Close')])
    ema_val = calculate_ema(close_col, span=10)
    stock_data.loc[:, ('EMA')] = ema_val

    ma_val = calculate_ma(close_col, window=10)
    stock_data.loc[:, ('MA')] = ma_val

    open_col = _ensure_series(stock_data.loc[:,('Open')])
    high_col = _ensure_series(stock_data.loc[:,('High')])
    low_col = _ensure_series(stock_data.loc[:,('Low')])
    volume_col = _ensure_series(stock_data.loc[:,('Volume')])
    ema_col = _ensure_series(stock_data.loc[:,('EMA')])
    ma_col = _ensure_series(stock_data.loc[:,('MA')])

    # Create Candlestick trace
    candlestick_trace = go.Candlestick(x=stock_data.index,
                                       open=open_col,
                                       high=high_col,
                                       low=low_col,
                                       close=close_col,
                                       name='Candlestick')

    # Create Volume trace
    volume_trace = go.Bar(x=stock_data.index, y=volume_col, name='Volume', marker=dict(color='red'))

    # Create EMA and MA traces
    ema_trace = go.Scatter(x=stock_data.index, y=ema_col, mode='lines', name='EMA', line=dict(color='dodgerblue'), legendgroup='indicators')
    ma_trace = go.Scatter(x=stock_data.index, y=ma_col, mode='lines', name='MA', line=dict(color='purple'), legendgroup='indicators')

    # Create subplot figure with larger space for volume and moving averages
    fig = make_subplots(
        rows=4,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.35, 0.2, 0.2, 0.25],
        subplot_titles=[f"Stock Mmovement", 'Volume Chart', 'Exponential Moving Average', 'Moving Average'],
        specs=[[{"type": "candlestick"}], [{"type": "bar"}], [{"type": "scatter"}], [{"type": "scatter"}]]
    )

    # Add traces to the first subplot
    fig.add_trace(candlestick_trace, row=1, col=1)

    # Add Volume trace to the second subplot
    fig.add_trace(volume_trace, row=2, col=1)

    # Add EMA and MA traces to the third subplot
    fig.add_trace(ema_trace, row=3, col=1)
    fig.add_trace(ma_trace, row=4, col=1)

    # Update layout
    fig.update_layout(
        title=stock_symbol,
        height=860,
        width=1400,
        template='none',
        showlegend=False,
        bargap=0.2,
        margin=dict(l=60, r=30, t=80, b=60),
    )

    # Update x-axis labels
    fig.update_xaxes(title_text="Date", row=4, col=1)

    # Update y-axis labels
    fig.update_yaxes(title_text="Price (₹)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1, tickformat='~s', automargin=True)
    fig.update_yaxes(title_text="Price (₹)", row=3, col=1)
    fig.update_yaxes(title_text="Price (₹)", row=4, col=1)

    # Render to PNG bytes in memory (kaleido; no shared files between requests)
    return fig.to_image(format='png')


def extract_stock_symbol(option):
    stock_data=pd.read_csv('StockSymbols.csv')
    stock_data = stock_data.dropna(subset=['Stock', 'ID'])
    stock = stock_data.loc[stock_data['Stock'] == option]
    if stock.empty:
        raise ValueError(f"Selected stock option not found: {option}")
    return stock.iloc[0]['ID']


def read_options_from_csv(file_path):
    try:
        options_df = pd.read_csv(file_path)
        options_df = options_df.dropna(subset=['Stock'])
        options = options_df['Stock'].astype(str).str.strip().tolist()
        return [option for option in options if option]
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return []
    

app = Flask('Fortel')

@app.route('/', methods=['GET', 'POST'])
def main():
    options = read_options_from_csv('StockSymbols.csv')

    if request.method == 'POST':

        stock_symbol = extract_stock_symbol(request.form.get('options'))
        duration = request.form.get('radio_option')
        stock_data = get_stock_data(stock_symbol)
        filtered_data = filter_stock_data(stock_data, duration)
        stock_plot=stock_plotter(filtered_data, stock_symbol)
        return render_template('index.html', options=options, plot=encode_png(stock_plot))

    return render_template('index.html', options=options)


@app.errorhandler(ValueError)
def bad_request(err):
    # Bad symbol, missing data or too little history: show the message instead of a 500
    return (str(err), 400)

@app.route('/lstm', methods=['GET', 'POST'])
def lstm():
    options = read_options_from_csv('StockSymbols.csv')
    if  request.method == 'POST':
        stock_symbol = extract_stock_symbol(request.form.get('options'))
        stock_data = get_stock_data(stock_symbol)
        lstm_plot=lstm_prediction(pd.DataFrame(stock_data),symbol=stock_symbol)

        return render_template('lstm.html', plot=encode_png(lstm_plot), options=options)

    return render_template('lstm.html', options=options)

@app.route('/gru', methods=['GET', 'POST'])
def gru():
    options = read_options_from_csv('StockSymbols.csv')
    if  request.method == 'POST':
        stock_symbol = extract_stock_symbol(request.form.get('options'))
        stock_data = get_stock_data(stock_symbol)
        gru_plot=gru_prediction(pd.DataFrame(stock_data),symbol=stock_symbol)

        return render_template('gru.html', plot=encode_png(gru_plot), options=options)

    return render_template('gru.html', options=options)

def _send_pdf(filename):
    return send_file(os.path.join(DOCS_DIR, filename), mimetype='application/pdf')

@app.route('/paper')
def paper():
    return _send_pdf('IJARCCE_reserch paper.pdf')

@app.route('/Certificate')
def certificate():
    return render_template('certificates.html')

@app.route('/Certificate/rohan')
def rohan():
    return _send_pdf('Rohan Waghmare.pdf')

@app.route('/Certificate/YC')
def yashC():
    return _send_pdf('Yash Chougale.pdf')

@app.route('/Certificate/YK')
def yashK():
    return _send_pdf('Yash Kashid.pdf')

@app.route('/Certificate/YD')
def yashD():
    return _send_pdf('Yashodhan Darekar.pdf')

@app.route('/Certificate/RR')
def rahulR():
    return _send_pdf('Rahul Rote.pdf')

# Health endpoints used by k8s probes
@app.route('/health')
def health():
    return ('OK', 200)

@app.route('/ready')
def ready():
    # Optionally perform checks (e.g., model file exists) before returning 200
    return ('OK', 200)

if __name__ == "__main__":
    app.run(debug=True)
