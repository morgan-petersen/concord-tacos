from dash import Dash, html, dcc
import plotly.express as px
import pandas as pd

# Theme colors
MAIN_COLOR = "#FF4838"  # primary accent (red)
ALT_COLOR = "#000000"   # alternate accent (black)
FONT_URL = "https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600&display=swap"

# Load data once at startup
base_df = pd.read_csv("data/Concord_taco_data_alltime_RAW_EXPORT.csv")
base_df['length'] = base_df['message'].str.len()

base_df["timestamp"] = pd.to_datetime(base_df["timestamp"], errors="coerce")
base_df.sort_values("timestamp", inplace=True)
base_df["week_start"] = base_df["timestamp"].dt.to_period("W").dt.start_time

leaderboard_givers = base_df.groupby("giver_name")["tacos"].sum().reset_index().sort_values("tacos", ascending=False)
leaderboard_receivers = base_df.groupby("receiver_name")["tacos"].sum().reset_index().sort_values("tacos", ascending=False)
leaderboard_redeemers = pd.read_csv("data/Concord_redemptions_alltime.csv")
leaderboard_redeemers = leaderboard_redeemers.groupby("name")["redemption_amount"].sum().reset_index().sort_values("redemption_amount", ascending=False)

leaderboard_message_length = (
    base_df[base_df["type"] == "message"]
    .groupby("giver_name")
    .agg(message_count=("message", "size"), avg_length=("length", "mean"))
    .reset_index()
    .query("message_count >= 10")
    .sort_values("avg_length", ascending=False)
)

leaderboard_messages_sent = (
    base_df[base_df["type"] == "message"]
    .groupby("giver_name")
    .agg(message_count=("message", "size"))
    .reset_index()
    .sort_values("message_count", ascending=False)
)


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

line_df = (
    base_df.groupby(["week_start", "type"], as_index=False)["tacos"]
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

# compute weekly message counts (count of rows where type == 'message')
messages_count_df = (
    base_df[base_df["type"] == "message"].groupby("week_start").size().reset_index(name="count")
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

app = Dash(__name__, external_stylesheets=[FONT_URL])

container_style = {
    "fontFamily": "Poppins, Arial, sans-serif",
    "padding": "24px",
    "backgroundColor": "#F0E7D5",
    "minHeight": "100vh",
}

card_style = {
    "backgroundColor": "#ffffff",
    "padding": "18px",
    "borderRadius": "8px",
    "boxShadow": "0 2px 6px rgba(0,0,0,0.08)",
}

leaderboard_card_style = {**card_style, "marginBottom": "16px"}


def make_givers_leaderboard():
    return html.Div(
        [
            html.H3("Top 10 Givers", style={"margin": "0 0 12px 0", "color": MAIN_COLOR}),
            html.Div(
                [
                    html.Div(
                        make_leaderboard_rows(leaderboard_givers.head(5), "giver_name", "tacos", start_rank=1),
                        style={"flex": "1", "minWidth": "0"},
                    ),
                    html.Div(
                        make_leaderboard_rows(leaderboard_givers.iloc[5:10], "giver_name", "tacos", start_rank=6),
                        style={"flex": "1", "minWidth": "0"},
                    ),
                ],
                style={"display": "flex", "gap": "14px"},
            ),
        ],
        style=leaderboard_card_style,
    )


def make_avg_length_leaderboard():
    return html.Div(
        [
            html.H3("Top 10 Avg Message Length", style={"margin": "0 0 4px 0", "color": MAIN_COLOR}),
            html.Div("Min 10 messages", style={"margin": "0 0 12px 0", "color": "#777", "fontSize": "0.9rem"}),
            html.Div(
                [
                    html.Div(
                        make_leaderboard_rows(
                            leaderboard_message_length.head(5),
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
                            leaderboard_message_length.iloc[5:10],
                            "giver_name",
                            "avg_length",
                            start_rank=6,
                            value_format=lambda v: f"{v:.1f}",
                            secondary_value_col="message_count",
                            secondary_format=lambda v: f"({int(v):,} msgs)",
                        ),
                        style={"flex": "1", "minWidth": "0"},
                    ),
                ],
                style={"display": "flex", "gap": "14px"},
            ),
        ],
        style=leaderboard_card_style,
    )

app.layout = html.Div(
    [
        html.Div(
            html.H1(
                "Concord Tacos",
                style={"color": MAIN_COLOR, "margin": "0 0 12px 0", "fontWeight": "300"},
            ),
            style={"marginBottom": "16px"},
        ),
        html.Div(
            [
                html.Div(
                    [
                        dcc.Tabs(
                            id="top-tabs",
                            value="tacos",
                            children=[
                                dcc.Tab(
                                    label="Tacos",
                                    value="tacos",
                                    children=[
                                        dcc.Graph(id="top-graph-tacos", figure=fig, style={"width": "100%", "minWidth": "300px"}),
                                    ],
                                ),
                                dcc.Tab(
                                    label="Messages",
                                    value="messages",
                                    children=[
                                        dcc.Graph(id="top-graph-messages", figure=fig_messages, style={"width": "100%", "minWidth": "300px"}),
                                    ],
                                ),
                            ],
                            style={"marginBottom": "12px"},
                        ),
                    ],
                    style={**card_style, "flex": "1 1 65%", "minWidth": "340px"},
                ),
                html.Div(
                    [
                        dcc.Tabs(
                            id="leaderboard-tabs",
                            value="tacos",
                            children=[
                                dcc.Tab(
                                    label="Total Given",
                                    value="tacos",
                                    children=[
                                        html.Div(
                                            [
                                                html.H3("Top 10 Givers", style={"margin": "0 0 12px 0", "color": MAIN_COLOR}),
                                                html.Div(
                                                    [
                                                        html.Div(
                                                            make_leaderboard_rows(leaderboard_givers.head(5), "giver_name", "tacos", start_rank=1),
                                                            style={"flex": "1", "minWidth": "0"},
                                                        ),
                                                        html.Div(
                                                            make_leaderboard_rows(leaderboard_givers.iloc[5:10], "giver_name", "tacos", start_rank=6),
                                                            style={"flex": "1", "minWidth": "0"},
                                                        ),
                                                    ],
                                                    style={"display": "flex", "gap": "14px"},
                                                ),
                                            ],
                                            style=leaderboard_card_style,
                                        ),
                                    ],
                                ),
                                dcc.Tab(
                                    label="Avg Length",
                                    value="avg_length",
                                    children=[
                                        html.Div(
                                            [
                                                html.H3("Top 10 Avg Message Length", style={"margin": "0 0 4px 0", "color": MAIN_COLOR}),
                                                html.Div("Min 10 messages", style={"margin": "0 0 12px 0", "color": "#777", "fontSize": "0.9rem"}),
                                                html.Div(
                                                    [
                                                        html.Div(
                                                            make_leaderboard_rows(
                                                                leaderboard_message_length.head(5),
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
                                                                leaderboard_message_length.iloc[5:10],
                                                                "giver_name",
                                                                "avg_length",
                                                                start_rank=6,
                                                                value_format=lambda v: f"{v:.1f}",
                                                                secondary_value_col="message_count",
                                                                secondary_format=lambda v: f"({int(v):,} msgs)",
                                                            ),
                                                            style={"flex": "1", "minWidth": "0"},
                                                        ),
                                                    ],
                                                    style={"display": "flex", "gap": "14px"},
                                                ),
                                            ],
                                            style=leaderboard_card_style,
                                        ),
                                    ],
                                ),
                                dcc.Tab(
                                    label="Messages Sent",
                                    value="messages_sent",
                                    children=[
                                        html.Div(
                                            [
                                                html.H3("Top 10 Messages Sent", style={"margin": "0 0 12px 0", "color": MAIN_COLOR}),
                                                html.Div(
                                                    [
                                                        html.Div(
                                                            make_leaderboard_rows(
                                                                leaderboard_messages_sent.head(5),
                                                                "giver_name",
                                                                "message_count",
                                                                start_rank=1,
                                                            ),
                                                            style={"flex": "1", "minWidth": "0"},
                                                        ),
                                                        html.Div(
                                                            make_leaderboard_rows(
                                                                leaderboard_messages_sent.iloc[5:10],
                                                                "giver_name",
                                                                "message_count",
                                                                start_rank=6,
                                                            ),
                                                            style={"flex": "1", "minWidth": "0"},
                                                        ),
                                                    ],
                                                    style={"display": "flex", "gap": "14px"},
                                                ),
                                            ],
                                            style=leaderboard_card_style,
                                        ),
                                    ],
                                ),
                            ],
                            style={"marginBottom": "12px"},
                        ),
                    ],
                    style={"flex": "1 1 30%", "minWidth": "280px"},
                ),
            ],
            style={"display": "flex", "gap": "20px", "flexWrap": "wrap", "maxWidth": "1100px", "margin": "0 auto"},
        ),
    ],
    style=container_style,
)

if __name__ == "__main__":
    app.run(debug=True)
