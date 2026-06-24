from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import PolynomialFeatures
from datetime import timedelta

app = FastAPI(title="Tech Resale Predictor API")

# Enable CORS so our frontend can securely communicate with this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection parameters (matching docker-compose.yml)
DB_CONFIG = {
    'dbname': 'resale_predictor',
    'user': 'admin',
    'password': 'password123',
    'host': 'localhost',
    'port': '5432'
}

def get_db_connection():
    # RealDictCursor returns rows as Python dictionaries instead of raw tuples
    return psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)


@app.get("/")
def read_root():
    return {"message": "Welcome to the Tech Resale Predictor API!"}


# Endpoint 1: Fetch all tracked devices
@app.get("/api/devices")
def get_devices():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM devices ORDER BY brand, model;")
        devices = cursor.fetchall()
        return devices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            cursor.close()
            conn.close()


# Endpoint 2: Fetch historical records for a specific device
@app.get("/api/history/{device_id}")
def get_device_history(device_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if device exists
        cursor.execute("SELECT * FROM devices WHERE device_id = %s;", (device_id,))
        device = cursor.fetchone()
        if not device:
            raise HTTPException(status_code=404, detail="Device not found")
        
        # Fetch historical records
        cursor.execute("""
            SELECT record_id, date_recorded, condition, resale_price, data_source 
            FROM historical_prices 
            WHERE device_id = %s 
            ORDER BY date_recorded ASC;
        """, (device_id,))
        history = cursor.fetchall()
        
        return {
            "device": device,
            "price_history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            cursor.close()
            conn.close()


# Endpoint 3: Forecast future depreciation using Machine Learning
@app.get("/api/predict/{device_id}")
def predict_price(device_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Fetch data rows needed for training matching the device ID
        cursor.execute("""
            SELECT date_recorded, resale_price 
            FROM historical_prices 
            WHERE device_id = %s 
            ORDER BY date_recorded ASC;
        """, (device_id,))
        records = cursor.fetchall()
        
        if len(records) < 10:
            raise HTTPException(status_code=400, detail="Not enough data points to train a reliable model.")
            
        # Parse data into a pandas DataFrame
        df = pd.DataFrame(records)
        df['date_recorded'] = pd.to_datetime(df['date_recorded'])
        
        # Convert absolute calendar dates to a continuous numerical feature (days passed)
        first_date = df['date_recorded'].min()
        df['days_passed'] = (df['date_recorded'] - first_date).dt.days
        
        # Isolate target variable and training feature
        X = df[['days_passed']]
        y = df['resale_price']
        
        # Apply polynomial transformation (degree 2)
        poly = PolynomialFeatures(degree=2)
        X_poly = poly.fit_transform(X)
        
        # Fit the scikit-learn linear regression estimator on polynomial features
        model = LinearRegression()
        model.fit(X_poly, y)
        
        # Establish reference metrics for projection offsets
        last_date = df['date_recorded'].max()
        last_days_passed = df['days_passed'].max()
        
        future_intervals = [30, 60, 90]
        predictions = []
        
        for days in future_intervals:
            future_X = pd.DataFrame({'days_passed': [last_days_passed + days]})
            future_X_poly = poly.transform(future_X)
            predicted_price = model.predict(future_X_poly)[0]
            
            predictions.append({
                "days_out": days,
                "target_date": (last_date + timedelta(days=days)).strftime("%Y-%m-%d"),
                "estimated_value": round(max(predicted_price, 0), 2)
            })
            
        return {
            "device_id": device_id,
            "trend": "Depreciating" if model.coef_[0] < 0 else "Appreciating",
            "predictions": predictions
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if conn:
            cursor.close()
            conn.close()