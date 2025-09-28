import os
from CTFd.plugins import register_plugin_assets_directory
from CTFd.utils.plugins import override_template
from CTFd.api import CTFd_API_v1

from .api_routes import category_scores_namespace
from .views import view_category_scoreboard


def load(app):
    # get plugin location
    dir_path = os.path.dirname(os.path.realpath(__file__))
    dir_name = os.path.basename(dir_path)

    register_plugin_assets_directory(
        app,
        base_path="/plugins/" + dir_name + "/assets/",
        endpoint="category_scoreboard_assets",
    )

    # Team settings page override
    override_template(
        "scoreboard.html",
        open(os.path.join(dir_path, "assets/teams/scoreboard.html")).read(),
    )

    # Team Modals
    app.view_functions["scoreboard.listing"] = view_category_scoreboard

    CTFd_API_v1.add_namespace(category_scores_namespace, "/scoreboard")
    endpoint_name = "api.category_scoreboard_scoreboard_detail"
    i = 2
    while (
        endpoint_name not in app.url_map._rules_by_endpoint
    ):  # I cannot for the life of me figure out why it is forcing me to load the namespace each time
        endpoint_name = f"api.category_scoreboard_scoreboard_detail_{i}"
        i += 1
    app.url_map._rules_by_endpoint["api.scoreboard_scoreboard_detail"] = (
        app.url_map._rules_by_endpoint[endpoint_name]
    )
    app.view_functions["api.scoreboard_scoreboard_detail"] = app.view_functions[
        endpoint_name
    ]
