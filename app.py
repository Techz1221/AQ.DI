import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from datetime import datetime, timezone

# ==========================================
# AQ.DI — DISASTER INTELLIGENCE SYSTEM
# ==========================================

st.set_page_config(
    page_title="AQ.DI | Disaster Intelligence",
    page_icon="🌍",
    layout="wide"
)

st.title("🌍 AQ.DI")
st.subheader("Multi-Source Disaster Intelligence System")

st.caption(
    "Semester VII | Big Data Analytics | "
    "Live Public Data Monitoring"
)

st.info(
    "Educational prototype using public weather "
    "and earthquake data. Not an official emergency "
    "warning service."
)

# ==========================================
# API CONFIGURATION
# ==========================================

WEATHER_API = "https://api.open-meteo.com/v1/forecast"

USGS_API = (
    "https://earthquake.usgs.gov/earthquakes/feed/"
    "v1.0/summary/all_day.geojson"
)

HEADERS = {
    "User-Agent": "AQ-DI-Student-Project/1.0"
}

# ==========================================
# LOCATION SELECTION
# ==========================================

locations = {
    "Mumbai": (19.0760, 72.8777),
    "Pune": (18.5204, 73.8567),
    "Nagpur": (21.1458, 79.0882),
    "Delhi": (28.6139, 77.2090),
    "Chennai": (13.0827, 80.2707),
    "Kolkata": (22.5726, 88.3639),
}

st.sidebar.title("Control Panel")

city = st.sidebar.selectbox(
    "Select Weather Location",
    list(locations.keys())
)

latitude, longitude = locations[city]

if st.sidebar.button("Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.caption(
    "Weather and earthquake feeds are retrieved "
    "independently."
)

# ==========================================
# WEATHER DATA COLLECTION
# ==========================================

@st.cache_data(ttl=300)
def get_weather(lat, lon):

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,relative_humidity_2m,"
            "apparent_temperature,precipitation,"
            "rain,wind_speed_10m"
        ),
        "hourly": (
            "temperature_2m,precipitation,"
            "precipitation_probability,wind_speed_10m"
        ),
        "forecast_days": 2,
        "timezone": "Asia/Kolkata"
    }

    response = requests.get(
        WEATHER_API,
        params=params,
        headers=HEADERS,
        timeout=20
    )

    response.raise_for_status()

    data = response.json()

    current = data["current"]
    hourly = data["hourly"]

    forecast = pd.DataFrame({
        "Time": pd.to_datetime(hourly["time"]),
        "Temperature": hourly["temperature_2m"],
        "Rainfall": hourly["precipitation"],
        "Rain_Probability":
            hourly["precipitation_probability"],
        "Wind_Speed": hourly["wind_speed_10m"]
    })

    return current, forecast, data.get("timezone", "")

# ==========================================
# EARTHQUAKE DATA COLLECTION
# ==========================================

@st.cache_data(ttl=300)
def get_earthquakes():

    response = requests.get(
        USGS_API,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    data = response.json()

    records = []

    for feature in data.get("features", []):

        props = feature.get("properties", {})
        geometry = feature.get("geometry") or {}
        coords = geometry.get("coordinates") or []

        if len(coords) < 3:
            continue

        records.append({
            "ID": feature.get("id"),
            "Time": (
                pd.to_datetime(
                    props["time"],
                    unit="ms",
                    utc=True
                )
                if props.get("time") is not None
                else pd.NaT
            ),
            "Magnitude": props.get("mag"),
            "Location": props.get("place"),
            "Longitude": coords[0],
            "Latitude": coords[1],
            "Depth_km": coords[2],
            "URL": props.get("url")
        })

    columns = [
        "ID", "Time", "Magnitude", "Location",
        "Longitude", "Latitude", "Depth_km", "URL"
    ]

    df = pd.DataFrame(records, columns=columns)

    if not df.empty:
        df = df.drop_duplicates(subset=["ID"])
        df = df.sort_values("Time", ascending=False)

    return df

# ==========================================
# FETCH LIVE DATA
# ==========================================

weather = None
forecast = pd.DataFrame()
earthquakes = pd.DataFrame()

weather_error = None
earthquake_error = None

with st.spinner("Retrieving live data..."):

    try:
        weather, forecast, timezone_name = get_weather(
            latitude, longitude
        )
    except Exception as error:
        weather_error = str(error)

    try:
        earthquakes = get_earthquakes()
    except Exception as error:
        earthquake_error = str(error)

# ==========================================
# CONNECTION STATUS
# ==========================================

st.header("Data Source Status")

col1, col2 = st.columns(2)

with col1:
    if weather_error is None:
        st.success("Weather API connected")
    else:
        st.error("Weather API unavailable")

with col2:
    if earthquake_error is None:
        st.success("USGS earthquake feed connected")
    else:
        st.error("USGS earthquake feed unavailable")

# ==========================================
# WEATHER DASHBOARD
# ==========================================

st.header(f"🌦️ Weather Intelligence — {city}")

if weather is not None:

    a, b, c, d = st.columns(4)

    a.metric(
        "Temperature",
        f"{weather.get('temperature_2m', 'N/A')} °C"
    )

    b.metric(
        "Humidity",
        f"{weather.get('relative_humidity_2m', 'N/A')}%"
    )

    c.metric(
        "Rainfall",
        f"{weather.get('precipitation', 'N/A')} mm"
    )

    d.metric(
        "Wind Speed",
        f"{weather.get('wind_speed_10m', 'N/A')} km/h"
    )

    st.caption(
        f"Observation time: {weather.get('time', 'N/A')} "
        f"| Timezone: {timezone_name}"
    )

    st.subheader("Temperature Forecast")

    fig = px.line(
        forecast,
        x="Time",
        y="Temperature",
        markers=True,
        title="Hourly Temperature Forecast"
    )

    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Rainfall Forecast")

    fig = px.bar(
        forecast,
        x="Time",
        y="Rainfall",
        title="Forecast Precipitation"
    )

    st.plotly_chart(fig, use_container_width=True)

else:
    st.warning("Weather information could not be retrieved.")

# ==========================================
# EARTHQUAKE ANALYTICS
# ==========================================

st.header("🌎 Worldwide Earthquake Intelligence")

if earthquake_error is None:

    if earthquakes.empty:

        st.info("No earthquake records returned.")

    else:

        magnitudes = earthquakes["Magnitude"].dropna()

        largest = (
            magnitudes.max()
            if not magnitudes.empty
            else None
        )

        a, b, c = st.columns(3)

        a.metric(
            "Events in Feed",
            len(earthquakes)
        )

        b.metric(
            "Largest Magnitude",
            f"{largest:.1f}" if largest is not None else "N/A"
        )

        b_value = earthquakes["Depth_km"].mean()

        c.metric(
            "Average Depth",
            f"{b_value:.1f} km"
            if pd.notna(b_value)
            else "N/A"
        )

        min_mag = st.slider(
            "Minimum Magnitude",
            min_value=0.0,
            max_value=8.0,
            value=0.0,
            step=0.5
        )

        filtered = earthquakes[
            earthquakes["Magnitude"].notna()
            & (earthquakes["Magnitude"] >= min_mag)
        ].copy()

        st.write(
            f"Events matching filter: {len(filtered)}"
        )

        if not filtered.empty:

            st.subheader("Earthquake Map")

            fig = px.scatter_geo(
                filtered,
                lat="Latitude",
                lon="Longitude",
                color="Magnitude",
                size="Magnitude",
                hover_name="Location",
                hover_data=["Depth_km", "Time"],
                projection="natural earth",
                title="Worldwide Earthquake Locations"
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            st.subheader("Magnitude Distribution")

            fig = px.histogram(
                filtered,
                x="Magnitude",
                nbins=20
            )

            st.plotly_chart(
                fig,
                use_container_width=True
            )

            st.subheader("Latest Earthquake Records")

            st.dataframe(
                filtered[
                    [
                        "Time",
                        "Magnitude",
                        "Location",
                        "Depth_km",
                        "URL"
                    ]
                ],
                use_container_width=True,
                hide_index=True
            )

            csv = filtered.to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                "Download Earthquake CSV",
                data=csv,
                file_name="earthquake_data.csv",
                mime="text/csv"
            )

else:
    st.warning("Earthquake information could not be retrieved.")

# ==========================================
# BDA CONCEPTS
# ==========================================

with st.expander("Big Data Analytics Concepts"):

    st.markdown("""
    - **Data Acquisition:** Retrieve public API data.
    - **Heterogeneous Data:** Process weather JSON
      and earthquake GeoJSON.
    - **ETL:** Extract, transform and prepare records.
    - **Data Preprocessing:** Standardize fields and
      remove duplicate earthquake identifiers.
    - **Multi-Source Analytics:** Present information
      from independent data sources.
    - **Temporal Analytics:** Examine timestamps and
      weather forecasts.
    - **Spatial Analytics:** Visualize event coordinates.
    - **Statistical Analysis:** Calculate event counts,
      magnitudes and depth summaries.
    - **Data Visualization:** Interactive charts and maps.
    - **Periodic Refresh:** Retrieve new API data when
      the application reruns after the cache expires.

    Note: This initial version uses periodic API polling,
    not continuous streaming or distributed Spark processing.
    """)

# ==========================================
# FOOTER
# ==========================================

st.divider()

st.caption(
    "Sources: Open-Meteo and USGS Earthquake Feed. "
    "Data updates depend on source availability. "
    "This project is an educational analytics prototype, "
    "not an official disaster warning system."
)

st.caption(
    "Application check time (UTC): "
    + datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
)