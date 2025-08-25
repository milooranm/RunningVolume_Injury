from fastapi import FastAPI, Form, Response
from fastapi.responses import HTMLResponse, StreamingResponse
import pickle
import matplotlib.pyplot as plt
import io
import os
from PIL import Image
from io import BytesIO

from apicall_input import main_api_call 
from data_extraction_v2 import main_extract_transform

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
    with open('..\models\mvp2best_logistic_model.pkl', 'rb') as file:
        model = pickle.load(file)   
    #pipeline steps    
    start_date, end_date, df_memory = main_api_call(email, password)
    df = main_extract_transform(start_date, end_date, df_memory)
    # add the normalisation step
    norm_df= norm_user_data(df)
    # make predictions
    df['injury probabilities'] = model.predict_proba(norm_df)[:, 1]
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
    try:
        # run the full pipeline to get the image
        img =  runitall(email, password)
           
        return StreamingResponse(img, media_type="image/png")
    
    except Exception as e:
        return {"error": str(e)}, 500
