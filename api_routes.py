from flask_restx import Namespace, Resource
from flask import request

from CTFd.models import Solves, Awards
from CTFd.utils import get_config
from CTFd.utils.user import is_admin
from CTFd.utils.dates import unix_time_to_utc, isoformat
from CTFd.utils.decorators import is_admin
from CTFd.utils.decorators.visibility import (
    check_score_visibility,
    check_account_visibility,
)
from .scores import (
    get_standings,
    get_challenges_by_category,
)

category_scores_namespace = Namespace(
    "category_scoreboard", description="Endpoint to retrieve scores by category"
)

@category_scores_namespace.route("")
class CategoryScoresList(Resource):
    @check_account_visibility
    @check_score_visibility
    def get(self):
        category = request.args.get("bracket_id", default=None)
        standings = get_standings(admin=is_admin(), category=category)
        challenges = get_challenges_by_category(category)

        team_ids = [team.account_id for team in standings]
        solves = Solves.query.filter(Solves.account_id.in_(team_ids))
        awards = Awards.query.filter(Awards.account_id.in_(team_ids))

        freeze = get_config("freeze")

        if freeze:
            solves = solves.filter(Solves.date < unix_time_to_utc(freeze))
            awards = awards.filter(Awards.date < unix_time_to_utc(freeze))

        solves = solves.all()
        awards = awards.all()

        response = {}
        for i, team in enumerate(team_ids):
            response[str(i + 1)] = {
                "id": standings[i].account_id,
                "name": standings[i].name,
                "solves": [],
            }
            for solve in solves:
                if solve.account_id == team and solve.challenge_id in challenges:
                    response[str(i + 1)]["solves"].append(
                        {
                            "challenge_id": solve.challenge_id,
                            "account_id": solve.account_id,
                            "team_id": solve.team_id,
                            "user_id": solve.user_id,
                            "value": solve.challenge.value,
                            "date": isoformat(solve.date),
                        }
                    )
            for award in awards:
                if award.account_id == team:
                    response[str(i + 1)]["solves"].append(
                        {
                            "challenge_id": None,
                            "account_id": award.account_id,
                            "team_id": award.team_id,
                            "user_id": award.user_id,
                            "value": award.value,
                            "date": isoformat(award.date),
                        }
                    )
            response[str(i + 1)]["solves"] = sorted(
                response[str(i + 1)]["solves"], key=lambda k: k["date"]
            )

        return {"success": True, "data": response}


@category_scores_namespace.route("/top/<int:count>")
@category_scores_namespace.param("count", "How many top teams to return")
class ScoreboardDetail(Resource):
    @check_account_visibility
    @check_score_visibility
    def get(self, count):
        category = request.args.get("bracket_id", default=None)
        standings = get_standings(count=count, admin=is_admin(), category=category)
        challenges = get_challenges_by_category(category)

        team_ids = [team.account_id for team in standings]
        solves = Solves.query.filter(Solves.account_id.in_(team_ids))
        awards = Awards.query.filter(Awards.account_id.in_(team_ids))

        freeze = get_config("freeze")

        if freeze:
            solves = solves.filter(Solves.date < unix_time_to_utc(freeze))
            awards = awards.filter(Awards.date < unix_time_to_utc(freeze))

        solves = solves.all()
        awards = awards.all()

        response = {}
        for i, team in enumerate(team_ids):
            response[str(i + 1)] = {
                "id": standings[i].account_id,
                "name": standings[i].name,
                "solves": [],
            }
            for solve in solves:
                if solve.account_id == team and solve.challenge_id in challenges:
                    response[str(i + 1)]["solves"].append(
                        {
                            "challenge_id": solve.challenge_id,
                            "account_id": solve.account_id,
                            "team_id": solve.team_id,
                            "user_id": solve.user_id,
                            "value": solve.challenge.value,
                            "date": isoformat(solve.date),
                        }
                    )
            for award in awards:
                if award.account_id == team:
                    response[str(i + 1)]["solves"].append(
                        {
                            "challenge_id": None,
                            "account_id": award.account_id,
                            "team_id": award.team_id,
                            "user_id": award.user_id,
                            "value": award.value,
                            "date": isoformat(award.date),
                        }
                    )
            response[str(i + 1)]["solves"] = sorted(
                response[str(i + 1)]["solves"], key=lambda k: k["date"]
            )

        return {"success": True, "data": response}
