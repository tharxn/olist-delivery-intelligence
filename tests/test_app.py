from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src.analysis import load_orders
from src.config import DB, ROOT

pytestmark = pytest.mark.skipif(not DB.exists(), reason="Build the original dataset before the app integration test.")


def test_dashboard_and_state_filter():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    assert not app.exception
    total = len(load_orders())
    assert app.metric[0].value == f"{total:,}"
    app.sidebar.multiselect[0].set_value(["SP"]).run()
    assert not app.exception
    assert int(app.metric[0].value.replace(",", "")) < total
    app.sidebar.slider[0].set_value(100).run()
    assert not app.exception


def test_dashboard_handles_an_empty_filtered_cohort():
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=60).run()
    import pandas as pd
    orders = load_orders()
    all_dates = pd.date_range(orders.purchased_at.min().normalize(), orders.purchased_at.max().normalize())
    empty_day = all_dates.difference(pd.DatetimeIndex(orders.purchased_at.dt.normalize().unique()))[0].date()
    app.sidebar.date_input[0].set_value((empty_day, empty_day)).run()
    # The app must render an empty-state message, with no divide-by-zero failure.
    assert not app.exception
    assert any("No orders" in value.value for value in app.info)
