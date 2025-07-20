from fastapi import FastAPI, Response
from fastapi.responses import StreamingResponse
from fastapi.responses import HTMLResponse

import pickle


from PIL import Image
from io import BytesIO

# import the model
with open('..\models\mvp2best_logistic_model.pkl', 'rb') as file:
    model = pickle.load(file)

# load test image
def load_image():
    img = Image.open("injury.png")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer


app = FastAPI(
    title = 'Run injury prediction API',
    description = 'Preddicting injury risk based on GarminConnect running data'
)

@app.get("/")
async def root():
    return {"message": "test for injury_risk_pred is running!"}

@app.post("/predict_and_visualize/")
async def predict_and_visualize(X:int = 2):
    """
    perform spoof calculation and return an image
    """
    try:
        
        # output the number squared
        X = X * 2

        # handle the image
        img = load_image()
            
        return StreamingResponse(img, media_type="image/png")
    
    except Exception as e:
        return {"error": str(e)}, 500
'''   
@app.get("/view/", response_class=HTMLResponse)
async def view():
    return """
    <html>
        <body>
            <h2>Injury Risk Prediction</h2>
            <div>
                <input type="number" id="x-value" value="2">
                <button onclick="makePrediction()">Predict</button>
            </div>
            <img src="" id="prediction-image">
            
            <script>
                async function makePrediction() {
                    const xValue = document.getElementById('x-value').value;
                    const response = await fetch('/predict_and_visualize/?X=' + xValue, {
                        method: 'POST'
                    });
                    const blob = await response.blob();
                    const img = document.getElementById('prediction-image');
                    img.src = URL.createObjectURL(blob);
                }
            </script>
        </body>
    </html>
    """
'''   