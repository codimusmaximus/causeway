"""Simple world map server with SQLite backend."""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
from pathlib import Path

app = FastAPI(title="World Map")
DB_PATH = Path(__file__).parent / "countries.db"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS countries (
            id INTEGER PRIMARY KEY,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            capital TEXT,
            population TEXT,
            region TEXT,
            currency TEXT,
            language TEXT,
            flag TEXT
        )
    """)

    # Seed data if empty
    count = conn.execute("SELECT COUNT(*) FROM countries").fetchone()[0]
    if count == 0:
        countries = [
            ("USA", "United States", "Washington, D.C.", "331 million", "North America", "US Dollar (USD)", "English", "🇺🇸"),
            ("CAN", "Canada", "Ottawa", "38 million", "North America", "Canadian Dollar (CAD)", "English, French", "🇨🇦"),
            ("MEX", "Mexico", "Mexico City", "128 million", "North America", "Mexican Peso (MXN)", "Spanish", "🇲🇽"),
            ("BRA", "Brazil", "Brasília", "214 million", "South America", "Brazilian Real (BRL)", "Portuguese", "🇧🇷"),
            ("ARG", "Argentina", "Buenos Aires", "45 million", "South America", "Argentine Peso (ARS)", "Spanish", "🇦🇷"),
            ("GBR", "United Kingdom", "London", "67 million", "Europe", "Pound Sterling (GBP)", "English", "🇬🇧"),
            ("FRA", "France", "Paris", "67 million", "Europe", "Euro (EUR)", "French", "🇫🇷"),
            ("DEU", "Germany", "Berlin", "83 million", "Europe", "Euro (EUR)", "German", "🇩🇪"),
            ("ITA", "Italy", "Rome", "60 million", "Europe", "Euro (EUR)", "Italian", "🇮🇹"),
            ("ESP", "Spain", "Madrid", "47 million", "Europe", "Euro (EUR)", "Spanish", "🇪🇸"),
            ("PRT", "Portugal", "Lisbon", "10 million", "Europe", "Euro (EUR)", "Portuguese", "🇵🇹"),
            ("NLD", "Netherlands", "Amsterdam", "17 million", "Europe", "Euro (EUR)", "Dutch", "🇳🇱"),
            ("BEL", "Belgium", "Brussels", "11 million", "Europe", "Euro (EUR)", "Dutch, French, German", "🇧🇪"),
            ("CHE", "Switzerland", "Bern", "8.6 million", "Europe", "Swiss Franc (CHF)", "German, French, Italian", "🇨🇭"),
            ("AUT", "Austria", "Vienna", "9 million", "Europe", "Euro (EUR)", "German", "🇦🇹"),
            ("POL", "Poland", "Warsaw", "38 million", "Europe", "Polish Zloty (PLN)", "Polish", "🇵🇱"),
            ("SWE", "Sweden", "Stockholm", "10 million", "Europe", "Swedish Krona (SEK)", "Swedish", "🇸🇪"),
            ("NOR", "Norway", "Oslo", "5.4 million", "Europe", "Norwegian Krone (NOK)", "Norwegian", "🇳🇴"),
            ("DNK", "Denmark", "Copenhagen", "5.8 million", "Europe", "Danish Krone (DKK)", "Danish", "🇩🇰"),
            ("FIN", "Finland", "Helsinki", "5.5 million", "Europe", "Euro (EUR)", "Finnish, Swedish", "🇫🇮"),
            ("RUS", "Russia", "Moscow", "144 million", "Europe/Asia", "Russian Ruble (RUB)", "Russian", "🇷🇺"),
            ("CHN", "China", "Beijing", "1.4 billion", "Asia", "Renminbi (CNY)", "Mandarin Chinese", "🇨🇳"),
            ("JPN", "Japan", "Tokyo", "125 million", "Asia", "Japanese Yen (JPY)", "Japanese", "🇯🇵"),
            ("KOR", "South Korea", "Seoul", "52 million", "Asia", "South Korean Won (KRW)", "Korean", "🇰🇷"),
            ("IND", "India", "New Delhi", "1.4 billion", "Asia", "Indian Rupee (INR)", "Hindi, English", "🇮🇳"),
            ("AUS", "Australia", "Canberra", "26 million", "Oceania", "Australian Dollar (AUD)", "English", "🇦🇺"),
            ("NZL", "New Zealand", "Wellington", "5 million", "Oceania", "New Zealand Dollar (NZD)", "English, Māori", "🇳🇿"),
            ("ZAF", "South Africa", "Pretoria", "60 million", "Africa", "South African Rand (ZAR)", "11 official languages", "🇿🇦"),
            ("EGY", "Egypt", "Cairo", "102 million", "Africa", "Egyptian Pound (EGP)", "Arabic", "🇪🇬"),
            ("NGA", "Nigeria", "Abuja", "211 million", "Africa", "Nigerian Naira (NGN)", "English", "🇳🇬"),
            ("SAU", "Saudi Arabia", "Riyadh", "35 million", "Middle East", "Saudi Riyal (SAR)", "Arabic", "🇸🇦"),
            ("TUR", "Turkey", "Ankara", "84 million", "Europe/Asia", "Turkish Lira (TRY)", "Turkish", "🇹🇷"),
            ("IDN", "Indonesia", "Jakarta", "274 million", "Asia", "Indonesian Rupiah (IDR)", "Indonesian", "🇮🇩"),
            ("THA", "Thailand", "Bangkok", "70 million", "Asia", "Thai Baht (THB)", "Thai", "🇹🇭"),
            ("VNM", "Vietnam", "Hanoi", "98 million", "Asia", "Vietnamese Dong (VND)", "Vietnamese", "🇻🇳"),
            ("PHL", "Philippines", "Manila", "110 million", "Asia", "Philippine Peso (PHP)", "Filipino, English", "🇵🇭"),
            ("MYS", "Malaysia", "Kuala Lumpur", "32 million", "Asia", "Malaysian Ringgit (MYR)", "Malay", "🇲🇾"),
            ("SGP", "Singapore", "Singapore", "5.7 million", "Asia", "Singapore Dollar (SGD)", "English, Malay, Mandarin, Tamil", "🇸🇬"),
            ("GRC", "Greece", "Athens", "10.4 million", "Europe", "Euro (EUR)", "Greek", "🇬🇷"),
            ("IRL", "Ireland", "Dublin", "5 million", "Europe", "Euro (EUR)", "English, Irish", "🇮🇪"),
            ("CZE", "Czech Republic", "Prague", "10.7 million", "Europe", "Czech Koruna (CZK)", "Czech", "🇨🇿"),
            ("HUN", "Hungary", "Budapest", "9.7 million", "Europe", "Hungarian Forint (HUF)", "Hungarian", "🇭🇺"),
            ("ROU", "Romania", "Bucharest", "19 million", "Europe", "Romanian Leu (RON)", "Romanian", "🇷🇴"),
            ("UKR", "Ukraine", "Kyiv", "41 million", "Europe", "Ukrainian Hryvnia (UAH)", "Ukrainian", "🇺🇦"),
            ("COL", "Colombia", "Bogotá", "51 million", "South America", "Colombian Peso (COP)", "Spanish", "🇨🇴"),
            ("PER", "Peru", "Lima", "33 million", "South America", "Peruvian Sol (PEN)", "Spanish", "🇵🇪"),
            ("CHL", "Chile", "Santiago", "19 million", "South America", "Chilean Peso (CLP)", "Spanish", "🇨🇱"),
            ("VEN", "Venezuela", "Caracas", "28 million", "South America", "Venezuelan Bolívar (VES)", "Spanish", "🇻🇪"),
            ("PAK", "Pakistan", "Islamabad", "220 million", "Asia", "Pakistani Rupee (PKR)", "Urdu, English", "🇵🇰"),
            ("BGD", "Bangladesh", "Dhaka", "165 million", "Asia", "Bangladeshi Taka (BDT)", "Bengali", "🇧🇩"),
            ("IRN", "Iran", "Tehran", "84 million", "Middle East", "Iranian Rial (IRR)", "Persian", "🇮🇷"),
            ("IRQ", "Iraq", "Baghdad", "41 million", "Middle East", "Iraqi Dinar (IQD)", "Arabic, Kurdish", "🇮🇶"),
            ("ISR", "Israel", "Jerusalem", "9.2 million", "Middle East", "Israeli Shekel (ILS)", "Hebrew, Arabic", "🇮🇱"),
            ("ARE", "United Arab Emirates", "Abu Dhabi", "10 million", "Middle East", "UAE Dirham (AED)", "Arabic", "🇦🇪"),
            ("KEN", "Kenya", "Nairobi", "54 million", "Africa", "Kenyan Shilling (KES)", "Swahili, English", "🇰🇪"),
            ("ETH", "Ethiopia", "Addis Ababa", "118 million", "Africa", "Ethiopian Birr (ETB)", "Amharic", "🇪🇹"),
            ("MAR", "Morocco", "Rabat", "37 million", "Africa", "Moroccan Dirham (MAD)", "Arabic, Berber", "🇲🇦"),
            ("DZA", "Algeria", "Algiers", "44 million", "Africa", "Algerian Dinar (DZD)", "Arabic", "🇩🇿"),
        ]
        conn.executemany(
            "INSERT INTO countries (code, name, capital, population, region, currency, language, flag) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            countries
        )
    conn.commit()
    conn.close()


@app.on_event("startup")
def startup():
    init_db()


@app.get("/api/countries")
def list_countries():
    conn = get_db()
    rows = conn.execute("SELECT * FROM countries ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/countries/{code}")
def get_country(code: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM countries WHERE code = ?", (code.upper(),)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Country not found")
    return dict(row)


@app.get("/", response_class=FileResponse)
def index():
    return Path(__file__).parent / "world-map.html"


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
