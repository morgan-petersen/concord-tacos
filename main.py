from dash import Dash, html, dcc, Input, Output, callback
import plotly.express as px
import pandas as pd
import os

# Theme colors
MAIN_COLOR = "#FF4838"  # primary accent (red)
ALT_COLOR = "#000000"   # alternate accent (black)
FONT_URL = "https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap"

# Load data once at startup
base_df = pd.read_csv("data/Concord_taco_data_alltime_RAW_EXPORT.csv")
base_df['length'] = base_df['message'].str.len()

base_df["timestamp"] = pd.to_datetime(base_df["timestamp"], errors="coerce")
base_df.sort_values("timestamp", inplace=True)
base_df = base_df[base_df['channel_name'] == 'kudos']
base_df["week_start"] = base_df["timestamp"].dt.to_period("W").dt.start_time

redemptions_df = pd.read_csv("data/Concord_redemptions_alltime.csv")
redemptions_df['program_name'] = redemptions_df['title'].str.replace(" $10 donation to", "").str.replace(" - $10 donation", "").str.replace(" $10 donation", "").str.replace("$10 donation to", "")
redemptions_df['program_name'] = redemptions_df['program_name'].str.replace("%20", " ", regex=False).str.replace("%27", "'", regex=False).str.split(" - ").str[0]
redemptions_df['timestamp'] = pd.to_datetime(redemptions_df['timestamp'], errors='coerce')
redemptions_df['week_start'] = redemptions_df['timestamp'].dt.to_period("W").dt.start_time


def make_leaderboard_rows(df, name_col, value_col, start_rank=1, value_format=None, secondary_value_col=None, secondary_format=None):
    def format_value(value):
        if value_format:
            return value_format(value)
        if isinstance(value, (int, float)) and float(value).is_integer():
            return f"{int(value):,}"
        return f"{value:,}"

    def format_secondary(value):
        if secondary_format:
            return secondary_format(value)
        return str(value)

    return [
        html.Div(
            [
                html.Span(f"{start_rank + row_idx}.", style={"fontWeight": "600", "marginRight": "10px"}),
                html.Span(str(row[name_col]), style={"flex": "1", "minWidth": "0", "whiteSpace": "nowrap", "overflow": "hidden", "textOverflow": "ellipsis"}),
                html.Span(format_value(row[value_col]), style={"marginLeft": "10px", "color": "#555", "fontWeight": "500"}),
                html.Span(
                    format_secondary(row[secondary_value_col]) if secondary_value_col else "",
                    style={"marginLeft": "6px", "color": "#999", "fontSize": "0.85em"},
                ) if secondary_value_col else None,
            ],
            style={"display": "flex", "alignItems": "center", "padding": "6px 0", "borderBottom": "1px solid #eee"},
        )
        for row_idx, (_, row) in enumerate(df.head(5).iterrows())
    ]

def make_figures(df):
    """Generate tacos and messages figures from filtered dataframe."""
    line_df = (
        df.groupby(["week_start", "type"], as_index=False)["tacos"]
        .sum()
        .sort_values("week_start")
    )
    
    fig = px.line(
        line_df,
        x="week_start",
        y="tacos",
        color="type",
        color_discrete_map={"message": MAIN_COLOR, "reaction": ALT_COLOR},
        title="Tacos Over Time by Week and Type",
        markers=True,
    )
    
    fig.update_layout(
        xaxis_title="Week Starting",
        yaxis_title="Tacos",
        legend_title="Type",
        font=dict(family="Poppins, Arial, sans-serif"),
        legend=dict(orientation="h", y=-0.18, yanchor="top", x=0.5, xanchor="center", font=dict(size=12)),
        margin=dict(r=80),
    )
    
    messages_count_df = (
        df[df["type"] == "message"].groupby("week_start").size().reset_index(name="count")
    )
    
    fig_messages = px.line(
        messages_count_df,
        x="week_start",
        y="count",
        title="Messages Per Week",
        markers=True,
    )
    fig_messages.update_layout(xaxis_title="Week Starting", yaxis_title="Message Count")
    fig_messages.update_traces(line=dict(color=MAIN_COLOR))
    fig_messages.update_layout(font=dict(family="Poppins, Arial, sans-serif"))
    
    return fig, fig_messages


def make_redemptions_figure(redemptions_df, start_date=None, end_date=None):
    """Generate a redemptions figure from filtered redemption data."""
    if start_date and end_date:
        filtered_redemptions = redemptions_df[
            (redemptions_df["timestamp"] >= start_date) & (redemptions_df["timestamp"] <= end_date)
        ].copy()
    else:
        filtered_redemptions = redemptions_df.copy()
    
    redemptions_by_week = (
        filtered_redemptions.groupby("week_start")["redemption_amount"]
        .sum()
        .reset_index(name="amount")
    )
    
    fig_redemptions = px.line(
        redemptions_by_week,
        x="week_start",
        y="amount",
        title="Redemption Amount Per Week",
        markers=True,
    )
    fig_redemptions.update_layout(
        xaxis_title="Week Starting",
        yaxis_title="Redemption Amount",
        font=dict(family="Poppins, Arial, sans-serif"),
    )
    fig_redemptions.update_traces(line=dict(color=ALT_COLOR))
    return fig_redemptions


def make_redemption_programs_figure(redemptions_df, start_date=None, end_date=None):
    """Generate a top program redemption amount bar chart."""
    if start_date and end_date:
        filtered_redemptions = redemptions_df[
            (redemptions_df["timestamp"] >= start_date) & (redemptions_df["timestamp"] <= end_date)
        ].copy()
    else:
        filtered_redemptions = redemptions_df.copy()

    top_programs = (
        filtered_redemptions.groupby("program_name")["redemption_amount"]
        .sum()
        .reset_index(name="total_amount")
        .sort_values("total_amount", ascending=False)
        .head(10)
    )

    fig_programs = px.bar(
        top_programs,
        x="total_amount",
        y="program_name",
        orientation="h",
        title="Top Redemption Programs by Total Tacos Given",
    )
    fig_programs.update_layout(
        xaxis_title="Total Tacos Redeemed",
        yaxis_title="Program Name",
        font=dict(family="Poppins, Arial, sans-serif"),
        yaxis=dict(autorange="reversed"),
        margin=dict(l=220),
    )
    fig_programs.update_traces(marker_color=MAIN_COLOR)
    return fig_programs


def make_leaderboards_from_df(df):
    """Calculate leaderboards from filtered dataframe."""
    lbd_givers = df.groupby("giver_name")["tacos"].sum().reset_index().sort_values("tacos", ascending=False)
    
    lbd_msg_len = (
        df[df["type"] == "message"]
        .groupby("giver_name")
        .agg(message_count=("message", "nunique"), avg_length=("length", "mean"))
        .reset_index()
        .query("message_count >= 10")
        .sort_values("avg_length", ascending=False)
    )
    
    lbd_msg_sent = (
        df[df["type"] == "message"]
        .groupby("giver_name")
        .agg(message_count=("message", "nunique"))
        .reset_index()
        .sort_values("message_count", ascending=False)
    )
    
    return lbd_givers, lbd_msg_len, lbd_msg_sent

# Styling
container_style = {
    "maxWidth": "1400px",
    "margin": "0 auto",
    "padding": "30px 20px",
    "fontFamily": "Poppins, Arial, sans-serif",
    "backgroundColor": "#f9f9f9",
}

leaderboard_card_style = {
    "backgroundColor": "#fff",
    "padding": "16px",
    "borderRadius": "8px",
    "boxShadow": "0 2px 8px rgba(0,0,0,0.1)",
    "marginBottom": "12px",
}

# Initialize app
app = Dash(__name__)
app.title = "Concord Tacos"

# Generate initial figures and leaderboards
fig, fig_messages = make_figures(base_df)
fig_redemptions = make_redemptions_figure(redemptions_df)
fig_redemption_programs = make_redemption_programs_figure(redemptions_df)
lbd_givers, lbd_msg_len, lbd_msg_sent = make_leaderboards_from_df(base_df)

# Helper functions to build leaderboard sections
def build_leaderboard_giver(df):
    return html.Div([
        html.H3("Most Tacos Given", style={"margin": "0 0 12px 0", "color": MAIN_COLOR}),
        html.Div([
            html.Div(
                make_leaderboard_rows(df.head(5), "giver_name", "tacos", start_rank=1),
                style={"flex": "1", "minWidth": "0"},
            ),
            html.Div(
                make_leaderboard_rows(df.iloc[5:10], "giver_name", "tacos", start_rank=6),
                style={"flex": "1", "minWidth": "0"},
            ),
        ], style={"display": "flex", "gap": "14px"}),
    ], style=leaderboard_card_style)

def build_leaderboard_avg(df):
    return html.Div([
        html.H3("Longest Avg Message Length", style={"margin": "0 0 4px 0", "color": MAIN_COLOR}),
        html.Div("Min 10 messages", style={"margin": "0 0 12px 0", "color": "#777", "fontSize": "0.9rem"}),
        html.Div([
            html.Div(
                make_leaderboard_rows(
                    df.head(5),
                    "giver_name",
                    "avg_length",
                    start_rank=1,
                    value_format=lambda v: f"{v:.1f}",
                    secondary_value_col="message_count",
                    secondary_format=lambda v: f"({int(v):,} msgs)",
                ),
                style={"flex": "1", "minWidth": "0"},
            ),
            html.Div(
                make_leaderboard_rows(
                    df.iloc[5:10],
                    "giver_name",
                    "avg_length",
                    start_rank=6,
                    value_format=lambda v: f"{v:.1f}",
                    secondary_value_col="message_count",
                    secondary_format=lambda v: f"({int(v):,} msgs)",
                ),
                style={"flex": "1", "minWidth": "0"},
            ),
        ], style={"display": "flex", "gap": "14px"}),
    ], style=leaderboard_card_style)

def build_leaderboard_sent(df):
    return html.Div([
        html.H3("Most Messages Sent", style={"margin": "0 0 12px 0", "color": MAIN_COLOR}),
        html.Div([
            html.Div(
                make_leaderboard_rows(
                    df.head(5),
                    "giver_name",
                    "message_count",
                    start_rank=1,
                ),
                style={"flex": "1", "minWidth": "0"},
            ),
            html.Div(
                make_leaderboard_rows(
                    df.iloc[5:10],
                    "giver_name",
                    "message_count",
                    start_rank=6,
                ),
                style={"flex": "1", "minWidth": "0"},
            ),
        ], style={"display": "flex", "gap": "14px"}),
    ], style=leaderboard_card_style)

# App layout
app.layout = html.Div(
    [
        html.Link(rel="stylesheet", href=FONT_URL),
        html.Div(
            [
                html.H1("Concord Tacos", style={"margin": "0 0 20px 0", "color": MAIN_COLOR}),
                html.Div([
                    html.Label("Filter by Date Range:", style={"marginRight": "10px", "fontWeight": "600"}),
                    dcc.DatePickerRange(
                        id="date-range-picker",
                        start_date="2023-12-04",
                        end_date="2026-04-02",
                        display_format="YYYY-MM-DD",
                        style={"marginRight": "20px"},
                    ),
                ], style={"marginBottom": "20px", "display": "flex", "alignItems": "center"}),
            ],
            style={"borderBottom": "2px solid #eee", "paddingBottom": "20px"}
        ),
        html.Div(
            [
                dcc.Tabs(
                    id="chart-tabs",
                    value="tab-tacos",
                    children=[
                        dcc.Tab(
                            label="Tacos",
                            value="tab-tacos",
                            children=[
                                dcc.Graph(
                                    id="top-graph-tacos",
                                    figure=fig,
                                ),
                            ],
                            style={"padding": "12px"},
                        ),
                        dcc.Tab(
                            label="Messages",
                            value="tab-messages",
                            children=[
                                dcc.Graph(
                                    id="top-graph-messages",
                                    figure=fig_messages,
                                ),
                            ],
                            style={"padding": "12px"},
                        ),
                        dcc.Tab(
                            label="Redemptions",
                            value="tab-redemptions",
                            children=[
                                dcc.Graph(
                                    id="top-graph-redemptions",
                                    figure=fig_redemptions,
                                ),
                            ],
                            style={"padding": "12px"},
                        ),
                    ],
                ),
            ],
            style={
                "backgroundColor": "#fff",
                "borderRadius": "8px",
                "boxShadow": "0 2px 8px rgba(0,0,0,0.1)",
                "padding": "0",
                "marginTop": "20px",
            },
        ),
        html.Div(
            [
                dcc.Tabs(
                    id="leaderboard-tabs",
                    value="tab-givers",
                    children=[
                        dcc.Tab(
                            label="Total Tacos Given",
                            value="tab-givers",
                            children=[
                                html.Div(id="leaderboard-givers-content", children=build_leaderboard_giver(lbd_givers)),
                            ],
                            style={"padding": "12px"},
                        ),
                        dcc.Tab(
                            label="Avg Message Length",
                            value="tab-avg",
                            children=[
                                html.Div(id="leaderboard-avg-content", children=build_leaderboard_avg(lbd_msg_len)),
                            ],
                            style={"padding": "12px"},
                        ),
                        dcc.Tab(
                            label="Total Messages Sent",
                            value="tab-sent",
                            children=[
                                html.Div(id="leaderboard-sent-content", children=build_leaderboard_sent(lbd_msg_sent)),
                            ],
                            style={"padding": "12px"},
                        ),
                    ],
                ),
            ],
            style={
                "backgroundColor": "#fff",
                "borderRadius": "8px",
                "boxShadow": "0 2px 8px rgba(0,0,0,0.1)",
                "padding": "0",
                "marginTop": "20px",
            },
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.H3("Top Redemption Programs", style={"margin": "0 0 12px 0", "color": MAIN_COLOR}),
                        dcc.Graph(id="redemption-programs-chart", figure=fig_redemption_programs),
                    ],
                    style=leaderboard_card_style,
                ),
            ],
            style={"marginTop": "20px"},
        ),
    ],
    style=container_style,
)

# Callback to update all visualizations based on date range
@callback(
    Output("top-graph-tacos", "figure"),
    Output("top-graph-messages", "figure"),
    Output("top-graph-redemptions", "figure"),
    Output("redemption-programs-chart", "figure"),
    Output("leaderboard-givers-content", "children"),
    Output("leaderboard-avg-content", "children"),
    Output("leaderboard-sent-content", "children"),
    Input("date-range-picker", "start_date"),
    Input("date-range-picker", "end_date"),
)
def update_dashboards(start_date, end_date):
    """Update all visualizations based on selected date range."""
    # Filter base_df by date range
    if start_date and end_date:
        filtered_df = base_df[
            (base_df["timestamp"] >= start_date) & (base_df["timestamp"] <= end_date)
        ].copy()
    else:
        filtered_df = base_df.copy()
    
    # Regenerate figures
    fig_updated, fig_messages_updated = make_figures(filtered_df)
    fig_redemptions_updated = make_redemptions_figure(redemptions_df, start_date, end_date)
    fig_redemption_programs_updated = make_redemption_programs_figure(redemptions_df, start_date, end_date)
    
    # Regenerate leaderboards
    lbd_givers_updated, lbd_msg_len_updated, lbd_msg_sent_updated = make_leaderboards_from_df(filtered_df)
    
    # Build leaderboard HTML
    givers_html = build_leaderboard_giver(lbd_givers_updated)
    avg_html = build_leaderboard_avg(lbd_msg_len_updated)
    sent_html = build_leaderboard_sent(lbd_msg_sent_updated)
    
    return fig_updated, fig_messages_updated, fig_redemptions_updated, fig_redemption_programs_updated, givers_html, avg_html, sent_html

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run_server(host="0.0.0.0", port=port, debug=False) 
    # print(redemptions_df.head())
