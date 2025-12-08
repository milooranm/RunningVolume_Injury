import pytest
from datetime import date, timedelta

from Render.data_extraction_v2 import create_emptydf, populatebydate_memory


def test_initial_transform_aggregates_daily_values():
    # Build pseudo run data: two runs on the same day, one on another day
    runs = [
        {'date': '01-12-2025', 'nr. sessions': 1, 'total_km': 10.0, 'km_z34': 3.0, 'km_z5plus': 1.0},
        {'date': '01-12-2025', 'nr. sessions': 1, 'total_km': 5.0,  'km_z34': 2.0, 'km_z5plus': 0.5},
        {'date': '02-12-2025', 'nr. sessions': 1, 'total_km': 8.0,  'km_z34': 2.5, 'km_z5plus': 0.8},
    ]

    # Build pseudo other data: one alt session per day
    other = [
        {'date': '01-12-2025', 'hours_alternative': 0.5},
        {'date': '02-12-2025', 'hours_alternative': 1.25},
    ]

    # Date range covering both days
    start = date(2025, 12, 1)
    end = date(2025, 12, 2)

    empty = create_emptydf(start, end)
    df_full = populatebydate_memory(empty, runs, other, Z3_min=135, Z5_min=172)

    day1 = df_full[df_full['Date'] == '01-12-2025'].iloc[0]
    assert day1['nr. sessions'] == 2  
    assert pytest.approx(day1['total km'], 0.001) == 15.0
    assert pytest.approx(day1['km Z3-4'], 0.001) == 5.0
    assert pytest.approx(day1['km Z5-T1-T2'], 0.001) == 1.5
    assert pytest.approx(day1['hours alternative'], 0.001) == 0.5

    day2 = df_full[df_full['Date'] == '02-12-2025'].iloc[0]
    assert pytest.approx(day2['nr. sessions'], 0.001) == 1
    assert pytest.approx(day2['total km'], 0.001) == 8.0
    assert pytest.approx(day2['km Z3-4'], 0.001) == 2.5
    assert pytest.approx(day2['km Z5-T1-T2'], 0.001) == 0.8
    assert pytest.approx(day2['hours alternative'], 0.001) == 1.25
