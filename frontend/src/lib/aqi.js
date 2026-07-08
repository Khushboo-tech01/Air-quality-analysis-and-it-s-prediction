export const AQI_LEVELS = [
  { low: 0,   high: 50,  label: "Good",                           color: "#10B981", token: "good" },
  { low: 51,  high: 100, label: "Moderate",                       color: "#F59E0B", token: "moderate" },
  { low: 101, high: 150, label: "Unhealthy for Sensitive Groups", color: "#F97316", token: "usg" },
  { low: 151, high: 200, label: "Unhealthy",                      color: "#EF4444", token: "unhealthy" },
  { low: 201, high: 300, label: "Very Unhealthy",                 color: "#8B5CF6", token: "very" },
  { low: 301, high: 10000, label: "Hazardous",                    color: "#7F1D1D", token: "hazardous" },
];

export function classifyAqi(aqi) {
  const n = Math.max(0, Number(aqi) || 0);
  for (const level of AQI_LEVELS) if (n >= level.low && n <= level.high) return { ...level, value: n };
  return { ...AQI_LEVELS[AQI_LEVELS.length - 1], value: n };
}

export const POLLUTANT_META = {
  pm25:     { label: "PM2.5",       unit: "µg/m³", placeholder: "35",   step: 0.1 },
  pm10:     { label: "PM10",        unit: "µg/m³", placeholder: "80",   step: 0.1 },
  no2:      { label: "NO₂",         unit: "µg/m³", placeholder: "25",   step: 0.1 },
  so2:      { label: "SO₂",         unit: "µg/m³", placeholder: "8",    step: 0.1 },
  co:       { label: "CO",          unit: "mg/m³", placeholder: "0.8",  step: 0.01 },
  o3:       { label: "O₃",          unit: "µg/m³", placeholder: "30",   step: 0.1 },
  temp:     { label: "Temperature", unit: "°C",    placeholder: "26",   step: 0.1 },
  humidity: { label: "Humidity",    unit: "%",     placeholder: "60",   step: 0.1 },
  wind:     { label: "Wind Speed",  unit: "m/s",   placeholder: "3.4",  step: 0.1 },
  pressure: { label: "Pressure",    unit: "hPa",   placeholder: "1010", step: 0.1 },
};

export const POLLUTANT_ORDER = ["pm25", "pm10", "no2", "so2", "co", "o3", "temp", "humidity", "wind", "pressure"];
