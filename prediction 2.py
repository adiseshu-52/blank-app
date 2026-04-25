import streamlit as st
import requests
import json
import re
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import date
import players_data
import prediction

st.set_page_config(page_title="IPL 2026 Live", layout="wide", initial_sidebar_state="expanded")

# Auto-refresh every 60 seconds
st_autorefresh(interval=60000, key="ipl_live_update")

# --- LIVE FEED via ESPNcricinfo JSON API ---
@st.cache_data(ttl=60)
def fetch_live_cricket_json():
    try:
        url = "https://hs-consumer-api.espncricinfo.com/v1/pages/matches/current"
        params = {"lang": "en", "latest": "true", "tzoffset": "0"}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.espncricinfo.com/",
            "Origin": "https://www.espncricinfo.com"
        }
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        matches = data.get("content", {}).get("matches", []) if isinstance(data, dict) else []
        if not matches:
            return "No Active Matches Found."
        lines = []
        for match in matches:
            teams = match.get("teams", [])
            if len(teams) == 2:
                t1_name = teams[0].get("team", {}).get("longName", "Team 1")
                t2_name = teams[1].get("team", {}).get("longName", "Team 2")
            else:
                t1_name = t2_name = "Unknown"
            status = match.get("statusText", "Status unknown")
            series_name = match.get("series", {}).get("longName", "Unknown Series")
            score_str = ""
            for score in match.get("scores", []):
                inn = score.get("inning", {})
                r = score.get("runs", 0)
                w = score.get("wickets", 0)
                o = score.get("overs", "0")
                live_text = score.get("liveText", "")
                if live_text:
                    score_str += f"{live_text} | "
                elif inn:
                    team_name = inn.get("team", {}).get("longName", "")
                    score_str += f"{team_name}: {r}/{w} ({o} ov) | "
            lines.append(f"📌 {series_name}\n🏏 {t1_name} vs {t2_name}\n📍 {status}\n📊 {score_str.strip(' | ')}\n")
        return "\n".join(lines) if lines else "No Active Matches Found."
    except Exception as e:
        return f"⚠️ Live scores temporarily unavailable.\n\nThe ESPNcricinfo API may be rate-limited or requires authentication.\n\nError: {str(e)}\n\n💡 Tip: Check live scores directly at https://www.espncricinfo.com/live-cricket-score"


def get_live_scores_for_teams(team1, team2):
    """
    Fetch live scores for a specific match between team1 and team2.
    Returns dict with innings data or None if not found.
    """
    try:
        url = "https://hs-consumer-api.espncricinfo.com/v1/pages/matches/current"
        params = {"lang": "en", "latest": "true", "tzoffset": "0"}
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.espncricinfo.com/",
            "Origin": "https://www.espncricinfo.com"
        }
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()
        matches = data.get("content", {}).get("matches", []) if isinstance(data, dict) else []
        
        # Normalize team names for matching
        team1_lower = team1.lower().replace("super giants", "supergiants")
        team2_lower = team2.lower().replace("super giants", "supergiants")
        
        for match in matches:
            teams = match.get("teams", [])
            if len(teams) != 2:
                continue
            
            match_t1 = teams[0].get("team", {}).get("longName", "")
            match_t2 = teams[1].get("team", {}).get("longName", "")
            match_t1_lower = match_t1.lower().replace("super giants", "supergiants")
            match_t2_lower = match_t2.lower().replace("super giants", "supergiants")
            
            # Check if this match involves our teams
            teams_match = (
                (team1_lower in match_t1_lower or team1_lower in match_t2_lower) and
                (team2_lower in match_t1_lower or team2_lower in match_t2_lower)
            )
            
            if not teams_match:
                continue
            
            # Extract innings scores
            innings_data = []
            for score in match.get("scores", []):
                inn = score.get("inning", {})
                if inn:
                    team_name = inn.get("team", {}).get("longName", "")
                    innings_data.append({
                        "team": team_name,
                        "runs": score.get("runs", 0),
                        "wickets": score.get("wickets", 0),
                        "overs": score.get("overs", "0"),
                        "live_text": score.get("liveText", ""),
                        "is_innings_complete": score.get("isInningsComplete", False)
                    })
            
            return {
                "match_t1": match_t1,
                "match_t2": match_t2,
                "status": match.get("statusText", ""),
                "innings": innings_data
            }
        
        return None
    except Exception:
        return None


st.title("🏏 IPL 2026 Real-Time Predictor")

# --- TODAY'S MATCH PREDICTIONS (Auto-generated for all scheduled matches) ---
today_str = str(date.today())
scheduled_matches = players_data.IPL_SCHEDULE.get(today_str, [])
scheduled_match = scheduled_matches[0] if scheduled_matches else None

if scheduled_matches:
    st.subheader("🔮 Today's Match Predictions")
    st.caption(f"Auto-generated predictions for all {len(scheduled_matches)} match(es) on {today_str}")
    
    match_cols = st.columns(len(scheduled_matches))
    for idx, (home, away) in enumerate(scheduled_matches):
        with match_cols[idx]:
            with st.container(border=True):
                st.markdown(f"**Match {idx+1}: {home} 🆚 {away}**")
                st.caption(f"🏟️ {players_data.HOME_GROUNDS.get(home, 'TBD')}")
                
                # Deterministic prediction from data analysis
                toss_win, decision = prediction.get_toss_prediction(home, away)
                win_p = prediction.get_win_probability(home, away, toss_win, decision, home_team=home)
                match_winner, winner_prob = prediction.get_match_winner(home, away, win_p)
                
                st.write(f"🪙 **Toss:** {toss_win} ({decision})")
                
                # Win probability — win_p is always probability for 'home' (first arg)
                prob_home = win_p
                prob_away = 100 - win_p
                
                st.write(f"📊 **Win Prob:** {home} {prob_home}% | {away} {prob_away}%")
                st.progress(prob_home / 100)
                
                if winner_prob >= 55:
                    st.success(f"🏆 **{match_winner}** wins ({winner_prob}%)")
                elif winner_prob >= 52:
                    st.warning(f"🏆 **{match_winner}** wins ({winner_prob}%)")
                else:
                    st.info(f"🏆 **{match_winner}** wins ({winner_prob}%)")
                
                if st.button(f"➡️ Select Match {idx+1}", key=f"select_match_{idx}"):
                    st.session_state["home_team"] = home
                    st.session_state["away_team"] = away
                    st.rerun()

# --- SIDEBAR: Match Simulator ---
st.sidebar.header("🎯 Match Simulator")

# Show today's scheduled matches in sidebar
if scheduled_matches:
    st.sidebar.markdown("---")
    st.sidebar.subheader("📅 Today's Matches")
    for i, (home, away) in enumerate(scheduled_matches, 1):
        st.sidebar.info(f"Match {i}: **{home}** 🆚 **{away}**")
    st.sidebar.markdown("---")

# Force reset button
if st.sidebar.button("🔄 Reset to Today's Match"):
    for key in ["schedule_date", "home_team", "away_team"]:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()

# Initialize / reset session state based on today's schedule
if "schedule_date" not in st.session_state:
    st.session_state["schedule_date"] = today_str

# If the date changed, reset teams to today's scheduled match
if st.session_state["schedule_date"] != today_str:
    st.session_state["schedule_date"] = today_str
    st.session_state["home_team"] = scheduled_match[0] if scheduled_match else "-- Select Home Team --"
    st.session_state["away_team"] = scheduled_match[1] if scheduled_match else "-- Select Away Team --"
else:
    if "home_team" not in st.session_state:
        st.session_state["home_team"] = scheduled_match[0] if scheduled_match else "-- Select Home Team --"
    if "away_team" not in st.session_state:
        st.session_state["away_team"] = scheduled_match[1] if scheduled_match else "-- Select Away Team --"

team_options = ["-- Select Home Team --"] + list(players_data.SQUADS.keys())

# Home Team Select
home_options = team_options.copy()
if st.session_state["away_team"] in home_options and st.session_state["away_team"] != "-- Select Away Team --":
    home_options.remove(st.session_state["away_team"])
t1 = st.sidebar.selectbox("Home Team", home_options, key="home_team")

# Away Team Select
away_pool = [t for t in players_data.SQUADS.keys() if t != t1]
away_options = ["-- Select Away Team --"] + away_pool
if st.session_state["away_team"] not in away_options:
    st.session_state["away_team"] = "-- Select Away Team --"
t2 = st.sidebar.selectbox("Away Team", away_options, key="away_team")

teams_selected = t1 != "-- Select Home Team --" and t2 != "-- Select Away Team --"

# AUTO-DETECT HOME TEAM & VENUE FROM SCHEDULE
home_team_auto = None
venue_auto = None
if teams_selected:
    # Search schedule for this matchup to find who is home
    for date_str, matches in players_data.IPL_SCHEDULE.items():
        for home, away in matches:
            if (home == t1 and away == t2) or (home == t2 and away == t1):
                home_team_auto = home
                venue_auto = players_data.HOME_GROUNDS.get(home, "TBD")
                break
        if home_team_auto:
            break
    
    # Show matchup info immediately (auto-updates)
    st.sidebar.markdown("---")
    st.sidebar.subheader("🏟️ Matchup")
    st.sidebar.info(f"**{t1}**  🆚  **{t2}**")
    
    if home_team_auto:
        st.sidebar.success(f"🏠 **Home Team:** {home_team_auto}")
        st.sidebar.caption(f"📍 **Venue:** {venue_auto}")
    else:
        st.sidebar.caption(f"📍 **Venue:** {players_data.HOME_GROUNDS.get(t1, 'TBD')}")

    # Auto-generate deterministic prediction
    toss_win, decision = prediction.get_toss_prediction(t1, t2)
    win_p = prediction.get_win_probability(t1, t2, toss_win, decision, home_team=home_team_auto)
    match_winner, winner_prob = prediction.get_match_winner(t1, t2, win_p)

    st.sidebar.success(f"🪙 **Toss Winner:** {toss_win}")
    st.sidebar.info(f"**Decision:** {decision} first")

    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Win Probability")
    col_a, col_b = st.sidebar.columns(2)
    col_a.metric(label=t1, value=f"{win_p}%")
    col_b.metric(label=t2, value=f"{100 - win_p}%")
    st.sidebar.progress(win_p / 100)

    st.sidebar.markdown("---")
    st.sidebar.subheader("🏆 Predicted Match Winner")
    if winner_prob >= 55:
        st.sidebar.success(f"**{match_winner}** wins with {winner_prob}% confidence — Strong Favorite")
    elif winner_prob >= 52:
        st.sidebar.warning(f"**{match_winner}** wins with {winner_prob}% confidence — Slight Edge")
    else:
        st.sidebar.info(f"**{match_winner}** wins with {winner_prob}% confidence — Toss-up")

    st.sidebar.markdown("---")
    st.sidebar.subheader("📈 Team Standings")
    pos1 = prediction.get_team_position(t1)
    pos2 = prediction.get_team_position(t2)
    if pos1:
        st.sidebar.write(f"• **{t1}**: Rank #{pos1['Rank']} | Pts: {pos1['Pts']} | NRR: {pos1['NRR']:+.3f}")
    if pos2:
        st.sidebar.write(f"• **{t2}**: Rank #{pos2['Rank']} | Pts: {pos2['Pts']} | NRR: {pos2['NRR']:+.3f}")

# --- MAIN CONTENT ---

# Points Table Section (Full Width)
st.markdown("---")
st.subheader("🏆 IPL 2026 Points Table (Live — Auto-updates after every match)")

try:
    points_data = prediction.get_points_table()
    df = pd.DataFrame(
        points_data,
        columns=["Rank", "Team", "P", "W", "L", "NR", "Pts", "NRR"]
    )
    
    def highlight_top4(row):
        if row["Rank"] <= 4:
            return ['background-color: #d4edda'] * len(row)
        return [''] * len(row)
    
    st.dataframe(
        df.style.apply(highlight_top4, axis=1).format({"NRR": "{:+.3f}"}),
        width='stretch',
        hide_index=True,
        height=420
    )
    st.caption("Top 4 teams highlighted in green (Qualification Zone) | Auto-refreshes every 60s")
except Exception as e:
    st.error(f"Could not load points table: {e}")

if not teams_selected:
    st.info("👈 **Please select Home Team and Away Team from the sidebar to view squads, impact players, and match simulations.**")
else:
    # Two Column Layout for Squads and Impact Players
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📋 Team Squads Comparison")
        
        # Home Team Compact Card
        with st.container(border=True):
            st.markdown(f"<h4 style='color:#1e88e5;margin:0'>🏠 {t1}</h4>", unsafe_allow_html=True)
            st.caption(f"{players_data.CAPTIONS.get(t1, '')} | 🏟️ {players_data.HOME_GROUNDS.get(t1, 'TBD')}")
            
            home_stats = prediction.get_team_position(t1)
            if home_stats:
                h1, h2, h3 = st.columns(3)
                h1.metric("Rank", f"#{home_stats['Rank']}")
                h2.metric("Record", f"{home_stats['W']}W/{home_stats['L']}L")
                h3.metric("Pts | NRR", f"{home_stats['Pts']} | {home_stats['NRR']:+.3f}")
            
            p_col1, p_col2 = st.columns(2)
            
            with p_col1:
                st.markdown("**🧢 Playing XI**")
                for name, role in players_data.SQUADS.get(t1, [])[:11]:
                    st.write(f"• {name} ({role})")
            
            with p_col2:
                st.markdown("**🔄 Reserves**")
                for name, role in players_data.SQUADS.get(t1, [])[11:]:
                    st.write(f"• {name} ({role})")
        
        st.markdown("")
        
        # Away Team Compact Card
        with st.container(border=True):
            st.markdown(f"<h4 style='color:#e53935;margin:0'>✈️ {t2}</h4>", unsafe_allow_html=True)
            st.caption(f"{players_data.CAPTIONS.get(t2, '')} | 🏟️ {players_data.HOME_GROUNDS.get(t2, 'TBD')}")
            
            away_stats = prediction.get_team_position(t2)
            if away_stats:
                a1, a2, a3 = st.columns(3)
                a1.metric("Rank", f"#{away_stats['Rank']}")
                a2.metric("Record", f"{away_stats['W']}W/{away_stats['L']}L")
                a3.metric("Pts | NRR", f"{away_stats['Pts']} | {away_stats['NRR']:+.3f}")
            
            p_col3, p_col4 = st.columns(2)
            
            with p_col3:
                st.markdown("**🧢 Playing XI**")
                for name, role in players_data.SQUADS.get(t2, [])[:11]:
                    st.write(f"• {name} ({role})")
            
            with p_col4:
                st.markdown("**🔄 Reserves**")
                for name, role in players_data.SQUADS.get(t2, [])[11:]:
                    st.write(f"• {name} ({role})")

    with col2:
        st.subheader("⚡ Impact Player Strategy")
        
        ip_col1, ip_col2 = st.columns(2)
        
        with ip_col1:
            with st.container(border=True):
                st.markdown(f"**{t1}**")
                ip1_batter, ip1_bowler = players_data.IMPACT_PLAYERS.get(t1, [("Unknown", "Impact Batter"), ("Unknown", "Impact Bowler")])
                st.write(f"🏏 {ip1_batter[0]}")
                st.write(f"🎯 {ip1_bowler[0]}")
        
        with ip_col2:
            with st.container(border=True):
                st.markdown(f"**{t2}**")
                ip2_batter, ip2_bowler = players_data.IMPACT_PLAYERS.get(t2, [("Unknown", "Impact Batter"), ("Unknown", "Impact Bowler")])
                st.write(f"🏏 {ip2_batter[0]}")
                st.write(f"🎯 {ip2_bowler[0]}")
        
        st.caption("💡 Lose 5+ wickets before 10 overs → Impact Batter comes in")
        
        st.markdown("---")
        st.subheader("📡 Live Match Tracker")
        st.caption("Auto-refreshes every 60s | Shows real scores from ESPNcricinfo when match is live")
        
        # Fetch live scores for selected teams
        live_data = get_live_scores_for_teams(t1, t2)
        
        if live_data and len(live_data.get("innings", [])) > 0:
            innings_list = live_data["innings"]
            st.success(f"🏏 **{live_data['match_t1']} vs {live_data['match_t2']}** — {live_data['status']}")
            
            # Display all innings
            for idx, inn in enumerate(innings_list):
                inn_num = idx + 1
                team_name = inn.get("team", "Unknown")
                runs = inn.get("runs", 0)
                wickets = inn.get("wickets", 0)
                overs = inn.get("overs", "0")
                
                if idx == 0:
                    st.markdown(f"**🥇 1st Innings — {team_name}**")
                    st.metric("Score", f"{runs}/{wickets}", f"{overs} overs")
                    target_runs = runs + 1
                    st.info(f"🎯 Target for 2nd innings: **{target_runs}**")
                else:
                    st.markdown(f"**🥈 2nd Innings — {team_name} (Chase)**")
                    st.metric("Score", f"{runs}/{wickets}", f"{overs} overs")
                    req_runs = max(0, target_runs - runs)
                    req_balls = max(0, 120 - int(float(overs) * 6))
                    if req_runs > 0:
                        st.warning(f"⚡ Need {req_runs} runs from {req_balls} balls")
                    else:
                        st.success(f"🏆 {team_name} WINS!")
        else:
            st.info("📡 No live match data for this pair. The tracker will automatically appear when the match goes live on ESPNcricinfo.")
            st.caption("When live: 1st innings score → auto-calculated target → 2nd innings chase tracker")
        
        st.markdown("---")
        st.subheader("📊 Key Match Insights")
        
        # Head-to-head style stats
        home_stats = prediction.get_team_position(t1)
        away_stats = prediction.get_team_position(t2)
        
        insight_col1, insight_col2 = st.columns(2)
        
        with insight_col1:
            with st.container(border=True):
                st.markdown(f"**{t1} Strengths**")
                if home_stats:
                    win_pct = (home_stats['W'] / max(home_stats['P'], 1)) * 100
                    st.write(f"• Win Rate: {win_pct:.1f}%")
                    st.write(f"• Points: {home_stats['Pts']}")
                    st.write(f"• NRR: {home_stats['NRR']:+.3f}")
                st.write(f"• Home Ground: {players_data.HOME_GROUNDS.get(t1, 'TBD')}")
        
        with insight_col2:
            with st.container(border=True):
                st.markdown(f"**{t2} Strengths**")
                if away_stats:
                    win_pct = (away_stats['W'] / max(away_stats['P'], 1)) * 100
                    st.write(f"• Win Rate: {win_pct:.1f}%")
                    st.write(f"• Points: {away_stats['Pts']}")
                    st.write(f"• NRR: {away_stats['NRR']:+.3f}")
                st.write(f"• Away at: {players_data.HOME_GROUNDS.get(t1, 'TBD')}")

# Live Feed Section (visible regardless of team selection)
st.markdown("---")
st.subheader("📡 Live Server Feed")
if st.button("🔄 Refresh Scores"):
    st.cache_data.clear()
    st.rerun()

live_data = fetch_live_cricket_json()

# Check if live feed failed and teams are selected -> show projected scores as fallback
live_failed = live_data.startswith("⚠️") or "No Active Matches Found" in live_data

if live_failed and teams_selected:
    st.warning("⚠️ Live scores unavailable — showing **Projected Scores** for selected matchup")
    
    # Determine batting order from toss prediction if available, else default
    toss_win, decision = prediction.get_toss_prediction(t1, t2)
    if decision == "bat":
        team_batting_first = toss_win
    else:
        team_batting_first = t2 if toss_win == t1 else t1
    
    team_chasing = t2 if team_batting_first == t1 else t1
    
    # Projected 1st innings
    inn_scores = prediction.predict_innings_scores(team_batting_first)
    
    # Projected 2nd innings (chase)
    target = inn_scores[20][0] + 1
    chase_scores = prediction.predict_chase_scores(team_chasing, target)
    
    st.markdown(f"**🏏 {team_batting_first} (1st Innings) vs {team_chasing} (2nd Innings)**")
    
    lf1, lf2, lf3, lf4 = st.columns(4)
    lf1.metric("6 Overs", f"{inn_scores[6][0]}/{inn_scores[6][1]}")
    lf2.metric("10 Overs", f"{inn_scores[10][0]}/{inn_scores[10][1]}")
    lf3.metric("15 Overs", f"{inn_scores[15][0]}/{inn_scores[15][1]}")
    lf4.metric("20 Overs", f"{inn_scores[20][0]}/{inn_scores[20][1]}")
    
    st.caption(f"📊 Projected total for {team_batting_first}: **{inn_scores[20][0]}/{inn_scores[20][1]}**")
    
    st.markdown("---")
    st.markdown(f"**🎯 {team_chasing} Chase (Target: {target})**")
    
    lf5, lf6, lf7, lf8 = st.columns(4)
    lf5.metric("6 Overs", f"{chase_scores[6][0]}/{chase_scores[6][1]}")
    lf6.metric("10 Overs", f"{chase_scores[10][0]}/{chase_scores[10][1]}")
    lf7.metric("15 Overs", f"{chase_scores[15][0]}/{chase_scores[15][1]}")
    lf8.metric("20 Overs", f"{chase_scores[20][0]}/{chase_scores[20][1]}")
    
    st.caption(f"📊 Projected chase for {team_chasing}: **{chase_scores[20][0]}/{chase_scores[20][1]}**")
    
    if chase_scores[20][0] >= target:
        st.success(f"🏆 Projected Winner: {team_chasing} wins the chase!")
    else:
        st.info(f"🏆 Projected Winner: {team_batting_first} defends {inn_scores[20][0]} runs!")
        
    st.caption("Data source: Prediction Engine (fallback when live feed is unavailable)")
else:
    st.code(live_data, language="markdown")
    st.caption("Data source: ESPNcricinfo JSON API | Click Refresh to update manually")
