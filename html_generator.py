
# html_generator.py

import os
import pandas as pd

# --- BEGIN TEAM COLORS ---
TEAM_COLORS = {
    "CIN": "#FB4F14",
    "DET": "#0076B6",
    "PHI": "#004C54",
    "DAL": "#041E42",
    "BUF": "#00338D",
    # ... Add all teams as needed
}
TEAM_TEXT_COLORS = {
    "CIN": "#fff",
    "DET": "#fff",
    "PHI": "#fff",
    "DAL": "#fff",
    "BUF": "#fff",
}
# --- END TEAM COLORS ---

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Best Matchups - Week {week}</title>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Segoe UI', sans-serif;
            margin: 0;
            padding: 30px;
            background-color: #f4f4f4;
            color: #333;
            max-width: 1200px;
            margin-left: auto;
            margin-right: auto;
        }}
        h1 {{
            text-align: center;
            margin-bottom: 30px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
        }}
        th, td {{
            text-align: left;
            padding: 10px;
        }}
        th {{
            background-color: #222;
            color: white;
            position: sticky;
            top: 0;
        }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        tr:hover {{ background-color: #eef; }}
        .final-high {{ background-color: #d4edda; }}
        .final-low {{ background-color: #f8d7da; }}
        .boost {{ font-weight: bold; color: #006400; }}
        .danger {{ color: #B22222; }}
        .note-icon {{ font-size: 18px; margin-right: 4px; }}
    </style>

    <!-- DataTables CSS & JS -->
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/buttons/2.4.1/css/buttons.dataTables.min.css">
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.1/js/dataTables.buttons.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.html5.min.js"></script>
    <script src="https://cdn.datatables.net/buttons/2.4.1/js/buttons.print.min.js"></script>
</head>
<body>
    <h1>📊 WR Matchup Visualizer – Week {week}</h1>
    <table id="matchupTable" class="display nowrap">
        <thead>
            <tr>
                <th>WR</th><th>Team</th><th>Opponent</th><th>Scheme</th>
                <th>Base Pts</th><th>Adj Pts</th><th>Env</th><th>Script</th><th>Final</th><th>Notes</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>

    <script>
        $(document).ready(function() {{
            $('#matchupTable').DataTable({{
                paging: true,
                searching: true,
                order: [[8, 'desc']],
                pageLength: 25,
                responsive: true,
                dom: 'Bfrtip',
                buttons: ['copy', 'csv', 'excel', 'print'],
                initComplete: function () {{
                    this.api().columns([1,2,0]).every(function () {{
                        var column = this;
                        var select = $('<select><option value="">All</option></select>')
                            .appendTo($(column.header()).empty())
                            .on('change', function () {{
                                var val = $.fn.dataTable.util.escapeRegex($(this).val());
                                column.search(val ? '^' + val + '$' : '', true, false).draw();
                            }});
                        column.data().unique().sort().each(function (d, j) {{
                            select.append('<option value="' + d + '">' + d + '</option>');
                        }});
                    }});
                }}
            }});
        }});
    </script>
</body>
</html>
"""

def generate_html_table(df):
    rows = []
    for _, row in df.iterrows():
        notes = []
        if row['env_boost'] > 1.02:
            notes.append("✅ Dome/Good weather")
        if row['env_boost'] < 0.98:
            notes.append("❄️ Weather risk")
        if row.get('game_script_boost', 1.0) > 1.05:
            notes.append("📈 Trailing game script")
        if row.get('game_script_boost', 1.0) < 0.95:
            notes.append("⛔ Game control risk")

        final_pts = round(row['adj_pts'] * row.get('game_script_boost', 1.0), 2)
        row_html = f"""
        <tr>
            <td>{row['wr_name']}</td>
            <td>{row['team']}</td>
            <td>{row['opp_team']}</td>
            <td>{row['scheme']}</td>
            <td>{row['base_pts']}</td>
            <td>{row['adj_pts']}</td>
            <td>{round(row['env_boost'], 2)}</td>
            <td>{round(row.get('game_script_boost', 1.0), 2)}</td>
            <td class="boost">{final_pts}</td>
            <td>{' | '.join(notes)}</td>
        </tr>
        """
        rows.append(row_html)
    return "\n".join(rows)

def get_headshot_url(wr_name, team):
    # Replace this with your actual image source or player ID lookup
    clean_name = wr_name.replace("'", "").replace(".", "").replace(" ", "-").lower()
    # This pattern works for most static image hosts; you can replace as needed
    return f"https://sleepercdn.com/content/nfl/players/{clean_name}.jpg"

def get_team_color(team):
    return TEAM_COLORS.get(team, "#444"), TEAM_TEXT_COLORS.get(team, "#fff")

def matchup_color(matchup_score):
    """Returns background color for matchup (green/yellow/red scale)"""
    try:
        score = float(matchup_score)
        if score >= 2.4:
            return "#24d35d"  # green
        elif score >= 2.1:
            return "#ffdf5b"  # yellow
        else:
            return "#ef6161"  # red
    except:
        return "#bbb"

def build_matchup_note(row):
    # Add more advanced details as needed
    note = (
        f"Man Win%: {row.get('man_win_rate', '--')}<br>"
        f"Zone Win%: {row.get('zone_win_rate', '--')}<br>"
        f"Sep/Man: {row.get('man_sep', '--')}<br>"
        f"Sep/Zone: {row.get('zone_sep', '--')}"
    )
    return note

def export_week_html(output_df, week):
    html_file = f"output/visualizations/week_{week:02d}.html"
    os.makedirs(os.path.dirname(html_file), exist_ok=True)

    table_rows = []
    for _, row in output_df.iterrows():
        team_color, text_color = get_team_color(row['team'])
        matchup_bg = matchup_color(row['adj_pts'])
        headshot_url = get_headshot_url(row['wr_name'], row['team'])
        tooltip = build_matchup_note(row)
        table_rows.append(f"""
            <tr>
                <td style="background: {team_color}; color: {text_color}; text-align: center;">
                    <img src="{headshot_url}" style="border-radius: 50%; width: 45px; height: 45px; border: 2px solid #fff; margin: 4px 0 0 0; background: #eee;"><br>
                    <span style="font-weight: bold; font-size: 1.05em;">{row['wr_name']}</span><br>
                    <span style="font-size: 0.95em;">{row['team']}</span>
                </td>
                <td style="background: {matchup_bg}; text-align: center;">
                    <span data-tooltip="{tooltip}" class="tooltipper" style="font-weight: bold; font-size: 1.2em; cursor: help;">{row['adj_pts']}</span>
                </td>
                <td style="text-align: center;">{row['opp_team']}</td>
                <td style="text-align: center;">{row.get('scheme','--')}</td>
                <td style="text-align: center;">{row.get('slot_weight','--')}</td>
                <td style="text-align: center;">{row.get('wide_weight','--')}</td>
                <td style="text-align: center;">{row.get('env_boost','--')}</td>
                <td style="text-align: center;">{row.get('game_script_boost','--')}</td>
            </tr>
        """)

    extra_css = """
    <style>
    body { font-family: 'Segoe UI', 'Roboto', Arial, sans-serif; background: #171a1f; color: #f8f8f8; margin: 0; padding: 0; }
    h1 { font-family: 'Montserrat', 'Segoe UI', sans-serif; font-size: 2.1em; text-align: center; font-weight: 800; letter-spacing: 1px; margin-top: 24px; margin-bottom: 6px; color: #39a7ff; text-shadow: 0 2px 8px #0003; }
    table { border-radius: 16px; border: 0; overflow: hidden; width: 97%; margin: 32px auto 64px auto; box-shadow: 0 6px 32px #0004; background: #23262f; }
    th { padding: 18px 8px 12px 8px; background: #1e2126; font-weight: 600; font-size: 1em; border: 0; color: #fff; }
    td { padding: 11px 7px; border: 0; font-size: 1.01em; }
    tr:hover td { background: #283045 !important; transition: background 0.16s; }
    .tooltipper { position: relative; }
    .tooltipper:hover:after {
        content: attr(data-tooltip);
        white-space: pre-line;
        position: absolute;
        left: 50%;
        top: 135%;
        min-width: 190px;
        background: #242731;
        color: #f8f8f8;
        padding: 14px 15px;
        border-radius: 11px;
        font-size: 0.98em;
        font-weight: 400;
        box-shadow: 0 4px 20px #0006;
        z-index: 99;
        transform: translateX(-52%);
        opacity: 0.97;
        pointer-events: none;
    }
    .dt-buttons { margin-bottom: 15px; }
    </style>
    """

    # DataTables JS/CSS and Email/Upload/Print
    extra_js = """
    <!-- jQuery and DataTables -->
    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <link rel="stylesheet" href="https://cdn.datatables.net/v/bs5/dt-2.0.5/b-3.0.2/b-html5-3.0.2/b-print-3.0.2/datatables.min.css"/>
    <script src="https://cdn.datatables.net/v/bs5/dt-2.0.5/b-3.0.2/b-html5-3.0.2/b-print-3.0.2/datatables.min.js"></script>

    <script>
    $(document).ready(function() {
        var table = $('#yaculator-table').DataTable({
            dom: 'Bfrtip',
            buttons: [
                'copy', 'csv', 'excel', 'print'
            ]
        });

        // Handle upload
        $('#csv-upload').on('change', function(e) {
            var reader = new FileReader();
            reader.onload = function(e) {
                var csv = e.target.result;
                var rows = csv.split('\\n').map(r=>r.split(','));
                var html = '';
                for (var i=1; i<rows.length; ++i) {
                    if (rows[i].length < 2) continue;
                    html += '<tr>';
                    for (var j=0; j<rows[0].length; ++j) {
                        html += '<td>' + (rows[i][j] || '') + '</td>';
                    }
                    html += '</tr>';
                }
                $('#yaculator-table tbody').html(html);
                table.clear().destroy();
                $('#yaculator-table').DataTable({
                    dom: 'Bfrtip',
                    buttons: [ 'copy', 'csv', 'excel', 'print' ]
                });
            };
            reader.readAsText(e.target.files[0]);
        });

        // Email button (creates a mailto link with CSV data)
        $('#email-btn').on('click', function() {
            var csv = table.buttons.exportData({modifier: {selected: null}}).body.map(row => row.join(",")).join("\\n");
            var mailto = "mailto:?subject=YACulator%20Week%20Table&body=" + encodeURIComponent(csv);
            window.location.href = mailto;
        });
    });
    </script>
    """

    # Upload & Email Buttons UI
    button_html = """
    <div style="display:flex;justify-content:center;gap:18px;margin-top:16px;">
        <label style="background:#24d35d;color:#23262f;padding:7px 18px;font-weight:700;border-radius:7px;cursor:pointer;">
            Upload CSV
            <input type="file" id="csv-upload" style="display:none;">
        </label>
        <button id="email-btn" style="background:#0076B6;color:#fff;padding:7px 18px;font-weight:700;border-radius:7px;cursor:pointer;">Email Table</button>
    </div>
    """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>WR Matchup Visualizer - Week {week}</title>
        {extra_css}
        {extra_js}
    </head>
    <body>
        <h1>WR Matchup Visualizer &bull; Week {week}</h1>
        {button_html}
        <table id="yaculator-table" class="display nowrap" style="width:98%;">
            <thead>
            <tr>
                <th>Player</th>
                <th>Proj Pts</th>
                <th>Opponent</th>
                <th>Scheme</th>
                <th>Slot%</th>
                <th>Wide%</th>
                <th>Env</th>
                <th>GameScript</th>
            </tr>
            </thead>
            <tbody>
            {''.join(table_rows)}
            </tbody>
        </table>
        <div style="text-align:center; color:#888; margin-bottom:25px;">&copy; {pd.Timestamp.now().year} YACulator | Inspired by PlayerProfiler</div>
    </body>
    </html>
    """

    with open(html_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"🌐 Matchup visualizer HTML saved to {html_file}")

def generate_index_page(output_dir="output/visualizations"):
    index_path = os.path.join(output_dir, "weekly_index.html")
    cards = []
    for week in range(1, 19):
        file_name = f"week_{str(week).zfill(2)}.html"
        full_path = os.path.join(output_dir, file_name)
        if os.path.exists(full_path):
            cards.append(f"""
            <div class="card">
                <h2>Week {week}</h2>
                <p class="summary">Top WR projections, matchup insights, and weather/game script context.</p>
                <a href="{file_name}" class="btn">View Matchups</a>
            </div>
            """)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>WR Matchup Visualizer Index</title>
        <style>
            body {{
                margin: 0;
                padding: 40px 20px;
                background-color: #121212;
                font-family: 'Segoe UI', sans-serif;
                color: #f0f0f0;
                display: flex;
                flex-direction: column;
                align-items: center;
            }}
            h1 {{
                color: #00bfff;
                margin-bottom: 30px;
                font-size: 2.5em;
            }}
            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
                gap: 25px;
                width: 100%;
                max-width: 1200px;
            }}
            .card {{
                background-color: #1e1e1e;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.4);
                text-align: center;
                transition: transform 0.2s, box-shadow 0.2s;
            }}
            .card:hover {{
                transform: translateY(-4px);
                box-shadow: 0 6px 16px rgba(0,0,0,0.6);
            }}
            .card h2 {{
                color: #ffffff;
                font-size: 1.5em;
                margin-bottom: 10px;
            }}
            .summary {{
                font-size: 0.95em;
                color: #cccccc;
                margin-bottom: 16px;
            }}
            .btn {{
                display: inline-block;
                padding: 10px 16px;
                background-color: #00bfff;
                color: white;
                text-decoration: none;
                border-radius: 6px;
                font-weight: bold;
            }}
            .btn:hover {{
                background-color: #008fcc;
            }}
            @media (max-width: 600px) {{
                h1 {{ font-size: 1.8em; }}
                .card h2 {{ font-size: 1.3em; }}
            }}
        </style>
    </head>
    <body>
        <h1>🏈 YACulator</h1>
        <div class="grid">
            {''.join(cards)}
        </div>
    </body>
    </html>
    """

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"🏠 Weekly homepage created at: {index_path}")
