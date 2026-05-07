# "NFC quality weather forecast.py"
# CUSTOMIZATION GUIDE (line numbers are estimates and may shift slightly):
# - Latitude/Longitude: around lines ~16-17 (LATITUDE / LONGITUDE)
# - Factor Weighting: around lines ~121-137 inside __init__ (self.weights = {...})
import os
import json
import requests
from datetime import datetime, timedelta, date
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Any
from zoneinfo import ZoneInfo

# ===== LOCALIZATION SETTINGS =====
# Replace these values with your own coordinates.
# Latitude: positive north, negative south
# Longitude: negative west, positive east
LATITUDE = 42.4206345
LONGITUDE = -71.1804986


@dataclass
class WeatherMetrics:
	timestamp: datetime
	temp: float  # Celsius
	humidity: int  # %

	# API/model values at 10m + derived estimate at ~2m
	wind_speed_10m: float  # m/s
	gust_speed_10m: float  # m/s
	wind_speed_ground: float  # m/s
	gust_speed_ground: float  # m/s

	cloud_cover: int  # %
	precipitation: float  # mm
	pressure: float  # hPa
	visibility: float  # meters (API value if available; fallback estimate otherwise)
	visibility_is_estimated: bool

	conditions: str
	is_historical: bool = False


@dataclass
class AcousticScore:
	overall_score: float  # 0-100 internal
	factors: Dict[str, Tuple[float, str]]  # factor -> (0-100 score, explanation)
	recommendation: str
	best_hours: List[int]


class NocturnalRecordingForecast:
	"""
	Analyze weather conditions for nocturnal audio recording quality.
	"""

	def __init__(self, location: Tuple[float, float]):
		self.lat, self.lon = location

		self.forecast_url = "https://api.open-meteo.com/v1/forecast"
		self.historical_url = "https://archive-api.open-meteo.com/v1/archive"
		self.sun_api_url = "https://api.sunrise-sunset.org/json"

		# Reverse geocoding sources
		self.fcc_geo_url = "https://geo.fcc.gov/api/census/block/find"
		self.nominatim_reverse_url = "https://nominatim.openstreetmap.org/reverse"

		self.model_version = "1.5.0"

		self.timezone_name = self._detect_timezone_name()
		self.local_tz = ZoneInfo(self.timezone_name)
		self.region_state_name = self._detect_region_state_name()

		self.twilight_cache: Dict[date, Dict[str, datetime]] = {}
		self.night_window_cache: Dict[date, Tuple[datetime, datetime]] = {}

		# Wind profile settings
		self.reference_wind_height_m = 10.0
		self.target_wind_height_m = 2.0
		self.wind_shear_exponent = 0.20

		self.thresholds = {
			"wind_ideal": 2.0,
			"wind_max": 8.0,
			"humidity_optimal_low": 68,
			"humidity_optimal_high": 75,
			"humidity_good_high": 85,
			"visibility_excellent": 8000,
			"visibility_min": 4000,
			"gust_max": 22.4,
			"pressure_high": 1015,
		}

		# ===== Factor weighting customization area =====
		# Precipitation is second-highest after wind because direct precipitation noise
		# can strongly mask flight calls and reduce usable recordings.
		self.weights = {
			"Surface Wind": 0.34,
			"Precipitation": 0.24,
			"Humidity": 0.14,
			"Visibility": 0.12,
			"Cloud Cover": 0.08,
			"Pressure": 0.06,
			"Temperature": 0.02,
		}

		self.weight_rationale = {
			"Surface Wind": "wind noise can mask calls",
			"Precipitation": "rain/sleet noise can directly mask calls",
			"Humidity": "affects sound absorption",
			"Visibility": "general proxy for atmospheric clarity",
			"Cloud Cover": "may influence sound confinement",
			"Pressure": "broad indicator of overnight stability",
			"Temperature": "can affect mixing and stability",
		}

		self.main_concern_hint = {
			"Surface Wind": "wind noise risk",
			"Precipitation": "rain noise risk",
			"Humidity": "sound absorption risk",
			"Visibility": "clarity/attenuation risk",
			"Cloud Cover": "less favorable sound confinement pattern",
			"Pressure": "less stable atmosphere may scatter and weaken distant calls",
			"Temperature": "mixing/stability risk",
		}

	# ----------------------------
	# Location + timezone helpers
	# ----------------------------

	def _fallback_location_text(self) -> str:
		return f"{self.lat:.4f}, {self.lon:.4f}"

	def _location_header_text(self) -> str:
		fallback = self._fallback_location_text()
		coords_text = f"{self.lat}°, {self.lon}°"
		if self.region_state_name == fallback:
			return coords_text
		return f"{self.region_state_name} | {coords_text}"

	def _detect_timezone_name(self) -> str:
		params = {
			"latitude": self.lat,
			"longitude": self.lon,
			"current": "temperature_2m",
			"timezone": "auto",
		}
		try:
			r = requests.get(self.forecast_url, params=params, timeout=15)
			r.raise_for_status()
			tz_name = r.json().get("timezone")
			if tz_name:
				return tz_name
		except requests.exceptions.RequestException:
			pass
		return "America/New_York"

	def _detect_region_state_name_fcc(self) -> Optional[str]:
		"""
		First choice for U.S. coordinates: FCC Census API.
		Good for county + state in the U.S.
		"""
		params = {
			"latitude": self.lat,
			"longitude": self.lon,
			"format": "json",
		}
		try:
			r = requests.get(self.fcc_geo_url, params=params, timeout=15)
			r.raise_for_status()
			data = r.json()

			county = (data.get("County") or {}).get("name")
			state = (data.get("State") or {}).get("name")

			if county and state:
				return f"{county}, {state}"
			if state:
				return state
			if county:
				return county
			return None
		except requests.exceptions.RequestException:
			return None

	def _detect_region_state_name_nominatim(self) -> Optional[str]:
		"""
		Fallback global reverse geocoder: OpenStreetMap Nominatim.
		Attempts to return County/Region + State/Province.
		"""
		params = {
			"lat": self.lat,
			"lon": self.lon,
			"format": "jsonv2",
			"addressdetails": 1,
			"zoom": 10,
		}
		headers = {"User-Agent": f"NocturnalRecordingForecast/{self.model_version}"}

		try:
			r = requests.get(self.nominatim_reverse_url, params=params, headers=headers, timeout=20)
			r.raise_for_status()
			data = r.json()
			address = data.get("address", {})

			region = (
				address.get("county")
				or address.get("state_district")
				or address.get("region")
				or address.get("municipality")
			)
			state = (
				address.get("state")
				or address.get("province")
				or address.get("territory")
			)

			if region and state:
				return f"{region}, {state}"
			if state:
				return state
			if region:
				return region
			return None
		except requests.exceptions.RequestException:
			return None

	def _detect_region_state_name(self) -> str:
		"""
		Three-step region lookup:
		1. FCC (best for U.S. county/state)
		2. Nominatim
		3. Fallback to coordinates
		"""
		fcc_name = self._detect_region_state_name_fcc()
		if fcc_name:
			return fcc_name

		nominatim_name = self._detect_region_state_name_nominatim()
		if nominatim_name:
			return nominatim_name

		return self._fallback_location_text()

	def _filename_location_fragment(self) -> str:
		fallback = self._fallback_location_text()
		if self.region_state_name and self.region_state_name != fallback:
			return self.region_state_name
		return fallback

	def _sanitize_filename_fragment(self, text: str) -> str:
		"""
		Keep spaces, but remove characters problematic on common filesystems.
		"""
		forbidden = '<>:"/\\|?*'
		cleaned = "".join("-" if c in forbidden else c for c in text)
		cleaned = " ".join(cleaned.split())
		cleaned = cleaned.strip().strip(".")
		return cleaned or "Unknown location"

	def build_output_basename(self, forecast_nights: Optional[List[Dict]] = None) -> str:
		if forecast_nights is None:
			forecast_nights = self.get_best_nights(days_ahead=3)

		if forecast_nights:
			date_fragment = forecast_nights[0]["twilight_start"].strftime("%Y-%m-%d")
		else:
			date_fragment = date.today().isoformat()

		location_fragment = self._sanitize_filename_fragment(self._filename_location_fragment())
		return f"Recording forecasts - {location_fragment} - {date_fragment}"

	# ----------------------------
	# Formatting + display helpers
	# ----------------------------

	def _round_to_half(self, x: float) -> float:
		return round(x * 2) / 2

	def score_100_to_10(self, score_100: float) -> float:
		return self._round_to_half(score_100 / 10.0)

	def format_score_10(self, score_100: float) -> str:
		val = self.score_100_to_10(score_100)
		return "10/10" if abs(val - 10.0) < 1e-9 else f"{val:.1f}/10"

	def _stars(self, filled: int) -> str:
		filled = max(1, min(5, filled))
		return "⭐" * filled + "⭐︎" * (5 - filled)

	def _tier_from_score(self, overall_100: float) -> int:
		if overall_100 >= 90:
			return 5
		if overall_100 >= 80:
			return 4
		if overall_100 >= 70:
			return 3
		if overall_100 >= 60:
			return 2
		return 1

	def _format_factor_list(self, factors: List[str]) -> str:
		if not factors:
			return "minor factors"
		if len(factors) == 1:
			return factors[0]
		if len(factors) == 2:
			return f"{factors[0]} and {factors[1]}"
		return ", ".join(factors[:-1]) + f", and {factors[-1]}"

	def _top_limiting_factors_from_factors(
		self,
		factors: Dict[str, Tuple[float, str]],
		max_n: int = 2
	) -> List[str]:
		"""
		Limiting factor importance = weighted penalty:
			penalty = (100 - factor_score) * factor_weight
		"""
		penalties: List[Tuple[str, float]] = []
		for factor_name in self.weights:
			score = factors.get(factor_name, (100.0, ""))[0]
			penalty = (100.0 - score) * self.weights[factor_name]
			penalties.append((factor_name, penalty))

		penalties.sort(key=lambda x: x[1], reverse=True)

		# Keep positive penalties; fallback to top factor even if tiny
		positive = [f for f, p in penalties if p > 0.1]
		if not positive:
			return [penalties[0][0]] if penalties else []

		return positive[:max_n]

	def _recommendation_lines_from_score_and_factors(
		self,
		overall_100: float,
		factors: Dict[str, Tuple[float, str]],
	) -> Tuple[str, str]:
		tier = self._tier_from_score(overall_100)
		stars = self._stars(tier)
		limiting_1 = self._top_limiting_factors_from_factors(factors, max_n=1)
		limiting_2 = self._top_limiting_factors_from_factors(factors, max_n=2)

		if tier == 5:
			text = "IDEAL - Expect clean audio for most or all of the night"
		elif tier == 4:
			text = f"EXCELLENT - Expect clean audio for much of the night, limited only by {self._format_factor_list(limiting_1)}"
		elif tier == 3:
			text = f"FAIR - {self._format_factor_list(limiting_2)} will limit quality for much of the night"
		elif tier == 2:
			text = f"POOR - Recording quality will be severely affected by {self._format_factor_list(limiting_2)}"
		else:
			text = "UNACCEPTABLE - Expect only noise"

		return stars, text

	def _recommendation_lines_for_night(self, night: Dict) -> Tuple[str, str]:
		# Build factor-like dict from night-level factor averages
		factor_avgs = self._factor_averages_for_night(night)
		factor_dict = {k: (factor_avgs.get(k, 100.0), "") for k in self.weights}
		return self._recommendation_lines_from_score_and_factors(night["average_score"], factor_dict)

	def _recommendation_flag(self, overall_100: float) -> str:
		if overall_100 >= 75:
			return "Yes"
		if overall_100 >= 60:
			return "Borderline"
		return "No"

	def _forecast_night_label(self, idx: int) -> str:
		if idx == 1:
			return "Tonight"
		if idx == 2:
			return "Tomorrow Night"
		if idx == 3:
			return "Night Three"
		return f"Night {idx}"

	def _historical_night_label(self, idx: int) -> str:
		if idx == 1:
			return "Last Night"
		if idx == 2:
			return "Two Nights Ago"
		if idx == 3:
			return "Three Nights Ago"
		return f"{idx} Nights Ago"

	def _format_range(self, values: List[float], decimals: int = 0) -> str:
		lo = round(min(values), decimals)
		hi = round(max(values), decimals)
		if decimals == 0:
			lo_s, hi_s = f"{int(lo)}", f"{int(hi)}"
		else:
			lo_s, hi_s = f"{lo:.{decimals}f}", f"{hi:.{decimals}f}"
		return lo_s if lo == hi else f"{lo_s}-{hi_s}"

	# ----------------------------
	# Unit conversions
	# ----------------------------

	def mps_to_mph(self, mps: float) -> float:
		return mps * 2.237

	def meters_to_miles(self, meters: float) -> float:
		return meters * 0.000621371

	def celsius_to_fahrenheit(self, celsius: float) -> float:
		return (celsius * 9 / 5) + 32

	def mm_to_inches(self, mm: float) -> float:
		return mm / 25.4

	def _wind_to_mps(self, value: float, unit: str) -> float:
		if value is None:
			return 0.0
		u = (unit or "").strip().lower().replace(" ", "")
		if u in ("m/s", "ms", ""):
			return float(value)
		if u in ("km/h", "kmh"):
			return float(value) / 3.6
		if u == "mph":
			return float(value) * 0.44704
		if u in ("kn", "kt", "knot", "knots"):
			return float(value) * 0.514444
		return float(value)

	# ----------------------------
	# Qualitative descriptors
	# ----------------------------

	def _label_span(self, labels: List[str], ordered_labels: List[str]) -> str:
		idx = {label: i for i, label in enumerate(ordered_labels)}
		present = sorted({idx[l] for l in labels if l in idx})
		if not present:
			return "Variable"
		if len(present) == 1:
			return ordered_labels[present[0]]
		return f"{ordered_labels[present[0]]} to {ordered_labels[present[-1]]}"

	def _count_transitions(self, labels: List[str]) -> int:
		if not labels:
			return 0
		return sum(1 for a, b in zip(labels, labels[1:]) if a != b)

	def _humidity_label(self, rh: int) -> str:
		if rh >= 90:
			return "Very humid"
		if rh >= 80:
			return "Humid"
		if rh >= 65:
			return "Moderate"
		return "Dry"

	def _visibility_label_and_tip(self, miles: float) -> Tuple[str, str]:
		if miles >= 6.0:
			return "Clear", "excellent clarity and distance"
		if miles >= 3.0:
			return "Good", "good clarity for most recordings"
		if miles >= 1.5:
			return "Limited", "some attenuation; prioritize nearby sounds"
		return "Poor", "significant attenuation; recording quality likely reduced"

	def _cloud_label(self, cloud_pct: int) -> str:
		if cloud_pct < 20:
			return "clear"
		if cloud_pct < 50:
			return "partly cloudy"
		if cloud_pct < 80:
			return "mostly cloudy"
		return "overcast"

	def _pressure_description(self, pressure_vals: List[float]) -> str:
		"""
		'Steady' = small net change across the night.
		'Very stable' = small total overnight range.
		"""
		avg = sum(pressure_vals) / len(pressure_vals)
		delta = pressure_vals[-1] - pressure_vals[0]
		span = max(pressure_vals) - min(pressure_vals)

		level = "High pressure" if avg >= 1022 else "Moderate pressure" if avg >= 1010 else "Low pressure"
		trend = "rising" if delta >= 1.5 else "falling" if delta <= -1.5 else "steady"
		variability = (
			"very stable overnight"
			if span <= 1.5
			else "fairly stable overnight"
			if span <= 3.5
			else "more variable overnight"
		)
		return (
			f"{level}, {trend}, {variability} "
			f"({min(pressure_vals):.1f}-{max(pressure_vals):.1f} hPa; net {delta:+.1f} hPa)"
		)

	# ----------------------------
	# Twilight logic
	# ----------------------------

	def _parse_iso_to_local_naive(self, iso_str: str) -> datetime:
		if iso_str.endswith("Z"):
			iso_str = iso_str.replace("Z", "+00:00")
		dt = datetime.fromisoformat(iso_str)
		return dt.astimezone(self.local_tz).replace(tzinfo=None) if dt.tzinfo else dt

	def _fallback_twilight_for_date(self, d: date) -> Dict[str, datetime]:
		return {
			"dawn": datetime(d.year, d.month, d.day, 5, 30),
			"dusk": datetime(d.year, d.month, d.day, 20, 0),
		}

	def _get_twilight_for_date(self, d: date) -> Dict[str, datetime]:
		if d in self.twilight_cache:
			return self.twilight_cache[d]

		params = {"lat": self.lat, "lng": self.lon, "date": d.isoformat(), "formatted": 0}
		try:
			r = requests.get(self.sun_api_url, params=params, timeout=20)
			r.raise_for_status()
			payload = r.json()

			if payload.get("status") != "OK":
				tw = self._fallback_twilight_for_date(d)
			else:
				results = payload.get("results", {})
				dawn_iso = results.get("astronomical_twilight_begin")
				dusk_iso = results.get("astronomical_twilight_end")
				if not dawn_iso or not dusk_iso:
					tw = self._fallback_twilight_for_date(d)
				else:
					tw = {
						"dawn": self._parse_iso_to_local_naive(dawn_iso),
						"dusk": self._parse_iso_to_local_naive(dusk_iso),
					}
		except requests.exceptions.RequestException:
			tw = self._fallback_twilight_for_date(d)

		self.twilight_cache[d] = tw
		return tw

	def _floor_hour(self, dt: datetime) -> datetime:
		return dt.replace(minute=0, second=0, microsecond=0)

	def _twilight_window_for_evening(self, evening_date: date) -> Tuple[datetime, datetime]:
		if evening_date in self.night_window_cache:
			return self.night_window_cache[evening_date]

		dusk = self._get_twilight_for_date(evening_date)["dusk"]
		dawn_next = self._get_twilight_for_date(evening_date + timedelta(days=1))["dawn"]
		start = self._floor_hour(dusk)
		end = self._floor_hour(dawn_next)
		if end <= start:
			end = datetime.combine(evening_date + timedelta(days=1), datetime.min.time()).replace(hour=5)

		self.night_window_cache[evening_date] = (start, end)
		return start, end

	def _metric_to_night_key(self, ts: datetime) -> Optional[date]:
		for eve in [ts.date(), ts.date() - timedelta(days=1)]:
			start, end = self._twilight_window_for_evening(eve)
			if start <= ts <= end:
				return eve
		return None

	# ----------------------------
	# Wind handling
	# ----------------------------

	def _sanitize_gust(self, wind_speed_mps: float, gust_speed_mps: float) -> float:
		max_reasonable_gust = 22.4
		gust_multiplier_max = 2.0
		if not gust_speed_mps or gust_speed_mps == 0:
			return wind_speed_mps
		if gust_speed_mps > max_reasonable_gust:
			return max_reasonable_gust
		if wind_speed_mps > 0 and gust_speed_mps > wind_speed_mps * gust_multiplier_max:
			return wind_speed_mps * gust_multiplier_max
		return gust_speed_mps

	def _estimate_ground_wind(self, wind_speed_10m_mps: float) -> float:
		if wind_speed_10m_mps <= 0:
			return 0.0
		factor = (self.target_wind_height_m / self.reference_wind_height_m) ** self.wind_shear_exponent
		est = wind_speed_10m_mps * factor
		return max(0.0, min(est, wind_speed_10m_mps))

	# ----------------------------
	# API fetch + normalize
	# ----------------------------

	def _estimate_visibility(self, precipitation_mm: float, cloud_cover_pct: int) -> float:
		if precipitation_mm > 2:
			return 3000.0
		if precipitation_mm > 0.5:
			return 5000.0
		if cloud_cover_pct > 80:
			return 7000.0
		return 10000.0

	def _request_open_meteo_json(self, url: str, params: Dict) -> Dict:
		try:
			r = requests.get(url, params=params, timeout=30)
			r.raise_for_status()
			return r.json()
		except requests.exceptions.HTTPError as e:
			status = e.response.status_code if e.response is not None else None
			hourly = params.get("hourly", "")
			if status == 400 and "visibility" in hourly:
				fallback = params.copy()
				fallback["hourly"] = ",".join(
					[v.strip() for v in hourly.split(",") if v.strip() != "visibility"]
				)
				r2 = requests.get(url, params=fallback, timeout=30)
				r2.raise_for_status()
				return r2.json()
			raise

	def _parse_hourly_payload(self, data: Dict, is_historical: bool) -> List[WeatherMetrics]:
		hourly = data.get("hourly", {})
		units = data.get("hourly_units", {})

		times = hourly.get("time", [])
		temps = hourly.get("temperature_2m", [])
		humidity = hourly.get("relative_humidity_2m", [])
		wind_10m = hourly.get("wind_speed_10m", [])
		gust_10m = hourly.get("wind_gusts_10m", [])
		cloud_cover = hourly.get("cloud_cover", [])
		precipitation = hourly.get("precipitation", [])
		pressure = hourly.get("surface_pressure", [])
		visibility = hourly.get("visibility", [])

		wind_unit = units.get("wind_speed_10m", "m/s")
		gust_unit = units.get("wind_gusts_10m", wind_unit)

		out: List[WeatherMetrics] = []
		for i, time_str in enumerate(times):
			ts = datetime.fromisoformat(time_str)

			t = float(temps[i]) if i < len(temps) and temps[i] is not None else 0.0
			rh = int(humidity[i]) if i < len(humidity) and humidity[i] is not None else 0

			w10_raw = float(wind_10m[i]) if i < len(wind_10m) and wind_10m[i] is not None else 0.0
			g10_raw = float(gust_10m[i]) if i < len(gust_10m) and gust_10m[i] is not None else 0.0
			w10_mps = self._wind_to_mps(w10_raw, wind_unit)
			g10_mps = self._sanitize_gust(w10_mps, self._wind_to_mps(g10_raw, gust_unit))

			w_ground = self._estimate_ground_wind(w10_mps)
			g_ground = self._sanitize_gust(w_ground, self._estimate_ground_wind(g10_mps))

			cc = int(cloud_cover[i]) if i < len(cloud_cover) and cloud_cover[i] is not None else 0
			pcp = float(precipitation[i]) if i < len(precipitation) and precipitation[i] is not None else 0.0
			prs = float(pressure[i]) if i < len(pressure) and pressure[i] is not None else 1013.0

			if i < len(visibility) and visibility[i] is not None:
				vis, vis_est = float(visibility[i]), False
			else:
				vis, vis_est = self._estimate_visibility(pcp, cc), True

			cond = "Clear" if cc < 20 else "Cloudy" if cc < 80 else "Overcast"

			out.append(
				WeatherMetrics(
					timestamp=ts,
					temp=t,
					humidity=rh,
					wind_speed_10m=w10_mps,
					gust_speed_10m=g10_mps,
					wind_speed_ground=w_ground,
					gust_speed_ground=g_ground,
					cloud_cover=cc,
					precipitation=pcp,
					pressure=prs,
					visibility=vis,
					visibility_is_estimated=vis_est,
					conditions=cond,
					is_historical=is_historical,
				)
			)
		return out

	def fetch_forecast(self) -> List[WeatherMetrics]:
		params = {
			"latitude": self.lat,
			"longitude": self.lon,
			"hourly": (
				"temperature_2m,relative_humidity_2m,wind_speed_10m,wind_gusts_10m,"
				"cloud_cover,precipitation,surface_pressure,visibility"
			),
			"timezone": self.timezone_name,
			"forecast_days": 3,
			"windspeed_unit": "ms",
			"models": "best_match",
		}
		try:
			return self._parse_hourly_payload(self._request_open_meteo_json(self.forecast_url, params), False)
		except requests.exceptions.RequestException as e:
			print(f"Error fetching forecast data: {e}")
			return []

	def fetch_historical(self, days_back: int = 3) -> List[WeatherMetrics]:
		end_date = date.today() - timedelta(days=1)
		start_date = end_date - timedelta(days=days_back - 1)
		params = {
			"latitude": self.lat,
			"longitude": self.lon,
			"start_date": start_date.isoformat(),
			"end_date": end_date.isoformat(),
			"hourly": (
				"temperature_2m,relative_humidity_2m,wind_speed_10m,wind_gusts_10m,"
				"cloud_cover,precipitation,surface_pressure,visibility"
			),
			"timezone": self.timezone_name,
			"windspeed_unit": "ms",
		}
		try:
			return self._parse_hourly_payload(self._request_open_meteo_json(self.historical_url, params), True)
		except requests.exceptions.RequestException as e:
			print(f"Error fetching historical data: {e}")
			return []

	# ----------------------------
	# Factor scoring
	# ----------------------------

	def score_wind(
		self,
		wind_ground_mps: float,
		gust_ground_mps: float,
		wind_10m_mps: float,
		gust_10m_mps: float,
	) -> Tuple[float, str]:
		wind_mph = self.mps_to_mph(wind_ground_mps)
		gust_mph = self.mps_to_mph(gust_ground_mps)
		wind10_mph = self.mps_to_mph(wind_10m_mps)
		gust10_mph = self.mps_to_mph(gust_10m_mps)

		if wind_ground_mps < 1.5:
			score = 100
			explanation = f"Perfect - near-silent ({wind_mph:.1f} mph; {wind10_mph:.1f} mph @10m)"
		elif wind_ground_mps < 3:
			score = 95
			explanation = f"Excellent - very calm ({wind_mph:.1f} mph; {wind10_mph:.1f} mph @10m)"
		elif wind_ground_mps < 4.5:
			score = 85
			explanation = f"Very good - light breeze ({wind_mph:.1f} mph; {wind10_mph:.1f} mph @10m)"
		elif wind_ground_mps < 6:
			score = 70
			explanation = f"Good - moderate wind ({wind_mph:.1f} mph; {wind10_mph:.1f} mph @10m)"
		elif wind_ground_mps < 8:
			score = 45
			explanation = f"Fair - windy ({wind_mph:.1f} mph; {wind10_mph:.1f} mph @10m)"
		else:
			score = 10
			explanation = f"Poor - heavy wind ({wind_mph:.1f} mph; {wind10_mph:.1f} mph @10m)"

		if gust_ground_mps >= 22.4:
			score *= 0.6
			explanation += " (gusts 50+ mph)"
		elif gust_ground_mps > 7:
			score *= 0.8
			explanation += f" (gusts {gust_mph:.1f} mph; {gust10_mph:.1f} mph @10m)"
		return score, explanation

	def score_humidity(self, humidity: int) -> Tuple[float, str]:
		lo = self.thresholds["humidity_optimal_low"]
		hi = self.thresholds["humidity_optimal_high"]
		good_hi = self.thresholds["humidity_good_high"]

		if lo <= humidity <= hi:
			return 95, f"Excellent - optimal humidity ({humidity}% RH)"
		if hi < humidity <= good_hi:
			return 95 - ((humidity - hi) * 1.5), f"Very good - acceptable humidity ({humidity}% RH)"
		if good_hi < humidity <= 92:
			return 75 - ((humidity - good_hi) * 1.5), f"Fair - humid ({humidity}% RH)"
		if humidity > 92:
			return 40, f"Poor - very humid ({humidity}% RH)"
		return 60, f"Poor - unusually dry ({humidity}% RH)"

	def score_visibility(self, visibility_meters: float) -> Tuple[float, str]:
		vm = self.meters_to_miles(visibility_meters)
		if visibility_meters >= 10000:
			return 95, f"Excellent - clear visibility ({vm:.1f} mi)"
		if visibility_meters >= 8000:
			return 90, f"Very good - excellent visibility ({vm:.1f} mi)"
		if visibility_meters >= 6000:
			return 80, f"Good - clear conditions ({vm:.1f} mi)"
		if visibility_meters >= 4000:
			return 65, f"Fair - some haze ({vm:.1f} mi)"
		if visibility_meters >= 2000:
			return 40, f"Poor - limited visibility ({vm:.1f} mi)"
		return 10, f"Very poor - fog/haze ({vm:.1f} mi)"

	def score_cloud_cover(self, cloud_cover: int) -> Tuple[float, str]:
		if cloud_cover >= 80:
			return 95, f"Excellent - heavy overcast ({cloud_cover}%)"
		if cloud_cover >= 70:
			return 92, f"Excellent - mostly cloudy ({cloud_cover}%)"
		if cloud_cover >= 50:
			return 85, f"Very good - broken clouds ({cloud_cover}%)"
		if cloud_cover >= 30:
			return 75, f"Good - partly cloudy ({cloud_cover}%)"
		if cloud_cover >= 10:
			return 65, f"Fair - mostly clear ({cloud_cover}%)"
		return 55, f"Fair - clear sky ({cloud_cover}%)"

	def score_pressure(self, pressure: float) -> Tuple[float, str]:
		if pressure >= 1025:
			return 100, f"Perfect - very high pressure ({pressure:.1f} hPa)"
		if pressure >= 1020:
			return 95, f"Excellent - high pressure ({pressure:.1f} hPa)"
		if pressure >= 1015:
			return 88, f"Very good - elevated pressure ({pressure:.1f} hPa)"
		if pressure >= 1010:
			return 75, f"Good - moderate pressure ({pressure:.1f} hPa)"
		if pressure >= 1005:
			return 55, f"Fair - low pressure ({pressure:.1f} hPa)"
		return 30, f"Poor - very low pressure ({pressure:.1f} hPa)"

	def score_precipitation(self, precip: float) -> Tuple[float, str]:
		p_in = self.mm_to_inches(precip)
		if precip == 0:
			return 100, "Perfect - no precipitation"
		if precip < 0.5:
			return 85, f"Very good - trace/light precipitation ({p_in:.2f} in)"
		if precip < 1:
			return 70, f"Good - light rain ({p_in:.2f} in)"
		if precip < 3:
			return 45, f"Fair - moderate rain ({p_in:.2f} in)"
		return 15, f"Poor - heavy rain ({p_in:.2f} in)"

	def score_temperature_stability(self, temp: float) -> Tuple[float, str]:
		tf = self.celsius_to_fahrenheit(temp)
		if 5 <= temp <= 15:
			return 90, f"Excellent - cool/moderate ({tf:.0f}°F)"
		if 3 <= temp < 5 or 15 < temp <= 20:
			return 85, f"Very good - stable-friendly ({tf:.0f}°F)"
		if 0 <= temp < 3 or 20 < temp <= 25:
			return 75, f"Good - acceptable ({tf:.0f}°F)"
		if 25 < temp <= 28:
			return 55, f"Fair - warm/less stable ({tf:.0f}°F)"
		return 40, f"Poor - {'very cold' if temp < 0 else 'hot'} ({tf:.0f}°F)"

	def analyze_forecast(self, weather: WeatherMetrics) -> AcousticScore:
		factors = {
			"Surface Wind": self.score_wind(
				weather.wind_speed_ground,
				weather.gust_speed_ground,
				weather.wind_speed_10m,
				weather.gust_speed_10m,
			),
			"Precipitation": self.score_precipitation(weather.precipitation),
			"Humidity": self.score_humidity(weather.humidity),
			"Visibility": self.score_visibility(weather.visibility),
			"Cloud Cover": self.score_cloud_cover(weather.cloud_cover),
			"Pressure": self.score_pressure(weather.pressure),
			"Temperature": self.score_temperature_stability(weather.temp),
		}

		overall = sum(factors[k][0] * self.weights[k] for k in self.weights)
		stars, label = self._recommendation_lines_from_score_and_factors(overall, factors)
		return AcousticScore(
			overall_score=overall,
			factors=factors,
			recommendation=f"{stars}\n{label}",
			best_hours=[],
		)

	# ----------------------------
	# Night analytics
	# ----------------------------

	def _factor_averages_for_night(self, night: Dict) -> Dict[str, float]:
		rows = night.get("all_forecasts", [])
		if not rows:
			return {}
		out = {k: [] for k in self.weights}
		for row in rows:
			for k in self.weights:
				out[k].append(row["score"].factors[k][0])
		return {k: (sum(v) / len(v)) for k, v in out.items() if v}

	def _main_concern(self, night: Dict) -> str:
		fa = self._factor_averages_for_night(night)
		if not fa:
			return "Insufficient data"
		penalties = {k: (100 - fa[k]) * self.weights[k] for k in self.weights}
		worst = max(penalties, key=penalties.get)
		return f"{worst} ({self.main_concern_hint.get(worst, 'primary risk')})"

	def _plain_language_takeaway(self, night: Dict) -> str:
		rec = self._recommendation_flag(night["average_score"])
		deploy = night["deploy_by"].strftime("%H:%M")
		peak = f"{night['peak_start'].strftime('%H:%M')}-{night['peak_end'].strftime('%H:%M')}"
		concern_factor = night["main_concern"].split(" (")[0].lower()

		if rec == "Yes":
			return f"Good night to record if you can deploy by {deploy}; best results likely around {peak}."
		if rec == "Borderline":
			return f"Possible to record if you deploy by {deploy}, but {concern_factor} may limit clarity."
		return f"Not recommended unless testing equipment; {concern_factor} is likely to limit pickup."

	def _peak_window(self, night: Dict, margin: float = 5.0) -> Tuple[datetime, datetime]:
		rows = sorted(night.get("all_forecasts", []), key=lambda x: x["time"])
		if not rows:
			t = night["best_time"]
			return t, t

		best_score = max(r["score"].overall_score for r in rows)
		threshold = best_score - margin
		best_time = night["best_time"]

		qualified = [r["time"] for r in rows if r["score"].overall_score >= threshold]
		if not qualified:
			return best_time, best_time

		groups = []
		current = [qualified[0]]
		for prev, cur in zip(qualified, qualified[1:]):
			if cur - prev == timedelta(hours=1):
				current.append(cur)
			else:
				groups.append(current)
				current = [cur]
		groups.append(current)

		containing = [g for g in groups if best_time in g]
		chosen = containing[0] if containing else max(groups, key=len)
		return chosen[0], chosen[-1]

	def _deploy_by(self, peak_start: datetime) -> datetime:
		return peak_start - timedelta(hours=1)

	def summarize_night_conditions(self, night: Dict) -> Dict[str, str]:
		rows = night.get("all_forecasts", [])
		weathers = [r["weather"] for r in rows]
		if not weathers:
			return {}

		wind_mph = [self.mps_to_mph(w.wind_speed_ground) for w in weathers]
		gust_mph = [self.mps_to_mph(w.gust_speed_ground) for w in weathers]
		humidity_vals = [w.humidity for w in weathers]
		vis_miles = [self.meters_to_miles(w.visibility) for w in weathers]
		cloud_vals = [w.cloud_cover for w in weathers]
		pressure_vals = [w.pressure for w in weathers]
		temp_f = [self.celsius_to_fahrenheit(w.temp) for w in weathers]
		precip_mm_total = sum(w.precipitation for w in weathers)
		precip_in_total = self.mm_to_inches(precip_mm_total)

		humidity_labels = [self._humidity_label(v) for v in humidity_vals]
		humidity_span = self._label_span(humidity_labels, ["Very humid", "Humid", "Moderate", "Dry"])

		vis_labels_tips = [self._visibility_label_and_tip(v) for v in vis_miles]
		vis_labels = [x[0] for x in vis_labels_tips]
		vis_tips = [x[1] for x in vis_labels_tips]
		vis_transitions = self._count_transitions(vis_labels)

		if len(set(vis_labels)) == 1:
			vis_desc, vis_tip = vis_labels[0], vis_tips[0]
		elif vis_transitions >= 2:
			vis_desc, vis_tip = "Variable", "conditions fluctuate through the night"
		else:
			vis_desc = self._label_span(vis_labels, ["Poor", "Limited", "Good", "Clear"])
			vis_tip = (
				"poorer periods may reduce clarity"
				if "significant attenuation; recording quality likely reduced" in vis_tips
				else "generally favorable for recording"
			)

		cloud_labels = [self._cloud_label(v) for v in cloud_vals]
		cloud_transitions = self._count_transitions(cloud_labels)
		if len(set(cloud_labels)) == 1:
			cloud_desc = f"{cloud_labels[0].capitalize()} throughout"
		else:
			cloud_desc = f"Going from {cloud_labels[0]} to {cloud_labels[-1]}"
			if cloud_transitions >= 2:
				cloud_desc += " (variable in between)"

		return {
			"Surface Wind": f"{self._format_range(wind_mph, decimals=1)} mph (max gust {max(gust_mph):.1f} mph)",
			"Humidity": f"{humidity_span} ({self._format_range([float(v) for v in humidity_vals], decimals=0)}% RH)",
			"Visibility": f"{vis_desc} ({self._format_range(vis_miles, decimals=1)} mi); {vis_tip}",
			"Cloud Cover": f"{cloud_desc} ({self._format_range([float(v) for v in cloud_vals], decimals=0)}%)",
			"Pressure": self._pressure_description(pressure_vals),
			"Temperature": f"{self._format_range(temp_f, decimals=0)}°F",
			"Total Precipitation": f"{precip_in_total:.2f} in ({precip_mm_total:.1f} mm)",
		}

	# ----------------------------
	# Night window grouping
	# ----------------------------

	def _check_hourly_contiguity(self, timestamps: List[datetime]) -> Tuple[bool, List[Tuple[datetime, datetime]]]:
		if len(timestamps) <= 1:
			return True, []
		ts_sorted = sorted(timestamps)
		gaps = [(a, b) for a, b in zip(ts_sorted, ts_sorted[1:]) if (b - a) != timedelta(hours=1)]
		return len(gaps) == 0, gaps

	def _analyze_night_windows(self, metrics: List[WeatherMetrics], reverse_chronological: bool = False) -> List[Dict]:
		windows: Dict[date, List[WeatherMetrics]] = {}
		for m in metrics:
			key = self._metric_to_night_key(m.timestamp)
			if key is not None:
				windows.setdefault(key, []).append(m)

		nights = []
		for key in sorted(windows.keys(), reverse=reverse_chronological):
			tw_start, tw_end = self._twilight_window_for_evening(key)
			rows = sorted(
				[w for w in windows[key] if tw_start <= w.timestamp <= tw_end],
				key=lambda x: x.timestamp,
			)
			if not rows:
				continue

			scored = [{"time": w.timestamp, "score": self.analyze_forecast(w), "weather": w} for w in rows]
			avg_score = sum(r["score"].overall_score for r in scored) / len(scored)
			best = max(scored, key=lambda x: x["score"].overall_score)
			worst = min(scored, key=lambda x: x["score"].overall_score)

			times = [r["time"] for r in scored]
			is_contiguous, gaps = self._check_hourly_contiguity(times)

			peak_start, peak_end = self._peak_window({"all_forecasts": scored, "best_time": best["time"]})
			deploy_by = self._deploy_by(peak_start)

			night = {
				"night_date": key,
				"twilight_start": tw_start,
				"twilight_end": tw_end,
				"window_start": times[0],
				"window_end": times[-1],
				"is_contiguous": is_contiguous,
				"gaps": gaps,
				"hours_count": len(times),
				"average_score": avg_score,
				"best_time": best["time"],
				"least_favorable_time": worst["time"],
				"best_condition_score": best["score"],
				"all_forecasts": scored,
				"peak_start": peak_start,
				"peak_end": peak_end,
				"deploy_by": deploy_by,
			}
			night["main_concern"] = self._main_concern(night)
			night["takeaway"] = self._plain_language_takeaway(night)
			nights.append(night)

		return nights

	def _next_evening_anchor(self) -> datetime:
		now = datetime.now()
		today = now.date()
		tonight_start, _ = self._twilight_window_for_evening(today)
		if now < tonight_start:
			return tonight_start
		tomorrow_start, _ = self._twilight_window_for_evening(today + timedelta(days=1))
		return tomorrow_start

	def get_best_nights(self, days_ahead: int = 3) -> List[Dict]:
		forecasts = self.fetch_forecast()
		if not forecasts:
			return []
		nights = self._analyze_night_windows(forecasts, reverse_chronological=False)
		anchor = self._next_evening_anchor()
		nights = [n for n in nights if n["twilight_start"] >= anchor]
		return nights[:days_ahead]

	def get_historical_nights(self, days_back: int = 3) -> List[Dict]:
		historical = self.fetch_historical(days_back)
		if not historical:
			return []
		nights = self._analyze_night_windows(historical, reverse_chronological=True)
		return nights[:days_back]

	def build_night_datasets(self, forecast_days: int = 3, historical_days: int = 3) -> Tuple[List[Dict], List[Dict]]:
		return self.get_best_nights(forecast_days), self.get_historical_nights(historical_days)

	# ----------------------------
	# Structured output
	# ----------------------------

	def _serialize_weather(self, weather: WeatherMetrics) -> Dict[str, Any]:
		return {
			"timestamp": weather.timestamp.isoformat(),
			"temp_c": weather.temp,
			"temp_f": round(self.celsius_to_fahrenheit(weather.temp), 1),
			"humidity_pct": weather.humidity,
			"wind_speed_10m_mps": weather.wind_speed_10m,
			"wind_speed_10m_mph": round(self.mps_to_mph(weather.wind_speed_10m), 1),
			"gust_speed_10m_mps": weather.gust_speed_10m,
			"gust_speed_10m_mph": round(self.mps_to_mph(weather.gust_speed_10m), 1),
			"wind_speed_ground_mps": weather.wind_speed_ground,
			"wind_speed_ground_mph": round(self.mps_to_mph(weather.wind_speed_ground), 1),
			"gust_speed_ground_mps": weather.gust_speed_ground,
			"gust_speed_ground_mph": round(self.mps_to_mph(weather.gust_speed_ground), 1),
			"cloud_cover_pct": weather.cloud_cover,
			"precipitation_mm": weather.precipitation,
			"precipitation_in": round(self.mm_to_inches(weather.precipitation), 3),
			"pressure_hpa": weather.pressure,
			"visibility_m": weather.visibility,
			"visibility_mi": round(self.meters_to_miles(weather.visibility), 2),
			"visibility_is_estimated": weather.visibility_is_estimated,
			"conditions": weather.conditions,
			"is_historical": weather.is_historical,
		}

	def _serialize_night(self, night: Dict, label: str, night_type: str) -> Dict[str, Any]:
		stars, label_text = self._recommendation_lines_for_night(night)
		night_conditions = self.summarize_night_conditions(night)

		factor_avgs = self._factor_averages_for_night(night)
		factor_avgs_serialized = {
			k: {
				"score_100": round(v, 2),
				"score_10": self.score_100_to_10(v),
			}
			for k, v in factor_avgs.items()
		}

		best_hour_factor_scores = {
			k: {
				"score_100": round(v[0], 2),
				"score_10": self.score_100_to_10(v[0]),
				"explanation": v[1],
			}
			for k, v in night["best_condition_score"].factors.items()
		}

		hourly_rows = []
		for row in night["all_forecasts"]:
			hourly_rows.append({
				"timestamp": row["time"].isoformat(),
				"overall_score_100": round(row["score"].overall_score, 2),
				"overall_score_10": self.score_100_to_10(row["score"].overall_score),
				"weather": self._serialize_weather(row["weather"]),
			})

		visibility_estimated_any = any(row["weather"].visibility_is_estimated for row in night["all_forecasts"])

		return {
			"type": night_type,
			"label": label,
			"window_start": night["window_start"].isoformat(),
			"window_end": night["window_end"].isoformat(),
			"twilight_start": night["twilight_start"].isoformat(),
			"twilight_end": night["twilight_end"].isoformat(),
			"average_score_100": round(night["average_score"], 2),
			"average_score_10": self.score_100_to_10(night["average_score"]),
			"stars": stars,
			"recommendation_text": label_text,
			"recommended": self._recommendation_flag(night["average_score"]),
			"best_time": night["best_time"].strftime("%H:%M"),
			"least_favorable_time": night["least_favorable_time"].strftime("%H:%M"),
			"peak_start": night["peak_start"].strftime("%H:%M"),
			"peak_end": night["peak_end"].strftime("%H:%M"),
			"deploy_by": night["deploy_by"].strftime("%H:%M"),
			"main_concern": night["main_concern"],
			"takeaway": night["takeaway"],
			"hours_count": night["hours_count"],
			"visibility_estimated_any": visibility_estimated_any,
			"night_conditions_summary": night_conditions,
			"factor_averages": factor_avgs_serialized,
			"best_hour_factor_scores": best_hour_factor_scores,
			"hourly": hourly_rows,
		}

	def generate_structured_output(
		self,
		forecast_nights: Optional[List[Dict]] = None,
		historical_nights: Optional[List[Dict]] = None,
	) -> Dict[str, Any]:
		if forecast_nights is None or historical_nights is None:
			forecast_nights, historical_nights = self.build_night_datasets()

		return {
			"model_version": self.model_version,
			"generated_at": datetime.now().isoformat(),
			"location": {
				"latitude": self.lat,
				"longitude": self.lon,
				"region_state_name": self.region_state_name,
				"timezone": self.timezone_name,
			},
			"units": {
				"wind": {"primary": "m/s", "display": "mph"},
				"temperature": {"primary": "C", "display": "F"},
				"visibility": {"primary": "m", "display": "mi"},
				"precipitation": {"primary": "mm", "display": "in"},
				"pressure": "hPa",
				"humidity": "%",
				"scores_internal": "0-100",
				"scores_display": "0-10",
			},
			"weights": self.weights,
			"weight_rationale": self.weight_rationale,
			"forecast_nights": [
				self._serialize_night(night, self._forecast_night_label(i), "forecast")
				for i, night in enumerate(forecast_nights, 1)
			],
			"historical_nights": [
				self._serialize_night(night, self._historical_night_label(i), "historical")
				for i, night in enumerate(historical_nights, 1)
			],
		}

	# ----------------------------
	# Report generation
	# ----------------------------

	def _decision_summary_line(self, idx_label: str, night: Dict) -> str:
		stars, _ = self._recommendation_lines_for_night(night)
		rec = self._recommendation_flag(night["average_score"])
		best_h = night["best_time"].strftime("%H:%M")
		peak = f"{night['peak_start'].strftime('%H:%M')}-{night['peak_end'].strftime('%H:%M')}"
		deploy = night["deploy_by"].strftime("%H:%M")
		concern = night["main_concern"]
		return (
			f"{idx_label:<16} {stars}  Rec: {rec}\n"
			f"{'':16} Best: {best_h}  Peak: {peak}  Deploy by: {deploy}\n"
			f"{'':16} Main concern: {concern}"
		)

	def generate_report(
		self,
		forecast_nights: Optional[List[Dict]] = None,
		historical_nights: Optional[List[Dict]] = None,
	) -> str:
		if forecast_nights is None or historical_nights is None:
			forecast_nights, historical_nights = self.build_night_datasets()

		if not forecast_nights:
			return "Unable to fetch weather data. Please check your internet connection."

		report = f"\n{'='*78}\n"
		report += "NOCTURNAL AUDIO RECORDING FORECAST: Is the weather good for recording?\n"
		report += "Optimized for audio quality, sound propagation, and low wind noise. Does not forecast migration numbers.\n"
		report += f"Location: {self._location_header_text()}  |  Timezone: {self.timezone_name}\n"
		report += "Customize latitude and longitude in code near lines ~16-17; adjust factor weights near lines ~121-137.\n"
		report += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
		report += f"{'='*78}\n"

		# Quick scan summary
		report += "\nDECISION SUMMARY (Quick Scan)\n"
		report += f"{'-'*78}\n"
		for i, night in enumerate(forecast_nights, 1):
			label = self._forecast_night_label(i)
			report += self._decision_summary_line(label, night) + "\n\n"

		# Detailed forecast
		report += f"{'='*78}\n"
		report += "FORECAST DETAIL (Next 3 Night Windows)\n"
		report += f"{'='*78}\n"

		for i, night in enumerate(forecast_nights, 1):
			tw_start, tw_end = night["twilight_start"], night["twilight_end"]
			stars, label = self._recommendation_lines_for_night(night)
			night_conditions = self.summarize_night_conditions(night)
			forecast_label = self._forecast_night_label(i)
			rec_flag = self._recommendation_flag(night["average_score"])

			report += (
				f"\n{i}. {forecast_label}: "
				f"{tw_start.strftime('%Y-%m-%d %H:%M')} (Dusk hour) → "
				f"{tw_end.strftime('%Y-%m-%d %H:%M')} (Dawn hour)\n"
			)
			report += f"   {stars}\n"
			report += f"   {label}\n"
			report += f"   Recording Quality Score: {self.format_score_10(night['average_score'])}\n"
			report += f"   Recommended: {rec_flag}\n"
			report += f"   Best Hour: {night['best_time'].strftime('%H:%M')}\n"
			report += f"   Peak Window: {night['peak_start'].strftime('%H:%M')}–{night['peak_end'].strftime('%H:%M')}\n"
			report += f"   Deploy by: {night['deploy_by'].strftime('%H:%M')}\n"
			report += f"   Main concern: {night['main_concern']}\n"
			report += f"   Takeaway: {night['takeaway']}\n"

			report += "\n   Audio Conditions for the Night:\n"
			for metric, details in night_conditions.items():
				report += f"   • {metric:20} {details}\n"

			best_hour_str = night["best_time"].strftime("%H:%M")
			report += f"\n   Audio Conditions at Best Hour ({best_hour_str}):\n"
			for factor, (score_100, explanation) in night["best_condition_score"].factors.items():
				report += f"   • {factor:20} {self.format_score_10(score_100):>6} - {explanation}\n"

		# Historical detail
		if historical_nights:
			report += f"\n{'='*78}\n"
			report += "OBSERVED CONDITIONS (Previous 3 Night Windows)\n"
			report += f"{'='*78}\n"

			for i, night in enumerate(historical_nights, 1):
				tw_start, tw_end = night["twilight_start"], night["twilight_end"]
				stars, label = self._recommendation_lines_for_night(night)
				night_conditions = self.summarize_night_conditions(night)
				historical_label = self._historical_night_label(i)
				rec_flag = self._recommendation_flag(night["average_score"])

				report += (
					f"\n{i}. {historical_label}: "
					f"{tw_start.strftime('%Y-%m-%d %H:%M')} (Dusk hour) → "
					f"{tw_end.strftime('%Y-%m-%d %H:%M')} (Dawn hour)\n"
				)
				report += f"   {stars}\n"
				report += f"   {label}\n"
				report += f"   Recording Quality Score: {self.format_score_10(night['average_score'])}\n"
				report += f"   Recommended: {rec_flag}\n"
				report += f"   Best Hour: {night['best_time'].strftime('%H:%M')}\n"
				report += f"   Peak Window: {night['peak_start'].strftime('%H:%M')}–{night['peak_end'].strftime('%H:%M')}\n"
				report += f"   Deploy by: {night['deploy_by'].strftime('%H:%M')}\n"
				report += f"   Main concern: {night['main_concern']}\n"
				report += f"   Takeaway: {night['takeaway']}\n"

				report += "\n   Audio Conditions for the Night:\n"
				for metric, details in night_conditions.items():
					report += f"   • {metric:20} {details}\n"

				best_hour_str = night["best_time"].strftime("%H:%M")
				report += f"\n   Audio Conditions at Best Hour ({best_hour_str}):\n"
				for factor, (score_100, explanation) in night["best_condition_score"].factors.items():
					report += f"   • {factor:20} {self.format_score_10(score_100):>6} - {explanation}\n"

		# Appendix
		weights_display = "\n".join(
			f"  • {factor:20} {weight:.0%} - {self.weight_rationale.get(factor, '')}"
			for factor, weight in self.weights.items()
		)

		report += f"\n{'='*78}\n"
		report += "APPENDIX: METHOD + CUSTOMIZATION\n"
		report += f"{'='*78}\n"
		report += "Code customization pointers (line numbers are estimates):\n"
		report += "  • Change location: edit LATITUDE / LONGITUDE near lines ~16-17\n"
		report += "  • Change factor weighting: edit self.weights near lines ~121-137\n\n"
		report += "Data notes:\n"
		report += "  • Timezone is automatically detected from coordinates\n"
		report += "  • Region/state label lookup tries FCC first, then Nominatim, then raw coordinates\n"
		report += "  • 10m wind is API model output; ground wind is derived estimate (~2m)\n"
		report += "  • Visibility uses API hourly visibility when available; otherwise estimated fallback\n"
		report += "  • Night windows are based on astronomical dusk-to-dawn hour bounds\n"
		report += "  • Pressure wording: 'steady' = small net change; 'very stable' = small total range\n"
		report += "  • A JSON file is also saved for structured downstream use\n\n"
		report += f"Scoring model version: {self.model_version}\n\n"
		report += "Factor Weighting:\n"
		report += weights_display + "\n"

		return report


# Backward-compatibility alias
NocturnalMigrationAlerts = NocturnalRecordingForecast


if __name__ == "__main__":
	alerts = NocturnalRecordingForecast((LATITUDE, LONGITUDE))

	forecast_nights, historical_nights = alerts.build_night_datasets()
	report = alerts.generate_report(forecast_nights, historical_nights)
	structured = alerts.generate_structured_output(forecast_nights, historical_nights)

	print(report)

	script_dir = os.path.dirname(os.path.abspath(__file__))
	basename = alerts.build_output_basename(forecast_nights)

	txt_filename = os.path.join(script_dir, f"{basename}.txt")
	json_filename = os.path.join(script_dir, f"{basename}.json")

	with open(txt_filename, "w", encoding="utf-8") as f:
		f.write(report)

	with open(json_filename, "w", encoding="utf-8") as f:
		json.dump(structured, f, indent=2)

	txt_size = os.path.getsize(txt_filename)
	json_size = os.path.getsize(json_filename)

	print(f"\n{'='*78}")
	print(f"✓ Text report saved to: {txt_filename}")
	print(f"  File size: {txt_size} bytes")
	print(f"✓ JSON data saved to: {json_filename}")
	print(f"  File size: {json_size} bytes")
	print(f"{'='*78}\n")
