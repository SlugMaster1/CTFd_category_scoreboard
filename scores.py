from sqlalchemy.sql.expression import union_all
from sqlalchemy import func

from CTFd.cache import cache
from CTFd.models import db, Teams, TeamFieldEntries, Solves, Awards, Challenges
from CTFd.utils.dates import unix_time_to_utc
from CTFd.utils import get_config
from CTFd.utils.modes import get_model


@cache.memoize(timeout=60)
def get_team_ids():
    attr_id = get_config("category_scoreboard_attr", 0)
    attr_value = get_config("category_scoreboard_value", "hidden")

    team_ids = []
    if attr_id == "-1":  # Where team size is <value>
        teams = (
            Teams.query.outerjoin(Teams.members)
            .group_by(Teams)
            .having(func.count_(Teams.members) == attr_value)
        )
        for team in teams:
            team_ids.append(team.id)
    elif attr_id == "-2":  # Where team size is less than <value>
        teams = (
            Teams.query.outerjoin(Teams.members)
            .group_by(Teams)
            .having(func.count_(Teams.members) <= attr_value)
        )
        for team in teams:
            team_ids.append(team.id)
    elif attr_id == "-3":  # Where team size is greater than <value>
        teams = (
            Teams.query.outerjoin(Teams.members)
            .group_by(Teams)
            .having(func.count_(Teams.members) >= attr_value)
        )
        for team in teams:
            team_ids.append(team.id)
    else:
        teams = TeamFieldEntries.query.filter_by(field_id=attr_id).filter(
            func.lower(TeamFieldEntries.value) == func.lower(str(attr_value))
        )
        for team in teams:
            team_ids.append(team.team_id)

    return team_ids


@cache.memoize(timeout=60)
def get_challenge_categories():
    categories = db.session.query(Challenges.category).distinct().all()
    return [c[0] for c in categories if c[0] is not None]


@cache.memoize(timeout=60)
def get_challenges_by_category(category):
    if category:
        challenges = db.session.query(Challenges.id).filter_by(category=category).all()
    else:
        challenges = db.session.query(Challenges.id).all()
    return [c[0] for c in challenges if c[0] is not None]


def get_scores(admin=False, category=None):
    scores = (
        db.session.query(
            Solves.account_id.label("account_id"),
            db.func.sum(Challenges.value).label("score"),
            db.func.max(Solves.id).label("id"),
            db.func.max(Solves.date).label("date"),
        )
        .join(Challenges)
        .filter(Challenges.value != 0)
    )

    if category:
        scores = scores.filter(Challenges.category == category)

    scores = scores.group_by(Solves.account_id)

    awards = (
        db.session.query(
            Awards.account_id.label("account_id"),
            db.func.sum(Awards.value).label("score"),
            db.func.max(Awards.id).label("id"),
            db.func.max(Awards.date).label("date"),
        )
        .filter(Awards.value != 0)
        .group_by(Awards.account_id)
    )

    freeze = get_config("freeze")
    if not admin and freeze:
        scores = scores.filter(Solves.date < unix_time_to_utc(freeze))
        awards = awards.filter(Awards.date < unix_time_to_utc(freeze))

    if category:
        results = scores.subquery().alias("results")
    else:
        results = union_all(scores, awards).alias("results")

    sumscores = (
        db.session.query(
            results.columns.account_id,
            db.func.sum(results.columns.score).label("score"),
            db.func.max(results.columns.id).label("id"),
            db.func.max(results.columns.date).label("date"),
        )
        .group_by(results.columns.account_id)
        .subquery()
    )

    return sumscores

@cache.memoize(timeout=60)
def get_standings(count=None, admin=False, fields=None, category=None):
    if fields is None:
        fields = []
    Model = get_model()
    sumscores = get_scores(admin, category=category)

    if admin:
        standings_query = (
            db.session.query(
                Model.id.label("account_id"),
                Model.oauth_id.label("oauth_id"),
                Model.name.label("name"),
                Model.hidden,
                Model.banned,
                sumscores.columns.score,
                *fields,
            )
            .join(sumscores, Model.id == sumscores.columns.account_id)
            .order_by(sumscores.columns.score.desc(), sumscores.columns.id)
        )
    else:
        standings_query = (
            db.session.query(
                Model.id.label("account_id"),
                Model.oauth_id.label("oauth_id"),
                Model.name.label("name"),
                sumscores.columns.score,
                *fields,
            )
            .join(sumscores, Model.id == sumscores.columns.account_id)
            .filter(Model.banned == False, Model.hidden == False)
            .order_by(sumscores.columns.score.desc(), sumscores.columns.id)
        )

    if count is None:
        standings = standings_query.all()
    else:
        standings = standings_query.limit(count).all()

    return standings


@cache.memoize(timeout=60)
def get_matched_standings(count=None, admin=False, fields=None):

    if fields is None:
        fields = []
    Model = get_model()
    team_ids = get_team_ids()
    sumscores = get_scores(admin)

    """
    Admins can see scores for all users but the public cannot see banned users.
    Filters out banned users.
    Properly resolves value ties by ID.
    Different databases treat time precision differently so resolve by the row ID instead.
    """
    if admin:
        standings_query = (
            db.session.query(
                Model.id.label("account_id"),
                Model.oauth_id.label("oauth_id"),
                Model.name.label("name"),
                Model.hidden,
                Model.banned,
                sumscores.columns.score,
                *fields,
            )
            .join(sumscores, Model.id == sumscores.columns.account_id)
            .filter(Model.id.in_(team_ids))
            .order_by(sumscores.columns.score.desc(), sumscores.columns.id)
        )
    else:
        standings_query = (
            db.session.query(
                Model.id.label("account_id"),
                Model.oauth_id.label("oauth_id"),
                Model.name.label("name"),
                sumscores.columns.score,
                *fields,
            )
            .join(sumscores, Model.id == sumscores.columns.account_id)
            .filter(Model.banned == False, Model.hidden == False)
            .filter(Model.id.in_(team_ids))
            .order_by(sumscores.columns.score.desc(), sumscores.columns.id)
        )

    """
    Only select a certain amount of users if asked.
    """
    if count is None:
        standings = standings_query.all()
    else:
        standings = standings_query.limit(count).all()

    return standings
