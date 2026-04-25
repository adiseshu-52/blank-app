import random


def get_toss_prediction(team1, team2):
    """Predict toss winner and decision using deterministic hash for consistency."""
    combined = (team1 + team2).lower().replace(" ", "")
    # Use hash to make it deterministic for same team pair
    hash_val = hash(combined) % 100
    if hash_val % 2 == 0:
        winner = team1
    else:
        winner = team2
    
    if hash_val % 3 == 0:
        decision = "bat"
    else:
        decision = "field"
    
    return winner, decision


def get_win_probability(team1, team2, toss_winner, decision, home_team=None):
    """
    Calculate win probability for team1 based on toss, home advantage, and team stats.
    Returns probability for team1 (0-100).
    """
    import players_data
    
    base_prob = 50

    # Home advantage: if team1 is the scheduled home team
    if home_team == team1:
        base_prob += 4
    elif home_team == team2:
        base_prob -= 4

    # Toss winner advantage
    if toss_winner == team1:
        base_prob += 2
    else:
        base_prob -= 2

    # Toss decision bias (fielding first is slightly advantageous in T20)
    if decision == "field":
        if toss_winner == team1:
            base_prob += 1
        else:
            base_prob -= 1

    # Team strength based on points table
    t1_stats = players_data.POINTS_TABLE.get(team1, {})
    t2_stats = players_data.POINTS_TABLE.get(team2, {})
    
    t1_pts = t1_stats.get("Pts", 6)
    t2_pts = t2_stats.get("Pts", 6)
    t1_nrr = t1_stats.get("NRR", 0)
    t2_nrr = t2_stats.get("NRR", 0)
    
    # Points difference: each point = 1.5% swing
    pts_diff = (t1_pts - t2_pts) * 1.5
    base_prob += pts_diff
    
    # NRR difference: each 0.1 NRR = 1% swing
    nrr_diff = (t1_nrr - t2_nrr) * 10
    base_prob += nrr_diff

    # Clamp between 30 and 70 for realistic uncertainty
    return max(30, min(70, round(base_prob)))


def get_match_winner(team1, team2, win_prob):
    """
    Predict match winner based on win probability.
    win_prob is probability for team1.
    Returns (predicted_winner, winner_probability).
    """
    prob_team1 = win_prob
    prob_team2 = 100 - win_prob

    if prob_team1 >= prob_team2:
        return team1, prob_team1
    else:
        return team2, prob_team2


def get_points_table():
    """
    Returns the points table sorted by Points (desc) and NRR (desc).
    Returns list of tuples: (rank, team, played, won, lost, nr, points, nrr)
    """
    import players_data
    
    table = []
    for team, stats in players_data.POINTS_TABLE.items():
        table.append({
            "Team": team,
            "P": stats.get("M", 0),
            "W": stats.get("W", 0),
            "L": stats.get("L", 0),
            "NR": stats.get("NR", 0),
            "Pts": stats.get("Pts", 0),
            "NRR": stats.get("NRR", 0.0)
        })

    # Sort by Points descending, then NRR descending
    table.sort(key=lambda x: (x["Pts"], x["NRR"]), reverse=True)

    ranked_table = []
    for idx, row in enumerate(table, start=1):
        ranked_table.append((
            idx,
            row["Team"],
            row["P"],
            row["W"],
            row["L"],
            row["NR"],
            row["Pts"],
            row["NRR"]
        ))

    return ranked_table


def get_team_position(team_name):
    """Get current position and stats of a specific team."""
    table = get_points_table()
    for rank, team, p, w, l, nr, pts, nrr in table:
        if team == team_name:
            return {"Rank": rank, "P": p, "W": w, "L": l, "NR": nr, "Pts": pts, "NRR": nrr}
    return None


def predict_innings_scores(team_name):
    """
    Predict innings scores and wickets at 6, 10, 15, 20 overs.
    Returns dict: {6: (runs, wickets), 10: (runs, wickets), 15: (runs, wickets), 20: (runs, wickets)}
    """
    import players_data
    
    team_stats = players_data.POINTS_TABLE.get(team_name, {})
    pts = team_stats.get("Pts", 6)
    nrr = team_stats.get("NRR", 0)
    
    # Base total based on team strength
    # Average team (6 pts, 0 NRR): ~160-195
    # Strong team: +3 runs per point above 6, +20 per NRR point
    strength_bonus = (pts - 6) * 3 + int(nrr * 20)
    base_total = random.randint(160, 195) + strength_bonus
    
    # Wickets based on team batting strength (better teams lose fewer wickets)
    # Average: 5-6 wickets, Strong: 3-4, Weak: 7-9
    base_wickets = random.randint(5, 6) - int((pts - 6) * 0.4) - int(nrr * 1.5)
    base_wickets = max(2, min(9, base_wickets))
    
    # Distribute wickets across overs (non-decreasing)
    w6 = random.randint(0, min(2, base_wickets))
    remaining = base_wickets - w6
    w10 = w6 + random.randint(0, min(2, remaining))
    remaining = base_wickets - w10
    w15 = w10 + random.randint(0, min(2, remaining))
    remaining = base_wickets - w15
    w20 = w15 + random.randint(0, remaining)
    
    # Distribute runs proportionally with randomness
    r6 = int(base_total * 0.28) + random.randint(-8, 8)
    r10 = int(base_total * 0.48) + random.randint(-8, 8)
    r15 = int(base_total * 0.72) + random.randint(-8, 8)
    r20 = base_total + random.randint(-5, 5)
    
    # Ensure strict score progression (runs must increase between overs)
    r6 = max(25, min(r6, r10 - 8))
    r10 = max(r6 + 8, min(r10, r15 - 15))
    r15 = max(r10 + 15, min(r15, r20 - 20))
    r20 = max(r15 + 20, r20)
    
    # Ensure final score is within T20 realistic bounds
    r20 = max(110, min(240, r20))
    
    return {
        6:  (r6, w6),
        10: (r10, w10),
        15: (r15, w15),
        20: (r20, w20)
    }


def predict_chase_scores(team_name, target):
    """
    Predict chase scores and wickets at 6, 10, 15, 20 overs.
    Returns dict: {6: (runs, wickets), 10: (runs, wickets), 15: (runs, wickets), 20: (runs, wickets)}
    """
    import players_data
    
    team_stats = players_data.POINTS_TABLE.get(team_name, {})
    pts = team_stats.get("Pts", 6)
    nrr = team_stats.get("NRR", 0)
    
    # Stronger teams chase better
    base_ability = 0.96 + random.uniform(-0.06, 0.06)
    team_bonus = (pts - 6) * 0.025 + nrr * 0.08
    chase_ability = base_ability + team_bonus
    chase_ability = max(0.75, min(1.15, chase_ability))
    
    base_total = int(target * chase_ability)
    
    # Wickets based on team chasing strength
    base_wickets = random.randint(5, 6) - int((pts - 6) * 0.3) - int(nrr * 1.0)
    base_wickets = max(3, min(9, base_wickets))
    
    # Distribute wickets across overs
    w6 = random.randint(0, min(2, base_wickets))
    remaining = base_wickets - w6
    w10 = w6 + random.randint(0, min(2, remaining))
    remaining = base_wickets - w10
    w15 = w10 + random.randint(0, min(2, remaining))
    remaining = base_wickets - w15
    w20 = w15 + random.randint(0, remaining)
    
    # Distribute runs proportionally
    r6 = int(base_total * 0.30) + random.randint(-8, 8)
    r10 = int(base_total * 0.52) + random.randint(-8, 8)
    r15 = int(base_total * 0.75) + random.randint(-8, 8)
    r20 = base_total + random.randint(-5, 5)
    
    # Ensure strict score progression
    r6 = max(20, min(r6, r10 - 8))
    r10 = max(r6 + 8, min(r10, r15 - 15))
    r15 = max(r10 + 15, min(r15, r20 - 20))
    r20 = max(r15 + 20, r20)
    
    # Ensure within realistic bounds
    r20 = max(80, min(260, r20))
    
    return {
        6:  (r6, w6),
        10: (r10, w10),
        15: (r15, w15),
        20: (r20, w20)
    }


def get_impact_player(team_name, wickets_lost, overs_completed):
    """
    Select impact player based on match situation.
    Returns tuple: (player_name, player_role)
    """
    import players_data
    
    batter, bowler = players_data.IMPACT_PLAYERS.get(team_name, [("Unknown", "Batter"), ("Unknown", "Bowler")])
    
    if wickets_lost >= 5 and overs_completed <= 10:
        return batter
    else:
        return bowler

