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
def load_image(username: str, password: str):
    if username and password:
        img = Image.open("injury.png")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
    else:
        reutrn None


app = FastAPI(
    title = 'Run injury prediction API',
    description = 'Preddicting injury risk based on GarminConnect running data'
)

@app.get("/")
async def root():
    return {"message": "test for injury_risk_pred is running!"}

# Route: HTML form served directly from Python
@app.get("/", response_class=HTMLResponse)
def login_form():
    html_content = """
    <html>
        <head><title>Login</title></head>
        <body>
            <h2>Please login</h2>
            <form action="/login" method="post">
                <label>Username:</label>
                <input type="text" name="username"><br/>
                <label>Password:</label>
                <input type="password" name="password"><br/>
                <button type="submit">Login</button>
            </form>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)



@app.post("/predict_and_visualize/")
async def predict_and_visualize(username:str = Form(...), password:str = Form(...)):
    """
    perform spoof calculation and return an image
    """
    try:
        # output the number squared
        if username and password:
        # handle the image
            img = load_image()
            
            return StreamingResponse(img, media_type="image/png")
        else:
            return {"error": "Invalid username or password"}, 401
    
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