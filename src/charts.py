import plotly.graph_objects as go

TEAL = "#157B74"
AMBER = "#CD6A31"
INK = "#182B42"
CHART_CONFIG = {"displayModeBar": False, "responsive": True, "scrollZoom": False, "displaylogo": False}


def style(figure, title, height=360):
    figure.update_layout(
        title={"text": title, "font": {"size": 16, "weight": 600}, "x": 0.01, "xanchor": "left"}, height=height,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font={"family": "Inter, sans-serif", "color": INK, "size": 12},
        margin={"l": 12, "r": 16, "t": 58, "b": 38},
        legend={"orientation": "h", "y": -0.2, "font": {"size": 11}},
        hoverlabel={"font": {"family": "Inter, sans-serif", "size": 12}},
        autosize=True,
    )
    figure.update_xaxes(showgrid=False, zeroline=False, automargin=True, title_standoff=12, nticks=5)
    figure.update_yaxes(gridcolor="#E6EBF0", zeroline=False, automargin=True, title_standoff=10)
    return figure


def monthly_chart(data):
    data = data[data.eligible_orders >= 100]
    figure = go.Figure(go.Scatter(
        x=data.purchase_month, y=data.late_rate_pct, mode="lines+markers",
        line={"color": TEAL, "width": 3}, marker={"size": 6},
        customdata=data[["eligible_orders", "late_orders"]].to_numpy(),
        hovertemplate="%{x|%b %Y}<br>Late: %{y:.1f}%<br>Eligible: %{customdata[0]:,}<br>Late orders: %{customdata[1]:,}<extra></extra>",
    ))
    figure.update_yaxes(title="Late deliveries (%)", rangemode="tozero", ticksuffix="%")
    return style(figure, "Monthly delivery reliability")


def review_chart(data):
    colors = [AMBER if value == "Late" else TEAL for value in data.delivery]
    figure = go.Figure(go.Bar(
        x=data.delivery, y=data.poor_review_pct, marker_color=colors,
        text=[f"{value:.1f}%" if value == value else "No reviews" for value in data.poor_review_pct],
        textposition="outside", cliponaxis=False,
        customdata=data[["reviewed_orders", "poor_reviews"]].to_numpy(),
        hovertemplate="%{x}<br>Poor reviews: %{y:.1f}%<br>Reviewed orders: %{customdata[0]:,}<br>1–2 star reviews: %{customdata[1]:,}<extra></extra>",
    ))
    figure.update_yaxes(title="Poor reviews (%)", rangemode="tozero", ticksuffix="%")
    return style(figure, "Delivery & customer reviews")


def state_chart(data):
    data = data.head(10).sort_values("late_orders")
    figure = go.Figure(go.Bar(
        x=data.late_orders, y=data.segment, orientation="h", marker_color=TEAL,
        customdata=data[["eligible_orders", "late_rate_pct"]].to_numpy(),
        hovertemplate="%{y}<br>Late orders: %{x:,}<br>Eligible: %{customdata[0]:,}<br>Late rate: %{customdata[1]:.1f}%<extra></extra>",
    ))
    figure.update_xaxes(title="Late orders")
    return style(figure, "Late orders by destination")


def seller_chart(data):
    data = data.head(10).iloc[::-1].copy()
    labels = data.seller_id.str[:8] + " · " + data.seller_state.fillna("?")
    figure = go.Figure(go.Scatter(
        x=data.late_rate_pct, y=labels, mode="markers",
        marker={"size": 9, "color": [AMBER if flag else TEAL for flag in data.investigate]},
        error_x={"type": "data", "symmetric": False,
                 "array": data.wilson_upper_pct-data.late_rate_pct,
                 "arrayminus": data.late_rate_pct-data.wilson_lower_pct,
                 "color": AMBER, "thickness": 1.4},
        customdata=data[["seller_id", "eligible_orders", "late_orders", "excess_late_orders"]].to_numpy(),
        hovertemplate="Seller %{customdata[0]}<br>Late rate: %{x:.1f}%<br>Eligible: %{customdata[1]:,}<br>Late: %{customdata[2]:,}<br>Excess vs benchmark: %{customdata[3]:.1f}<extra></extra>",
    ))
    if not data.empty:
        figure.add_vline(x=float(data.baseline_rate_pct.iloc[0]), line_dash="dot", line_color=TEAL)
    figure.update_xaxes(title="Late rate · 95% Wilson interval", ticksuffix="%", rangemode="tozero")
    return style(figure, "Seller investigation shortlist", height=410)


def stage_chart(data):
    data = data.head(10).iloc[::-1]
    figure = go.Figure()
    for column, name, color in (
        ("median_handling_days", "Purchase to carrier", TEAL),
        ("median_transit_days", "Carrier to customer", AMBER),
    ):
        figure.add_trace(go.Bar(
            x=data[column], y=data.route, name=name, orientation="h", marker_color=color,
            hovertemplate="%{y}<br>Median: %{x:.1f} days<extra>%{fullData.name}</extra>",
        ))
    figure.update_layout(barmode="group")
    figure.update_xaxes(title="Elapsed days · separate medians")
    return style(figure, "Delivery stages by route", height=440)
