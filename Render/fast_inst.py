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

def runitall(email: str, password: str, zone3: int , zone5: int ):
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
        df = main_extract_transform(start_date, end_date, df_memory, zone3, zone5)
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
    plt.title('Injury Risk score over time')
    plt.xlabel('Date')
    plt.ylabel('Injury Risk Score (0-1)')
    # add faint horizontal lines at 0.2, 0.4, 0.6, 0.8
    plt.axhline(y=0.2, color='r', linestyle='--', alpha=0.3)
    plt.axhline(y=0.4, color='r', linestyle='--', alpha=0.3)
    plt.axhline(y=0.6, color='r', linestyle='--', alpha=0.3)
    plt.axhline(y=0.8, color='r', linestyle='--', alpha=0.3)    

    plt.plot(df['Date'],df['injury probabilities'])#.rolling(window=3).mean())
    plt.xticks(df['Date'][::5], rotation=45, ha='right')
    plt.ylim(0, 1)
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
            <h2>Login with Your Garmin Credentials to Generate Injury Risk Prediction</h2>
            <p style="max-width:600px; font-size:14px; color:#333;">
                This tool connects to your Garmin data and uses your training history combined with a machine learning model 
                to produce a visualisation of your short-term injury risk trends. 
                Your credentials are only used in memory during processing and are not stored.
            </p>
            <form action="/predict_and_visualize/" method="post" onsubmit="showLoading()">
                <label> User Email:</label>
                <input type="text" name="email" required><br/>
                <label>GarminConnect Password:</label>
                <input type="password" name="password" required><br/>
                <label>Zone 3 Threshold Heart Rate:</label>
                <input type="range" name="zone3" min="100" max="200" value="150" 
                       oninput="document.getElementById('z3val').innerText = this.value">
                <span id="z3val">150</span><br/><br/>

                <label>Zone 5 Threshold Heart Rate:</label>
                <input type="range" name="zone5" min="100" max="200" value="180" 
                       oninput="document.getElementById('z5val').innerText = this.value">
                <span id="z5val">180</span><br/><br/>
                <button type="submit">Generate Prediction</button>
            </form>
            <p style="max-width:600px; font-size:14px; color:#333;">
                So the goal of this tool is to improve on the common reccomendations of 
                "10percent increase in training load per week"
                as a primary load management tool.<br/>
                The model does this by taking into account both your recent acute training history in 
                the most recent week as well as your 'form' for the past three weeks. <br/>
                The model looks at not only your total training volume but also the intensity 
                of that training, with heart rate zones as a proxy for intensity.<br/>
                The model is trained on a large dataset of running training logs and injury records, 
                and is able to identify patterns that are associated with increased injury risk. <br/>
                The output is a risk score between 0 and 1, with higher scores indicating a higher risk. <br/>
                Calibrating the model is particularly difficult, as I can't exactly tell a load of 
                people to go out and train harder until they get injured. <br/>
                From what I can tell of looking at outputs from my people who have tested the tool, a score below 0.6 
                seems to be a low risk of injury, and scores above .7 would warrant a bit of extra caution.
                What I would like for users to do is take a look at the trends: Is your risk score
                  increasing for the past few days, is it largely stable, or just fluctuating a little? 
                  Either steady or rapid increases are probably cause for concern <br/>
                The model can be used as a guide to help you make informed decisions about your training.
                <br/>Please note that this tool is not a substitute for professional medical advice.
                <br/><br/>               

            
                
            </p>
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
async def predict_and_visualize(email: str = Form(...), password: str = Form(...), zone3: int = Form(...), zone5: int = Form(...)):
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
