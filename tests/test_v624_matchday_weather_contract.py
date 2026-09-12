from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / "frontend-next" / "src" / "components" / "PublicCupView.tsx"
WEATHER = ROOT / "frontend-next" / "src" / "components" / "MatchdayWeather.tsx"


def test_matchday_renders_weather_for_actual_next_match():
    view = VIEW.read_text(encoding="utf-8")
    assert 'import { MatchdayWeather } from "./MatchdayWeather"' in view
    assert '<MatchdayWeather address={cup.tournament.arena_address} matchStart={heroMatch.scheduled_start}/>' in view


def test_matchday_weather_uses_hourly_open_meteo_and_defensive_fallbacks():
    weather = WEATHER.read_text(encoding="utf-8")
    assert 'hourly", "temperature_2m,precipitation_probability,wind_speed_10m,weather_code"' in weather
    assert 'Math.abs(new Date(current).getTime()-matchTimestamp)' in weather
    assert 'if(![temperature,rain,wind,code].every(Number.isFinite))' in weather
    assert 'Vädret vid nästa match kunde inte hämtas just nu.' in weather
    assert 'Prognosen visas här när nästa match är inom 16 dagar.' in weather
