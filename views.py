from flask import render_template, request, session, current_app as app

from CTFd.utils import config
from CTFd.utils.decorators.visibility import check_score_visibility
from CTFd.models import Teams
from .scores import get_standings, get_challenge_categories


@app.route("/scoreboard", methods=["GET", "POST"])
@check_score_visibility
def view_category_scoreboard():
    team_ids = session.get("teams_watching")
    if team_ids == None:
        team_ids = []
    if request.method == "POST":
        team_ids = [int(e) for e in request.form.getlist("teams") if str(e).isdigit()]
        if all(isinstance(item, int) for item in team_ids):
            session["teams_watching"] = team_ids

    teams = Teams.query.filter_by(banned=False)
    watching = session.get("teams_watching")

    standings = get_standings()
    categories = get_challenge_categories()
    standings_by_category = {}
    for category in categories:
        standings_by_category[category] = get_standings(category=category)

    return render_template(
        "scoreboard.html",
        teams=teams,
        watching=watching,
        standings=standings,
        categories=categories,
        standings_by_category=standings_by_category,
        score_frozen=config.is_scoreboard_frozen(),
    )
