from fastapi import FastAPI, Form, Response
from fastapi.responses import HTMLResponse, StreamingResponse
import pickle
import matplotlib.pyplot as plt
import io
import logging
import time
from PIL import Image
from io import BytesIO

from apicall_input import main_api_call 
from data_extraction_v2 import main_extract_transform

logger = logging.getLogger(__name__)

logger.setLevel(logging.DEBUG)

# Create and configure handlers
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO) # Only show INFO, WARNING, ERROR, and CRITICAL messages in the console

file_handler = logging.FileHandler("app_errors.log")
file_handler.setLevel(logging.ERROR) # Only write ERROR and CRITICAL messages to the file

formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(name)s - %(message)s")
formatter.converter = time.gmtime
# Set the formatter for both handlers
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

def normalize_user(row, mean_df, std_df):
    z = (row - mean_df) / std_df
    return z

def getMeanStd_user(data):
    # drop the date column while the normalisaition is going on
    data_no_date = data.drop(columns =['Date'], errors = 'ignore')
    mean = data_no_date.mean()
    std = data_no_date.std()
    std.replace(to_replace=0.0, value=0.01, inplace=True)
    return mean, std

def norm_user_data(df):
    """
    normalize the user data
    """
    # Get the mean + std dev
    user_test_means, user_test_std = getMeanStd_user(df.copy())
    # Normalize
    user_normalized = df.apply(lambda x: normalize_user(x, user_test_means,user_test_std), axis=1)
    user_normalized = user_normalized.drop(columns=[ 'Date'], errors='ignore')
    return user_normalized

def runitall(email: str, password: str):
    """ 
    run all functions to get the image
            email: str : user email for api call
            password: str : user password for api call
        return: buffer_img : image buffer with the plot
    """
    # import model
    try: 

        with open('mvp2best_logistic_model.pkl', 'rb') as file:
            model = pickle.load(file)
    except FileNotFoundError:
        logger.error("Model file not found. Please ensure 'mvp2best_logistic_model.pkl' is in the 'models' directory.")
        raise
    except Exception as e:
        logger.error(f"An error occurred while loading the model: {e}")
        raise
    logger.info("Model loaded successfully.")

    #pipeline steps
    try:    
        start_date, end_date, df_memory = main_api_call(email, password)
    except Exception as e:
        logger.error(f"An error occurred during the API call: {e}")
        raise
    logger.info("API call completed successfully.")
    try: 
        df = main_extract_transform(start_date, end_date, df_memory)
    except Exception as e:
        logger.error(f"An error occurred during data extraction and transformation: {e}")
        raise
    logger.info("Data extraction and transformation completed successfully.")
    # add the normalisation step
    try:
        norm_df= norm_user_data(df)
    except Exception as e:
        logger.error(f"An error occurred during data normalization: {e}")
        raise
    logger.info("Data normalization completed successfully.")
    # make predictions
    try:
        df['injury probabilities'] = model.predict_proba(norm_df)[:, 1]
    except Exception as e:
        logger.error(f"An error occurred while making predictions on converted data: {e}")
        raise
    logger.info("Predictions made successfully.")
    # plot the probabilities over time with a rolling mean
    plt.figure(figsize=(10,5))
    plt.plot(df['Date'],df['injury probabilities'].rolling(window=3).mean())
    plt.xticks(df['Date'][::5], rotation=45, ha='right')
    # Save to buffer
    buffer_img = io.BytesIO()
    plt.savefig(buffer_img, format="png")
    buffer_img.seek(0)
    plt.close()  # free memory

    return buffer_img

app = FastAPI(
    title = 'Run Injury Prediction API',
    description = 'Predicting injury risk based on GarminConnect running data'
)

# Endpoint to handle form submission and show 'loading'
@app.get("/", response_class=HTMLResponse)
async def login_form():
    html_content = """
    <html>
        <head><title>Injury Risk Prediction</title></head>
        <body>
            <h2>Login to Generate Injury Risk Prediction</h2>
            <form action="/predict_and_visualize/" method="post" onsubmit="showLoading()">
                <label>Email:</label>
                <input type="text" name="email" required><br/>
                <label>Password:</label>
                <input type="password" name="password" required><br/>
                <button type="submit">Generate Prediction</button>
            </form>
            <p id="loading-message" style="display:none;">Processing... Should take about 2 minutes, Please wait.</p>
            <script>
                function showLoading() {
                    document.getElementById('loading-message').style.display = 'block';
                }
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/predict_and_visualize/")
async def predict_and_visualize(email: str = Form(...), password: str = Form(...)):
    """
    perform spoof calculation and return an image
    """
    logger.info("Received request for injury risk prediction.")
    try:
        # run the full pipeline to get the image
        img =  runitall(email, password)
        
        return StreamingResponse(img, media_type="image/png")
        

    
    except Exception as e:
        logger.error(f"An error occurred in the prediction and visualization endpoint: {e}")
        return {"something didn't go quite right with this. Try again to be sure but if no joy send me a quick email at milomoran123@gmail.com and I'll try to figure out what happened": str(e)}, 500
